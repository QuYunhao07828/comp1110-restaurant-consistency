"""Drop unnecessary public editor identity metadata from the initial snapshot."""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
p=ROOT/"data/raw/osm_hk_food.json"
m=ROOT/"data/provenance/osm_hk_food.json.json"
b=p.read_bytes();d=json.loads(b);removed=0
for row in d["elements"]:
    for key in ["user","uid","changeset"]:
        if key in row:
            del row[key];removed+=1
if removed:
    meta=json.loads(m.read_text(encoding="utf-8"))
    out=json.dumps(d,ensure_ascii=False,separators=(",",":")).encode("utf-8")
    meta["upstream_response_sha256"]=meta["sha256"]
    meta["upstream_response_bytes"]=meta["bytes"]
    meta["sha256"]=hashlib.sha256(out).hexdigest();meta["bytes"]=len(out)
    meta["post_retrieval_transformation"]="Removed public OSM user, uid and changeset metadata, which is unnecessary for business-record comparisons. Original upstream response is not retained. Tags, object IDs, geometry, versions and object timestamps remain."
    p.write_bytes(out);m.write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding="utf-8")
print("Removed metadata fields:",removed)
