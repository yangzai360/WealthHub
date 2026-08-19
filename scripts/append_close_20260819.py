# -*- coding: utf-8 -*-
"""盘后档 2026-08-19 增量写入：indices(A股4收盘+沪深300+港股2新闻口径) / etf_intraday(收盘9) / fund_nav(8/19当日净值+QDII补更)"""
import json, os, csv

BASE = '/Users/jieyang/Documents/WealthHub'
HIST = os.path.join(BASE, 'data/processed/history')
TODAY = '2026-08-19'

with open(os.path.join(HIST, 'close_20260819.json'), encoding='utf-8') as f:
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
# 沪深300 收盘（额外抓取）
idx_extra = [
    ['index', TODAY, '沪深300', '000300', '4588.70', '-2.90', '收盘20:00'],
]
for i in idx_extra:
    key = (i[1], i[3], i[6])
    if key not in existing:
        new_idx.append(i)
# 港股新闻口径补录（spot 连续第6日盘后失败，本次用新华社/证券时报收评：恒指 25495.07 +0.09% / 恒科 4682.05 -1.21%）
hk_news = [
    ['index', TODAY, '恒生指数', 'HSI', '25495.07', '0.09', '收盘20:00(新闻口径补录)'],
    ['index', TODAY, '恒生科技', 'HSTECH', '4682.05', '-1.21', '收盘20:00(新闻口径补录)'],
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

# ---------- 3. fund_nav (code, nav_date) 判重，8/19 当日净值 + QDII 补更 ----------
fund_path = os.path.join(HIST, 'fund_nav.csv')
existing_fund = set()
with open(fund_path, encoding='utf-8-sig') as f:
    for row in csv.reader(f):
        if row and len(row) >= 6:
            existing_fund.add((row[1], row[3]))  # (code, nav_date)
new_fund = []
for n in data['fund_navs']:
    key = (n['code'], n['nav_date'])
    if key not in existing_fund and n['nav'] is not None and n['nav_date'] >= '2026-08-19':
        new_fund.append([TODAY, n['code'], n['name'], n['nav_date'], str(n['nav']), str(n['pct']) if n['pct'] is not None else ''])
# QDII 交银海外互联 8/18 补更（T+1，盘前停在 8/17）
extra_fund = [
    [TODAY, '164906', '交银海外互联', '2026-08-18', '0.961', '-0.23'],
]
for f_ in extra_fund:
    key = (f_[1], f_[3])
    if key not in existing_fund:
        new_fund.append(f_)
if new_fund:
    with open(fund_path, 'a', encoding='utf-8') as f:
        for row in new_fund:
            f.write(','.join(row) + '\n')
    print(f'\nfund_nav 新增 {len(new_fund)} 行:')
    for r in new_fund:
        print('  ' + ','.join(r))
else:
    print('fund_nav 无 8/19 当日新增（T+1 未更新，正常）')

print('\nDONE 增量写入完成')
