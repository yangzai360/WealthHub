# -*- coding: utf-8 -*-
"""把 close_20260811.json 增量写入 indices/etf_intraday/fund_nav CSV（判重 key=整行）"""
import json, os, csv

BASE = '/Users/jieyang/Documents/WealthHub'
HIST = os.path.join(BASE, 'data/processed/history')
d = json.load(open(os.path.join(HIST, 'close_20260811.json')))

def load_rows(path, ncols):
    if not os.path.exists(path):
        return []
    with open(path, encoding='utf-8-sig') as f:
        return [tuple(r[:ncols]) for r in csv.reader(f) if r and not r[0].startswith('type') and not r[0].startswith('date')]

def append_unique(path, headers, new_rows):
    existing = set(load_rows(path, len(headers)))
    added = 0
    with open(path, 'a', encoding='utf-8-sig') as f:
        w = csv.writer(f)
        for row in new_rows:
            row = [str(x) for x in row]
            if tuple(row) not in existing:
                w.writerow(row)
                existing.add(tuple(row))
                added += 1
    print(f'{os.path.basename(path)}: +{added} 行')

# 1. indices.csv: type,date,name,code,close,pct_change,note
idx_rows = []
for x in d['indices']:
    if x['close'] is None:
        continue
    idx_rows.append([x['type'], x['date'], x['name'], x['code'], x['close'], x['pct_change'], x['note']])
# 美股 8/10 收盘（XLV 新数据 + IYH 已在库判重跳过）
for sym in ['XLV', 'IYH']:
    if sym in d['us']:
        u = d['us'][sym]
        nm = '美股医疗XLV' if sym == 'XLV' else '美股医疗IYH'
        idx_rows.append(['us_index', u['date'], nm, sym, u['close'], u['pct'], '美股收盘(隔夜)'])
append_unique(os.path.join(HIST, 'indices.csv'), ['type','date','name','code','close','pct_change','note'], idx_rows)

# 2. etf_intraday.csv: date,code,name,price,pct,amount_wan,note
etf_rows = [[x['date'], x['code'], x['name'], x['price'], x['pct'], x['amount_wan'], x['note']] for x in d['etf']]
append_unique(os.path.join(HIST, 'etf_intraday.csv'), ['date','code','name','price','pct','amount_wan','note'], etf_rows)

# 3. fund_nav.csv: date,code,name,nav_date,nav,pct（6 列全含）
nav_rows = []
for x in d['fund_navs']:
    if x['nav'] is None:
        continue
    nav_rows.append([x['date'], x['code'], x['name'], x['nav_date'], x['nav'], x['pct'] if x['pct'] is not None else ''])
append_unique(os.path.join(HIST, 'fund_nav.csv'), ['date','code','name','nav_date','nav','pct'], nav_rows)

print('DONE')
