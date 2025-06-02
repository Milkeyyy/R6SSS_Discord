import r6sss
from r6sss.types import MaintenanceSchedule


class MaintenanceScheduleManager:
	schedule: MaintenanceSchedule | None

	@classmethod
	async def get(cls) -> MaintenanceSchedule | None:
		"""最新のメンテナンススケジュールを取得して整えて返す"""
		# メンテナンススケジュールを取得
		cls.schedule = r6sss.get_maintenance_schedule()
		return cls.schedule
