"""Audit returned A/B files without revealing held-out reference labels.

A calibration-only preview may be exported while a held-out formatting error is
being corrected. It is not a successful strict ingestion, freeze or evaluation.
"""
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import unicodedata

from ingest_reviews import ROOT, DECISIONS, actual_date, load_rows, text
from evaluate_reviews import template


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def name_key(value):
    return " ".join(unicodedata.normalize("NFKC", text(value)).casefold().split())


def audit_one(rows, admin):
    """Return metadata/errors and validated rows; never guess a judgement."""
    errors, valid = [], {}
    ids = [text(r.get("pair_id")) for r in rows]
    if len(ids) != 60 or len(set(ids)) != 60 or set(ids) != set(admin):
        errors.append({"pair_id": None, "field": "pair_id", "issue": "Require exactly the 60 original unique pair IDs"})
    for index, row in enumerate(rows, start=8):
        key = text(row.get("pair_id"))
        original = admin.get(key)
        issues = []
        if original is None:
            issues.append(("pair_id", "Unknown original pair"))
        elif text(row.get("candidate_id")) != original["candidate_id"]:
            issues.append(("candidate_id", "Original candidate ID changed"))
        if text(row.get("decision")) not in DECISIONS:
            issues.append(("decision", "Use exactly Match, Non-match or Uncertain; ask original reviewer to correct"))
        for field in ["evidence_and_reason", "reviewer_name"]:
            if not text(row.get(field)):
                issues.append((field, "Required input is blank"))
        try:
            date = actual_date(row.get("reviewed_at"))
        except ValueError:
            date = None
            issues.append(("reviewed_at", "Use an actual, non-future ISO or Excel date"))
        for field, issue in issues:
            errors.append({"excel_row": index, "pair_id": key,
                           "split": original.get("split") if original else None,
                           "field": field, "issue": issue})
        if not issues:
            valid[key] = {"decision": text(row["decision"]),
                          "evidence_and_reason": text(row["evidence_and_reason"]),
                          "reviewer_name": text(row["reviewer_name"]), "reviewed_at": date}
    names = sorted({text(r.get("reviewer_name")) for r in rows if text(r.get("reviewer_name"))})
    if len({name_key(n) for n in names}) != 1:
        errors.append({"pair_id": None, "field": "reviewer_name", "issue": "One consistent actual reviewer is required per file"})
    return {"expected_rows": 60, "received_rows": len(rows), "valid_rows": len(valid),
            "reviewer_names": names, "error_count": len(errors), "errors": errors}, valid


def calibration_preview(admin, a, b):
    required = {k: v for k, v in admin.items() if v["split"] == "calibration"}
    if not set(required) <= set(a) or not set(required) <= set(b):
        return None
    # template only visits the split requested. No held-out decision is exported.
    return template(required, a, b, "calibration")


def run(path_a, path_b, output):
    if output.exists():
        raise ValueError("Use a new output directory; retain originals and earlier audits")
    admin = {r["pair_id"]: r for r in json.loads((ROOT / "data/review/review_admin.json").read_text(encoding="utf-8"))}
    inputs = [path_a, path_b]
    before = [digest(p) for p in inputs]
    audits, validated = [], []
    for path in inputs:
        audit, valid = audit_one(load_rows(path), admin)
        audits.append(audit)
        validated.append(valid)
    a, b = validated
    independent_names = all(len(v["reviewer_names"]) == 1 for v in audits) and name_key(audits[0]["reviewer_names"][0]) != name_key(audits[1]["reviewer_names"][0])
    preview = calibration_preview(admin, a, b) if independent_names else None
    result = {"audited_utc": datetime.now(timezone.utc).isoformat(),
              "inputs": [{"file": p.name, "sha256": h} for p, h in zip(inputs, before)],
              "reviewers": {slot: value for slot, value in zip(["A", "B"], audits)},
              "different_reviewer_names": independent_names,
              "independence_attested": False,
              "strict_input_validation_passed": independent_names and not any(v["errors"] for v in audits),
              "calibration_preview_rows": len(preview) if preview else 0,
              "held_out_labels_exported": 0, "freeze_created": False,
              "validation_metrics_created": False,
              "scope": "Input quality and calibration-only preview. Names do not establish independence. The original strict importer and freeze requirements remain in force."}
    assert before == [digest(p) for p in inputs], "Original reviewer input changed during audit"
    output.mkdir(parents=True, exist_ok=False)
    if preview:
        with (output / "calibration_adjudication.csv").open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(preview[0]))
            writer.writeheader()
            writer.writerows(preview)
    (output / "quality_summary.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: result[k] for k in ["strict_input_validation_passed", "calibration_preview_rows", "held_out_labels_exported", "freeze_created", "validation_metrics_created"]}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reviewer_a", type=Path)
    parser.add_argument("reviewer_b", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    run(args.reviewer_a, args.reviewer_b, args.output_dir)
