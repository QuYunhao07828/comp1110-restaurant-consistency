"""Reproducible FEHD branch sampling, independent of external-source match yield."""
from collections import Counter, defaultdict
import csv
import hashlib
import json
from pathlib import Path
import re
import unicodedata
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "processed"
SEED = "COMP1110-2026-FOUR-DISTRICTS-v1"
DISTRICTS = {"18":"Central and Western", "12":"Wan Chai", "61":"Yau Tsim Mong", "62":"Yau Tsim Mong", "97":"Sha Tin"}


def norm(value):
    s=unicodedata.normalize("NFKC", value or "").casefold()
    return "".join(c for c in s if c.isalnum())


def dump_csv(path, rows):
    if not rows:
        raise ValueError("Refusing empty data table " + str(path))
    with path.open("w",encoding="utf-8-sig",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]))
        writer.writeheader()
        for row in rows:
            writer.writerow({k:json.dumps(v,ensure_ascii=False) if isinstance(v,(list,dict)) else v for k,v in row.items()})


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    en=ET.parse(RAW/"fehd_en.xml").getroot()
    tc=ET.parse(RAW/"fehd_tc.xml").getroot()
    zh={x.findtext("LICNO"):x for x in tc.findall("./LPS/LP")}
    records=[]
    groups=defaultdict(list)
    excluded=[]
    for x in en.findall("./LPS/LP"):
        rec={child.tag:child.text or "" for child in x}
        records.append(rec)
        if rec["DIST"] not in DISTRICTS:
            continue
        z=zh.get(rec["LICNO"])
        name_zh=z.findtext("SS","") if z is not None else ""
        adr_zh=z.findtext("ADR","") if z is not None else ""
        if not (norm(rec["SS"]) or norm(name_zh)) or not norm(rec["ADR"]):
            excluded.append({"licence_id":rec["LICNO"],"reason":"Missing business name or English premises address"})
            continue
        key=(DISTRICTS[rec["DIST"]], norm(rec["SS"]) or norm(name_zh),norm(rec["ADR"]))
        groups[key].append((rec,name_zh,adr_zh))
    frame=[]
    for key, values in groups.items():
        values.sort(key=lambda x:x[0]["LICNO"])
        r,z,a=values[0]
        ids=[v[0]["LICNO"] for v in values]
        stable_key="|".join(key)
        branch_id="B"+hashlib.sha256(stable_key.encode()).hexdigest()[:12]
        frame.append({"branch_id":branch_id,"district":key[0],"fehd_district_codes":sorted(set(v[0]["DIST"] for v in values)),"licence_ids":ids,"name_en":r["SS"],"name_zh":z,"address_en":r["ADR"],"address_zh":a,"licence_types":sorted(set(v[0]["TYPE"] for v in values)),"expiry_dates":sorted(set(v[0]["EXPDATE"] for v in values)),"sampling_hash":hashlib.sha256((SEED+"|"+stable_key).encode()).hexdigest(),"fehd_generation_date":en.findtext("GENERATION_DATE"),"merged_licence_count":len(ids)})
    frame.sort(key=lambda x:(x["district"],x["sampling_hash"]))
    sample=[]
    for district in dict.fromkeys(DISTRICTS.values()):
        candidates=[x for x in frame if x["district"]==district]
        if len(candidates)<25:
            raise ValueError("Insufficient district frame")
        for rank,r in enumerate(candidates[:25],1):
            sample.append({**r,"district_sample_rank":rank,"pilot":rank<=5,"main_sample_status":"provisional pending pilot review; do not replace missing matches"})
    pilot=[x for x in sample if x["pilot"]]
    for name,rows in [("fehd_sampling_frame",frame),("sample_100",sample),("pilot_20",pilot)]:
        (OUT/(name+".json")).write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding="utf-8")
        dump_csv(OUT/(name+".csv"),rows)
    metadata={"seed":SEED,"selection":"ascending SHA256(seed|district|normalised name|normalised English address), first 25 per district; first 5 per district form pilot","raw_licence_records":len(records),"fehd_generation_date":en.findtext("GENERATION_DATE"),"tc_generation_date":tc.findtext("GENERATION_DATE"),"raw_licences_in_four_districts":sum(r["DIST"] in DISTRICTS for r in records),"eligible_branch_groups":len(frame),"district_frame_counts":dict(Counter(x["district"] for x in frame)),"district_sample_counts":dict(Counter(x["district"] for x in sample)),"pilot_counts":dict(Counter(x["district"] for x in pilot)),"deduplication":"Exact normalised business-name and premises-address groups within district; licence IDs preserved; possible aliases not merged without review","excluded":excluded,"limitations":["FEHD Yau Tsim (61) and Mong Kok (62) are pooled into Yau Tsim Mong.","FEHD listing and expiry dates are not proof of current operation.","Exact branch grouping cannot guarantee resolution of alias names or suite-level overlaps.","Equal district quotas are not proportional Hong Kong sampling.","Sample is fixed without consulting OSM or Overture match yield."]}
    (OUT/"sampling_metadata.json").write_text(json.dumps(metadata,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(metadata,ensure_ascii=False,indent=2))
    print("PILOT")
    for p in pilot:
        print(p["branch_id"],p["district"],p["name_en"],"|",p["name_zh"])


if __name__=="__main__":
    main()
