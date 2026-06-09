import asyncio
import logging
from collections.abc import AsyncIterable
from typing import TypeVar

from fastapi import APIRouter
from fastapi.sse import EventSourceResponse, ServerSentEvent

from app.core.sse import sse_manager
from app.db.supabase import get_supabase
from app.schemas.analysis import DoneEventData, ErrorEventData

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/analysis", tags=["analysis"])

_T = TypeVar("_T", int, float)


def _or_zero(v: _T | None, default: _T) -> _T:
    return v if v is not None else default


@router.get("/{session_id}/stream", response_class=EventSourceResponse)
async def stream_analysis(
    session_id: str,
) -> AsyncIterable[ServerSentEvent]:
    db = await get_supabase()

    result = await db.table("analysis_sessions").select(
        "status, total_damage, max_damage, avg_damage, hit_count"
    ).eq("id", session_id).execute()

    if not result.data:
        yield ServerSentEvent(
            data=ErrorEventData(message="セッションが見つかりません").model_dump(),
            event="error",
        )
        return

    session = result.data[0]

    # 処理完了済み: 即座に done イベントを返す
    if session["status"] == "done":
        yield ServerSentEvent(
            data=DoneEventData(
                total_damage=_or_zero(session["total_damage"], 0),
                max_damage=_or_zero(session["max_damage"], 0),
                avg_damage=_or_zero(session["avg_damage"], 0.0),
                hit_count=_or_zero(session["hit_count"], 0),
            ).model_dump(),
            event="done",
        )
        return

    # エラー状態
    if session["status"] == "error":
        yield ServerSentEvent(
            data=ErrorEventData(message="処理中にエラーが発生しました").model_dump(),
            event="error",
        )
        return

    # キューのライフサイクルはバックグラウンドタスク側で管理する。
    # ここでは remove() を呼ばず、再接続時に同一キューを再利用できるようにする。
    # クライアント切断時は FastAPI が aclose() を呼び CancelledError を発生させる。
    # 暗黙の伝搬でフレームワーク層がクリーンアップを行う。
    queue = sse_manager.get_or_create(session_id)
    while True:
        try:
            item = await asyncio.wait_for(queue.get(), timeout=1800.0)
        except asyncio.TimeoutError:
            yield ServerSentEvent(
                data=ErrorEventData(message="処理がタイムアウトしました").model_dump(),
                event="error",
            )
            return

        if item is None:
            return

        yield ServerSentEvent(
            data=item["data"],
            event=item["event"],
        )

        if item["event"] in ("done", "error"):
            return
