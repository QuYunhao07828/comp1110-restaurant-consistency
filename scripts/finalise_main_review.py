"""Import genuine main-sample review declarations without promoting AI suggestions."""
import argparse
from collections import Counter, defaultdict
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ("OSM", "Overture")
FIELDS = ("name", "address", "phone", "category", "opening_hours", "operating_status")
DECISIONS = {"Confirmed", "Uncertain", "No counterpart confirmed"}
HEADERS = ["branch_id", "source", "district", "pilot", "name", "address", "decision",
           "record_id", "evidence_and_reason", "reviewer_name", "reviewed_at", "ai_assisted"]


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def write_csv(path, rows, headers=None):
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=headers or list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def verify_source_package(paths):
    """Bind source fields to the retained package, not just to candidate scores."""
    manifest_path = ROOT / "docs/evidence_manifest.json"
    manifest = read_json(manifest_path)
    expected = {r["path"]: r["sha256"] for r in manifest["files"]}
    for p in paths:
        p = p.resolve()
        rel = p.relative_to(ROOT).as_posix()
        if rel not in expected or digest(p) != expected[rel]:
            raise ValueError("Source fields differ from the retained evidence package: " + rel)
    return manifest_path


def templates(sample):
    return [{"branch_id": b["branch_id"], "source": src, "district": b["district"],
             "pilot": b["pilot"], "name": b["name_en"], "address": b["address_en"],
             "decision": "", "record_id": "", "evidence_and_reason": "", "reviewer_name": "",
             "reviewed_at": "", "ai_assisted": ""} for b in sample for src in SOURCES]


def validate_rows(rows, sample, sources, pilot_allowed=False):
    """Validate supplied declarations and IDs, not a person's actual independence."""
    from ingest_reviews import actual_date
    bybranch = {b["branch_id"]: b for b in sample}
    wanted = {(bid, src) for bid in bybranch for src in SOURCES}
    result = {}
    used = {}
    for raw in rows:
        row = {k: str(raw.get(k) or "").strip() for k in HEADERS}
        key = row["branch_id"], row["source"]
        if key not in wanted or key in result:
            raise ValueError("Unknown or duplicate branch/source task.")
        b = bybranch[key[0]]
        if row["district"] != b["district"]:
            raise ValueError("District changed for a fixed sample branch.")
        if row["decision"] not in DECISIONS or not all(row[k] for k in ["evidence_and_reason", "reviewer_name", "reviewed_at"]):
            raise ValueError("Every task needs an actual decision, evidence, reviewer and date. AI suggestions are not accepted as review declarations.")
        row["reviewed_at"] = actual_date(row["reviewed_at"])
        flag = row["ai_assisted"].lower()
        if flag not in {"true", "false"}:
            raise ValueError("Declare ai_assisted as true or false for every row.")
        row["ai_assisted"] = flag == "true"
        if b["pilot"] and not pilot_allowed:
            raise ValueError("Pilot main-review declarations require the documented rule-freeze gate first.")
        rid = row["record_id"]
        if row["decision"] == "Confirmed" and not rid:
            raise ValueError("Confirmed needs one explicit source record ID; do not infer it from AI prose.")
        if row["decision"] == "No counterpart confirmed" and rid:
            raise ValueError("No counterpart confirmed must not contain a selected counterpart ID.")
        if rid and rid not in sources[key[1]]:
            raise ValueError("Selected ID is not in the declared source snapshot.")
        if row["decision"] == "Confirmed":
            source_key = row["source"], rid
            if source_key in used:
                raise ValueError("One source record is confirmed for multiple branches; resolve granularity or retain uncertainty before counting.")
            used[source_key] = key
        row.update(pilot=b["pilot"], name=b["name_en"], address=b["address_en"])
        result[key] = row
    if set(result) != wanted:
        raise ValueError(f"The full sample needs {len(wanted)} unique review tasks; received {len(result)}. Partial input is not final coverage.")
    return result


def field_observations(sample, reviews, sources):
    from analyse import norm, address_norm
    rows = []
    for b in sample:
        records = {src: sources[src].get(reviews[b["branch_id"], src]["record_id"]) for src in SOURCES}
        def value(src, field):
            if src == "FEHD":
                return b["aliases"] if field == "name" else b["addresses"]
            r = records[src]
            if not r:
                return None
            return {"name": r["aliases"], "address": r["addresses"], "phone": r["phones"],
                    "category": r.get("category_common"), "opening_hours": r.get("opening_hours"),
                    "operating_status": r.get("operating_status")}[field]
        for a, c in [("FEHD", "OSM"), ("FEHD", "Overture"), ("OSM", "Overture")]:
            for field in FIELDS:
                va = vb = None
                unsupported = ("FEHD" in (a, c) and field in {"phone", "category", "opening_hours", "operating_status"}) or ("Overture" in (a, c) and field == "opening_hours")
                if unsupported:
                    state, note = "Non-comparable", "Source schema or field meanings do not provide a common measure."
                elif any(src != "FEHD" and reviews[b["branch_id"], src]["decision"] != "Confirmed" for src in (a, c)):
                    state, note = "Ambiguous match", "At least one source has no confirmed counterpart; do not compare unrelated records."
                else:
                    va, vb = value(a, field), value(c, field)
                    if not va or not vb:
                        state, note = "Unavailable", "A comparable field is absent from at least one selected record."
                    elif field in {"name", "address", "phone"}:
                        normalise = address_norm if field == "address" else norm
                        equal = bool({normalise(x) for x in va} & {normalise(x) for x in vb})
                        state = "Agree" if equal else "Disagree"
                        note = "Exact equality after documented normalisation, not a semantic error or truth judgement."
                    else:
                        state = "Agree" if va == vb else "Disagree"
                        note = "Equality at the documented common category level."
                rows.append({"branch_id": b["branch_id"], "district": b["district"], "pilot": b["pilot"],
                             "pair": f"{a} vs {c}", "field": field, "state": state,
                             "value_a": va, "value_b": vb, "note": note})
    return rows


def summaries(sample, reviews, fields):
    coverage = []
    for district in ["All sampled districts"] + sorted({b["district"] for b in sample}):
        subset = [b for b in sample if district == "All sampled districts" or b["district"] == district]
        for src in SOURCES:
            states = Counter(reviews[b["branch_id"], src]["decision"] for b in subset)
            coverage.append({"district": district, "source": src, "sample_n": len(subset),
                             "confirmed": states["Confirmed"], "uncertain": states["Uncertain"],
                             "no_counterpart_confirmed": states["No counterpart confirmed"],
                             "reviewed_link_coverage": states["Confirmed"] / len(subset) if subset else None})
    result = []
    for scope in ["all", "pilot"]:
        grouped = defaultdict(Counter)
        for row in fields:
            if scope == "all" or row["pilot"]:
                grouped[row["pair"], row["field"]][row["state"]] += 1
        for (pair, field), count in sorted(grouped.items()):
            denominator = count["Agree"] + count["Disagree"]
            result.append({"scope": scope, "pair": pair, "field": field, "n": sum(count.values()),
                           "agree": count["Agree"], "disagree": count["Disagree"],
                           "unavailable": count["Unavailable"], "non_comparable": count["Non-comparable"],
                           "ambiguous_match": count["Ambiguous match"], "comparable_n": denominator,
                           "agreement": count["Agree"] / denominator if denominator else None})
    return coverage, result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=["prepare", "analyse"])
    parser.add_argument("--reviews", type=Path, nargs="+")
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--freeze", type=Path)
    parser.add_argument("--reviewer-a", type=Path)
    parser.add_argument("--reviewer-b", type=Path)
    args = parser.parse_args()
    if args.output_dir.exists():
        parser.error("Use a new versioned directory; inputs and existing outputs are not overwritten.")
    sample_path = ROOT / "data/processed/sample_100_enriched.json"
    sample = read_json(sample_path)
    if len(sample) != 100 or len({b["branch_id"] for b in sample}) != 100:
        raise ValueError("The retained study requires the fixed 100-branch sample.")
    if args.stage == "prepare":
        args.output_dir.mkdir(parents=True, exist_ok=False)
        write_csv(args.output_dir / "main_review_template.csv", templates(sample), HEADERS)
        write_json(args.output_dir / "template_manifest.json", {"created_utc": datetime.now(timezone.utc).isoformat(),
                   "sample_sha256": digest(sample_path), "tasks": 200, "completed_declarations": 0,
                   "instruction": "Fill actual decisions, explicit IDs, evidence, name, date and AI-use flag. Pilot work is gated by rule freeze. This is not the independent 60-pair A/B form."})
        print("Prepared 200 blank main-review tasks; no human labels or metrics created.")
        return
    if not args.reviews or not all([args.freeze, args.reviewer_a, args.reviewer_b]):
        parser.error("Analysis requires real review CSVs and the verified freeze with both original independent reviewer files.")
    from evaluate_reviews import verify_freeze
    verify_freeze(args.freeze, args.reviewer_a, args.reviewer_b)
    source_paths = [ROOT / ("data/processed/" + name) for name in ["osm_records.json", "overture_records.json"]]
    package_manifest = verify_source_package([sample_path, *source_paths])
    bound = [Path(__file__), sample_path, *source_paths, package_manifest, *args.reviews,
             args.freeze, args.reviewer_a, args.reviewer_b]
    before = {str(p.resolve()): digest(p) for p in bound}
    sources = {src: {r["id"]: r for r in read_json(p)} for src, p in zip(SOURCES, source_paths)}
    inputs = []
    for path in args.reviews:
        with path.open(encoding="utf-8-sig", newline="") as stream:
            inputs.extend(csv.DictReader(stream))
    reviews = validate_rows(inputs, sample, sources, pilot_allowed=True)
    fields = field_observations(sample, reviews, sources)
    coverage, field_summary = summaries(sample, reviews, fields)
    if before != {str(p.resolve()): digest(p) for p in bound}:
        raise ValueError("Input changed during analysis; no result is published.")
    args.output_dir.mkdir(parents=True, exist_ok=False)
    write_json(args.output_dir / "reviewed_links.json", list(reviews.values()))
    write_csv(args.output_dir / "reviewed_links.csv", list(reviews.values()))
    write_json(args.output_dir / "field_observations.json", fields)
    write_csv(args.output_dir / "coverage.csv", coverage)
    write_csv(args.output_dir / "field_summary.csv", field_summary)
    write_json(args.output_dir / "main_summary.json", {"created_utc": datetime.now(timezone.utc).isoformat(),
        "sample_n": len(sample), "supplied_review_declarations": len(reviews),
        "declared_ai_assisted_n": sum(r["ai_assisted"] for r in reviews.values()),
        "independent_validation_metrics": None, "input_sha256": before,
        "coverage": coverage, "field_summary": field_summary,
        "limitations": ["Review declarations do not certify actual human work or independent correctness.",
                        "No counterpart confirmed is not proof of source absence.",
                        "Reviewed-link coverage is not platform accuracy or representative Hong Kong-wide coverage.",
                        "Name/address agreement is conditional on linkage and affected by selection bias.",
                        "The separate 60-pair reference evaluation and 40 pilot miss searches remain separate requirements."]})
    print("Generated versioned main-sample summaries from supplied declarations; baseline and reference metrics unchanged.")


if __name__ == "__main__": main()
