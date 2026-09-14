# -*- coding: utf-8 -*-
"""2026-09-14 盘后档增量入库: indices.csv / etf_intraday.csv / fund_nav.csv
判重 key = 整行（§3.9 补充7）"""
import json, os, csv

BASE = '/Users/jieyang/Documents/WealthHub'
HIST = os.path.join(BASE, 'data/processed/history')
TODAY = '2026-09-14'

cur = json.load(open(os.path.join(HIST, 'close_20260914.json'), encoding='utf-8'))

def append_csv(path, header, rows):
    existing = set()
    if os.path.exists(path):
        with open(path, encoding='utf-8-sig') as f:
            for ln in f.read().splitlines()[1:]:
                if ln.strip():
                    existing.add(ln.strip())
    added = 0
    with open(path, 'a', encoding='utf-8') as f:
        for r in rows:
            line = ','.join(str(x) for x in r)
            if line not in existing:
                f.write(line + '\n')
                existing.add(line)
                added += 1
    return added

# ---------- 1. indices.csv ----------
rows = []
for r in cur['indices']:
    rows.append([r['type'], r['date'], r['name'], r['code'], r['close'], r['pct_change'], r['note']])
for r in cur['hk']:
    rows.append([r['type'], r['date'], r['name'], r['code'], r['close'], r['pct_change'], r['note']])
n1 = append_csv(os.path.join(HIST, 'indices.csv'),
                ['type', 'date', 'name', 'code', 'close', 'pct_change', 'note'], rows)
print(f'indices.csv +{n1} 行')

# ---------- 2. etf_intraday.csv ----------
rows = []
for r in cur['etf']:
    rows.append([r['date'], r['code'], r['name'], r['price'], r['pct'], r['amount_wan'], r['note']])
n2 = append_csv(os.path.join(HIST, 'etf_intraday.csv'),
                ['date', 'code', 'name', 'price', 'pct', 'amount_wan', 'note'], rows)
print(f'etf_intraday.csv +{n2} 行')

# ---------- 3. fund_nav.csv (date=归档日, nav_date=净值日) ----------
rows = []
for r in cur['fund_navs']:
    if r['nav_date'] == TODAY or r['nav_date'] == '2026-09-11':
        rows.append([TODAY, r['code'], r['name'], r['nav_date'], r['nav'], r['pct']])
n3 = append_csv(os.path.join(HIST, 'fund_nav.csv'),
                ['date', 'code', 'name', 'nav_date', 'nav', 'pct'], rows)
print(f'fund_nav.csv +{n3} 行')

# ---------- 校验 ----------
for fn in ['indices.csv', 'etf_intraday.csv', 'fund_nav.csv']:
    p = os.path.join(HIST, fn)
    with open(p, encoding='utf-8-sig') as f:
        lines = [l for l in f.read().splitlines() if l.strip()]
    print(f'{fn}: {len(lines)-1} 数据行')
    for l in lines[-4:]:
        print('   ', l)
