import datetime

import httpx

from logger import logger
import status_indicator


API_URL = "https://api-r6sss.milkeyyy.com/v2/status"

# サーバーステータス辞書
data: dict = {}
updated_at: int = 0

# テキストチャンネルの名前に表示するステータスインジケーター(絵文字)
indicator = status_indicator.Unknown

async def get() -> dict[str, dict] | None:
	"""サーバーステータスを取得して整えて返す"""

	global updated_at
	global indicator

	# サーバーステータスを取得
	result = httpx.get(API_URL)
	if result.status_code != 200:
		logger.error("サーバーステータスの取得に失敗")
		logger.error("- %s %s", str(result.status_code), result.json()["detail"])
		return None

	status = result.json()["data"]
	updated_at = int(datetime.datetime.now().timestamp())

	status_list = []
	# ステータスインジケーターを設定
	for k, v in status.items():
		if k.startswith("_") :
			continue

		st = v["Status"]["Connectivity"]
		status_list.append(st)

		if st == "Operational" and "Interrupted" not in status_list and "Degraded" not in status_list and "Maintenance" not in status_list:
			indicator = status_indicator.Operational
		if st == "Interrupted":
			indicator = status_indicator.Interrupted
		if st == "Degraded":
			indicator = status_indicator.Degraded
		if v["Status"]["Maintenance"]:
			indicator = status_indicator.Maintenance

	return status
