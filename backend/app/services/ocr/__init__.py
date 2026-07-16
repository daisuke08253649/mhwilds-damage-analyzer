from app.core.config import get_settings
from app.services.ocr.base import OCRServiceBase
from app.services.ocr.custom_model import CustomModelOCRService
from app.services.ocr.model import GeminiOCRService


def get_ocr_service() -> OCRServiceBase:
    settings = get_settings()
    if settings.ocr_backend == "finetuned":
        return CustomModelOCRService()

    return GeminiOCRService(
        api_key=settings.gemini_api_key,
        model=settings.gemini_model,
        timeout_seconds=settings.gemini_ocr_timeout_seconds,
    )
