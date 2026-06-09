import asyncio
import base64
import json
import logging
from io import BytesIO

from openai import AsyncOpenAI
from PIL import Image

from app.services.ocr.base import OCRResult, OCRServiceBase

logger = logging.getLogger(__name__)

_PROMPT = (
    "This is a screenshot from Monster Hunter Wilds gameplay. "
    "Extract all damage numbers visible on screen (floating combat text). "
    'Return ONLY valid JSON in this exact format: {"damages": [number, ...]}. '
    'If no damage numbers are visible, return {"damages": []}. '
    "Do not include any other text."
)
_MAX_RETRIES = 3


class OpenRouterOCRService(OCRServiceBase):
    def __init__(self, api_key: str, model: str) -> None:
        self._client = AsyncOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
        )
        self._model = model

    async def recognize(self, frame: Image.Image) -> OCRResult:
        buf = BytesIO()
        frame.save(buf, format="JPEG")
        b64 = base64.b64encode(buf.getvalue()).decode()
        data_url = f"data:image/jpeg;base64,{b64}"

        for attempt in range(_MAX_RETRIES):
            try:
                response = await self._client.chat.completions.create(
                    model=self._model,
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": _PROMPT},
                                {"type": "image_url", "image_url": {"url": data_url}},
                            ],
                        }
                    ],
                )
                text = response.choices[0].message.content or ""
                return self._parse(text)
            except Exception as exc:
                if attempt < _MAX_RETRIES - 1:
                    wait = 2**attempt
                    logger.warning(
                        "OpenRouter OCR attempt %d failed, retrying in %ds: %s",
                        attempt + 1, wait, exc,
                    )
                    await asyncio.sleep(wait)
                else:
                    logger.error("OpenRouter OCR failed after %d attempts: %s", _MAX_RETRIES, exc)
                    raise
        return OCRResult()

    @staticmethod
    def _parse(text: str) -> OCRResult:
        text = text.strip()

        # マークダウンコードブロックを除去
        if "```" in text:
            parts = text.split("```")
            text = parts[1] if len(parts) > 1 else text
            if text.startswith("json"):
                text = text[4:]

        data = json.loads(text)
        damages = [
            int(d)
            for d in data.get("damages", [])
            if isinstance(d, (int, float)) and d > 0
        ]
        return OCRResult(damages=damages)
