import datetime
import json
import logging
import urllib

# サーバーステータスAPIのURL
api_url = "https://game-status-api.ubisoft.com/v1/instances?spaceIds=57e580a1-6383-4506-9509-10a390b7e2f1,05bfb3f7-6c21-4c42-be1f-97a33fb5cf66,96c1d424-057e-4ff7-860b-6b9c9222bdbf,98a601e5-ca91-4440-b1c5-753f601a2c90,631d8095-c443-4e21-b301-4af1a0929c27"
pc_api_url = "https://game-status-api.ubisoft.com/v1/instances?appIds=e3d5ea9e-50bd-43b7-88bf-39794f4e3d40"

# サーバーステータス辞書
data = {}

# サーバーステータスを取得して整えて返す
async def get():
	# サーバーステータスを取得する
	res = urllib.request.urlopen(urllib.request.Request(api_url))
	#logging.info(str(res.read()))
	res_pc = urllib.request.urlopen(urllib.request.Request(pc_api_url))
	#logging.info(str(res_pc.read()))

	# ステータスコードが200出ない場合はNoneを返す
	if res.status != 200 or res_pc.status != 200:
		status = {"Unknown": {"Status": {"Connectivity": "Unknown", "Authentication": "Unknown", "Leaderboard": "Unknown", "Matchmaking": "Unknown", "Purchase": "Unknown"}, "Maintenance": None, "ImpactedFeatures": None}, "_update_date": datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))}
		return status

	raw_status = json.loads(res_pc.read())
	raw_status.extend(json.loads(res.read()))
	#logging.info(str(raw_status))

	# 各プラットフォームのステータスをループ、ステータス辞書に加える
	status = {}
	for s in raw_status:
		p = s["Platform"]
		status[p] = {"Status": {"Connectivity": None, "Authentication": "Operational", "Leaderboard": "Operational", "Matchmaking": "Operational", "Purchase": "Operational"}, "Maintenance": None, "ImpactedFeatures": None}
		status[p]["Status"]["Connectivity"] = s["Status"]
		if status[p]["Status"]["Connectivity"] == "Online": status[p]["Status"]["Connectivity"] = "Operational"

		# ImpactedFeatures をループ リストに含まれる場合は停止中なので、該当するステータスをOutageにする
		for f in s["ImpactedFeatures"]:
			status[p]["Status"][f] = "Outage"

		status[p]["Maintenance"] = s["Maintenance"]

	status["_update_date"] = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))

	#logging.info(str(status))

	return status