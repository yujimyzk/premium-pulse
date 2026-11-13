#!/usr/bin/env python3
"""Rebuild published prices from source-verified CSV. Does not scrape websites."""
import csv,json,datetime,pathlib,urllib.parse
base=pathlib.Path(__file__).resolve().parent
items=[]
with (base/'data/verified.csv').open(encoding='utf-8-sig',newline='') as file:
    for row in csv.DictReader(file):
        if not row.get('name','').strip():continue
        for key in ('id','name','brand','sku','source','checked'):
            if not row.get(key,'').strip():raise ValueError(f'Missing {key}')
        source=urllib.parse.urlparse(row['source'])
        if source.scheme!='https' or not source.netloc:raise ValueError('Source URL must be HTTPS')
        checked=datetime.date.fromisoformat(row['checked'])
        if checked>datetime.date.today():raise ValueError('Future observation date')
        retail=int(row['retail']);listing=int(row['listing']);prior=int(row['prior']) if row.get('prior') else 0
        if retail<=0 or listing<=0 or prior<0:raise ValueError('Invalid price')
        items.append({**{k:row.get(k,'') for k in ('id','name','brand','category','sku','source','checked','note')},'retail':retail,'listing':listing,'prior':prior})
out={'mode':'verified','updated':max([x['checked'] for x in items],default=None),'items':items}
(base/'data/latest.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(f'Validated {len(items)} rows')
