import argparse
import asyncio
import logging
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

# 引数ぱーさー
parser = argparse.ArgumentParser()
parser.add_argument(
	"--token",
	help="Botのトークン (使用法: --token ここにトークンを挿入)",
	type=str,
	required=True
)
parser.add_argument(
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
)
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
	auth = Auth(args.ubi_email, args.ubi_password)
	status = 


# コマンド
@client.slash_command()
async def status(ctx):
	logging.info(f"コマンド実行: status / 実行者: {ctx.user}")
	await ctx.respond(embed=embed)

@client.slash_command()
async def create(ctx):
	logging.info(f"コマンド実行: create / 実行者: {ctx.user}")

@client.slash_command()
async def ping(ctx):
	raw_ping = client.latency
	ping = round(raw_ping * 1000)
	ping_embed = discord.Embed(title="Pong!",description=f"Latency: **`{ping}`** ms",color=discord.Colour.from_rgb(79,168,254))
	await ctx.respond(embed=ping_embed)
	logging.info(f"コマンド実行: ping / 実行者: {ctx.user}")


# ログイン
client.run(args.token)