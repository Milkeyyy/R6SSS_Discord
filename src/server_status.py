import datetime

import r6sss

import status_indicator


class ServerStatusManager:
	"""サーバーステータスを管理するクラス"""

	data: list[r6sss.types.Status] | None = None
	previous_data: list[r6sss.types.Status] | None = None
	updated_at: int = 0
	indicator = status_indicator.Unknown  # テキストチャンネルの名前に表示するステータスインジケーター(絵文字)

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
		# ステータスインジケーターを設定
		for status in result:
			st = status.connectivity
			status_list.append(st)
			if all(
				(st == "Operational", "Interrupted" not in status_list, "Degraded" not in status_list, "Maintenance" not in status_list)
			):
				cls.indicator = status_indicator.Operational
			if st == "Interrupted":
				cls.indicator = status_indicator.Interrupted
			if st in ("Degraded", "Outage"):  # Connectivity が Outage になるかわからないので、念の為入れておく
				cls.indicator = status_indicator.Degraded
			if status.maintenance:
				cls.indicator = status_indicator.Maintenance

		return result
