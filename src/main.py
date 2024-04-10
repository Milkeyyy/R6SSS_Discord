import argparse
import json
import os
import sys
import traceback

import discord
from discord.commands import Option
from discord.ext import tasks

import heartbeat
import localizations
from logger import logger
import platform_icon
import serverstatus
import status_icon as status_icon_set
import status_indicator


# Botの名前
bot_name = "R6SSS"
# Botのバージョン
bot_version = "1.6.0"

default_embed = discord.Embed

default_guilddata_item = {"server_status_message": [0, 0, "en-GB"]} # チャンネルID, メッセージID]

default_guilddata_item = {
	"server_status_message": {
		"channel_id": 0,
		"message_id": 0,
		"language": "en-GB",
		"status_indicator": True
	}
}

db = {}

# 引数ぱーさー
parser = argparse.ArgumentParser()
args = parser.parse_args()

# くらいあんと
intents = None
client = discord.Bot(intents = intents)


# Bot起動時のイベント
@client.event
async def on_ready():
	print("---------------------------------------")
	print(f" {bot_name} - Version {bot_version}")
	print(f" using Pycord {discord.__version__}")
	print(f" Developed by Milkeyyy")
	print("---------------------------------------")
	print("")
	await client.change_presence(
		activity=discord.Game(
			name=f"Type /create | v{bot_version}"
		)
	)
	logger.info(f"{client.user} へログインしました！ (ID: {client.user.id})")

	# ハートビートのキーを読み込み
	heartbeat.load_keys()

	# 旧ギルドデータの変換処理を試行
	await convert_guilddata()

	# ギルドデータの確認を開始
	await load_guilddata()
	await check_guilddata()

	logger.info("サーバーステータスの定期更新開始")
	update_serverstatus.start()


# 関数
# ギルドデータの保存
async def save_guilddata():
	# グローバル変数宣言
	global db

	# 書き込み用にファイルを開く
	file = open("guilds.json", "w", encoding="utf-8")
	# 辞書をファイルへ保存
	file.write(json.dumps(db, indent=2, sort_keys=True))
	file.close()

	await load_guilddata()


# ギルドデータの読み込み
async def load_guilddata():
	# グローバル変数宣言
	global db

	try:  # ファイルが存在しない場合
		# ファイルを作成して初期データを書き込む
		file = open("guilds.json", "x", encoding="utf-8")
		file.write(json.dumps(db, indent=2, sort_keys=True))
		file.close()
		# ファイルから読み込む
		file = open("guilds.json", "r", encoding="utf-8")
		db = json.load(file)
		file.close()

	except FileExistsError:  # ファイルが存在する場合
		# ファイルから読み込む
		file = open("guilds.json", "r", encoding="utf-8")
		db = json.load(file)
		file.close()

# ギルドデータの確認
async def check_guilddata(guild = None):
	global default_guilddata_item

	logger.info("ギルドデータの確認開始")
	guilds = []
	if guild == None:
		guilds = client.guilds
	else:
		guilds = [guild]

	for guild in guilds:
		# すべてのギルドのデータが存在するかチェック、存在しないギルドがあればそのギルドのデータを作成する
		if db.get(str(guild.id)) == None:
			db[str(guild.id)] = default_guilddata_item

		# 各項目が存在するかチェック 存在しなければ追加する
		for k, v in default_guilddata_item.items():
			if db[str(guild.id)].get(k) == None or type(db[str(guild.id)].get(k)) != list:
				db[str(guild.id)][k] == v

	logger.info("ギルドデータの確認完了")

# 旧ギルドデータの変換
async def convert_guilddata():
	global default_guilddata_item

	try:
		# 旧ギルドデータが存在する場合は変換処理を実行する
		if os.path.exists("guild.json"):
			# ファイルの読み込み
			file = open("guild.json", "r", encoding="utf-8")
			old_gd = json.load(file)
			new_gd = {}
			file.close()

			for guild_id in old_gd.keys():
				new_gd[guild_id] = {"server_status_message": {}}
				new_gd[guild_id]["server_status_message"]["channel_id"] = old_gd[guild_id]["server_status_message"][0]
				new_gd[guild_id]["server_status_message"]["message_id"] = old_gd[guild_id]["server_status_message"][1]
				new_gd[guild_id]["server_status_message"]["language"] = old_gd[guild_id]["server_status_message"][2]
				new_gd[guild_id]["server_status_message"]["status_indicator"] = True

			# 書き込み用にファイルを開く
			file = open("guilds.json", "w", encoding="utf-8")
			# 辞書をファイルへ保存
			file.write(json.dumps(new_gd, indent=2, sort_keys=True))
			file.close()
			await load_guilddata()

	except Exception as e:
		logger.warning("ギルドデータの変換処理に失敗しました: " + str(e))


# 1分毎にサーバーステータスを更新する
serverstatus_loop_isrunning = False

@tasks.loop(seconds=180.0)
async def update_serverstatus():
	global serverstatus_loop_isrunning
	serverstatus_loop_isrunning = True

	# ハートビートを送信
	heartbeat.heartbeat.ping(state="complete")

	# Heartbeatイベントを送信 (サーバーステータスの更新が開始されたことを報告)
	heartbeat.monitor.ping(state="run", message="サーバーステータスの更新開始")

	logger.info("サーバーステータスの更新開始")

	try:
		await save_guilddata()

		# サーバーステータスを取得する
		status = await serverstatus.get()

		# サーバーステータスを更新する
		serverstatus.data = status

		# 各ギルドの埋め込みメッセージIDチェック、存在する場合はメッセージを更新する
		for guild in client.guilds:
			#logger.info(f"ギルド: {guild.name}")
			try:
				ch_id = int(db[str(guild.id)]["server_status_message"]["channel_id"])
				msg_id = int(db[str(guild.id)]["server_status_message"]["message_id"])
				loc = db[str(guild.id)]["server_status_message"]["language"]
			except Exception as e:
				logger.warning(f"ギルドデータ({guild.name}) の読み込み失敗")
				tb = sys.exc_info()
				logger.error(str(traceback.format_tb(tb)))
				db[str(guild.id)] = default_guilddata_item
				ch_id = db[str(guild.id)]["server_status_message"]["channel_id"]
				msg_id = db[str(guild.id)]["server_status_message"]["message_id"]
				loc = db[str(guild.id)]["server_status_message"]["language"]

			try:
				if ch_id != 0 and msg_id != 0 and loc != None:
					# IDからテキストチャンネルを取得する
					ch = client.get_channel(ch_id)
					# チャンネルが存在しない場合はギルドデータからチャンネルIDとメッセージIDを削除する
					if ch == None:
						db[str(guild.id)]["server_status_message"]["channel_id"] = 0
						db[str(guild.id)]["server_status_message"]["message_id"] = 0
						# ギルドデータを保存
						await save_guilddata()
						continue # ループを続ける

					ch_name = ch.name

					e = ""
					try:
						# 取得したテキストチャンネルからメッセージを取得する
						msg = await ch.fetch_message(msg_id)
					except discord.errors.NotFound as err:
						msg = None
						e = err

					if msg is None:
						logger.warning("ギルド " + guild.name + " のメッセージ(" + str(msg_id) + ")の取得に失敗")
						logger.warning(str(e))
						db[str(guild.id)] = default_guilddata_item
					else:
						# テキストチャンネルの名前にステータスインジケーターを設定
						try:
							if ch_name[0] in status_indicator.List: ch_name = ch_name[1:]
							if db[str(guild.id)]["server_status_message"]["status_indicator"] == True: await msg.channel.edit(name=serverstatus.indicator + ch_name)
						except Exception as e:
							logger.error(f"ギルド {guild.name} のステータスインジケーターの更新に失敗: {e}")

						await msg.edit(embeds=await generate_serverstatus_embed(loc))
			except Exception as e:
				tb = sys.exc_info()
				logger.error(f"ギルド {guild.name} のサーバーステータスメッセージ({str(msg_id)})の更新に失敗")
				logger.error(traceback.format_exc())
	except Exception as e:
		logger.error(traceback.format_exc())
		heartbeat.monitor.ping(state="fail", message="サーバーステータスの更新エラー: " + str(e))

	logger.info("サーバーステータスの更新完了")

	# Cronitorのモニターに成功したことを報告
	heartbeat.monitor.ping(state="complete", message="サーバーステータスの更新完了")

@update_serverstatus.after_loop
async def after_updateserverstatus():
	global serverstatus_loop_isrunning
	serverstatus_loop_isrunning = False
	logger.info("サーバーステータスの定期更新終了")
	if serverstatus_loop_isrunning == False: update_serverstatus.start()

# サーバーステータス埋め込みメッセージを更新
async def generate_serverstatus_embed(locale):
	pf_list = {
		"PC": ["PC", "PC", 2],
		"PS4": ["PS4", "PlayStation 4", 0],
		"PS5": ["PS5", "PlayStation 5", 1],
		"XB1": ["XBOXONE", "Xbox One", 0],
		"XBSX": ["XBOX SERIES X", "Xbox Series X/S", 1]
	}

	# 各プラットフォームの埋め込みメッセージの色
	color_list = {
		"PC": discord.Colour.from_rgb(255, 255, 255),
		"PS4": discord.Colour.from_rgb(0, 67, 156),
		"PS5": discord.Colour.from_rgb(0, 67, 156),
		"XB1": discord.Colour.from_rgb(16, 124, 16),
		"XBSX": discord.Colour.from_rgb(16, 124, 16)
	}

	embeds = []

	# 翻訳先言語を設定
	localizations.locale = locale

	# サーバーステータスを取得
	status = serverstatus.data

	# 各プラットフォームごとの埋め込みメッセージを作成
	embed = discord.Embed(color=color_list["PC"])
	embed.set_author(name="R6S Server Status", icon_url="https://www.google.com/s2/favicons?sz=64&domain_url=https://www.ubisoft.com/en-us/game/rainbow-six/siege/status")
	embed.set_footer(text=localizations.translate("Last Update") + ": " + status["_update_date"].strftime('%Y/%m/%d %H:%M:%S') + " (JST)")

	for k, v in pf_list.items():
		status_list = []

		pf_id = v[0] # PC, PS4, XB1...
		pf_display_name = v[1] # プラットフォームの表示名

		if pf_id.startswith("_"): continue
		# サーバーの状態によってアイコンを変更する
		# 問題なし
		if status[pf_id]["Status"]["Connectivity"] == "Operational":
			status_icon = status_icon_set.OPERATIONAL
		# 計画メンテナンス
		elif status[pf_id]["Status"]["Connectivity"] == "Maintenance":
			status_icon = status_icon_set.MAINTENANCE
		# 想定外の問題
		elif status[pf_id]["Status"]["Connectivity"] == "Interrupted":
			status_icon = status_icon_set.INTERRUPTED
		# 想定外の停止
		elif status[pf_id]["Status"]["Connectivity"] == "Degraded":
			status_icon = status_icon_set.DEGRADED
		# それ以外
		else:
			status_icon = status_icon_set.UNKNOWN

		connectivity_text = localizations.translate(status[pf_id]["Status"]["Connectivity"])

		mt_text = ""
		if status[pf_id]["Maintenance"] == True:
			status_icon = status_icon_set.MAINTENANCE
			connectivity_text = localizations.translate(localizations.translate("Maintenance"))

		f_list = []
		f_text = ""
		f_status_text = ""
		for f, s in status[pf_id]["Status"].items():
			if f == "Connectivity": continue
			# 通常
			f_status_icon = status_icon_set.OPERATIONAL
			f_status_text = localizations.translate(s)
			# 停止
			if s != "Operational":
				f_status_icon = status_icon_set.DEGRADED
			# メンテナンス
			if status[pf_id]["Maintenance"] == True:
				f_status_icon = status_icon_set.MAINTENANCE
			# 不明
			if s == "Unknown":
				f_status_icon = status_icon_set.UNKNOWN
				f_status_text = localizations.translate("Unknown")

			f_list.append("┣ **" + localizations.translate(f) + "**\n┣ " + f_status_icon + "`" + f_status_text + "`")

		f_text = "" + "\n".join(f_list)

		# 埋め込みメッセージにプラットフォームのフィールドを追加
		status_list.append(mt_text + f_text)

		# プラットフォームのステータスのフィールドを追加
		embed.add_field(
			name=platform_icon.LIST[v[0]] + " " + pf_display_name + " - " + status_icon + "`" + connectivity_text + "`",
			value="\n".join(status_list)
		)
		# 各プラットフォームごとに別の行にするために、リストで指定された数の空のフィールドを挿入する
		for i in range(v[2]):
			embed.add_field(name="", value="")

	embeds.append(embed)

	return embeds

# コマンド
@client.slash_command(description="サーバーステータスメッセージの言語を設定します。")
async def setlanguage(ctx,
	locale: Option(
		str,
		name="language",
		choices=localizations.locales,
		permission=discord.Permissions.administrator
	)
):
	global d

	logger.info(f"コマンド実行: setlanguage / 実行者: {ctx.user}")

	await ctx.defer(ephemeral=True)

	# ギルドデータをチェック
	await check_guilddata(ctx.guild)

	if locale in localizations.data["Locales"].values():
		db[str(ctx.guild.id)]["server_status_message"]["language"] = [k for k, v in localizations.data["Locales"].items() if v == locale][0]
	else:
		db[str(ctx.guild.id)]["server_status_message"]["language"] = "en-GB"

	# ギルドデータを保存
	await save_guilddata()

	await ctx.send_followup(content="サーバーステータスメッセージの言語を `" + localizations.data["Locales"][db[str(ctx.guild.id)]["server_status_message"]["language"]] + "` に設定しました。")

@client.slash_command(description="サーバーステータスインジケーターの表示を設定します。")
async def setindicator(ctx,
	enable: Option(
		bool,
		name="enable",
		permission=discord.Permissions.administrator
	)
):
	global db

	logger.info(f"コマンド実行: setindicator / 実行者: {ctx.user}")

	await ctx.defer(ephemeral=True)

	# ギルドデータをチェック
	await check_guilddata(ctx.guild)

	db[str(ctx.guild.id)]["server_status_message"]["status_indicator"] = enable

	# ギルドデータを保存
	await save_guilddata()

	await ctx.send_followup(content="サーバーステータスインジケーターの表示を `" + str(enable) + "` に設定しました。")

@client.slash_command(description="現在のサーバーステータスを送信します。このコマンドで送信されたサーバーステータスは自動更新されません。")
async def status(ctx):
	logger.info(f"コマンド実行: status / 実行者: {ctx.user}")

	await ctx.defer(ephemeral=False)
	try:
		await ctx.send_followup(embeds=await generate_serverstatus_embed(db[str(ctx.guild_id)]["server_status_message"]["language"]))
	except Exception as e:
		logger.error(traceback.format_exc())
		await ctx.send_followup(content="サーバーステータスメッセージの送信時にエラーが発生しました: `" + str(e) + "`")

@client.slash_command(description="毎分自動更新されるサーバーステータスメッセージを作成します。")
async def create(ctx,
	channel: Option(
		discord.TextChannel,
		required=False,
		name="textchannel",
		description="自動更新されるサーバーステータスを送信するテキストチャンネルを指定します。指定しない場合は現在のチャンネルへ作成されます。",
		permission=discord.Permissions.administrator
	)
):
	logger.info(f"コマンド実行: create / 実行者: {ctx.user}")

	await ctx.defer(ephemeral=True)

	try:
		# ギルドデータをチェック
		await check_guilddata(ctx.guild)

		additional_msg = ""
		if db[str(ctx.guild_id)]["server_status_message"]["message_id"] != 0:
			additional_msg = "\n(以前送信した古いメッセージは更新されなくなります。)"

		if channel is None:
			ch_id = ctx.channel_id
		else:
			ch_id = channel.id
		ch = client.get_channel(ch_id)

		# サーバーステータス埋め込みメッセージを送信
		try:
			msg = await ch.send(embeds=await generate_serverstatus_embed(db[str(ctx.guild_id)]["server_status_message"]["language"]))
		except Exception as e:
			if type(e) == discord.errors.ApplicationCommandInvokeError and str(e).endswith("Missing Permissions"):
				await ctx.send_followup(content="テキストチャンネル " + ch.mention + " へメッセージを送信する権限がありません！")
			else:
				logger.error(traceback.format_exc())
				await ctx.send_followup(content="サーバーステータスメッセージの作成時にエラーが発生しました: `" + str(e) + "`")
			return

		# 送信したチャンネルとメッセージのIDをギルドデータへ保存する
		db[str(ctx.guild_id)]["server_status_message"]["channel_id"] = ch_id
		db[str(ctx.guild_id)]["server_status_message"]["message_id"] = msg.id

		# ギルドデータを保存
		await save_guilddata()

		await ctx.send_followup(content="テキストチャンネル " + ch.mention + " へサーバーステータスメッセージを送信しました。\n以後このメッセージは自動的に更新されます。" + additional_msg)
	except Exception as e:
		logger.error(traceback.format_exc())
		await ctx.send_followup(content="サーバーステータスメッセージの送信時にエラーが発生しました: `" + str(e) + "`")

@client.slash_command(description="ボットのレイテンシーを送信します。")
async def ping(ctx):
	logger.info(f"コマンド実行: ping / 実行者: {ctx.user}")
	try:
		raw_ping = client.latency
		ping = round(raw_ping * 1000)
		ping_embed = discord.Embed(title="Pong!",description=f"Latency: **`{ping}`** ms",color=discord.Colour.from_rgb(79,168,254))
		await ctx.respond(embed=ping_embed)
	except Exception as e:
		logger.error(traceback.format_exc())
		await ctx.respond(content="コマンドの実行時にエラーが発生しました: `" + str(e) + "`")

@client.slash_command(description="このボットについての情報を送信します。")
async def about(ctx):
	logger.info(f"コマンド実行: about / 実行者: {ctx.user}")
	try:
		embed = discord.Embed(color=discord.Colour.blue())
		embed.set_author(name=bot_name, icon_url=client.user.display_avatar.url)
		embed.set_footer(text=f"Developed by Milkeyyy")
		embed.add_field(name="Version", value="`" + bot_version + "`")
		embed.add_field(name="Library", value=f"Pycord: `{discord.__version__}`")

		await ctx.respond(embed=embed)
	except Exception as e:
		logger.error(traceback.format_exc())
		await ctx.respond(content="コマンドの実行時にエラーが発生しました: `" + str(e) + "`")


# ログイン
try:
	# 言語データを読み込む
	localizations.load_localedata()
	# ログイン
	f = open('token.txt', 'r', encoding='UTF-8')
	client.run(f.read())
	f.close()
except Exception as e:
	logger.error(traceback.format_exc())
	#os.system("kill 1")
