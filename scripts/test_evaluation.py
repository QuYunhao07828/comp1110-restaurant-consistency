"""Unit and isolated workflow tests. Fixtures are not study labels or findings."""
import contextlib
import copy
import csv
from datetime import date
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

import evaluate_reviews as workflow
from review_safety import assert_no_human_inputs, xlsx_has_review_inputs

TODAY = date.today().isoformat()
TEST_TEMP = Path(__file__).resolve().parents[1] / "tmp/review_tests"
TEST_TEMP.mkdir(parents=True, exist_ok=True)


def label(decision, name):
    return {"decision": decision, "reviewer_name": name,
            "evidence_and_reason": "ISOLATED TEST FIXTURE. NOT STUDY EVIDENCE.", "reviewed_at": TODAY}


class MetricsTests(unittest.TestCase):
    def test_saved_study_predictions_reproduce_current_rule(self):
        self.assertEqual(workflow.verify_matching_outputs(), 200)

    def test_perfect(self):
        result = workflow.classification_metrics({"p": "Match", "n": "Non-match"}, {"p": True, "n": False})
        self.assertEqual((result["tp"], result["tn"], result["precision"], result["recall"], result["f1"]), (1, 1, 1, 1, 1))

    def test_false_positive_false_negative_and_exclusion(self):
        result = workflow.classification_metrics({"tp": "Match", "fp": "Non-match", "fn": "Match", "u": "Uncertain"}, {"tp": True, "fp": True, "fn": False, "u": True})
        self.assertEqual((result["reviewed_n"], result["evaluated_n"], result["excluded_uncertain"]), (4, 3, 1))
        self.assertEqual((result["precision"], result["recall"], result["f1"]), (.5, .5, .5))
        self.assertEqual((result["precision_denominator"], result["recall_denominator"]), (2, 2))

    def test_no_automatic_acceptance(self):
        result = workflow.classification_metrics({"p": "Match"}, {"p": False})
        self.assertIsNone(result["precision"])
        self.assertEqual((result["recall"], result["f1"]), (0, 0))

    def test_all_uncertain(self):
        result = workflow.classification_metrics({"u": "Uncertain"}, {"u": True})
        self.assertEqual(result["evaluated_n"], 0)
        self.assertTrue(all(result[k] is None for k in ["precision", "recall", "f1"]))

    def test_only_true_negative(self):
        result = workflow.classification_metrics({"n": "Non-match"}, {"n": False})
        self.assertEqual(result["tn"], 1)
        self.assertTrue(all(result[k] is None for k in ["precision", "recall", "f1"]))

    def test_empty(self):
        self.assertIsNone(workflow.classification_metrics({}, {})["f1"])

    def test_invalid_pair_universe(self):
        with self.assertRaises(ValueError):
            workflow.classification_metrics({"x": "Match"}, {"y": True})

    def test_invalid_label_or_non_boolean_prediction(self):
        for refs, predicted in [({"x": "Wrong"}, {"x": True}), ({"x": "Match"}, {"x": 1})]:
            with self.assertRaises(ValueError):
                workflow.classification_metrics(refs, predicted)

    def test_kappa_opposite_labels(self):
        a = {"x": label("Match", "A"), "y": label("Non-match", "A")}
        b = {"x": label("Non-match", "B"), "y": label("Match", "B")}
        self.assertEqual(workflow.reviewer_agreement(a, b, a)["cohens_kappa"], -1)

    def test_kappa_degenerate(self):
        a, b = {"x": label("Match", "A")}, {"x": label("Match", "B")}
        self.assertIsNone(workflow.reviewer_agreement(a, b, a)["cohens_kappa"])


class AdjudicationTests(unittest.TestCase):
    def setUp(self):
        self.admin = {"p": {"pair_id": "p", "branch_id": "b", "candidate_source": "OSM", "candidate_id": "r", "split": "calibration"}}
        self.a = {"p": label("Match", "TEST REVIEWER A")}
        self.b = {"p": label("Match", "TEST REVIEWER B")}

    def rows(self):
        return workflow.template(self.admin, self.a, self.b, "calibration")

    def resolve(self, rows):
        return workflow.resolved_references(rows, self.admin, self.a, self.b, "calibration")

    def test_consensus_without_fabricated_adjudicator(self):
        self.assertEqual(self.resolve(self.rows()), {"p": "Match"})

    def test_disagreement_needs_third_person(self):
        self.b["p"]["decision"] = "Non-match"
        with self.assertRaises(ValueError):
            self.resolve(self.rows())

    def test_uncertain_consensus_needs_documented_resolution(self):
        self.a["p"]["decision"] = self.b["p"]["decision"] = "Uncertain"
        with self.assertRaises(ValueError):
            self.resolve(self.rows())

    def test_documented_uncertainty_can_remain_uncertain(self):
        self.b["p"]["decision"] = "Uncertain"
        rows = self.rows()
        rows[0].update(final_decision="Uncertain", adjudicator_name="TEST THIRD PERSON", adjudication_evidence="Test only", adjudicated_at=TODAY)
        self.assertEqual(self.resolve(rows), {"p": "Uncertain"})

    def test_initial_reviewer_cannot_adjudicate(self):
        self.b["p"]["decision"] = "Non-match"
        rows = self.rows()
        rows[0].update(final_decision="Match", adjudicator_name=" test reviewer a ", adjudication_evidence="Test", adjudicated_at=TODAY)
        with self.assertRaises(ValueError):
            self.resolve(rows)

    def test_original_label_and_candidate_metadata_preserved(self):
        for field in ["candidate_id", "A_evidence_and_reason", "B_decision"]:
            rows = self.rows(); rows[0][field] = "tampered"
            with self.assertRaises(ValueError):
                self.resolve(rows)

    def test_duplicate_or_missing_rows(self):
        for rows in [[], self.rows() * 2]:
            with self.assertRaises(ValueError):
                self.resolve(rows)


class SafetyTests(unittest.TestCase):
    def test_csv_input_guard(self):
        with tempfile.TemporaryDirectory(prefix="comp1110-TEST-not-study-", dir=TEST_TEMP) as directory:
            root = Path(directory); folder = root / "data/review"; folder.mkdir(parents=True)
            path = folder / "reviewer_A.csv"
            path.write_text("pair_id,decision\np,\n", encoding="utf-8")
            assert_no_human_inputs(root)
            path.write_text("pair_id,decision\np,Match\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                assert_no_human_inputs(root)

    def test_workbook_input_guard(self):
        with tempfile.TemporaryDirectory(prefix="comp1110-TEST-not-study-", dir=TEST_TEMP) as directory:
            path = Path(directory) / "fixture.xlsx"
            for value, expected in [("", False), ("TEST ONLY", True)]:
                with zipfile.ZipFile(path, "w") as archive:
                    archive.writestr("xl/worksheets/sheet1.xml", '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData><row r="8"><c r="J8" t="inlineStr"><is><t>' + value + '</t></is></c></row></sheetData></worksheet>')
                self.assertEqual(xlsx_has_review_inputs(path), expected)

    def test_ingestion_marker_stops_regeneration(self):
        with tempfile.TemporaryDirectory(prefix="comp1110-TEST-not-study-", dir=TEST_TEMP) as directory:
            root = Path(directory); folder = root / "data/review/batch"; folder.mkdir(parents=True)
            (folder / "ingestion.json").write_text("{}", encoding="utf-8")
            with self.assertRaises(ValueError):
                assert_no_human_inputs(root)


class IsolatedWorkflowTests(unittest.TestCase):
    def test_freeze_reveal_evaluate_and_tamper_guards(self):
        # Entire fixture tree is outside study evidence and is automatically removed.
        with tempfile.TemporaryDirectory(prefix="comp1110-TEST-not-study-", dir=TEST_TEMP) as directory:
            root = Path(directory)
            admin, a, b, links = {}, {}, {}, []
            for branch in range(20):
                for candidate in range(3):
                    pair_id = f"TEST-P{branch:02d}-{candidate}"
                    source = "OSM" if candidate != 1 else "Overture"
                    record_id = f"TEST-R{branch:02d}-{candidate}"
                    admin[pair_id] = {"pair_id": pair_id, "branch_id": f"TEST-B{branch}", "candidate_source": source,
                                      "candidate_id": record_id, "split": "calibration" if branch < 7 else "held-out"}
                    a[pair_id] = label("Match" if candidate < 2 else "Non-match", "TEST A NOT REAL LABELS")
                    b[pair_id] = label(a[pair_id]["decision"], "TEST B NOT REAL LABELS")
                    if candidate < 2:
                        links.append({"branch_id": f"TEST-B{branch}", "source": source, "status": "Automatic proposal", "proposed_record_id": record_id})
            for name in workflow.BOUND_FILES:
                path = root / name; path.parent.mkdir(parents=True, exist_ok=True)
                if name.endswith("review_admin.json"):
                    workflow.write_json(path, list(admin.values()))
                elif name.endswith("links.json"):
                    workflow.write_json(path, links)
                else:
                    path.write_text("{}", encoding="utf-8")
            paths = [root / "test_A.csv", root / "test_B.csv"]
            for path, labels in zip(paths, [a, b]):
                workflow.write_csv(path, [{"pair_id": k, "candidate_id": admin[k]["candidate_id"], **v} for k, v in labels.items()])
            calibration = root / "test_calibration.csv"
            workflow.write_csv(calibration, workflow.template(admin, a, b, "calibration"))
            common = ["--reviewer-a", str(paths[0]), "--reviewer-b", str(paths[1])]

            def command(*args):
                # Rule reproduction is separately checked on the real snapshots above.
                with patch.object(workflow, "ROOT", root), patch.object(workflow, "verify_matching_outputs", return_value=40), patch.object(sys, "argv", ["evaluate_reviews.py", *args]), contextlib.redirect_stdout(io.StringIO()):
                    workflow.main()

            command("freeze", *common, "--adjudication", str(calibration), "--owner", "TEST ONLY",
                    "--note", "TEST FIXTURE, NO ACTUAL CALIBRATION", "--attest-held-out-unseen", "--output-dir", str(root / "freeze"))
            freeze = root / "freeze/freeze.json"
            self.assertTrue(freeze.exists())
            command("prepare-held-out", *common, "--freeze", str(freeze), "--output-dir", str(root / "heldout"))
            adjudication = root / "heldout/held_out_adjudication.csv"
            self.assertEqual(len(workflow.read_csv(adjudication)), 39)
            command("evaluate", *common, "--freeze", str(freeze), "--adjudication", str(adjudication), "--output-dir", str(root / "results"))
            result = workflow.read_json(root / "results/evaluation.json")
            self.assertEqual((result["pooled"]["reviewed_n"], result["pooled"]["tp"], result["pooled"]["tn"], result["pooled"]["f1"]), (39, 26, 13, 1))
            with self.assertRaises(SystemExit):
                with contextlib.redirect_stderr(io.StringIO()):
                    command("evaluate", *common, "--freeze", str(freeze), "--adjudication", str(adjudication), "--output-dir", str(root / "results"))
            rule = root / "scripts/analyse.py"; rule.write_text("changed", encoding="utf-8")
            with patch.object(workflow, "ROOT", root), self.assertRaises(ValueError):
                workflow.verify_freeze(freeze, *paths)
            rule.write_text("{}", encoding="utf-8")
            paths[0].write_text("changed", encoding="utf-8")
            with patch.object(workflow, "ROOT", root), self.assertRaises(ValueError):
                workflow.verify_freeze(freeze, *paths)


if __name__ == "__main__":
    unittest.main(verbosity=2)
