from unittest.mock import AsyncMock, MagicMock, patch

from app.api.v1.upload import _process_video
from app.core.sse import SSEQueueManager


class _FakeImage:
    def __init__(self) -> None:
        self.closed = False

    def close(self) -> None:
        self.closed = True


def _make_db_mock() -> MagicMock:
    mock_db = MagicMock()
    mock_db.table.return_value.update.return_value.eq.return_value.execute = AsyncMock()
    return mock_db


def _make_ocr_mock(*, recognize: AsyncMock) -> MagicMock:
    mock_ocr = MagicMock()
    mock_ocr.recognize = recognize
    mock_ocr.__aenter__ = AsyncMock(return_value=mock_ocr)
    mock_ocr.__aexit__ = AsyncMock(return_value=None)
    return mock_ocr


async def test_process_video_closes_frame_when_ocr_raises() -> None:
    manager = SSEQueueManager()
    session_id = "sess-ocr-error"
    queue = manager.get_or_create(session_id)

    fake_image = _FakeImage()

    async def _fake_extract_frames(body: object):
        yield 0, 0, fake_image

    mock_ocr = _make_ocr_mock(recognize=AsyncMock(side_effect=RuntimeError("boom")))
    mock_db = _make_db_mock()

    with (
        patch("app.api.v1.upload.get_supabase", new=AsyncMock(return_value=mock_db)),
        patch("app.api.v1.upload.sse_manager", manager),
        patch("app.api.v1.upload.r2.get_streaming_body", new=AsyncMock(return_value=object())),
        patch("app.api.v1.upload.r2.delete_object", new=AsyncMock()),
        patch("app.api.v1.upload.video.extract_frames", _fake_extract_frames),
        patch("app.api.v1.upload.get_ocr_service", return_value=mock_ocr),
    ):
        await _process_video(session_id, user_id=None)

    assert fake_image.closed is True

    events = []
    while not queue.empty():
        events.append(queue.get_nowait())
    assert any(e is not None and e["event"] == "error" for e in events)


async def test_process_video_closes_frame_on_success() -> None:
    manager = SSEQueueManager()
    session_id = "sess-ocr-success"
    queue = manager.get_or_create(session_id)

    fake_image = _FakeImage()

    async def _fake_extract_frames(body: object):
        yield 0, 0, fake_image

    ocr_result = MagicMock(damages=[])
    mock_ocr = _make_ocr_mock(recognize=AsyncMock(return_value=ocr_result))
    mock_db = _make_db_mock()

    with (
        patch("app.api.v1.upload.get_supabase", new=AsyncMock(return_value=mock_db)),
        patch("app.api.v1.upload.sse_manager", manager),
        patch("app.api.v1.upload.r2.get_streaming_body", new=AsyncMock(return_value=object())),
        patch("app.api.v1.upload.r2.delete_object", new=AsyncMock()),
        patch("app.api.v1.upload.video.extract_frames", _fake_extract_frames),
        patch("app.api.v1.upload.get_ocr_service", return_value=mock_ocr),
    ):
        await _process_video(session_id, user_id=None)

    assert fake_image.closed is True

    events = []
    while not queue.empty():
        events.append(queue.get_nowait())
    assert any(e is not None and e["event"] == "done" for e in events)
