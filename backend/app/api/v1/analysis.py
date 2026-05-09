import asyncio
import json
import logging
from collections.abc import AsyncIterable

from fastapi import APIRouter
from fastapi.sse import EventSourceResponse, ServerSentEvent

from app.core.sse import sse_manager
from app.db.supabase import get_supabase

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/analysis", tags=["analysis"])


@router.get("/{session_id}/stream", response_class=EventSourceResponse)
async def stream_analysis(session_id: str) -> AsyncIterable[ServerSentEvent]:
    db = get_supabase()

    result = db.table("analysis_sessions").select(
        "status, total_damage, max_damage, avg_damage, hit_count"
    ).eq("id", session_id).execute()

    if not result.data:
        yield ServerSentEvent(
            data=json.dumps({"message": "セッションが見つかりません"}),
            event="error",
        )
        return

    session = result.data[0]

    # 処理完了済み: 即座に done イベントを返す
    if session["status"] == "done":
        yield ServerSentEvent(
            data=json.dumps({
                "total_damage": session["total_damage"] or 0,
                "max_damage": session["max_damage"] or 0,
                "avg_damage": session["avg_damage"] or 0.0,
                "hit_count": session["hit_count"] or 0,
            }),
            event="done",
        )
        return

    # エラー状態
    if session["status"] == "error":
        yield ServerSentEvent(
            data=json.dumps({"message": "処理中にエラーが発生しました"}),
            event="error",
        )
        return

    # キューのライフサイクルはバックグラウンドタスク側で管理する。
    # ここでは remove() を呼ばず、再接続時に同一キューを再利用できるようにする。
    queue = sse_manager.get_or_create(session_id)
    while True:
        try:
            item = await asyncio.wait_for(queue.get(), timeout=1800.0)
        except asyncio.TimeoutError:
            yield ServerSentEvent(
                data=json.dumps({"message": "処理がタイムアウトしました"}),
                event="error",
            )
            return

        if item is None:
            return

        yield ServerSentEvent(
            data=json.dumps(item["data"]),
            event=item["event"],
        )

        if item["event"] in ("done", "error"):
            return
