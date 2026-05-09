from typing import Optional


def is_duplicate(damage_value: int, prev_value: Optional[int]) -> bool:
    """連続する同一ダメージ値を重複とみなす。"""
    return damage_value == prev_value


def compute_summary(damage_values: list[int]) -> dict[str, int | float]:
    if not damage_values:
        return {
            "total_damage": 0,
            "max_damage": 0,
            "avg_damage": 0.0,
            "hit_count": 0,
        }
    return {
        "total_damage": sum(damage_values),
        "max_damage": max(damage_values),
        "avg_damage": round(sum(damage_values) / len(damage_values), 2),
        "hit_count": len(damage_values),
    }
