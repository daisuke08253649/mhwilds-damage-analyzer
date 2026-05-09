import asyncio
import json
import logging
from io import BytesIO

from google import genai
from google.genai import types
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
_MODEL = "gemini-1.5-flash"


class GeminiOCRService(OCRServiceBase):
    def __init__(self, api_key: str) -> None:
        self._client = genai.Client(api_key=api_key)

    async def recognize(self, frame: Image.Image) -> OCRResult:
        for attempt in range(_MAX_RETRIES):
            try:
                return await asyncio.to_thread(self._recognize_sync, frame)
            except Exception as exc:
                if attempt < _MAX_RETRIES - 1:
                    wait = 2**attempt
                    logger.warning(
                        "Gemini OCR attempt %d failed, retrying in %ds: %s",
                        attempt + 1, wait, exc,
                    )
                    await asyncio.sleep(wait)
                else:
                    logger.error("Gemini OCR failed after %d attempts: %s", _MAX_RETRIES, exc)
                    raise
        return OCRResult()

    def _recognize_sync(self, frame: Image.Image) -> OCRResult:
        buf = BytesIO()
        frame.save(buf, format="JPEG")
        image_bytes = buf.getvalue()

        response = self._client.models.generate_content(
            model=_MODEL,
            contents=[
                types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg"),
                _PROMPT,
            ],
        )
        text = response.text
        if text is None:
            logger.warning("Gemini のレスポンスがセーフティフィルターによりブロックされました")
            raise RuntimeError("Gemini response was blocked by safety filter")
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
