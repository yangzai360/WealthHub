# -*- coding: utf-8 -*-
"""2026-09-25 盘后：把 close_20260925.json 的场外净值增量写入 fund_nav.csv
⚠️ §3.81：判重用 (date, code, nav_date) 三元组
⚠️ §3.87/§3.89：字节级追加，禁止整表重写
⚠️ QDII 净值日口径：本档检查是否出现 9/24 的 QDII 净值（000369/016280/164906）
"""
import json, os, csv

BASE = '/Users/jieyang/Documents/WealthHub'
HIST = os.path.join(BASE, 'data/processed/history')
TODAY = '2026-09-25'
SRC = os.path.join(HIST, 'close_' + TODAY.replace('-', '') + '.json')
P = os.path.join(HIST, 'fund_nav.csv')

navs = json.load(open(SRC, encoding='utf-8'))['fund_navs']

existing = set()
with open(P, encoding='utf-8-sig') as fh:
    for row in csv.reader(fh):
        if len(row) >= 4:
            existing.add((row[0], row[1], row[3]))

rows = []
for n in navs:
    key = (TODAY, n['code'], n['nav_date'])
    if key in existing:
        continue
    rows.append([TODAY, n['code'], n['name'], n['nav_date'], n['nav'],
                 ('' if n.get('pct') is None else n['pct'])])

# 去重（同一 key 只留一条）
seen = set()
uniq = []
for r in rows:
    k = (r[0], r[1], r[3])
    if k in seen:
        continue
    seen.add(k)
    uniq.append(r)

if uniq:
    d = open(P, 'rb').read()
    assert d[:3] == b'\xef\xbb\xbf', 'BOM 缺失'
    eol = b'\r\n' if d.endswith(b'\r\n') else b'\n'
    if not d.endswith(eol):
        d = d + eol
    buf = b''.join(','.join(str(x) for x in r).encode('utf-8') + eol for r in uniq)
    with open(P, 'ab') as fh:
        fh.write(buf)

print(f'fund_nav.csv +{len(uniq)} 行 / -0（纯新增）')
for r in uniq:
    print('   +', r)

print('\n=== 当前各基金最新净值日（>=9/23） ===')
from collections import defaultdict
latest = {}
for n in navs:
    c = n['code']
    if c not in latest or n['nav_date'] > latest[c]['nav_date']:
        latest[c] = n
for c, v in sorted(latest.items()):
    if v['nav_date'] >= '2026-09-23':
        print(f"  {c}  {v['name']:22s} {v['nav_date']}  {v['nav']}  {v['pct']}")
