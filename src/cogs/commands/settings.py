import traceback

import discord
from discord.commands import Option, OptionChoice
from discord.ext import commands
from pycord.i18n import _

import embeds
from client import bot
from config import GuildConfigManager
from debug_logger import DebugLogger
from localizations import Localization
from logger import logger


class SettingsCommands(commands.Cog):
	def __init__(self, bot: discord.Bot) -> None:
		self.bot = bot

	@commands.slash_command()
	@discord.guild_only()
	@discord.default_permissions(administrator=True)
	@commands.cooldown(2, 5)
	async def setlanguage(
		self,
		ctx: discord.ApplicationContext,
		locale: Option(
			str,
			choices=[
				OptionChoice(_n, _l) for _l, _n in Localization.EXISTS_LOCALE_LIST.items()
			],  # 選択可能言語リストから選択肢のリストを生成
		),  # pyright: ignore[reportInvalidTypeForm]
	) -> None:
		"""サーバーステータスメッセージの言語を設定するコマンド"""
		await ctx.defer(ephemeral=True)

		if ctx.guild is None:
			raise Exception("ctx.guild is None")

		gc = None

		# ギルドコンフィグを取得する
		gc = await GuildConfigManager.get(ctx.guild.id)
		if gc is None:
			await ctx.send_followup(
				embed=embeds.Notification.internal_error(
					description=_("CmdMsg_FailedToGetConfig"),
					error_code=await DebugLogger.report_internal_error("FailedToGetGuildConfig"),
				)
			)
			return

		if locale in Localization.LOCALE_DATA:
			gc.server_status_message.language = locale
		else:
			gc.server_status_message.language = "en_GB"

		# サーバーステータス埋め込みメッセージを更新する
		await bot.client.get_cog("ServerStatusEmbedManager").update(ctx.guild, None, gc, None)

		# ギルドコンフィグを更新
		if not (await GuildConfigManager.update(ctx.guild.id, gc)):
			# コンフィグの更新に失敗した場合はエラーメッセージを返す
			await ctx.send_followup(embed=embeds.Notification.error(description=_("CmdMsg_FailedToUpdateConfig")))
			return

		await ctx.send_followup(
			embed=embeds.Notification.success(
				description=_(
					"Cmd_setlanguage_Success",
					Localization.EXISTS_LOCALE_LIST.get(gc.server_status_message.language),
					gc.server_status_message.language,
				)
			)
		)

	@commands.slash_command()
	@discord.guild_only()
	@discord.default_permissions(administrator=True)
	@commands.cooldown(2, 5)
	async def setindicator(
		self,
		ctx: discord.ApplicationContext,
		enable: Option(bool),  # pyright: ignore[reportInvalidTypeForm]
	) -> None:
		"""サーバーステータスメッセージが送信されているテキストチャンネルの名前の先頭に表示するインジケーターを設定するコマンド"""
		await ctx.defer(ephemeral=True)

		if ctx.guild is None:
			raise Exception("ctx.guild is None")

		gc = None

		# ギルドコンフィグを取得する
		gc = await GuildConfigManager.get(ctx.guild.id)
		if gc is None:
			await ctx.send_followup(
				embed=embeds.Notification.internal_error(
					description=_("CmdMsg_FailedToGetConfig"),
					error_code=await DebugLogger.report_internal_error("FailedToGetGuildConfig"),
				)
			)
			return

		gc.server_status_message.status_indicator = enable

		# サーバーステータス埋め込みメッセージを更新する
		await bot.client.get_cog("ServerStatusEmbedManager").update(ctx.guild, None, gc, None)

		# ギルドコンフィグを更新
		if not (await GuildConfigManager.update(ctx.guild.id, gc)):
			# コンフィグの更新に失敗した場合はエラーメッセージを返す
			await ctx.send_followup(embed=embeds.Notification.error(description=_("CmdMsg_FailedToUpdateConfig")))
			return

		await ctx.send_followup(embed=embeds.Notification.success(description=_("Cmd_setindicator_Success_" + str(enable), _(str(enable)))))

	@commands.slash_command()
	@discord.guild_only()
	@discord.default_permissions(administrator=True)
	@commands.cooldown(2, 5)
	async def setnotification(
		self,
		ctx: discord.ApplicationContext,
		enable: Option(bool, required=True),  # pyright: ignore[reportInvalidTypeForm]
		channel: Option(discord.TextChannel, required=False),  # pyright: ignore[reportInvalidTypeForm]
		role: Option(discord.Role, required=False),  # pyright: ignore[reportInvalidTypeForm]
		auto_delete: Option(int, required=False, default=10, min_value=0, max_value=600),  # pyright: ignore[reportInvalidTypeForm]
	) -> None:
		"""サーバーステータスに変化があった際に送信される通知を設定するコマンド"""
		await ctx.defer(ephemeral=True)

		if ctx.guild is None:
			raise Exception("ctx.guild is None")

		gc = None
		try:
			# 設定完了埋め込みメッセージを生成
			success_embed = embeds.Notification.success(description=_("Cmd_setnotification_Success", _(str(enable))))

			# ギルドコンフィグを取得する
			gc = await GuildConfigManager.get(ctx.guild.id)
			if gc is None:
				await ctx.send_followup(
					embed=embeds.Notification.internal_error(
						description=_("CmdMsg_FailedToGetConfig"),
						error_code=await DebugLogger.report_internal_error("FailedToGetGuildConfig"),
					)
				)
				return

			# 有効化
			if enable:
				# チャンネルが指定されていない場合はコマンドが実行されたチャンネルにする
				ch_id = ctx.channel_id if channel is None else channel.id

				# 指定されたチャンネルが存在するかチェックする
				ch = await bot.client.get_or_fetch(discord.TextChannel, ch_id)
				# 見つからない場合はエラーメッセージを送信する
				if ch is None:
					await ctx.send_followup(embed=embeds.Notification.error(description=_("CmdMsg_TextChannelNotFound")))
					return
				# メッセージを送信する権限がない場合もエラーメッセージを送信する
				if not ch.can_send():
					await ctx.send_followup(embed=embeds.Notification.error(description=_("CmdMsg_DontHavePermission_SendMessage")))
					return

				# ロールが指定されている場合
				if role is not None:
					# 指定されたロールがメンション可能かチェックする
					# メンションができない場合はエラーメッセージを送信する
					if not role.mentionable:
						await ctx.send_followup(embed=embeds.Notification.error(description=_("Cmd_setnotification_RoleIsNotMentionable")))
						return
					# 指定されたロールのIDを保存
					gc.server_status_notification.role_id = str(role.id)
				# ロールが指定されていない場合
				else:
					# メンションを無効化
					gc.server_status_notification.role_id = "0"

				# 自動削除の値が設定されている場合
				if auto_delete is not None:
					# 秒数を保存
					gc.server_status_notification.auto_delete = int(auto_delete)
				# 指定されていない場合はデフォルト値の10秒にする
				else:
					gc.server_status_notification.auto_delete = 10

				# 指定されたチャンネルのIDを保存
				gc.server_status_notification.channel_id = str(ch_id)

				# 設定完了埋め込みメッセージに項目を追加する
				# テキストチャンネルの項目
				success_embed.add_field(name=_("Cmd_setnotification_Channel"), value=ch.mention)
				# メンションが有効かどうかの項目
				mention_settings_text = role.mention if role else _("False")
				success_embed.add_field(name=_("Cmd_setnotification_Mention"), value=mention_settings_text)
				# 自動削除の項目
				success_embed.add_field(
					name=_("Cmd_setnotification_AutoDelete"),
					value=_("False") if int(auto_delete) == 0 else _("Cmd_setnotification_AutoDelete_Seconds", auto_delete),
				)

			# 無効化
			else:
				gc.server_status_notification.channel_id = "0"
				gc.server_status_notification.role_id = "0"
				gc.server_status_notification.auto_delete = 0

			# ギルドコンフィグを更新
			if not (await GuildConfigManager.update(ctx.guild.id, gc)):
				# コンフィグの更新に失敗した場合はエラーメッセージを返す
				await ctx.send_followup(embed=embeds.Notification.error(description=_("CmdMsg_FailedToUpdateConfig")))
				return

			await ctx.send_followup(embed=success_embed)
		# 例外発生時
		except Exception:
			# 設定をリセット
			if gc is not None:
				gc.server_status_notification.channel_id = "0"
				gc.server_status_notification.role_id = "0"
				gc.server_status_notification.auto_delete = 0
				await GuildConfigManager.update(ctx.guild.id, gc)
			logger.error(traceback.format_exc())
			await ctx.send_response(
				embed=embeds.Notification.internal_error(error_code=await DebugLogger.report_internal_error(traceback.format_exc()))
			)

	@commands.slash_command()
	@discord.guild_only()
	@discord.default_permissions(administrator=True)
	@commands.cooldown(2, 5)
	async def setscheduledisplay(
		self,
		ctx: discord.ApplicationContext,
		enable: Option(bool, required=True),  # pyright: ignore[reportInvalidTypeForm]
	) -> None:
		"""サーバーステータスメッセージにメンテナンススケジュール情報を表示するかどうかを設定するコマンド"""
		await ctx.defer(ephemeral=True)

		if ctx.guild is None:
			raise Exception("ctx.guild is None")

		gc = None
		try:
			# ギルドコンフィグを取得する
			gc = await GuildConfigManager.get(ctx.guild.id)
			if gc is None:
				await ctx.send_followup(
					embed=embeds.Notification.internal_error(
						description=_("CmdMsg_FailedToGetConfig"),
						error_code=await DebugLogger.report_internal_error("FailedToGetGuildConfig"),
					)
				)
				return

			gc.server_status_message.maintenance_schedule = enable

			# サーバーステータス埋め込みメッセージを更新する
			await bot.client.get_cog("ServerStatusEmbedManager").update(ctx.guild, None, gc, None)

			# ギルドコンフィグを更新
			if not (await GuildConfigManager.update(ctx.guild.id, gc)):
				# コンフィグの更新に失敗した場合はエラーメッセージを返す
				await ctx.send_followup(embed=embeds.Notification.error(description=_("CmdMsg_FailedToUpdateConfig")))
				return

			await ctx.send_followup(embed=embeds.Notification.success(description=_("Cmd_setscheduledisplay_Success", _(str(enable)))))
		except Exception:
			# 設定をリセット
			if gc is not None:
				gc.server_status_message.maintenance_schedule = True
				await GuildConfigManager.update(ctx.guild.id, gc)
			logger.error(traceback.format_exc())
			await ctx.send_response(
				embed=embeds.Notification.internal_error(error_code=await DebugLogger.report_internal_error(traceback.format_exc()))
			)

	@commands.slash_command()
	@discord.guild_only()
	@discord.default_permissions(administrator=True)
	@commands.cooldown(2, 5)
	async def viewsettings(self, ctx: discord.ApplicationContext) -> None:
		await ctx.defer(ephemeral=True)

		if ctx.guild is None:
			raise Exception("ctx.guild is None")

		gc = None

		# ギルドコンフィグを取得する
		gc = await GuildConfigManager.get(ctx.guild.id)
		if gc is None:
			await ctx.send_followup(
				embed=embeds.Notification.internal_error(
					description=_("CmdMsg_FailedToGetConfig"),
					error_code=await DebugLogger.report_internal_error("FailedToGetGuildConfig"),
				)
			)
			return

		# 作成されたサーバーステータスメッセージ(とそのテキストチャンネル)を取得する
		status_msg_ch = await bot.client.get_or_fetch(discord.TextChannel, int(gc.server_status_message.channel_id))
		if status_msg_ch:
			try:
				status_msg = await status_msg_ch.fetch_message(int(gc.server_status_message.message_id))
			except discord.errors.NotFound:
				status_msg = None
		else:
			status_msg = None

		language = gc.server_status_message.language
		language_text = f"`{Localization.EXISTS_LOCALE_LIST.get(language)}` (`{language}`)"

		sections = [
			# サーバーステータスメッセージ
			{
				"icon": ":envelope:",
				"name": _("Cmd_viewsettings_ServerStatusMessage"),
				"value": (
					f"[**{_('Cmd_viewsettings_ServerStatusMessage_Created')}**]({status_msg.jump_url})"
					if status_msg
					else f"**{_('Cmd_viewsettings_ServerStatusMessage_None')}**"
				),
			},
			# メンテナンススケジュールの表示
			{
				"icon": ":calendar:",
				"name": _("Cmd_viewsettings_MaintenanceSchedule"),
				"value": f"`{_(str(gc.server_status_message.maintenance_schedule))}`",
			},
			# インジケーター
			{
				"icon": ":radio_button:",
				"name": _("Cmd_viewsettings_Indicator"),
				"value": f"`{_(str(gc.server_status_message.status_indicator))}`",
			},
			# 言語
			{
				"icon": ":globe_with_meridians:",
				"name": _("Cmd_viewsettings_Language"),
				"value": language_text,
			},
		]

		# 通知
		notif_ch = await bot.client.get_or_fetch(discord.TextChannel, int(gc.server_status_notification.channel_id))
		if notif_ch is not None:
			# ロール
			if gc.server_status_notification.role_id != "0":
				notif_role_text = f"<@&{gc.server_status_notification.role_id}>"
			else:
				notif_role_text = f"`{_('False')}`"
			# 自動削除
			if int(gc.server_status_notification.auto_delete) == 0:
				notif_ad_text = f"`{_('False')}`"
			else:
				notif_ad_text = _(
					"Cmd_setnotification_AutoDelete_Seconds",
					gc.server_status_notification.auto_delete,
				)
			# 有効
			sections.append(
				{
					"icon": ":bell:",
					"name": _("Cmd_viewsettings_Notification"),
					"value": f"`{_('True')}`",
					# チャンネル / メンション / 自動削除
					"items": [
						{"name": _("Cmd_setnotification_Channel"), "value": notif_ch.mention},
						{"name": _("Cmd_setnotification_Mention"), "value": notif_role_text},
						{"name": _("Cmd_setnotification_AutoDelete"), "value": notif_ad_text},
					],
				}
			)
		else:
			# 無効
			sections.append(
				{
					"icon": ":bell:",
					"name": _("Cmd_viewsettings_Notification"),
					"value": f"`{_('False')}`",
				}
			)

		# 生成した埋め込みメッセージを送信
		await ctx.send_followup(
			embed=await embeds.Settings.settings(
				title=_("Cmd_viewsettings_CurrentSettings"),
				sections=sections,
			)
		)


def setup(bot: discord.Bot) -> None:
	bot.add_cog(SettingsCommands(bot))
