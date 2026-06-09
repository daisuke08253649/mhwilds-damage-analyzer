import pytest

from app.schemas.analysis import DoneEventData
from app.services.aggregator import compute_summary, is_duplicate


def test_is_duplicate_same_value() -> None:
    assert is_duplicate(100, 100) is True


def test_is_duplicate_different_values() -> None:
    assert is_duplicate(100, 200) is False


def test_is_duplicate_none_prev() -> None:
    assert is_duplicate(100, None) is False


def test_compute_summary_empty() -> None:
    result = compute_summary([])
    assert result == DoneEventData(total_damage=0, max_damage=0, avg_damage=0.0, hit_count=0)


def test_compute_summary_single_value() -> None:
    result = compute_summary([500])
    assert result.total_damage == 500
    assert result.max_damage == 500
    assert result.avg_damage == pytest.approx(500.0)
    assert result.hit_count == 1


def test_compute_summary_multiple_values() -> None:
    result = compute_summary([100, 200, 300])
    assert result.total_damage == 600
    assert result.max_damage == 300
    assert result.avg_damage == pytest.approx(200.0)
    assert result.hit_count == 3


def test_compute_summary_avg_rounding() -> None:
    result = compute_summary([1, 2])
    assert result.avg_damage == pytest.approx(1.5)


def test_compute_summary_rounds_to_two_decimals() -> None:
    # 1 + 1 + 2 = 4, avg = 4/3 ≈ 1.333... → 1.33
    result = compute_summary([1, 1, 2])
    assert result.avg_damage == pytest.approx(1.33)
