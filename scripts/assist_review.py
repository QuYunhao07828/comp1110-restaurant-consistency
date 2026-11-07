"""Build AI-assisted evidence, never independent human labels or validated metrics."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from difflib import SequenceMatcher

ROOT = Path(__file__).resolve().parents[1]
DISTRICTS = ("Central and Western", "Wan Chai", "Yau Tsim Mong", "Sha Tin")
INPUTS = ["data/processed/sample_100_enriched.json", "data/processed/candidates.json",
          "data/processed/osm_records.json", "data/processed/overture_records.json",
          "data/review/reviewer_A.csv", "data/review/reviewer_B.csv",
          "data/review/review_admin.json", "data/review/review_protocol.json",
          "data/processed/links.json", "data/processed/matching_config.json",
          "outputs/study_2026-10-23/Independent_Reviewer_A.xlsx",
          "outputs/study_2026-10-23/Independent_Reviewer_B.xlsx"]


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def read(rel):
    return json.loads((ROOT / rel).read_text(encoding="utf-8-sig"))


def validate_curation(evidence, curation):
    """Validate provenance boundaries, not real-world correctness of AI suggestions."""
    cases = {(r["branch_id"], r["source"]): r for r in evidence["cases"]}
    if len(cases) != len(evidence["cases"]):
        raise ValueError("Duplicate evidence task.")
    forbidden = {r["branch_id"] for r in evidence["deferred_pilot_tasks"]}
    seen = set()
    for item in curation["overrides"]:
        key = item["branch_id"], item["source"]
        if key in seen or key not in cases or item["branch_id"] in forbidden:
            raise ValueError("Unknown, duplicate or protected pilot curation.")
        seen.add(key)
        ids = {r["id"] for r in cases[key]["records"]}
        if not set(item["selected_ids"]).issubset(ids):
            raise ValueError("Suggested ID is not in the retained evidence.")
    for row in evidence["cases"]:
        if any(row.get(k) for k in ["human_decision", "human_name", "human_date", "human_evidence"]):
            raise ValueError("Do not overwrite human inputs with an AI preparation run.")
    if evidence["independent_labels_created"] != 0 or evidence["human_searches_created"] != 0:
        raise ValueError("AI preparation must not create human-study completion claims.")
    return True


def build(output, district="Sha Tin", client_date=None):
    if district not in DISTRICTS:
        raise ValueError("Choose one of the four submitted-plan districts.")
    if output.exists():
        raise ValueError("Use a new output directory; no files are overwritten.")
    client_date = client_date or datetime.now().date().isoformat()
    from analyse import indexes, norm, haversine, name_similarity
    from rapidfuzz import process, fuzz
    before = {p: digest(ROOT / p) for p in INPUTS}
    sample = [b for b in read(INPUTS[0]) if b["district"] == district]
    original = read(INPUTS[1])
    admin = read("data/review/review_admin.json")
    protected = {r["branch_id"] for r in admin}
    evidence = []
    pilot_tasks = []
    for src, filename in [("OSM", "osm_records.json"), ("Overture", "overture_records.json")]:
        records = read("data/processed/" + filename)
        grid, exact = indexes(records)
        byid = {r["id"]: i for i, r in enumerate(records)}
        for branch in sample:
            # No machine-authored case verdicts or expanded searches on protected pilot branches.
            if branch["branch_id"] in protected or branch["pilot"]:
                pilot_tasks.append({"branch_id": branch["branch_id"], "name": branch["name_en"],
                                    "source": src, "state": "Deferred until documented rule freeze",
                                    "human_search_completed": False})
                continue
            saved = [r for r in original if r["branch_id"] == branch["branch_id"] and r["source"] == src]
            ids = {byid[r["record_id"]] for r in saved if r["record_id"] in byid}
            # Broad geographic search: 1,500 m, no minimum name similarity or category filter.
            if branch.get("coords"):
                x, y = branch["coords"]
                gx, gy = int(x / .005), int(y / .005)
                for dx in range(-4, 5):
                    for dy in range(-4, 5):
                        for i in grid.get((gx + dx, gy + dy), []):
                            d = haversine(branch["coords"], records[i]["coords"])
                            if d is not None and d <= 1500:
                                ids.add(i)
            # Additional source-wide name search; deliberately different from the saved top-12 cut.
            for alias in branch["aliases"]:
                n = norm(alias)
                ids.update(exact.get(n, []))
                for value, similarity, key in process.extract(n, exact.keys(), scorer=fuzz.ratio,
                                                              score_cutoff=65, limit=30):
                    ids.update(exact[value])
            original_ids = {r["record_id"] for r in saved}
            expanded = []
            for i in ids:
                r = records[i]
                ns = name_similarity(branch["aliases"], r["aliases"])
                distance = haversine(branch.get("coords"), r.get("coords"))
                address_text = " | ".join(r.get("addresses", []))
                # Display order only. This is neither the original score nor a calibrated decision rule.
                address_hint = max((SequenceMatcher(None, norm(a), norm(b)).ratio()
                                    for a in branch["addresses"] for b in r.get("addresses", [])), default=0)
                priority = ns + .2 * address_hint + (.12 if distance is not None and distance < 300 else 0)
                expanded.append({"id": r["id"], "name": r["name"], "aliases": r["aliases"],
                                 "address": address_text, "distance_m": round(distance, 2) if distance is not None else None,
                                 "name_similarity": round(ns, 4), "category": r.get("category_raw"),
                                 "phones": r.get("phones", []), "coords": r.get("coords"),
                                 "url": r.get("url"), "websites": r.get("websites"),
                                 "was_in_saved_top12": r["id"] in original_ids, "display_priority": priority})
            expanded.sort(key=lambda r: (-r["display_priority"], r["id"]))
            # Retain all inspected records in JSON, not just this display shortlist.
            evidence.append({"branch_id": branch["branch_id"], "name": branch["name_en"],
                             "name_zh": branch["name_zh"], "address": branch["address_en"],
                             "address_zh": branch["address_zh"], "coords": branch.get("coords"),
                             "source": src, "original_candidate_n": len(saved), "searched_record_n": len(records),
                             "expanded_record_n": len(expanded), "records": expanded,
                             "ai_suggestion": "Evidence prepared; case assessment pending",
                             "human_decision": "", "human_name": "", "human_date": "", "human_evidence": ""})
        del records, byid, grid, exact
    after = {p: digest(ROOT / p) for p in INPUTS}
    if before != after:
        raise ValueError("Protected input changed during evidence preparation.")
    if len(evidence) != 40 or len(pilot_tasks) != 10:
        raise ValueError("Expected 40 non-pilot source tasks and 10 deferred pilot source tasks.")
    result = {"prepared_client_date": client_date, "executed_utc": datetime.now(timezone.utc).isoformat(),
              "district": district, "source_snapshot_date": "2026-10-23",
              "scope": "AI-assisted non-pilot evidence only; not independent human validation",
              "search": "Saved top 12 plus 1500 m without name/category filtering plus source-wide fuzzy aliases >=65, top 30 name variants per alias. Bounded search, not proof of absence.",
              "independent_labels_created": 0, "human_searches_created": 0,
              "protected_inputs_before": before, "protected_inputs_after": after,
              "cases": evidence, "deferred_pilot_tasks": pilot_tasks}
    output.mkdir(parents=True, exist_ok=False)
    (output / "evidence.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(output), "cases": len(evidence), "deferred": len(pilot_tasks),
                      "expanded_records": sum(r["expanded_record_n"] for r in evidence),
                      "protected_inputs_unchanged": before == after}, ensure_ascii=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--district", choices=DISTRICTS, default="Sha Tin")
    parser.add_argument("--client-date", help="Actual local preparation date, ISO YYYY-MM-DD; defaults to today.")
    args = parser.parse_args()
    build(args.output_dir, district=args.district, client_date=args.client_date)
