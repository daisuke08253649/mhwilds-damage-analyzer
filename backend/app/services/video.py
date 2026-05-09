import asyncio
import logging
from io import BytesIO
from typing import AsyncIterator

from botocore.response import StreamingBody
from PIL import Image

logger = logging.getLogger(__name__)

_SOI = b"\xff\xd8"
_EOI = b"\xff\xd9"
_CHUNK_SIZE = 1024 * 1024  # 1 MB
_FPS = 2


async def _drain_stderr(proc: asyncio.subprocess.Process) -> None:
    """FFmpeg の stderr を読み取り、エラー出力をログに残す。"""
    assert proc.stderr is not None
    while True:
        line = await proc.stderr.readline()
        if not line:
            break
        logger.debug("FFmpeg: %s", line.decode("utf-8", errors="replace").rstrip())


async def _write_stdin(proc: asyncio.subprocess.Process, body: StreamingBody) -> None:
    """R2 StreamingBody を FFmpeg の stdin にストリーミングする（別タスクで実行）。"""
    loop = asyncio.get_event_loop()
    try:
        while True:
            chunk = await loop.run_in_executor(None, body.read, _CHUNK_SIZE)
            if not chunk:
                break
            proc.stdin.write(chunk)
            await proc.stdin.drain()
    finally:
        proc.stdin.close()
        await proc.stdin.wait_closed()


async def extract_frames(body: StreamingBody) -> AsyncIterator[tuple[int, int, Image.Image]]:
    """
    R2 StreamingBody から FFmpeg を通じて JPEG フレームを抽出する。
    (frame_index, timestamp_ms, PIL.Image) のタプルを yield する。
    フレームはメモリ上のみで処理し、ディスクには書き込まない。
    """
    proc = await asyncio.create_subprocess_exec(
        "ffmpeg",
        "-i", "pipe:0",
        "-vf", f"fps={_FPS}",
        "-f", "image2pipe",
        "-vcodec", "mjpeg",
        "-q:v", "3",
        "pipe:1",
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    write_task = asyncio.create_task(_write_stdin(proc, body))
    stderr_task = asyncio.create_task(_drain_stderr(proc))

    try:
        buffer = bytearray()
        frame_index = 0

        while True:
            chunk = await proc.stdout.read(65536)
            if not chunk:
                break
            buffer += chunk

            while True:
                soi = buffer.find(_SOI)
                if soi == -1:
                    buffer.clear()
                    break
                eoi = buffer.find(_EOI, soi + 2)
                if eoi == -1:
                    if soi > 0:
                        del buffer[:soi]
                    break
                jpeg_data = bytes(buffer[soi : eoi + 2])
                del buffer[: eoi + 2]
                try:
                    image = Image.open(BytesIO(jpeg_data))
                    image.load()
                    timestamp_ms = frame_index * (1000 // _FPS)
                    yield frame_index, timestamp_ms, image
                    frame_index += 1
                except Exception as exc:
                    logger.warning("フレーム %d のデコードに失敗: %s", frame_index, exc)
                    frame_index += 1
    finally:
        write_task.cancel()
        stderr_task.cancel()
        try:
            await write_task
        except (asyncio.CancelledError, Exception):
            pass
        try:
            await stderr_task
        except (asyncio.CancelledError, Exception):
            pass
        await proc.wait()


async def download_youtube_to_r2(url: str, session_id: str) -> None:
    """yt-dlp で YouTube 動画をダウンロードし R2 に保存する。"""
    import os
    import tempfile

    from app.services import r2

    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        proc = await asyncio.create_subprocess_exec(
            "yt-dlp",
            "-f", "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]/best[height<=720]",
            "--merge-output-format", "mp4",
            "-o", tmp_path,
            "--no-playlist",
            url,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await proc.wait()
        if proc.returncode != 0:
            raise RuntimeError(f"yt-dlp が失敗しました (returncode={proc.returncode})")

        with open(tmp_path, "rb") as f:
            await r2.upload_fileobj(f, session_id)
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
