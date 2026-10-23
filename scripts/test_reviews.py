"""Check review-input guards without storing synthetic labels as study evidence."""
import copy
import json
from pathlib import Path
from ingest_reviews import load_rows, validate

ROOT = Path(__file__).resolve().parents[1]
admin = {r["pair_id"]: r for r in json.loads((ROOT / "data/review/review_admin.json").read_text(encoding="utf-8"))}


def rejects(rows):
    try:
        validate(rows, admin)
    except ValueError:
        return
    raise AssertionError("Invalid review accepted")


for slot in ["A", "B"]:
    rows = load_rows(ROOT / f"outputs/study_2026-10-23/Independent_Reviewer_{slot}.xlsx")
    assert len(rows) == 60
    rejects(rows)
    # Temporary in-memory fixtures are deliberately never written to any study file.
    fixture = copy.deepcopy(rows)
    for row in fixture:
        row.update(decision="Uncertain", reviewer_name="TEST FIXTURE NOT A HUMAN LABEL",
                   evidence_and_reason="Parser test only", reviewed_at="2026-10-23")
    assert len(validate(fixture, admin)) == 60
    fixture[0]["candidate_id"] = "changed"
    rejects(fixture)
    fixture[0] = copy.deepcopy(fixture[1])
    rejects(fixture)
print("Review parser tests passed: original IDs, complete inputs and blank/changed/duplicate guards. No study labels written.")
