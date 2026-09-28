import asyncio
import sys
import traceback
from os import getenv

import pymongo
import pymongo.asynchronous.collection
import pymongo.asynchronous.database

from logger import logger


class DBManager:
	_client: pymongo.AsyncMongoClient
	db: pymongo.asynchronous.database.AsyncDatabase
	col: pymongo.asynchronous.collection.AsyncCollection
	counters_col: pymongo.asynchronous.collection.AsyncCollection
	"""統計の日次カウンタ (stats_counters)"""
	guilds_col: pymongo.asynchronous.collection.AsyncCollection
	"""統計のギルド情報 (stats_guilds)"""
	events_col: pymongo.asynchronous.collection.AsyncCollection
	"""統計のギルド参加/脱退履歴 (stats_guild_events)"""
	snapshots_col: pymongo.asynchronous.collection.AsyncCollection
	"""統計のヘルス・推移スナップショット (stats_snapshots)"""
	connected: bool = False
	connected_event: asyncio.Event = asyncio.Event()
	"""データベースの接続完了を通知するイベント"""

	@classmethod
	async def connect(cls) -> None:
		"""データベースへ接続する"""
		try:
			# データベース情報が設定されているかチェックする
			db_uri = getenv("DB_URI")
			db_name = getenv("DB_DATABASE")
			db_collection = getenv("DB_COLLECTION")
			db_settings = (db_uri, db_name, db_collection)
			# 1つでも設定されていないものがある場合はエラーを出力して終了する
			if not all(db_settings):
				logger.error("データベース接続失敗")
				for e in db_settings:
					if not e or e == "":
						logger.error("- 環境変数 %s が設定されていません", e)
				sys.exit(1)

			# 接続する
			logger.info("データベースへ接続")
			cls._client = pymongo.AsyncMongoClient(host=db_uri)
			await cls._client.aconnect()

			# データベース/コレクションを取得
			logger.info("- データベースを取得: %s", db_name)
			cls.db = cls._client.get_database(db_name)
			cls.col = cls.db.get_collection(db_collection)
			cls.counters_col = cls.db.get_collection("stats_counters")
			cls.guilds_col = cls.db.get_collection("stats_guilds")
			cls.events_col = cls.db.get_collection("stats_guild_events")
			cls.snapshots_col = cls.db.get_collection("stats_snapshots")

			# 接続完了通知
			cls.connected = True
			cls.connected_event.set()

			# 統計用コレクションのインデックスを作成する
			await cls.ensure_indexes()
		except Exception:
			logger.error("データベース接続失敗")
			logger.error(traceback.format_exc())
			sys.exit(1)

	@classmethod
	async def ensure_indexes(cls) -> None:
		"""統計用コレクションのインデックスを作成する

		インデックスの作成に失敗しても警告ログのみを出力して起動を継続する
		"""
		# (コレクション, コレクション名, キー, オプション)
		index_definitions = [
			(cls.counters_col, "stats_counters", [("date", 1), ("metric", 1), ("dim1", 1), ("dim2", 1)], {"unique": True}),
			(cls.guilds_col, "stats_guilds", [("guild_id", 1)], {"unique": True}),
			(cls.guilds_col, "stats_guilds", [("is_active", 1)], {}),
			(cls.events_col, "stats_guild_events", [("occurred_at", -1)], {}),
			(cls.snapshots_col, "stats_snapshots", [("captured_at", -1)], {}),
			# 180日 (15552000秒) で期限切れにする TTL インデックス
			(cls.snapshots_col, "stats_snapshots", [("captured_at", 1)], {"expireAfterSeconds": 15552000}),
		]

		for collection, collection_name, keys, options in index_definitions:
			try:
				await collection.create_index(keys, **options)
			except Exception:
				logger.warning("インデックスの作成に失敗 - コレクション: %s | キー: %s", collection_name, str(keys))
				logger.warning(traceback.format_exc())

		logger.info("統計用コレクションのインデックスを確認")
