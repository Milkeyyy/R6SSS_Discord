import datetime
import json
import os
from sys import exit
import traceback

import discord
from discord.commands import Option
from discord.ext import tasks
try:
	from dotenv import load_dotenv
except ImportError:
	pass
from pycord.i18n import _
import r6sss
from r6sss.types import MaintenanceSchedule

# ロガー
from logger import logger

# Discordのクライアント
import client as app
from client import client

# コンフィグ
from config import GuildConfig

# 埋め込み
import embeds

# Uptime Kuma
from kumasan import KumaSan

# スケジュール
from maintenance_schedule import MaintenanceScheduleManager

# サーバーステータス
from server_status import ServerStatusManager

# アイコン
import platform_icon
import status_icon as status_icon_set
import status_indicator

# ローカライズ
import localizations
from localizations import i18n, LOCALE_DATA


# Bot起動時のイベント
@client.event
async def on_ready() -> None:
	print("---------------------------------------")
	print(f" {app.NAME} - Version {app.VERSION}")
	print(f" using Pycord {discord.__version__}")
	print(" Developed by Milkeyyy")
	print("---------------------------------------")
	print("")
	await client.change_presence(
		activity=discord.Game(
			name=f"Type /create | v{app.VERSION}"
		)
	)
	logger.info("%s へログインしました！ (ID: %s)", client.user.display_name, str(client.user.id))

	# コマンドのローカライズ
	i18n.localize_commands()
	await client.sync_commands()

	# ギルドデータの確認を開始
	await GuildConfig.load()
	await GuildConfig.check()

	logger.info("サーバーステータスの定期更新開始")
	update_serverstatus.start()


# アプリケーションコマンド実行時のイベント
@client.event
async def on_application_command_completion(ctx: discord.ApplicationContext) -> None:
	full_command_name = ctx.command.qualified_name
	if ctx.guild is not None:
		logger.info(
			f"アプリケーションコマンド {full_command_name} が {ctx.guild.name} (ID: {ctx.guild.id}) にて {ctx.user} (ID: {ctx.user.id}) によって実行"
		)
	else:
		logger.info(
			f"アプリケーションコマンド {full_command_name} が {ctx.user} (ID: {ctx.user.id}) によって DM にて実行"
		)

# アプリケーションコマンドエラー時のイベント
@client.event
async def on_application_command_error(ctx: discord.ApplicationContext, ex: discord.DiscordException) -> None:
	logger.error("アプリケーションコマンド実行エラー")
	logger.error(ex)


# 1分毎にサーバーステータスを更新する
serverstatus_loop_isrunning = False

@tasks.loop(seconds=120.0)
async def update_serverstatus() -> None:
	global serverstatus_loop_isrunning
	serverstatus_loop_isrunning = True

	# Heartbeatイベントを送信 (サーバーステータスの更新が開始されたことを報告)
	KumaSan.ping(state="up", message="サーバーステータスの更新開始")

	logger.info("サーバーステータスの更新開始")

	try:
		await GuildConfig.save()

		# メンテナンススケジュール情報を取得
		sched = await MaintenanceScheduleManager.get()

		# サーバーステータスを取得/更新する
		await ServerStatusManager.update()
		if ServerStatusManager.data is None:
			return

		# 各ギルドの埋め込みメッセージIDチェック、存在する場合はメッセージを更新する
		for guild in client.guilds:
			logger.info("ギルド: %s", guild.name)
			try:
				ch_id = int(GuildConfig.data.config[str(guild.id)]["server_status_message"]["channel_id"])
				msg_id = int(GuildConfig.data.config[str(guild.id)]["server_status_message"]["message_id"])
				notif_ch_id = int(GuildConfig.data.config[str(guild.id)]["server_status_notification"]["channel_id"])
				notif_role_id = int(GuildConfig.data.config[str(guild.id)]["server_status_notification"]["role_id"])
				lang = GuildConfig.data.config[str(guild.id)]["server_status_message"]["language"]
			except Exception:
				logger.warning("ギルドデータ (%s) の読み込み失敗", guild.name)
				logger.error(traceback.format_exc())
				continue # 更新をスキップ

			try:
				if ch_id != 0 and msg_id != 0 and lang is not None:
					# IDからテキストチャンネルを取得する
					ch = guild.get_channel(ch_id)
					# チャンネルが存在しない場合はギルドデータのチャンネルIDとメッセージIDをリセットする
					if ch is None:
						GuildConfig.data.config[str(guild.id)]["server_status_message"]["channel_id"] = 0
						GuildConfig.data.config[str(guild.id)]["server_status_message"]["message_id"] = 0
						# ギルドデータを保存
						await GuildConfig.save()
						continue # ループを続ける

					ch_name = ch.name
					logger.info("- チャンネル: #%s", ch_name)

					e = ""
					try:
						# 取得したテキストチャンネルからメッセージを取得する
						msg = await ch.fetch_message(msg_id)
					except discord.errors.NotFound as err:
						msg = None
						e = err

					if msg is None:
						logger.warning("ギルド %s のメッセージ(%s)の取得に失敗", guild.name, str(msg_id))
						logger.warning(str(e))
						# メッセージが存在しない(削除されている)場合はギルドデータのチャンネルIDとメッセージIDをリセットする
						GuildConfig.data.config[str(guild.id)]["server_status_message"]["channel_id"] = 0
						GuildConfig.data.config[str(guild.id)]["server_status_message"]["message_id"] = 0
						# ギルドデータを保存
						await GuildConfig.save()
					else:
						# テキストチャンネルの名前にステータスインジケーターを設定
						try:
							if ch_name[0] in status_indicator.List:
								ch_name = ch_name[1:]
							if GuildConfig.data.config[str(guild.id)]["server_status_message"]["status_indicator"]:
								await msg.channel.edit(name=ServerStatusManager.indicator + ch_name)
						except Exception as e:
							logger.error(traceback.format_exc())
							logger.error("ギルド %s のステータスインジケーターの更新に失敗: %s", guild.name, str(e))

						try:
							# 埋め込みメッセージを生成
							server_status_embeds = await generate_serverstatus_embed(lang, sched)
						except Exception as e:
							server_status_embeds = None
							logger.error(traceback.format_exc())
							logger.error("サーバーステータスメッセージの生成に失敗: %s", str(e))

						try:
							# サーバーステータスメッセージを編集
							if server_status_embeds is not None:
								await msg.edit(embeds=server_status_embeds)
						except Exception as e:
							logger.error(traceback.format_exc())
							logger.error("サーバーステータスメッセージの生成に失敗: %s", str(e))

						try:
							# TODO: ここにサーバーステータスが変更されたかチェックするコードを書く
							if ServerStatusManager.previous_data:
								notif_embeds = []

								if client.user is not None:
									embed_author = discord.EmbedAuthor(client.user.display_name, icon_url=client.user.display_avatar.url)
								else:
									embed_author = None

								# サーバーステータスの比較を行う
								compare_result = r6sss.compare_server_status(ServerStatusManager.previous_data, ServerStatusManager.data)

								for result in compare_result:
									# ステータスの比較結果から通知用のEmbedを生成する
									notif_embeds.append(embeds.Notification.get_by_comparison_result(result, lang))
									# 対象プラットフォームの一覧テキストを生成
									# 全プラットフォームの場合は専用のテキストにする
									# if {p.platform for p in ServerStatusManager.data}.issubset(set(result.platforms)):
									# 	target_platforms_text = localizations.translate("Platform_All", lang=lang)
									# else:
									# 	target_platforms_text = " | ".join([platform_icon.LIST[p.value] + " " + p.name for p in result.platforms])

									# if result.detail == r6sss.ComparisonDetail.START_MAINTENANCE:
									# 	# メンテナンス開始
									# 	logger.info("通知送信: メンテナンス開始")
									# 	notif_embeds.append(discord.Embed(
									# 		color=discord.Colour.light_grey(),
									# 		title=localizations.translate("Title_Maintenance_Start", lang=lang),
									# 		description="**" + localizations.translate("TargetPlatform", lang=lang) + ": " + target_platforms_text + "**",
									# 		author=embed_author,
									# 	))

								# 通知メッセージを送信するチャンネルを取得
								notif_ch = guild.get_channel(notif_ch_id)
								notif_role = guild.get_role(notif_role_id)

								# メンションが可能な場合はメンション用のテキストを設定
								if notif_role is not None and notif_role.mentionable:
									notif_role_mention = notif_role.mention
								else:
									notif_role_mention = ""

								# 通知メッセージを送信
								if notif_ch is not None and notif_embeds is not None:
									for notif_embed in notif_embeds:
										if notif_embed is not None:
											notif_embed.description = f"[**💬 {localizations.translate('Notification_Show_Server_Status', lang=lang)}**]({msg.jump_url})\n{notif_embed.description}"
									if notif_embeds:
										# 自動削除が有効の場合は削除までの時間を指定する
										notif_delete_after_seconds = int(GuildConfig.data.config[str(guild.id)]["server_status_notification"]["delete_after"])
										if notif_delete_after_seconds > 0:
											await notif_ch.send(
												content=localizations.translate("Notification_Server_Status_Updated", lang=lang) + "\n" + notif_role_mention,
												embeds=notif_embeds,
												delete_after=notif_delete_after_seconds
											)
										# 自動削除が無効の場合は削除までの時間を指定しない
										else:
											await notif_ch.send(
												content=localizations.translate("Notification_Server_Status_Updated", lang=lang) + "\n" + notif_role_mention,
												embeds=notif_embeds
											)

						except Exception as e:
							logger.error(traceback.format_exc())
							logger.error("サーバーステータス通知メッセージの送信に失敗: %s", str(e))

			except Exception as e:
				logger.error("ギルド %s のサーバーステータスメッセージ(%s)の更新に失敗", guild.name, str(msg_id))
				logger.error(traceback.format_exc())

	except Exception as e:
		logger.error(traceback.format_exc())
		KumaSan.ping(state="pending", message="サーバーステータスの更新エラー: " + str(e))

	logger.info("サーバーステータスの更新完了")

	KumaSan.ping(state="up", message="サーバーステータスの更新完了")

@update_serverstatus.after_loop
async def after_updateserverstatus() -> None:
	global serverstatus_loop_isrunning

	serverstatus_loop_isrunning = False
	logger.info("サーバーステータスの定期更新終了")
	if not serverstatus_loop_isrunning:
		update_serverstatus.start()

# サーバーステータス埋め込みメッセージを更新
async def generate_serverstatus_embed(locale, sched: MaintenanceSchedule) -> list[discord.Embed]:
	embed_settings = {
		"PC": [discord.Colour.from_rgb(255, 255, 255), 2], # 埋め込みの色, 埋め込みのスペーシング
		"PS4": [discord.Colour.from_rgb(0, 67, 156), 0],
		"PS5": [discord.Colour.from_rgb(0, 67, 156), 1],
		"XB1": [discord.Colour.from_rgb(16, 124, 16), 0],
		"XBSX": [discord.Colour.from_rgb(16, 124, 16), 1]
	}

	embeds = []

	# サーバーステータスを取得
	status_list = ServerStatusManager.data

	# サーバーステータスが取得できない場合は、エラーメッセージを返す
	if status_list is None:
		return [
			discord.Embed(
				color=discord.Colour.light_grey(),
				title=localizations.translate("Embed_Unknown_Title", lang=locale),
				description=localizations.translate("Embed_Unknown_Desc", lang=locale),
			)
		]

	# 各プラットフォームごとの埋め込みメッセージを作成
	embed = discord.Embed(color=embed_settings["PC"][0]) # 色は白で固定
	embed.title = "📶 R6S Server Status"
	embed.description = "🕒 " + localizations.translate("Last Update", lang=locale) + ": " + f"<t:{ServerStatusManager.updated_at}:f> (<t:{ServerStatusManager.updated_at}:R>)"
	embed.set_footer(text="⚠️\n" + localizations.translate("NotAffiliatedWithOrRndorsedBy", lang=locale))

	status_index = -1
	for status in status_list:
		status_index += 1

		connectivity_text_list = []

		pf_id = status.platform.name # PC, PS4, XB1...
		pf_display_name = status.platform.value # プラットフォームの表示名

		if pf_id.startswith("_"):
			continue

		# サーバーの状態によってアイコンを変更する
		# 問題なし
		if status.connectivity == "Operational":
			status_icon = status_icon_set.OPERATIONAL
		# 計画メンテナンス
		elif status.connectivity == "Maintenance":
			status_icon = status_icon_set.MAINTENANCE
		# 想定外の問題
		elif status.connectivity == "Interrupted":
			status_icon = status_icon_set.INTERRUPTED
		# 想定外の停止
		elif status.connectivity == "Degraded":
			status_icon = status_icon_set.DEGRADED
		# それ以外
		else:
			status_icon = status_icon_set.UNKNOWN

		connectivity_text = localizations.translate(status.connectivity, lang=locale)

		mt_text = ""
		if status.maintenance:
			status_icon = status_icon_set.MAINTENANCE
			connectivity_text = localizations.translate("Maintenance", lang=locale)

		features_list = []
		features_text = ""
		features_status_text = ""
		# 各サービスをループしてステータスに合わせてアイコンとテキストを設定
		#for f, s in status[pf_id]["Status"]["Features"].items():
		for s in [("Authentication", status.authentication), ("Matchmaking", status.matchmaking), ("Purchase", status.purchase)]: 
			# 通常
			f_status_icon = status_icon_set.OPERATIONAL
			features_status_text = localizations.translate(s[1], lang=locale)
			# 停止
			if s[1] != "Operational":
				f_status_icon = status_icon_set.DEGRADED
			# メンテナンス
			if status.maintenance:
				f_status_icon = status_icon_set.MAINTENANCE
			# 不明
			if s[1] == "Unknown":
				f_status_icon = status_icon_set.UNKNOWN
				features_status_text = localizations.translate("Unknown", lang=locale)

			features_list.append("" + localizations.translate(s[0], lang=locale) + "\n┗ " + f_status_icon + "`" + features_status_text + "`")

		features_text = "" + "\n".join(features_list)

		# 埋め込みメッセージにプラットフォームのフィールドを追加
		connectivity_text_list.append(mt_text + features_text)

		# プラットフォームのステータスのフィールドを追加
		embed.add_field(
			name=platform_icon.LIST[status.platform.name] + " " + pf_display_name + " - " + status_icon + "**`" + connectivity_text + "`**",
			value="\n".join(connectivity_text_list)
		)
		# 各プラットフォームごとに別の行にするために、リストで指定された数の空のフィールドを挿入する
		# for _ in range(embed_settings[status.platform.value][1]):
		# 	embed.add_field(name="", value="")
		for _ in range(list(embed_settings.values())[status_index][1]):
			embed.add_field(name="", value="")

	embeds.append(embed)

	# スケジュール埋め込みを生成
	create = True
	pf_list_text = ""
	if sched:
		#platform_list = [p["Name"] for p in sched["Platforms"]]
		platform_list = sched.platforms

		# タイムスタンプを整数へ変換
		date_timestamp = int(sched.date.timestamp())

		# 全プラットフォーム同一
		# if "All" in platform_list:
		# 	# スケジュールが範囲内か判定
		# 	if datetime.datetime.now().timestamp() >= (date_timestamp + (sched.downtime * 60)):
		# 		create = False
		# 	# プラットフォーム一覧テキストを生成
		# 	pf_list_text = "・**" + localizations.translate('Platform_All', lang=locale) + "**\n"
		# else: # プラットフォーム別
		# スケジュールが範囲内か判定
		if datetime.datetime.now().timestamp() >= (date_timestamp + (sched.downtime * 60)):
			create = False
		else: # TODO: プラットフォームごとに実施日時が異なる場合があるかもしれないのでそれに対応する？
			for p in platform_list:
				# プラットフォーム一覧テキストを生成
				pf_list_text = pf_list_text + "- **" + localizations.translate(f'Platform_{p.name}', lang=locale) + "**\n"

		if create:
			# 埋め込みメッセージを生成
			embed = discord.Embed(
				colour=discord.colour.Colour.nitro_pink(),
				title=":wrench::calendar: " + localizations.translate("MaintenanceSchedule", lang=locale),
				description="**" + sched.title + "**\n" + sched.detail,
				footer=discord.EmbedFooter("⚠️\n" + localizations.translate("MaintenanceSchedule_Notes", lang=locale)),
				fields=[
					# ダウンタイム
					discord.EmbedField(
						name="**:clock3: " + localizations.translate("MaintenanceSchedule_Downtime", lang=locale) + "**",
						value="- " + str(sched.downtime) + " " + localizations.translate("MaintenanceSchedule_Downtime_Minute", lang=locale)
					),
					# 予定日時
					discord.EmbedField(
						name="**:calendar: " + localizations.translate("MaintenanceSchedule_ScheduledDT", lang=locale) + "**",
						value=f"- <t:{date_timestamp}:f> (<t:{date_timestamp}:R>)"
					),
					# 対象プラットフォーム一覧
					discord.EmbedField(
						name="**:video_game: " + localizations.translate("MaintenanceSchedule_TargetPlatform", lang=locale) + "**",
						value=pf_list_text
					)
				]
			)
			# パッチノートのURLが指定されている場合は末尾にフィールドを追加する
			if sched.patchnotes.startswith(("http://", "https://")):
				embed.fields.append(
					discord.EmbedField(
						name="**:notepad_spiral: " + localizations.translate("MaintenanceSchedule_PatchNotes", lang=locale) + "**",
						value=sched.patchnotes
					)
				)
		else: # 予定されているメンテナンスがない場合
			embed = discord.Embed(
				colour=discord.colour.Colour.nitro_pink(),
				title=":wrench::calendar: " + localizations.translate("MaintenanceSchedule", lang=locale),
				description=localizations.translate("MaintenanceSchedule_NoMaintenanceScheduled", lang=locale),
				footer=discord.EmbedFooter("⚠️\n" + localizations.translate("MaintenanceSchedule_Notes", lang=locale))
			)

		embeds.append(embed)

	return embeds

# コマンド
@client.slash_command()
@discord.guild_only()
@discord.default_permissions(administrator=True)
async def setlanguage(ctx: discord.ApplicationContext,
	locale: Option(
		str,
		choices=LOCALE_DATA.keys()
	)
) -> None:
	await ctx.defer(ephemeral=True)

	try:
		# ギルドデータをチェック
		await GuildConfig.check_guild(ctx.guild.id)

		if locale in localizations.LOCALE_DATA:
			#GuildConfig.data.config[str(ctx.guild.id)]["server_status_message"]["language"] = [k for k, v in localizations.LOCALE_DATA.keys() if v == locale][0]
			GuildConfig.data.config[str(ctx.guild.id)]["server_status_message"]["language"] = locale
		else:
			GuildConfig.data.config[str(ctx.guild.id)]["server_status_message"]["language"] = "en_GB"

		# ギルドデータを保存
		await GuildConfig.save()

		await ctx.send_followup(embed=embeds.Notification.success(description=_("Cmd_setlanguage_Success", GuildConfig.data.config[str(ctx.guild.id)]["server_status_message"]["language"])))
	except Exception:
		# 設定をリセット
		GuildConfig.data.config[str(ctx.guild.id)]["server_status_message"]["language"] = "en_GB"
		await GuildConfig.save()
		logger.error(traceback.format_exc())
		await ctx.send_followup(embed=embeds.Notification.internal_error())

@client.slash_command()
@discord.guild_only()
@discord.default_permissions(administrator=True)
async def setindicator(ctx: discord.ApplicationContext,
	enable: Option(
		bool
	)
) -> None:
	await ctx.defer(ephemeral=True)

	try:
		# ギルドデータをチェック
		await GuildConfig.check_guild(ctx.guild.id)

		GuildConfig.data.config[str(ctx.guild.id)]["server_status_message"]["status_indicator"] = enable

		# ギルドデータを保存
		await GuildConfig.save()

		await ctx.send_followup(embed=embeds.Notification.success(description=_("Cmd_setindicator_Success", str(enable))))
	except Exception:
		# 設定をリセット
		GuildConfig.data.config[str(ctx.guild.id)]["server_status_message"]["status_indicator"] = False
		await GuildConfig.save()
		logger.error(traceback.format_exc())
		await ctx.send_followup(embed=embeds.Notification.internal_error())

@client.slash_command()
@discord.guild_only()
@discord.default_permissions(administrator=True)
async def setnotification(ctx: discord.ApplicationContext,
	enable: Option(
		bool,
		required=True
	),
	channel: Option(
		discord.TextChannel,
		required=False
	),
	role: Option(
		discord.Role,
		required=False
	),
	auto_delete: Option(
		int,
		required=False,
		default=10,
		min_value=0,
		max_value=600
	)
) -> None:
	await ctx.defer(ephemeral=True)

	try:
		# ギルドデータをチェック
		await GuildConfig.check_guild(ctx.guild.id)

		# 有効化
		if enable:
			# チャンネルが指定されていない場合はコマンドが実行されたチャンネルにする
			if channel is None:
				ch_id = ctx.channel_id
			else:
				ch_id = channel.id

			# 指定されたチャンネルが存在するかチェックする
			ch = client.get_channel(ch_id)
			# 見つからない場合はエラーメッセージを送信する
			if not ch:
				await ctx.send_followup(embed=embeds.Notification.error(description=_("CmdMsg_TextChannelNotFound")))
				return
			# メッセージを送信する権限がない場合もエラーメッセージを送信する
			if not ch.can_send():
				await ctx.send_followup(embed=embeds.Notification.error(description=_("CmdMsg_DontHavePermission_SendMessage")))
				return

			# ロールが指定されている場合
			if role:
				# 指定されたロールがメンション可能かチェックする
				# メンションができない場合はエラーメッセージを送信する
				if not role.mentionable:
					await ctx.send_followup(embed=embeds.Notification.error(description=_("Cmd_setnotification_RoleIsNotMentionable")))
					return
				# 指定されたロールのIDを保存
				GuildConfig.data.config[str(ctx.guild.id)]["server_status_notification"]["role_id"] = role.id
			# ロールが指定されていない場合
			else:
				# メンションを無効化
				GuildConfig.data.config[str(ctx.guild.id)]["server_status_notification"]["role_id"] = 0

			# 自動削除の値が設定されている場合
			if auto_delete:
				# 秒数を保存
				GuildConfig.data.config[str(ctx.guild.id)]["server_status_notification"]["auto_delete"] = auto_delete
			# 指定されていない場合はデフォルト値の10秒にする
			else:
				GuildConfig.data.config[str(ctx.guild.id)]["server_status_notification"]["auto_delete"] = 10

			# 指定されたチャンネルのIDを保存
			GuildConfig.data.config[str(ctx.guild.id)]["server_status_notification"]["channel_id"] = ch_id

		# 無効化
		else:
			GuildConfig.data.config[str(ctx.guild.id)]["server_status_notification"]["channel_id"] = 0
			GuildConfig.data.config[str(ctx.guild.id)]["server_status_notification"]["role_id"] = 0
			GuildConfig.data.config[str(ctx.guild.id)]["server_status_notification"]["auto_delete"] = 0

		# ギルドデータを保存
		await GuildConfig.save()

		# 設定完了メッセージを送信する
		success_embed = embeds.Notification.success(description=_("Cmd_setnotification_Success", _(str(enable))))
		if enable:
			# テキストチャンネルの項目
			success_embed.add_field(name=_("Cmd_setnotification_Channel"), value=ch.mention)
			# メンションが有効かどうかの項目
			if role:
				mention_settings_text = role.mention
			else:
				mention_settings_text = _("False")
			success_embed.add_field(name=_("Cmd_setnotification_Mention"), value=mention_settings_text)
		await ctx.send_followup(embed=success_embed)
	# 例外発生時
	except Exception:
		# 設定をリセット
		GuildConfig.data.config[str(ctx.guild.id)]["server_status_notification"]["channel_id"] = 0
		GuildConfig.data.config[str(ctx.guild.id)]["server_status_notification"]["role_id"] = 0
		GuildConfig.data.config[str(ctx.guild.id)]["server_status_notification"]["auto_delete"] = 0
		await GuildConfig.save()
		logger.error(traceback.format_exc())
		await ctx.send_followup(embed=embeds.Notification.internal_error())

@client.slash_command()
@discord.guild_only()
@discord.default_permissions(send_messages=True)
async def status(ctx: discord.ApplicationContext) -> None:
	await ctx.defer(ephemeral=False)
	try:
		sched = MaintenanceScheduleManager.schedule
		await ctx.send_followup(embeds=await generate_serverstatus_embed(GuildConfig.data.config[str(ctx.guild_id)]["server_status_message"]["language"], sched))
	except Exception:
		logger.error(traceback.format_exc())
		await ctx.send_followup(embed=embeds.Notification.internal_error())

@client.slash_command()
@discord.guild_only()
@discord.default_permissions(administrator=True)
async def create(ctx: discord.ApplicationContext,
	channel: Option(
		discord.TextChannel,
		required=False
	)
) -> None:
	await ctx.defer(ephemeral=True)

	try:
		# ギルドデータをチェック
		await GuildConfig.check_guild(ctx.guild.id)

		additional_msg = ""
		if GuildConfig.data.config[str(ctx.guild_id)]["server_status_message"]["message_id"] != 0:
			additional_msg = f"\n({_('Cmd_create_OldMessagesWillNoLongerBeUpdated')})"

		if channel is None:
			ch_id = ctx.channel_id()
		else:
			ch_id = channel.id
		ch = client.get_channel(ch_id)

		# サーバーステータス埋め込みメッセージを送信
		try:
			sched = MaintenanceScheduleManager.schedule
			msg = await ch.send(embeds=await generate_serverstatus_embed(GuildConfig.data.config[str(ctx.guild_id)]["server_status_message"]["language"], sched))
		except Exception as e:
			# 権限エラー
			if isinstance(e, discord.errors.ApplicationCommandInvokeError) and str(e).endswith("Missing Permissions"):
				await ctx.send_followup(embed=embeds.Notification.error(description=_("CmdMsg_DontHavePermission_SendMessage", ch.mention)))
			# それ以外のエラー
			else:
				logger.error(traceback.format_exc())
				await ctx.send_followup(embed=embeds.Notification.internal_error())
			return

		# 送信したチャンネルとメッセージのIDをギルドデータへ保存する
		GuildConfig.data.config[str(ctx.guild_id)]["server_status_message"]["channel_id"] = ch_id
		GuildConfig.data.config[str(ctx.guild_id)]["server_status_message"]["message_id"] = msg.id

		# ギルドデータを保存
		await GuildConfig.save()

		await ctx.send_followup(embed=embeds.Notification.success(description=_("Cmd_create_Success", ch.mention) + additional_msg))
	except Exception:
		# 設定をリセット
		GuildConfig.data.config[str(ctx.guild_id)]["server_status_message"]["channel_id"] = 0
		GuildConfig.data.config[str(ctx.guild_id)]["server_status_message"]["message_id"] = 0
		await GuildConfig.save()
		logger.error(traceback.format_exc())
		await ctx.send_followup(embed=embeds.Notification.internal_error())

@client.slash_command()
@discord.default_permissions(send_messages=True)
async def ping(ctx: discord.ApplicationContext) -> None:
	try:
		raw_ping = client.latency
		ping = round(raw_ping * 1000)
		ping_embed = discord.Embed(title="Pong!",description=f"Latency: **`{ping}`** ms",color=discord.Colour.from_rgb(79,168,254))
		await ctx.respond(embed=ping_embed)
	except Exception:
		logger.error(traceback.format_exc())
		await ctx.send_followup(embed=embeds.Notification.internal_error())

@client.slash_command()
@discord.default_permissions(send_messages=True)
async def about(ctx: discord.ApplicationContext) -> None:
	try:
		embed = discord.Embed(color=discord.Colour.blue())
		embed.set_author(name=app.NAME, icon_url=client.user.display_avatar.url)
		embed.set_footer(text="Developed by Milkeyyy")
		embed.add_field(name="Version", value="`" + app.VERSION + "`")
		embed.add_field(name="Library", value=f"Pycord: `{discord.__version__}`")

		await ctx.respond(embed=embed)
	except Exception:
		logger.error(traceback.format_exc())
		await ctx.send_followup(embed=embeds.Notification.internal_error())

@client.slash_command()
@discord.guild_only()
async def test_notification(ctx: discord.ApplicationContext, comparison_target: str) -> None:
	try:
		if await client.is_owner(ctx.user):
			await ctx.defer(ephemeral=True)

			raw_status = json.loads(comparison_target)["data"]
			status_list = []
			for _platform, _status in raw_status.items():
				status_list.append(r6sss.functions.Status(r6sss.types.Platform[_platform], _status))

			# 比較を実行
			if ServerStatusManager.data is None:
				raise Exception("ServerStatusManager.data is None")
			compare_result = r6sss.compare_server_status(ServerStatusManager.data, status_list)

			# 通知メッセージを送信
			for result in compare_result:
				await ctx.respond(
					content=f"Test notification message\nType: `{result.detail}`",
					embed=embeds.Notification.get_by_comparison_result(result, "ja")
				)
		else:
			await ctx.respond(content=_("CmdMsg_DontHavePermission_Execution"), ephemeral=True)
	except Exception:
		logger.error(traceback.format_exc())
		await ctx.send_followup(embed=embeds.Notification.internal_error())

@client.slash_command()
@discord.guild_only()
async def synccommands(ctx: discord.ApplicationContext) -> None:
	try:
		if await client.is_owner(ctx.user):
			await ctx.defer(ephemeral=True)
			i18n.localize_commands()
			await client.sync_commands()
			await ctx.send_followup(content="コマンドを同期しました。")
		else:
			await ctx.respond(content=_("CmdMsg_DontHavePermission_Execution"), ephemeral=True)
	except Exception:
		logger.error(traceback.format_exc())
		await ctx.send_followup(embed=embeds.Notification.internal_error(), ephemeral=True)


# ログイン
try:
	# .envファイルが存在する場合はファイルから環境変数を読み込む
	env_path = os.path.join(os.getcwd(), ".env")
	if os.path.isfile(env_path):
		try:
			load_dotenv(env_path)
		except NameError:
			pass

	# 言語データを読み込む
	#localizations.load_localedata()

	# ログイン
	client.run(os.getenv("CLIENT_TOKEN"))
except Exception as e:
	logger.error(traceback.format_exc())
	exit(1)
