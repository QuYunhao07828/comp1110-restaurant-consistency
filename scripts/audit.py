"""Check reproducibility and accounting invariants, not empirical match correctness."""
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/".vendor"))
from analyse import name_similarity,phone_norm,haversine,link_status
from review_split import calibration_branches, DEVELOPMENT_BRANCHES
from evaluate_reviews import verify_matching_outputs


def main():
    checks=[]
    def check(name,condition):
        checks.append({"check":name,"passed":bool(condition)})
        if not condition:raise AssertionError(name)
    p=ROOT/"data/processed"
    sample=json.loads((p/"sample_100.json").read_text(encoding="utf-8"))
    links=json.loads((p/"links.json").read_text(encoding="utf-8"))
    summary=json.loads((p/"summary.json").read_text(encoding="utf-8"))
    fields=json.loads((p/"field_comparisons.json").read_text(encoding="utf-8"))
    review=json.loads((ROOT/"data/review/review_admin.json").read_text(encoding="utf-8"))
    check("100 unique branch IDs",len(sample)==100 and len({x["branch_id"] for x in sample})==100)
    check("25 branches per district",set(Counter(x["district"] for x in sample).values())=={25})
    check("20 pilot branches and five per district",sum(x["pilot"] for x in sample)==20 and set(Counter(x["district"] for x in sample if x["pilot"]).values())=={5})
    check("Every district sample follows the saved hash order",all([x["sampling_hash"] for x in sample if x["district"]==d]==sorted(x["sampling_hash"] for x in sample if x["district"]==d) for d in {x["district"] for x in sample}))
    check("200 distinct branch-source link decisions",len(links)==200 and len({(x["branch_id"],x["source"]) for x in links})==200)
    check("1,800 distinct branch-pair-field comparisons",len(fields)==1800 and len({(x["branch_id"],x["pair"],x["field"]) for x in fields})==1800)
    check("Agreement counts reconcile to explicit denominators",all(x["agree"]+x["disagree"]+x["unavailable"]+x["non_comparable"]+x["ambiguous_match"]==x["n"] and x["comparable_n"]==x["agree"]+x["disagree"] and (x["agreement"] is None if x["comparable_n"]==0 else abs(x["agreement"]-x["agree"]/x["comparable_n"])<1e-12) for x in summary["field_summary"]))
    check("60 distinct reference pairs prepared",len(review)==60 and len({x["pair_id"] for x in review})==60)
    check("Calibration and held-out branches disjoint",not ({x["branch_id"] for x in review if x["split"]=="calibration"}&{x["branch_id"] for x in review if x["split"]=="held-out"}))
    check("Inspected development cases reserved for calibration",DEVELOPMENT_BRANCHES <= {x["branch_id"] for x in review if x["split"]=="calibration"})
    check("Review split follows documented revised rule",{x["branch_id"] for x in review if x["split"]=="calibration"}==calibration_branches(x["branch_id"] for x in review))
    check("No independent review claims manufactured",summary["human_review_completed_n"]==0 and all(x["decision"]=="" and x["reviewer_name"]=="" for x in review))
    check("Precision recall F1 are unavailable pending reference labels",all(summary[k] is None for k in ["precision","recall","f1"]))
    check("A short mall suffix cannot replace a restaurant name",name_similarity(["UNAGI YONDAIME KIKUKAWA K11 MUSEA"],["K11 Musea"])<0.84)
    check("Phone normalisation preserves HK numbers and rejects invalid ones",phone_norm("+852 2345 6789;23456789;123")==["+85223456789"])
    check("Zero geographic separation",haversine([114.17,22.3],[114.17,22.3])==0)
    check("Missing reference coordinates do not auto-confirm",link_status([{"score":0.99,"name_similarity":1,"distance_m":None}])[0]!="Automatic proposal")
    check("All saved matching decisions follow current rules and weights",verify_matching_outputs(ROOT)==200)
    hashed=0
    for f in (ROOT/"data/provenance").glob("*.json"):
        meta=json.loads(f.read_text(encoding="utf-8"))
        raw=ROOT/"data/raw"/f.name[:-5]
        if raw.exists() and meta.get("sha256"):
            check("Snapshot checksum "+raw.name,hashlib.sha256(raw.read_bytes()).hexdigest()==meta["sha256"])
            hashed+=1
    check("All three primary source snapshots have provenance",all((ROOT/"data/provenance"/(n+".json")).exists() for n in ["fehd_en.xml","osm_hk_food.json","overture_hk_places.json"]))
    result={"audited_utc":datetime.now(timezone.utc).isoformat(timespec="seconds"),"passed":True,"checks":checks,"snapshot_hash_checks":hashed,"scope":"Checks data lineage, sampling, rule regressions and count accounting. Does not establish real-world entity matching accuracy or source correctness."}
    (p/"verification.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({"passed":True,"checks":len(checks),"snapshot_hash_checks":hashed,"scope":result["scope"]},indent=2))


if __name__=="__main__":main()
