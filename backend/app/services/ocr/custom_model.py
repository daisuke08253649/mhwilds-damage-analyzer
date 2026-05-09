from PIL import Image

from app.services.ocr.base import OCRResult, OCRServiceBase


class CustomModelOCRService(OCRServiceBase):
    """将来のファインチューニング済みモデル用スタブ。"""

    async def recognize(self, frame: Image.Image) -> OCRResult:
        raise NotImplementedError("CustomModelOCRService is not yet implemented.")
