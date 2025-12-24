import os
import sys
import unittest

# Ensure src is on path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.transform.data_cleaner import DataCleaner


class TestDataCleaner(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cleaner = DataCleaner()

    def test_clean_study_with_drug_and_conditions(self):
        raw = {
            "nct_id": "NCT_UNIT_001",
            "brief_title": "  lung cancer study  ",
            "phase": "PHASE2",
            "overall_status": "RECRUITING",
            "drugs": [
                {"name": "aspirin", "description": "take one tablet orally"},
                {"name": "placebo", "description": None},
            ],
            "conditions": ["lung cancer", "Lung Cancer"],
            "sponsors": [{"name": "Pfizer Inc", "class": "INDUSTRY"}],
        }

        clean = self.cleaner.clean_study(raw)

        # Title trimmed
        self.assertEqual(clean["title"], "lung cancer study")
        # Conditions deduped and normalized
        self.assertEqual(len(clean["conditions"]), 1)
        self.assertEqual(clean["conditions"][0]["name"], "Lung Cancer")
        # Drugs processed
        self.assertEqual(len(clean["drugs"]), 2)
        drug_names = {d["name"] for d in clean["drugs"]}
        self.assertIn("Aspirin", drug_names)
        # Inference applied to first drug
        aspirin = next(d for d in clean["drugs"] if d["name"] == "Aspirin")
        self.assertEqual(aspirin["route"], "Oral")
        self.assertEqual(aspirin["dosage_form"], "Tablet")
        # Unknown on missing description
        placebo = next(d for d in clean["drugs"] if d["name"] == "Placebo")
        self.assertEqual(placebo["route"], "Unknown")
        self.assertEqual(placebo["dosage_form"], "Unknown")


if __name__ == "__main__":
    unittest.main()

