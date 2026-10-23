"""Freeze real calibration, reveal held-out labels, then evaluate a fixed rule."""
from collections import Counter
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import unicodedata

from ingest_reviews import ROOT, DECISIONS, actual_date, load_rows, text, validate

BOUND_FILES = ["scripts/analyse.py", "scripts/review_split.py",
               "data/processed/matching_config.json", "data/processed/candidates.json",
               "data/processed/links.json", "data/review/review_admin.json",
               "data/review/review_protocol.json"]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def name_key(value):
    return " ".join(unicodedata.normalize("NFKC", text(value)).casefold().split())


def independent_inputs(path_a, path_b, admin):
    a, b = [validate(load_rows(p), admin) for p in [path_a, path_b]]
    names = [next(iter(x.values()))["reviewer_name"] for x in [a, b]]
    if name_key(names[0]) == name_key(names[1]):
        raise ValueError("Two different actual human reviewers are required.")
    return a, b


def template(admin, a, b, split):
    rows = []
    for pair_id, original in admin.items():
        if original["split"] != split:
            continue
        row = {k: original[k] for k in ["pair_id", "branch_id", "candidate_source", "candidate_id"]}
        for slot, labels in [("A", a), ("B", b)]:
            row.update({slot + "_" + k: v for k, v in labels[pair_id].items()})
        row.update(needs_adjudication=a[pair_id]["decision"] != b[pair_id]["decision"] or
                   "Uncertain" in [a[pair_id]["decision"], b[pair_id]["decision"]],
                   adjudicator_name="", final_decision="", adjudication_evidence="", adjudicated_at="")
        rows.append(row)
    return rows


def resolved_references(rows, admin, a, b, split):
    expected = {k: v for k, v in admin.items() if v["split"] == split}
    by_id = {text(r.get("pair_id")): r for r in rows}
    if len(rows) != len(expected) or len(by_id) != len(expected) or set(by_id) != set(expected):
        raise ValueError(f"Adjudication must contain exactly the original {len(expected)} {split} pairs.")
    result = {}
    for pair_id, row in by_id.items():
        original = expected[pair_id]
        if any(text(row.get(k)) != text(original[k]) for k in ["branch_id", "candidate_source", "candidate_id"]):
            raise ValueError(f"Original pair metadata changed: {pair_id}")
        for slot, labels in [("A", a), ("B", b)]:
            for key, value in labels[pair_id].items():
                observed = actual_date(row.get(slot + "_" + key)) if key == "reviewed_at" else text(row.get(slot + "_" + key))
                if observed != value:
                    raise ValueError(f"Original {slot} review was changed for {pair_id}.")
        da, db = a[pair_id]["decision"], b[pair_id]["decision"]
        final = text(row.get("final_decision"))
        needs = da != db or da == "Uncertain" or bool(final and final != da)
        if needs:
            person = text(row.get("adjudicator_name"))
            if final not in DECISIONS or not person or not text(row.get("adjudication_evidence")):
                raise ValueError(f"A documented third-person adjudication is required for {pair_id}.")
            if name_key(person) in {name_key(a[pair_id]["reviewer_name"]), name_key(b[pair_id]["reviewer_name"])}:
                raise ValueError(f"The adjudicator must differ from both initial reviewers: {pair_id}.")
            when = actual_date(row.get("adjudicated_at"))
            if when < max(a[pair_id]["reviewed_at"], b[pair_id]["reviewed_at"]):
                raise ValueError(f"Adjudication predates an initial review: {pair_id}.")
        elif not final:
            final = da
        elif final not in DECISIONS:
            raise ValueError(f"Invalid final decision for {pair_id}.")
        result[pair_id] = final
    return result


def classification_metrics(reference, predicted):
    if set(reference) != set(predicted) or any(x not in DECISIONS for x in reference.values()) or any(type(x) is not bool for x in predicted.values()):
        raise ValueError("Metrics require identical pair IDs, valid reference labels and Boolean predictions.")
    counts = Counter()
    for pair_id, label in reference.items():
        if label == "Uncertain":
            counts["excluded_uncertain"] += 1
            continue
        truth, guess = label == "Match", predicted[pair_id]
        counts["tp" if truth and guess else "fn" if truth else "fp" if guess else "tn"] += 1
    tp, fp, fn, tn = [counts[k] for k in ["tp", "fp", "fn", "tn"]]
    return {"reviewed_n": len(reference), "evaluated_n": tp + fp + fn + tn,
            **{k: counts[k] for k in ["tp", "fp", "fn", "tn", "excluded_uncertain"]},
            "precision_denominator": tp + fp, "recall_denominator": tp + fn,
            "precision": tp / (tp + fp) if tp + fp else None,
            "recall": tp / (tp + fn) if tp + fn else None,
            "f1": 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else None}


def reviewer_agreement(a, b, pair_ids):
    pair_ids = set(pair_ids)
    n = len(pair_ids)
    ca = Counter(a[k]["decision"] for k in pair_ids)
    cb = Counter(b[k]["decision"] for k in pair_ids)
    agree = sum(a[k]["decision"] == b[k]["decision"] for k in pair_ids)
    pe = sum(ca[label] * cb[label] for label in DECISIONS) / (n * n) if n else None
    po = agree / n if n else None
    return {"n": n, "agree_n": agree, "observed_agreement": po,
            "cohens_kappa": (po - pe) / (1 - pe) if n and pe < 1 else None,
            "note": "Three-category unweighted agreement before adjudication. These purposeful, clustered pairs do not support population-wide quality claims."}


def write_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def write_csv(path, rows):
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)


def read_csv(path):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def verify_matching_outputs(root=ROOT):
    """Reject stale decisions/configuration before freezing a purportedly fixed rule."""
    from analyse import CONFIG, link_status
    if read_json(root / "data/processed/matching_config.json") != CONFIG:
        raise ValueError("Saved configuration differs from executable matching rules. Recompute/version the analysis before freezing.")
    groups = {}
    for row in read_json(root / "data/processed/candidates.json"):
        features = {"name": row["name_similarity"], "address": row["address_similarity"], "distance": row["distance_similarity"]}
        weighted = [(CONFIG["weights"][key], value) for key, value in features.items() if value is not None]
        expected = sum(w * value for w, value in weighted) / sum(w for w, value in weighted)
        if abs(expected - row["score"]) > 1.1e-6:
            raise ValueError("Stored candidate score is inconsistent with the current weights.")
        groups.setdefault((row["branch_id"], row["source"]), []).append(row)
    links = read_json(root / "data/processed/links.json")
    expected = {}
    for row in links:
        key = row["branch_id"], row["source"]
        candidates = sorted(groups.get(key, []), key=lambda x: (-x["score"], x["record_id"]))
        status, top, margin = link_status(candidates)
        expected[key] = {"status": status, "id": top["record_id"] if top else "", "margin": round(margin, 6) if margin is not None else None}
    used = Counter((key[1], row["id"]) for key, row in expected.items() if row["status"] == "Automatic proposal")
    for key, row in expected.items():
        if row["status"] == "Automatic proposal" and used[key[1], row["id"]] > 1:
            row["status"] = "Review needed"
    for row in links:
        wanted = expected[row["branch_id"], row["source"]]
        if (row["status"], row["proposed_record_id"], row["margin"]) != (wanted["status"], wanted["id"], wanted["margin"]):
            raise ValueError("Saved link decisions differ from the executable rules. Do not freeze stale predictions.")
    return len(links)


def verify_freeze(path, path_a, path_b):
    frozen = read_json(path)
    if frozen.get("version") != "review-freeze-v1" or not frozen.get("held_out_labels_unseen_attested"):
        raise ValueError("A documented pre-evaluation freeze and explicit unseen-label attestation are required.")
    if set(frozen.get("bound_file_sha256", {})) != set(BOUND_FILES):
        raise ValueError("The freeze is missing a required rule, data or split binding.")
    frozen_at = datetime.fromisoformat(frozen["frozen_utc"])
    if frozen_at.tzinfo is None or frozen_at > datetime.now(timezone.utc):
        raise ValueError("The freeze must contain a valid, non-future, timezone-aware actual timestamp.")
    if [digest(p) for p in [path_a, path_b]] != frozen["review_input_sha256"]:
        raise ValueError("Reviewer files changed after freeze; do not replace original judgements.")
    for name, expected in frozen["bound_file_sha256"].items():
        if digest(ROOT / name) != expected:
            raise ValueError(f"Frozen input or matching rule changed: {name}. Do not reuse this evaluation for tuning.")
    return frozen


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=["freeze", "prepare-held-out", "evaluate"])
    parser.add_argument("--reviewer-a", type=Path, required=True)
    parser.add_argument("--reviewer-b", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True, help="A NEW output directory; nothing is overwritten.")
    parser.add_argument("--adjudication", type=Path)
    parser.add_argument("--freeze", type=Path)
    parser.add_argument("--owner")
    parser.add_argument("--note")
    parser.add_argument("--attest-held-out-unseen", action="store_true")
    args = parser.parse_args()
    if args.output_dir.exists():
        parser.error("Output directory exists. Use a new version; original inputs must be retained.")
    admin = {r["pair_id"]: r for r in read_json(ROOT / "data/review/review_admin.json")}
    a, b = independent_inputs(args.reviewer_a, args.reviewer_b, admin)
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    if args.stage == "freeze":
        if not args.adjudication or not text(args.owner) or not text(args.note) or not args.attest_held_out_unseen:
            parser.error("Freeze requires completed calibration, an actual owner, calibration-change note and explicit unseen-label attestation.")
        refs = resolved_references(read_csv(args.adjudication), admin, a, b, "calibration")
        verify_matching_outputs(ROOT)
        result = {"version": "review-freeze-v1", "frozen_utc": now, "owner": args.owner,
                  "calibration_note": args.note, "held_out_labels_unseen_attested": True,
                  "calibration_pair_n": len(refs), "calibration_adjudication_sha256": digest(args.adjudication),
                  "review_input_sha256": [digest(p) for p in [args.reviewer_a, args.reviewer_b]],
                  "bound_file_sha256": {name: digest(ROOT / name) for name in BOUND_FILES},
                  "limitation": "Pilot features were inspected during development; this holds out reference labels, not an untouched external dataset. Attestation is a human declaration, not machine proof of independence."}
        args.output_dir.mkdir(parents=True, exist_ok=False)
        write_json(args.output_dir / "freeze.json", result)
        print("Calibration validated and rules frozen at the actual current time. No held-out decisions exported or metrics computed.")
        return
    if not args.freeze:
        parser.error("A previously recorded freeze is required.")
    frozen = verify_freeze(args.freeze, args.reviewer_a, args.reviewer_b)
    if args.stage == "prepare-held-out":
        rows = template(admin, a, b, "held-out")
        args.output_dir.mkdir(parents=True, exist_ok=False)
        write_csv(args.output_dir / "held_out_adjudication.csv", rows)
        write_json(args.output_dir / "opening.json", {"held_out_opened_utc": now,
                   "freeze_sha256": digest(args.freeze), "freeze_recorded_utc": frozen["frozen_utc"],
                   "pairs_exported": len(rows), "instruction": "Do not tune the rule using these labels and report the same set as a fresh test. Resolve required cases before evaluation."})
        print(f"Exported {len(rows)} held-out pairs for adjudication after verifying the frozen rules.")
        return
    if not args.adjudication:
        parser.error("Completed held-out adjudication is required for evaluation.")
    refs = resolved_references(read_csv(args.adjudication), admin, a, b, "held-out")
    links = {(r["branch_id"], r["source"]): r for r in read_json(ROOT / "data/processed/links.json")}
    predicted = {}
    for pair_id in refs:
        row = admin[pair_id]
        link = links[row["branch_id"], row["candidate_source"]]
        predicted[pair_id] = link["status"] == "Automatic proposal" and link["proposed_record_id"] == row["candidate_id"]
    result = {"evaluated_utc": now, "freeze_sha256": digest(args.freeze),
              "held_out_adjudication_sha256": digest(args.adjudication),
              "prediction_definition": "Match iff the fixed workflow automatically proposes this exact branch/source/candidate link. Review-needed and weak cases are non-acceptance (negative) decisions, not human non-matches.",
              "scope": "Automatic-link acceptance on 39 purposefully selected held-out candidate pairs only. Not whole-source accuracy, end-to-end retrieval recall or validated 100-branch coverage.",
              "pooled": classification_metrics(refs, predicted),
              "by_source": {source: classification_metrics({k: v for k, v in refs.items() if admin[k]["candidate_source"] == source},
                           {k: v for k, v in predicted.items() if admin[k]["candidate_source"] == source}) for source in ["OSM", "Overture"]},
              "reviewer_agreement_all_60": reviewer_agreement(a, b, admin),
              "reviewer_agreement_held_out": reviewer_agreement(a, b, refs),
              "limitations": ["Uncertain adjudications are excluded and counted separately.",
                 "Pairs are purposefully selected and clustered by branch; results do not estimate population prevalence or universal platform quality.",
                 "Pilot features were inspected during development; only reference labels were held out.",
                 "Human independence and unseen-label declarations cannot be certified by this script.",
                 "The separate pilot missed-candidate searches and the full 100-branch link adjudication remain necessary."]}
    args.output_dir.mkdir(parents=True, exist_ok=False)
    write_json(args.output_dir / "evaluation.json", result)
    write_csv(args.output_dir / "held_out_pair_results.csv", [{"pair_id": k, "source": admin[k]["candidate_source"], "reference": v,
              "automatic_acceptance": predicted[k], "included_in_metrics": v != "Uncertain"} for k, v in refs.items()])
    print("Evaluated the frozen rule on supplied real adjudications; results retain explicit denominators and scope limitations.")


if __name__ == "__main__":
    main()
