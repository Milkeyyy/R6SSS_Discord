import json
import logging

locale = "ja-JP"
data = {}
locales = []

def loadLocaleData():
	global data
	global locales

	# ファイルから言語データを読み込む
	file = open("localizations.json", "r", encoding="utf-8")
	data = json.load(file)
	file.close()
	locales = data["Locales"].values()

def translate(text):
	global locale

	try:
		return data["Text"][text][locale]
	except KeyError as e:
		#logging.error(str(e))
		return text