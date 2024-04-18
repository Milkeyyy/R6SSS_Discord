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

	async def _convert_v1_guildconfig(item: dict) -> dict | None:
		if "info" not in item or "config" not in item:
			data = Box(GuildConfig.DEFAULT_DATA.copy())
			for k, v in item.items():
				if client.get_guild(int(k)) != None: # キー(ギルドのID)からギルドを取得して、存在するならギルドIDとみなして変換する
					data.config[str(k)] = v
			return data
		else:
			return None

	async def _check_dict_items(item: dict, default_items: dict) -> None:
		for k, v in default_items.items():
			if k not in item:
				item[k] = v
			if type(item[k]) == dict:
				await GuildConfig._check_dict_items(item[k], default_items[k])

	async def check_guild(id: int) -> None:
		# 渡されたIDのデータをチェック
		gid = str(id)
		if gid not in GuildConfig.data.config:
			await GuildConfig.create(gid)
		await GuildConfig._check_dict_items(GuildConfig.data.config[gid], GuildConfig.DEFAULT_GUILD_DATA)

	async def check() -> None:
		# コンフィグファイルの各ギルドの項目チェック
		for guild in client.guilds:
			gid = str(guild.id)
			if gid not in GuildConfig.data.config:
				await GuildConfig.create(gid)
			await GuildConfig._check_dict_items(GuildConfig.data.config[gid], GuildConfig.DEFAULT_GUILD_DATA)

	async def load() -> None:
		logger.info("ギルドコンフィグを読み込み")
		if path.isfile(GuildConfig.FILE_PATH): # ファイルが存在する場合
			# ファイルから読み込む
			GuildConfig.data = Box.from_json(filename=GuildConfig.FILE_PATH, encoding="utf-8")

			# v1以前のギルドコンフィグの変換
			cd = await GuildConfig._convert_v1_guildconfig(GuildConfig.data.to_dict())
			if cd != None:
				GuildConfig.data = cd
				GuildConfig.data.info.created_at = datetime.datetime.now(tz=datetime.timezone.utc).timestamp()

			# コンフィグファイルの項目チェック
			await GuildConfig._check_dict_items(GuildConfig.data, GuildConfig.DEFAULT_DATA)

		else: # ファイルが存在しない場合
			# 新しくギルドコンフィグを作成する
			GuildConfig.data = Box(GuildConfig.DEFAULT_DATA.copy())
			GuildConfig.data.info.created_at = datetime.datetime.now(tz=datetime.timezone.utc).timestamp()
			# ファイルへ保存する
			await GuildConfig.save()

		# 各項目のチェック
		await GuildConfig.check()

	async def save() -> None:
		logger.info("ギルドコンフィグを保存")
		GuildConfig.data.to_json(GuildConfig.FILE_PATH, encoding="utf-8", indent=2)

	async def create(gid: str) -> None:
		logger.info("ギルドコンフィグを作成: " + gid)
		GuildConfig.data.config[gid] = GuildConfig.DEFAULT_GUILD_DATA.copy()
		await GuildConfig.save()

	async def set(guild_id: int, keys: list, value: object) -> None:
		obj = GuildConfig.data.config[str(guild_id)]
		root = keys[len(keys)-1]
		keys.pop()
		for key in keys:
			obj = obj[key]
		obj[root] = value
		await GuildConfig.save()
