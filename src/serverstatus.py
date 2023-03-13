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
		status = {"Unknown": {"Status": {"Connectivity": "Unknown", "Authentication": "Unknown", "Leaderboard": "Unknown", "Matchmaking": "Unknown", "Purchase": "Unknown"}, "Maintenance": None, "ImpactedFeatures": None}, "_update_date": datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))}
		indicator = statusindicator.Unknown
		return status

	status = json.loads(res.read())
	status["_update_date"] = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))

	# ステータスインジケーターを設定
	for k, v in status.items():
		if k == "_update_date": continue
		st = v["Status"]["Connectivity"]
		if st == "Operational" and indicator != statusindicator.Interrupted and indicator != statusindicator.Degraded and indicator != statusindicator.Maintenance:
			indicator = statusindicator.Operational
		if st == "Interrupted":
			indicator = statusindicator.Interrupted
		if st == "Degraded":
			indicator = statusindicator.Degraded
		if st == "Maintenance":
			indicator = statusindicator.Maintenance

	return status
