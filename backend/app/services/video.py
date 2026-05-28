import asyncio
import concurrent.futures
import logging
import subprocess
import threading
from io import BytesIO
from typing import AsyncIterator

from botocore.response import StreamingBody
from PIL import Image

logger = logging.getLogger(__name__)

_SOI = b"\xff\xd8"
_EOI = b"\xff\xd9"
_CHUNK_SIZE = 1024 * 1024  # 1 MB
_FPS = 2
_SENTINEL = object()


async def extract_frames(body: StreamingBody) -> AsyncIterator[tuple[int, int, Image.Image]]:
    """R2 StreamingBody から FFmpeg でフレームを抽出し (frame_index, timestamp_ms, image) を yield する。"""
    loop = asyncio.get_running_loop()
    queue: asyncio.Queue = asyncio.Queue(maxsize=10)
    stop_event = threading.Event()

    def _enqueue(item: object) -> None:
        """スレッドから asyncio キューに積む。stop_event が立ったら即返す。"""
        if stop_event.is_set():
            return
        try:
            fut = asyncio.run_coroutine_threadsafe(queue.put(item), loop)
            while not stop_event.is_set():
                try:
                    fut.result(timeout=0.1)
                    return
                except concurrent.futures.TimeoutError:
                    continue
            fut.cancel()
        except Exception:
            pass

    def producer() -> None:
        try:
            try:
                proc = subprocess.Popen(
                    [
                        "ffmpeg",
                        "-i", "pipe:0",
                        "-vf", f"fps={_FPS}",
                        "-f", "image2pipe",
                        "-vcodec", "mjpeg",
                        "-q:v", "3",
                        "pipe:1",
                    ],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
            except FileNotFoundError as exc:
                raise RuntimeError("ffmpeg がインストールされていません") from exc

            stderr_chunks: list[bytes] = []

            def read_stderr() -> None:
                assert proc.stderr is not None
                try:
                    while True:
                        chunk = proc.stderr.read(4096)
                        if not chunk:
                            break
                        stderr_chunks.append(chunk)
                except Exception:
                    pass

            def write_stdin() -> None:
                try:
                    while not stop_event.is_set():
                        chunk = body.read(_CHUNK_SIZE)
                        if not chunk:
                            break
                        proc.stdin.write(chunk)
                except Exception:
                    pass
                finally:
                    try:
                        proc.stdin.close()
                    except Exception:
                        pass

            stderr_thread = threading.Thread(target=read_stderr, daemon=True)
            stderr_thread.start()
            write_thread = threading.Thread(target=write_stdin, daemon=True)
            write_thread.start()

            buffer = bytearray()
            frame_index = 0

            while not stop_event.is_set():
                chunk = proc.stdout.read(65536)
                if not chunk:
                    break
                buffer += chunk

                while not stop_event.is_set():
                    soi = buffer.find(_SOI)
                    if soi == -1:
                        # SOI がチャンク境界をまたぐ可能性があるため末尾 1 バイトだけ保持する
                        if buffer and buffer[-1:] == _SOI[:1]:
                            del buffer[:-1]
                        else:
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
                        _enqueue((frame_index, timestamp_ms, image))
                        frame_index += 1
                    except Exception as exc:
                        logger.warning("フレーム %d のデコードに失敗: %s", frame_index, exc)
                        frame_index += 1

            write_thread.join(timeout=5)
            stderr_thread.join(timeout=5)

            if proc.returncode is None:
                try:
                    proc.terminate()
                except ProcessLookupError:
                    pass
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait()

            if not stop_event.is_set() and proc.returncode != 0:
                stderr_text = b"".join(stderr_chunks).decode("utf-8", errors="replace").strip()
                detail = f": {stderr_text[-500:]}" if stderr_text else ""
                logger.error("ffmpeg stderr: %s", stderr_text)
                raise RuntimeError(f"ffmpeg が失敗しました (returncode={proc.returncode}){detail}")

        except Exception as exc:
            _enqueue(exc)
            return

        _enqueue(_SENTINEL)

    future = loop.run_in_executor(None, producer)

    try:
        while True:
            item = await queue.get()
            if item is _SENTINEL:
                break
            if isinstance(item, Exception):
                raise item
            yield item
    finally:
        stop_event.set()
        # キューを排出して _enqueue のブロックを解除する
        while True:
            try:
                queue.get_nowait()
            except Exception:
                break
        run_loop = asyncio.get_running_loop()
        await run_loop.run_in_executor(None, body.close)
        try:
            await asyncio.wrap_future(future)
        except Exception:
            pass


async def download_youtube_to_r2(url: str, session_id: str) -> None:
    """yt-dlp で YouTube 動画をダウンロードし R2 に保存する。"""
    import os
    import shutil
    import tempfile

    from app.services import r2

    # NamedTemporaryFile で事前に空ファイルを作ると Windows で yt-dlp の rename が
    # 失敗し 0 バイトファイルが R2 にアップロードされる問題を避けるため mkdtemp を使う
    tmp_dir = tempfile.mkdtemp()
    tmp_path = os.path.join(tmp_dir, "video.mp4")

    try:
        try:
            result = await asyncio.to_thread(
                subprocess.run,
                [
                    "yt-dlp",
                    "-f", "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]/best[height<=720]",
                    "--merge-output-format", "mp4",
                    "-o", tmp_path,
                    "--no-playlist",
                    url,
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
            )
        except FileNotFoundError as exc:
            raise RuntimeError("yt-dlp がインストールされていません (pip install yt-dlp)") from exc

        if result.returncode != 0:
            stderr_text = (result.stderr or b"").decode("utf-8", errors="replace").strip()
            detail = f": {stderr_text[:300]}" if stderr_text else ""
            raise RuntimeError(f"yt-dlp が失敗しました (returncode={result.returncode}){detail}")

        if not os.path.exists(tmp_path) or os.path.getsize(tmp_path) == 0:
            raise RuntimeError("yt-dlp が動画ファイルを生成しませんでした")

        with open(tmp_path, "rb") as f:
            await r2.upload_fileobj(f, session_id)
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
