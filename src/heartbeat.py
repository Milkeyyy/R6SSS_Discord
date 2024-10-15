import os

import cronitor

from logger import logger


heartbeat: cronitor.Monitor
monitor: cronitor.Monitor

def load_keys():
	global heartbeat
	global monitor

	# APIキーを読み込み
	if not os.getenv("CRONITOR_API_KEY"):
		logger.warning("CronitorのAPIキーが指定されていません")
		return

	cronitor.api_key = os.getenv("CRONITOR_API_KEY")
	heartbeat = cronitor.Monitor(os.getenv("CRONITOR_HEARTBEAT_KEY"))
	monitor = cronitor.Monitor(os.getenv("CRONITOR_MONITOR_KEY"))
