import discord
from pycord.i18n import _
import r6sss

from client import client
import localizations
import platform_icon
from server_status import ServerStatusManager


class Notification:
	@classmethod
	def success(cls, title: str = "", description: str = ""):
		"""成功時用埋め込みメッセージ"""

		if title == "":
			title = _("CmdMsg_Success")

		embed = discord.Embed(
			title=":white_check_mark: " + title,
			description=description,
			colour=discord.Colour.from_rgb(140, 176, 91)
		)
		return embed

	@classmethod
	def warning(cls, title: str = "", description: str = ""):
		"""警告用埋め込みメッセージ"""

		if title == "":
			title = _("CmdMsg_Warning")

		embed = discord.Embed(
			title=":warning: " + title,
			description=description,
			colour=discord.Colour.from_rgb(228, 146, 16)
		)
		return embed

	@classmethod
	def error(cls, title: str = "", description: str = ""):
		"""エラー発生時用埋め込みメッセージ"""

		if title == "":
			title = _("CmdMsg_ExcutionError")

		embed = discord.Embed(
			title=":no_entry_sign: " + title,
			description=description,
			colour=discord.Colour.from_rgb(247, 206, 80)
		)
		return embed

	@classmethod
	def internal_error(cls):
		"""内部エラー発生時用埋め込みメッセージ"""

		embed = discord.Embed(
			title=":closed_book: " + _("CmdMsg_InternalError"),
			description = _("CmdMsg_InternalError_Description"),
			colour=discord.Colour.from_rgb(205, 61, 66)
		)
		return embed

	@classmethod
	def get_by_comparison_result(cls, result: r6sss.ComparisonResult, lang: str) -> discord.Embed | None:
		"""サーバーステータスの比較結果から通知用のEmbedを生成する"""

		if ServerStatusManager.data is None or client.user is None:
			return None

		if client.user is not None:
			embed_author = discord.EmbedAuthor(client.user.display_name, icon_url=client.user.display_avatar.url)
		else:
			embed_author = None

		# 対象プラットフォームの一覧テキストを生成
		# 全プラットフォームの場合は専用のテキストにする
		if {p.platform for p in ServerStatusManager.data}.issubset(set(result.platforms)):
			target_platforms_text = localizations.translate("Platform_All", lang=lang)
		else:
			target_platforms_text = " | ".join([platform_icon.LIST[p.value] + " " + p.name for p in result.platforms])

		# メンテナンス開始
		if result.detail == r6sss.ComparisonDetail.START_MAINTENANCE:
			embed = discord.Embed(
				color=discord.Colour.light_grey(),
				title=localizations.translate("Title_Maintenance_Start", lang=lang),
				description="**" + localizations.translate("TargetPlatform", lang=lang) + ": " + target_platforms_text + "**",
				author=embed_author,
			)
		# メンテナンス終了
		elif result.detail == r6sss.ComparisonDetail.END_MAINTENANCE:
			embed = discord.Embed(
				color=discord.Colour.light_grey(),
				title=localizations.translate("Title_Maintenance_End", lang=lang),
				description="**" + localizations.translate("TargetPlatform", lang=lang) + ": " + target_platforms_text + "**",
				author=embed_author,
			)

		# TODO: 計画メンテナンス開始/終了の場合の処理を実装する

		# すべての機能の問題が解消
		elif result.detail == r6sss.ComparisonDetail.ALL_FEATURES_OUTAGE_RESOLVED:
			embed = discord.Embed(
				color=discord.Colour.green(),
				title=localizations.translate("Title_AllFeaturesOutageResolved", lang=lang),
				description="**" + localizations.translate("TargetPlatform", lang=lang) + ": " + target_platforms_text + "**",
				author=embed_author,
			)
			embed.add_field(
				name=localizations.translate("Detail_ImpactedFeatures_After", lang=lang),
				value="- " + "\n- ".join(result.resolved_impacted_features)
			)
		# すべての機能で問題が発生中
		elif result.detail == r6sss.ComparisonDetail.ALL_FEATURES_OUTAGE:
			embed = discord.Embed(
				color=discord.Colour.red(),
				title=localizations.translate("Title_AllFeaturesOutage", lang=lang),
				description="**" + localizations.translate("TargetPlatform", lang=lang) + ": " + target_platforms_text + "**",
				author=embed_author,
			)
			embed.add_field(
				name=localizations.translate("Detail_ImpactedFeatures", lang=lang),
				value="- " + "\n- ".join(result.impacted_features)
			)
		# 一部の機能で問題が発生中
		elif result.detail == r6sss.ComparisonDetail.SOME_FEATURES_OUTAGE:
			embed = discord.Embed(
				color=discord.Colour.red(),
				title=localizations.translate("Title_SomeFeaturesOutage", lang=lang),
				description="**" + localizations.translate("TargetPlatform", lang=lang) + ": " + target_platforms_text + "**",
				author=embed_author,
			)
			embed.add_field(
				name=localizations.translate("Detail_ImpactedFeatures", lang=lang),
				value="- " + "\n- ".join(result.impacted_features)
			)
		# 一部の機能で問題が解消 (影響を受ける機能が変わった)
		elif result.detail == r6sss.ComparisonDetail.SOME_FEATURES_OUTAGE_RESOLVED:
			embed = discord.Embed(
				color=discord.Colour.red(),
				title=localizations.translate("Title_SomeFeaturesOutageResolved", lang=lang),
				description="**" + localizations.translate("TargetPlatform", lang=lang) + ": " + target_platforms_text + "**",
				author=embed_author,
			)
			embed.add_field(
				name=localizations.translate("Detail_ImpactedFeatures", lang=lang),
				value="- " + "\n- ".join(result.resolved_impacted_features)
			)
			embed.add_field(
				name=localizations.translate("Detail_ImpactedFeatures_After", lang=lang),
				value="- " + "\n- ".join(result.impacted_features)
			)
		else:
			embed = None

		return embed
