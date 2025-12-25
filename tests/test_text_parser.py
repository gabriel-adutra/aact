import os
import sys
import unittest

# Ensure src is on path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.transform.text_parser import TextParser


class TestTextParser(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.parser = TextParser("config/text_rules.yaml")

    def test_infer_oral_tablet(self):
        text = "Patients will take 10mg tablet orally twice a day."
        result = self.parser.infer_route_and_form(text)
        self.assertEqual(result["route"], "Oral")
        self.assertEqual(result["dosage_form"], "Tablet")

    def test_infer_intravenous(self):
        text = "Drug administered via IV infusion over 30 minutes."
        result = self.parser.infer_route_and_form(text)
        self.assertEqual(result["route"], "Intravenous")
        # Form may remain Unknown because 'infusion' is route-like, not a form keyword
        self.assertIn(result["dosage_form"], {"Unknown", "Injection"})

    def test_infer_unknown_on_empty(self):
        result = self.parser.infer_route_and_form(None)
        self.assertEqual(result["route"], "Unknown")
        self.assertEqual(result["dosage_form"], "Unknown")


if __name__ == "__main__":
    unittest.main()

