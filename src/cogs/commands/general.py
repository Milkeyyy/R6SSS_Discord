import discord
from discord.ext import commands

import embeds
from app import App
from client import client


class GeneralCommands(commands.Cog):
	def __init__(self, bot: discord.Bot) -> None:
		self.bot = bot

	@commands.slash_command()
	@discord.default_permissions(send_messages=True)
	@commands.cooldown(2, 5)
	async def ping(self, ctx: discord.ApplicationContext) -> None:
		raw_ping = client.latency
		ping = round(raw_ping * 1000)
		ping_embed = discord.Embed(
			title="Pong!",
			description=f"Latency: **`{ping}`** ms",
			color=discord.Colour.from_rgb(79, 168, 254),
		)
		await ctx.respond(embed=ping_embed)

	@commands.slash_command()
	@discord.default_permissions(send_messages=True)
	@commands.cooldown(2, 5)
	async def about(self, ctx: discord.ApplicationContext) -> None:
		embed = discord.Embed(color=discord.Colour.blue())
		embed.set_image(url=App.bot_banner_url)
		embed.set_author(name=App.NAME, icon_url=client.user.display_avatar.url)
		embed.set_footer(text=App.COPYRIGHT)
		embed.add_field(
			name="Version",
			value=f"`{App.VERSION_STRING}` ([`{App.get_git_commit_hash()[0:7]}`]({App.GITHUB_REPO_URL}/commit/{App.get_git_commit_hash()}))",
		)
		embed.add_field(
			name="Source",
			value=f"[GitHub]({App.GITHUB_REPO_URL})",
			inline=False,
		)
		embed.add_field(
			name="Developer",
			value=f"- {App.DEVELOPER_NAME}\n  - [Website]({App.DEVELOPER_WEBSITE_URL})\n  - [Twitter]({App.DEVELOPER_TWITTER_URL})",
			inline=True,
		)
		embed.add_field(
			name="Other Services",
			value=f"- [Bluesky Bot]({App.BLUESKY_BOT_URL})\n- [Twitter Bot]({App.TWITTER_BOT_URL})",
			inline=True,
		)
		await ctx.respond(embeds=[embed, await embeds.Donation.donation()])


def setup(bot: discord.Bot) -> None:
	bot.add_cog(GeneralCommands(bot))
