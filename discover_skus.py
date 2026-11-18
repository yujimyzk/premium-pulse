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
# Model code formats differ by brand. These are *candidate extraction* patterns only.
# Names and SKU-like strings are never treated as authenticated product identities.
NIKE_SKU = re.compile(r"(?<![A-Z0-9])([A-Z]{1,3}[0-9]{4}-[0-9]{3})(?![A-Z0-9])", re.I)
ADIDAS_SKU = re.compile(r"(?<![A-Z0-9])([A-Z]{1,2}[0-9]{4,5})(?![A-Z0-9])", re.I)
NB_SKU = re.compile(r"(?<![A-Z0-9])([A-Z]{1,3}[0-9]{3,4}[A-Z0-9]{2,5})(?![A-Z0-9])", re.I)
ASICS_SKU = re.compile(r"(?<![A-Z0-9])([0-9]{4}[A-Z][0-9]{3}-[0-9]{3})(?![A-Z0-9])", re.I)
PUMA_SKU = re.compile(r"(?<![A-Z0-9])([0-9]{6}-[0-9]{2})(?![A-Z0-9])", re.I)
BRAND_PATTERNS = {
    "Nike": NIKE_SKU,
    "adidas": ADIDAS_SKU,
    "New Balance": NB_SKU,
    "ASICS": ASICS_SKU,
    "PUMA": PUMA_SKU,
}
BRAND_TERMS = {
    "Nike": ("NIKE", "ナイキ", "JORDAN", "ジョーダン"),
    "adidas": ("ADIDAS", "アディダス", "YEEZY", "イージー"),
    "New Balance": ("NEW BALANCE", "ニューバランス"),
    "ASICS": ("ASICS", "アシックス", "GEL-KAYANO", "GEL-NYC"),
    "PUMA": ("PUMA", "プーマ"),
}
# Rotated in two queries/day to avoid multiplying API usage and HTTP 429 risk.
SEEDS = [
    ("Nike", "ナイキ エアジョーダン 限定"),
    ("adidas", "アディダス サンバ スペツィアル コラボ"),
    ("New Balance", "ニューバランス 990 9060 限定"),
    ("ASICS", "アシックス GEL-KAYANO GEL-NYC スニーカー"),
    ("PUMA", "プーマ スピードキャット コラボ スニーカー"),
    ("Nike", "ナイキ トラヴィススコット スニーカー"),
    ("adidas", "adidas YEEZY スニーカー 型番"),
    ("New Balance", "New Balance 2002R 1906R スニーカー"),
    ("ASICS", "ASICS GEL-LYTE 3 コラボ"),
    ("PUMA", "PUMA スウェード 限定 スニーカー"),
    ("Nike", "NIKE SB DUNK LOW 限定"),
    ("Nike", "NIKE AIR MAX 限定"),
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

def classify_brand(name):
    upper = name.upper()
    for brand, tokens in BRAND_TERMS.items():
        if any(token.upper() in upper for token in tokens):
            return brand
    return None

def extract_skus(name, brand=None):
    if any(token in name for token in BLOCKED):
        return []
    brand = brand or classify_brand(name)
    if not brand:
        return []
    # The item title itself must identify the intended brand, regardless of
    # the search term, to reduce cross-brand model code contamination.
    if classify_brand(name) != brand:
        return []
    matches = sorted(set(m.group(1).upper() for m in BRAND_PATTERNS[brand].finditer(name)))
    # Multiple model codes in one title can describe color variants or a product
    # family. Without verification, assigning one listing price to every code
    # creates misleading cross-SKU candidates, so leave ambiguous titles out.
    return matches if len(matches) == 1 else []

def discover(payloads, existing, previous, observed_at):
    counts = {}
    for entry in payloads:
        # Legacy tests supply a raw payload. New data includes a targeted brand.
        expected_brand = entry.get("target_brand")
        payload = entry.get("payload", entry)
        for hit in payload.get("hits", []):
            name = str(hit.get("name") or "")
            url = str(hit.get("url") or "")
            parsed = urllib.parse.urlsplit(url)
            if parsed.scheme != "https" or not parsed.netloc:
                continue
            brand = classify_brand(name)
            if expected_brand and brand != expected_brand:
                continue
            for sku in extract_skus(name, brand):
                if sku in existing:
                    continue
                key = (brand, sku)
                row = counts.setdefault(key, {"sku": sku, "brand": brand,
                    "first_seen": observed_at, "last_seen": observed_at,
                    "matching_listings": 0, "sample_name": name[:180],
                    "sample_url": url, "sample_image_url": official_image(hit),
                    "status": "pending_review",
                    "note": "未確認の型番候補。商品種別・型番・サイズ・真贋を要確認。"})
                row["matching_listings"] += 1
    prev_map = {(x.get("brand") or classify_brand(x.get("sample_name", "")), x["sku"]): x
                for x in previous.get("candidates", []) if x.get("sku")}
    for key, row in counts.items():
        if key in prev_map:
            prior = prev_map[key]
            row["first_seen"] = prior.get("first_seen", observed_at)
            if not row.get("sample_image_url"):
                row["sample_image_url"] = prior.get("sample_image_url")
    # Keep pending models discovered on previous days, even when query rotates.
    for key, prior in prev_map.items():
        if key not in counts and prior.get("sku") not in existing and prior.get("status") == "pending_review":
            counts[key] = dict(prior, brand=prior.get("brand") or key[0] or "Unknown")
    return {"status": "pending_review", "updated_at": observed_at,
        "candidates": sorted(counts.values(), key=lambda x:
            (-int(x.get("matching_listings", 0)), x.get("brand", ""), x["sku"]))[:500]}

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
    # Rotate search topics to reduce daily API calls and handle rate limits.
    # Keep earlier discoveries when some/all new topic requests fail.
    day_index=dt.datetime.fromisoformat(now).date().toordinal()
    topics=[SEEDS[(day_index*2+i)%len(SEEDS)] for i in range(min(2,len(SEEDS)))]
    payloads=[]
    for brand, topic in topics:
        try:
            payloads.append({"target_brand": brand, "payload": fetch(key, topic)})
        except SystemExit:
            print("Discovery skipped one topic due to API rejection; preserving previous candidates.")
    if not payloads:
        print("All discovery queries failed; leaving existing discovery file untouched.")
        return
    result=discover(payloads,existing,previous,now)
    target.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"Discovered {len(result['candidates'])} potential new SKUs; all require approval.")

if __name__=="__main__":
    main()
