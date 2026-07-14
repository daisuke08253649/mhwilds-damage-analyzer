import asyncio
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, Optional

import magic
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, UploadFile

from app.core.security import get_current_user, limiter
from app.core.sse import sse_manager
from app.db.supabase import get_supabase
from app.schemas.analysis import UploadFileResponse, YoutubeUploadRequest, YoutubeUploadResponse
from app.services import aggregator, r2, video
from app.services.ocr import get_ocr_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/upload", tags=["upload"])

_ALLOWED_MIME = {"video/mp4", "video/quicktime", "video/x-msvideo"}
_ALLOWED_EXT = {".mp4", ".mov", ".avi"}
_YOUTUBE_RE = re.compile(
    r"^https?://(www\.)?(youtube\.com/watch\?.*v=|youtu\.be/)[A-Za-z0-9_\-]{11}"
)


async def _process_video(session_id: str, user_id: Optional[str]) -> None:
    """バックグラウンド処理: R2 → FFmpeg → OCR → DB 保存 → SSE 配信。"""
    db = await get_supabase()
    ocr = get_ocr_service()
    queue = sse_manager.get_or_create(session_id)

    try:
        await db.table("analysis_sessions").update({"status": "processing"}).eq("id", session_id).execute()

        body = await r2.get_streaming_body(session_id)
        damage_values: list[int] = []
        prev_damage: Optional[int] = None

        async with ocr:
            async for frame_index, timestamp_ms, image in video.extract_frames(body):
                try:
                    result = await ocr.recognize(image)
                finally:
                    image.close()
                for damage_value in result.damages:
                    if aggregator.is_duplicate(damage_value, prev_damage):
                        continue
                    prev_damage = damage_value
                    damage_values.append(damage_value)

                    if user_id:
                        await db.table("damage_logs").insert({
                            "session_id": session_id,
                            "timestamp_ms": timestamp_ms,
                            "damage_value": damage_value,
                            "frame_index": frame_index,
                        }).execute()

                    # 動画の総フレーム数は事前不明のため、最大 50 分（3,000,000ms）で正規化
                    progress = min(99, int(timestamp_ms / (50 * 60 * 1000) * 100))
                    await queue.put({
                        "event": "damage",
                        "data": {
                            "timestamp_ms": timestamp_ms,
                            "damage_value": damage_value,
                            "progress": progress,
                        },
                    })

        summary = aggregator.compute_summary(damage_values)
        await db.table("analysis_sessions").update({
            "status": "done",
            "completed_at": datetime.now(timezone.utc).isoformat(),
            **summary.model_dump(),
        }).eq("id", session_id).execute()

        await queue.put({"event": "done", "data": summary.model_dump()})
        await queue.put(None)

    except BaseException as exc:
        logger.error("セッション %s の処理に失敗: %s", session_id, exc)
        try:
            await db.table("analysis_sessions").update({"status": "error"}).eq("id", session_id).execute()
        except Exception:
            pass
        try:
            await queue.put({"event": "error", "data": {"message": str(exc) or type(exc).__name__}})
            await queue.put(None)
        except Exception:
            pass
        if isinstance(exc, asyncio.CancelledError):
            raise
    finally:
        try:
            await r2.delete_object(session_id)
        except Exception as exc:
            logger.error("R2 削除に失敗 (session=%s): %s", session_id, exc)
        # キューのライフサイクルはバックグラウンドタスクが管理する。
        # 処理完了（正常・異常問わず）後に削除し、再接続済みSSEクライアントが
        # 古いキューを参照し続けないようにする。
        sse_manager.remove(session_id)


@router.post("/file", status_code=202, response_model=UploadFileResponse)
@limiter.limit("10/hour")
async def upload_file(
    request: Request,
    file: UploadFile,
    background_tasks: BackgroundTasks,
    user_id: Annotated[Optional[str], Depends(get_current_user)] = None,
) -> UploadFileResponse:
    db = await get_supabase()

    # 拡張子チェック
    ext = Path(file.filename or "").suffix.lower()
    if ext not in _ALLOWED_EXT:
        raise HTTPException(status_code=400, detail=f"非対応のファイル形式です: {ext}")

    # MIME タイプチェック（先頭 4096 バイトで判定）
    header = await file.read(4096)
    try:
        mime = magic.from_buffer(header, mime=True)
        if mime not in _ALLOWED_MIME:
            raise HTTPException(status_code=400, detail=f"非対応の MIME タイプです: {mime}")
    except magic.MagicException:
        pass  # libmagic が利用できない場合は拡張子チェックのみ
    await file.seek(0)

    # DB にセッションレコード作成
    result = await db.table("analysis_sessions").insert({
        "user_id": user_id,
        "video_name": file.filename,
        "video_source": "file",
        "status": "pending",
    }).execute()
    session_id = result.data[0]["id"]

    # R2 にストリーミングアップロード
    try:
        await r2.upload_fileobj(file.file, session_id)
    except Exception as exc:
        await db.table("analysis_sessions").update({"status": "error"}).eq("id", session_id).execute()
        raise HTTPException(status_code=500, detail="動画のアップロードに失敗しました") from exc

    background_tasks.add_task(_process_video, session_id=session_id, user_id=user_id)

    return UploadFileResponse(session_id=session_id, status="pending")


@router.post("/youtube", status_code=202, response_model=YoutubeUploadResponse)
@limiter.limit("10/hour")
async def upload_youtube(
    request: Request,
    body: YoutubeUploadRequest,
    background_tasks: BackgroundTasks,
    user_id: Annotated[Optional[str], Depends(get_current_user)] = None,
) -> YoutubeUploadResponse:
    db = await get_supabase()

    if not _YOUTUBE_RE.match(str(body.url)):
        raise HTTPException(status_code=400, detail="有効な YouTube URL を入力してください")

    result = await db.table("analysis_sessions").insert({
        "user_id": user_id,
        "video_name": str(body.url),
        "video_source": "youtube",
        "status": "pending",
    }).execute()
    session_id = result.data[0]["id"]

    async def _youtube_pipeline(sid: str, url: str, uid: Optional[str]) -> None:
        try:
            await video.download_youtube_to_r2(url, sid)
        except Exception as exc:
            logger.exception("YouTube ダウンロード失敗 (session=%s)", sid)
            pipeline_db = await get_supabase()
            try:
                await pipeline_db.table("analysis_sessions").update({"status": "error"}).eq("id", sid).execute()
            except Exception:
                logger.exception("analysis_sessions の error 更新に失敗 (session=%s)", sid)
            queue = sse_manager.get_or_create(sid)
            error_message = str(exc) if str(exc) else type(exc).__name__
            try:
                await queue.put({"event": "error", "data": {"message": error_message}})
                await queue.put(None)
            finally:
                sse_manager.remove(sid)
            return
        await _process_video(sid, uid)  # _process_video の finally で remove される

    background_tasks.add_task(_youtube_pipeline, session_id, str(body.url), user_id)

    return YoutubeUploadResponse(session_id=session_id, status="pending")
