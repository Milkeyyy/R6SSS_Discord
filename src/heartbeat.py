import cronitor
import logging
import sys

def loadKeys():
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

	logging.info(f"Load Cronitor API/Heartbeat Keys: {v[0]}/{v[1]}")

	cronitor.api_key = v[0]
	monitor = cronitor.Monitor(v[1])

	f.close()