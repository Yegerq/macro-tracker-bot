import re
from typing import Optional, Pattern, Sequence, Tuple

from .models import ParsedMeal

NUMBER_FRAGMENT = r"(?P<value>\d+(?:[.,]\d+)?)"
GRAM_FRAGMENT = r"(?:г|гр|грамм(?:а|ов)?)"


def _compile_patterns(keywords: Sequence[str], allow_grams: bool) -> Tuple[Pattern[str], Pattern[str]]:
    keyword_fragment = "(?:" + "|".join(keywords) + ")"
    value_first = NUMBER_FRAGMENT
    if allow_grams:
        value_first += rf"\s*(?:{GRAM_FRAGMENT}\s*)?"
    value_first += rf"\s*{keyword_fragment}"

    keyword_first = rf"{keyword_fragment}\s*[:=-]?\s*{NUMBER_FRAGMENT}"
    if allow_grams:
        keyword_first += rf"\s*(?:{GRAM_FRAGMENT})?"

    return (
        re.compile(keyword_first, re.IGNORECASE),
        re.compile(value_first, re.IGNORECASE),
    )


CALORIE_PATTERNS = _compile_patterns(
    ("ккал", "калори(?:я|и|й)", "kcal", "cal(?:orie)?s?"),
    allow_grams=False,
)
CARB_PATTERNS = _compile_patterns(
    ("углевод(?:ы|а|ов)?", "carb(?:s)?"),
    allow_grams=True,
)
PROTEIN_PATTERNS = _compile_patterns(
    ("бел(?:ок|ка|ки|ков)?", "protein(?:s)?"),
    allow_grams=True,
)
FAT_PATTERNS = _compile_patterns(
    ("жир(?:ы|а|ов)?", "fat(?:s)?"),
    allow_grams=True,
)


def _extract_metric(text: str, patterns: Sequence[Pattern[str]]) -> Optional[float]:
    for pattern in patterns:
        match = pattern.search(text)
        if match:
            return float(match.group("value").replace(",", "."))
    return None


def parse_meal(text: str) -> Optional[ParsedMeal]:
    calories = _extract_metric(text, CALORIE_PATTERNS)
    carbs = _extract_metric(text, CARB_PATTERNS)
    protein = _extract_metric(text, PROTEIN_PATTERNS)
    fat = _extract_metric(text, FAT_PATTERNS)

    if None in (calories, carbs, protein, fat):
        return None

    return ParsedMeal(
        calories=calories,
        carbs=carbs,
        protein=protein,
        fat=fat,
    )
