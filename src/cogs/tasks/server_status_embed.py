import traceback

import discord
import r6sss
from discord.ext import commands, tasks

import embeds
import localizations
import status_indicator
from client import client
from config import GuildConfigManager
from kumasan import KumaSan
from logger import logger
from maintenance_schedule import MaintenanceScheduleManager
from server_status import ServerStatusManager


class ServerStatusEmbedManager(commands.Cog):
	def __init__(self, bot: discord.Bot) -> None:
		self.bot = bot
		self.server_status_update_loop_is_running: bool = False
		self.update_server_status.start()

	# 2分毎にサーバーステータスを更新する
	@tasks.loop(minutes=2)
	async def update_server_status(self) -> None:  # noqa: PLR0915
		self.server_status_update_loop_is_running = True

		# Heartbeatイベントを送信 (サーバーステータスの更新が開始されたことを報告)
		await KumaSan.ping(state="up", message="サーバーステータスの更新開始")

		logger.info("サーバーステータスの更新開始")

		try:
			# サーバーステータス情報を取得する
			status_data = await ServerStatusManager.get()
			# 取得できなかった場合は処理を行わずにエラーを出力する
			if status_data is None:
				logger.error("- 更新中止: status_data is None")
				await KumaSan.ping("pending", "サーバーステータスの更新中止: status_data is None")
				return

			# メンテナンススケジュール情報を取得する
			schedule_data = await MaintenanceScheduleManager.get()

			# 各ギルドの埋め込みメッセージIDチェック、存在する場合はメッセージを更新する
			for guild in client.guilds:
				logger.info("ギルド: %s", guild.name)
				try:
					# データベースからギルドコンフィグを取得する
					gc = await GuildConfigManager.get(guild.id)
					# 取得できなかった場合はスキップする
					if gc is None:
						logger.warning("更新スキップ: ギルドデータ (%s) の取得失敗", guild.name)
						continue
					ch_id = int(gc.server_status_message.channel_id)
					msg_id = int(gc.server_status_message.message_id)
					notif_ch_id = int(gc.server_status_notification.channel_id)
					notif_role_id = int(gc.server_status_notification.role_id)
					lang = gc.server_status_message.language
				except Exception:
					logger.warning("更新スキップ: ギルドデータ (%s) の取得時エラー", guild.name)
					logger.error(traceback.format_exc())
					continue  # 更新をスキップ

				try:
					# テキストチャンネルとメッセージのID, 通知メッセージの送信先
					# 両方が設定されていない場合は処理をスキップする
					if (ch_id == 0 or msg_id == 0) and (notif_ch_id == 0):
						continue

					# IDからテキストチャンネルを取得する
					ch = guild.get_channel(ch_id)
					# チャンネルが存在しない場合はギルドデータのチャンネルIDとメッセージIDをリセットする
					if ch is None:
						logger.info("更新スキップ: テキストチャンネルの取得失敗")
						logger.info("- 設定リセット実行")
						gc.server_status_message.channel_id = "0"
						gc.server_status_message.message_id = "0"
						# ギルドコンフィグを保存
						await GuildConfigManager.update(guild.id, gc)
						continue  # 処理をスキップする

					ch_name = ch.name
					logger.info("- 更新実行: #%s", ch_name)

					e = ""
					try:
						# 取得したテキストチャンネルからメッセージを取得する
						msg = await ch.fetch_message(msg_id)
					except discord.errors.NotFound as err:
						logger.info(" - メッセージの取得失敗 (%s)", str(err))
						msg = None

					# 既存のサーバーステータスメッセージの取得に失敗した場合はコンフィグをリセットして処理をスキップする
					if msg is None:
						logger.info("- 更新中止: メッセージの取得失敗")
						logger.info("ギルド %s のメッセージ (ID: %s) の取得に失敗", guild.name, str(msg_id))
						# メッセージが存在しない(削除されている)場合はギルドデータのチャンネルIDとメッセージIDをリセットする
						gc.server_status_message.channel_id = "0"
						gc.server_status_message.message_id = "0"
						# ギルドデータを保存
						await GuildConfigManager.update(guild.id, gc)
						continue

					# ステータスインジケーターが有効かつインジケーターに変化があった場合は
					# 元の名前を保持して先頭にインジケーターを追加または置換する
					if all(
						(
							gc.server_status_message.status_indicator,  # ステータスインジケーターが有効
							ch_name[0] in status_indicator.List,  # チャンネル名の先頭がステータスインジケーターか
							ch_name[0] != ServerStatusManager.indicator,  # チャンネル名の先頭が現在のインジケーターと異なるか
						)
					):
						# インジケーター文字を除いたチャンネル名を取得する
						ch_name_min_count = 2
						ch_name = ch_name[1:] if len(ch_name) >= ch_name_min_count else ""
						try:
							await msg.channel.edit(
								name=ServerStatusManager.indicator + ch_name,
							)
						except Exception as e:
							logger.error(traceback.format_exc())
							logger.error("ギルド %s のステータスインジケーターの更新に失敗: %s", guild.name, str(e))

					try:
						# 埋め込みメッセージを生成
						server_status_embeds = await embeds.ServerStatus.generate(
							lang,
							status_data,
							schedule_data,
						)
					except Exception as e:
						server_status_embeds = None
						logger.error(traceback.format_exc())
						logger.error(
							"サーバーステータスメッセージの生成に失敗: %s",
							str(e),
						)

					try:
						# サーバーステータスメッセージを編集
						if server_status_embeds is not None:
							await msg.edit(embeds=server_status_embeds)
					except Exception as e:
						logger.error(traceback.format_exc())
						logger.error(
							"サーバーステータスメッセージの生成に失敗: %s",
							str(e),
						)

					try:
						if ServerStatusManager.previous_data is not None:
							notif_embeds = []

							# if client.user is not None:
							# 	embed_author = discord.EmbedAuthor(
							# 		client.user.display_name,
							# 		icon_url=client.user.display_avatar.url,
							# 	)
							# else:
							# 	embed_author = None

							# 以前のサーバーステータスが None でなければ、サーバーステータスの比較を行う
							if ServerStatusManager.previous_data is not None:
								compare_result = r6sss.compare_server_status(ServerStatusManager.previous_data, status_data)

								# ステータスの比較結果一覧から通知用の埋め込みメッセージを生成する
								notif_embeds = [embeds.Notification.get_by_comparison_result(result, lang) for result in compare_result]
								# for result in compare_result:
								# 	# 対象プラットフォームの一覧テキストを生成
								# 	# 全プラットフォームの場合は専用のテキストにする
								# 	if {p.platform for p in ServerStatusManager.data}.issubset(set(result.platforms)):
								# 		target_platforms_text = localizations.translate("Platform_All", lang=lang)
								# 	else:
								# 		target_platforms_text = " | ".join(
								# 			[platform_icon.LIST[p.value] + " " + p.name for p in result.platforms]
								# 		)

								# 	if result.detail == r6sss.ComparisonDetail.START_MAINTENANCE:
								# 		# メンテナンス開始
								# 		logger.info("通知送信: メンテナンス開始")
								# 		notif_embeds.append(
								# 			discord.Embed(
								# 				color=discord.Colour.light_grey(),
								# 				title=localizations.translate("Title_Maintenance_Start", lang=lang),
								# 				description="**"
								# 				+ localizations.translate("TargetPlatform", lang=lang)
								# 				+ ": "
								# 				+ target_platforms_text
								# 				+ "**",
								# 				author=embed_author,
								# 			)
								# 		)

								# 通知メッセージを送信するチャンネルを取得
								notif_ch = guild.get_channel(notif_ch_id)
								notif_role = guild.get_role(notif_role_id)

								# メンションするロールが設定済みかつメンションが可能な場合はメンション用のテキストを設定
								notif_role_mention = (
									(notif_role.mention if notif_role.mentionable else "") if notif_role is not None else ""
								)

								# 通知メッセージを送信
								if notif_ch is not None and notif_embeds is not None:
									for notif_embed in notif_embeds:
										if notif_embed is not None:
											notif_embed.description = f"\
	[**💬 {localizations.translate('Notification_Show_Server_Status', lang=lang)}**]\
	({msg.jump_url})\n{notif_embed.description}"
									if len(notif_embeds) >= 1:
										# 自動削除が有効の場合は削除までの時間を指定する
										notif_delete_after_seconds = int(gc.server_status_notification.auto_delete)
										if notif_delete_after_seconds > 0:
											await notif_ch.send(
												content=localizations.translate(
													"Notification_Server_Status_Updated",
													lang=lang,
												)
												+ "\n"
												+ notif_role_mention,
												embeds=notif_embeds,
												delete_after=notif_delete_after_seconds,
											)
										# 自動削除が無効の場合は削除までの時間を指定しない
										else:
											await notif_ch.send(
												content=localizations.translate(
													"Notification_Server_Status_Updated",
													lang=lang,
												)
												+ "\n"
												+ notif_role_mention,
												embeds=notif_embeds,
											)

					except Exception as e:
						logger.error(traceback.format_exc())
						logger.error(
							"サーバーステータス通知メッセージの送信に失敗: %s",
							str(e),
						)

				except Exception:
					logger.error(
						"ギルド %s のサーバーステータスメッセージ(%s)の更新に失敗",
						guild.name,
						str(msg_id),
					)
					logger.error(traceback.format_exc())

		except Exception as e:
			logger.error(traceback.format_exc())
			await KumaSan.ping(
				state="pending",
				message="サーバーステータスの更新エラー: " + str(e),
			)

		logger.info("サーバーステータスの更新完了")

		await KumaSan.ping(state="up", message="サーバーステータスの更新完了")

	@update_server_status.after_loop
	async def after_update_server_status(self) -> None:
		self.server_status_update_loop_is_running = False
		logger.info("サーバーステータスの定期更新終了")
		if not self.server_status_update_loop_is_running:
			self.update_server_status.start()

	@update_server_status.before_loop
	async def before_update_server_status(self) -> None:
		logger.info("サーバーステータスの定期更新待機中")
		logger.info("- クライアントの準備完了まで待機中")
		await self.bot.wait_until_ready()
		logger.info("- クライアントの準備完了")
		logger.info("定期更新開始")


def setup(bot: discord.Bot) -> None:
	bot.add_cog(ServerStatusEmbedManager(bot))
