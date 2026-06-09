from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from types import TracebackType

from PIL import Image


@dataclass
class OCRResult:
    damages: list[int] = field(default_factory=list)


class OCRServiceBase(ABC):
    async def __aenter__(self) -> "OCRServiceBase":
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        pass

    @abstractmethod
    async def recognize(self, frame: Image.Image) -> OCRResult:
        """フレーム画像からダメージ数値を認識して返す。"""
        ...
