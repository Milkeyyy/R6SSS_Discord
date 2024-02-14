import datetime

import serverstatus_api
import statusindicator


# サーバーステータス辞書
data = {}

# テキストチャンネルの名前に表示するステータスインジケーター(絵文字)
indicator = statusindicator.Unknown

# サーバーステータスを取得して整えて返す
async def get():
	global indicator

	# サーバーステータスを取得
	status = await serverstatus_api.get_serverstatus()
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
