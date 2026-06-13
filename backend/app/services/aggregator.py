from typing import Optional

from app.schemas.analysis import DoneEventData


def is_duplicate(damage_value: int, prev_value: Optional[int]) -> bool:
    """連続する同一ダメージ値を重複とみなす。"""
    return damage_value == prev_value


def compute_summary(damage_values: list[int]) -> DoneEventData:
    if not damage_values:
        return DoneEventData(total_damage=0, max_damage=0, avg_damage=0.0, hit_count=0)
    total = sum(damage_values)
    return DoneEventData(
        total_damage=total,
        max_damage=max(damage_values),
        avg_damage=round(total / len(damage_values), 2),  # banker's rounding（Python標準）で小数点以下2桁
        hit_count=len(damage_values),
    )
