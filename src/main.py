import datetime
import os
import traceback

import discord
from discord.commands import Option
from discord.ext import tasks
try:
	from dotenv import load_dotenv
except ImportError:
	pass
from pycord.i18n import _

# ロガー
from logger import logger

# Discordのクライアント
import client as app
from client import client

# コンフィグ
from config import GuildConfig

# Cronitor
import heartbeat

# スケジュール
import maintenance_schedule

# サーバーステータス
import serverstatus

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
	#await client.sync_commands()

	# ハートビートのキーを読み込み
	heartbeat.load_keys()

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
async def on_application_command_error(ctx: discord.ApplicationContext) -> None:
	pass


# 1分毎にサーバーステータスを更新する
serverstatus_loop_isrunning = False

@tasks.loop(seconds=120.0)
async def update_serverstatus() -> None:
	global serverstatus_loop_isrunning
	serverstatus_loop_isrunning = True

	# ハートビートを送信
	heartbeat.heartbeat.ping(state="complete")

	# Heartbeatイベントを送信 (サーバーステータスの更新が開始されたことを報告)
	heartbeat.monitor.ping(state="run", message="サーバーステータスの更新開始")

	logger.info("サーバーステータスの更新開始")

	try:
		await GuildConfig.save()

		# メンテナンススケジュール情報を取得
		sched = await maintenance_schedule.get()

		# サーバーステータスを取得する
		status = await serverstatus.get()
		if status is None:
			return

		# サーバーステータスを更新する
		serverstatus.data = status

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
								await msg.channel.edit(name=serverstatus.indicator + ch_name)
						except Exception as e:
							logger.error(traceback.format_exc())
							logger.error("ギルド %s のステータスインジケーターの更新に失敗: %s", guild.name, str(e))

						try:
							# 埋め込みメッセージを生成
							embeds = await generate_serverstatus_embed(lang, sched)
						except Exception as e:
							embeds = None
							logger.error(traceback.format_exc())
							logger.error("サーバーステータスメッセージの生成に失敗: %s", str(e))

						try:
							# サーバーステータスメッセージを編集
							if embeds is not None:
								await msg.edit(embeds=embeds)
						except Exception as e:
							logger.error(traceback.format_exc())
							logger.error("サーバーステータスメッセージの生成に失敗: %s", str(e))

						try:
							# TODO: ここにサーバーステータスが変更されたかチェックするコードを書く

							# 通知メッセージを送信
							notif_ch = guild.get_channel(notif_ch_id)
							notif_role = guild.get_role(notif_role_id)

							if notif_role is not None and notif_role.mentionable:
								notif_role_mention = notif_role.mention
							else:
								notif_role_mention = ""

							if notif_ch is not None:
								embed: discord.Embed = embeds[0]
								embed.description = f"{embed.description}\n[**🌐{localizations.translate('Notification_Show_Server_Status', lang)}**]({msg.jump_url})"
								await notif_ch.send(
									content=localizations.translate("Notification_Server_Status_Updated", lang) + "\n" + notif_role_mention,
									embed=embed
								)

						except Exception as e:
							logger.error(traceback.format_exc())
							logger.error("サーバーステータス通知メッセージの送信に失敗: %s", str(e))

			except Exception as e:
				logger.error("ギルド %s のサーバーステータスメッセージ(%s)の更新に失敗", guild.name, str(msg_id))
				logger.error(traceback.format_exc())

	except Exception as e:
		logger.error(traceback.format_exc())
		heartbeat.monitor.ping(state="fail", message="サーバーステータスの更新エラー: " + str(e))

	logger.info("サーバーステータスの更新完了")

	# Cronitorのモニターに成功したことを報告
	heartbeat.monitor.ping(state="complete", message="サーバーステータスの更新完了")

@update_serverstatus.after_loop
async def after_updateserverstatus() -> None:
	global serverstatus_loop_isrunning

	serverstatus_loop_isrunning = False
	logger.info("サーバーステータスの定期更新終了")
	if not serverstatus_loop_isrunning:
		update_serverstatus.start()

# サーバーステータス埋め込みメッセージを更新
async def generate_serverstatus_embed(locale, sched) -> list[discord.Embed]:
	pf_list = {
		"PC": ["PC", "PC", 2],
		"PS4": ["PS4", "PS4", 0],
		"PS5": ["PS5", "PS5", 1],
		"XB1": ["XBOXONE", "XB1", 0],
		"XBSX": ["XBOX SERIES X", "XBSX/S", 1]
	}

	# 各プラットフォームの埋め込みメッセージの色
	color_list = {
		"PC": discord.Colour.from_rgb(255, 255, 255),
		"PS4": discord.Colour.from_rgb(0, 67, 156),
		"PS5": discord.Colour.from_rgb(0, 67, 156),
		"XB1": discord.Colour.from_rgb(16, 124, 16),
		"XBSX": discord.Colour.from_rgb(16, 124, 16)
	}

	embeds = []

	# サーバーステータスを取得
	status = serverstatus.data

	# 各プラットフォームごとの埋め込みメッセージを作成
	embed = discord.Embed(color=color_list["PC"])
	embed.title = "📶 R6S Server Status"
	embed.description = "🕒 " + localizations.translate("Last Update", locale) + ": " + f"<t:{serverstatus.updated_at}:f> (<t:{serverstatus.updated_at}:R>)"
	embed.set_footer(text="⚠️\n" + localizations.translate("NotAffiliatedWithOrRndorsedBy", locale))

	for _, v in pf_list.items():
		status_list = []

		pf_id = v[0] # PC, PS4, XB1...
		pf_display_name = v[1] # プラットフォームの表示名

		if pf_id.startswith("_"):
			continue

		# サーバーの状態によってアイコンを変更する
		# 問題なし
		if status[pf_id]["Status"]["Connectivity"] == "Operational":
			status_icon = status_icon_set.OPERATIONAL
		# 計画メンテナンス
		elif status[pf_id]["Status"]["Connectivity"] == "Maintenance":
			status_icon = status_icon_set.MAINTENANCE
		# 想定外の問題
		elif status[pf_id]["Status"]["Connectivity"] == "Interrupted":
			status_icon = status_icon_set.INTERRUPTED
		# 想定外の停止
		elif status[pf_id]["Status"]["Connectivity"] == "Degraded":
			status_icon = status_icon_set.DEGRADED
		# それ以外
		else:
			status_icon = status_icon_set.UNKNOWN

		connectivity_text = localizations.translate(status[pf_id]["Status"]["Connectivity"], locale)

		mt_text = ""
		if status[pf_id]["Status"]["Maintenance"]:
			status_icon = status_icon_set.MAINTENANCE
			connectivity_text = localizations.translate("Maintenance", locale)

		f_list = []
		f_text = ""
		f_status_text = ""
		# 各サービスをループしてステータスに合わせてアイコンとテキストを設定
		for f, s in status[pf_id]["Status"]["Features"].items():
			# 通常
			f_status_icon = status_icon_set.OPERATIONAL
			f_status_text = localizations.translate(s, locale)
			# 停止
			if s != "Operational":
				f_status_icon = status_icon_set.DEGRADED
			# メンテナンス
			if status[pf_id]["Status"]["Maintenance"]:
				f_status_icon = status_icon_set.MAINTENANCE
			# 不明
			if s == "Unknown":
				f_status_icon = status_icon_set.UNKNOWN
				f_status_text = localizations.translate("Unknown", locale)

			f_list.append("" + localizations.translate(f, locale) + "\n┗ " + f_status_icon + "`" + f_status_text + "`")

		f_text = "" + "\n".join(f_list)

		# 埋め込みメッセージにプラットフォームのフィールドを追加
		status_list.append(mt_text + f_text)

		# プラットフォームのステータスのフィールドを追加
		embed.add_field(
			name=platform_icon.LIST[v[0]] + " " + pf_display_name + " - " + status_icon + "**`" + connectivity_text + "`**",
			value="\n".join(status_list)
		)
		# 各プラットフォームごとに別の行にするために、リストで指定された数の空のフィールドを挿入する
		for _ in range(v[2]):
			embed.add_field(name="", value="")

	embeds.append(embed)

	create = True
	#dt = "**:calendar: " + localizations.translate("MaintenanceSchedule_ScheduledDT", locale) + "**\n"
	dt = ""
	# スケジュール埋め込みを生成
	if sched is not None:
		platform_list = [p["Name"] for p in sched["Platforms"]]
		# 全プラットフォーム同一
		if "All" in platform_list:
			# スケジュールが範囲内か判定
			if datetime.datetime.now().timestamp() >= (sched["Timestamp"] + (sched["Downtime"] * 60)):
				create = False
			# 予定日時一覧を生成
			dt = "・**" + localizations.translate('Platform_All', locale) + f"**: <t:{sched['Timestamp']}:f> (<t:{sched['Timestamp']}:R>)" + "\n"
		else: # プラットフォーム別
			# スケジュールが範囲内か判定
			if datetime.datetime.now().timestamp() >= (sched["Timestamp"] + (sched["Downtime"] * 60)):
				create = False
			else:
				for p in platform_list:
					# 予定日時一覧を生成
					dt = dt + "・**" + localizations.translate(f'Platform_{p}', locale) + f"**: <t:{sched['Timestamp']}:f> (<t:{sched['Timestamp']}:R>)" + "\n"

		if create:
			embed = discord.Embed(
				colour=discord.colour.Colour.nitro_pink(),
				title=":wrench::calendar: " + localizations.translate("MaintenanceSchedule", locale),
				description="**" + sched["Title"] + "**\n" + sched["Detail"],
				footer=discord.EmbedFooter("⚠️\n" + localizations.translate("MaintenanceSchedule_Notes", locale)),
				fields=[
					# ダウンタイム
					discord.EmbedField(
						name="**:clock3: " + localizations.translate("MaintenanceSchedule_Downtime", locale) + "**",
						value="・" + str(sched["Downtime"]) + " " + localizations.translate("MaintenanceSchedule_Downtime_Minute", locale)
					),
					# 各プラットフォームの予定日時
					discord.EmbedField(
						name="**:video_game: " + localizations.translate("MaintenanceSchedule_TargetPlatform", locale) + "**",
						value=dt
					)
				]
			)
		else: # 予定されているメンテナンスがない場合
			embed = discord.Embed(
				colour=discord.colour.Colour.nitro_pink(),
				title=":wrench::calendar: " + localizations.translate("MaintenanceSchedule", locale),
				description=localizations.translate("MaintenanceSchedule_NoMaintenanceScheduled", locale),
				footer=discord.EmbedFooter("⚠️\n" + localizations.translate("MaintenanceSchedule_Notes", locale))
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

		if locale in localizations.LOCALE_DATA.keys():
			#GuildConfig.data.config[str(ctx.guild.id)]["server_status_message"]["language"] = [k for k, v in localizations.LOCALE_DATA.keys() if v == locale][0]
			GuildConfig.data.config[str(ctx.guild.id)]["server_status_message"]["language"] = locale
		else:
			GuildConfig.data.config[str(ctx.guild.id)]["server_status_message"]["language"] = "en_GB"

		# ギルドデータを保存
		await GuildConfig.save()

		await ctx.send_followup(content=_("Cmd_setlanguage_Success", GuildConfig.data.config[str(ctx.guild.id)]["server_status_message"]["language"]))
	except Exception as e:
		logger.error(traceback.format_exc())
		await ctx.send_followup(content=_("An error occurred when running the command") + ": `" + str(e) + "`")

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

		await ctx.send_followup(content=_("Cmd_setindicator_Success", str(enable)))
	except Exception as e:
		logger.error(traceback.format_exc())
		await ctx.send_followup(content=_("An error occurred when running the command") + ": `" + str(e) + "`")

@client.slash_command()
@discord.guild_only()
@discord.default_permissions(send_messages=True)
async def status(ctx: discord.ApplicationContext) -> None:
	await ctx.defer(ephemeral=False)
	try:
		sched = await maintenance_schedule.get()
		await ctx.send_followup(embeds=await generate_serverstatus_embed(GuildConfig.data.config[str(ctx.guild_id)]["server_status_message"]["language"], sched))
	except Exception as e:
		logger.error(traceback.format_exc())
		await ctx.send_followup(content=_("An error occurred when running the command") + ": `" + str(e) + "`")

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
			additional_msg = f"\n({_('Cmd_create_Old messages you previously sent will no longer be updated.')})"

		if channel is None:
			ch_id = ctx.channel_id
		else:
			ch_id = channel.id
		ch = client.get_channel(ch_id)

		# サーバーステータス埋め込みメッセージを送信
		try:
			sched = await maintenance_schedule.get()
			msg = await ch.send(embeds=await generate_serverstatus_embed(GuildConfig.data.config[str(ctx.guild_id)]["server_status_message"]["language"], sched))
		except Exception as e:
			if type(e) == discord.errors.ApplicationCommandInvokeError and str(e).endswith("Missing Permissions"):
				await ctx.send_followup(content=_("DontHavePermission_SendMessage", ch.mention))
			else:
				logger.error(traceback.format_exc())
				await ctx.send_followup(content=_("An error occurred when running the command") + ": `" + str(e) + "`")
			return

		# 送信したチャンネルとメッセージのIDをギルドデータへ保存する
		GuildConfig.data.config[str(ctx.guild_id)]["server_status_message"]["channel_id"] = ch_id
		GuildConfig.data.config[str(ctx.guild_id)]["server_status_message"]["message_id"] = msg.id

		# ギルドデータを保存
		await GuildConfig.save()

		await ctx.send_followup(content=_("Cmd_create_Success", ch.mention) + additional_msg)
	except Exception as e:
		logger.error(traceback.format_exc())
		await ctx.send_followup(content=_("An error occurred when running the command") + ": `" + str(e) + "`")

@client.slash_command()
@discord.default_permissions(send_messages=True)
async def ping(ctx: discord.ApplicationContext) -> None:
	try:
		raw_ping = client.latency
		ping = round(raw_ping * 1000)
		ping_embed = discord.Embed(title="Pong!",description=f"Latency: **`{ping}`** ms",color=discord.Colour.from_rgb(79,168,254))
		await ctx.respond(embed=ping_embed)
	except Exception as e:
		logger.error(traceback.format_exc())
		await ctx.respond(content=_("An error occurred when running the command") + ": `" + str(e) + "`")

@client.slash_command()
@discord.default_permissions(send_messages=True)
async def about(ctx: discord.ApplicationContext) -> None:
	try:
		embed = discord.Embed(color=discord.Colour.blue())
		embed.set_author(name=app.NAME, icon_url=client.user.display_avatar.url)
		embed.set_footer(text=f"Developed by Milkeyyy")
		embed.add_field(name="Version", value="`" + app.VERSION + "`")
		embed.add_field(name="Library", value=f"Pycord: `{discord.__version__}`")

		await ctx.respond(embed=embed)
	except Exception as e:
		logger.error(traceback.format_exc())
		await ctx.respond(content=_("An error occurred when running the command") + ": `" + str(e) + "`")

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
			await ctx.respond(content=_("Cmd_General_DontHavePermission"), ephemeral=True)
	except Exception as e:
		logger.error(traceback.format_exc())
		await ctx.respond(content=_("An error occurred when running the command") + ": `" + str(e) + "`", ephemeral=True)


# ログイン
try:
	# .envファイルが存在する場合はファイルから環境変数を読み込む
	env_path = os.path.join(os.getcwd(), ".env")
	if os.path.isfile(env_path):
		load_dotenv(env_path)

	# 言語データを読み込む
	#localizations.load_localedata()

	# ログイン
	client.run(os.getenv("CLIENT_TOKEN"))
except Exception as e:
	logger.error(traceback.format_exc())
