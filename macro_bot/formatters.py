from datetime import date

from .models import DailyTotals, ParsedMeal


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
