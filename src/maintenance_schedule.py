import r6sss
from r6sss.types import MaintenanceSchedule

from logger import logger


API_URL = "https://api-r6sss.milkeyyy.com/v2/schedule/latest"


class MaintenanceScheduleManager:
	schedule: list[MaintenanceSchedule]

	@classmethod
	async def get(cls) -> list[MaintenanceSchedule]:
		"""最新のメンテナンススケジュールを取得して整えて返す"""

		# メンテナンススケジュールを取得
		cls.schedule = r6sss.get_maintenance_schedule()

		return cls.schedule
