from app.core.config import get_settings
from app.services.ocr.base import OCRServiceBase
from app.services.ocr.custom_model import CustomModelOCRService
from app.services.ocr.model import OpenRouterOCRService


def get_ocr_service() -> OCRServiceBase:
    settings = get_settings()
    if settings.ocr_backend == "finetuned":
        return CustomModelOCRService()

    return OpenRouterOCRService(api_key=settings.openrouter_api_key, model=settings.openrouter_model)
