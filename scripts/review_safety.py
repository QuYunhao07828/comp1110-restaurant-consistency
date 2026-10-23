"""Protect real human inputs from baseline-template regeneration."""
import csv
import json
from pathlib import Path
import zipfile
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
NS = {"s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}


def xlsx_has_review_inputs(path):
    with zipfile.ZipFile(path) as archive:
        strings = []
        if "xl/sharedStrings.xml" in archive.namelist():
            xml = ET.fromstring(archive.read("xl/sharedStrings.xml"))
            strings = ["".join(x.itertext()) for x in xml.findall("s:si", NS)]
        xml = ET.fromstring(archive.read("xl/worksheets/sheet1.xml"))
        for cell in xml.findall(".//s:c", NS):
            ref = cell.attrib.get("r", "")
            col = "".join(c for c in ref if c.isalpha())
            row = int("".join(c for c in ref if c.isdigit()) or "0")
            if col not in {"I", "J", "K", "L"} or not 8 <= row <= 67:
                continue
            if cell.find("s:f", NS) is not None:
                return True
            value = cell.findtext("s:v", "", NS)
            if cell.attrib.get("t") == "s" and value:
                value = strings[int(value)]
            elif cell.attrib.get("t") == "inlineStr":
                value = "".join(cell.find("s:is", NS).itertext())
            if value.strip():
                return True
    return False


def assert_no_human_inputs(root=ROOT):
    review = root / "data/review"
    for path in review.rglob("*.csv"):
        with path.open(encoding="utf-8-sig", newline="") as stream:
            for row in csv.DictReader(stream):
                fields = {k for k in row if k and (k in {"reviewer_name", "decision", "evidence_and_reason", "reviewed_at", "search_method_and_scope", "located_record_id", "found_outside_candidate_set", "evidence", "adjudicator_name", "final_decision"} or k.startswith(("A_", "B_")))}
                if any(str(row.get(k) or "").strip() for k in fields):
                    raise ValueError(f"Human input exists in {path}; preserve it and use a separate versioned project copy.")
    admin = review / "review_admin.json"
    if admin.exists() and any(r.get("decision") or r.get("reviewer_name") for r in json.loads(admin.read_text(encoding="utf-8"))):
        raise ValueError("Human input exists in the review administrator file.")
    for name in ["ingestion.json", "freeze.json"]:
        if any(review.rglob(name)):
            raise ValueError(f"A returned review batch or freeze exists ({name}); do not regenerate baseline templates.")
    for slot in ["A", "B"]:
        path = root / f"outputs/study_2026-10-23/Independent_Reviewer_{slot}.xlsx"
        if path.exists() and xlsx_has_review_inputs(path):
            raise ValueError(f"Filled reviewer workbook exists: {path}. It must not be overwritten.")


if __name__ == "__main__":
    assert_no_human_inputs()
    print("No human inputs would be overwritten by baseline regeneration.")
