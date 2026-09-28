"""統計収集 (StatsManager) のユニットテスト

MongoDB への実接続は不要 (データベース操作はフェイクへ差し替える)
"""

import datetime

import pytest
from pymongo import UpdateOne

from db import DBManager
from stats import StatsManager


@pytest.fixture(autouse=True)
def _clear_buffer():
	"""各テストの前後で統計バッファを空にする"""
	StatsManager._buffer.clear()
	yield
	StatsManager._buffer.clear()


class _FakeCollection:
	"""`bulk_write` のみを実装したテスト用コレクション"""

	def __init__(self, *, fail: bool = False) -> None:
		self.fail = fail
		self.ops: list[UpdateOne] = []

	async def bulk_write(self, ops: list[UpdateOne], ordered: bool = False) -> None:
		if self.fail:
			msg = "bulk_write failed"
			raise RuntimeError(msg)
		self.ops.extend(ops)


def _patch_jst_date(monkeypatch: pytest.MonkeyPatch, date: str = "2026-09-28") -> None:
	"""JST 日付変換を固定値へ差し替える"""
	monkeypatch.setattr(StatsManager, "_get_jst_date", classmethod(lambda cls, dt=None: date))


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
	"""バッファの上限に達した場合は最古のキーが破棄されること"""
	_patch_jst_date(monkeypatch)
	monkeypatch.setattr(StatsManager, "MAX_BUFFER_KEYS", 2)

	StatsManager.add_command("a", 1, ok=True)
	StatsManager.add_command("b", 1, ok=True)
	StatsManager.add_command("c", 1, ok=True)

	assert len(StatsManager._buffer) == 2
	assert ("2026-09-28", "command", "a", "1") not in StatsManager._buffer
	assert ("2026-09-28", "command", "c", "1") in StatsManager._buffer


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
	monkeypatch.setattr(DBManager, "connected", True)
	monkeypatch.setattr(DBManager, "counters_col", fake_collection, raising=False)
	_patch_jst_date(monkeypatch)
	StatsManager.add_command("ping", 123, ok=True)

	await StatsManager.flush()

	assert len(fake_collection.ops) == 1
	assert StatsManager._buffer == {}


async def test_flush_failure_keeps_buffer(monkeypatch: pytest.MonkeyPatch):
	"""書き込みに失敗した場合はバッファが保持されること"""
	fake_collection = _FakeCollection(fail=True)
	monkeypatch.setattr(DBManager, "connected", True)
	monkeypatch.setattr(DBManager, "counters_col", fake_collection, raising=False)
	_patch_jst_date(monkeypatch)
	StatsManager.add_command("ping", 123, ok=True)

	await StatsManager.flush()

	assert StatsManager._buffer[("2026-09-28", "command", "ping", "123")] == {"count": 1, "error_count": 0}
