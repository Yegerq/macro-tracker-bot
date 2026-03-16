import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from macro_bot.database import MacroDatabase


class MacroDatabaseExerciseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database = MacroDatabase(Path(self.temp_dir.name) / "macro.sqlite3")
        self.database.init_schema()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_returns_highest_weight_as_personal_record(self) -> None:
        now = datetime(2025, 3, 16, 12, 0, 0)

        self.database.add_exercise_result(1, now, "bench_press", 100)
        self.database.add_exercise_result(1, now + timedelta(minutes=5), "bench_press", 95)
        self.database.add_exercise_result(1, now + timedelta(minutes=10), "bench_press", 105)

        record = self.database.get_personal_record(1, "bench_press")

        self.assertIsNotNone(record)
        self.assertEqual(record.exercise_key, "bench_press")
        self.assertEqual(record.weight, 105)

    def test_groups_personal_records_by_exercise(self) -> None:
        now = datetime(2025, 3, 16, 12, 0, 0)

        self.database.add_exercise_result(1, now, "bench_press", 100)
        self.database.add_exercise_result(1, now + timedelta(minutes=5), "bench_press", 102.5)
        self.database.add_exercise_result(1, now + timedelta(minutes=10), "squat", 140)

        records = self.database.get_personal_records(1)
        record_map = {record.exercise_key: record.weight for record in records}

        self.assertEqual(record_map["bench_press"], 102.5)
        self.assertEqual(record_map["squat"], 140)


if __name__ == "__main__":
    unittest.main()
