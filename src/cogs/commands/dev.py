from collections import Counter

import discord
from discord.ext import commands

from stats import StatsManager


class DevCommands(commands.Cog):
	def __init__(self, bot: discord.Bot) -> None:
		self.bot = bot

	@commands.slash_command()
	@discord.default_permissions(administrator=True)
	@commands.cooldown(2, 5)
	@commands.is_owner()
	async def botstats(self, ctx: discord.ApplicationContext) -> None:
		embed = discord.Embed(
			title="R6SSS Bot Stats",
			description="",
			color=discord.Colour.from_rgb(79, 168, 254),
		)
		embed.add_field(name="Total Servers", value=str(len(self.bot.guilds)), inline=False)

		embed.add_field(
			name="Total Server Status Embeds",
			value=str(self.bot.get_cog("ServerStatusEmbedManager").server_status_embeds_count),
		)
		update_time = self.bot.get_cog("ServerStatusEmbedManager").server_status_embeds_update_time
		ut_min, ut_min_sec = divmod(update_time, 60)
		embed.add_field(
			name="Server Status Embeds Last Update Time",
			value=f"{int(ut_min)} m {ut_min_sec:.0f} s ({update_time:.1f} s)",
			inline=False,
		)

		locale_counts = Counter(guild.preferred_locale or "Not Defined" for guild in self.bot.guilds)
		embed.add_field(
			name="Server Preferred Locale List",
			value="- " + str("\n- ".join(f"`{locale}` ({count})" for locale, count in locale_counts.most_common())),
			inline=False,
		)

		# 本日のコマンド実行数をデータベースから集計する
		today_stats = await StatsManager.get_today_command_stats()
		embed.add_field(
			name="Today's Commands",
			value=f"{today_stats[0]} (Errors: {today_stats[1]})" if today_stats is not None else "N/A",
			inline=False,
		)

		await ctx.respond(embed=embed)


def setup(bot: discord.Bot) -> None:
	bot.add_cog(DevCommands(bot))
