import json
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

from app.services.ocr.model import GeminiOCRService


@pytest.fixture
def mock_image() -> Image.Image:
    return Image.new("RGB", (100, 100), color=(0, 0, 0))


@pytest.fixture
def service() -> GeminiOCRService:
    return GeminiOCRService(api_key="dummy-test-key", model="gemma-4-26b-a4b-it")


def _make_response(content: str | None) -> MagicMock:
    resp = MagicMock()
    resp.text = content
    return resp


async def test_recognize_returns_damages(
    service: GeminiOCRService, mock_image: Image.Image
) -> None:
    resp = _make_response(json.dumps({"damages": [100, 200, 300]}))
    with patch.object(service._client.models, "generate_content", return_value=resp):
        result = await service.recognize(mock_image)

    assert result.damages == [100, 200, 300]


async def test_recognize_filters_non_positive_values(
    service: GeminiOCRService, mock_image: Image.Image
) -> None:
    resp = _make_response(json.dumps({"damages": [-50, 0, 100, 200]}))
    with patch.object(service._client.models, "generate_content", return_value=resp):
        result = await service.recognize(mock_image)

    assert result.damages == [100, 200]


async def test_recognize_strips_markdown_code_block(
    service: GeminiOCRService, mock_image: Image.Image
) -> None:
    resp = _make_response('```json\n{"damages": [500]}\n```')
    with patch.object(service._client.models, "generate_content", return_value=resp):
        result = await service.recognize(mock_image)

    assert result.damages == [500]


async def test_recognize_empty_damages(
    service: GeminiOCRService, mock_image: Image.Image
) -> None:
    resp = _make_response(json.dumps({"damages": []}))
    with patch.object(service._client.models, "generate_content", return_value=resp):
        result = await service.recognize(mock_image)

    assert result.damages == []


async def test_recognize_retries_on_failure_then_succeeds(
    service: GeminiOCRService, mock_image: Image.Image
) -> None:
    success = _make_response(json.dumps({"damages": [150]}))
    with patch.object(
        service._client.models,
        "generate_content",
        side_effect=[Exception("API error"), success],
    ), patch("asyncio.sleep") as mock_sleep:
        result = await service.recognize(mock_image)

    assert result.damages == [150]
    mock_sleep.assert_called_once_with(1)


async def test_recognize_raises_after_max_retries(
    service: GeminiOCRService, mock_image: Image.Image
) -> None:
    with patch.object(
        service._client.models,
        "generate_content",
        side_effect=Exception("API error"),
    ), patch("asyncio.sleep"):
        with pytest.raises(Exception, match="API error"):
            await service.recognize(mock_image)


async def test_recognize_raises_on_safety_filter_none_text(
    service: GeminiOCRService, mock_image: Image.Image
) -> None:
    resp = _make_response(None)
    with patch.object(service._client.models, "generate_content", return_value=resp):
        with patch("asyncio.sleep"):
            with pytest.raises(RuntimeError, match="safety filter"):
                await service.recognize(mock_image)


async def test_recognize_raises_on_safety_filter_exception(
    service: GeminiOCRService, mock_image: Image.Image
) -> None:
    resp = MagicMock()
    type(resp).text = property(lambda self: (_ for _ in ()).throw(ValueError("blocked")))
    with patch.object(service._client.models, "generate_content", return_value=resp):
        with patch("asyncio.sleep"):
            with pytest.raises(RuntimeError, match="safety filter"):
                await service.recognize(mock_image)
