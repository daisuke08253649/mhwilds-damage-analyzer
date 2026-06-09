import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from PIL import Image

from app.services.ocr.model import OpenRouterOCRService


@pytest.fixture
def mock_image() -> Image.Image:
    return Image.new("RGB", (100, 100), color=(0, 0, 0))


@pytest.fixture
def service() -> OpenRouterOCRService:
    with patch("app.services.ocr.model.AsyncOpenAI"):
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


async def test_recognize_returns_damages(
    service: OpenRouterOCRService, mock_image: Image.Image
) -> None:
    service._client.chat.completions.create = AsyncMock(
        return_value=_make_response(json.dumps({"damages": [100, 200, 300]}))
    )

    result = await service.recognize(mock_image)

    assert result.damages == [100, 200, 300]


async def test_recognize_filters_non_positive_values(
    service: OpenRouterOCRService, mock_image: Image.Image
) -> None:
    service._client.chat.completions.create = AsyncMock(
        return_value=_make_response(json.dumps({"damages": [-50, 0, 100, 200]}))
    )

    result = await service.recognize(mock_image)

    assert result.damages == [100, 200]


async def test_recognize_strips_markdown_code_block(
    service: OpenRouterOCRService, mock_image: Image.Image
) -> None:
    service._client.chat.completions.create = AsyncMock(
        return_value=_make_response('```json\n{"damages": [500]}\n```')
    )

    result = await service.recognize(mock_image)

    assert result.damages == [500]


async def test_recognize_empty_damages(
    service: OpenRouterOCRService, mock_image: Image.Image
) -> None:
    service._client.chat.completions.create = AsyncMock(
        return_value=_make_response(json.dumps({"damages": []}))
    )

    result = await service.recognize(mock_image)

    assert result.damages == []


async def test_recognize_retries_on_failure_then_succeeds(
    service: OpenRouterOCRService, mock_image: Image.Image
) -> None:
    success = _make_response(json.dumps({"damages": [150]}))
    service._client.chat.completions.create = AsyncMock(
        side_effect=[Exception("API error"), success]
    )

    with patch("asyncio.sleep", new_callable=AsyncMock):
        result = await service.recognize(mock_image)

    assert result.damages == [150]
    assert service._client.chat.completions.create.call_count == 2


async def test_recognize_raises_after_max_retries(
    service: OpenRouterOCRService, mock_image: Image.Image
) -> None:
    service._client.chat.completions.create = AsyncMock(
        side_effect=Exception("API error")
    )

    with patch("asyncio.sleep", new_callable=AsyncMock):
        with pytest.raises(Exception, match="API error"):
            await service.recognize(mock_image)

    assert service._client.chat.completions.create.call_count == 3
