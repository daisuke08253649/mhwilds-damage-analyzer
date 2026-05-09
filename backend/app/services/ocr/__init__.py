from app.core.config import get_settings
from app.services.ocr.base import OCRServiceBase


def get_ocr_service() -> OCRServiceBase:
    settings = get_settings()
    if settings.ocr_backend == "finetuned":
        from app.services.ocr.custom_model import CustomModelOCRService
        return CustomModelOCRService()
    from app.services.ocr.gemini import GeminiOCRService
    return GeminiOCRService(api_key=settings.gemini_api_key)
