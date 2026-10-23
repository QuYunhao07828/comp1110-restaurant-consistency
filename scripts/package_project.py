"""Build a self-contained evidence archive without credentials or dependency caches."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/study_2026-10-23"
ARCHIVE = ROOT / "outputs/COMP1110_Project_Evidence_2026-10-23.zip"


def include(path):
    parts = path.relative_to(ROOT).parts
    if any(p in {".git", "__pycache__", "node_modules", ".vendor", "tmp", "local"} for p in parts):
        return False
    if path.name.endswith((".pyc", ".inspect.ndjson")):
        return False
    if parts[0] == "outputs":
        return path.parent == OUT and path.suffix in {".docx", ".xlsx"} or path.parent == OUT / "figures"
    if parts[0] == "site":
        return parts[1] == "dist" or parts[1:] == (".openai", "hosting.json")
    return parts[0] in {"data", "docs", "scripts"} or path.name in {"README.md", "requirements.txt", ".gitignore"}


def main():
    manifest_path = ROOT / "docs/evidence_manifest.json"
    files = []
    for directory, dirs, names in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in {".git", "__pycache__", "node_modules", ".vendor", "tmp", "local"}]
        for name in names:
            p = Path(directory) / name
            if include(p) and p != manifest_path:
                files.append(p)
    files.sort()
    manifest = {"created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "evidence_date": "2026-10-23", "human_labels_complete": False,
                "scope": "Interim computational evidence and working draft; not a completed validated final submission.",
                "files": [{"path": p.relative_to(ROOT).as_posix(), "bytes": p.stat().st_size,
                           "sha256": hashlib.sha256(p.read_bytes()).hexdigest()} for p in files]}
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    files.append(manifest_path)
    with zipfile.ZipFile(ARCHIVE, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for p in files:
            z.write(p, "restaurant-consistency/" + p.relative_to(ROOT).as_posix())
    with zipfile.ZipFile(ARCHIVE) as z:
        if z.testzip() is not None:
            raise ValueError("Archive CRC check failed")
        assert not any("/.git/" in n or "/node_modules/" in n or "/.vendor/" in n for n in z.namelist())
        assert sum(n.endswith(".docx") for n in z.namelist()) == 2
        assert sum(n.endswith(".xlsx") for n in z.namelist()) == 3
    print(json.dumps({"archive": str(ARCHIVE), "files": len(files), "bytes": ARCHIVE.stat().st_size,
                      "sha256": hashlib.sha256(ARCHIVE.read_bytes()).hexdigest(), "crc_checked": True}, indent=2))


if __name__ == "__main__":
    main()
