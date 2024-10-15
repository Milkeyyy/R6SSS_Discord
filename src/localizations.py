from glob import glob
import json
import os
from os import path

from pycord.i18n import I18n

from client import client
from logger import logger


locale = "ja-JP"
#LOCALES: list


def load_localedata() -> None:
	global i18n
	global LOCALE_DATA

	# 言語一覧
	LOCALE_DATA = {}

	# 言語ファイルを読み込む
	logger.info("言語ファイルを読み込み")
	logger.info("- %s", os.getcwd())
	for f in glob("./locales/*.json"):
		lang = path.splitext(path.basename(f))[0]
		logger.info("- " + lang)
		# 翻訳データを読み込み
		with open(f, mode="r", encoding="utf-8") as f:
			LOCALE_DATA[lang] = json.loads(f.read())
			#i18n.translations[lang] = f.read()
			#i18n.localizations[lang] = f.read()

	i18n = I18n(
		client,
		consider_user_locale=True,
		**LOCALE_DATA
	)
	#print(i18n.current_locale)

def translate(text: str, lang: str="en_GB") -> str:
	global LOCALE_DATA

	try:
		return LOCALE_DATA[lang]["strings"][text]
	except KeyError as e:
		return text

load_localedata()
