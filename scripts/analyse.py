"""Traceable pilot matching and provisional summaries; never invent reference labels."""
from __future__ import annotations
from collections import Counter, defaultdict
from datetime import datetime, timezone
import csv
import hashlib
import json
import math
from pathlib import Path
import re
import sys
import unicodedata

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/".vendor"))
from rapidfuzz import fuzz, process
from sample import dump_csv
from review_split import calibration_branches, write_protocol
from review_safety import assert_no_human_inputs

RAW=ROOT/"data/raw"
OUT=ROOT/"data/processed"
REVIEW=ROOT/"data/review"
CONFIG={"weights":{"name":0.55,"address":0.25,"distance":0.20},"candidate_radius_m":750,"name_fallback_min":0.86,"proposal_score_min":0.82,"proposal_name_min":0.84,"proposal_distance_max_m":200,"proposal_margin_min":0.08,"distance_scale_m":150,"name_exact_min_chars":3,"version":"pilot-v1-pre-human-calibration"}


def save(name,obj,folder=OUT):
    folder.mkdir(parents=True,exist_ok=True)
    (folder/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding="utf-8")


def strings(obj):
    if isinstance(obj,str): return [obj]
    if isinstance(obj,list): return [s for v in obj for s in strings(v)]
    if isinstance(obj,dict): return [s for v in obj.values() for s in strings(v)]
    return []


def norm(s):
    s=unicodedata.normalize("NFKC",s or "").casefold().replace("’","'")
    return " ".join("".join(c if c.isalnum() else " " for c in s).split())


def address_norm(s):
    s=norm(s)
    for a,b in [("hong kong","hk"),("road","rd"),("street","st"),("avenue","ave"),("building","bldg"),("ground floor","g f"),("shop","unit")]:
        s=re.sub(r"\b"+a+r"\b",b,s)
    return s


def phone_norm(s):
    values=[]
    for x in re.split(r"[;,/]",s or ""):
        digits=re.sub(r"\D","",x)
        if len(digits)==11 and digits.startswith("852"): digits=digits[3:]
        if len(digits)==8: values.append("+852"+digits)
    return sorted(set(values))


def name_similarity(a,b):
    pairs=[(norm(x),norm(y)) for x in a for y in b if norm(x) and norm(y)]
    if not pairs:return 0.0
    def score(x,y):
        base=max(fuzz.ratio(x,y),fuzz.token_sort_ratio(x,y))
        length_ratio=min(len(x.replace(" ","")),len(y.replace(" ","")))/max(len(x.replace(" ","")),len(y.replace(" ","")))
        # A mall or district suffix alone must not stand in for a much longer business name.
        if min(len(x.replace(" ","")),len(y.replace(" ","")))>=4 and length_ratio>=0.65:
            base=max(base,0.92*fuzz.token_set_ratio(x,y))
        return base/100
    return max(score(x,y) for x,y in pairs)


def addr_similarity(a,b):
    pairs=[(address_norm(x),address_norm(y)) for x in a for y in b if address_norm(x) and address_norm(y)]
    return max((max(fuzz.ratio(x,y),fuzz.token_set_ratio(x,y))/100 for x,y in pairs),default=None)


def haversine(a,b):
    if not a or not b:return None
    lon1,lat1,lon2,lat2=map(math.radians,[*a,*b])
    v=math.sin((lat2-lat1)/2)**2+math.cos(lat1)*math.cos(lat2)*math.sin((lon2-lon1)/2)**2
    return 6371000*2*math.asin(min(1,math.sqrt(v)))


def osm_category(value):
    return {"restaurant":"restaurant","cafe":"cafe","fast_food":"fast_food","food_court":"food_court","bar":"bar_pub","pub":"bar_pub","ice_cream":"dessert"}.get(value)


def overture_category(taxonomy):
    t=taxonomy or {}
    h=set(t.get("hierarchy") or [])|{t.get("primary")}
    for keys,label in [({"fast_food_restaurant","fast_food"},"fast_food"),({"coffee_shop","cafe","tea_house","tea_room","bubble_tea_shop"},"cafe"),({"bar","pub","cocktail_bar","beer_bar"},"bar_pub"),({"ice_cream_shop","dessert_shop","dessert_restaurant"},"dessert"),({"food_court"},"food_court"),({"restaurant"},"restaurant")]:
        if h&keys:return label
    return None


def load_sources():
    osm=json.loads((RAW/"osm_hk_food.json").read_text(encoding="utf-8"))
    osm_rows=[]
    for x in osm["elements"]:
        tags=x.get("tags",{})
        aliases=[]
        for k in ["name","name:en","name:zh","name:zh-Hant","name:zh-Hans","official_name","alt_name","short_name"]:
            aliases.extend(v.strip() for v in tags.get(k,"").split(";") if v.strip())
        coords=[x.get("lon"),x.get("lat")] if "lon" in x else [x.get("center",{}).get("lon"),x.get("center",{}).get("lat")]
        coords=coords if None not in coords else None
        addresses=[]
        for suffix in ["",":en",":zh"]:
            full=tags.get("addr:full"+suffix)
            if full:addresses.append(full)
            street=tags.get("addr:street"+suffix) or tags.get("addr:street")
            hn=tags.get("addr:housenumber","")
            house=tags.get("addr:housename"+suffix,"") or tags.get("addr:housename","")
            unit=tags.get("addr:unit"+suffix,"") or tags.get("addr:unit","")
            if street or house:
                addresses.append(" ".join(v for v in [unit,house,hn,street] if v))
        addresses=list(dict.fromkeys(addresses))
        phones=phone_norm(tags.get("phone","")+";"+tags.get("contact:phone",""))
        rid=f"{x['type']}/{x['id']}"
        osm_rows.append({"source":"OSM","id":rid,"name":tags.get("name") or (aliases[0] if aliases else ""),"aliases":list(dict.fromkeys(aliases)),"addresses":addresses,"phones":phones,"coords":coords,"category_raw":tags.get("amenity"),"category_common":osm_category(tags.get("amenity")),"cuisine":tags.get("cuisine"),"opening_hours":tags.get("opening_hours"),"operating_status":tags.get("operational_status"),"url":"https://www.openstreetmap.org/"+rid,"tags":tags})
    overture=json.loads((RAW/"overture_hk_places.json").read_text(encoding="utf-8"))
    ov_rows=[]
    for x in overture:
        names=x.get("names") or {}
        aliases=list(dict.fromkeys([s for s in ([names.get("primary")]+strings(names.get("common"))+[v.get("value") for v in names.get("rules") or []]) if s]))
        addresses=[]
        for a in x.get("addresses") or []:
            if a.get("freeform"):
                addresses.append(a["freeform"])
        box=x.get("bbox") or {}
        coords=[box.get("xmin"),box.get("ymin")]
        coords=coords if None not in coords else None
        tax=x.get("taxonomy") or {}
        ov_rows.append({"source":"Overture","id":x["id"],"name":names.get("primary") or "","aliases":aliases,"addresses":addresses,"phones":sorted(set(p for val in x.get("phones") or [] for p in phone_norm(val))),"coords":coords,"category_raw":tax.get("primary"),"category_common":overture_category(tax),"taxonomy":tax,"basic_category":x.get("basic_category"),"opening_hours":None,"operating_status":x.get("operating_status"),"existence_confidence":x.get("confidence"),"sources":x.get("sources"),"websites":x.get("websites"),"url":"https://docs.overturemaps.org/guides/places/"})
    save("osm_records.json",osm_rows)
    # Keep the larger original Overture extract unmodified; compact records are for computation.
    save("overture_records.json",ov_rows)
    return {"OSM":osm_rows,"Overture":ov_rows}


def grid_key(coords):return (int(coords[0]/0.005),int(coords[1]/0.005))


def enrich_sample(sample):
    csdi=json.loads((RAW/"fehd_csdi_sample_100.geojson").read_text(encoding="utf-8-sig"))
    byid=defaultdict(list)
    for f in csdi["features"]:byid[f["properties"]["SEARCH02_EN"]].append(f)
    for s in sample:
        s["aliases"]=list(dict.fromkeys(v for v in [s["name_en"],s["name_zh"]] if v))
        s["addresses"]=list(dict.fromkeys(v for v in [s["address_en"],s["address_zh"]] if v))
        s["coords"]=None
        s["coordinate_source"]=None
        found=[f for lic in s["licence_ids"] for f in byid.get(lic,[])]
        if len(found)==1 and found[0].get("geometry"):
            f=found[0]; p=f["properties"]
            s["coords"]=f["geometry"]["coordinates"]
            s["coordinate_source"]="FEHD CSDI; exact SEARCH02_EN-to-LICNO join"
            s["csdi_object_id"]=f["id"]
            s["csdi_lastupdate"]=p.get("LASTUPDATE")
            s["csdi_name"]=p.get("NSEARCH03_EN")
            s["csdi_address"]=p.get("ADDRESS_EN")
            s["csdi_address_exact"]=address_norm(s["address_en"])==address_norm(p.get("ADDRESS_EN"))
            s["csdi_name_exact"]=norm(s["name_en"])==norm(p.get("NSEARCH03_EN"))
    save("sample_100_enriched.json",sample)
    return sample


def indexes(records):
    grid=defaultdict(list); exact=defaultdict(list)
    for i,r in enumerate(records):
        if r["coords"]:grid[grid_key(r["coords"])].append(i)
        for name in r["aliases"]:
            n=norm(name)
            if n:exact[n].append(i)
    return grid,exact


def make_candidates(branch,records,index):
    grid,exact=index
    candidates=set()
    if branch["coords"]:
        gx,gy=grid_key(branch["coords"])
        for dx in range(-2,3):
            for dy in range(-2,3):
                for i in grid.get((gx+dx,gy+dy),[]):
                    if haversine(branch["coords"],records[i]["coords"])<=CONFIG["candidate_radius_m"]:candidates.add(i)
    for alias in branch["aliases"]:
        n=norm(alias)
        candidates.update(exact.get(n,[]))
        # Broader name fallback is independent of the spatial block.
        for matched_name,sim,key in process.extract(n, exact.keys(), scorer=fuzz.ratio, score_cutoff=86,limit=8):
            candidates.update(exact[matched_name])
    rows=[]
    for i in candidates:
        r=records[i]
        ns=name_similarity(branch["aliases"],r["aliases"])
        if ns<0.18:continue
        ads=addr_similarity(branch["addresses"],r["addresses"])
        dist=haversine(branch["coords"],r["coords"])
        ds=math.exp(-(dist/CONFIG["distance_scale_m"])**2) if dist is not None else None
        features={"name":ns,"address":ads,"distance":ds}
        weighted=[(CONFIG["weights"][k],v) for k,v in features.items() if v is not None]
        score=sum(w*v for w,v in weighted)/sum(w for w,v in weighted)
        rows.append({"branch_id":branch["branch_id"],"pilot":branch["pilot"],"district":branch["district"],"source":r["source"],"record_id":r["id"],"name_similarity":round(ns,6),"address_similarity":round(ads,6) if ads is not None else None,"distance_m":round(dist,2) if dist is not None else None,"distance_similarity":round(ds,6) if ds is not None else None,"score":round(score,6),"source_name":r["name"],"source_address":" | ".join(r["addresses"]),"fehd_name":branch["name_en"],"fehd_address":branch["address_en"],"candidate_by_distance":dist is not None and dist<=CONFIG["candidate_radius_m"],"candidate_by_name":ns>=CONFIG["name_fallback_min"]})
    rows.sort(key=lambda x:(-x["score"],x["record_id"]))
    for i,r in enumerate(rows):r["rank"]=i+1
    return rows[:12]


def link_status(rows):
    if not rows:return "No candidate",None,None
    r=rows[0]
    margin=r["score"]-(rows[1]["score"] if len(rows)>1 else 0)
    if r["score"]>=CONFIG["proposal_score_min"] and r["name_similarity"]>=CONFIG["proposal_name_min"] and r["distance_m"] is not None and r["distance_m"]<=CONFIG["proposal_distance_max_m"] and margin>=CONFIG["proposal_margin_min"]:
        return "Automatic proposal",r,margin
    if r["name_similarity"]<0.45 or r["score"]<0.48:
        return "No strong candidate",r,margin
    return "Review needed",r,margin


def comparisons(branch,records,statuses):
    fields=[]
    sources=["FEHD","OSM","Overture"]
    for a,b in [("FEHD","OSM"),("FEHD","Overture"),("OSM","Overture")]:
        for field in ["name","address","phone","category","opening_hours","operating_status"]:
            pair=a+" vs "+b
            comparable_schema=not ((field in ["phone","category","opening_hours","operating_status"] and "FEHD" in [a,b]) or (field=="opening_hours" and "Overture" in [a,b]))
            if not comparable_schema:
                state="Non-comparable"; note="The source schemas or field meanings do not provide a common measure."
                va=vb=None
            elif any(s!="FEHD" and statuses[s]!="Automatic proposal" for s in [a,b]):
                state="Ambiguous match"; note="The algorithm has not proposed an unambiguous link for both sources."
                va=vb=None
            else:
                def val(src):
                    if src=="FEHD":return branch["aliases"] if field=="name" else branch["addresses"]
                    r=records.get(src)
                    if not r:return None
                    return {"name":r["aliases"],"address":r["addresses"],"phone":r["phones"],"category":r["category_common"],"opening_hours":r["opening_hours"],"operating_status":r["operating_status"]}[field]
                va,vb=val(a),val(b)
                if not va or not vb:state="Unavailable"; note="A required value is missing in at least one proposed record."
                else:
                    if field in ["name","address","phone"]:
                        f=address_norm if field=="address" else norm
                        agree=bool({f(x) for x in va}&{f(x) for x in vb})
                    else:agree=va==vb
                    state="Agree" if agree else "Disagree"
                    note="Exact equality after documented normalisation; different address text may describe the same premises."
            fields.append({"branch_id":branch["branch_id"],"pilot":branch["pilot"],"district":branch["district"],"pair":pair,"field":field,"state":state,"value_a":va,"value_b":vb,"note":note,"validation":"provisional automatic links; human reference labels pending"})
    return fields


def main():
    assert_no_human_inputs(ROOT)
    REVIEW.mkdir(parents=True,exist_ok=True)
    sources=load_sources()
    print("Source records normalised", {k:len(v) for k,v in sources.items()},flush=True)
    sample=enrich_sample(json.loads((OUT/"sample_100.json").read_text(encoding="utf-8")))
    idx={k:indexes(v) for k,v in sources.items()}
    byid={k:{r["id"]:r for r in v} for k,v in sources.items()}
    candidates=[]; links=[]; field_rows=[]; display=[]
    all_candidates={}
    for branch_number,s in enumerate(sample,1):
        records={}; statuses={}; source_display={}
        for source,rows in sources.items():
            c=make_candidates(s,rows,idx[source]);candidates.extend(c);all_candidates[(s["branch_id"],source)]=c
            status,top,margin=link_status(c)
            statuses[source]=status
            r=byid[source].get(top["record_id"]) if top else None
            if r:records[source]=r
            links.append({"branch_id":s["branch_id"],"pilot":s["pilot"],"district":s["district"],"source":source,"status":status,"proposed_record_id":top["record_id"] if top else "","score":top["score"] if top else None,"margin":round(margin,6) if margin is not None else None,"name_similarity":top["name_similarity"] if top else None,"address_similarity":top["address_similarity"] if top else None,"distance_m":top["distance_m"] if top else None,"reference_review":"Pending"})
            source_display[source]={"status":status,"record":r,"top_candidates":c[:5]}
        fields=comparisons(s,records,statuses);field_rows.extend(fields)
        display.append({"branch":s,"sources":source_display,"comparisons":fields})
        if branch_number%10==0:print("Matched",branch_number,"of",len(sample),flush=True)
    # One source record linked to multiple FEHD branches needs explicit human review.
    used=Counter((r["source"],r["proposed_record_id"]) for r in links if r["status"]=="Automatic proposal")
    conflicts=[r for r in links if r["status"]=="Automatic proposal" and used[(r["source"],r["proposed_record_id"])]>1]
    if conflicts:
        for r in conflicts:r["status"]="Review needed";r["reference_review"]="Pending; duplicate automatic assignment"
        # Conservative: suppress field summaries for every affected source link.
        conflict_keys={(r["branch_id"],r["source"]) for r in conflicts}
        for f in field_rows:
            if f["state"] not in ["Non-comparable"] and any((f["branch_id"],s) in conflict_keys for s in f["pair"].split(" vs ")):
                f["state"]="Ambiguous match";f["note"]="One source record was proposed for multiple sampled FEHD branches."
        for d in display:
            for source in d["sources"]:
                if (d["branch"]["branch_id"],source) in conflict_keys:d["sources"][source]["status"]="Review needed"
    for name,rows in [("candidates",candidates),("links",links),("field_comparisons",field_rows)]:
        save(name+".json",rows);dump_csv(OUT/(name+".csv"),rows)
    pilot=[x for x in sample if x["pilot"]]
    review_pairs=[]
    # Split by branch, not by pair, to reduce leakage between calibration and evaluation.
    calibration=calibration_branches(x["branch_id"] for x in pilot)
    for s in pilot:
        selected=[]
        for src in sources:
            c=all_candidates[(s["branch_id"],src)]
            if c:selected.append((c[0],"top candidate for source"))
        alternatives=[c[1] for src in sources if len(c:=all_candidates[(s["branch_id"],src)])>1]
        if alternatives:selected.append((max(alternatives,key=lambda x:x["score"]),"highest scoring alternative across sources"))
        for c,reason in selected:
            r=byid[c["source"]][c["record_id"]]
            review_pairs.append({"pair_id":"P"+hashlib.sha256((s["branch_id"]+c["source"]+r["id"]).encode()).hexdigest()[:10],"branch_id":s["branch_id"],"district":s["district"],"fehd_licence_ids":";".join(s["licence_ids"]),"fehd_name_en":s["name_en"],"fehd_name_zh":s["name_zh"],"fehd_address_en":s["address_en"],"fehd_address_zh":s["address_zh"],"fehd_coords":s["coords"],"candidate_source":c["source"],"candidate_id":r["id"],"candidate_names":" | ".join(r["aliases"]),"candidate_addresses":" | ".join(r["addresses"]),"candidate_coords":r["coords"],"candidate_url":r["url"],"reviewer_name":"","decision":"","evidence_and_reason":"","reviewed_at":"","split":"calibration" if s["branch_id"] in calibration else "held-out","selection_reason":reason,"machine_score":c["score"],"machine_rank":c["rank"]})
    review_pairs.sort(key=lambda x:hashlib.sha256(("review-order-v1|"+x["pair_id"]).encode()).hexdigest())
    save("review_admin.json",review_pairs,REVIEW)
    write_protocol()
    public_fields=[k for k in review_pairs[0] if k not in ["split","selection_reason","machine_score","machine_rank"]]
    blinded=[{k:r[k] for k in public_fields} for r in review_pairs]
    dump_csv(REVIEW/"reviewer_A.csv",blinded);dump_csv(REVIEW/"reviewer_B.csv",blinded)
    search_rows=[{"branch_id":s["branch_id"],"district":s["district"],"name":s["name_en"],"name_zh":s["name_zh"],"address":s["address_en"],"source":src,"reviewer_name":"","search_method_and_scope":"","located_record_id":"","found_outside_candidate_set":"","evidence":"","reviewed_at":""} for s in pilot for src in sources]
    dump_csv(REVIEW/"pilot_candidate_miss_search.csv",search_rows)
    summary={"created_utc":datetime.now(timezone.utc).isoformat(timespec="seconds"),"sample_n":len(sample),"pilot_n":len(pilot),"source_records":{"OSM_food_bbox":len(sources["OSM"]),"Overture_all_places_bbox":len(sources["Overture"])},"fehd_csdi_coordinate_n":sum(s["coords"] is not None for s in sample),"fehd_csdi_address_exact_n":sum(s.get("csdi_address_exact",False) for s in sample),"candidate_pair_n":len(candidates),"review_pair_n":len(review_pairs),"review_split":dict(Counter(r["split"] for r in review_pairs)),"human_review_completed_n":0,"precision":None,"recall":None,"f1":None,"reason_metrics_unavailable":"Independent human labels and adjudicated reference set have not been supplied.","link_status":{},"field_summary":[],"limitations":["All link proposals and agreement summaries are unvalidated and provisional.","Names, addresses and distance used for linkage induce selection bias in their conditional agreement.","Address Disagree means different normalised text, not proof of conflicting premises.","OSM snapshot is food amenities in a bounding box, whereas Overture extract includes every place category in that box; neither raw count is an estimate of Hong Kong restaurants.","Official CSDI coordinates have their own update dates and may be imperfect or stale.","At least 60 pairs need actual independent review, and pilot miss searches remain uncompleted."]}
    for scope,ls in [("pilot",[r for r in links if r["pilot"]]),("main_provisional",links)]:
        summary["link_status"][scope]={src:dict(Counter(r["status"] for r in ls if r["source"]==src)) for src in sources}
        for pair in ["FEHD vs OSM","FEHD vs Overture","OSM vs Overture"]:
            for field in ["name","address","phone","category","opening_hours","operating_status"]:
                rows=[r for r in field_rows if r["pair"]==pair and r["field"]==field and (scope!="pilot" or r["pilot"])]
                counts=Counter(r["state"] for r in rows);den=counts["Agree"]+counts["Disagree"]
                summary["field_summary"].append({"scope":scope,"pair":pair,"field":field,"n":len(rows),"agree":counts["Agree"],"disagree":counts["Disagree"],"unavailable":counts["Unavailable"],"non_comparable":counts["Non-comparable"],"ambiguous_match":counts["Ambiguous match"],"comparable_n":den,"agreement":counts["Agree"]/den if den else None})
    save("summary.json",summary);save("matching_config.json",CONFIG)
    dump_csv(OUT/"field_summary.csv",summary["field_summary"])
    save("display_data.json",{"summary":summary,"config":CONFIG,"restaurants":display})
    print(json.dumps({k:v for k,v in summary.items() if k not in ["field_summary","limitations"]},ensure_ascii=False,indent=2))


if __name__=="__main__":
    main()
