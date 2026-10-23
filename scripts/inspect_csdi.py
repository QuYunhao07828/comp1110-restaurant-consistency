"""Inspect official CSDI service metadata linked by the FEHD catalogue."""
import json
from acquire import fetch

URLS = [
    ("https://portal.csdi.gov.hk/server/rest/services/common/fehd_rcd_1630036390312_58893/MapServer?f=pjson","fehd_csdi_service.json"),
    ("https://portal.csdi.gov.hk/geoportal/?lang=en&datasetId=fehd_rcd_1630036390312_58893","fehd_csdi_portal.html"),
]
for url,name in URLS:
    try:
        body=fetch(url,name,timeout=30)
        print(name,body.decode("utf-8",errors="replace")[:11000],flush=True)
    except Exception as exc:
        print(name,exc,flush=True)
