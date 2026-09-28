"""統計収集 (StatsManager) のユニットテスト

MongoDB への実接続は不要 (データベース操作はフェイクへ差し替える)
"""

import datetime

import pytest
from pymongo import UpdateOne
from pymongo.errors import BulkWriteError

from app import App
from db import DBManager
from stats import StatsManager


@pytest.fixture(autouse=True)
def _reset_stats():
	"""各テストの前後で統計バッファと起動時刻を初期化する"""
	StatsManager._buffer.clear()
	StatsManager.started_at = None
	yield
	StatsManager._buffer.clear()
	StatsManager.started_at = None


class _FakeAggregateCursor:
	"""`to_list` のみを実装したテスト用カーソル"""

	def __init__(self, documents: list) -> None:
		self.documents = documents

	async def to_list(self, length: int | None = None) -> list:
		return self.documents


class _FakeCollection:
	"""データベース操作をフェイクに置き換えたテスト用コレクション"""

	def __init__(
		self,
		*,
		bulk_write_exception: Exception | None = None,
		aggregate_result: list | None = None,
		count_result: int = 0,
	) -> None:
		self.bulk_write_exception = bulk_write_exception
		self.aggregate_result = aggregate_result if aggregate_result is not None else []
		self.count_result = count_result
		self.ops: list[UpdateOne] = []
		self.updates: list[tuple[dict, dict, bool]] = []
		self.inserted: list[dict] = []

	async def bulk_write(self, ops: list[UpdateOne], ordered: bool = False) -> None:
		if self.bulk_write_exception is not None:
			raise self.bulk_write_exception
		self.ops.extend(ops)

	async def update_one(self, query: dict, update: dict, *, upsert: bool = False) -> None:
		self.updates.append((query, update, upsert))

	async def insert_one(self, document: dict) -> None:
		self.inserted.append(document)

	async def aggregate(self, pipeline: list) -> _FakeAggregateCursor:
		return _FakeAggregateCursor(self.aggregate_result)

	async def count_documents(self, query: dict) -> int:
		return self.count_result


class _FakeIcon:
	"""`Guild.icon` の代わりに使用するテスト用アイコン"""

	key = "icon_key"


class _FakeGuild:
	"""`discord.Guild` の代わりに使用するテスト用ギルド"""

	def __init__(
		self,
		guild_id: int = 123,
		name: str = "テストギルド",
		member_count: int | None = 42,
		preferred_locale: str | None = "ja",
	) -> None:
		self.id = guild_id
		self.name = name
		self.icon = _FakeIcon()
		self.member_count = member_count
		self.preferred_locale = preferred_locale
		self.me = None


class _FakeCog:
	"""`ServerStatusEmbedManager` の代わりに使用するテスト用 Cog"""

	server_status_embeds_update_time = 1.5
	server_status_embeds_count = 8


class _FakeClient:
	"""`discord.Client` の代わりに使用するテスト用クライアント"""

	def __init__(self, guilds: list, cog: object | None = None) -> None:
		self.guilds = guilds
		self.latency = 0.05
		self.cog = cog

	def get_cog(self, name: str) -> object | None:
		return self.cog


def _patch_jst_date(monkeypatch: pytest.MonkeyPatch, date: str = "2026-09-28") -> None:
	"""JST 日付変換を固定値へ差し替える"""
	monkeypatch.setattr(StatsManager, "_get_jst_date", classmethod(lambda cls, dt=None: date))


def _patch_db(monkeypatch: pytest.MonkeyPatch) -> None:
	"""データベース接続済みの状態へ差し替える"""
	monkeypatch.setattr(DBManager, "connected", True)


# 日付・バッファ


def test_get_jst_date_boundary():
	"""JST 日付の境界 (14:59 / 15:00 UTC) が正しく変換されること"""
	assert StatsManager._get_jst_date(datetime.datetime(2026, 9, 28, 14, 59, tzinfo=datetime.UTC)) == "2026-09-28"
	assert StatsManager._get_jst_date(datetime.datetime(2026, 9, 28, 15, 0, tzinfo=datetime.UTC)) == "2026-09-29"


def test_add_command_buffer_key(monkeypatch: pytest.MonkeyPatch):
	"""コマンドの記録が JST 日付をキーとしてバッファへ加算されること"""
	_patch_jst_date(monkeypatch)

	StatsManager.add_command("ping", 123, ok=True)
	StatsManager.add_command("ping", 123, ok=False)
	StatsManager.add_command("help", None, ok=True)

	assert StatsManager._buffer[("2026-09-28", "command", "ping", "123")] == {"count": 2, "error_count": 1}
	assert StatsManager._buffer[("2026-09-28", "command", "help", "DM")] == {"count": 1, "error_count": 0}


def test_add_embed_buffer_key(monkeypatch: pytest.MonkeyPatch):
	"""埋め込みの生成 / 実送信が種類別に記録されること"""
	_patch_jst_date(monkeypatch)

	StatsManager.add_embed_created("server_status")
	StatsManager.add_embed_sent("status_update", 456)
	StatsManager.add_embed_sent("notification", 456, count=3)

	assert StatsManager._buffer[("2026-09-28", "embed_created", "server_status", "-")] == {"count": 1, "error_count": 0}
	assert StatsManager._buffer[("2026-09-28", "embed_sent", "status_update", "456")] == {"count": 1, "error_count": 0}
	assert StatsManager._buffer[("2026-09-28", "embed_sent", "notification", "456")] == {"count": 3, "error_count": 0}


def test_buffer_limit(monkeypatch: pytest.MonkeyPatch):
	"""バッファの上限に達した場合は最も古いキーが破棄されること"""
	_patch_jst_date(monkeypatch)
	monkeypatch.setattr(StatsManager, "MAX_BUFFER_KEYS", 2)

	StatsManager.add_command("a", 1, ok=True)
	StatsManager.add_command("b", 1, ok=True)
	StatsManager.add_command("c", 1, ok=True)

	assert len(StatsManager._buffer) == 2
	assert ("2026-09-28", "command", "a", "1") not in StatsManager._buffer
	assert ("2026-09-28", "command", "c", "1") in StatsManager._buffer


def test_buffer_limit_evicts_least_recently_updated(monkeypatch: pytest.MonkeyPatch):
	"""バッファは最終更新が最も古いキーから破棄されること"""
	_patch_jst_date(monkeypatch)
	monkeypatch.setattr(StatsManager, "MAX_BUFFER_KEYS", 2)

	StatsManager.add_command("a", 1, ok=True)
	StatsManager.add_command("b", 1, ok=True)
	# a を更新して最終更新を最新にする
	StatsManager.add_command("a", 1, ok=True)
	StatsManager.add_command("c", 1, ok=True)

	assert ("2026-09-28", "command", "a", "1") in StatsManager._buffer
	assert ("2026-09-28", "command", "b", "1") not in StatsManager._buffer


def test_record_start():
	"""起動時刻が1度だけ記録されること"""
	StatsManager.record_start()
	started_at = StatsManager.started_at

	assert started_at is not None

	StatsManager.record_start()

	assert StatsManager.started_at == started_at


# バッファの書き込み


def test_build_flush_ops():
	"""バッファが $inc + upsert の操作一覧へ変換されること"""
	buffer = {
		("2026-09-28", "command", "ping", "DM"): {"count": 3, "error_count": 1},
		("2026-09-28", "embed_created", "server_status", "-"): {"count": 5, "error_count": 0},
	}
	updated_at = datetime.datetime(2026, 9, 28, 12, 0, tzinfo=datetime.UTC)

	ops = StatsManager._build_flush_ops(buffer, updated_at)

	assert len(ops) == 2
	assert all(isinstance(op, UpdateOne) for op in ops)
	assert ops[0]._filter == {"date": "2026-09-28", "metric": "command", "dim1": "ping", "dim2": "DM"}
	assert ops[0]._doc == {
		"$inc": {"count": 3, "error_count": 1},
		"$set": {"updated_at": updated_at},
	}
	assert ops[0]._upsert is True


async def test_flush_success(monkeypatch: pytest.MonkeyPatch):
	"""書き込みに成功した場合はバッファが空になること"""
	fake_collection = _FakeCollection()
	_patch_db(monkeypatch)
	monkeypatch.setattr(DBManager, "counters_col", fake_collection, raising=False)
	_patch_jst_date(monkeypatch)
	StatsManager.add_command("ping", 123, ok=True)

	await StatsManager.flush()

	assert len(fake_collection.ops) == 1
	assert StatsManager._buffer == {}


async def test_flush_failure_keeps_buffer(monkeypatch: pytest.MonkeyPatch):
	"""書き込みに失敗した場合はバッファが保持されること"""
	fake_collection = _FakeCollection(bulk_write_exception=RuntimeError("bulk_write failed"))
	_patch_db(monkeypatch)
	monkeypatch.setattr(DBManager, "counters_col", fake_collection, raising=False)
	_patch_jst_date(monkeypatch)
	StatsManager.add_command("ping", 123, ok=True)

	await StatsManager.flush()

	assert StatsManager._buffer[("2026-09-28", "command", "ping", "123")] == {"count": 1, "error_count": 0}


async def test_flush_partial_failure_subtracts_written_only(monkeypatch: pytest.MonkeyPatch):
	"""一部の操作のみ失敗した場合は成功した操作の分だけバッファから減算されること"""
	err = BulkWriteError(
		{
			"writeErrors": [{"index": 1, "code": 11000, "errmsg": "duplicate key"}],
			"writeConcernErrors": [],
			"nInserted": 0,
			"nUpserted": 1,
			"nMatched": 0,
			"nModified": 0,
			"nRemoved": 0,
			"upserted": [],
		}
	)
	fake_collection = _FakeCollection(bulk_write_exception=err)
	_patch_db(monkeypatch)
	monkeypatch.setattr(DBManager, "counters_col", fake_collection, raising=False)
	_patch_jst_date(monkeypatch)
	StatsManager.add_command("ping", 123, ok=True)
	StatsManager.add_embed_created("server_status")

	await StatsManager.flush()

	# 1番目の操作 (ping) は成功したものとして減算され、2番目 (embed_created) は保持される
	assert ("2026-09-28", "command", "ping", "123") not in StatsManager._buffer
	assert StatsManager._buffer[("2026-09-28", "embed_created", "server_status", "-")] == {"count": 1, "error_count": 0}


async def test_flush_write_concern_error_keeps_buffer(monkeypatch: pytest.MonkeyPatch):
	"""WriteConcernError の場合は書き込み可否を判別できないためバッファを保持すること"""
	err = BulkWriteError(
		{
			"writeErrors": [],
			"writeConcernErrors": [{"code": 64, "errmsg": "waiting for replication timed out"}],
			"nInserted": 0,
			"nUpserted": 1,
			"nMatched": 0,
			"nModified": 0,
			"nRemoved": 0,
			"upserted": [],
		}
	)
	fake_collection = _FakeCollection(bulk_write_exception=err)
	_patch_db(monkeypatch)
	monkeypatch.setattr(DBManager, "counters_col", fake_collection, raising=False)
	_patch_jst_date(monkeypatch)
	StatsManager.add_command("ping", 123, ok=True)

	await StatsManager.flush()

	assert StatsManager._buffer[("2026-09-28", "command", "ping", "123")] == {"count": 1, "error_count": 0}


# 集計


async def test_get_today_command_stats(monkeypatch: pytest.MonkeyPatch):
	"""本日のコマンド実行数とエラー数が集計されること"""
	fake_collection = _FakeCollection(aggregate_result=[{"_id": None, "count": 10, "error_count": 2}])
	_patch_db(monkeypatch)
	monkeypatch.setattr(DBManager, "counters_col", fake_collection, raising=False)

	assert await StatsManager.get_today_command_stats() == (10, 2)


async def test_get_today_command_stats_no_data(monkeypatch: pytest.MonkeyPatch):
	"""本日のデータが存在しない場合は (0, 0) が返ること"""
	fake_collection = _FakeCollection(aggregate_result=[])
	_patch_db(monkeypatch)
	monkeypatch.setattr(DBManager, "counters_col", fake_collection, raising=False)

	assert await StatsManager.get_today_command_stats() == (0, 0)


async def test_get_today_command_stats_not_connected(monkeypatch: pytest.MonkeyPatch):
	"""データベース未接続の場合は None が返ること"""
	monkeypatch.setattr(DBManager, "connected", False)

	assert await StatsManager.get_today_command_stats() is None


# ギルド関連


async def test_upsert_guilds_snapshot_fields(monkeypatch: pytest.MonkeyPatch):
	"""定期スナップショットでアクティブ状態を更新せず、人数を補完して保存すること"""
	fake_collection = _FakeCollection()
	_patch_db(monkeypatch)
	monkeypatch.setattr(DBManager, "guilds_col", fake_collection, raising=False)
	guild = _FakeGuild()
	guild_without_count = _FakeGuild(guild_id=456, member_count=None)

	await StatsManager.upsert_guilds([guild, guild_without_count])

	assert len(fake_collection.ops) == 2
	snapshot_op = fake_collection.ops[0]
	assert snapshot_op._doc["$set"]["name"] == "テストギルド"
	assert snapshot_op._doc["$set"]["icon"] == "icon_key"
	assert snapshot_op._doc["$set"]["member_count"] == 42
	assert snapshot_op._doc["$set"]["preferred_locale"] == "ja"
	assert "is_active" not in snapshot_op._doc["$set"]
	assert "left_at" not in snapshot_op._doc["$set"]
	assert snapshot_op._doc["$setOnInsert"]["is_active"] is True
	assert snapshot_op._doc["$setOnInsert"]["joined_at"] is not None
	assert snapshot_op._upsert is True
	# 人数が取得できない場合は 0 として保存する
	assert fake_collection.ops[1]._doc["$set"]["member_count"] == 0


async def test_upsert_guild_marks_active(monkeypatch: pytest.MonkeyPatch):
	"""再参加時はギルドをアクティブ状態へ戻して保存すること"""
	fake_collection = _FakeCollection()
	_patch_db(monkeypatch)
	monkeypatch.setattr(DBManager, "guilds_col", fake_collection, raising=False)

	await StatsManager.upsert_guild(_FakeGuild())

	op = fake_collection.ops[0]
	assert op._doc["$set"]["is_active"] is True
	assert op._doc["$set"]["left_at"] is None


async def test_mark_guild_left_fields(monkeypatch: pytest.MonkeyPatch):
	"""脱退時はギルド情報一式と脱退日時が保存されること"""
	fake_collection = _FakeCollection()
	_patch_db(monkeypatch)
	monkeypatch.setattr(DBManager, "guilds_col", fake_collection, raising=False)

	await StatsManager.mark_guild_left(_FakeGuild())

	_, update, upsert = fake_collection.updates[0]
	assert update["$set"]["is_active"] is False
	assert update["$set"]["left_at"] is not None
	assert update["$set"]["icon"] == "icon_key"
	assert update["$set"]["member_count"] == 42
	assert update["$set"]["preferred_locale"] == "ja"
	assert update["$setOnInsert"]["joined_at"] is not None
	assert upsert is True


async def test_record_guild_event_inserts_document(monkeypatch: pytest.MonkeyPatch):
	"""ギルドの参加 / 脱退イベントが記録されること"""
	fake_collection = _FakeCollection()
	_patch_db(monkeypatch)
	monkeypatch.setattr(DBManager, "events_col", fake_collection, raising=False)

	await StatsManager.record_guild_event("leave", _FakeGuild())

	document = fake_collection.inserted[0]
	assert document["type"] == "leave"
	assert document["guild_id"] == "123"
	assert document["guild_name"] == "テストギルド"
	assert document["member_count"] == 42


# スナップショット


async def test_collect_snapshot(monkeypatch: pytest.MonkeyPatch):
	"""スナップショットが収集して保存されること"""
	fake_counts = _FakeCollection(count_result=3)
	fake_snapshots = _FakeCollection()
	_patch_db(monkeypatch)
	monkeypatch.setattr(DBManager, "col", fake_counts, raising=False)
	monkeypatch.setattr(DBManager, "snapshots_col", fake_snapshots, raising=False)
	client = _FakeClient([_FakeGuild(member_count=10)], cog=_FakeCog())

	await StatsManager.collect_snapshot(client)

	snapshot = fake_snapshots.inserted[0]
	assert snapshot["guild_count"] == 1
	assert snapshot["total_member_count"] == 10
	assert snapshot["latency_ms"] == 50
	assert snapshot["version"] == App.VERSION_STRING
	assert snapshot["status_message_guilds"] == 3
	assert snapshot["notification_guilds"] == 3
	assert snapshot["update_loop_ms"] == 1500
	assert snapshot["embeds_last_update"] == 8
