import sqlite3
from datetime import date, datetime
from pathlib import Path
from typing import List

from .models import DailyTotals, ParsedMeal


class MacroDatabase:
    def __init__(self, path: Path):
        self.path = path

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(str(self.path))
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def init_schema(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS chats (
                    chat_id INTEGER PRIMARY KEY,
                    first_seen TEXT NOT NULL,
                    last_seen TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS meals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id INTEGER NOT NULL,
                    logged_date TEXT NOT NULL,
                    logged_at TEXT NOT NULL,
                    calories REAL NOT NULL,
                    carbs REAL NOT NULL,
                    protein REAL NOT NULL,
                    fat REAL NOT NULL,
                    raw_text TEXT NOT NULL,
                    FOREIGN KEY(chat_id) REFERENCES chats(chat_id)
                );

                CREATE TABLE IF NOT EXISTS daily_reports (
                    chat_id INTEGER NOT NULL,
                    report_date TEXT NOT NULL,
                    sent_at TEXT NOT NULL,
                    PRIMARY KEY (chat_id, report_date),
                    FOREIGN KEY(chat_id) REFERENCES chats(chat_id)
                );

                CREATE INDEX IF NOT EXISTS idx_meals_chat_date
                ON meals (chat_id, logged_date);
                """
            )

    def touch_chat(self, chat_id: int, seen_at: datetime) -> None:
        seen_at_value = seen_at.isoformat()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO chats (chat_id, first_seen, last_seen)
                VALUES (?, ?, ?)
                ON CONFLICT(chat_id) DO UPDATE SET last_seen = excluded.last_seen
                """,
                (chat_id, seen_at_value, seen_at_value),
            )

    def add_meal(self, chat_id: int, logged_at: datetime, meal: ParsedMeal, raw_text: str) -> None:
        logged_at_value = logged_at.isoformat()
        logged_date_value = logged_at.date().isoformat()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO chats (chat_id, first_seen, last_seen)
                VALUES (?, ?, ?)
                ON CONFLICT(chat_id) DO UPDATE SET last_seen = excluded.last_seen
                """,
                (chat_id, logged_at_value, logged_at_value),
            )
            connection.execute(
                """
                INSERT INTO meals (
                    chat_id,
                    logged_date,
                    logged_at,
                    calories,
                    carbs,
                    protein,
                    fat,
                    raw_text
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    chat_id,
                    logged_date_value,
                    logged_at_value,
                    meal.calories,
                    meal.carbs,
                    meal.protein,
                    meal.fat,
                    raw_text,
                ),
            )

    def get_daily_totals(self, chat_id: int, logged_date: date) -> DailyTotals:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT
                    COUNT(*) AS meal_count,
                    COALESCE(SUM(calories), 0) AS calories,
                    COALESCE(SUM(carbs), 0) AS carbs,
                    COALESCE(SUM(protein), 0) AS protein,
                    COALESCE(SUM(fat), 0) AS fat
                FROM meals
                WHERE chat_id = ? AND logged_date = ?
                """,
                (chat_id, logged_date.isoformat()),
            ).fetchone()

        return DailyTotals(
            logged_date=logged_date,
            meal_count=int(row["meal_count"]),
            calories=float(row["calories"]),
            carbs=float(row["carbs"]),
            protein=float(row["protein"]),
            fat=float(row["fat"]),
        )

    def list_chat_ids(self) -> List[int]:
        with self._connect() as connection:
            rows = connection.execute("SELECT chat_id FROM chats ORDER BY chat_id").fetchall()
        return [int(row["chat_id"]) for row in rows]

    def was_report_sent(self, chat_id: int, report_date: date) -> bool:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT 1
                FROM daily_reports
                WHERE chat_id = ? AND report_date = ?
                """,
                (chat_id, report_date.isoformat()),
            ).fetchone()
        return row is not None

    def mark_report_sent(self, chat_id: int, report_date: date, sent_at: datetime) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO daily_reports (chat_id, report_date, sent_at)
                VALUES (?, ?, ?)
                ON CONFLICT(chat_id, report_date) DO UPDATE SET sent_at = excluded.sent_at
                """,
                (chat_id, report_date.isoformat(), sent_at.isoformat()),
            )
