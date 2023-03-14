import argparse
import json
import logging
import os
import sys
import traceback

import discord
from discord.commands import Option
from discord.ext import tasks

import heartbeat
import localizations
import serverstatus
import statusicon
import statusindicator

logging.basicConfig(level=logging.INFO)
logging.basicConfig(level=logging.WARNING)

# Botの名前
bot_name = "R6SSS"
# Botのバージョン
bot_version = "1.4.1"

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

# 言語データを読み込む
localizations.loadLocaleData()

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
			name=f"Type /create | Version {bot_version}"
		)
	)
	logging.info(f"{client.user} へログインしました！ (ID: {client.user.id})")

	# ハートビートのキーを読み込み
	heartbeat.loadKeys()

	# 旧ギルドデータの変換処理を試行
	await convertGuildData()

	# ギルドデータの確認を開始
	await loadGuildData()
	await checkGuildData()

	logging.info("サーバーステータスの定期更新開始")
	updateserverstatus.start()


# 関数
# ギルドデータの保存
async def saveGuildData():
	# グローバル変数宣言
	global db

	# 書き込み用にファイルを開く
	file = open("guilds.json", "w", encoding="utf-8")
	# 辞書をファイルへ保存
	file.write(json.dumps(db, indent=2, sort_keys=True))
	file.close()

	await loadGuildData()


# ギルドデータの読み込み
async def loadGuildData():
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
async def checkGuildData(guild = None):
	global default_guilddata_item

	logging.info("ギルドデータの確認開始")
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

	logging.info("ギルドデータの確認完了")

# 旧ギルドデータの変換
async def convertGuildData():
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
			await loadGuildData()

	except Exception as e:
		logging.warning("ギルドデータの変換処理に失敗しました: " + str(e))


# 1分毎にサーバーステータスを更新する
serverstatus_loop_isrunning = False

@tasks.loop(seconds=60.0)
async def updateserverstatus():
	global serverstatus_loop_isrunning
	serverstatus_loop_isrunning = True

	# ハートビートを送信
	heartbeat.heartbeat.ping(state="complete")

	# Heartbeatイベントを送信 (サーバーステータスの更新が開始されたことを報告)
	heartbeat.monitor.ping(state="run", message="サーバーステータスの更新開始")

	logging.info("サーバーステータスの更新開始")

	try:
		await saveGuildData()

		# サーバーステータスを取得する
		status = await serverstatus.get()

		# サーバーステータスを更新する
		serverstatus.data = status

		# 各ギルドの埋め込みメッセージIDチェック、存在する場合はメッセージを更新する
		for guild in client.guilds:
			#logging.info(f"ギルド: {guild.name}")
			try:
				ch_id = int(db[str(guild.id)]["server_status_message"]["channel_id"])
				msg_id = int(db[str(guild.id)]["server_status_message"]["message_id"])
				loc = db[str(guild.id)]["server_status_message"]["language"]
			except Exception as e:
				logging.warning(f"ギルドデータ({guild.name}) の読み込み失敗")
				tb = sys.exc_info()
				logging.error(str(traceback.format_tb(tb)))
				db[str(guild.id)] = default_guilddata_item
				ch_id = db[str(guild.id)]["server_status_message"]["channel_id"]
				msg_id = db[str(guild.id)]["server_status_message"]["message_id"]
				loc = db[str(guild.id)]["server_status_message"]["language"]

			try:
				if ch_id != 0 and msg_id != 0 and loc != None:
					# IDからテキストチャンネルを取得する
					ch = client.get_channel(ch_id)
					ch_name = ch.name

					e = ""
					try:
						# 取得したテキストチャンネルからメッセージを取得する
						msg = await ch.fetch_message(msg_id)
					except discord.errors.NotFound as err:
						msg = None
						e = err

					if msg is None:
						logging.warning("ギルド " + guild.name + " のメッセージ(" + str(msg_id) + ")の取得に失敗")
						logging.warning(str(e))
						db[str(guild.id)] = default_guilddata_item
					else:
						# テキストチャンネルの名前にステータスインジケーターを設定
						try:
							if ch_name[0] in statusindicator.List: ch_name = ch_name[1:]
							if db[str(guild.id)]["server_status_message"]["status_indicator"] == True: await msg.channel.edit(name=serverstatus.indicator + ch_name)
						except Exception as e:
							logging.error(f"ギルド {guild.name} のステータスインジケーターの更新に失敗: {e}")

						await msg.edit(embeds=await generateserverstatusembed(loc))
			except Exception as e:
				tb = sys.exc_info()
				logging.error(f"ギルド {guild.name} のサーバーステータスメッセージ({str(msg_id)})の更新に失敗")
				logging.error(traceback.format_exc())
	except Exception as e:
		logging.error(traceback.format_exc())
		heartbeat.monitor.ping(state="fail", message="サーバーステータスの更新エラー: " + str(e))

	logging.info("サーバーステータスの更新完了")

	# Cronitorのモニターに成功したことを報告
	heartbeat.monitor.ping(state="complete", message="サーバーステータスの更新完了")

@updateserverstatus.after_loop
async def after_updateserverstatus():
	global serverstatus_loop_isrunning
	serverstatus_loop_isrunning = False
	logging.info("サーバーステータスの定期更新終了")
	if serverstatus_loop_isrunning == False: updateserverstatus.start()

# サーバーステータス埋め込みメッセージを更新
async def generateserverstatusembed(locale):
	embeds = []
	pf_list = {"PC": ["PC"], "PlayStation": ["PS4"], "Xbox": ["XBOXONE"]}

	# 翻訳先言語を設定
	localizations.locale = locale

	# 各プラットフォームの埋め込みメッセージの色
	color_list = {"PC": discord.Colour.from_rgb(255, 255, 255), "PlayStation": discord.Colour.from_rgb(0, 67, 156), "Xbox": discord.Colour.from_rgb(16, 124, 16)}

	# サーバーステータスを取得
	status = serverstatus.data

	# 各プラットフォームごとの埋め込みメッセージを作成
	for pf in pf_list:
		embed = discord.Embed(color=color_list[pf])
		embed.set_author(name=pf + " | R6S Server Status", icon_url="https://www.google.com/s2/favicons?sz=64&domain_url=https://www.ubisoft.com/en-us/game/rainbow-six/siege/status")
		embed.set_footer(text=localizations.translate("Last Update") + ": " + status["_update_date"].strftime('%Y/%m/%d %H:%M:%S') + " (JST)")

		for p in pf_list[pf]:
			if p.startswith("_"): continue

			# サーバーの状態によってアイコンを変更する
			# 問題なし
			if status[p]["Status"]["Connectivity"] == "Operational":
				status_icon = statusicon.Operational
			# 計画メンテナンス
			elif status[p]["Status"]["Connectivity"] == "Maintenance":
				status_icon = statusicon.Maintenance
			# 想定外の問題
			elif status[p]["Status"]["Connectivity"] == "Interrupted":
				status_icon = statusicon.Interrupted
			# 想定外の停止
			elif status[p]["Status"]["Connectivity"] == "Degraded":
				status_icon = statusicon.Degraded
			# それ以外
			else:
				status_icon = statusicon.Unknown

			connectivity_text = localizations.translate(status[p]["Status"]["Connectivity"])

			mt_text = ""
			if status[p]["Maintenance"] == True:
				status_icon = statusicon.Maintenance
				connectivity_text = localizations.translate(localizations.translate("Maintenance"))

			f_list = []
			f_text = ""
			f_status_text = ""
			for f, s in status[p]["Status"].items():
				if f == "Connectivity": continue
				# 通常
				f_status_icon = statusicon.Operational
				f_status_text = localizations.translate(s)
				# 停止
				if s != "Operational":
					f_status_icon = statusicon.Degraded
				# メンテナンス
				if status[p]["Maintenance"] == True:
					f_status_icon = statusicon.Maintenance
				# 不明
				if s == "Unknown":
					f_status_icon = statusicon.Unknown
					f_status_text = localizations.translate("Unknown")

				f_list.append("┣━ **" + localizations.translate(f) + "**\n┣━ " + f_status_icon + "`" + f_status_text + "`")

			f_text = "" + "\n".join(f_list)

			# 埋め込みメッセージにプラットフォームのフィールドを追加
			embed.add_field(name=status_icon + " **" + localizations.translate("Connectivity") + "** - `" + connectivity_text + "`", value=mt_text + f_text)

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
	global db

	logging.info(f"コマンド実行: setlanguage / 実行者: {ctx.user}")

	await ctx.defer(ephemeral=True)

	# ギルドデータをチェック
	await checkGuildData(ctx.guild)

	if locale in localizations.data["Locales"].values():
		db[str(ctx.guild.id)]["server_status_message"]["language"] = [k for k, v in localizations.data["Locales"].items() if v == locale][0]
	else:
		db[str(ctx.guild.id)]["server_status_message"]["language"] = "en-GB"

	# ギルドデータを保存
	await saveGuildData()

	await ctx.send_followup(content="サーバーステータスメッセージの言語を `" + locale + "` に設定しました。")

@client.slash_command(description="サーバーステータスインジケーターの表示を設定します。")
async def setindicator(ctx,
	enable: Option(
		bool,
		name="enable",
		permission=discord.Permissions.administrator
	)
):
	global db

	logging.info(f"コマンド実行: setindicator / 実行者: {ctx.user}")

	await ctx.defer(ephemeral=True)

	# ギルドデータをチェック
	await checkGuildData(ctx.guild)

	db[str(ctx.guild.id)]["server_status_message"]["status_indicator"] = enable

	# ギルドデータを保存
	await saveGuildData()

	await ctx.send_followup(content="サーバーステータスインジケーターの表示を `" + str(enable) + "` に設定しました。")

@client.slash_command(description="現在のサーバーステータスを送信します。このコマンドで送信されたサーバーステータスは自動更新されません。")
async def status(ctx):
	logging.info(f"コマンド実行: status / 実行者: {ctx.user}")

	await ctx.defer(ephemeral=True)
	try:
		await ctx.send_followup(embeds=await generateserverstatusembed(db[str(ctx.guild_id)]["server_status_message"]["language"]))
	except Exception as e:
		logging.error(traceback.format_exc())
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
	logging.info(f"コマンド実行: create / 実行者: {ctx.user}")

	await ctx.defer(ephemeral=True)

	try:
		# ギルドデータをチェック
		await checkGuildData(ctx.guild)

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
			msg = await ch.send(embeds=await generateserverstatusembed(db[str(ctx.guild_id)]["server_status_message"]["language"]))
		except Exception as e:
			if type(e) == discord.errors.ApplicationCommandInvokeError and str(e).endswith("Missing Permissions"):
				await ctx.send_followup(content="テキストチャンネル " + ch.mention + " へメッセージを送信する権限がありません！")
			else:
				logging.error(traceback.format_exc())
				await ctx.send_followup(content="サーバーステータスメッセージの作成時にエラーが発生しました: `" + str(e) + "`")
			return

		# 送信したチャンネルとメッセージのIDをギルドデータへ保存する
		db[str(ctx.guild_id)]["server_status_message"]["channel_id"] = ch_id
		db[str(ctx.guild_id)]["server_status_message"]["message_id"] = msg.id

		# ギルドデータを保存
		await saveGuildData()

		await ctx.send_followup(content="テキストチャンネル " + ch.mention + " へサーバーステータスメッセージを送信しました。\n以後このメッセージは自動的に更新されます。" + additional_msg)
	except Exception as e:
		logging.error(traceback.format_exc())
		await ctx.send_followup(content="サーバーステータスメッセージの送信時にエラーが発生しました: `" + str(e) + "`")

@client.slash_command(description="ボットのレイテンシーを送信します。")
async def ping(ctx):
	logging.info(f"コマンド実行: ping / 実行者: {ctx.user}")
	try:
		raw_ping = client.latency
		ping = round(raw_ping * 1000)
		ping_embed = discord.Embed(title="Pong!",description=f"Latency: **`{ping}`** ms",color=discord.Colour.from_rgb(79,168,254))
		await ctx.respond(embed=ping_embed)
	except Exception as e:
		logging.error(traceback.format_exc())
		await ctx.respond(content="コマンドの実行時にエラーが発生しました: `" + str(e) + "`")

@client.slash_command(description="このボットについての情報を送信します。")
async def about(ctx):
	logging.info(f"コマンド実行: about / 実行者: {ctx.user}")
	try:
		embed = discord.Embed(color=discord.Colour.blue())
		embed.set_author(name=bot_name, icon_url=client.user.display_avatar.url)
		embed.set_footer(text=f"Developed by Milkeyyy#0625")
		embed.add_field(name="Version", value="`" + bot_version + "`")
		embed.add_field(name="Library", value=f"Pycord: `{discord.__version__}`")

		await ctx.respond(embed=embed)
	except Exception as e:
		logging.error(traceback.format_exc())
		await ctx.respond(content="コマンドの実行時にエラーが発生しました: `" + str(e) + "`")


# ログイン
try:
	f = open('token.txt', 'r', encoding='UTF-8')
	client.run(f.read())
	f.close()
except Exception as e:
	logging.error(traceback.format_exc())
	#os.system("kill 1")
