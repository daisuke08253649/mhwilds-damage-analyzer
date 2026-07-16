import asyncio
import json
import logging
from io import BytesIO

import httpx
from google import genai
from google.genai import types
from PIL import Image

from app.core.config import seconds_to_ms
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
_DEFAULT_TIMEOUT_SECONDS = 45.0

# asyncio.wait_for はスレッド自体を止められないため、外側のタイムアウトだけに
# 頼るとタイムアウト後もリクエストがバックグラウンドで動き続け、リトライのたびに
# スレッドが積み上がってしまう。実際の打ち切りは Client の http_options.timeout
# （SDK が内部で使う httpx のタイムアウト）に行わせ、asyncio.wait_for 側は
# それが機能しなかった場合の保険として少し長めに設定する。
_OUTER_TIMEOUT_BUFFER_SECONDS = 5.0


class GeminiOCRService(OCRServiceBase):
    def __init__(
        self, api_key: str, model: str, timeout_seconds: float = _DEFAULT_TIMEOUT_SECONDS
    ) -> None:
        self._client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(timeout=seconds_to_ms(timeout_seconds)),
        )
        self._model = model
        self._timeout_seconds = timeout_seconds

    async def recognize(self, frame: Image.Image) -> OCRResult:
        outer_timeout = self._timeout_seconds + _OUTER_TIMEOUT_BUFFER_SECONDS
        for attempt in range(_MAX_RETRIES):
            try:
                return await asyncio.wait_for(
                    asyncio.to_thread(self._recognize_sync, frame),
                    timeout=outer_timeout,
                )
            # SDK側のhttp_options.timeoutが打ち切った場合は httpx.TimeoutException、
            # 保険側のasyncio.wait_forが打ち切った場合は asyncio.TimeoutError になる。
            # どちらも利用者から見れば同じ「タイムアウト」なので同じ経路に正規化する。
            except (asyncio.TimeoutError, httpx.TimeoutException) as exc:
                if attempt < _MAX_RETRIES - 1:
                    logger.warning("Gemini OCR attempt %d timed out, retrying", attempt + 1)
                    await asyncio.sleep(2**attempt)
                else:
                    logger.error("Gemini OCR timed out after %d attempts", _MAX_RETRIES)
                    raise RuntimeError(
                        f"Gemini OCR がタイムアウトしました ({self._timeout_seconds:.0f}秒)"
                    ) from exc
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
            model=self._model,
            contents=[
                types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg"),
                _PROMPT,
            ],
        )
        try:
            text = response.text
        except Exception as exc:
            logger.warning("Gemini のレスポンスへのアクセスに失敗しました (safety filter または SDK エラー): %s", exc)
            raise RuntimeError("Gemini response was blocked by safety filter") from exc
        if text is None:
            logger.warning("Gemini のレスポンスがセーフティフィルターによりブロックされました")
            raise RuntimeError("Gemini response was blocked by safety filter")
        text = text.strip()

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
