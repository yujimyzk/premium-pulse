#!/usr/bin/env python3
"""Publish carefully checked sneaker observations; no automated scraping or invented prices."""
import csv
import datetime as dt
import json
import pathlib
from urllib.parse import urlparse

BASE = pathlib.Path(__file__).resolve().parent
REQUIRED = [
    "id", "name", "brand", "sku", "size_cm", "condition", "price_type",
    "tax_basis", "retail", "observed_price", "retail_source", "source", "checked"
]
KINDS = {"listing", "sale"}
CONDITIONS = {"new", "used"}
TAX = {"tax_included", "tax_excluded"}
items = []
ids = set()

def https_url(raw):
    p = urlparse(raw)
    return p.scheme == "https" and bool(p.netloc)

with (BASE / "data/verified.csv").open(encoding="utf-8-sig", newline="") as file:
    reader = csv.DictReader(file)
    if not reader.fieldnames or any(k not in reader.fieldnames for k in REQUIRED):
        raise ValueError("Missing required columns")
    for number, row in enumerate(reader, start=2):
        if not any((v or "").strip() for v in row.values()):
            continue
        for key in REQUIRED:
            if not (row.get(key) or "").strip():
                raise ValueError(f"Line {number}: missing {key}")
        if row["id"] in ids:
            raise ValueError(f"Line {number}: duplicate id")
        ids.add(row["id"])
        if row["condition"] not in CONDITIONS or row["price_type"] not in KINDS or row["tax_basis"] not in TAX:
            raise ValueError(f"Line {number}: invalid condition/price_type/tax_basis")
        try:
            size = float(row["size_cm"])
            if not 15 <= size <= 40:
                raise ValueError("size")
            retail, observed = int(row["retail"]), int(row["observed_price"])
            prior = int(row["prior_price"]) if (row.get("prior_price") or "").strip() else None
        except (ValueError, TypeError):
            raise ValueError(f"Line {number}: invalid numeric field")
        if not 0 < retail <= 10000000 or not 0 < observed <= 10000000 or prior is not None and not 0 < prior <= 10000000:
            raise ValueError(f"Line {number}: invalid price")
        today = dt.date.today()
        checked = dt.date.fromisoformat(row["checked"])
        if checked > today:
            raise ValueError(f"Line {number}: observation is in future")
        previous_date = None
        if prior is not None:
            if not (row.get("prior_checked") or "").strip():
                raise ValueError(f"Line {number}: prior_price requires prior_checked")
            previous_date = dt.date.fromisoformat(row["prior_checked"])
            if previous_date >= checked:
                raise ValueError(f"Line {number}: previous observation must precede current")
        elif (row.get("prior_checked") or "").strip():
            raise ValueError(f"Line {number}: prior_checked without price")
        if not https_url(row["source"]) or not https_url(row["retail_source"]):
            raise ValueError(f"Line {number}: HTTPS source URLs required")
        items.append({
            "id":row["id"], "name":row["name"], "brand":row["brand"],
            "category":row.get("category") or "", "sku":row["sku"],
            "size_cm":size, "condition":row["condition"],
            "price_type":row["price_type"], "tax_basis":row["tax_basis"],
            "retail":retail, "observed_price":observed,
            "prior_price":prior, "prior_checked":str(previous_date) if previous_date else None,
            "retail_source":row["retail_source"], "source":row["source"],
            "checked":str(checked), "note":row.get("note") or "",
        })
payload = {"mode":"verified", "updated":max((x["checked"] for x in items), default=None), "items":items}
(BASE / "data/latest.json").write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(f"Validated {len(items)} source-verified observations")
