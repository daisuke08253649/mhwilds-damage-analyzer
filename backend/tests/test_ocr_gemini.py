import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

import pytest
from PIL import Image

from app.services.ocr.gemini import GeminiOCRService


@pytest.fixture
def mock_image() -> Image.Image:
    return Image.new("RGB", (100, 100), color=(0, 0, 0))


@pytest.fixture
def service() -> GeminiOCRService:
    with patch("app.services.ocr.gemini.genai.Client"):
        return GeminiOCRService(api_key="dummy-test-key-never-used")


async def test_recognize_returns_damages(
    service: GeminiOCRService, mock_image: Image.Image
) -> None:
    mock_response = MagicMock()
    mock_response.text = json.dumps({"damages": [100, 200, 300]})
    service._client.models.generate_content.return_value = mock_response

    result = await service.recognize(mock_image)

    assert result.damages == [100, 200, 300]


async def test_recognize_filters_non_positive_values(
    service: GeminiOCRService, mock_image: Image.Image
) -> None:
    mock_response = MagicMock()
    mock_response.text = json.dumps({"damages": [-50, 0, 100, 200]})
    service._client.models.generate_content.return_value = mock_response

    result = await service.recognize(mock_image)

    assert result.damages == [100, 200]


async def test_recognize_strips_markdown_code_block(
    service: GeminiOCRService, mock_image: Image.Image
) -> None:
    mock_response = MagicMock()
    mock_response.text = '```json\n{"damages": [500]}\n```'
    service._client.models.generate_content.return_value = mock_response

    result = await service.recognize(mock_image)

    assert result.damages == [500]


async def test_recognize_safety_filter_blocked(
    service: GeminiOCRService, mock_image: Image.Image
) -> None:
    mock_response = MagicMock()
    mock_response.text = None
    service._client.models.generate_content.return_value = mock_response

    with patch("asyncio.sleep", new_callable=AsyncMock):
        with pytest.raises(RuntimeError, match="safety filter"):
            await service.recognize(mock_image)


async def test_recognize_response_text_raises_exception(
    service: GeminiOCRService, mock_image: Image.Image
) -> None:
    # SDK が response.text アクセス時に例外を送出するケース（BlockedPromptException 等）
    mock_response = MagicMock()
    type(mock_response).text = PropertyMock(side_effect=ValueError("blocked"))
    service._client.models.generate_content.return_value = mock_response

    with patch("asyncio.sleep", new_callable=AsyncMock):
        with pytest.raises(RuntimeError, match="safety filter"):
            await service.recognize(mock_image)


async def test_recognize_retries_on_failure_then_succeeds(
    service: GeminiOCRService, mock_image: Image.Image
) -> None:
    mock_response = MagicMock()
    mock_response.text = json.dumps({"damages": [150]})
    service._client.models.generate_content.side_effect = [
        Exception("API error"),
        mock_response,
    ]

    with patch("asyncio.sleep", new_callable=AsyncMock):
        result = await service.recognize(mock_image)

    assert result.damages == [150]
    assert service._client.models.generate_content.call_count == 2


async def test_recognize_raises_after_max_retries(
    service: GeminiOCRService, mock_image: Image.Image
) -> None:
    service._client.models.generate_content.side_effect = Exception("API error")

    with patch("asyncio.sleep", new_callable=AsyncMock):
        with pytest.raises(Exception, match="API error"):
            await service.recognize(mock_image)

    assert service._client.models.generate_content.call_count == 3
