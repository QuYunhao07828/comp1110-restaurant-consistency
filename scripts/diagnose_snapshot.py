"""Read-only snapshot diagnostics; proposal counts are never validated coverage."""
import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import csv
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump_csv(path, rows):
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def proposed_ids(groups, score_min, margin_min, name_min=.84, distance_max=200):
    """Apply the documented gates and remove duplicate source-record proposals."""
    selected = {}
    for key, rows in groups.items():
        if not rows:
            continue
        rows = sorted(rows, key=lambda r: (-r["score"], r["record_id"]))
        top = rows[0]
        margin = top["score"] - (rows[1]["score"] if len(rows) > 1 else 0)
        if (top["score"] >= score_min and top["name_similarity"] >= name_min
                and top["distance_m"] is not None and top["distance_m"] <= distance_max
                and margin >= margin_min):
            selected[key] = top["record_id"]
    uses = Counter((key[1], rid) for key, rid in selected.items())
    return {key: rid for key, rid in selected.items() if uses[key[1], rid] == 1}


def presence(records, source):
    fields = ["aliases", "addresses", "phones", "coords", "category_common",
              "opening_hours", "operating_status"]
    result = []
    for field in fields:
        n = sum(bool(r.get(field)) for r in records)
        result.append({"source": source, "population": "food amenities in bbox" if source == "OSM" else "all place categories in bbox",
                       "field": field, "records": len(records), "present_n": n,
                       "present_fraction": n / len(records) if records else None,
                       "interpretation": "Snapshot attribute presence, not restaurant coverage or accuracy."})
    return result


def placeholder_names(sample):
    """Flag explicit missing-name markers without changing the retained sample."""
    markers = {"no record", "no records", "no record found", "no records found", "n a", "nil"}
    def marker(value):
        return re.sub(r"[^a-z0-9]+", " ", str(value or "").casefold()).strip() in markers
    result = []
    for b in sample:
        english, chinese = marker(b.get("name_en")), marker(b.get("name_zh"))
        if english or chinese:
            genuine = [a for a in b.get("aliases", []) if str(a).strip() and not marker(a)]
            result.append({"branch_id": b["branch_id"], "english_name_is_marker": english,
                           "chinese_name_is_marker": chinese, "genuine_alias_available": bool(genuine),
                           "coordinate_available": bool(b.get("coords")),
                           "target_name_verification_needed": not bool(genuine)})
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.output_dir.exists():
        parser.error("Use a new output directory.")
    from finalise_main_review import verify_source_package
    paths = {name: ROOT / "data/processed" / name for name in [
        "sample_100_enriched.json", "candidates.json", "links.json", "matching_config.json",
        "osm_records.json", "overture_records.json", "summary.json"]}
    verify_source_package([paths[k] for k in ["sample_100_enriched.json", "osm_records.json", "overture_records.json"]])
    before = {k: digest(v) for k, v in paths.items()}
    sample, candidates, links, config = (read(paths[k]) for k in [
        "sample_100_enriched.json", "candidates.json", "links.json", "matching_config.json"])
    groups = defaultdict(list)
    for c in candidates:
        groups[c["branch_id"], c["source"]].append(c)
    expected = {(b["branch_id"], source) for b in sample for source in ["OSM", "Overture"]}
    for key in expected:
        groups[key]
    base = proposed_ids(groups, config["proposal_score_min"], config["proposal_margin_min"],
                        config["proposal_name_min"], config["proposal_distance_max_m"])
    saved = {(r["branch_id"], r["source"]): r["proposed_record_id"] for r in links if r["status"] == "Automatic proposal"}
    if base != saved:
        raise ValueError("Diagnostic rule does not reproduce saved automatic proposals.")
    bybranch = {b["branch_id"]: b for b in sample}
    tasks = []
    for key in sorted(expected):
        rows = sorted(groups[key], key=lambda r: (-r["score"], r["record_id"]))
        top = rows[0] if rows else {}
        margin = top["score"] - (rows[1]["score"] if len(rows) > 1 else 0) if rows else None
        tasks.append({"branch_id": key[0], "source": key[1], "district": bybranch[key[0]]["district"],
                      "pilot": bybranch[key[0]]["pilot"], "saved_candidate_n": len(rows),
                      "saved_list_at_cap": len(rows) == 12, "top_name_similarity": top.get("name_similarity"),
                      "top_address_similarity": top.get("address_similarity"), "top_distance_m": top.get("distance_m"),
                      "top_score": top.get("score"), "top_margin": margin,
                      "automatic_proposal": key in base, "top_address_absent": top.get("address_similarity") is None,
                      "note": "Saved top-12 diagnostics; a capped list is not all retrieved candidates."})
    sensitivity = []
    # Predeclared display grid. No reference labels are loaded, and no optimum is selected.
    for score in [.78, .82, .86]:
        for margin in [.04, .08, .12]:
            selected = proposed_ids(groups, score, margin)
            for district in ["All sampled districts"] + sorted({b["district"] for b in sample}):
                ids = {b["branch_id"] for b in sample if district == "All sampled districts" or b["district"] == district}
                for source in ["OSM", "Overture"]:
                    keys = {(bid, source) for bid in ids}
                    sensitivity.append({"score_min": score, "margin_min": margin,
                                        "name_min": .84, "distance_max_m": 200, "district": district,
                                        "source": source, "branch_n": len(ids),
                                        "automatic_proposal_n": len(keys & selected.keys()),
                                        "added_vs_baseline_n": len((keys & selected.keys()) - base.keys()),
                                        "removed_vs_baseline_n": len((keys & base.keys()) - selected.keys()),
                                        "interpretation": "Automatic proposal behaviour only; not accuracy or verified source coverage."})
    fields = []
    for source, fname in [("OSM", "osm_records.json"), ("Overture", "overture_records.json")]:
        records = read(paths[fname])
        fields.extend(presence(records, source))
        del records
    after = {k: digest(v) for k, v in paths.items()}
    if before != after:
        raise ValueError("A protected snapshot input changed.")
    placeholders = placeholder_names(sample)
    summary = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "snapshot_date": "2026-10-23", "source_hashes": before, "inputs_unchanged": before == after,
        "sample_n": len(sample), "branch_source_tasks": len(tasks), "saved_candidate_pairs": len(candidates),
        "automatic_proposals_reproduced": True,
        "automatic_proposal_counts": dict(Counter(key[1] for key in base)),
        "no_saved_candidate_tasks": sum(t["saved_candidate_n"] == 0 for t in tasks),
        "at_saved_cap_tasks": sum(t["saved_list_at_cap"] for t in tasks),
        "automatic_top_address_absent": dict(Counter(t["source"] for t in tasks if t["automatic_proposal"] and t["top_address_absent"])),
        "top_high_name_but_over_200m_tasks": sum(t["top_name_similarity"] is not None and t["top_name_similarity"] >= .84 and t["top_distance_m"] is not None and t["top_distance_m"] > 200 for t in tasks),
        "placeholder_english_name_branches": [b["branch_id"] for b in placeholders if b["english_name_is_marker"]],
        "placeholder_name_diagnostics": placeholders,
        "placeholder_note": "Explicit missing-name markers are not business names. Use genuine alternative-language names where available; otherwise retain target-identity uncertainty. Missing coordinates also prevent the geographic search. No baseline, source values or sample members were modified here.",
        "independent_labels_read": False, "human_reviews_created": 0,
        "sensitivity_grid": {"score_min": [.78, .82, .86], "margin_min": [.04, .08, .12], "selected_optimum": None},
        "limitations": ["Raw source populations differ.", "Saved candidates are truncated at 12; this audit is not a candidate-miss search.",
                        "Attribute presence is not proof of correctness.", "Proposal counts and conditional field agreement are not independently validated coverage.",
                        "No reviewed reference labels are used and no precision, recall or F1 is calculated."]}
    args.output_dir.mkdir(parents=True, exist_ok=False)
    (args.output_dir / "diagnostic_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    dump_csv(args.output_dir / "candidate_diagnostics.csv", tasks)
    dump_csv(args.output_dir / "proposal_sensitivity.csv", sensitivity)
    dump_csv(args.output_dir / "snapshot_field_presence.csv", fields)
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
