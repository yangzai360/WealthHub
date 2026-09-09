# -*- coding: utf-8 -*-
"""2026-09-09 盘后: close_20260909.json -> indices.csv/etf_intraday.csv/fund_nav.csv 增量写入
判重 key: indices=[type,date,code,note]; etf=[date,code,note]; fund_nav=[code,nav_date]"""
import json, os, csv

BASE = '/Users/jieyang/Documents/WealthHub'
HIST = os.path.join(BASE, 'data/processed/history')
with open(os.path.join(HIST, 'close_20260909.json'), encoding='utf-8') as f:
    close = json.load(f)

def load_lines(path):
    if os.path.exists(path) and os.path.getsize(path) > 0:
        with open(path, encoding='utf-8-sig') as f:
            return [l.rstrip('\n') for l in f if l.strip()]
    return []

def append_unique(path, rows, key_idx, header):
    existing = load_lines(path)
    keys = set()
    for r in existing[1:]:
        parts = r.split(',')
        if len(parts) > max(key_idx):
            keys.add(','.join(parts[i] for i in key_idx))
    new = []
    for row in rows:
        k = ','.join(str(row[i]) for i in key_idx)
        if k not in keys:
            new.append([str(x) for x in row])
            keys.add(k)
    if new:
        exists = os.path.exists(path) and os.path.getsize(path) > 0
        with open(path, 'a', encoding='utf-8-sig') as f:
            if not exists:
                f.write(header + '\n')
            for r in new:
                f.write(','.join(r) + '\n')
    return len(new)

# 1. indices（A股 5 + 港股 2）
idx_rows = []
for r in close['indices'] + close['hk']:
    if r.get('close') is None:
        continue
    idx_rows.append([r['type'], r['date'], r['name'], r['code'], r['close'], r['pct_change'], r['note']])
n1 = append_unique(os.path.join(HIST, 'indices.csv'), idx_rows, [0, 1, 3, 6],
                   'type,date,name,code,close,pct_change,note')
print(f'[indices] 新增 {n1} 条')

# 2. etf_intraday
etf_rows = [[r['date'], r['code'], r['name'], r['price'], r['pct'],
             round(float(r['amount_wan']) / 1e4, 1), r['note']] for r in close['etf']]
n2 = append_unique(os.path.join(HIST, 'etf_intraday.csv'), etf_rows, [0, 1, 6],
                   'date,code,name,price,pct,amount_wan,note')
print(f'[etf_intraday] 新增 {n2} 条')

# 3. fund_nav（只写 nav_date>=2026-09-06，避免历史行重复；QDII 9/7 补更 + 当日 9/9）
nav_rows = [['2026-09-09', r['code'], r['name'], r['nav_date'], r['nav'], r['pct'] if r['pct'] is not None else '']
            for r in close['fund_navs'] if r['nav_date'] >= '2026-09-06']
n3 = append_unique(os.path.join(HIST, 'fund_nav.csv'), nav_rows, [1, 3],
                   'date,code,name,nav_date,nav,pct')
print(f'[fund_nav] 新增 {n3} 条 (nav_date>=9/6)')

# 校验: 当日 indices 含 A股 5 + HSI/HSTECH 收盘行 (§3.59 教训)
with open(os.path.join(HIST, 'indices.csv'), encoding='utf-8-sig') as f:
    lines = f.readlines()
today_rows = [l.strip() for l in lines if '2026-09-09' in l and '收盘20:00' in l]
print(f'\n校验 indices.csv 今日收盘行 {len(today_rows)} 条:')
for l in today_rows:
    print('  ' + l)
assert len(today_rows) >= 7, '今日 indices 收盘行不足 7 条!'
print('\n校验通过: A股5 + 港股2 收盘行齐全')
