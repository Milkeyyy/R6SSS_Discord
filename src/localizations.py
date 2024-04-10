from glob import glob
import json
from os import path

from pycord.i18n import I18n

from client import client
from logger import logger


locale = "ja-JP"
data = {}
#LOCALES: list


def load_localedata():
	global data
	global i18n
	global LOCALES

	# 言語一覧
	LOCALES = []
	locale_data = dict()

	# 言語ファイルを読み込む
	logger.info("言語ファイルを読み込み")
	for f in glob("src/locales/*.json"):
		lang = path.splitext(path.basename(f))[0]
		logger.info("- " + lang)
		# 言語一覧に追加
		LOCALES.append(lang)
		# 翻訳データを読み込み
		with open(f, mode="r", encoding="utf-8") as f:
			locale_data[lang] = json.loads(f.read())
			#i18n.translations[lang] = f.read()
			#i18n.localizations[lang] = f.read()

	i18n = I18n(
		client,
		consider_user_locale=True,
		**locale_data
	)
	#print(i18n.current_locale)

load_localedata()
