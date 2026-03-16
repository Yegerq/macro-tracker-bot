from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class ParsedMeal:
    calories: float
    carbs: float
    protein: float
    fat: float


@dataclass(frozen=True)
class DailyTotals:
    logged_date: date
    meal_count: int
    calories: float
    carbs: float
    protein: float
    fat: float
