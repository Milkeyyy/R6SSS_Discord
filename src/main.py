import argparse
import json
import sys
import traceback
from os import getenv
from pathlib import Path

import discord
import discord.types.guild
from discord.commands import Option
from discord.ext import commands

try:
	from dotenv import load_dotenv
except ImportError:
	pass
import discord.types
import r6sss
from pycord.i18n import _

import client as app
import embeds
from client import client
from config import GuildConfigManager
from db import DBManager
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
	logger.info(f" {app.NAME} - Version {app.VERSION_STRING}")
	logger.info(f" using Pycord {discord.__version__}")
	logger.info(f" Developed by {app.DEVELOPER_NAME}")
	logger.info(f" {app.COPYRIGHT}")
	logger.info("---------------------------------------")
	logger.info("")

	# ステータス表示を更新
	await client.change_presence(
		activity=discord.Game(name=f"Type /create | v{app.VERSION_STRING}"),
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
				),
			)
			return

		# サーバーステータスを取得する
		status_data = await ServerStatusManager.get()
		# 取得できなかった場合 (None) はエラーメッセージを返す
		if status_data is None:
			await ctx.send_followup(
				embed=embeds.Notification.internal_error(
					description=_("CmdMsg_FailedToGetServerStatus"),
				),
			)
			return

		# メンテナンススケジュールを取得する
		schedule_data = MaintenanceScheduleManager.schedule

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
		if gc is None:
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
			status_data = await ServerStatusManager.get()
			# 取得できなかった場合 (None) はエラーメッセージを返す
			if status_data is None:
				await ctx.send_followup(
					embed=embeds.Notification.internal_error(
						description=_("CmdMsg_FailedToGetServerStatus"),
					),
				)

			# メンテナンススケジュールを取得する
			schedule_data = MaintenanceScheduleManager.schedule

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
		else:
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
			value=f"`{app.VERSION_STRING}` ([`{app.get_git_commit_hash()[0:7]}`]\
({app.GITHUB_REPO_URL}/commit/{app.get_git_commit_hash()}))",
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

			status_data = await ServerStatusManager.get()

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
