import pytest

from app.core.config import Settings


@pytest.mark.parametrize("invalid_width", [0, -1, -100])
def test_settings_rejects_non_positive_frame_max_width(invalid_width: int) -> None:
    with pytest.raises(ValueError, match="FRAME_MAX_WIDTH"):
        Settings(frame_max_width=invalid_width)


@pytest.mark.parametrize("valid_width", [1, 640, 1280, 3840])
def test_settings_accepts_positive_frame_max_width(valid_width: int) -> None:
    settings = Settings(frame_max_width=valid_width)
    assert settings.frame_max_width == valid_width
