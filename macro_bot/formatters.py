from datetime import date
from typing import Optional, Sequence

from .exercises import EXERCISE_CHOICES, get_exercise_label
from .models import DailyTotals, ParsedMeal, PersonalRecord


def format_number(value: float) -> str:
    rounded = round(float(value), 2)
    if rounded.is_integer():
        return str(int(rounded))
    return ("{:.2f}".format(rounded)).rstrip("0").rstrip(".")


def format_summary(title: str, totals: DailyTotals) -> str:
    lines = [
        title,
        "",
        f"Приемов пищи: {totals.meal_count}",
        f"Калории: {format_number(totals.calories)} ккал",
        f"Углеводы: {format_number(totals.carbs)} г",
        f"Белки: {format_number(totals.protein)} г",
        f"Жиры: {format_number(totals.fat)} г",
    ]
    if totals.meal_count == 0:
        lines.extend(["", "Записей за этот день нет."])
    return "\n".join(lines)


def format_confirmation(meal: ParsedMeal, totals: DailyTotals) -> str:
    lines = [
        "Записал прием пищи:",
        f"Калории: {format_number(meal.calories)} ккал",
        f"Углеводы: {format_number(meal.carbs)} г",
        f"Белки: {format_number(meal.protein)} г",
        f"Жиры: {format_number(meal.fat)} г",
        "",
        format_summary("Итого за сегодня", totals),
    ]
    return "\n".join(lines)


def dated_title(prefix: str, logged_date: date) -> str:
    return f"{prefix} {logged_date.strftime('%d.%m.%Y')}"


def format_exercise_result(
    exercise_key: str,
    weight: float,
    previous_record: Optional[PersonalRecord],
) -> str:
    label = get_exercise_label(exercise_key)
    lines = [f"Записал результат: {label} — {format_number(weight)} кг"]

    if previous_record is None:
        lines.append("Это первый результат по этому упражнению.")
        lines.append(f"Текущий PR: {format_number(weight)} кг")
    elif weight > previous_record.weight:
        lines.append(f"Новый PR: {format_number(weight)} кг")
    elif weight == previous_record.weight:
        lines.append(f"Повторил свой PR: {format_number(weight)} кг")
    else:
        lines.append(f"Текущий PR: {format_number(previous_record.weight)} кг")

    return "\n".join(lines)


def format_pr_summary(records: Sequence[PersonalRecord]) -> str:
    record_map = {record.exercise_key: record for record in records}
    lines = ["Твои PR по упражнениям", ""]

    for exercise_key, label in EXERCISE_CHOICES:
        record = record_map.get(exercise_key)
        if record is None:
            lines.append(f"{label}: пока нет записей")
            continue
        lines.append(f"{label}: {format_number(record.weight)} кг")

    return "\n".join(lines)


def format_single_pr(exercise_key: str, record: Optional[PersonalRecord]) -> str:
    label = get_exercise_label(exercise_key)
    if record is None:
        return f"По упражнению {label} пока нет записей."
    return f"Твой PR в упражнении {label}: {format_number(record.weight)} кг"
