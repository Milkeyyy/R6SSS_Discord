from os import getenv

import httpx

from logger import logger


class KumaSan:
	cl = httpx.AsyncClient()

	@classmethod
	async def ping(cls, state: str = "up", message: str = "OK", ping: str = "") -> None:
		base_url = getenv("UPTIME_KUMA_PUSH_URL")
		if base_url is None:
			logger.warning("UPTIME_KUMA_PUSH_URL is not set")
			return
		result = None
		try:
			result = await cls.cl.get(
				url=base_url,
				params={"status": state, "msg": message, "ping": ping},
				timeout=15,
			)
			logger.debug(
				"Heartbeat send complete - State: %s | Msg: %s | Ping: %s ",
				state,
				message,
				ping,
			)
			logger.debug(
				"- Status code: %s / Elapsed time: %ds",
				result.status_code,
				result.elapsed.seconds,
			)
		except Exception:
			logger.warning(
				"Heartbeat send failed - State: %s | Msg: %s | Ping: %s ",
				state,
				message,
				ping,
			)
			if result is not None:
				logger.warning(
					"- Status code: %s / Elapsed time: %ds",
					result.status_code,
					result.elapsed.seconds,
				)
