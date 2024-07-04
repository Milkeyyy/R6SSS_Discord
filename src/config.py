import datetime
from os import path

from box import Box

from client import client
from logger import logger


class GuildConfig:
	FILE_PATH: str = "./guilds.json"
	DEFAULT_DATA: dict = {
		"info": {
			"created_at": ""
		},
		"config": {}
	}
	DEFAULT_GUILD_DATA: dict = {
		"server_status_message": {
			"channel_id": 0,
			"message_id": 0,
			"language": "en-GB",
			"status_indicator": True
		},
		"server_status_notification": {
			"channel_id": 0,
			"role_id": 0
		}
	}

	data: Box

	@classmethod
	async def _convert_v1_guildconfig(cls, item: dict) -> dict | None:
		if "info" not in item or "config" not in item:
			data = Box(cls.DEFAULT_DATA.copy())
			for k, v in item.items():
				if client.get_guild(int(k)) != None: # キー(ギルドのID)からギルドを取得して、存在するならギルドIDとみなして変換する
					data.config[str(k)] = v
			return data
		else:
			return None

	@classmethod
	async def _check_dict_items(cls, item: dict, default_items: dict) -> None:
		for k, v in default_items.items():
			if k not in item:
				item[k] = v
			if type(item[k]) == dict:
				await cls._check_dict_items(item[k], default_items[k])

	@classmethod
	async def check_guild(cls, id: int) -> None:
		# 渡されたIDのデータをチェック
		gid = str(id)
		if gid not in cls.data.config:
			await cls.create(gid)
		await cls._check_dict_items(cls.data.config[gid], cls.DEFAULT_GUILD_DATA)

	@classmethod
	async def check(cls) -> None:
		# コンフィグファイルの各ギルドの項目チェック
		for guild in client.guilds:
			gid = str(guild.id)
			if gid not in cls.data.config:
				await cls.create(gid)
			await cls._check_dict_items(cls.data.config[gid], cls.DEFAULT_GUILD_DATA)

	@classmethod
	async def load(cls) -> None:
		logger.info("ギルドコンフィグを読み込み")
		if path.isfile(cls.FILE_PATH): # ファイルが存在する場合
			# ファイルから読み込む
			cls.data = Box.from_json(filename=cls.FILE_PATH, encoding="utf-8")

			# v1以前のギルドコンフィグの変換
			cd = await cls._convert_v1_guildconfig(cls.data.to_dict())
			if cd != None:
				cls.data = cd
				cls.data.info.created_at = datetime.datetime.now(tz=datetime.timezone.utc).timestamp()

			# コンフィグファイルの項目チェック
			await cls._check_dict_items(cls.data, cls.DEFAULT_DATA)

		else: # ファイルが存在しない場合
			# 新しくギルドコンフィグを作成する
			cls.data = Box(cls.DEFAULT_DATA.copy())
			cls.data.info.created_at = datetime.datetime.now(tz=datetime.timezone.utc).timestamp()
			# ファイルへ保存する
			await cls.save()

		# 各項目のチェック
		await cls.check()

	@classmethod
	async def save(cls) -> None:
		logger.info("ギルドコンフィグを保存")
		cls.data.to_json(cls.FILE_PATH, encoding="utf-8", indent=2)

	@classmethod
	async def create(cls, gid: str) -> None:
		logger.info("ギルドコンフィグを作成: " + gid)
		cls.data.config[gid] = cls.DEFAULT_GUILD_DATA.copy()
		await cls.save()

	@classmethod
	async def set(cls, guild_id: int, keys: list, value: object) -> None:
		obj = cls.data.config[str(guild_id)]
		root = keys[len(keys)-1]
		keys.pop()
		for key in keys:
			obj = obj[key]
		obj[root] = value
		await cls.save()
