# -*- coding: utf-8 -*-
"""盘后档 2026-08-28 增量写入：indices(A股3收盘+港股2新闻口径) / etf_intraday(收盘9) / fund_nav(8/28当日+QDII T+1)"""
import json, os, csv

BASE = '/Users/jieyang/Documents/WealthHub'
HIST = os.path.join(BASE, 'data/processed/history')
TODAY = '2026-08-28'

with open(os.path.join(HIST, 'close_20260828.json'), encoding='utf-8') as f:
    data = json.load(f)

# ---------- 1. indices ----------
idx_path = os.path.join(HIST, 'indices.csv')
existing = set()
with open(idx_path, encoding='utf-8-sig') as f:
    for row in csv.reader(f):
        if row and len(row) >= 7:
            existing.add((row[1], row[3], row[6]))  # (date, code, note)
new_idx = []
for i in data['indices']:  # A股收盘
    key = (i['date'], i['code'], i['note'])
    if key not in existing and i['close'] is not None:
        new_idx.append([i['type'], i['date'], i['name'], i['code'], str(i['close']), str(i['pct_change']), i['note']])
# 港股新闻口径补录（spot 盘后连续第13日失败，本次用新华网/证券时报/中新经纬三源交叉：恒指 25584.79 +0.07% / 恒科 4605.15 -0.33%）
hk_news = [
    ['index', TODAY, '恒生指数', 'HSI', '25584.79', '0.07', '收盘20:00(新闻口径补录)'],
    ['index', TODAY, '恒生科技', 'HSTECH', '4605.15', '-0.33', '收盘20:00(新闻口径补录)'],
]
for h in hk_news:
    key = (h[1], h[3], h[6])
    if key not in existing:
        new_idx.append(h)
if new_idx:
    with open(idx_path, 'a', encoding='utf-8') as f:
        for row in new_idx:
            f.write(','.join(row) + '\n')
    print(f'indices 新增 {len(new_idx)} 行:')
    for r in new_idx:
        print('  ' + ','.join(r))
else:
    print('indices 无新增')

# ---------- 2. etf_intraday ----------
etf_path = os.path.join(HIST, 'etf_intraday.csv')
existing_etf = set()
with open(etf_path, encoding='utf-8-sig') as f:
    for row in csv.reader(f):
        if row and len(row) >= 7:
            existing_etf.add((row[0], row[1], row[6]))  # (date, code, note)
new_etf = []
for e in data['etf']:
    key = (e['date'], e['code'], e['note'])
    if key not in existing_etf:
        new_etf.append([e['date'], e['code'], e['name'], str(e['price']), str(e['pct']), str(e['amount_wan']), e['note']])
if new_etf:
    with open(etf_path, 'a', encoding='utf-8') as f:
        for row in new_etf:
            f.write(','.join(row) + '\n')
    print(f'\netf_intraday 新增 {len(new_etf)} 行:')
    for r in new_etf:
        print('  ' + ','.join(r))
else:
    print('etf_intraday 无新增')

# ---------- 3. fund_nav (code, nav_date) 判重：8/28 当日净值 + 8/27 补录(含QDII T+1宽松) ----------
fund_path = os.path.join(HIST, 'fund_nav.csv')
existing_fund = set()
with open(fund_path, encoding='utf-8-sig') as f:
    for row in csv.reader(f):
        if row and len(row) >= 6:
            existing_fund.add((row[1], row[3]))  # (code, nav_date)
new_fund = []
for n in data['fund_navs']:
    key = (n['code'], n['nav_date'])
    if key not in existing_fund and n['nav'] is not None:
        # 记录字段：record_date(TODAY), code, name, nav_date, nav, pct
        new_fund.append([TODAY, n['code'], n['name'], n['nav_date'], str(n['nav']), str(n['pct']) if n['pct'] is not None else ''])
if new_fund:
    with open(fund_path, 'a', encoding='utf-8') as f:
        for row in new_fund:
            f.write(','.join(row) + '\n')
    print(f'\nfund_nav 新增 {len(new_fund)} 行:')
    for r in new_fund:
        print('  ' + ','.join(r))
else:
    print('fund_nav 无新增')

print('\nDONE 增量写入完成')
