import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from PIL import Image

from app.services.ocr.model import OpenRouterOCRService, _is_rate_limit_error


@pytest.fixture
def mock_image() -> Image.Image:
    return Image.new("RGB", (100, 100), color=(0, 0, 0))


@pytest.fixture
def service() -> OpenRouterOCRService:
    return OpenRouterOCRService(
        api_key="dummy-test-key",
        model="google/gemma-4-26b-a4b-it:free",
    )


def _make_response(content: str) -> MagicMock:
    msg = MagicMock()
    msg.content = content
    choice = MagicMock()
    choice.message = msg
    resp = MagicMock()
    resp.choices = [choice]
    return resp


def _mock_openrouter(send_async: AsyncMock) -> tuple[Any, MagicMock]:
    """OpenRouter の async context manager をモックするヘルパー。"""
    mock_client = MagicMock()
    mock_client.chat.send_async = send_async

    mock_cls = MagicMock()
    mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
    mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

    return patch("app.services.ocr.model.OpenRouter", mock_cls), mock_client


async def test_recognize_returns_damages(
    service: OpenRouterOCRService, mock_image: Image.Image
) -> None:
    send = AsyncMock(return_value=_make_response(json.dumps({"damages": [100, 200, 300]})))
    ctx, _ = _mock_openrouter(send)

    with ctx:
        async with service:
            result = await service.recognize(mock_image)

    assert result.damages == [100, 200, 300]


async def test_recognize_filters_non_positive_values(
    service: OpenRouterOCRService, mock_image: Image.Image
) -> None:
    send = AsyncMock(return_value=_make_response(json.dumps({"damages": [-50, 0, 100, 200]})))
    ctx, _ = _mock_openrouter(send)

    with ctx:
        async with service:
            result = await service.recognize(mock_image)

    assert result.damages == [100, 200]


async def test_recognize_strips_markdown_code_block(
    service: OpenRouterOCRService, mock_image: Image.Image
) -> None:
    send = AsyncMock(return_value=_make_response('```json\n{"damages": [500]}\n```'))
    ctx, _ = _mock_openrouter(send)

    with ctx:
        async with service:
            result = await service.recognize(mock_image)

    assert result.damages == [500]


async def test_recognize_empty_damages(
    service: OpenRouterOCRService, mock_image: Image.Image
) -> None:
    send = AsyncMock(return_value=_make_response(json.dumps({"damages": []})))
    ctx, _ = _mock_openrouter(send)

    with ctx:
        async with service:
            result = await service.recognize(mock_image)

    assert result.damages == []


async def test_recognize_retries_on_failure_then_succeeds(
    service: OpenRouterOCRService, mock_image: Image.Image
) -> None:
    success = _make_response(json.dumps({"damages": [150]}))
    send = AsyncMock(side_effect=[Exception("API error"), success])
    ctx, mock_client = _mock_openrouter(send)

    with ctx:
        async with service:
            with patch("asyncio.sleep", new_callable=AsyncMock):
                result = await service.recognize(mock_image)

    assert result.damages == [150]
    assert mock_client.chat.send_async.call_count == 2


async def test_recognize_raises_after_max_retries(
    service: OpenRouterOCRService, mock_image: Image.Image
) -> None:
    send = AsyncMock(side_effect=Exception("API error"))
    ctx, mock_client = _mock_openrouter(send)

    with ctx:
        async with service:
            with patch("asyncio.sleep", new_callable=AsyncMock):
                with pytest.raises(Exception, match="API error"):
                    await service.recognize(mock_image)

    assert mock_client.chat.send_async.call_count == 5


async def test_recognize_rate_limit_waits_longer(
    service: OpenRouterOCRService, mock_image: Image.Image
) -> None:
    success = _make_response(json.dumps({"damages": [200]}))
    send = AsyncMock(side_effect=[Exception("429 Too Many Requests"), success])
    ctx, _ = _mock_openrouter(send)

    with ctx:
        async with service:
            with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
                result = await service.recognize(mock_image)

    assert result.damages == [200]
    mock_sleep.assert_called_once_with(30)


def test_is_rate_limit_error_detects_429() -> None:
    assert _is_rate_limit_error(Exception("429 Too Many Requests"))
    assert _is_rate_limit_error(Exception("Provider returned error: too many requests"))
    assert _is_rate_limit_error(Exception("rate limit exceeded"))
    assert not _is_rate_limit_error(Exception("Provider returned error"))
    assert not _is_rate_limit_error(Exception("API error"))


async def test_recognize_raises_without_context_manager(
    service: OpenRouterOCRService, mock_image: Image.Image
) -> None:
    with pytest.raises(RuntimeError, match="not initialized"):
        await service.recognize(mock_image)
