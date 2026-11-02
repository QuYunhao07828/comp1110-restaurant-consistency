"""Isolated main-review tests. Fixture decisions are never study observations."""
import copy
import contextlib
import csv
from datetime import date
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import finalise_main_review as main


def branch(bid="B1", pilot=False):
    return {"branch_id": bid, "pilot": pilot, "district": "Fixture district", "name_en": "Fixture Cafe",
            "address_en": "Shop 1, 10 Test Road", "aliases": ["Fixture Cafe"], "addresses": ["Shop 1, 10 Test Road"]}


def record(rid):
    return {"id": rid, "aliases": ["Fixture Cafe"], "addresses": ["Shop 1, 10 Test Road"],
            "phones": ["+85223456789"], "category_common": "restaurant", "opening_hours": None,
            "operating_status": None}


def declarations(sample):
    rows = main.templates(sample)
    for r in rows:
        r.update(decision="Confirmed", record_id=r["source"] + r["branch_id"],
                 evidence_and_reason="ISOLATED FIXTURE; NOT STUDY EVIDENCE", reviewer_name="Fixture reviewer",
                 reviewed_at=date.today().isoformat(), ai_assisted="true")
    return rows


class MainReviewTests(unittest.TestCase):
    def setUp(self):
        self.sample = [branch()]
        self.rows = declarations(self.sample)
        self.sources = {src: {src + "B1": record(src + "B1")} for src in main.SOURCES}

    def valid(self):
        return main.validate_rows(self.rows, self.sample, self.sources)

    def test_valid_declarations(self):
        self.assertEqual(len(self.valid()), 2)
        self.assertTrue(all(r["ai_assisted"] for r in self.valid().values()))

    def test_blank_template_is_not_completed_review(self):
        self.rows = main.templates(self.sample)
        with self.assertRaises(ValueError): self.valid()

    def test_missing_task_rejected(self):
        self.rows.pop()
        with self.assertRaises(ValueError): self.valid()

    def test_duplicate_task_rejected(self):
        self.rows.append(copy.deepcopy(self.rows[0]))
        with self.assertRaises(ValueError): self.valid()

    def test_wrong_source_or_branch_rejected(self):
        self.rows[0]["source"] = "Other"
        with self.assertRaises(ValueError): self.valid()

    def test_missing_record_id_rejected(self):
        self.rows[0]["record_id"] = ""
        with self.assertRaises(ValueError): self.valid()

    def test_foreign_record_id_rejected(self):
        self.rows[0]["record_id"] = "OvertureB1"
        with self.assertRaises(ValueError): self.valid()

    def test_evidence_name_date_required(self):
        for field in ["evidence_and_reason", "reviewer_name", "reviewed_at"]:
            rows = copy.deepcopy(self.rows)
            rows[0][field] = ""
            with self.assertRaises(ValueError): main.validate_rows(rows, self.sample, self.sources)

    def test_ai_disclosure_required(self):
        self.rows[0]["ai_assisted"] = ""
        with self.assertRaises(ValueError): self.valid()

    def test_pilot_requires_freeze_gate(self):
        self.sample[0]["pilot"] = True
        with self.assertRaises(ValueError): self.valid()
        self.assertEqual(len(main.validate_rows(self.rows, self.sample, self.sources, pilot_allowed=True)), 2)

    def test_duplicate_selected_record_across_branches(self):
        self.sample.append(branch("B2"))
        self.rows = declarations(self.sample)
        self.sources = {src: {src + b["branch_id"]: record(src + b["branch_id"]) for b in self.sample} for src in main.SOURCES}
        self.rows[2]["record_id"] = self.rows[0]["record_id"]
        with self.assertRaises(ValueError): self.valid()

    def test_district_cannot_be_changed(self):
        self.rows[0]["district"] = "Wrong district"
        with self.assertRaises(ValueError): self.valid()

    def test_no_counterpart_cannot_keep_selected_id(self):
        self.rows[0]["decision"] = "No counterpart confirmed"
        with self.assertRaises(ValueError): self.valid()

    def test_unconfirmed_is_not_compared(self):
        self.rows[0].update(decision="Uncertain", record_id="")
        observations = main.field_observations(self.sample, self.valid(), self.sources)
        self.assertEqual(len(observations), 18)
        osm_name = next(r for r in observations if r["pair"] == "FEHD vs OSM" and r["field"] == "name")
        self.assertEqual(osm_name["state"], "Ambiguous match")

    def test_schema_omission_not_disagreement(self):
        observations = main.field_observations(self.sample, self.valid(), self.sources)
        self.assertTrue(all(r["state"] == "Non-comparable" for r in observations if r["field"] == "opening_hours"))

    def test_missing_phone_is_unavailable(self):
        self.sources["OSM"]["OSMB1"]["phones"] = []
        observations = main.field_observations(self.sample, self.valid(), self.sources)
        phone = next(r for r in observations if r["pair"] == "OSM vs Overture" and r["field"] == "phone")
        self.assertEqual(phone["state"], "Unavailable")

    def test_agreement_denominators_and_no_truth_metrics(self):
        reviewed = self.valid()
        fields = main.field_observations(self.sample, reviewed, self.sources)
        coverage, summary = main.summaries(self.sample, reviewed, fields)
        self.assertTrue(all(r["confirmed"] == r["sample_n"] == 1 for r in coverage))
        self.assertTrue(all(r["comparable_n"] == r["agree"] + r["disagree"] for r in summary))
        self.assertTrue(all(r["agreement"] is None for r in summary if r["comparable_n"] == 0))

    def test_no_confirmed_counterpart_retains_denominator(self):
        for r in self.rows: r.update(decision="No counterpart confirmed", record_id="")
        reviewed = self.valid()
        coverage, summary = main.summaries(self.sample, reviewed, main.field_observations(self.sample, reviewed, self.sources))
        self.assertTrue(all(r["sample_n"] == 1 and r["confirmed"] == 0 and r["reviewed_link_coverage"] == 0 for r in coverage))
        self.assertTrue(all(r["agreement"] is None for r in summary))


class MainReviewWorkflowTests(unittest.TestCase):
    def setUp(self):
        sandbox = Path(__file__).resolve().parents[1] / "tmp/main_review_tests"
        sandbox.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=sandbox)
        self.root = Path(self.temp.name)
        (self.root / "data/processed").mkdir(parents=True)
        (self.root / "docs").mkdir()
        self.sample = [branch(f"FIXTURE{i}") for i in range(100)]
        self.sample_path = self.root / "data/processed/sample_100_enriched.json"
        self.sample_path.write_text(json.dumps(self.sample), encoding="utf-8")
        self.sources = {}
        for src, filename in [("OSM", "osm_records.json"), ("Overture", "overture_records.json")]:
            p = self.root / "data/processed" / filename
            records = [record(src + b["branch_id"]) for b in self.sample]
            p.write_text(json.dumps(records), encoding="utf-8")
            self.sources[src] = p
        paths = [self.sample_path, *self.sources.values()]
        (self.root / "docs/evidence_manifest.json").write_text(json.dumps({"scope": "ISOLATED FIXTURE, NOT STUDY DATA",
            "files": [{"path": p.relative_to(self.root).as_posix(), "sha256": main.digest(p)} for p in paths]}), encoding="utf-8")

    def tearDown(self): self.temp.cleanup()

    def run_cli(self, arguments):
        with patch.object(main, "ROOT", self.root), patch("sys.argv", ["test_main_review", *map(str, arguments)]), contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            main.main()

    def test_prepare_is_blank_and_refuses_overwrite(self):
        out = self.root / "prepared"
        self.run_cli(["prepare", "--output-dir", out])
        with (out / "main_review_template.csv").open(encoding="utf-8-sig", newline="") as stream:
            rows = list(csv.DictReader(stream))
        self.assertEqual(len(rows), 200)
        self.assertTrue(all(not r["decision"] and not r["reviewer_name"] for r in rows))
        with self.assertRaises(SystemExit): self.run_cli(["prepare", "--output-dir", out])

    def test_missing_real_freeze_rejected_before_output(self):
        out = self.root / "result"
        with self.assertRaises(SystemExit): self.run_cli(["analyse", "--output-dir", out])
        self.assertFalse(out.exists())

    def test_source_tampering_rejected(self):
        with patch.object(main, "ROOT", self.root):
            main.verify_source_package([self.sample_path, *self.sources.values()])
            self.sources["OSM"].write_text("[]", encoding="utf-8")
            with self.assertRaises(ValueError): main.verify_source_package([self.sample_path, *self.sources.values()])

    def test_synthetic_end_to_end_not_research_results(self):
        # The freeze gate is mocked ONLY inside this isolated test. No study freeze is fabricated.
        p = self.root / "fixture_reviews.csv"
        main.write_csv(p, declarations(self.sample), main.HEADERS)
        markers = []
        for name in ["not_a_study_freeze.txt", "fixture_A.txt", "fixture_B.txt"]:
            f = self.root / name
            f.write_text("ISOLATED TEST MARKER; NOT A VALID STUDY FREEZE OR HUMAN FILE", encoding="utf-8")
            markers.append(f)
        out = self.root / "fixture_result"
        with patch("evaluate_reviews.verify_freeze", return_value={"scope": "MOCK IN ISOLATED TEST ONLY"}):
            self.run_cli(["analyse", "--reviews", p, "--freeze", markers[0], "--reviewer-a", markers[1], "--reviewer-b", markers[2], "--output-dir", out])
        result = main.read_json(out / "main_summary.json")
        self.assertEqual(result["supplied_review_declarations"], 200)
        self.assertIsNone(result["independent_validation_metrics"])
        self.assertEqual(len(main.read_json(out / "field_observations.json")), 1800)
        self.assertEqual(result["declared_ai_assisted_n"], 200)


if __name__ == "__main__": unittest.main()
