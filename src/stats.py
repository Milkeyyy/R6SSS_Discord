import datetime
import traceback
from collections import OrderedDict
from typing import ClassVar, Literal
from zoneinfo import ZoneInfo

import discord
from pymongo import UpdateOne
from pymongo.errors import BulkWriteError

from app import App
from db import DBManager
from logger import logger

JST: datetime.tzinfo
"""日本標準時 (Asia/Tokyo)"""

try:
	JST = ZoneInfo("Asia/Tokyo")
except Exception:
	# タイムゾーンデータが存在しない環境では UTC+9 の固定オフセットで代替する
	JST = datetime.timezone(datetime.timedelta(hours=9))
	logger.warning("タイムゾーンデータ (Asia/Tokyo) を読み込めなかったため UTC+9 で代替します")
	logger.warning(traceback.format_exc())


class StatsManager:
	"""運用統計の収集とデータベースへの書き込みを管理するクラス

	すべてのメソッドは例外を内部で処理し、失敗時はログのみを出力する
	(統計の収集失敗が Bot 本体の動作へ影響しないようにするため)
	"""

	MAX_BUFFER_KEYS: int = 5000
	"""バッファに保持する最大キー数"""

	started_at: datetime.datetime | None = None
	"""Bot の起動時刻 (UTC)"""

	_buffer: ClassVar[OrderedDict[tuple[str, str, str, str], dict[str, int]]] = OrderedDict()
	"""(日付, metric, dim1, dim2) をキーとした書き込み待ちカウンタ (最終更新順)"""

	# 日付・カウンタの記録

	@classmethod
	def _get_jst_date(cls, dt: datetime.datetime | None = None) -> str:
		"""指定された日時 (省略時は現在時刻) の JST 日付を `YYYY-MM-DD` 形式で返す"""
		if dt is None:
			dt = datetime.datetime.now(tz=datetime.UTC)
		# タイムゾーンが設定されていない場合は UTC として扱う
		elif dt.tzinfo is None:
			dt = dt.replace(tzinfo=datetime.UTC)
		return dt.astimezone(JST).strftime("%Y-%m-%d")

	@classmethod
	def _add_counter(
		cls,
		metric: str,
		dim1: str,
		dim2: str,
		*,
		count: int = 0,
		error_count: int = 0,
		occurred_at: datetime.datetime | None = None,
	) -> None:
		"""カウンタをバッファへ加算する"""
		try:
			# 記録時点の JST 日付でキーを確定する
			key = (cls._get_jst_date(occurred_at), metric, dim1, dim2)
			# バッファの上限に達している場合は最終更新が最も古いキーを破棄する (通常運用では到達しない)
			if key not in cls._buffer and len(cls._buffer) >= cls.MAX_BUFFER_KEYS:
				oldest_key = next(iter(cls._buffer))
				cls._buffer.pop(oldest_key, None)
				logger.warning("統計バッファの上限に達したため最も古いデータを破棄: %s", str(oldest_key))
			counter = cls._buffer.setdefault(key, {"count": 0, "error_count": 0})
			counter["count"] += count
			counter["error_count"] += error_count
			# 更新したキーを末尾へ移動する (上限到達時は先頭から破棄するため)
			cls._buffer.move_to_end(key)
		except Exception:
			logger.error("統計カウンタの記録に失敗")
			logger.error(traceback.format_exc())

	@classmethod
	def add_command(cls, command: str, guild_id: int | None, *, ok: bool) -> None:
		"""コマンドの実行 (成功 / エラー) を記録する"""
		cls._add_counter(
			"command",
			command,
			str(guild_id) if guild_id is not None else "DM",
			count=1,
			error_count=0 if ok else 1,
		)

	@classmethod
	def add_embed_created(cls, kind: str) -> None:
		"""埋め込みメッセージの生成を記録する"""
		cls._add_counter("embed_created", kind, "-", count=1)

	@classmethod
	def add_embed_sent(cls, kind: str, guild_id: int, count: int = 1) -> None:
		"""埋め込みメッセージの実送信を記録する"""
		cls._add_counter("embed_sent", kind, str(guild_id), count=count)

	# バッファの書き込み

	@classmethod
	def _build_flush_ops(
		cls,
		buffer: dict[tuple[str, str, str, str], dict[str, int]],
		updated_at: datetime.datetime,
	) -> list[UpdateOne]:
		"""バッファの内容から一括書き込み用の操作一覧を生成する"""
		ops = []
		for (date, metric, dim1, dim2), counter in buffer.items():
			ops.append(
				UpdateOne(
					{"date": date, "metric": metric, "dim1": dim1, "dim2": dim2},
					{
						"$inc": {"count": counter["count"], "error_count": counter["error_count"]},
						"$set": {"updated_at": updated_at},
					},
					upsert=True,
				)
			)
		return ops

	@classmethod
	def _subtract_written(cls, written: dict[tuple[str, str, str, str], dict[str, int]]) -> None:
		"""書き込みが完了した分をバッファから減算する"""
		for key, counter in written.items():
			current = cls._buffer.get(key)
			if current is None:
				continue
			current["count"] = max(0, current["count"] - counter["count"])
			current["error_count"] = max(0, current["error_count"] - counter["error_count"])
			if current["count"] <= 0 and current["error_count"] <= 0:
				cls._buffer.pop(key, None)

	@classmethod
	async def flush(cls) -> None:
		"""バッファの内容をデータベースへ一括書き込みする

		書き込みに失敗した場合はバッファを保持して次回リトライする
		(一部の操作のみ失敗した場合は、成功した操作の分だけバッファから減算する)
		"""
		if not DBManager.connected or not cls._buffer:
			return
		try:
			# 書き込み中に加算された分を取りこぼさないよう、書き込み対象をコピーしてから実行する
			target = {key: counter.copy() for key, counter in cls._buffer.items()}
			ops = cls._build_flush_ops(target, datetime.datetime.now(tz=datetime.UTC))
			try:
				await DBManager.counters_col.bulk_write(ops, ordered=False)
			# 一部の操作が失敗した場合は、成功した操作の分だけバッファから減算する
			except BulkWriteError as err:
				failed_indexes = {error["index"] for error in err.details.get("writeErrors", []) if "index" in error}
				# どの操作が書き込まれたか判別できない場合はバッファを保持して次回リトライする
				if not failed_indexes or err.details.get("writeConcernErrors"):
					raise
				cls._subtract_written({key: counter for i, (key, counter) in enumerate(target.items()) if i not in failed_indexes})
				logger.warning("統計カウンタの一部の書き込みに失敗 (成功分のみバッファから減算)")
				logger.warning("失敗した操作数: %d / %d", len(failed_indexes), len(ops))
			else:
				# 書き込みに成功した分だけバッファから減算する
				cls._subtract_written(target)
				logger.debug("統計カウンタの書き込み完了 - 件数: %d", len(ops))
		except Exception:
			logger.error("統計カウンタの書き込みに失敗 (次回リトライ)")
			logger.error(traceback.format_exc())

	# 集計

	@classmethod
	async def get_today_command_stats(cls) -> tuple[int, int] | None:
		"""本日 (JST) のコマンド実行数とエラー数を集計して返す

		集計に失敗した場合は `None` を返す
		"""
		if not DBManager.connected:
			return None
		try:
			cursor = await DBManager.counters_col.aggregate(
				[
					{"$match": {"metric": "command", "date": cls._get_jst_date()}},
					{"$group": {"_id": None, "count": {"$sum": "$count"}, "error_count": {"$sum": "$error_count"}}},
				]
			)
			result = await cursor.to_list(length=1)
			if not result:
				return 0, 0
			return result[0]["count"], result[0]["error_count"]
		except Exception:
			logger.error("本日のコマンド実行数の集計に失敗")
			logger.error(traceback.format_exc())
			return None

	# ギルド関連

	@classmethod
	async def upsert_guilds(cls, guilds: list[discord.Guild], *, mark_active: bool = False) -> None:
		"""ギルド情報のスナップショットを一括で保存する

		`mark_active` を指定した場合はアクティブ状態へ戻す (再参加時にのみ指定する)
		"""
		if not DBManager.connected:
			return
		try:
			now = datetime.datetime.now(tz=datetime.UTC)
			ops = []
			for guild in guilds:
				joined_at = guild.me.joined_at if guild.me is not None else None
				set_values: dict[str, object] = {
					"name": guild.name,
					"icon": guild.icon.key if guild.icon is not None else None,
					"member_count": guild.member_count or 0,
					"preferred_locale": str(guild.preferred_locale) if guild.preferred_locale is not None else None,
					"updated_at": now,
				}
				# 定期スナップショットで脱退記録を上書きしないよう、アクティブ状態は再参加時のみ更新する
				if mark_active:
					set_values["is_active"] = True
					set_values["left_at"] = None
				ops.append(
					UpdateOne(
						{"guild_id": str(guild.id)},
						{
							"$set": set_values,
							"$setOnInsert": {
								"guild_id": str(guild.id),
								"joined_at": joined_at if joined_at is not None else now,
								"is_active": True,
								"left_at": None,
							},
						},
						upsert=True,
					)
				)
			if ops:
				await DBManager.guilds_col.bulk_write(ops, ordered=False)
				logger.debug("ギルド情報の保存完了 - 件数: %d", len(ops))
		except Exception:
			logger.error("ギルド情報の保存に失敗")
			logger.error(traceback.format_exc())

	@classmethod
	async def upsert_guild(cls, guild: discord.Guild) -> None:
		"""ギルド情報のスナップショットを保存する (再参加時はアクティブ状態へ戻す)"""
		await cls.upsert_guilds([guild], mark_active=True)

	@classmethod
	async def record_guild_event(cls, event_type: Literal["join", "leave"], guild: discord.Guild) -> None:
		"""ギルドの参加 / 脱退イベントを記録する"""
		if not DBManager.connected:
			return
		try:
			await DBManager.events_col.insert_one(
				{
					"type": event_type,
					"guild_id": str(guild.id),
					"guild_name": guild.name,
					"member_count": guild.member_count or 0,
					"occurred_at": datetime.datetime.now(tz=datetime.UTC),
				}
			)
		except Exception:
			logger.error("ギルドイベントの記録に失敗")
			logger.error(traceback.format_exc())

	@classmethod
	async def mark_guild_left(cls, guild: discord.Guild) -> None:
		"""ギルドの脱退をギルド情報へ反映する"""
		if not DBManager.connected:
			return
		try:
			now = datetime.datetime.now(tz=datetime.UTC)
			await DBManager.guilds_col.update_one(
				{"guild_id": str(guild.id)},
				{
					"$set": {
						"name": guild.name,
						"icon": guild.icon.key if guild.icon is not None else None,
						"member_count": guild.member_count or 0,
						"preferred_locale": str(guild.preferred_locale) if guild.preferred_locale is not None else None,
						"is_active": False,
						"left_at": now,
						"updated_at": now,
					},
					# ギルド情報が存在しない場合の最低限の補完 (参加日時は不明のため脱退日時を設定する)
					"$setOnInsert": {"guild_id": str(guild.id), "joined_at": now},
				},
				upsert=True,
			)
		except Exception:
			logger.error("ギルド情報の脱退反映に失敗")
			logger.error(traceback.format_exc())

	# スナップショット

	@classmethod
	def record_start(cls) -> None:
		"""Bot の起動時刻を記録する"""
		try:
			if cls.started_at is None:
				cls.started_at = datetime.datetime.now(tz=datetime.UTC)
				logger.info("統計の記録を開始: %s", cls.started_at.isoformat())
		except Exception:
			logger.error("統計の開始時刻の記録に失敗")
			logger.error(traceback.format_exc())

	@classmethod
	async def collect_snapshot(cls, client: discord.Client) -> None:
		"""ヘルス・推移スナップショットを収集して保存する"""
		if not DBManager.connected:
			return
		try:
			now = datetime.datetime.now(tz=datetime.UTC)
			# サーバーステータス埋め込みメッセージ / 通知が設定されているギルド数を集計する
			# (ギルドコンフィグの ID は文字列で保持されている点に注意)
			status_message_guilds = await DBManager.col.count_documents(
				{"config.server_status_message.message_id": {"$ne": "0"}},
			)
			notification_guilds = await DBManager.col.count_documents(
				{"config.server_status_notification.channel_id": {"$ne": "0"}},
			)
			# サーバーステータス埋め込みメッセージの更新状況を取得する (Cog が存在しない場合は None)
			cog = client.get_cog("ServerStatusEmbedManager")
			await DBManager.snapshots_col.insert_one(
				{
					"captured_at": now,
					"guild_count": len(client.guilds),
					"total_member_count": sum(guild.member_count or 0 for guild in client.guilds),
					"latency_ms": round(client.latency * 1000),
					"version": App.VERSION_STRING,
					"commit": App.get_git_commit_hash(),
					"uptime_sec": int((now - cls.started_at).total_seconds()) if cls.started_at is not None else None,
					"status_message_guilds": status_message_guilds,
					"notification_guilds": notification_guilds,
					"update_loop_ms": round(cog.server_status_embeds_update_time * 1000) if cog is not None else None,
					"embeds_last_update": cog.server_status_embeds_count if cog is not None else None,
				}
			)
			logger.debug("統計スナップショットの保存完了")
		except Exception:
			logger.error("統計スナップショットの収集に失敗")
			logger.error(traceback.format_exc())
