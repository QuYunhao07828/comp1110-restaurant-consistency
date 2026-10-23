"""Export only code/docs/static UI, without study inputs, credentials or nested Git."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil

ROOT = Path(__file__).resolve().parents[1]
STATIC_UI = {"index.html", "styles.css", "app.js", "review.html", "review.js"}
SECRET = re.compile(r"github_pat_[A-Za-z0-9_]{30,}|gh[pousr]_[A-Za-z0-9]{30,}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")
PRIVATE_METADATA = re.compile(r"https://[A-Za-z0-9.-]+\.chatgpt\.site|appg(?:prj|ver|dep)_[A-Za-z0-9]{12,}|[A-Za-z]:[/\\]Users[/\\]", re.IGNORECASE)


def selected(path):
    rel = path.relative_to(ROOT)
    if "__pycache__" in rel.parts:
        return False
    if len(rel.parts) == 1:
        return path.name in {"README.md", "requirements.txt", ".gitignore"}
    if rel.parts[0] == "scripts":
        return path.suffix in {".py", ".mjs", ".ps1"}
    if rel.parts[0] == "docs":
        return path.suffix in {".md", ".json"} and path.name not in {"evidence_manifest.json", "github_publication_receipt.json", "site_deployment.json"}
    return rel.parts[:2] == ("site", "dist") and path.name in STATIC_UI


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True, help="A new directory; no existing files will be overwritten.")
    args = parser.parse_args()
    if args.output_dir.exists():
        parser.error("Use a NEW export directory; the destination already exists.")
    files = [p for p in ROOT.iterdir() if p.is_file()]
    for folder in [ROOT / "scripts", ROOT / "docs", ROOT / "site/dist", ROOT / "site/.openai"]:
        files.extend(p for p in folder.iterdir() if p.is_file())
    files = sorted(p for p in files if selected(p))
    for path in files:
        contents = path.read_text(encoding="utf-8-sig")
        if SECRET.search(contents):
            raise ValueError(f"Possible credential/private key found; export refused: {path.name}")
        if PRIVATE_METADATA.search(contents):
            raise ValueError(f"Private Site metadata/personal local path found; export refused: {path.name}")
    args.output_dir.mkdir(parents=True, exist_ok=False)
    entries = []
    for path in files:
        rel = path.relative_to(ROOT)
        destination = args.output_dir / rel
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, destination)
        entries.append({"path": rel.as_posix(), "bytes": path.stat().st_size,
                        "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    manifest = {"exported_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "scope": "Code, method documentation and static UI only. Study data, human inputs, private Site metadata and personal local paths are excluded.",
                "files": entries}
    (args.output_dir / "SOURCE_EXPORT.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"files": len(entries), "bytes": sum(x["bytes"] for x in entries),
                      "output_dir": str(args.output_dir), "credential_pattern_scan": "no matches",
                      "private_metadata_pattern_scan": "no matches",
                      "nested_git_included": False, "study_data_included": False}, ensure_ascii=False))


if __name__ == "__main__":
    main()
