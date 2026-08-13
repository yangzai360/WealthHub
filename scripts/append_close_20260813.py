# -*- coding: utf-8 -*-
"""盘后档 2026-08-13 增量写入：indices(收盘5+美股XLV回填) / etf_intraday(收盘9) / fund_nav(8/13当日净值)"""
import json, os, csv

BASE = '/Users/jieyang/Documents/WealthHub'
HIST = os.path.join(BASE, 'data/processed/history')
TODAY = '2026-08-13'

with open(os.path.join(HIST, 'close_20260813.json'), encoding='utf-8') as f:
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
for h in data['hk']:  # 港股收盘（新闻口径补录）
    key = (h['date'], h['code'], h['note'])
    if key not in existing and h['close'] is not None:
        new_idx.append([h['type'], h['date'], h['name'], h['code'], str(h['close']), str(h['pct_change']), h['note']])
# 美股 XLV 8/12 回填（盘前只写了 IYH 8/12）
x = data['us'].get('XLV', {})
if x and x.get('date') == '2026-08-12':
    key = ('2026-08-12', 'XLV', '美股收盘(8/12回填)')
    if key not in existing:
        new_idx.append(['us_index', '2026-08-12', '美股医疗XLV', 'XLV', str(x['close']), str(x['pct']), '美股收盘(8/12回填)'])
if new_idx:
    with open(idx_path, 'a', encoding='utf-8') as f:
        for row in new_idx:
            f.write(','.join(row) + '\n')
    print(f'indices 新增 {len(new_idx)} 行:')
    for r in new_idx:
        print('  ' + ','.join(r))

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

# ---------- 3. fund_nav ----------
fund_path = os.path.join(HIST, 'fund_nav.csv')
existing_fund = set()
with open(fund_path, encoding='utf-8-sig') as f:
    for row in csv.reader(f):
        if row and len(row) >= 6:
            existing_fund.add((row[1], row[3]))  # (code, nav_date)
new_fund = []
for n in data['fund_navs']:
    key = (n['code'], n['nav_date'])
    if key not in existing_fund and n['nav'] is not None and n['nav_date'] == '2026-08-13':
        new_fund.append([TODAY, n['code'], n['name'], n['nav_date'], str(n['nav']), str(n['pct']) if n['pct'] is not None else ''])
if new_fund:
    with open(fund_path, 'a', encoding='utf-8') as f:
        for row in new_fund:
            f.write(','.join(row) + '\n')
    print(f'\nfund_nav 新增 {len(new_fund)} 行(8/13当日净值):')
    for r in new_fund:
        print('  ' + ','.join(r))

print('\nDONE 增量写入完成')
