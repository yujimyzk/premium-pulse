#!/usr/bin/env python3
"""Collect unverified Yahoo! Shopping listing candidates via official V3 API."""
import datetime as dt
import json,os,pathlib,re,urllib.parse,urllib.request,urllib.error
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

def listing_size_hint(name):
    """Extract only explicitly labeled Japanese/English centimeter shoe sizes."""
    # Not a verified product attribute: merchant titles can be inaccurate.
    match=re.search(r"(?<![\d.])((?:2[0-9]|30)(?:\.[05])?)\s*(?:cm|センチ)(?![a-z])", name, re.I)
    if not match:
        return None
    value=float(match.group(1))
    return value if 20 <= value <= 30 else None

def collect(key,queries,request=None):
    def fetch(url):
        try:
            with urllib.request.urlopen(urllib.request.Request(url,headers={"User-Agent":"PremiumPulse/1.0"}),timeout=20) as resp:
                return json.loads(resp.read(4000000).decode("utf-8"))
        except urllib.error.HTTPError as e:
            # Never print the request URL because it contains the Client ID.
            print(f"Yahoo Shopping API returned HTTP {e.code}.")
            # Inspect only a structured error code, never print URL or raw response/Client ID.
            try:
                body=json.loads(e.read(4096).decode("utf-8"))
                code=body.get("Error",{}).get("Code") or body.get("error",{}).get("code")
                if isinstance(code,str) and re.fullmatch(r"[A-Za-z0-9_-]{1,32}",code):
                    print(f"Yahoo API error code: {code}")
            except (ValueError,AttributeError,TypeError,UnicodeError):
                pass
            if e.code==403:
                print("Possible causes: wrong/unauthorized Client ID. Check the value in GitHub Actions Secret and official API access status.")
            raise SystemExit(1) from None
    request=request or fetch
    now=dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).replace(microsecond=0).isoformat()
    result=[]
    for item in queries:
        sku=str(item["sku"]).strip();query=str(item["query"]).strip()
        if not re.fullmatch(r"[A-Za-z0-9_.-]{4,32}",sku) or not 0<len(query)<=120:raise ValueError("Invalid watch query")
        url=API+"?"+urllib.parse.urlencode({"appid":key,"query":query,"results":10,"in_stock":"true","image_size":300})
        for hit in request(url).get("hits",[]):
            name=str(hit.get("name") or "")
            price=hit.get("price")
            link=str(hit.get("url") or "")
            parsed=urllib.parse.urlparse(link)
            if sku.lower() not in name.lower() or not isinstance(price,int) or price<=0 or parsed.scheme!="https" or not parsed.netloc:continue
            result.append({"watch_sku":sku,"name":name[:240],"price_jpy":price,"price_kind":"listing",
              "verification":"pending","condition_hint":hit.get("condition"),"seller":(hit.get("seller") or {}).get("name"),
              "url":link,"image_url":official_image(hit),"size_cm_hint":listing_size_hint(name),"observed_at":now,"source":"Yahoo! Shopping API v3",
              "warning":"未検証の出品価格候補。サイズ・状態・定価・真贋・出品内容を要確認。成約価格ではありません。"})
    return {"generated_at":now,"status":"unverified_candidates","source":"Yahoo! Shopping API v3","count":len(result),"candidates":result}
def main():
    key=os.environ.get("YAHOO_SHOPPING_APP_ID","").strip()
    if not key:
        print("ERROR: YAHOO_SHOPPING_APP_ID secret missing or empty. Configure repository Actions secret.")
        raise SystemExit(1)
    queries=json.loads((ROOT/"data/watch_queries.json").read_text(encoding="utf-8"))
    result=collect(key,queries)
    (ROOT/"data/review_candidates.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"Collected {result['count']} unverified candidates; never auto-published")
if __name__=="__main__":main()
