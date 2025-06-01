from os import getenv
import sys
import traceback

import pymongo
import pymongo.asynchronous.collection
import pymongo.asynchronous.database
import pymongo.collection
import pymongo.database

from logger import logger


class DBManager:
	_client: pymongo.AsyncMongoClient
	db: pymongo.asynchronous.database.AsyncDatabase
	col: pymongo.asynchronous.collection.AsyncCollection

	@classmethod
	async def connect(cls) -> None:
		"""データベースへ接続する"""

		try:
			# データベース情報が設定されているかチェックする
			db_uri = getenv("MTSCHED_DB_URI")
			db_name = getenv("MTSCHED_DB_DATABASE")
			db_collection = getenv("MTSCHED_DB_COLLECTION")
			db_settings = (db_uri, db_name, db_collection)
			# 1つでも設定されていないものがある場合はエラーを出力して終了する
			if not all(db_settings):
				logger.error("データベース接続失敗")
				_ = [logger.error("- 環境変数 %s が設定されていません", e) if e else "" for e in db_settings]
				sys.exit(1)

			# 接続する
			logger.info("データベースへ接続")
			cls._client = pymongo.AsyncMongoClient(
				host=getenv("MTSCHED_DB_URI")
			)
			await cls._client.aconnect()

			# データベース/コレクションを取得
			logger.info("- データベースを取得: %s", db_name)
			cls.db = cls._client.get_database(db_name)
			cls.col = cls.db.get_collection(db_collection)
		except Exception:
			logger.error("データベース接続失敗")
			logger.error(traceback.format_exc())
			sys.exit(1)
