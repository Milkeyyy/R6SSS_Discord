import r6sss
from r6sss.types import MaintenanceSchedule


class MaintenanceScheduleManager:
	data: MaintenanceSchedule | None

	@classmethod
	async def get(cls) -> MaintenanceSchedule | None:
		"""最新のメンテナンススケジュールを取得して整えて返す"""
		# メンテナンススケジュールを取得
		cls.data = r6sss.get_maintenance_schedule()
		return cls.data
