from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.api.v1.analysis import stream_analysis
from app.core.sse import SSEQueueManager


def _make_db_mock(session_row: dict | None) -> MagicMock:
    """Supabase クライアントのモックを生成する。"""
    mock_db = MagicMock()
    select_result = MagicMock()
    select_result.data = [session_row] if session_row else []
    mock_db.table.return_value.select.return_value.eq.return_value.execute = AsyncMock(
        return_value=select_result
    )
    return mock_db


async def _collect(session_id: str, mock_db: MagicMock, manager: SSEQueueManager) -> list[dict]:
    """ジェネレータからすべての SSE イベントを収集して返す。"""
    events = []
    with (
        patch("app.api.v1.analysis.get_supabase", new=AsyncMock(return_value=mock_db)),
        patch("app.api.v1.analysis.sse_manager", manager),
    ):
        async for event in stream_analysis(session_id=session_id):
            events.append({"event": event.event, "data": event.data})
    return events


@pytest.fixture
def manager() -> SSEQueueManager:
    return SSEQueueManager()


async def test_stream_session_not_found(manager: SSEQueueManager) -> None:
    mock_db = _make_db_mock(None)
    events = await _collect("missing-id", mock_db, manager)

    assert len(events) == 1
    assert events[0]["event"] == "error"
    assert "message" in events[0]["data"]


async def test_stream_done_session_returns_summary(manager: SSEQueueManager) -> None:
    session_row = {
        "status": "done",
        "total_damage": 1500,
        "max_damage": 600,
        "avg_damage": 300.0,
        "hit_count": 5,
        "user_id": None,
    }
    mock_db = _make_db_mock(session_row)
    events = await _collect("done-session", mock_db, manager)

    assert len(events) == 1
    ev = events[0]
    assert ev["event"] == "done"
    data = ev["data"]
    assert data["total_damage"] == 1500
    assert data["max_damage"] == 600
    assert data["avg_damage"] == 300.0
    assert data["hit_count"] == 5


async def test_stream_error_session_returns_error(manager: SSEQueueManager) -> None:
    session_row = {
        "status": "error",
        "total_damage": None,
        "max_damage": None,
        "avg_damage": None,
        "hit_count": None,
        "user_id": None,
    }
    mock_db = _make_db_mock(session_row)
    events = await _collect("error-session", mock_db, manager)

    assert len(events) == 1
    assert events[0]["event"] == "error"



async def test_stream_queue_delivers_damage_and_done(manager: SSEQueueManager) -> None:
    session_row = {
        "status": "processing",
        "total_damage": None,
        "max_damage": None,
        "avg_damage": None,
        "hit_count": None,
        "user_id": None,
    }
    mock_db = _make_db_mock(session_row)

    session_id = "queue-session"
    queue = manager.get_or_create(session_id)
    await queue.put({"event": "damage", "data": {"timestamp_ms": 500, "damage_value": 200, "progress": 10}})
    await queue.put({"event": "damage", "data": {"timestamp_ms": 1000, "damage_value": 350, "progress": 20}})
    await queue.put({
        "event": "done",
        "data": {"total_damage": 550, "max_damage": 350, "avg_damage": 275.0, "hit_count": 2},
    })
    await queue.put(None)

    events = await _collect(session_id, mock_db, manager)
    manager.remove(session_id)

    damage_events = [e for e in events if e["event"] == "damage"]
    done_events = [e for e in events if e["event"] == "done"]

    assert len(damage_events) == 2
    assert damage_events[0]["data"]["damage_value"] == 200
    assert damage_events[1]["data"]["damage_value"] == 350
    assert len(done_events) == 1
    assert done_events[0]["data"]["total_damage"] == 550
