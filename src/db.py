from os import getenv
from sys import exit
import traceback

import pymongo
import pymongo.asynchronous.collection
import pymongo.asynchronous.database
import pymongo.collection
import pymongo.database

from logger import logger


class GuildDB:
	_client: pymongo.AsyncMongoClient
	db: pymongo.asynchronous.database.AsyncDatabase
	col: pymongo.asynchronous.collection.AsyncCollection

	@classmethod
	async def connect(cls) -> None:
		"""データベースへ接続する"""

		try:
			# 接続する
			logger.info("データベースへ接続")
			cls._client = pymongo.AsyncMongoClient(
				host=getenv("DB_URI")
			)
			await cls._client.aconnect()
			# データベース/コレクションを取得
			logger.info("- データベースを取得: %s", getenv("DB_DATABASE"))
			cls.db = cls._client.get_database(getenv("DB_DATABASE"))
			cls.col = cls.db.get_collection(getenv("DB_COLLECTION"))
		except Exception:
			logger.error("データベース接続失敗")
			logger.error(traceback.format_exc())
			exit(1)

