import httpx

from logger import logger


API_URL = "https://api-r6sss.milkeyyy.com/v2/schedule/latest"


async def get() -> dict | None:
	"""最新のメンテナンススケジュールを取得して整えて返す"""

	# メンテナンススケジュールを取得
	result = httpx.get(API_URL)
	if result.status_code != 200:
		logger.error("メンテナンススケジュールの取得に失敗")
		logger.error("- %s %s", str(result.status_code), result.json()["detail"])
		return None

	sched = result.json()["data"]

	return sched
