from typing import Optional

EXERCISE_CHOICES = (
    ("bench_press", "Жим"),
    ("squat", "Приседание"),
    ("deadlift", "Становая"),
)

EXERCISE_LABELS = {key: label for key, label in EXERCISE_CHOICES}
EXERCISE_ALIASES = {
    "bench_press": "bench_press",
    "bench press": "bench_press",
    "bench": "bench_press",
    "press": "bench_press",
    "жим": "bench_press",
    "squat": "squat",
    "присед": "squat",
    "приседание": "squat",
    "deadlift": "deadlift",
    "dead_lift": "deadlift",
    "dead lift": "deadlift",
    "становая": "deadlift",
    "становая тяга": "deadlift",
    "становая_тяга": "deadlift",
}


def get_exercise_label(exercise_key: str) -> str:
    return EXERCISE_LABELS.get(exercise_key, exercise_key)


def parse_exercise_name(text: str) -> Optional[str]:
    normalized = text.strip().lower().replace("-", " ").replace("_", " ")
    normalized = " ".join(normalized.split())
    return EXERCISE_ALIASES.get(normalized)
