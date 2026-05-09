from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.security import get_current_user
from app.db.supabase import get_supabase
from app.schemas.analysis import HistoryResponse, HistorySessionItem

router = APIRouter(prefix="/history", tags=["history"])


@router.get("", response_model=HistoryResponse)
async def get_history(
    user_id: Annotated[Optional[str], Depends(get_current_user)],
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
) -> HistoryResponse:
    if not user_id:
        raise HTTPException(status_code=401, detail="認証が必要です")

    db = get_supabase()
    offset = (page - 1) * limit

    result = db.table("analysis_sessions").select(
        "id, video_name, total_damage, created_at", count="exact"
    ).eq("user_id", user_id).order("created_at", desc=True).range(offset, offset + limit - 1).execute()

    sessions = [
        HistorySessionItem(
            id=s["id"],
            video_name=s["video_name"],
            total_damage=s["total_damage"],
            created_at=s["created_at"],
        )
        for s in result.data
    ]
    return HistoryResponse(sessions=sessions, total=result.count or 0)
