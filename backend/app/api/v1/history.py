from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.core.security import get_current_user_required
from app.db.supabase import get_supabase
from app.schemas.analysis import HistoryResponse, HistorySessionItem

router = APIRouter(prefix="/history", tags=["history"])


@router.get("", response_model=HistoryResponse)
async def get_history(
    user_id: Annotated[str, Depends(get_current_user_required)],
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
) -> HistoryResponse:
    db = await get_supabase()
    offset = (page - 1) * limit

    result = await db.table("analysis_sessions").select(
        "id, video_name, total_damage, status, created_at", count="exact"
    ).eq("user_id", user_id).order("created_at", desc=True).range(offset, offset + limit - 1).execute()

    sessions = [
        HistorySessionItem(
            id=s["id"],
            video_name=s["video_name"],
            total_damage=s["total_damage"],
            status=s["status"],
            created_at=s["created_at"],
        )
        for s in result.data
    ]
    return HistoryResponse(sessions=sessions, total=result.count or 0)
