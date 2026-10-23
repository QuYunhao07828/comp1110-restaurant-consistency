"""Acquire public source snapshots, preserving timestamps and original responses."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import time
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
META = ROOT / "data" / "provenance"
USER_AGENT = "COMP1110-RestaurantConsistency/0.1 (academic public-data pilot; non-commercial)"


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def fetch(url, name, data=None, timeout=90):
    RAW.mkdir(parents=True, exist_ok=True)
    META.mkdir(parents=True, exist_ok=True)
    target = RAW / name
    if target.exists() and (META / (name + ".json")).exists():
        print(f"CACHED {name} {target.stat().st_size} bytes", flush=True)
        return target.read_bytes()
    request = urllib.request.Request(url, data=data, headers={"User-Agent": USER_AGENT})
    started = now()
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                body = response.read()
                metadata = {
                    "url": url, "method": "POST" if data else "GET",
                    "request_body": data.decode("utf-8") if data else None,
                    "retrieval_started_utc": started, "retrieved_utc": now(),
                    "http_status": response.status, "response_headers": dict(response.headers),
                    "bytes": len(body), "sha256": hashlib.sha256(body).hexdigest(),
                }
            target.write_bytes(body)
            (META / (name + ".json")).write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"SAVED {name} {len(body)} bytes", flush=True)
            return body
        except Exception as exc:
            print(f"RETRY {name} attempt {attempt+1}: {exc}", flush=True)
            if attempt == 2:
                (META / (name + ".error.json")).write_text(json.dumps({"url": url,"attempted_utc":now(),"error":str(exc)}, indent=2), encoding="utf-8")
                raise
            time.sleep(2 * (attempt + 1))


def fehd():
    urls = {
        "fehd_en.xml": "https://www.fehd.gov.hk/english/licensing/license/text/LP_Restaurants_EN.XML",
        "fehd_tc.xml": "https://www.fehd.gov.hk/tc_chi/licensing/license/text/LP_Restaurants_TC.XML",
        "fehd_schema.xsd": "https://www.fehd.gov.hk/datagovhk/LP_Restaurants.xsd",
    }
    for name, url in urls.items():
        fetch(url, name)


def osm():
    # Wider than the four study districts, so candidates outside district borders remain searchable.
    query = '[out:json][timeout:120];nwr["amenity"~"^(restaurant|cafe|fast_food|food_court|bar|pub|ice_cream)$"](22.15,113.80,22.60,114.45);out center;'
    body = urllib.parse.urlencode({"data": query}).encode("utf-8")
    endpoints = ["https://overpass-api.de/api/interpreter", "https://overpass.kumi.systems/api/interpreter"]
    for endpoint in endpoints:
        try:
            result = json.loads(fetch(endpoint, "osm_hk_food.json", data=body, timeout=150))
            if "elements" not in result or result.get("remark"):
                raise ValueError(f"Incomplete Overpass response: {result.get('remark')}")
            print(f"OSM elements={len(result['elements'])} osm_base={result.get('osm3s',{}).get('timestamp_osm_base')}", flush=True)
            return
        except Exception as exc:
            print(f"OSM endpoint failed {endpoint}: {exc}", flush=True)
    raise RuntimeError("No complete Overpass snapshot retrieved")


def stac():
    root_url = "https://stac.overturemaps.org/catalog.json"
    root = json.loads(fetch(root_url, "overture_catalog.json"))
    release = root["latest"]
    release_url = next(x["href"] for x in root["links"] if x.get("rel") == "child" and release in x["href"])
    release_doc = json.loads(fetch(release_url, "overture_release.json"))
    print("OVERTURE RELEASE", release, flush=True)
    print(json.dumps(release_doc.get("links", []), ensure_ascii=False), flush=True)
    (META / "overture_release_selected.json").write_text(json.dumps({"release":release,"catalog_url":release_url,"selected_utc":now()}, indent=2), encoding="utf-8")
    places_url = next(x["href"] for x in release_doc["links"] if x.get("rel") == "child" and "/places/" in x["href"])
    places = json.loads(fetch(places_url, "overture_places_catalog.json"))
    print("PLACES CATALOG", json.dumps(places, ensure_ascii=False)[:10000], flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("source", choices=["all", "fehd", "osm", "stac"])
    args = parser.parse_args()
    jobs = {"fehd":fehd,"osm":osm,"stac":stac}
    selected = jobs if args.source == "all" else {args.source:jobs[args.source]}
    failed = []
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {executor.submit(fn):name for name,fn in selected.items()}
        for future in as_completed(futures):
            try:
                future.result()
            except Exception as exc:
                failed.append(futures[future])
                print(f"FAILED {futures[future]}: {exc}", flush=True)
    if failed:
        raise SystemExit("Acquisition incomplete: " + ", ".join(failed))


if __name__ == "__main__":
    main()
