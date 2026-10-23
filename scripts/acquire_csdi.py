"""Official FEHD CSDI coordinates, joined only on the explicit licence field."""
import hashlib
import json
from pathlib import Path
import subprocess
import urllib.parse
from acquire import now, RAW, META

ROOT=Path(__file__).resolve().parents[1]
BASE="https://portal.csdi.gov.hk/server/rest/services/common/fehd_rcd_1630036390312_58893/MapServer"


def native_fetch(url,name):
    path=RAW/name
    if path.exists() and (META/(name+".json")).exists():
        print("CACHED",name)
        return json.loads(path.read_text(encoding="utf-8-sig"))
    started=now()
    p=subprocess.run(["powershell.exe","-NoProfile","-ExecutionPolicy","Bypass","-File",str(ROOT/"scripts"/"download_public.ps1"),"-Uri",url,"-OutputPath",str(path)],capture_output=True,encoding="utf-8")
    if p.returncode:
        raise RuntimeError(p.stderr)
    response=json.loads(p.stdout)
    data=path.read_bytes()
    meta={"url":url,"retrieval_started_utc":started,"retrieved_utc":now(),"http_status":response["status"],"response_headers":response["headers"],"bytes":len(data),"sha256":hashlib.sha256(data).hexdigest(),"tls":"Validated by Windows system certificate trust; TLS verification not disabled."}
    (META/(name+".json")).write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding="utf-8")
    print("SAVED",name,len(data),flush=True)
    doc=json.loads(data)
    if "error" in doc:
        raise ValueError(doc["error"])
    return doc


def main():
    native_fetch(BASE+"?f=pjson","fehd_csdi_service.json")
    native_fetch(BASE+"/0?f=pjson","fehd_csdi_layer.json")
    sample=json.loads((ROOT/"data/processed/sample_100.json").read_text(encoding="utf-8"))
    ids=[lic for r in sample for lic in r["licence_ids"]]
    where="SEARCH02_EN IN ("+",".join("'"+x+"'" for x in ids)+")"
    url=BASE+"/0/query?"+urllib.parse.urlencode({"where":where,"outFields":"*","returnGeometry":"true","outSR":"4326","resultRecordCount":1000,"f":"geojson"})
    doc=native_fetch(url,"fehd_csdi_sample_100.geojson")
    if doc.get("exceededTransferLimit") or doc.get("properties",{}).get("exceededTransferLimit"):
        raise ValueError("Truncated CSDI query")
    print("CSDI matched features",len(doc["features"]),"requested licences",len(ids),flush=True)
    if any(x["properties"]["SEARCH02_EN"] not in ids for x in doc["features"]):
        raise ValueError("Unexpected licence in CSDI extract")


if __name__=="__main__":
    main()
