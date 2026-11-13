#!/usr/bin/env python3
"""Summarize unverified shopping results; do not assert market prices."""
import collections, datetime, json, pathlib, re, urllib.parse
ROOT=pathlib.Path(__file__).resolve().parent
source=ROOT/"data/review_candidates.json"
raw=json.loads(source.read_text(encoding="utf-8"))
rows=raw.get("candidates",[])
if not isinstance(rows,list):
    raise ValueError("Expected a list of candidates")
seen=set()
count=collections.Counter()
examples=[]
unique=0
size_detected=0
for x in rows:
    sku=str(x.get("watch_sku",""))
    price=x.get("price_jpy")
    name=str(x.get("name") or "")
    url=str(x.get("url") or "")
    parsed=urllib.parse.urlsplit(url)
    if not re.fullmatch(r"[A-Za-z0-9_.-]{4,32}",sku):continue
    if not isinstance(price,int) or not 0 < price < 10000000:continue
    if sku.casefold() not in name.casefold():continue
    if parsed.scheme!="https" or not parsed.netloc:continue
    key=(sku,url.split("?")[0])
    if key in seen:
        count["duplicate_url"]+=1
        continue
    seen.add(key)
    unique+=1
    match=re.search(r"(?<![0-9])(?:SIZE[:： ]*)?([12][0-9](?:\.[05])?|30(?:\.0)?)\s*cm\b",name,re.I)
    if match:
        size_detected+=1
    else:
        count["size_unspecified"]+=1
    condition=x.get("condition_hint")
    if condition not in ("new","used"):
        count["condition_unspecified"]+=1
    count[sku]+=1
    # Evidence is still insufficient: product title and API condition hints are not verified.
result={
  "generated_at":raw.get("generated_at"),"data_status":"review_required",
  "observed_candidates":len(rows),"unique_listing_urls":unique,
  "possibly_size_labeled":size_detected,"size_not_determined":count["size_unspecified"],
  "api_condition_unknown":count["condition_unspecified"],"duplicate_urls_excluded":count["duplicate_url"],
  "by_sku":dict(sorted((k,v) for k,v in count.items() if re.fullmatch(r"[A-Za-z0-9_.-]{4,32}",k) and k not in ("duplicate_url","size_unspecified","condition_unspecified"))),
  "published_as_market_price":0,
  "note":"商品名中のcm表記は参考値で、型番・サイズ・状態・実物・税込区分・定価・成約の確認は未実施。ランキングへの自動公開はしません。"
}
(ROOT/"data/review_summary.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(f"Review summary: {len(rows)} candidates, {unique} distinct URLs, {size_detected} size-text matches. Published prices: 0")
