"""Read only STAC-selected Parquet partitions and a bounded place extract."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".vendor"))
from acquire import fetch, RAW, META, now
import duckdb

BBOX = [113.80, 22.15, 114.45, 22.60]


def overlaps(a, b):
    return a[0] <= b[2] and a[2] >= b[0] and a[1] <= b[3] and a[3] >= b[1]


def main():
    collection = json.loads((RAW / "overture_place_collection.json").read_text(encoding="utf-8"))
    urls = [x["href"] for x in collection["links"] if x.get("rel") == "item"]
    def item(url):
        name = "overture_stac_" + url.rsplit("/",1)[-1]
        return json.loads(fetch(url, name))
    with ThreadPoolExecutor(max_workers=4) as executor:
        items = list(executor.map(item, urls))
    selected = [x for x in items if overlaps(x["bbox"], BBOX)]
    print("OVERLAPPING ITEMS", [(x["id"],x["bbox"]) for x in selected], flush=True)
    paths = []
    for x in selected:
        candidates = [(k,a) for k,a in x["assets"].items() if "parquet" in a.get("type","") or a["href"].endswith(".parquet")]
        print("ASSETS", x["id"], json.dumps(candidates, ensure_ascii=False)[:3500], flush=True)
        https_assets = [a["href"] for k,a in candidates if a["href"].startswith("https://")]
        s3_assets = [a["href"] for k,a in candidates if a["href"].startswith("s3://")]
        if https_assets:
            paths.append(https_assets[0])
        elif s3_assets:
            paths.append(s3_assets[0].replace("s3://overturemaps-us-west-2/","https://overturemaps-us-west-2.s3.us-west-2.amazonaws.com/"))
        else:
            raise ValueError("No Parquet data asset")
    if not paths:
        raise ValueError("STAC selection has no partitions")
    out = RAW / "overture_hk_places.json"
    if out.exists():
        print("CACHED bounded Overture extract", out.stat().st_size, flush=True)
        return
    started = now()
    con = duckdb.connect()
    extension_dir = ROOT / ".vendor" / "duckdb_extensions"
    extension_dir.mkdir(parents=True,exist_ok=True)
    con.execute("SET extension_directory='"+str(extension_dir).replace("'","''")+"'")
    con.execute("INSTALL httpfs; LOAD httpfs;")
    con.execute("SET memory_limit='700MB'; SET threads=4; SET http_timeout=120;")
    path_sql = "[" + ",".join("'"+x.replace("'","''")+"'" for x in paths) + "]"
    relation = f"read_parquet({path_sql}, hive_partitioning=false)"
    schema = con.execute("DESCRIBE SELECT * FROM "+relation).fetchall()
    print("SCHEMA",schema,flush=True)
    (META / "overture_extract_schema.json").write_text(json.dumps(schema,ensure_ascii=False,indent=2),encoding="utf-8")
    sql = f"SELECT id, bbox, names, addresses, phones, websites, taxonomy, basic_category, operating_status, confidence, sources, version FROM {relation} WHERE bbox.xmin BETWEEN {BBOX[0]} AND {BBOX[2]} AND bbox.ymin BETWEEN {BBOX[1]} AND {BBOX[3]}"
    con.execute("COPY ("+sql+") TO '"+out.as_posix().replace("'","''")+"' (FORMAT JSON, ARRAY true)")
    b=out.read_bytes()
    records=json.loads(b)
    metadata={"release":json.loads((META/"overture_release_selected.json").read_text())["release"],"started_utc":started,"retrieved_utc":now(),"bbox":BBOX,"sql":sql,"partitions":paths,"stac_items":[x["id"] for x in selected],"records":len(records),"bytes":len(b),"sha256":hashlib.sha256(b).hexdigest(),"duckdb_version":duckdb.__version__,"note":"Subset materialised via HTTP range reads; hash covers extracted JSON, not complete upstream Parquet objects."}
    (META / "overture_hk_places.json.json").write_text(json.dumps(metadata,ensure_ascii=False,indent=2),encoding="utf-8")
    print("EXTRACTED",len(records),"places",len(b),"bytes",flush=True)


if __name__ == "__main__":
    main()
