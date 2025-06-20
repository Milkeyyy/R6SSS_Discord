import datetime

import discord
import r6sss

import icons


class ServerStatusManager:
	"""サーバーステータスを管理するクラス"""

	data: list[r6sss.types.Status] | None = None
	previous_data: list[r6sss.types.Status] | None = None
	updated_at: int = 0
	indicator = icons.Indicator.UNKNOWN.value
	"""テキストチャンネルの名前に表示するステータスインジケーター(絵文字)"""
	colour = discord.Colour.from_rgb(255, 255, 255)
	"""埋め込みメッセージの色"""

	@classmethod
	async def get(cls) -> list[r6sss.types.Status] | None:
		"""サーバーステータスを取得して整えて返す"""
		# サーバーステータスを取得
		result = r6sss.get_server_status()
		if result is None:
			return None

		# 以前のサーバーステータスを更新する
		cls.previous_data = cls.data

		# 現在のサーバーステータスを更新する
		cls.data = result

		# 更新日時を設定
		cls.updated_at = int(datetime.datetime.now(tz=datetime.UTC).timestamp())

		status_list = []
		# ステータスインジケータと埋め込みメッセージの色を設定
		for status in result:
			st = status.connectivity
			status_list.append(st)
			if all(
				(st == "Operational", "Interrupted" not in status_list, "Degraded" not in status_list, "Maintenance" not in status_list)
			):
				cls.indicator = icons.Indicator.OPERATIONAL.value
				cls.colour = discord.Colour.from_rgb(91, 207, 109)
			if st == "Interrupted":
				cls.indicator = icons.Indicator.INTERRUPTED.value
				cls.colour = discord.Colour.from_rgb(255, 106, 0)
			if st in ("Degraded", "Outage"):  # Connectivity が Outage になるかわからないので、念の為入れておく
				cls.indicator = icons.Indicator.DEGRADED.value
				cls.colour = discord.Colour.from_rgb(255, 0, 0)
			if status.maintenance:
				cls.indicator = icons.Indicator.MAINTENANCE.value
				cls.colour = discord.Colour.from_rgb(160, 160, 160)

		return result
