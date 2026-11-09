"""Convert a filled district assistance workbook into explicit review declarations.

This imports supplied human fields, not AI suggestions or independent labels.
It does not create final coverage, a rule freeze or evaluation metrics.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import re

from finalise_main_review import (HEADERS, SOURCES, digest, read_json, validate_rows,
                                 verify_source_package, write_csv, write_json)
from ingest_reviews import actual_date, text

ROOT = Path(__file__).resolve().parents[1]
SHEET_HEADERS = ["分店ID", "餐厅", "来源", "目标地址", "AI建议", "建议记录ID", "证据与限制",
                 "待补资料", "人工结果", "人工依据或更正ID", "核对人", "实际日期", "填写状态"]
RECORD_ID = re.compile(r"(?:node|way|relation)/[0-9]+|[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}")
EXPLICIT_ID = re.compile(r"^ID\s*=\s*([^;；\r\n]+)[;；\r\n]+(.+)$", re.IGNORECASE | re.DOTALL)


def read_grid(path):
    """Read the actual cells, rejecting formulas in human input columns."""
    from openpyxl import load_workbook
    if path.suffix.lower() != ".xlsx":
        raise ValueError("Return the original XLSX format, not a screenshot or CSV.")
    book = load_workbook(path, read_only=True, data_only=False)
    try:
        if "Main review" not in book.sheetnames:
            raise ValueError("The original Main review sheet is required.")
        sheet = book["Main review"]
        if sheet.max_row is None or sheet.max_column is None:
            # Valid exported XLSX can omit the optional dimension element.
            # Calculate it from actual cells, without editing the workbook.
            sheet.calculate_dimension(force=True)
        if sheet.max_row > 2000 or sheet.max_column > len(SHEET_HEADERS):
            raise ValueError("Unexpected worksheet extent; preserve the original form layout.")
        headers = [text(c.value) for c in next(sheet.iter_rows(min_row=7, max_row=7, max_col=13))]
        if headers != SHEET_HEADERS:
            raise ValueError("Column headers changed; preserve the original form columns.")
        rows = {}
        for cells in sheet.iter_rows(min_row=8, max_col=13):
            if not any(c.value is not None for c in cells):
                continue
            values = [c.value for c in cells]
            key = text(values[0]), text(values[2])
            if not all(key) or key in rows:
                raise ValueError("Unknown or duplicate branch/source task in workbook.")
            if any(c.data_type == "f" for c in cells[8:12]):
                raise ValueError("Human decision, evidence, name and date must be entered values, not formulas.")
            rows[key] = values
        return {"rows": rows, "assistance_date": actual_date(sheet["H5"].value)}
    finally:
        book.close()


def bind_original(original, triage, sample):
    """Bind the unfilled form to its retained AI notes and fixed non-pilot targets."""
    notes = triage.get("tasks", [])
    by_key = {(text(r["branch_id"]), text(r["source"])): r for r in notes}
    if len(by_key) != len(notes) or set(by_key) != set(original["rows"]):
        raise ValueError("Original form and triage task IDs differ.")
    branches = {b["branch_id"]: b for b in sample}
    districts = {branches[bid]["district"] for bid, _ in by_key if bid in branches}
    if len(districts) != 1:
        raise ValueError("Use one original district workbook at a time.")
    district = next(iter(districts))
    scope = [b for b in sample if b["district"] == district and not b["pilot"]]
    wanted = {(b["branch_id"], src) for b in scope for src in SOURCES}
    if set(by_key) != wanted:
        raise ValueError("Exactly the district's fixed non-pilot tasks are required; pilot cases remain separate.")
    for key, row in original["rows"].items():
        b, note = branches[key[0]], by_key[key]
        expected = [b["branch_id"], b["name_en"], key[1], b["address_zh"], note["suggestion"],
                    "; ".join(note["selected_ids"]), note["reason"], note.get("question", "")]
        if [text(v) for v in row[:8]] != [text(v) for v in expected]:
            raise ValueError("Original prefilled fields differ from the fixed target or retained AI notes.")
        if any(text(v) for v in row[8:12]):
            raise ValueError("The reference form must be the unfilled original, not another student's return.")
    return scope


def select_id(decision, reason, suggestions):
    """Accept an explicit override or confirmation of one displayed suggestion."""
    match = EXPLICIT_ID.fullmatch(reason)
    if re.match(r"^ID\s*=", reason, re.IGNORECASE) and not match:
        raise ValueError("Use ID=<exact record ID>; <actual reason> when selecting or changing an ID.")
    if match:
        rid, explanation = match.group(1).strip(), match.group(2).strip()
        if not rid or not explanation:
            raise ValueError("An explicit ID needs a non-empty reason.")
        if decision == "No counterpart confirmed":
            raise ValueError("No counterpart confirmed cannot also select an ID.")
        return rid
    if decision == "No counterpart confirmed":
        return ""
    if decision == "Confirmed":
        if len(suggestions) != 1:
            raise ValueError("Confirmed needs one explicit ID; no ID or several AI suggestions cannot choose it for you.")
        mentioned = set(RECORD_ID.findall(reason))
        if mentioned - set(suggestions):
            raise ValueError("Reason mentions another source ID. Identify the selected one with ID=<ID>; <reason>.")
        return suggestions[0]
    # Uncertain remains unconfirmed. Multiple tentative IDs are retained in the
    # original workbook/receipt, rather than silently selecting the first.
    return ""


def convert(original, returned, triage, sample, sources):
    scope = bind_original(original, triage, sample)
    if set(returned["rows"]) != set(original["rows"]):
        raise ValueError("The returned form has missing, additional or changed task IDs.")
    if returned["assistance_date"] != original["assistance_date"]:
        raise ValueError("The prefilled assistance date was changed.")
    declarations = []
    for key, base in original["rows"].items():
        row = returned["rows"][key]
        if [text(v) for v in row[:8]] != [text(v) for v in base[:8]]:
            raise ValueError("Returned A-H source/AI fields were changed. Put corrections in J, preserving the original evidence.")
        decision, reason, name = [text(v) for v in row[8:11]]
        if not decision or not reason or not name or not text(row[11]):
            raise ValueError("Complete all human I-L fields for every district task; blank AI forms are not review returns.")
        review_date = actual_date(row[11])
        if review_date < original["assistance_date"]:
            raise ValueError("AI-assisted confirmation cannot predate the assistance form. Preserve earlier unassisted returns separately.")
        suggestions = [v.strip() for v in text(base[5]).split(";") if v.strip()]
        rid = select_id(decision, reason, suggestions)
        b = next(b for b in scope if b["branch_id"] == key[0])
        declarations.append({"branch_id":key[0], "source":key[1], "district":b["district"],
                             "decision":decision, "record_id":rid, "evidence_and_reason":reason,
                             "reviewer_name":name, "reviewed_at":review_date, "ai_assisted":"true"})
    validated = validate_rows(declarations, scope, sources, pilot_allowed=False)
    return [{**r, "ai_assisted":"true"} for r in validated.values()]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--original", type=Path, required=True, help="The retained unfilled district XLSX.")
    parser.add_argument("--triage", type=Path, required=True, help="Its retained triage.json.")
    parser.add_argument("--returned", type=Path, required=True, help="The student's filled XLSX, preserved unchanged.")
    parser.add_argument("--output-dir", type=Path, required=True, help="A new versioned output directory.")
    args = parser.parse_args()
    if args.output_dir.exists():
        parser.error("Use a new output directory; previous returns are not overwritten.")
    input_paths = {"original_workbook":args.original, "triage":args.triage, "returned_workbook":args.returned,
                   "sample":ROOT/"data/processed/sample_100_enriched.json",
                   "OSM":ROOT/"data/processed/osm_records.json", "Overture":ROOT/"data/processed/overture_records.json"}
    before = {k:digest(p) for k,p in input_paths.items()}
    original, returned = read_grid(args.original), read_grid(args.returned)
    # Reject blanks before loading the large private source snapshots.
    if any(not all(text(v) for v in row[8:12]) for row in returned["rows"].values()):
        raise ValueError("Blank or incomplete human I-L fields; no declarations or metrics were created.")
    manifest = verify_source_package([input_paths[k] for k in ["sample","OSM","Overture"]])
    sources = {src:{str(r["id"]):r for r in read_json(input_paths[src])} for src in SOURCES}
    rows = convert(original, returned, read_json(args.triage), read_json(input_paths["sample"]), sources)
    if before != {k:digest(p) for k,p in input_paths.items()}:
        raise ValueError("An input changed while importing; no output written.")
    args.output_dir.mkdir(parents=True, exist_ok=False)
    write_csv(args.output_dir/"nonpilot_review_declarations.csv", rows, HEADERS)
    receipt = {"created_utc":datetime.now(timezone.utc).isoformat(), "scope":"Supplied non-pilot review declarations only; not independent reference labels or final source coverage.",
               "input_sha256":before, "source_package_manifest_sha256":digest(manifest),
               "district":rows[0]["district"], "declarations_n":len(rows),
               "declared_decisions":dict(Counter(r["decision"] for r in rows)), "ai_assisted":True,
               "original_and_returned_files_unchanged":True, "reviewer_identity_or_work_not_independently_verified":True,
               "pilot_tasks_imported":0, "independent_labels_created":0, "final_coverage_or_accuracy_created":False}
    write_json(args.output_dir/"import_receipt.json", receipt)
    print(json.dumps({"declarations_n":len(rows), "district":rows[0]["district"],
                      "pilot_tasks_imported":0, "final_metrics_created":False}, ensure_ascii=False))


if __name__ == "__main__":
    main()
