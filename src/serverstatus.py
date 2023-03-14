import datetime
import json
import logging
import urllib

import statusindicator

# サーバーステータスAPIのURL
api_url = "https://api.r6sss.milkeyyy.com"

# サーバーステータス辞書
data = {}

# テキストチャンネルの名前に表示するステータスインジケーター(絵文字)
indicator = statusindicator.Unknown

# サーバーステータスを取得して整えて返す
async def get():
	global indicator

	# サーバーステータスを取得する
	res = urllib.request.urlopen(urllib.request.Request(api_url))
	#logging.info(str(res.read()))

	# ステータスコードが200以外の場合はUnknownなデータを返す
	if res.status != 200:
		status = {"Unknown": {"Status": {"Connectivity": "Unknown", "Authentication": "Unknown", "Leaderboard": "Unknown", "Matchmaking": "Unknown", "Purchase": "Unknown"}, "Maintenance": None, "ImpactedFeatures": None}, "_update_date": datetime.datetime.utcnow().timestamp()}
		indicator = statusindicator.Unknown
		return status

	status = json.loads(res.read())
	status["_update_date"] = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))

	status_list = []
	# ステータスインジケーターを設定
	for k, v in status.items():
		if k == "_update_date": continue

		st = v["Status"]["Connectivity"]
		status_list.append(st)

		if st == "Operational" and "Interrupted" not in status_list and "Degraded" not in status_list and "Maintenance" not in status_list:
			indicator = statusindicator.Operational
		if st == "Interrupted":
			indicator = statusindicator.Interrupted
		if st == "Degraded":
			indicator = statusindicator.Degraded
		if v["Maintenance"] == True:
			indicator = statusindicator.Maintenance

	return status
