# -*- coding: utf-8 -*-
"""2026-10-18 纯非交易日档：美股 10/16（美东周五）收盘归档 → indices.csv 增量写入
判重键 = (type, date, code)（§3.108 条款 21 精神：KEY 不可退化）
"""
import csv, json, os

BASE = '/Users/jieyang/Documents/WealthHub'
HIST = os.path.join(BASE, 'data/processed/history')
P = os.path.join(HIST, 'indices.csv')
cur = json.load(open(os.path.join(HIST, 'close_20261018.json'), encoding='utf-8'))

rows_existing = list(csv.DictReader(open(P, encoding='utf-8-sig')))
keys = {(r['type'], r['date'], r['code']) for r in rows_existing}
print(f'既有行数 {len(rows_existing)}；10/16 行数 {sum(1 for r in rows_existing if r["date"]=="2026-10-16")}')

NEW = []
for x in cur['us']:
    if x.get('close') is None:
        print(f"  ⚠️ {x['code']} 数据暂缺，跳过写入")
        continue
    d = x['nav_date']
    k = ('us_index', d, x['code'])
    if k in keys:
        print(f'  已存在，跳过：{k}')
        continue
    NEW.append({'type': 'us_index', 'date': d, 'name': x['name'], 'code': x['code'],
                'close': x['close'], 'pct_change': round(x['pct_change'], 2),
                'note': '美股收盘(非交易日归档)'})
    keys.add(k)

# 保持文件原有 BOM（utf-8-sig）+ LF 追加
with open(P, 'a', encoding='utf-8-sig', newline='') as f:
    w = csv.DictWriter(f, fieldnames=['type', 'date', 'name', 'code', 'close', 'pct_change', 'note'])
    for r in NEW:
        w.writerow(r)

print(f'\n✅ 追加 {len(NEW)} 行：')
for r in NEW:
    print(f"  {r['date']} {r['code']:6s} {r['name']:14s} {r['close']:>11,.4f} {r['pct_change']:+.2f}%")

# 回读校验
back = list(csv.DictReader(open(P, encoding='utf-8-sig')))
print(f'\n回读行数 {len(back)}（+{len(back)-len(rows_existing)}）')
last = back[-len(NEW):] if NEW else []
print('末 %d 行：' % len(NEW))
for r in last:
    print('  ', r['date'], r['code'], r['close'], r['pct_change'])
