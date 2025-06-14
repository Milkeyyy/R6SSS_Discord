import traceback

import discord
import uuid_utils as uuid

import embeds
from logger import logger


class DebugLogger:
	debug_guild: discord.Guild | None = None
	debug_channel: discord.TextChannel | None = None

	@classmethod
	async def log(cls, text: str) -> None:
		"""デバッグログを送信する"""
		if cls.debug_guild is None or cls.debug_channel is None:
			logger.warning("デバッグログ記録中止 - デバッグ用サーバーまたはチャンネルが設定されていません")
			return
		try:
			await cls.debug_channel.send(text)
		except Exception:
			logger.error("デバッグログ送信失敗")
			logger.error(traceback.format_exc())

	@classmethod
	async def report_internal_error(cls, traceback_text: str) -> str | None:
		"""内部エラーを報告してエラーコードを返す 失敗した場合は None を返す"""
		try:
			if cls.debug_guild is None or cls.debug_channel is None:
				logger.warning("内部エラー報告中止 - デバッグ用サーバーまたはチャンネルが設定されていません")
				return None
			# エラーコードを生成
			error_code = str(uuid.uuid7())
			await cls.debug_channel.send(
				embed=embeds.Notification.internal_error(
					description=f"エラーコード\n```{error_code}```\nトレースバック\n```{traceback_text}```"
				)
			)
		except Exception:
			logger.error("内部エラー報告失敗")
			logger.error(traceback.format_exc())
			return None
		else:
			return error_code
