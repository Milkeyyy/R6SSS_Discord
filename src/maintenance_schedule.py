from typing import ClassVar

import r6sss
from r6sss.types import MaintenanceSchedule


class MaintenanceScheduleManager:
	data: dict[str, MaintenanceSchedule] | None
	LOCALE_LIST: ClassVar[list[str]] = ["ja", "en"]
	LOCALE_MAP: ClassVar[dict[str, str]] = {"en_GB": "en", "en_US": "en"}

	@classmethod
	async def get(cls) -> dict[str, MaintenanceSchedule] | None:
		"""最新のメンテナンススケジュールを取得して整えて返す"""
		data = {}
		# メンテナンススケジュールを取得 (言語をキーとして辞書に整えて返す)
		for locale in cls.LOCALE_LIST:
			data[locale] = r6sss.get_maintenance_schedule(language=locale)
		for k, v in cls.LOCALE_MAP.items():
			if v in data:
				data[k] = data[v]
		cls.data = data
		return cls.data
