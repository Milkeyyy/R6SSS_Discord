import traceback

import discord
from discord.commands import Option, OptionChoice
from discord.ext import commands
from pycord.i18n import _

from client import client
from config import GuildConfig
import embeds
import localizations
from localizations import EXISTS_LOCALE_LIST
from logger import logger


class SettingsCommands(commands.Cog):
	def __init__(self, bot) -> None:
		self.bot = bot

	@commands.slash_command()
	@discord.guild_only()
	@discord.default_permissions(administrator=True)
	@commands.cooldown(2, 5)
	async def setlanguage(self, ctx: discord.ApplicationContext,
		locale: Option(
			str,
			choices=[OptionChoice(_n, _l) for _l, _n in EXISTS_LOCALE_LIST.items()] # 選択可能言語リストから選択肢のリストを生成
		) # pyright: ignore[reportInvalidTypeForm]
	) -> None:
		await ctx.defer(ephemeral=True)

		gc = None
		try:
			# ギルドコンフィグを取得する
			gc = await GuildConfig.get(ctx.guild.id)
			if not gc:
				await ctx.send_followup(embed=embeds.Notification.internal_error(description=_("CmdMsg_FailedToGetConfig")))
				return

			if locale in localizations.LOCALE_DATA:
				gc.server_status_message.language = locale
			else:
				gc.server_status_message.language = "en_GB"

			# ギルドデータを保存
			await GuildConfig.set(ctx.guild.id, gc)

			await ctx.send_followup(embed=embeds.Notification.success(
				description=_(
					"Cmd_setlanguage_Success",
					EXISTS_LOCALE_LIST.get(gc.server_status_message.language),
					gc.server_status_message.language
				)
			))
		except Exception:
			# 設定をリセット
			if gc is not None:
				gc.server_status_message.language = "en_GB"
				await GuildConfig.set(ctx.guild.id, gc)
			logger.error(traceback.format_exc())
			await ctx.send_followup(embed=embeds.Notification.internal_error())

	@commands.slash_command()
	@discord.guild_only()
	@discord.default_permissions(administrator=True)
	@commands.cooldown(2, 5)
	async def setindicator(self, ctx: discord.ApplicationContext,
		enable: Option(
			bool
		) # pyright: ignore[reportInvalidTypeForm]
	) -> None:
		await ctx.defer(ephemeral=True)

		gc = None
		try:
			# ギルドコンフィグを取得する
			gc = await GuildConfig.get(ctx.guild.id)
			if not gc:
				await ctx.send_followup(embed=embeds.Notification.internal_error(description=_("CmdMsg_FailedToGetConfig")))
				return

			gc.server_status_message.status_indicator = enable

			# ギルドコンフィグを保存
			await GuildConfig.set(ctx.guild.id, gc)

			await ctx.send_followup(embed=embeds.Notification.success(description=_("Cmd_setindicator_Success", str(enable))))
		except Exception:
			# 設定をリセット
			if gc is not None:
				gc.server_status_message.status_indicator = False
				await GuildConfig.set(ctx.guild.id, gc)
			logger.error(traceback.format_exc())
			await ctx.send_followup(embed=embeds.Notification.internal_error())

	@commands.slash_command()
	@discord.guild_only()
	@discord.default_permissions(administrator=True)
	@commands.cooldown(2, 5)
	async def setnotification(self, ctx: discord.ApplicationContext,
		enable: Option(
			bool,
			required=True
		), # pyright: ignore[reportInvalidTypeForm]
		channel: Option(
			discord.TextChannel,
			required=False
		), # pyright: ignore[reportInvalidTypeForm]
		role: Option(
			discord.Role,
			required=False
		), # pyright: ignore[reportInvalidTypeForm]
		auto_delete: Option(
			int,
			required=False,
			default=10,
			min_value=0,
			max_value=600
		) # pyright: ignore[reportInvalidTypeForm]
	) -> None:
		await ctx.defer(ephemeral=True)

		gc = None
		try:
			# ギルドコンフィグを取得する
			gc = await GuildConfig.get(ctx.guild.id)
			if not gc:
				await ctx.send_followup(embed=embeds.Notification.internal_error(description=_("CmdMsg_FailedToGetConfig")))
				return

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
					gc.server_status_notification.role_id = str(role.id)
				# ロールが指定されていない場合
				else:
					# メンションを無効化
					gc.server_status_notification.role_id = "0"

				# 自動削除の値が設定されている場合
				if auto_delete:
					# 秒数を保存
					gc.server_status_notification.auto_delete = auto_delete
				# 指定されていない場合はデフォルト値の10秒にする
				else:
					gc.server_status_notification.auto_delete = 10

				# 指定されたチャンネルのIDを保存
				gc.server_status_notification.channel_id = str(ch_id)

			# 無効化
			else:
				gc.server_status_notification.channel_id = "0"
				gc.server_status_notification.role_id = "0"
				gc.server_status_notification.auto_delete = "0"

			# ギルドデータを保存
			await GuildConfig.set(ctx.guild.id, gc)

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
				# 自動削除の項目
				success_embed.add_field(name=_("Cmd_setnotification_AutoDelete"), value=_("False") if auto_delete == 0 else _("Cmd_setnotification_AutoDelete_Seconds", auto_delete))
			await ctx.send_followup(embed=success_embed)
		# 例外発生時
		except Exception:
			# 設定をリセット
			if gc is not None:
				gc.server_status_notification.channel_id = "0"
				gc.server_status_notification.role_id = "0"
				gc.server_status_notification.auto_delete = "0"
				await GuildConfig.set(ctx.guild.id, gc)
			logger.error(traceback.format_exc())
			await ctx.send_followup(embed=embeds.Notification.internal_error())

	@commands.slash_command()
	@discord.guild_only()
	@discord.default_permissions(administrator=True)
	@commands.cooldown(2, 5)
	async def viewsettings(self, ctx: discord.ApplicationContext):
		await ctx.defer(ephemeral=True)

		gc = None
		try:
			# ギルドコンフィグを取得する
			gc = await GuildConfig.get(ctx.guild.id)
			if not gc:
				await ctx.send_followup(embed=embeds.Notification.internal_error(description=_("CmdMsg_FailedToGetConfig")))
				return

			# 埋め込みメッセージを生成
			embed = discord.Embed(
				title=":gear: " + _("Cmd_showsettings_CurrentSettings")
			)
			# 作成されたサーバーステータスメッセージ
			status_msg_ch = client.get_channel(gc.server_status_message.channel_id)
			status_msg = await status_msg_ch.fetch_message(gc.server_status_message.message_id)
			embed.add_field(
				name=f":envelope: {_("Cmd_showsettings_ServerStatusMessage")}",
				value=f"[**{_("Cmd_showsettings_ServerStatusMessage_Created")}**]({status_msg.jump_url})" if status_msg else f"**{_("Cmd_showsettings_ServerStatusMessage_None")}**"
			)
			# インジケーター
			embed.add_field(
				name=f":radio_button: {_("Cmd_showsettings_Indicator")}",
				value=f"`{_(str(gc.server_status_message.status_indicator))}`"
			)
			# 言語
			embed.add_field(
				name=f":globe_with_meridians: {_("Cmd_showsettings_Language")}",
				value=f"`{EXISTS_LOCALE_LIST.get(gc.server_status_message.language)}` (`{gc.server_status_message.language}`)"
			)
			# 通知
			notif_ch = client.get_channel(gc.server_status_notification.channel_id)
			if notif_ch:
				# 有効
				notif_settings_text = f"`{_("True")}`"
				# チャンネル
				notif_settings_text += f"\n> `{_("Cmd_setnotification_Channel")}`: {notif_ch.mention}"
				# ロール
				if gc.server_status_notification.role_id != 0:
					notif_role_text = f"<@&{gc.server_status_notification.role_id}>"
				else:
					notif_role_text = F"`{_("False")}`"
				notif_settings_text += f"\n> `{_("Cmd_setnotification_Mention")}`: {notif_role_text}"
				# 自動削除
				if gc.server_status_notification.auto_delete != 0:
					notif_ad_text = _("Cmd_setnotification_AutoDelete_Seconds", gc.server_status_notification.auto_delete)
				else:
					notif_ad_text = f"`{_("False")}`"
				notif_settings_text += f"\n> `{_("Cmd_setnotification_AutoDelete")}`: {notif_ad_text}"
			else:
				# 無効
				notif_settings_text = f"`{_("False")}`"
			embed.add_field(
				name=f":bell: {_("Cmd_showsettings_Notification")}",
				value=notif_settings_text,
				inline=False
			)
			# 生成した埋め込みメッセージを送信
			await ctx.send_followup(embed=embed)
		except Exception:
			logger.error(traceback.format_exc())
			await ctx.send_followup(embed=embeds.Notification.internal_error())


def setup(bot):
	bot.add_cog(SettingsCommands(bot))
