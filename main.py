from keep_alive import keep_alive

import argparse
import datetime
import json
import logging
import os
import sys
from time import sleep

import discord
from discord.commands import Option
from discord.ext import tasks
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

logging.basicConfig(level=logging.INFO)
logging.basicConfig(level=logging.WARNING)

# Botの名前
bot_name = "R6SSS"
# Botのバージョン
bot_version = "1.0.0"

# サーバーステータス辞書
server_status = {"pc": {"status": "-----"}, "psn": {"status": "-----"}, "xbox": {"status": "-----"}}

server_status_embed = discord.Embed

guilddata = {}
default_guilddata_item = {"server_status_message": [0, 0]} # チャンネルID, メッセージID

# 引数ぱーさー
parser = argparse.ArgumentParser()
parser.add_argument(
	"--token",
	help="Botのトークン (使用法: --token ここにトークンを挿入)",
	type=str,
	required=False
)
parser.add_argument(
	"--statuslanguage",
	help="Server Status Language (ja-jp/en-us)",
	type=str,
	required=False
)
args = parser.parse_args()

# トークンを取得する
#token = ""
# トークンが指定されていない場合はエラーを発生させる
#if args.token is None:
#	if os.getenv("TOKEN") is None:
#		logging.error("トークンが指定されていません！")
#		sys.exit(1)
#	else:
#		token = os.getenv("TOKEN")
#else:
#	token = args.token

# ステータスメッセージの言語が指定されていないまたは正しく指定されていない場合は日本語に設定する
if args.statuslanguage is None:
	status_language = "ja-jp"
elif args.statuslanguage != "ja-jp" and args.statuslanguage != "en-us":
	status_language = "ja-jp"
else:
	status_language = args.statuslanguage

# サーバーステータスページのURL
status_url = f"https://www.ubisoft.com/{status_language}/game/rainbow-six/siege/status"

# くらいあんと
intents = discord.Intents.all()
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
	logging.info(f"{client.user} へログインしました！ (ID: {client.user.id})")

	# ギルドデータの確認を開始
	checkGuildData()

	logging.info("サーバーステータスの定期更新開始")
	updateserverstatus.start()


# 関数
# ギルドデータの保存
def saveGuildData():
	# グローバル変数宣言
	global guilddata

	# 書き込み用にファイルを開く
	file = open("guild.json", "w", encoding="utf-8")
	# 辞書をファイルへ保存
	file.write(json.dumps(guilddata, indent=2, sort_keys=True))
	file.close()
	loadGuildData()


# ギルドデータの読み込み
def loadGuildData():
	# グローバル変数宣言
	global guilddata

	try:  # ファイルが存在しない場合
		# ファイルを作成して初期データを書き込む
		file = open("guild.json", "x", encoding="utf-8")
		file.write(json.dumps(guilddata, indent=2, sort_keys=True))
		file.close()
		# ファイルから読み込む
		file = open("guild.json", "r", encoding="utf-8")
		guilddata = json.load(file)
		file.close()

	except FileExistsError:  # ファイルが存在する場合
		# ファイルから読み込む
		file = open("guild.json", "r", encoding="utf-8")
		guilddata = json.load(file)
		file.close()

# ギルドデータの確認
def checkGuildData():
	global guilddata
	global default_guilddata_item

	loadGuildData()

	logging.info("ギルドデータの確認開始")
	for guild in client.guilds:
		# すべてのギルドのデータが存在するかチェック、存在しないギルドがあればそのギルドのデータを作成する
		if guilddata.get(str(guild.id)) == None:
			guilddata[str(guild.id)] = default_guilddata_item

	saveGuildData()
	logging.info("ギルドデータの確認完了")


# 1分毎にサーバーステータスを更新する
@tasks.loop(seconds=60.0)
async def updateserverstatus():
	global guilddata
	global server_status
	global server_status_embed

	logging.info("サーバーステータスの更新開始")

	# サーバーステータスを取得する
	status = await getserverstatus()

	# サーバーステータスを更新する
	server_status = status

	# 埋め込みメッセージを更新する
	await updateserverstatusembed()

	# 各ギルドの埋め込みメッセージIDチェック、存在する場合はメッセージを更新する
	for guild in client.guilds:
		try:
			ch_id = int(guilddata[str(guild.id)]["server_status_message"][0])
			msg_id = int(guilddata[str(guild.id)]["server_status_message"][1])
		except KeyError as e:
			logging.warning(f"ギルド {guild.name} のデータが見つかりませんでした")
			logging.warning(e)
			guilddata[str(guild.id)]["server_status_message"] = [0, 0]
		if ch_id != 0 and msg_id != 0:
			ch = client.get_channel(ch_id) # IDからテキストチャンネルを取得する
			msg = await ch.fetch_message(msg_id) # 取得したテキストチャンネルからメッセージを取得する
			if msg is None:
				logging.warning("ギルド " + guild.name + " のメッセージ " + str(msg_id) + " の更新に失敗")
				guilddata[str(guild.id)]["server_status_message"] = [0, 0]
			else:
				await msg.edit(embed=server_status_embed)

	saveGuildData()

	logging.info("サーバーステータスの更新完了")

@updateserverstatus.after_loop
async def after_updateserverstatus():
	logging.info("サーバーステータスの定期更新終了")

# サーバーステータスを取得する
async def getserverstatus():
	base_path = '/html/body/div[1]/main/div/div/div[1]/div/ul'

	chrome_options = Options()
	chrome_options.add_argument('--no-sandbox')
	chrome_options.add_argument('--disable-dev-shm-usage')

	# ウィンドウを表示しない
	chrome_options.add_argument("--headless")

	driver = webdriver.Chrome(options=chrome_options)

	#driver = webdriver.Chrome("chromedriver_win32\chromedriver", options=chrome_options)

	driver.get(status_url)

	# ステータスが読み込まれるまで待機する
	wait = WebDriverWait(driver, 20)
	wait.until(EC.visibility_of_element_located((By.XPATH, '/html/body/div[1]/main/div/div/div[1]/div/ul[1]/li[1]/span/small')))

	# 全プラットフォームのステータスを表示(展開)する
	driver.find_element(By.XPATH, '/html/body/div[1]/main/div/div/div[1]/div/div[1]/button').click()
	# 全プラットフォームのステータスが展開されるまで待機する
	wait.until(EC.visibility_of_element_located((By.XPATH, base_path + '[1]/li[2]/p/small')))

	status = {"pc": {}, "psn": {}, "xbox": {}}

	# サーバーステータスを取得
	# PC
	status["pc"]["status"] = ["PC", driver.find_element(By.XPATH, base_path + '[1]/li[1]/span/small').text]
	status["pc"]["connectivity"] = [driver.find_element(By.XPATH, base_path + '[1]/li[2]/h4').text, driver.find_element(By.XPATH, base_path + '[1]/li[2]/p/small').text]
	status["pc"]["authentication"] = [driver.find_element(By.XPATH, base_path + '[1]/li[3]/h4').text, driver.find_element(By.XPATH, base_path + '[1]/li[3]/p/small').text]
	status["pc"]["store"] = [driver.find_element(By.XPATH, base_path + '[1]/li[4]/h4').text, driver.find_element(By.XPATH, base_path + '[1]/li[4]/p/small').text]
	status["pc"]["matchmaking"] = [driver.find_element(By.XPATH, base_path + '[1]/li[5]/h4').text, driver.find_element(By.XPATH, base_path + '[1]/li[5]/p/small').text]

	# PSN
	status["psn"]["status"] = ["PSN", driver.find_element(By.XPATH, base_path + '[2]/li[1]/span/small').text]
	status["psn"]["connectivity"] = [driver.find_element(By.XPATH, base_path + '[2]/li[2]/h4').text, driver.find_element(By.XPATH, base_path + '[2]/li[2]/p/small').text]
	status["psn"]["authentication"] = [driver.find_element(By.XPATH, base_path + '[2]/li[3]/h4').text, driver.find_element(By.XPATH, base_path + '[2]/li[3]/p/small').text]
	status["psn"]["store"] = [driver.find_element(By.XPATH, base_path + '[2]/li[4]/h4').text, driver.find_element(By.XPATH, base_path + '[2]/li[4]/p/small').text]
	status["psn"]["matchmaking"] = [driver.find_element(By.XPATH, base_path + '[2]/li[5]/h4').text, driver.find_element(By.XPATH, base_path + '[2]/li[5]/p/small').text]

	# Xbox
	status["xbox"]["status"] = ["Xbox", driver.find_element(By.XPATH, base_path + '[3]/li[1]/span/small').text]
	status["xbox"]["connectivity"] = [driver.find_element(By.XPATH, base_path + '[3]/li[2]/h4').text, driver.find_element(By.XPATH, base_path + '[3]/li[2]/p/small').text]
	status["xbox"]["authentication"] = [driver.find_element(By.XPATH, base_path + '[3]/li[3]/h4').text, driver.find_element(By.XPATH, base_path + '[3]/li[3]/p/small').text]
	status["xbox"]["store"] = [driver.find_element(By.XPATH, base_path + '[3]/li[4]/h4').text, driver.find_element(By.XPATH, base_path + '[3]/li[4]/p/small').text]
	status["xbox"]["matchmaking"] = [driver.find_element(By.XPATH, base_path + '[3]/li[5]/h4').text, driver.find_element(By.XPATH, base_path + '[3]/li[5]/p/small').text]

	status["update_date"] = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))

	print(status)
	return status

# サーバーステータス埋め込みメッセージを更新
async def updateserverstatusembed():
	global server_status_embed

	# サーバーステータスを取得
	status = server_status

	# 埋め込みメッセージを作成
	embed = discord.Embed(color=discord.Colour.dark_grey())
	embed.set_author(name="Rainbow Six Siege - Server Status", icon_url="https://www.google.com/s2/favicons?sz=64&domain_url=https://www.ubisoft.com/en-us/game/rainbow-six/siege/status")
	embed.set_footer(text="最終更新: " + status["update_date"].strftime('%Y/%m/%d %H:%M:%S') + " (JST)")

	platform_list = ["pc", "psn", "xbox"]
	for p in platform_list:
		status_list = []

		# サーバーの状態によってアイコンを変更する
		if status[p]["status"][1] == "問題なし" or status[p]["status"][1] == "No Issues":
			status_icon = ":green_circle:"
		elif status[p]["status"][1] == "想定外の問題":
			status_icon = ":orange_circle:"
		else:
			status_icon = ":yellow_circle:"

		# ステータステキストを作成
		for key in status[p].keys():
			if key != "status":
				status_list.append("**" + status[p][key][0] + "**" + "\n- **`" + status[p][key][1] + "`**")
		status_text = "\n".join(status_list)

		# 埋め込みメッセージにプラットフォームのフィールドを追加
		embed.add_field(name=status_icon + " " + status[p]["status"][0] + " - " + status[p]["status"][1], value=status_text)

	server_status_embed = embed

# コマンド
@client.slash_command()
async def status(ctx):
	global server_status_embed

	logging.info(f"コマンド実行: status / 実行者: {ctx.user}")

	await ctx.defer()
	await ctx.followup.send(embed=server_status_embed)

@client.slash_command()
async def create(ctx, channel: Option(
	discord.TextChannel,
	required=False,
	name="テキストチャンネル",
	description="サーバーステータスを送信するテキストチャンネルを指定します。指定しない場合は現在のチャンネルになります。")
):
	global server_status_embed

	logging.info(f"コマンド実行: create / 実行者: {ctx.user}")

	await ctx.defer()

	checkGuildData()

	additional_msg = ""
	if guilddata[str(ctx.guild_id)]["server_status_message"][1] != 0:
		additional_msg = "\n(以前送信した古いメッセージは更新されなくなります。)"

	if channel is None:
		ch_id = ctx.channel_id
	else:
		ch_id = channel.id
	ch = client.get_channel(ch_id)

	# サーバーステータス埋め込みメッセージを送信
	msg = await ch.send(embed=server_status_embed)

	# 送信したチャンネルとメッセージのIDをギルドデータへ保存する
	guilddata[str(ctx.guild_id)]["server_status_message"][0] = ch_id
	guilddata[str(ctx.guild_id)]["server_status_message"][1] = msg.id
	saveGuildData()

	await ctx.send_followup(content="テキストチャンネル " + ch.mention + " へサーバーステータスメッセージを送信しました。\n以後このメッセージは自動的に更新されます。" + additional_msg)

@client.slash_command()
async def ping(ctx):
	logging.info(f"コマンド実行: ping / 実行者: {ctx.user}")
	raw_ping = client.latency
	ping = round(raw_ping * 1000)
	ping_embed = discord.Embed(title="Pong!",description=f"Latency: **`{ping}`** ms",color=discord.Colour.from_rgb(79,168,254))
	await ctx.respond(embed=ping_embed)

@client.slash_command()
async def about(ctx):
	logging.info(f"コマンド実行: about / 実行者: {ctx.user}")
	embed = discord.Embed(color=discord.Colour.blue())
	embed.set_author(name=bot_name, icon_url=client.user.display_avatar.url)
	embed.set_footer(text=f"Developed by Milkeyyy#0625")
	embed.add_field(name="Version", value="`" + bot_version + "`")
	embed.add_field(name="Library", value=f"Pycord: `{discord.__version__}`")

	await ctx.respond(embed=embed)


# ログイン
try:
	keep_alive()
	client.run(os.getenv("TOKEN"))
except Exception as e:
	logging.error(str(e))
	os.system("kill 1")