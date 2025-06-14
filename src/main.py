import argparse
import json
import sys
import traceback
from os import getenv
from pathlib import Path

import discord
from discord.commands import Option
from discord.ext import commands

try:
	from dotenv import load_dotenv
except ImportError:
	pass
import r6sss
from pycord.i18n import _

import embeds
from app import App
from client import client
from config import GuildConfigManager
from db import DBManager
from debug_logger import DebugLogger
from localizations import Localization
from logger import logger
from maintenance_schedule import MaintenanceScheduleManager
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
	# Cogs の読み込み
	client.load_extensions("cogs.commands.settings", "cogs.tasks.server_status_embed")
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
	logger.info(f" {App.NAME} - Version {App.VERSION_STRING}")
	logger.info(f" using Pycord {discord.__version__}")
	logger.info(f" Developed by {App.DEVELOPER_NAME}")
	logger.info(f" {App.COPYRIGHT}")
	logger.info("---------------------------------------")
	logger.info("")

	# ステータス表示を更新
	await client.change_presence(
		activity=discord.Game(name=f"Type /create | v{App.VERSION_STRING}"),
	)
	logger.info(
		"%s へログインしました！ (ID: %s)",
		client.user.display_name,
		str(client.user.id),
	)

	# 内部エラー報告機能の初期化
	try:
		logger.info("デバッグ用サーバー/チャンネル取得")
		debug_gd_id = getenv("DEBUG_GUILD_ID", "")
		debug_ch_id = getenv("DEBUG_TEXT_CHANNEL_ID", "")
		DebugLogger.debug_guild = client.get_guild(int(debug_gd_id))
		DebugLogger.debug_channel = await DebugLogger.debug_guild.fetch_channel(debug_ch_id)
		if DebugLogger.debug_guild:
			logger.info("- サーバー: %s (ID: %d)", DebugLogger.debug_guild.name, DebugLogger.debug_guild.id)
		else:
			logger.warning("- サーバーが見つかりません: %s", debug_gd_id)
		if DebugLogger.debug_channel:
			logger.info("- チャンネル: %s (ID: %d)", DebugLogger.debug_channel.name, DebugLogger.debug_channel.id)
		else:
			logger.warning("- チャンネルが見つかりません: %s", debug_ch_id)
	except Exception:
		logger.error("内部エラー報告機能の初期化に失敗")
		logger.error(traceback.format_exc())

	# データベースへ接続する
	await DBManager.connect()

	# ギルドデータのチェックを実行
	await GuildConfigManager.load()


# サーバー参加時のイベント
@client.event
async def on_guild_join(guild: discord.Guild) -> None:
	logger.info("ギルド参加: %s (%d)", guild.name, guild.id)
	await DebugLogger.log(f"ギルド参加\n- ギルド: `{guild.name}`\n- ID: `{guild.id}`")
	# 参加したギルドのコンフィグを作成する
	await GuildConfigManager.create(guild.id)


# サーバー脱退時のイベント
@client.event
async def on_guild_remove(guild: discord.Guild) -> None:
	logger.info("ギルド脱退: %s (%d)", guild.name, guild.id)
	await DebugLogger.log(f"ギルド脱退\n- ギルド: `{guild.name}`\n- ID: `{guild.id}`")
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
		if gc is None:
			await ctx.send_followup(
				embed=embeds.Notification.internal_error(
					description=_("CmdMsg_FailedToGetConfig"),
					error_code=await DebugLogger.report_internal_error("FailedToGetGuildConfig"),
				),
			)
			return

		# サーバーステータスを取得する
		status_data = ServerStatusManager.data
		# 取得できなかった場合 (None) はエラーメッセージを返す
		if status_data is None:
			await ctx.send_followup(
				embed=embeds.Notification.internal_error(
					description=_("CmdMsg_FailedToGetServerStatus"),
					error_code=await DebugLogger.report_internal_error("FailedToGetServerStatus"),
				),
			)
			return

		# 埋め込みメッセージを生成して送信する
		await ctx.send_followup(
			embeds=await embeds.ServerStatus.generate_embed(gc.server_status_message.language, status_data),
		)
	except Exception:
		logger.error(traceback.format_exc())
		await ctx.send_followup(
			embed=embeds.Notification.internal_error(error_code=await DebugLogger.report_internal_error(traceback.format_exc()))
		)


@client.slash_command()
@discord.guild_only()
@discord.default_permissions(send_messages=True)
@commands.cooldown(2, 5)
async def schedule(ctx: discord.ApplicationContext) -> None:
	await ctx.defer(ephemeral=False)
	try:
		# ギルドコンフィグを取得する
		gc = await GuildConfigManager.get(ctx.guild.id)
		if gc is None:
			await ctx.send_followup(
				embed=embeds.Notification.internal_error(
					description=_("CmdMsg_FailedToGetConfig"),
				),
			)
			return

		# メンテナンススケジュールを取得する
		schedule_data = MaintenanceScheduleManager.data

		# 埋め込みメッセージを生成して送信する
		await ctx.send_followup(embeds=await embeds.MaintenanceSchedule.generate_embed(gc.server_status_message.language, schedule_data))
	except Exception:
		logger.error(traceback.format_exc())
		await ctx.send_followup(
			embed=embeds.Notification.internal_error(error_code=await DebugLogger.report_internal_error(traceback.format_exc()))
		)


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
		if gc is None:
			await ctx.send_followup(
				embed=embeds.Notification.internal_error(
					description=_("CmdMsg_FailedToGetConfig"),
					error_code=await DebugLogger.report_internal_error("FailedToGetGuildConfig"),
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
			if status_data is None:
				await ctx.send_followup(
					embed=embeds.Notification.internal_error(
						description=_("CmdMsg_FailedToGetServerStatus"),
						error_code=await DebugLogger.report_internal_error("FailedToGetServerStatus"),
					),
				)

			# サーバーステータス埋め込みメッセージ生成してを送信する (作成)
			try:
				msg = await ch.send(
					embeds=await embeds.ServerStatus.generate_embed(gc.server_status_message.language, status_data),
				)
			except discord.errors.Forbidden as e:
				logger.info("サーバーステータスメッセージ作成失敗 - %s", str(e))
				# Missing Access (テキストチャンネルを閲覧する権限なし)
				if e.code == 50001:
					await ctx.send_followup(
						embed=embeds.Notification.error(
							description=_(
								"Cmd_create_Error_MissingAccess",
								ch.mention,
							),
						),
					)
				# Missing Permission (メッセージを送信する権限なし)
				elif e.code == 50013:
					await ctx.send_followup(
						embed=embeds.Notification.error(
							description=_(
								"CmdMsg_DontHavePermission_SendMessage",
								ch.mention,
							),
						),
					)
				# それ以外
				else:
					await ctx.send_followup(
						embed=embeds.Notification.internal_error(error_code=await DebugLogger.report_internal_error(traceback.format_exc()))
					)
				return

			# 送信したチャンネルとメッセージのIDをギルドデータへ保存する
			gc.server_status_message.channel_id = str(ch.id)
			gc.server_status_message.message_id = str(msg.id)
			# ギルドコンフィグを保存
			await GuildConfigManager.update(ctx.guild.id, gc)

		except Exception:
			logger.error(traceback.format_exc())
			await ctx.send_followup(
				embed=embeds.Notification.internal_error(error_code=await DebugLogger.report_internal_error(traceback.format_exc()))
			)
			return
		else:
			logger.info("サーバーステータスメッセージ新規作成: ギルド: %s | チャンネル: %s", ctx.guild.name, ch.name)
			await DebugLogger.log(f"サーバーステータスメッセージ新規作成\n- ギルド: `{ctx.guild.name}`\n- チャンネル: `{ch.name}`")
			# 作成成功メッセージを送信する
			await ctx.send_followup(
				embed=embeds.Notification.success(
					description=_("Cmd_create_Success", ch.mention) + additional_msg,
				),
			)
	except Exception:
		# 設定をリセット
		if gc is not None:
			gc.server_status_message.channel_id = "0"
			gc.server_status_message.message_id = "0"
			await GuildConfigManager.update(ctx.guild.id, gc)
		logger.error(traceback.format_exc())
		await ctx.send_followup(
			embed=embeds.Notification.internal_error(error_code=await DebugLogger.report_internal_error(traceback.format_exc()))
		)


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
		await ctx.send_followup(
			embed=embeds.Notification.internal_error(error_code=await DebugLogger.report_internal_error(traceback.format_exc()))
		)


@client.slash_command()
@discord.default_permissions(send_messages=True)
@commands.cooldown(2, 5)
async def about(ctx: discord.ApplicationContext) -> None:
	try:
		embed = discord.Embed(color=discord.Colour.blue())
		embed.set_author(name=App.NAME, icon_url=client.user.display_avatar.url)
		embed.set_footer(text=App.COPYRIGHT)
		embed.add_field(
			name="Version",
			value=f"`{App.VERSION_STRING}` ([`{App.get_git_commit_hash()[0:7]}`]\
({App.GITHUB_REPO_URL}/commit/{App.get_git_commit_hash()}))",
		)
		embed.add_field(
			name="Source",
			value=f"[GitHub]({App.GITHUB_REPO_URL})",
			inline=False,
		)
		embed.add_field(
			name="Developer",
			value=f"- {App.DEVELOPER_NAME}\n\
  - [Website]({App.DEVELOPER_WEBSITE_URL})\n\
  - [Twitter]({App.DEVELOPER_TWITTER_URL})",
			inline=True,
		)
		embed.add_field(
			name="Other Services",
			value=f"- [Bluesky Bot]({App.BLUESKY_BOT_URL})\n- [Twitter Bot]({App.TWITTER_BOT_URL})",
			inline=True,
		)
		await ctx.respond(embed=embed)
	except Exception:
		logger.error(traceback.format_exc())
		await ctx.send_followup(
			embed=embeds.Notification.internal_error(error_code=await DebugLogger.report_internal_error(traceback.format_exc()))
		)


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

			status_data = ServerStatusManager.data
			schedule_data = MaintenanceScheduleManager.data

			# サーバーステータスが None の場合はエラーメッセージを返す
			if status_data is None:
				logger.error("ServerStatusManager.data is None")
				await ctx.respond(
					embed=embeds.Notification.error(
						description=_("CmdMsg_FailedToGetServerStatus"),
					),
				)
				return

			# 比較を実行
			compare_result = r6sss.compare_server_status(
				status_data,
				status_list,
				schedule_data,
			)

			# 通知メッセージを送信
			await ctx.respond(f"テスト通知 ({len(compare_result)})")
			for result in compare_result:
				await ctx.channel.send(
					content=f"Test notification message\nType: `{result.detail}`",
					embed=embeds.Notification.get_by_comparison_result(result, "ja", schedule_data),
				)
		else:
			await ctx.respond(
				embed=embeds.Notification.error(
					description=_("CmdMsg_DontHavePermission_Execution"),
				),
			)
	except Exception:
		logger.error(traceback.format_exc())
		await ctx.send_followup(
			embed=embeds.Notification.internal_error(error_code=await DebugLogger.report_internal_error(traceback.format_exc()))
		)


# ログイン
try:
	# .envファイルが存在する場合はファイルから環境変数を読み込む
	env_path = Path(Path.cwd()) / ".env"
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
