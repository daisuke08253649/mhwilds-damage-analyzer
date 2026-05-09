from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from PIL import Image


@dataclass
class OCRResult:
    damages: list[int] = field(default_factory=list)


class OCRServiceBase(ABC):
    @abstractmethod
    async def recognize(self, frame: Image.Image) -> OCRResult:
        """フレーム画像からダメージ数値を認識して返す。"""
        ...
