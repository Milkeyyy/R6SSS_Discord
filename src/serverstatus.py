import datetime
import json
import logging
import urllib

# サーバーステータスAPIのURL
api_url = "https://api.r6sss.milkeyyy.com"

# サーバーステータス辞書
data = {}

# サーバーステータスを取得して整えて返す
async def get():
	# サーバーステータスを取得する
	res = urllib.request.urlopen(urllib.request.Request(api_url))
	#logging.info(str(res.read()))

	# ステータスコードが200以外の場合はUnknownなデータを返す
	if res.status != 200:
		status = {"Unknown": {"Status": {"Connectivity": "Unknown", "Authentication": "Unknown", "Leaderboard": "Unknown", "Matchmaking": "Unknown", "Purchase": "Unknown"}, "Maintenance": None, "ImpactedFeatures": None}, "_update_date": datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))}
		return status

	status = json.loads(res.read())
	status["_update_date"] = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))

	return status
