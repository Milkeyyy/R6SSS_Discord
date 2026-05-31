import asyncio
from typing import ClassVar

import httpx
import r6sss
from r6sss.types import MaintenanceSchedule

from logger import logger


class MaintenanceScheduleManager:
	RETRY_COUNT = 3
	RETRY_DELAY_SECONDS = 1
	data: dict[str, MaintenanceSchedule] | None = None
	previous_data: dict[str, MaintenanceSchedule] | None = None
	LOCALE_LIST: ClassVar[list[str]] = ["ja", "en"]
	LOCALE_MAP: ClassVar[dict[str, str]] = {"en_GB": "en", "en_US": "en"}

	@classmethod
	async def get(cls) -> dict[str, MaintenanceSchedule] | None:
		"""最新のメンテナンススケジュールを取得して整えて返す"""
		for attempt in range(1, cls.RETRY_COUNT + 1):
			data = {}
			try:
				# メンテナンススケジュールを取得 (言語をキーとして辞書に整えて返す)
				for locale in cls.LOCALE_LIST:
					data[locale] = await asyncio.to_thread(r6sss.get_maintenance_schedule, language=locale)
				for k, v in cls.LOCALE_MAP.items():
					if v in data:
						data[k] = data[v]
			except httpx.HTTPError as e:
				logger.warning("メンテナンススケジュールの取得に失敗 (%s/%s): %s", attempt, cls.RETRY_COUNT, str(e))
				if attempt < cls.RETRY_COUNT:
					await asyncio.sleep(cls.RETRY_DELAY_SECONDS)
				continue

			cls.previous_data = cls.data
			cls.data = data
			return cls.data

		return None
