import argparse
import json
import sys
import traceback
from os import getenv
from pathlib import Path

import discord
import discord.types.guild
from discord.commands import Option
from discord.ext import commands, tasks

try:
	from dotenv import load_dotenv
except ImportError:
	pass
import discord.types
import r6sss
from pycord.i18n import _

# Discordのクライアント
import client as app

# 埋め込み
import embeds

# ローカライズ
import localizations

# アイコン
import status_indicator
from client import client

# コンフィグ/DB
from config import GuildConfigManager
from db import DBManager

# Uptime Kuma
from kumasan import KumaSan
from localizations import Localization

# ロガー
from logger import logger

# スケジュール
from maintenance_schedule import MaintenanceScheduleManager

# サーバーステータス
from server_status import ServerStatusManager

# コマンドライン引数
parser = argparse.ArgumentParser()
parser.add_argument("--dev", action="store_true")  # 開発モード
args = parser.parse_args()


# Bot接続時のイベント
@client.event
async def on_connect() -> None:
	# 言語データを読み込む
	Localization.load_locale_data()
	# Cog (コマンド) の読み込み
	client.load_extension("cogs.settings")
	# コマンドの同期とローカライズ
	if client.auto_sync_commands:
		logger.info("コマンドを同期")
		Localization.localize_commands()
		await client.sync_commands()
	logger.info("接続完了")


# Bot起動時のイベント
@client.event
async def on_ready() -> None:
	logger.info("---------------------------------------")
	logger.info(f" {app.NAME} - Version {app.VERSION}")
	logger.info(f" using Pycord {discord.__version__}")
	logger.info(f" Developed by {app.DEVELOPER_NAME}")
	logger.info(f" {app.COPYRIGHT}")
	logger.info("---------------------------------------")
	logger.info("")

	# ステータス表示を更新
	await client.change_presence(
		activity=discord.Game(name=f"Type /create | v{app.VERSION}"),
	)
	logger.info(
		"%s へログインしました！ (ID: %s)",
		client.user.display_name,
		str(client.user.id),
	)

	# データベースへ接続する
	await DBManager.connect()

	# ギルドデータのチェックを実行
	await GuildConfigManager.load()

	logger.info("サーバーステータスの定期更新開始")
	ServerStatusEmbedManager.update_server_status.start()


# サーバー参加時のイベント
@client.event
async def on_guild_join(guild: discord.Guild) -> None:
	logger.info("ギルド参加: %s (%d)", guild.name, guild.id)
	# 参加したギルドのコンフィグを作成する
	await GuildConfigManager.create(guild.id)


# サーバー脱退時のイベント
@client.event
async def on_guild_remove(guild: discord.Guild) -> None:
	logger.info("ギルド脱退: %s (%d)", guild.name, guild.id)
	# 脱退したギルドのコンフィグを削除する
	await GuildConfigManager.delete(guild.id)


# アプリケーションコマンド実行時のイベント
@client.event
async def on_application_command_completion(ctx: discord.ApplicationContext) -> None:
	full_command_name = ctx.command.qualified_name
	if ctx.guild is not None:
		logger.info(
			"アプリケーションコマンド実行 - %s | ギルド: %s (%d) | 実行者: %s (%s)",
			full_command_name,
			ctx.guild.name,
			ctx.guild.id,
			ctx.user,
			ctx.user.id,
		)
	else:
		logger.info(
			"アプリケーションコマンド実行 - %s | DM | 実行者: %s (%s)",
			full_command_name,
			ctx.user,
			ctx.user.id,
		)


# アプリケーションコマンドエラー時のイベント
@client.event
async def on_application_command_error(
	ctx: discord.ApplicationContext,
	ex: discord.DiscordException,
) -> None:
	logger.error("アプリケーションコマンド実行エラー")
	logger.error(ex)
	# クールダウン
	if str(ex).startswith("You are on cooldown"):
		await ctx.respond(
			embed=embeds.Notification.warning(description=_("CmdMsg_CooldownWarning")),
			ephemeral=True,
		)


class ServerStatusEmbedManager:
	def __init__(self) -> None:
		self.server_status_update_loop_is_running = False

	# 2分毎にサーバーステータスを更新する
	@tasks.loop(minutes=2)
	async def update_server_status(self) -> None:  # noqa: PLR0915
		self.server_status_update_loop_is_running = True

		# Heartbeatイベントを送信 (サーバーステータスの更新が開始されたことを報告)
		await KumaSan.ping(state="up", message="サーバーステータスの更新開始")

		logger.info("サーバーステータスの更新開始")

		try:
			# サーバーステータス情報を取得する
			status_data = await ServerStatusManager.get()
			# 取得できなかった場合は処理を行わずにエラーを出力する
			if status_data is None:
				logger.error("- 更新中止: status_data is None")
				await KumaSan.ping("pending", "サーバーステータスの更新中止: status_data is None")
				return

			# メンテナンススケジュール情報を取得する
			schedule_data = await MaintenanceScheduleManager.get()

			# 各ギルドの埋め込みメッセージIDチェック、存在する場合はメッセージを更新する
			for guild in client.guilds:
				logger.info("ギルド: %s", guild.name)
				try:
					# データベースからギルドコンフィグを取得する
					gc = await GuildConfigManager.get(guild.id)
					# 取得できなかった場合はスキップする
					if not gc:
						logger.warning("更新スキップ: ギルドデータ (%s) の取得失敗", guild.name)
						continue
					ch_id = int(gc.server_status_message.channel_id)
					msg_id = int(gc.server_status_message.message_id)
					notif_ch_id = int(gc.server_status_notification.channel_id)
					notif_role_id = int(gc.server_status_notification.role_id)
					lang = gc.server_status_message.language
				except Exception:
					logger.warning("更新スキップ: ギルドデータ (%s) の取得時エラー", guild.name)
					logger.error(traceback.format_exc())
					continue  # 更新をスキップ

				try:
					# テキストチャンネルとメッセージのID, 通知メッセージの送信先
					# 両方が設定されていない場合は処理をスキップする
					if (ch_id == 0 or msg_id == 0) and (notif_ch_id == 0):
						continue

					# IDからテキストチャンネルを取得する
					ch = guild.get_channel(ch_id)
					# チャンネルが存在しない場合はギルドデータのチャンネルIDとメッセージIDをリセットする
					if ch is None:
						logger.info("更新スキップ: テキストチャンネルの取得失敗")
						logger.info("- 設定リセット実行")
						gc.server_status_message.channel_id = "0"
						gc.server_status_message.message_id = "0"
						# ギルドコンフィグを保存
						await GuildConfigManager.update(guild.id, gc)
						continue  # 処理をスキップする

					ch_name = ch.name
					logger.info("- 更新実行: #%s", ch_name)

					e = ""
					try:
						# 取得したテキストチャンネルからメッセージを取得する
						msg = await ch.fetch_message(msg_id)
					except discord.errors.NotFound as err:
						logger.info(" - メッセージの取得失敗 (%s)", str(err))
						msg = None

					# 既存のサーバーステータスメッセージの取得に失敗した場合はコンフィグをリセットして処理をスキップする
					if msg is None:
						logger.info("- 更新中止: メッセージの取得失敗")
						logger.info("ギルド %s のメッセージ (ID: %s) の取得に失敗", guild.name, str(msg_id))
						# メッセージが存在しない(削除されている)場合はギルドデータのチャンネルIDとメッセージIDをリセットする
						gc.server_status_message.channel_id = "0"
						gc.server_status_message.message_id = "0"
						# ギルドデータを保存
						await GuildConfigManager.update(guild.id, gc)
						continue

					# ステータスインジケーターが有効かつインジケーターに変化があった場合は
					# 元の名前を保持して先頭にインジケーターを追加または置換する
					if all(
						(
							gc.server_status_message.status_indicator,  # ステータスインジケーターが有効
							ch_name[0] in status_indicator.List,  # チャンネル名の先頭がステータスインジケーターか
							ch_name[0] != ServerStatusManager.indicator,  # チャンネル名の先頭が現在のインジケーターと異なるか
						)
					):
						# インジケーター文字を除いたチャンネル名を取得する
						ch_name_min_count = 2
						ch_name = ch_name[1:] if len(ch_name) >= ch_name_min_count else ""
						try:
							await msg.channel.edit(
								name=ServerStatusManager.indicator + ch_name,
							)
						except Exception as e:
							logger.error(traceback.format_exc())
							logger.error("ギルド %s のステータスインジケーターの更新に失敗: %s", guild.name, str(e))

					try:
						# 埋め込みメッセージを生成
						server_status_embeds = await embeds.ServerStatus.generate(
							lang,
							status_data,
							schedule_data,
						)
					except Exception as e:
						server_status_embeds = None
						logger.error(traceback.format_exc())
						logger.error(
							"サーバーステータスメッセージの生成に失敗: %s",
							str(e),
						)

					try:
						# サーバーステータスメッセージを編集
						if server_status_embeds is not None:
							await msg.edit(embeds=server_status_embeds)
					except Exception as e:
						logger.error(traceback.format_exc())
						logger.error(
							"サーバーステータスメッセージの生成に失敗: %s",
							str(e),
						)

					try:
						if ServerStatusManager.previous_data:
							notif_embeds = []

							# if client.user is not None:
							# 	embed_author = discord.EmbedAuthor(
							# 		client.user.display_name,
							# 		icon_url=client.user.display_avatar.url,
							# 	)
							# else:
							# 	embed_author = None

							# サーバーステータスの比較を行う
							compare_result = r6sss.compare_server_status(ServerStatusManager.previous_data, status_data)

							# ステータスの比較結果一覧から通知用の埋め込みメッセージを生成する
							notif_embeds = [embeds.Notification.get_by_comparison_result(result, lang) for result in compare_result]
							# for result in compare_result:
							# 	# 対象プラットフォームの一覧テキストを生成
							# 	# 全プラットフォームの場合は専用のテキストにする
							# 	if {p.platform for p in ServerStatusManager.data}.issubset(set(result.platforms)):
							# 		target_platforms_text = localizations.translate("Platform_All", lang=lang)
							# 	else:
							# 		target_platforms_text = " | ".join(
							# 			[platform_icon.LIST[p.value] + " " + p.name for p in result.platforms]
							# 		)

							# 	if result.detail == r6sss.ComparisonDetail.START_MAINTENANCE:
							# 		# メンテナンス開始
							# 		logger.info("通知送信: メンテナンス開始")
							# 		notif_embeds.append(
							# 			discord.Embed(
							# 				color=discord.Colour.light_grey(),
							# 				title=localizations.translate("Title_Maintenance_Start", lang=lang),
							# 				description="**"
							# 				+ localizations.translate("TargetPlatform", lang=lang)
							# 				+ ": "
							# 				+ target_platforms_text
							# 				+ "**",
							# 				author=embed_author,
							# 			)
							# 		)

							# 通知メッセージを送信するチャンネルを取得
							notif_ch = guild.get_channel(notif_ch_id)
							notif_role = guild.get_role(notif_role_id)

							# メンションするロールが設定済みかつメンションが可能な場合はメンション用のテキストを設定
							notif_role_mention = (notif_role.mention if notif_role.mentionable else "") if notif_role is not None else ""

							# 通知メッセージを送信
							if notif_ch is not None and notif_embeds is not None:
								for notif_embed in notif_embeds:
									if notif_embed is not None:
										notif_embed.description = f"\
[**💬 {localizations.translate('Notification_Show_Server_Status', lang=lang)}**]\
({msg.jump_url})\n{notif_embed.description}"
								if notif_embeds:
									# 自動削除が有効の場合は削除までの時間を指定する
									notif_delete_after_seconds = int(
										gc.server_status_notification.auto_delete,
									)
									if notif_delete_after_seconds > 0:
										await notif_ch.send(
											content=localizations.translate(
												"Notification_Server_Status_Updated",
												lang=lang,
											)
											+ "\n"
											+ notif_role_mention,
											embeds=notif_embeds,
											delete_after=notif_delete_after_seconds,
										)
									# 自動削除が無効の場合は削除までの時間を指定しない
									else:
										await notif_ch.send(
											content=localizations.translate(
												"Notification_Server_Status_Updated",
												lang=lang,
											)
											+ "\n"
											+ notif_role_mention,
											embeds=notif_embeds,
										)

					except Exception as e:
						logger.error(traceback.format_exc())
						logger.error(
							"サーバーステータス通知メッセージの送信に失敗: %s",
							str(e),
						)

				except Exception:
					logger.error(
						"ギルド %s のサーバーステータスメッセージ(%s)の更新に失敗",
						guild.name,
						str(msg_id),
					)
					logger.error(traceback.format_exc())

		except Exception as e:
			logger.error(traceback.format_exc())
			await KumaSan.ping(
				state="pending",
				message="サーバーステータスの更新エラー: " + str(e),
			)

		logger.info("サーバーステータスの更新完了")

		await KumaSan.ping(state="up", message="サーバーステータスの更新完了")

	@update_server_status.after_loop
	async def after_update_server_status(self) -> None:
		self.server_status_update_loop_is_running = False
		logger.info("サーバーステータスの定期更新終了")
		if not self.server_status_update_loop_is_running:
			self.update_server_status.start()


# コマンド
@client.slash_command()
@discord.guild_only()
@discord.default_permissions(send_messages=True)
@commands.cooldown(2, 5)
async def status(ctx: discord.ApplicationContext) -> None:
	await ctx.defer(ephemeral=False)
	try:
		# ギルドコンフィグを取得する
		gc = await GuildConfigManager.get(ctx.guild.id)
		if not gc:
			await ctx.send_followup(
				embed=embeds.Notification.internal_error(
					description=_("CmdMsg_FailedToGetConfig"),
				),
			)
			return

		# サーバーステータスを取得する
		status_data = ServerStatusManager.data
		# 取得できなかった場合 (None) はエラーメッセージを返す
		if not status_data:
			await ctx.send_followup(
				embed=embeds.Notification.internal_error(
					description=_("CmdMsg_FailedToGetServerStatus"),
				),
			)

		# メンテナンススケジュールを取得する
		schedule_data = MaintenanceScheduleManager.schedule
		# 取得できなかった場合 (None) はエラーメッセージを返す
		if not schedule_data:
			await ctx.send_followup(
				embed=embeds.Notification.internal_error(
					description=_("CmdMsg_FailedToGetMaintenanceSchedule"),
				),
			)

		# 埋め込みメッセージを生成して送信する
		await ctx.send_followup(
			embeds=await embeds.ServerStatus.generate(
				gc.server_status_message.language,
				status_data,
				schedule_data,
			),
		)
	except Exception:
		logger.error(traceback.format_exc())
		await ctx.send_followup(embed=embeds.Notification.internal_error())


@client.slash_command()
@discord.guild_only()
@discord.default_permissions(administrator=True)
@commands.cooldown(2, 5)
async def create(
	ctx: discord.ApplicationContext,
	channel: Option(discord.TextChannel, required=False),  # pyright: ignore[reportInvalidTypeForm]
) -> None:
	await ctx.defer(ephemeral=True)

	gc = None
	try:
		# ギルドコンフィグを取得する
		gc = await GuildConfigManager.get(ctx.guild.id)
		if not gc:
			await ctx.send_followup(
				embed=embeds.Notification.internal_error(
					description=_("CmdMsg_FailedToGetConfig"),
				),
			)
			return

		additional_msg = ""
		if gc.server_status_message.message_id != "0":
			additional_msg = f"\n({_('Cmd_create_OldMessagesWillNoLongerBeUpdated')})"

		# テキストチャンネルのID
		ch_id = channel.id if channel else ctx.channel_id
		# IDからテキストチャンネルを取得する
		ch = ctx.guild.get_channel(ch_id)

		try:
			# サーバーステータスを取得する
			status_data = ServerStatusManager.data
			# 取得できなかった場合 (None) はエラーメッセージを返す
			if not status_data:
				await ctx.send_followup(
					embed=embeds.Notification.internal_error(
						description=_("CmdMsg_FailedToGetServerStatus"),
					),
				)

			# メンテナンススケジュールを取得する
			schedule_data = MaintenanceScheduleManager.schedule
			# 取得できなかった場合 (None) はエラーメッセージを返す
			if not schedule_data:
				await ctx.send_followup(
					embed=embeds.Notification.internal_error(
						description=_("CmdMsg_FailedToGetMaintenanceSchedule"),
					),
				)

			# サーバーステータス埋め込みメッセージ生成してを送信する (作成)
			msg = await ch.send(
				embeds=await embeds.ServerStatus.generate(
					gc.server_status_message.language,
					status_data,
					schedule_data,
				),
			)

			# 送信したチャンネルとメッセージのIDをギルドデータへ保存する
			gc.server_status_message.channel_id = str(ch.id)
			gc.server_status_message.message_id = str(msg.id)
			# ギルドコンフィグを保存
			await GuildConfigManager.update(ctx.guild.id, gc)
		except Exception as e:
			# 権限エラー
			if isinstance(e, discord.errors.ApplicationCommandInvokeError) and str(
				e,
			).endswith("Missing Permissions"):
				await ctx.send_followup(
					embed=embeds.Notification.error(
						description=_(
							"CmdMsg_DontHavePermission_SendMessage",
							ch.mention,
						),
					),
				)
			# それ以外のエラー
			else:
				logger.error(traceback.format_exc())
				await ctx.send_followup(embed=embeds.Notification.internal_error())
			return

		await ctx.send_followup(
			embed=embeds.Notification.success(
				description=_("Cmd_create_Success", ch.mention) + additional_msg,
			),
		)
	except Exception:
		# 設定をリセット
		if gc:
			gc.server_status_message.channel_id = "0"
			gc.server_status_message.message_id = "0"
			await GuildConfigManager.update(ctx.guild.id, gc)
		logger.error(traceback.format_exc())
		await ctx.send_followup(embed=embeds.Notification.internal_error())


@client.slash_command()
@discord.default_permissions(send_messages=True)
@commands.cooldown(2, 5)
async def ping(ctx: discord.ApplicationContext) -> None:
	try:
		raw_ping = client.latency
		ping = round(raw_ping * 1000)
		ping_embed = discord.Embed(
			title="Pong!",
			description=f"Latency: **`{ping}`** ms",
			color=discord.Colour.from_rgb(79, 168, 254),
		)
		await ctx.respond(embed=ping_embed)
	except Exception:
		logger.error(traceback.format_exc())
		await ctx.send_followup(embed=embeds.Notification.internal_error())


@client.slash_command()
@discord.default_permissions(send_messages=True)
@commands.cooldown(2, 5)
async def about(ctx: discord.ApplicationContext) -> None:
	try:
		embed = discord.Embed(color=discord.Colour.blue())
		embed.set_author(name=app.NAME, icon_url=client.user.display_avatar.url)
		embed.set_footer(text=app.COPYRIGHT)
		embed.add_field(
			name="Version",
			value=f"`{app.VERSION}` ([`{app.get_git_commit_hash()[0:7]}`]({app.GITHUB_REPO_URL}/commit/{app.get_git_commit_hash()}))",
		)
		embed.add_field(
			name="Source",
			value=f"[GitHub]({app.GITHUB_REPO_URL})",
			inline=False,
		)
		embed.add_field(
			name="Developer",
			value=f"- {app.DEVELOPER_NAME}\n\
  - [Website]({app.DEVELOPER_WEBSITE_URL})\n\
  - [Twitter]({app.DEVELOPER_TWITTER_URL})",
			inline=True,
		)
		embed.add_field(
			name="Other Services",
			value=f"- [Bluesky Bot]({app.BLUESKY_BOT_URL})\n- [Twitter Bot]({app.TWITTER_BOT_URL})",
			inline=True,
		)
		await ctx.respond(embed=embed)
	except Exception:
		logger.error(traceback.format_exc())
		await ctx.send_followup(embed=embeds.Notification.internal_error())


@client.slash_command()
@discord.guild_only()
@discord.default_permissions(administrator=True)
@commands.cooldown(2, 5)
async def testnotification(
	ctx: discord.ApplicationContext,
	comparison_target: str,
) -> None:
	try:
		if await client.is_owner(ctx.user):
			await ctx.defer(ephemeral=True)

			raw_status = json.loads(comparison_target)["data"]
			status_list = []
			for _platform, _status in raw_status.items():
				status_list.append(
					r6sss.functions.Status(r6sss.types.Platform[_platform], _status),
				)

			# サーバーステータスが None の場合はエラーメッセージを返す
			if ServerStatusManager.data is None:
				logger.error("ServerStatusManager.data is None")
				await ctx.respond(
					embed=embeds.Notification.error(
						description=_("CmdMsg_FailedToGetServerStatus"),
					),
				)

			# 比較を実行
			compare_result = r6sss.compare_server_status(
				ServerStatusManager.data,
				status_list,
			)

			# 通知メッセージを送信
			await ctx.respond(f"テスト通知 ({len(compare_result)})")
			for result in compare_result:
				await ctx.channel.send(
					content=f"Test notification message\nType: `{result.detail}`",
					embed=embeds.Notification.get_by_comparison_result(result, "ja"),
				)
		else:
			await ctx.respond(
				embed=embeds.Notification.error(
					description=_("CmdMsg_DontHavePermission_Execution"),
				),
			)
	except Exception:
		logger.error(traceback.format_exc())
		await ctx.send_followup(embed=embeds.Notification.internal_error())


@client.slash_command()
@discord.guild_only()
@discord.default_permissions(administrator=True)
@commands.cooldown(2, 5)
async def synccommands(ctx: discord.ApplicationContext) -> None:
	try:
		if await client.is_owner(ctx.user):
			await ctx.defer(ephemeral=True)
			Localization.localize_commands()
			await client.sync_commands()
			await ctx.send_followup(content="コマンドを同期しました。")
		else:
			await ctx.respond(
				embed=embeds.Notification.error(
					description=_("CmdMsg_DontHavePermission_Execution"),
				),
			)
	except Exception:
		logger.error(traceback.format_exc())
		await ctx.send_followup(
			embed=embeds.Notification.internal_error(),
			ephemeral=True,
		)


# ログイン
try:
	# .envファイルが存在する場合はファイルから環境変数を読み込む
	env_path = Path.joinpath(Path.cwd(), ".env")
	if Path.is_file(env_path):
		try:
			load_dotenv(env_path)
		except NameError:
			pass

	# ログイン
	client.run(getenv("CLIENT_TOKEN"))
except Exception:
	logger.error(traceback.format_exc())
	sys.exit(1)
