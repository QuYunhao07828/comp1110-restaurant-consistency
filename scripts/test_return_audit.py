"""Adversarial audit boundary fixtures, never study labels."""
import unittest
from audit_review_returns import audit_one, calibration_preview


class ReturnAuditBoundaries(unittest.TestCase):
    def setUp(self):
        self.admin = {f"FIX{i}": {"pair_id": f"FIX{i}", "candidate_id": f"node/fixture{i}",
                                 "branch_id": f"BRANCH{i}", "candidate_source": "OSM",
                                 "split": "calibration" if i < 21 else "held-out"} for i in range(60)}
        self.rows = [{"pair_id": k, "candidate_id": v["candidate_id"], "decision": "Non-match",
                      "evidence_and_reason": "Isolated test fixture", "reviewer_name": "Fixture A",
                      "reviewed_at": "2026-11-03"} for k, v in self.admin.items()]

    def test_invalid_held_out_is_not_guessed_or_exported(self):
        self.rows[24]["decision"] = "??"
        audit, valid = audit_one(self.rows, self.admin)
        self.assertEqual(audit["valid_rows"], 59)
        self.assertEqual(audit["error_count"], 1)
        self.assertNotIn("decision_value", audit["errors"][0])
        preview = calibration_preview(self.admin, valid, valid)
        self.assertEqual(len(preview), 21)
        self.assertTrue(all(r["pair_id"] not in {f"FIX{i}" for i in range(21, 60)} for r in preview))

    def test_invalid_calibration_stops_preview(self):
        self.rows[0]["decision"] = "??"
        _, valid = audit_one(self.rows, self.admin)
        self.assertIsNone(calibration_preview(self.admin, valid, valid))

    def test_changed_candidate_is_not_accepted(self):
        self.rows[3]["candidate_id"] = "node/replacement"
        audit, valid = audit_one(self.rows, self.admin)
        self.assertNotIn("FIX3", valid)
        self.assertEqual(audit["errors"][0]["field"], "candidate_id")

    def test_preview_preserves_judgements_and_blank_adjudication(self):
        _, valid = audit_one(self.rows, self.admin)
        preview = calibration_preview(self.admin, valid, valid)
        self.assertEqual(preview[0]["A_decision"], self.rows[0]["decision"])
        for row in preview:
            self.assertEqual(row["final_decision"], "")
            self.assertEqual(row["adjudicator_name"], "")


if __name__ == "__main__":
    unittest.main()
