import traceback

import discord

import embeds
from logger import logger


class GuildOwnerAnnounceUtil:
	@classmethod
	async def send_message_to_guild_owner(
		cls,
		guild: discord.Guild,
		content: str | None = None,
		embeds: list[discord.Embed] | None = None,
	) -> bool:
		try:
			owner = guild.owner
			if owner is not None:
				await guild.owner.send(content=content, embeds=embeds)
				logger.info("オーナーメッセージ送信 - ギルド: %s | オーナー: %s", guild.name, owner.name)
		except Exception as e:
			logger.error(traceback.format_exc())
			logger.warning("オーナーメッセージ送信失敗: %s", str(e))
			return False
		else:
			return True

	@classmethod
	async def send_warning(cls, guild: discord.Guild, title: str = "", description: str = "") -> bool:
		"""指定したギルドのオーナーへ警告メッセージを送信する"""
		return await cls.send_message_to_guild_owner(
			guild=guild,
			embeds=[embeds.Notification.warning(title=title, description=description)],
		)
