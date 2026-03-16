import unittest

from macro_bot.parser import parse_meal


class ParseMealTests(unittest.TestCase):
    def test_parses_standard_russian_format(self) -> None:
        meal = parse_meal("520 ккал, 48 углеводов, 32 белков, 18 жиров")

        self.assertIsNotNone(meal)
        self.assertEqual(meal.calories, 520)
        self.assertEqual(meal.carbs, 48)
        self.assertEqual(meal.protein, 32)
        self.assertEqual(meal.fat, 18)

    def test_parses_keyword_first_with_decimals(self) -> None:
        meal = parse_meal("углеводы 40,5 белки 30 жиры 10,2 ккал 410")

        self.assertIsNotNone(meal)
        self.assertEqual(meal.calories, 410)
        self.assertEqual(meal.carbs, 40.5)
        self.assertEqual(meal.protein, 30)
        self.assertEqual(meal.fat, 10.2)

    def test_returns_none_when_some_metric_is_missing(self) -> None:
        meal = parse_meal("520 ккал, 48 углеводов, 18 жиров")

        self.assertIsNone(meal)


if __name__ == "__main__":
    unittest.main()
