#!/usr/bin/env python3
"""Collect unverified Yahoo! Shopping listing candidates via official V3 API."""
import datetime as dt
import json,os,pathlib,re,urllib.parse,urllib.request,urllib.error
from discover_skus import classify_brand, extract_skus
ROOT=pathlib.Path(__file__).resolve().parent
API="https://shopping.yahooapis.jp/ShoppingWebService/V3/itemSearch"
def official_image(hit):
    """Choose an HTTPS image supplied by the official API, never scrape or guess."""
    large=(hit.get("exImage") or {}).get("url") if isinstance(hit.get("exImage"),dict) else None
    medium=(hit.get("image") or {}).get("medium") if isinstance(hit.get("image"),dict) else None
    small=(hit.get("image") or {}).get("small") if isinstance(hit.get("image"),dict) else None
    for candidate in (large,medium,small):
        if isinstance(candidate,str):
            p=urllib.parse.urlsplit(candidate)
            if p.scheme=="https" and p.hostname and (p.hostname=="yimg.jp" or p.hostname.endswith(".yimg.jp")):
                return candidate
    return None

def jan_code_hint(hit):
    """Return a valid merchant-reported JAN/EAN-13, never infer it from titles."""
    raw=hit.get("janCode")
    if not isinstance(raw,str) or not re.fullmatch(r"[0-9]{13}",raw):
        return None
    digits=[int(c) for c in raw]
    check=(10-(sum(digits[:12:2])+3*sum(digits[1:12:2]))%10)%10
    return raw if digits[-1]==check else None

def listing_size_hint(name):
    """Extract only explicitly labeled Japanese/English centimeter shoe sizes."""
    # Not a verified product attribute: merchant titles can be inaccurate.
    match=re.search(r"(?<![\d.])((?:2[0-9]|30)(?:\.[05])?)\s*(?:cm|センチ)(?![a-z])", name, re.I)
    if not match:
        return None
    value=float(match.group(1))
    return value if 20 <= value <= 30 else None


def canonical_listing_url(url):
    """Remove volatile tracking query; preserve seller listing path and SKU."""
    p=urllib.parse.urlsplit(str(url or ""))
    if p.scheme!="https" or not p.hostname or p.username or p.password:
        return None
    return urllib.parse.urlunsplit((p.scheme,p.netloc.lower(),p.path.rstrip("/") or "/","",""))

def dedupe_candidates(rows):
    """Do not collapse different SKUs or different actual listing URLs."""
    unique={}
    for r in rows:
        url=canonical_listing_url(r.get("url"))
        if not url:
            continue
        key=(r.get("watch_sku","").upper(),url)
        old=unique.get(key)
        quality=lambda x:(bool(x.get("jan_code")),bool(x.get("image_url")),bool(x.get("size_cm_hint")))
        if old is None or quality(r)>quality(old):
            unique[key]=r
    return list(unique.values())

def collect(key,queries,request=None,exploration_queries=None):
    def fetch(url):
        try:
            with urllib.request.urlopen(urllib.request.Request(url,headers={"User-Agent":"PremiumPulse/1.0"}),timeout=20) as resp:
                return json.loads(resp.read(4000000).decode("utf-8"))
        except urllib.error.HTTPError as e:
            print(f"Yahoo Shopping API returned HTTP {e.code}.")
            if e.code==403:
                print("Check GitHub Actions Client ID secret and official API access.")
            raise SystemExit(1) from None
    request=request or fetch
    now=dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).replace(microsecond=0).isoformat()
    result=[]
    blocked=("靴紐","シューレース","キーホルダー","ステッカー","インソール","ソックス","靴下")
    def listing(hit,sku,mode):
        name=str(hit.get("name") or "")
        price=hit.get("price")
        link=str(hit.get("url") or "")
        if type(price) is not int or not 0<price<10000000 or not canonical_listing_url(link):
            return None
        if any(word in name for word in blocked):
            return None
        seller=hit.get("seller") or {}
        return {"watch_sku":sku,"name":name[:240],"price_jpy":price,"price_kind":"listing",
            "verification":"pending","condition_hint":hit.get("condition"),
            "seller":seller.get("name") if isinstance(seller,dict) else None,
            "url":link,"image_url":official_image(hit),"jan_code":jan_code_hint(hit),
            "size_cm_hint":listing_size_hint(name),"observed_at":now,
            "source":"Yahoo! Shopping API v3","brand_hint":classify_brand(name),
            "collection_mode":mode,
            "warning":"未検証の出品価格候補。サイズ・状態・JAN・真贋を要確認。成約価格ではありません。"}
    for item in queries:
        sku=str(item["sku"]).strip().upper()
        query=str(item["query"]).strip()
        if not re.fullmatch(r"[A-Z0-9_.-]{4,32}",sku) or not 0<len(query)<=120:
            raise ValueError("Invalid watch query")
        url=API+"?"+urllib.parse.urlencode({"appid":key,"query":query,"results":10,"in_stock":"true","image_size":300})
        for hit in request(url).get("hits",[]):
            name=str(hit.get("name") or "")
            if not re.search(r"(?<![A-Za-z0-9])"+re.escape(sku)+r"(?![A-Za-z0-9])",name,re.I):
                continue
            row=listing(hit,sku,"tracked")
            if row:
                result.append(row)
    # Query every configured brand once per collection, rotating through that
    # brand's search themes. This gives each brand daily discovery coverage
    # without auto-verifying model identity.
    topics=list(exploration_queries or [])
    allowed_brands=("Nike","adidas","New Balance","ASICS","PUMA")
    by_brand={brand:[] for brand in allowed_brands}
    for topic in topics:
        brand=str(topic["brand"])
        query=str(topic["query"]).strip()
        if brand not in allowed_brands or not 0<len(query)<=120:
            raise ValueError("Invalid expansion query")
        by_brand[brand].append(query)
    if topics:
        day=dt.datetime.fromisoformat(now).date().toordinal()
        for brand in allowed_brands:
            queries_for_brand=by_brand[brand]
            if not queries_for_brand:
                continue
            query=queries_for_brand[day % len(queries_for_brand)]
            url=API+"?"+urllib.parse.urlencode({"appid":key,"query":query,"results":30,"in_stock":"true","image_size":300})
            try:
                payload=request(url)
            except SystemExit:
                print(f"Optional {brand} discovery query rejected; keeping other brand and tracked candidates.")
                continue
            for hit in payload.get("hits",[]):
                name=str(hit.get("name") or "")
                if classify_brand(name)!=brand:
                    continue
                for sku in extract_skus(name,brand):
                    row=listing(hit,sku,"brand_discovery")
                    if row:
                        result.append(row)
    unique=dedupe_candidates(result)
    removed=len(result)-len(unique)
    if removed:
        print(f"Excluded {removed} duplicate SKU/listing links.")
    return {"generated_at":now,"status":"unverified_candidates","source":"Yahoo! Shopping API v3",
            "count":len(unique),"duplicates_removed":removed,"candidates":unique}

def main():
    key=os.environ.get("YAHOO_SHOPPING_APP_ID","").strip()
    if not key:
        print("ERROR: YAHOO_SHOPPING_APP_ID secret missing or empty. Configure repository Actions secret.")
        raise SystemExit(1)
    queries=json.loads((ROOT/"data/watch_queries.json").read_text(encoding="utf-8"))
    extra=json.loads((ROOT/'data/expansion_queries.json').read_text(encoding='utf-8'))
    result=collect(key,queries,exploration_queries=extra)
    (ROOT/"data/review_candidates.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"Collected {result['count']} unverified candidates; never auto-published")
if __name__=="__main__":main()
