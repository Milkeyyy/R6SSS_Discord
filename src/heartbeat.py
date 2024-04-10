import cronitor
import logging
import sys


def load_keys():
	global heartbeat
	global monitor

	# APIキーを読み込み
	try:
		f = open('cronitor_keys.txt', 'r', encoding='UTF-8')
	except FileNotFoundError as e:
		logging.warning("Cronitorのキー(cronitor_keys.txt)が見つかりません")
		logging.error(str(e))
		sys.exit(1)

	v = [s.strip() for s in f.readlines()]

	if len(v) < 1:
		f.close()
		logging.error("Cronitorのキーが指定されていません")
		sys.exit(1)

	logging.info(f"Cronitor API/Heartbeat Keys has been loaded: {v[0]}/{v[1]}/{v[2]}")

	cronitor.api_key = v[0]
	heartbeat = cronitor.Monitor(v[1])
	monitor = cronitor.Monitor(v[2])

	f.close()
