import argparse
import asyncio
import logging

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from time import sleep
import sys

import discord
from discord.commands import Option

from siegeapi import Auth

logging.basicConfig(level=logging.INFO)
logging.basicConfig(level=logging.WARNING)

# Botの名前
bot_name = "R6ServerStatusBot"
# Botのバージョン
bot_version = "1.0.0"

# サーバーステータスページのURL
status_url = "https://www.ubisoft.com/ja-jp/game/rainbow-six/siege/status"

# 引数ぱーさー
parser = argparse.ArgumentParser()
parser.add_argument(
	"--token",
	help="Botのトークン (使用法: --token ここにトークンを挿入)",
	type=str,
	required=True
)
""" parser.add_argument(
	"--ubi_email",
	help="Ubisoftアカウントのメールアドレス",
	type=str,
	required=True
)
parser.add_argument(
	"--ubi_password",
	help="Ubisoftアカウントのパスワード",
	type=str,
	required=True
) """
args = parser.parse_args()

# トークンが指定されていない場合はエラーを発生させる
if args.token is None:
	logging.error("トークンが指定されていません！")
	sys.exit(1)


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


# 関数
async def getserverstatus():
	chrome_options = Options()
	#chrome_options.add_argument('--no-sandbox')
	#chrome_options.add_argument('--disable-dev-shm-usage')

	# ウィンドウを表示しない
	chrome_options.add_argument("--headless")

	driver = webdriver.Chrome("chromedriver_win32\chromedriver", options=chrome_options)

	driver.get(status_url)

	wait = WebDriverWait(driver, 10)
	selector = '/html/body/div[1]/main/div/div/div[1]/div/ul[1]/li[1]/span/small'
	wait.until(EC.visibility_of_element_located((By.XPATH, selector)))

	text = driver.find_element(By.XPATH, '/html/body/div[1]/main/div/div/div[1]/div/ul[1]/li[1]/span/small').text

	return text


# コマンド
@client.slash_command()
async def status(ctx):
	logging.info(f"コマンド実行: status / 実行者: {ctx.user}")

	await ctx.defer()

	# サーバーステータスを取得
	text = await getserverstatus()

	print(f"Status: {text}")
	await ctx.followup.send(content=f"Status: {text}")

@client.slash_command()
async def create(ctx):
	logging.info(f"コマンド実行: create / 実行者: {ctx.user}")

@client.slash_command()
async def ping(ctx):
	logging.info(f"コマンド実行: ping / 実行者: {ctx.user}")
	raw_ping = client.latency
	ping = round(raw_ping * 1000)
	ping_embed = discord.Embed(title="Pong!",description=f"Latency: **`{ping}`** ms",color=discord.Colour.from_rgb(79,168,254))
	await ctx.respond(embed=ping_embed)



# ログイン
client.run(args.token)