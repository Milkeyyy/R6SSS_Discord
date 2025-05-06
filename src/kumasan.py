from os import getenv

import httpx

from logger import logger



class KumaSan:
	@classmethod
	def ping(cls, state: str = "up", message: str = "OK", ping = "") -> None:
		base_url = getenv("UPTIME_KUMA_PUSH_URL")
		if not base_url:
			logger.warning("UPTIME_KUMA_PUSH_URL is not set")
			return
		result = httpx.get(
			url=base_url,
			params={"status": state, "msg": message, "ping": ping},
			timeout=5
		)
