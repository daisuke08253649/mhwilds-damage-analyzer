import asyncio
import shutil
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.services.video import _drain_and_close_queue, extract_frames

_requires_ffmpeg = pytest.mark.skipif(
    shutil.which("ffmpeg") is None, reason="ffmpeg not available in this environment"
)


class _FakeStreamingBody:
    """StreamingBody 互換の read()/close() のみを持つテスト用ダミー。"""

    def __init__(self, data: bytes) -> None:
        self._pos = 0
        self._data = data
        self.closed = False

    def read(self, size: int = -1) -> bytes:
        if size < 0:
            chunk, self._pos = self._data[self._pos :], len(self._data)
        else:
            chunk = self._data[self._pos : self._pos + size]
            self._pos += len(chunk)
        return chunk

    def close(self) -> None:
        self.closed = True


def _generate_test_video(width: int, height: int, tmp_path: Path) -> bytes:
    out_path = tmp_path / "test_input.mp4"
    subprocess.run(
        [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", f"color=c=blue:s={width}x{height}:d=1:r=10",
            "-pix_fmt", "yuv420p",
            str(out_path),
        ],
        check=True,
        capture_output=True,
    )
    return out_path.read_bytes()


@_requires_ffmpeg
async def test_extract_frames_downscales_when_wider_than_max_width(tmp_path: Path) -> None:
    video_bytes = _generate_test_video(1920, 1080, tmp_path)
    body = _FakeStreamingBody(video_bytes)

    mock_settings = MagicMock(frame_max_width=1280)
    with patch("app.services.video.get_settings", return_value=mock_settings):
        frames = [item async for item in extract_frames(body)]

    try:
        assert len(frames) >= 1
        _, _, image = frames[0]
        assert image.size == (1280, 720)
    finally:
        for _, _, image in frames:
            image.close()


@_requires_ffmpeg
async def test_extract_frames_does_not_upscale_when_narrower_than_max_width(tmp_path: Path) -> None:
    video_bytes = _generate_test_video(640, 360, tmp_path)
    body = _FakeStreamingBody(video_bytes)

    mock_settings = MagicMock(frame_max_width=1280)
    with patch("app.services.video.get_settings", return_value=mock_settings):
        frames = [item async for item in extract_frames(body)]

    try:
        assert len(frames) >= 1
        _, _, image = frames[0]
        assert image.size == (640, 360)
    finally:
        for _, _, image in frames:
            image.close()


class _FakeImage:
    def __init__(self) -> None:
        self.closed = False

    def close(self) -> None:
        self.closed = True


async def test_drain_and_close_queue_closes_all_remaining_frames() -> None:
    queue: asyncio.Queue = asyncio.Queue()
    images = [_FakeImage() for _ in range(3)]
    for i, image in enumerate(images):
        queue.put_nowait((i, i * 500, image))
    # フレーム以外の要素（センチネル等）が混ざっていても無視して処理を続けられること
    queue.put_nowait(object())

    _drain_and_close_queue(queue)

    assert all(image.closed for image in images)
    assert queue.empty()
