import json
import os
import traceback

from attrdict import AttrDict

from client import client
from db import GuildDB
from logger import logger


class GuildConfig:
	FILE_PATH: str = "./guilds.json"
	DEFAULT_DB_DATA: dict = {
		"guild_id": "",
		"config": {}
	}
	DEFAULT_GUILD_DATA: dict = {
		"server_status_message": {
			"channel_id": 0,
			"message_id": 0,
			"language": "en_GB",
			"status_indicator": True
		},
		"server_status_notification": {
			"channel_id": 0,
			"role_id": 0,
			"auto_delete": 10
		}
	}

	@classmethod
	def generate_default_guild_data(cls, guild_id: str) -> dict:
		"""初期ギルドコンフィグを生成して返す"""

		d = cls.DEFAULT_DB_DATA.copy()
		d["guild_id"] = guild_id
		d["config"] = cls.DEFAULT_GUILD_DATA.copy()
		return d

	@classmethod
	async def _check_dict_items(cls, item: dict, default_items: dict) -> dict:
		for k, v in default_items.copy().items():
			if k not in item:
				item[k] = v
			if isinstance(item[k], dict):
				await cls._check_dict_items(item[k], default_items[k])
		return item

	@classmethod
	async def check(cls) -> None:
		"""各ギルドのコンフィグをチェックする 存在しなければ新規作成する"""

		# コンフィグファイルの各ギルドの項目チェック
		for guild in client.guilds:
			gid = str(guild.id)
			gd = await GuildDB.col.find_one({"guild_id": gid})
			if gd is None:
				await cls.create(gid)

	@classmethod
	async def load(cls) -> None:
		"""ギルドコンフィグをデータベースから読み込んでチェックする"""

		logger.info("ギルドコンフィグを読み込み")

		# 今までのコンフィグファイルが存在する場合は読み込んでデータベースへ移行する
		try:
			if os.path.exists("./guilds.json"):
				logger.info("ギルドコンフィグをファイルから移行")
				with open("./guilds.json", "r", encoding="utf-8") as f:
					old_gc = json.loads(f.read())
				for gid, conf in old_gc["config"].items():
					logger.info("- ギルド: %s", str(gid))
					# データベースへ保存
					await cls.set(int(gid), conf)
				# ファイルをリネームする
				os.rename("./guilds.json", "./guilds_migrated.json")
		except Exception:
			logger.warning("ギルドコンフィグ移行エラー")
			logger.warning(traceback.format_exc())

		# 各項目のチェック
		await cls.check()

	@classmethod
	async def create(cls, guild_id: str) -> None:
		"""指定されたギルドIDのコンフィグを新規作成する"""

		logger.info("ギルドコンフィグを新規作成: %s", guild_id)
		await GuildDB.col.insert_one(cls.generate_default_guild_data(guild_id))

	@classmethod
	async def get(cls, guild_id: int) -> AttrDict | None:
		"""指定されたギルドIDのコンフィグを取得して返す"""

		logger.info("ギルドコンフィグを取得 - ID: %s", str(guild_id))

		# データベースから指定されたギルドIDに一致するコンフィグを取得する
		obj = await GuildDB.col.find_one({"guild_id": str(guild_id)})

		# 見つからない場合は初期値を新たに作成する
		if obj is None:
			await GuildDB.col.insert_one(cls.generate_default_guild_data(str(guild_id)))
			obj = await GuildDB.col.find_one({"guild_id": str(guild_id)})
			if obj is None:
				logger.warning("ギルドコンフィグ取得失敗: obj is None")
				return None

		return AttrDict(obj["config"])

	@classmethod
	async def set(cls, guild_id: int, value: dict) -> None:
		"""指定されたギルドIDのコンフィグを更新する"""

		result = await GuildDB.col.update_one(
			{"guild_id": str(guild_id)},
			{"$set": {"config": value}}
		)
		logger.info("ギルドコンフィグ更新 - ID: %s | Matched Count: %d", str(guild_id), result.matched_count)
