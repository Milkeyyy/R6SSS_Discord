import traceback

import discord
from discord.ext import commands, tasks

from db import DBManager
from logger import logger
from stats import StatsManager


class StatsTaskManager(commands.Cog):
	def __init__(self, bot: discord.Bot) -> None:
		self.bot = bot
		self.flush_stats.start()
		self.collect_stats.start()

	def cog_unload(self) -> None:
		"""Cog のアンロード時に定期実行ループを停止する"""
		self.flush_stats.cancel()
		self.collect_stats.cancel()

	async def _wait_until_ready(self, label: str) -> None:
		"""クライアントとデータベースの準備が完了するまで待機する"""
		logger.info("統計の%s待機中", label)
		logger.info("- クライアントの準備完了まで待機中")
		await self.bot.wait_until_ready()
		logger.info("- クライアントの準備完了")
		logger.info("- データベースの接続待機中")
		await DBManager.connected_event.wait()
		logger.info("- データベースの接続完了")
		logger.info("統計の%s開始", label)

	# 60秒毎に統計バッファをデータベースへ書き込む
	@tasks.loop(seconds=60)
	async def flush_stats(self) -> None:
		try:
			await StatsManager.flush()
		except Exception:
			logger.error("統計データの定期書き込みでエラー")
			logger.error(traceback.format_exc())

	# 10分毎にスナップショットとギルド情報を収集する
	@tasks.loop(minutes=10)
	async def collect_stats(self) -> None:
		try:
			await StatsManager.collect_snapshot(self.bot)
			await StatsManager.upsert_guilds(list(self.bot.guilds))
		except Exception:
			logger.error("統計データの定期収集でエラー")
			logger.error(traceback.format_exc())

	@flush_stats.before_loop
	async def before_flush_stats(self) -> None:
		await self._wait_until_ready("定期書き込み")

	@collect_stats.before_loop
	async def before_collect_stats(self) -> None:
		await self._wait_until_ready("定期収集")


def setup(bot: discord.Bot) -> None:
	bot.add_cog(StatsTaskManager(bot))
