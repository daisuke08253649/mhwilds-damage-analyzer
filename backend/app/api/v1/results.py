import csv
import io
import json

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response

from app.db.supabase import get_supabase
from app.schemas.analysis import DamageLogItem, DamageLogsResponse, SummaryResponse

router = APIRouter(prefix="/results", tags=["results"])


@router.get("/{session_id}/summary", response_model=SummaryResponse)
async def get_summary(session_id: str) -> SummaryResponse:
    db = await get_supabase()
    result = await db.table("analysis_sessions").select(
        "id, status, total_damage, max_damage, avg_damage, hit_count"
    ).eq("id", session_id).execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="セッションが見つかりません")

    s = result.data[0]
    return SummaryResponse(
        session_id=s["id"],
        total_damage=s["total_damage"] or 0,
        max_damage=s["max_damage"] or 0,
        avg_damage=s["avg_damage"] or 0.0,
        hit_count=s["hit_count"] or 0,
        status=s["status"],
    )


@router.get("/{session_id}/logs", response_model=DamageLogsResponse)
async def get_logs(
    session_id: str,
    page: int = Query(1, ge=1),
    limit: int = Query(100, ge=1, le=500),
) -> DamageLogsResponse:
    db = await get_supabase()

    session = await db.table("analysis_sessions").select("id").eq("id", session_id).execute()
    if not session.data:
        raise HTTPException(status_code=404, detail="セッションが見つかりません")

    offset = (page - 1) * limit
    result = await db.table("damage_logs").select(
        "timestamp_ms, damage_value", count="exact"
    # supabase-py の range() は両端 inclusive: range(start, end) で end 件目まで取得
    ).eq("session_id", session_id).order("timestamp_ms").range(offset, offset + limit - 1).execute()

    logs = [DamageLogItem(timestamp_ms=r["timestamp_ms"], damage_value=r["damage_value"]) for r in result.data]
    return DamageLogsResponse(logs=logs, total=result.count or 0)


@router.get("/{session_id}/export")
async def export_results(
    session_id: str,
    format: str = Query("json", pattern="^(json|csv)$"),
) -> Response:
    db = await get_supabase()

    session = await db.table("analysis_sessions").select("id").eq("id", session_id).execute()
    if not session.data:
        raise HTTPException(status_code=404, detail="セッションが見つかりません")

    result = await db.table("damage_logs").select(
        "timestamp_ms, damage_value"
    ).eq("session_id", session_id).order("timestamp_ms").execute()

    if format == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["timestamp_ms", "damage_value"])
        for row in result.data:
            writer.writerow([row["timestamp_ms"], row["damage_value"]])
        return Response(
            content=output.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=damage_log_{session_id}.csv"},
        )

    return Response(
        content=json.dumps(result.data, ensure_ascii=False),
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename=damage_log_{session_id}.json"},
    )
