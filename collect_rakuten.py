#!/usr/bin/env python3
"""Fetch unverified Rakuten Ichiba listing candidates via official 2026-07-01 API.
Requires RAKUTEN_APP_ID and RAKUTEN_ACCESS_KEY as GitHub Actions secrets.
This script does not publish resale prices, and never logs credentials.
"""
import datetime as dt
import json
import os
import pathlib
import re
import urllib.parse
import urllib.request
import urllib.error

ROOT = pathlib.Path(__file__).resolve().parent
API = "https://openapi.rakuten.co.jp/ichibams/api/IchibaItem/Search/20260701"
TARGET = ROOT / "data/rakuten_candidates.json"
SIZE_RE = re.compile(r"(?<![\d.])((?:2[0-9]|30)(?:\.[05])?)\s*(?:cm|センチ)(?![a-z])", re.I)
BLOCKED = ("靴紐", "シューレース", "キーホルダー", "ステッカー", "インソール", "靴下", "ソックス")
def size_hint(name):
    m = SIZE_RE.search(name)
    return float(m.group(1)) if m else None

def safe_url(raw, allowed=None):
    if not isinstance(raw, str):
        return None
    p = urllib.parse.urlsplit(raw)
    if p.scheme != "https" or not p.hostname or p.username or p.password:
        return None
    if allowed and not (p.hostname in allowed or any(p.hostname.endswith("." + h) for h in allowed)):
        return None
    return raw

def image_url(item):
    urls = item.get("mediumImageUrls") or item.get("smallImageUrls") or []
    for value in urls:
        # Current API uses a string array; handle legacy {"imageUrl": ...} defensively.
        url = value.get("imageUrl") if isinstance(value, dict) else value
        result = safe_url(url, allowed=("rakuten.co.jp", "rakuten.ne.jp", "r10s.jp"))
        if result:
            return result
    return None

def normalize(payload, sku, now):
    result = []
    for record in payload.get("items", []):
        row = record.get("item", record) if isinstance(record, dict) else {}
        if not isinstance(row, dict):
            continue
        name = str(row.get("itemName") or "")
        # Check exact SKU token boundary; do not match a prefix of a longer identifier.
        if not re.search(r"(?<![A-Za-z0-9])" + re.escape(sku) + r"(?![A-Za-z0-9])", name, re.I):
            continue
        if any(b in name for b in BLOCKED):
            continue
        price = row.get("itemPrice")
        link = safe_url(row.get("itemUrl"), allowed=("rakuten.co.jp",))
        if type(price) is not int or price <= 0 or not link:
            continue
        result.append({
            "watch_sku": sku,
            "name": name[:240],
            "price_jpy": price,
            "price_kind": "listing",
            "verification": "pending",
            "condition_hint": None,
            "seller": str(row.get("shopName") or "")[:100],
            "url": link,
            "image_url": image_url(row),
            "size_cm_hint": size_hint(name),
            "observed_at": now,
            "source": "Rakuten Ichiba Item Search API",
            "source_site": "Rakuten Ichiba",
            "postage_flag": row.get("postageFlag"),
            "tax_flag": row.get("taxFlag"),
            "warning": "未検証の店舗出品価格。商品サイズ・状態・送料・真贋未確認。成約価格ではありません。"
        })
    return result

def collect(app_id, access_key, queries, request=None):
    now = dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).isoformat(timespec="seconds")
    result = []
    def http_get(url, headers):
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read(4000000).decode("utf-8"))
    request = request or http_get
    for entry in queries:
        sku = str(entry["sku"]).strip().upper()
        if not re.fullmatch(r"[A-Z0-9_.-]{4,32}", sku):
            raise ValueError("Invalid SKU")
        url = API + "?" + urllib.parse.urlencode({
            "applicationId": app_id, "keyword": sku, "hits": 15,
            "format": "json", "formatVersion": 2, "availability": 1
        })
        try:
            payload = request(url, {"accessKey": access_key, "User-Agent": "PremiumPulse/1.0"})
        except urllib.error.HTTPError as error:
            # Credentials may appear in URL, so never print exception string.
            print("Rakuten API returned HTTP", error.code)
            raise SystemExit(1) from None
        result.extend(normalize(payload, sku, now))
    return {
        "generated_at": now,
        "status": "unverified_candidates",
        "source": "Rakuten Ichiba Item Search API",
        "count": len(result),
        "candidates": result
    }

def main():
    app_id = os.environ.get("RAKUTEN_APP_ID", "").strip()
    access_key = os.environ.get("RAKUTEN_ACCESS_KEY", "").strip()
    if not app_id or not access_key:
        print("Rakuten secrets not configured. Keeping existing data unchanged.")
        return
    queries = json.loads((ROOT / "data/watch_queries.json").read_text(encoding="utf-8"))
    data = collect(app_id, access_key, queries)
    TARGET.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Rakuten unverified listing candidates:", data["count"])

if __name__ == "__main__":
    main()
