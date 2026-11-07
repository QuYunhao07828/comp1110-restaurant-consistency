"""Boundary tests for AI assistance. Fixtures are not study labels."""
import unittest
from assist_review import validate_curation, build
from pathlib import Path


class AssistanceBoundaries(unittest.TestCase):
    def setUp(self):
        self.e = {"cases": [{"branch_id": "NONPILOT", "source": "OSM", "records": [{"id": "node/test"}],
                              "human_decision": "", "human_name": "", "human_date": "", "human_evidence": ""}],
                  "deferred_pilot_tasks": [{"branch_id": "PILOT"}],
                  "independent_labels_created": 0, "human_searches_created": 0}
        self.c = {"overrides": [{"branch_id": "NONPILOT", "source": "OSM", "selected_ids": ["node/test"]}]}

    def test_valid_ai_only(self):
        self.assertTrue(validate_curation(self.e, self.c))

    def test_unknown_id(self):
        self.c["overrides"][0]["selected_ids"] = ["node/unknown"]
        with self.assertRaises(ValueError): validate_curation(self.e, self.c)

    def test_duplicate_curation(self):
        self.c["overrides"] *= 2
        with self.assertRaises(ValueError): validate_curation(self.e, self.c)

    def test_protected_pilot(self):
        self.c["overrides"][0]["branch_id"] = "PILOT"
        with self.assertRaises(ValueError): validate_curation(self.e, self.c)

    def test_filled_human_input(self):
        self.e["cases"][0]["human_name"] = "Actual fixture reviewer"
        with self.assertRaises(ValueError): validate_curation(self.e, self.c)

    def test_cannot_claim_independent_completion(self):
        self.e["independent_labels_created"] = 1
        with self.assertRaises(ValueError): validate_curation(self.e, self.c)

    def test_unknown_district_fails_before_retrieval(self):
        with self.assertRaisesRegex(ValueError, "four submitted-plan districts"):
            build(Path("unused_fixture_output"), district="Not a study district")


if __name__ == "__main__": unittest.main()
