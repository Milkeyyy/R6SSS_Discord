import datetime

import serverstatus_api
import status_indicator


# サーバーステータス辞書
data = {}

# テキストチャンネルの名前に表示するステータスインジケーター(絵文字)
indicator = status_indicator.Unknown

async def get() -> dict[str, dict]:
	"""サーバーステータスを取得して整えて返す"""

	global indicator

	# サーバーステータスを取得
	status = await serverstatus_api.get_serverstatus()
	status["_Update_At"] = int(datetime.datetime.now(datetime.timezone.utc).timestamp())

	status_list = []
	# ステータスインジケーターを設定
	for k, v in status.items():
		if k.startswith("_") : continue

		st = v["Status"]["Connectivity"]
		status_list.append(st)

		if st == "Operational" and "Interrupted" not in status_list and "Degraded" not in status_list and "Maintenance" not in status_list:
			indicator = status_indicator.Operational
		if st == "Interrupted":
			indicator = status_indicator.Interrupted
		if st == "Degraded":
			indicator = status_indicator.Degraded
		if v["Maintenance"] == True:
			indicator = status_indicator.Maintenance

	return status
