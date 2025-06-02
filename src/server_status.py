import datetime

import r6sss

import status_indicator


class ServerStatusManager:
	"""サーバーステータスを管理するクラス"""

	def __init__(self) -> None:
		self.data: list[r6sss.types.Status] | None = []
		self.previous_data: list = []
		self.updated_at: int = 0
		self.indicator = status_indicator.Unknown  # テキストチャンネルの名前に表示するステータスインジケーター(絵文字)

	@classmethod
	async def get(cls) -> list[r6sss.types.Status] | None:
		"""サーバーステータスを取得して整えて返す"""
		# サーバーステータスを取得
		result = r6sss.get_server_status()
		if result is None:
			return None

		cls.updated_at = int(datetime.datetime.now(tz=datetime.UTC).timestamp())

		status_list = []
		# ステータスインジケーターを設定
		for status in result:
			st = status.connectivity
			status_list.append(st)

			if (
				st == "Operational"
				and "Interrupted" not in status_list
				and "Degraded" not in status_list
				and "Maintenance" not in status_list
			):
				cls.indicator = status_indicator.Operational
			if st == "Interrupted":
				cls.indicator = status_indicator.Interrupted
			if st == "Degraded":
				cls.indicator = status_indicator.Degraded
			if status.maintenance:
				cls.indicator = status_indicator.Maintenance

		return result

	@classmethod
	async def update(cls) -> None:
		"""サーバーステータスを更新する"""
		cls.previous_data = cls.data
		cls.data = await cls.get()
