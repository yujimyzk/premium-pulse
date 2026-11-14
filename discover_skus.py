#!/usr/bin/env python3
"""Discover potential Nike-style SKUs from official Yahoo Shopping product search.

This script NEVER auto-approves tracking or market prices. It writes review-only
candidates and uses the existing YAHOO_SHOPPING_APP_ID secret.
"""
import datetime as dt
import json
import os
import pathlib
import re
import urllib.error
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent
API = "https://shopping.yahooapis.jp/ShoppingWebService/V3/itemSearch"
# Restrict to Nike-style SKU format until model-specific verification is possible.
SKU = re.compile(r"(?<![A-Z0-9])([A-Z]{1,3}[0-9]{4}-[0-9]{3})(?![0-9])", re.I)
SEEDS = [
    "ナイキ エアジョーダン 限定",
    "ナイキ トラヴィススコット スニーカー",
    "ナイキ ダンク コラボ",
    "NIKE SB DUNK LOW 限定",
    "ナイキ エアジョーダン1 コラボ",
    "NIKE OFF-WHITE DUNK LOW",
    "NIKE KOBE PROTRO",
    "NIKE AIR MAX 限定"
]
def official_image(hit):
    img=hit.get("exImage") or {}
    medium=hit.get("image") or {}
    urls=[img.get("url") if isinstance(img,dict) else None,
          medium.get("medium") if isinstance(medium,dict) else None,
          medium.get("small") if isinstance(medium,dict) else None]
    for url in urls:
        if isinstance(url,str):
            p=urllib.parse.urlsplit(url)
            if p.scheme=="https" and p.hostname and (p.hostname=="yimg.jp" or p.hostname.endswith(".yimg.jp")):
                return url
    return None

BLOCKED = ("靴紐", "シューレース", "キーホルダー", "ステッカー", "カバー", "ソックス", "インソール")

def extract_skus(name):
    if any(token in name for token in BLOCKED):
        return []
    return sorted(set(m.group(1).upper() for m in SKU.finditer(name)))

def discover(payloads, existing, previous, observed_at):
    counts = {}
    for payload in payloads:
        for hit in payload.get("hits", []):
            name = str(hit.get("name") or "")
            url = str(hit.get("url") or "")
            parsed = urllib.parse.urlsplit(url)
            if parsed.scheme != "https" or not parsed.netloc:
                continue
            for sku in extract_skus(name):
                if sku in existing:
                    continue
                row = counts.setdefault(sku, {"sku": sku, "first_seen":observed_at,
                    "last_seen":observed_at,"matching_listings":0,"sample_name":name[:180],
                    "sample_url":url, "sample_image_url":official_image(hit), "status":"pending_review",
                    "note":"型番文字列の候補。商品が本物のスニーカーか、型番・モデルを要確認。"})
                row["matching_listings"] += 1
    previous_map={x["sku"]:x for x in previous.get("candidates", []) if x.get("sku")}
    for sku,row in counts.items():
        if sku in previous_map:
            row["first_seen"]=previous_map[sku].get("first_seen",observed_at)
            if not row.get("sample_image_url"):
                row["sample_image_url"]=previous_map[sku].get("sample_image_url")
    # Retain prior unreviewed candidates, even if a subsequent search does not return them.
    for sku,row in previous_map.items():
        if sku not in counts and sku not in existing and row.get("status")=="pending_review":
            counts[sku]=row
    return {"status":"pending_review","updated_at":observed_at,
            "candidates":sorted(counts.values(),key=lambda x:(-int(x.get("matching_listings",0)),x["sku"]))[:200]}

def fetch(key, query):
    url=API+"?"+urllib.parse.urlencode({"appid":key,"query":query,"results":30,"in_stock":"true","image_size":300})
    req=urllib.request.Request(url,headers={"User-Agent":"PremiumPulse/1.0"})
    try:
        with urllib.request.urlopen(req,timeout=20) as resp:
            return json.loads(resp.read(4000000).decode("utf-8"))
    except urllib.error.HTTPError as e:
        # Do not log the request URL since it carries the secret.
        print(f"Discovery API error: HTTP {e.code}")
        raise SystemExit(1) from None

def main():
    key=os.environ.get("YAHOO_SHOPPING_APP_ID","").strip()
    if not key:
        raise SystemExit("YAHOO_SHOPPING_APP_ID is missing")
    existing={row["sku"].upper() for row in json.loads((ROOT/"data/watch_queries.json").read_text(encoding="utf-8"))}
    target=ROOT/"data/discovery_queue.json"
    previous=json.loads(target.read_text(encoding="utf-8")) if target.exists() else {"candidates":[]}
    now=dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).isoformat(timespec="seconds")
    payloads=[fetch(key,q) for q in SEEDS]
    result=discover(payloads,existing,previous,now)
    target.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"Discovered {len(result['candidates'])} potential new SKUs; all require approval.")

if __name__=="__main__":
    main()
