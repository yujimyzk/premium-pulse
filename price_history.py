#!/usr/bin/env python3
"""Append observations to a review-only price history. Never infer sales from listings."""
import json, pathlib, datetime, urllib.parse

ROOT=pathlib.Path(__file__).resolve().parent
CURRENT=ROOT/"data/review_candidates.json"
HISTORY=ROOT/"data/price_history.json"
REPORT=ROOT/"data/history_summary.json"

def append_history(current, history):
    existing=list(history.get("observations",[]))
    keys={(x.get("observed_at"),x.get("url"),x.get("price_jpy")) for x in existing}
    added=0
    for row in current.get("candidates",[]):
        url=row.get("url","")
        p=urllib.parse.urlparse(url)
        price=row.get("price_jpy")
        if p.scheme!="https" or not p.netloc or not isinstance(price,int) or price<=0:
            continue
        rec={k:row.get(k) for k in ("watch_sku","name","price_jpy","condition_hint","url","observed_at")}
        rec["price_type"]="listing"
        rec["verified"]=False
        key=(rec["observed_at"],rec["url"],price)
        if key in keys:
            continue
        existing.append(rec)
        keys.add(key)
        added+=1
    by_url={}
    for row in existing:
        by_url.setdefault(row["url"],[]).append(row)
    comparisons=[]
    for url, rows in by_url.items():
        rows.sort(key=lambda x:x["observed_at"])
        if len(rows)<2:
            continue
        a,b=rows[-2:]
        if a["observed_at"]==b["observed_at"] or a["price_jpy"]==b["price_jpy"]:
            continue
        comparisons.append({"watch_sku":b["watch_sku"],"url":url,
           "from_jpy":a["price_jpy"],"to_jpy":b["price_jpy"],
           "change_percent":round((b["price_jpy"]/a["price_jpy"]-1)*100,2),
           "from_date":a["observed_at"],"to_date":b["observed_at"],
           "note":"同一URLの出品希望価格の変動。成約や市場全体の変動ではありません。"})
    return {"schema_version":1,"observations":existing},{
      "last_collection":current.get("generated_at"),"observation_count":len(existing),
      "new_observations":added,"unique_urls":len(by_url),
      "observed_listing_changes":sorted(comparisons,key=lambda x:abs(x["change_percent"]),reverse=True)[:20],
      "status":"unverified_listing_history",
      "warning":"出品価格の履歴であり、成約相場ではありません。サイズ・状態・商品の同一性を確認していません。"}

def main():
    current=json.loads(CURRENT.read_text(encoding="utf-8"))
    if current.get("status")!="unverified_candidates":
        raise ValueError("Not an unverified candidate dataset")
    old=json.loads(HISTORY.read_text(encoding="utf-8")) if HISTORY.exists() else {"schema_version":1,"observations":[]}
    new, report=append_history(current,old)
    HISTORY.write_text(json.dumps(new,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"History: {report['observation_count']} observations across {report['unique_urls']} listing URLs; {report['new_observations']} newly added.")

if __name__=="__main__":
    main()
