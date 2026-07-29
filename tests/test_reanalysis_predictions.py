import unittest

from services.prediction_service import merge_reanalysis_predictions


class ReanalysisPredictionMergeTests(unittest.TestCase):
    def test_merges_new_reanalysis_predictions_without_losing_existing_future_plan(self):
        existing_predictions = [
            {"week": 0, "date": "2026-07-01", "weight": 100.0},
            {"week": 1, "date": "2026-07-08", "weight": 99.0},
            {"week": 2, "date": "2026-07-15", "weight": 98.0},
            {"week": 3, "date": "2026-07-22", "weight": 97.0},
            {"week": 4, "date": "2026-07-29", "weight": 96.0},
        ]
        new_predictions = [
            {"week": 0, "date": "2026-07-15", "weight": 97.5},
            {"week": 1, "date": "2026-07-22", "weight": 96.8},
        ]

        merged = merge_reanalysis_predictions(
            existing_predictions,
            new_predictions,
            current_date="2026-07-20",
        )

        merged_by_week = {entry["week"]: entry for entry in merged}

        self.assertEqual(sorted(merged_by_week.keys()), [0, 1, 2, 3, 4])
        self.assertEqual(merged_by_week[2]["weight"], 97.5)
        self.assertEqual(merged_by_week[3]["weight"], 96.8)
        self.assertEqual(merged_by_week[4]["weight"], 96.0)
        self.assertEqual(merged_by_week[2]["date"], "2026-07-15")
        self.assertEqual(merged_by_week[3]["date"], "2026-07-22")


if __name__ == "__main__":
    unittest.main()
