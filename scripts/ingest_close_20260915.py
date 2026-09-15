# -*- coding: utf-8 -*-
"""2026-09-15 盘后：增量写入 indices.csv / etf_intraday.csv / fund_nav.csv
判重规则：indices/etf 用整行；fund_nav 用 (date, code, nav_date) 三元组（§3.81）"""
import json, os, csv

BASE = '/Users/jieyang/Documents/WealthHub'
HIST = os.path.join(BASE, 'data/processed/history')
TODAY = '2026-09-15'
NOTE = '收盘20:00'

d = json.load(open(os.path.join(HIST, 'close_' + TODAY.replace('-', '') + '.json'), encoding='utf-8'))

# ---------- 1. indices.csv ----------
IDX = {x['code']: x for x in d['indices']}
HK = {x['code']: x for x in d['hk']}
rows_idx = []
idx_meta = [('sh000001', '上证指数', '000001'), ('sz399001', '深证成指', '399001'),
            ('sz399006', '创业板指', '399006'), ('sh000300', '沪深300', '000300'),
            ('sh000932', '中证消费', '000932'), ('sh000933', '中证医药', '000933'),
            ('sz399989', '中证医疗', '399989'), ('sz399997', '中证白酒', '399997'),
            ('sh000688', '科创50', '000688'), ('sh000827', '中证环保', '000827')]
for sym, name, code in idx_meta:
    x = IDX.get(sym)
    if not x:
        print('MISS index', name); continue
    rows_idx.append(['index', TODAY, name, code, str(x['close']), str(x['pct']), NOTE + '(新浪hq直取)'])
for sym, name, code in [('HSI', '恒生指数', 'HSI'), ('HSTECH', '恒生科技', 'HSTECH')]:
    x = HK.get(sym)
    if not x:
        print('MISS hk', name); continue
    rows_idx.append(['index', TODAY, name, code, str(x['close']), str(x['pct']), NOTE + '(新浪hq直取)'])

p = os.path.join(HIST, 'indices.csv')
exist = set()
with open(p, encoding='utf-8-sig') as f:
    for r in csv.reader(f):
        exist.add(tuple(r))
add = [r for r in rows_idx if tuple(r) not in exist]
with open(p, 'a', encoding='utf-8-sig', newline='') as f:
    csv.writer(f).writerows(add)
print(f'indices.csv +{len(add)} 行')

# ---------- 2. etf_intraday.csv ----------
rows_etf = []
for x in d['etf']:
    rows_etf.append([TODAY, x['code'].replace('sh', '').replace('sz', ''), x['name'],
                     str(x['close']), str(x['pct']), str(round(float(x['amount']) / 10000, 1)), NOTE])
p = os.path.join(HIST, 'etf_intraday.csv')
exist = set()
with open(p, encoding='utf-8-sig') as f:
    for r in csv.reader(f):
        exist.add(tuple(r))
add = [r for r in rows_etf if tuple(r) not in exist]
with open(p, 'a', encoding='utf-8-sig', newline='') as f:
    csv.writer(f).writerows(add)
print(f'etf_intraday.csv +{len(add)} 行')

# ---------- 3. fund_nav.csv ----------
p = os.path.join(HIST, 'fund_nav.csv')
exist = set()
with open(p, encoding='utf-8-sig') as f:
    for r in csv.reader(f):
        if len(r) >= 4:
            exist.add((r[0], r[1], r[3]))
add = []
for n in d['fund_navs']:
    if n['nav_date'] < '2026-09-11':
        continue
    key = (TODAY, n['code'], n['nav_date'])
    if key in exist:
        continue
    exist.add(key)
    add.append([TODAY, n['code'], n['name'], n['nav_date'], str(round(n['nav'], 4)),
                '' if n['pct'] is None else str(n['pct'])])
with open(p, 'a', encoding='utf-8-sig', newline='') as f:
    csv.writer(f).writerows(add)
print(f'fund_nav.csv +{len(add)} 行')
for r in add:
    print('   ', r)
