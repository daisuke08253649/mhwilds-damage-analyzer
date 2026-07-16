import math

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


def test_settings_defaults_gemini_model_and_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GEMINI_MODEL", raising=False)
    monkeypatch.delenv("GEMINI_OCR_TIMEOUT_SECONDS", raising=False)
    settings = Settings()
    assert settings.gemini_model == "gemini-3.1-flash-lite"
    assert settings.gemini_ocr_timeout_seconds == 45.0


def test_settings_blank_gemini_model_falls_back_to_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GEMINI_MODEL", "")
    settings = Settings()
    assert settings.gemini_model == "gemini-3.1-flash-lite"


def test_settings_gemini_model_can_be_overridden_for_local_testing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GEMINI_MODEL", "gemma-4-26b-a4b-it")
    settings = Settings()
    assert settings.gemini_model == "gemma-4-26b-a4b-it"


@pytest.mark.parametrize(
    "invalid_timeout",
    [0, -1, -0.001, math.nan, math.inf, -math.inf, 0.0005, 0.5, 0.999],
)
def test_settings_rejects_invalid_gemini_ocr_timeout(invalid_timeout: float) -> None:
    with pytest.raises(ValueError, match="GEMINI_OCR_TIMEOUT_SECONDS"):
        Settings(gemini_ocr_timeout_seconds=invalid_timeout)


@pytest.mark.parametrize("valid_timeout", [1, 1.0, 45, 120])
def test_settings_accepts_valid_gemini_ocr_timeout(valid_timeout: float) -> None:
    settings = Settings(gemini_ocr_timeout_seconds=valid_timeout)
    assert settings.gemini_ocr_timeout_seconds == valid_timeout
