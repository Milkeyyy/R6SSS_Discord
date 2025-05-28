import json
from os import path
from typing import get_args

from pycord.i18n import I18n, Locale

from client import client
from logger import logger


locale = "ja-JP"

def load_localedata() -> None:
	global i18n
	global LOCALE_DATA
	global EXISTS_LOCALE_LIST

	# 言語一覧
	LOCALE_DATA = {}
	EXISTS_LOCALE_LIST = []

	# 言語ファイルを読み込む
	logger.info("言語ファイルを読み込み")
	for lang in get_args(Locale):
		# 言語ファイルのフォルダー
		lang_file_base_path = "./locales"
		# - を _ へ置き換える
		lang = lang.replace("-", "_")
		# 言語ファイルのパス
		lang_file_path = path.join(lang_file_base_path, lang + ".json")
		# 対象の言語ファイルが存在するかチェック
		if not path.exists(lang_file_path):
			# ファイルが存在しない場合は英語 (en_GB) のファイルを読み込むようにする (フォールバック
			logger.info("- %s -> en_GB (フォールバック)", lang)
			lang_file_path = path.join(lang_file_base_path, "en_GB.json")
		else:
			logger.info("- %s", lang)
			EXISTS_LOCALE_LIST.append(lang)
		# 翻訳データを読み込む
		with open(lang_file_path, mode="r", encoding="utf-8") as lang_file:
			LOCALE_DATA[lang] = json.loads(lang_file.read())

	i18n = I18n(
		client,
		consider_user_locale=True,
		**LOCALE_DATA
	)

def translate(text: str, values: list = [], lang: str="en_GB") -> str:
	global LOCALE_DATA

	try:
		return LOCALE_DATA[lang]["strings"][text].format(values)
	except KeyError as e:
		logger.error("Translate KeyError: %s", str(e))
		return text

_ = translate

load_localedata()
