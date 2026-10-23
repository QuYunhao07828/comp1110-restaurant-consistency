"""Reserve inspected development cases for calibration before human labels exist."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEVELOPMENT_BRANCHES = {"B7ab2873fb313"}  # K11 mall-suffix rule-development example


def calibration_branches(branch_ids):
    ids = set(branch_ids)
    if not DEVELOPMENT_BRANCHES <= ids:
        raise ValueError("The documented development case is absent from the pilot.")
    ordered = sorted(ids - DEVELOPMENT_BRANCHES,
                     key=lambda x: hashlib.sha256(("review-split-v1|" + x).encode()).hexdigest())
    return DEVELOPMENT_BRANCHES | set(ordered[:7 - len(DEVELOPMENT_BRANCHES)])


def write_protocol():
    protocol = {
        "version": "review-split-v2-development-reserved",
        "recorded_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "development_branches_reserved_for_calibration": sorted(DEVELOPMENT_BRANCHES),
        "method": "Reserve the inspected K11 development branch, then select six other branches by review-split-v1 SHA256 order. Remaining thirteen branches have held-out reference labels.",
        "change_reason": "The K11 mall-suffix example informed a name-similarity correction and cannot be treated as an untouched evaluation case. Split revised before either independent human reviewer supplied labels.",
        "limitation": "Pilot features and machine outputs were inspected during development. Held-out means reference labels reserved from calibration, not a wholly untouched external test dataset. Any later inspection of held-out labels invalidates that evaluation for further tuning.",
        "human_reference_labels_received": False,
    }
    (ROOT / "data/review/review_protocol.json").write_text(
        json.dumps(protocol, ensure_ascii=False, indent=2), encoding="utf-8")


def main():
    from review_safety import assert_no_human_inputs
    assert_no_human_inputs(ROOT)
    path = ROOT / "data/review/review_admin.json"
    rows = json.loads(path.read_text(encoding="utf-8"))
    if any(r.get("decision") or r.get("reviewer_name") for r in rows):
        raise ValueError("Human input exists: do not revise the split retrospectively.")
    calibration = calibration_branches(r["branch_id"] for r in rows)
    for row in rows:
        row["split"] = "calibration" if row["branch_id"] in calibration else "held-out"
    path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    write_protocol()
    print("Reserved development case; 7 calibration branches / 13 label-held-out branches. No labels changed.")


if __name__ == "__main__":
    main()
