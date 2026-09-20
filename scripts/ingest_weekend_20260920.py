# -*- coding: utf-8 -*-
"""2026-09-20 周日盘后档：增量写入 indices.csv（美股 9/18 收盘 8 行）与 fund_nav.csv（未入库净值）
判重：indices 用整行；fund_nav 用 (code, nav_date) 二元组（§3.86）
写入：字节追加，保留原 BOM 与「末行行尾」风格（§3.87/§3.89：禁止整表重写/归一化）
"""
import json, os, csv

BASE = '/Users/jieyang/Documents/WealthHub'
HIST = os.path.join(BASE, 'data/processed/history')
TODAY = '2026-09-20'
US_DAY = '2026-09-18'

d = json.load(open(os.path.join(HIST, 'close_' + TODAY.replace('-', '') + '.json'), encoding='utf-8'))

NAME_MAP = {
    'XLV': '美股医疗XLV', 'IYH': '美股医疗IYH', 'QQQ': '纳指100ETF',
    'DIA': '道指ETF', 'SPY': '标普500ETF',
    '.IXIC': '纳斯达克', '.DJI': '道琼斯', '.INX': '标普500',
}


def append_rows(path, rows, expect_bom=True):
    data = open(path, 'rb').read()
    if expect_bom:
        assert data[:3] == b'\xef\xbb\xbf', f'{path} 缺 BOM，终止'
    assert data.endswith(b'\n'), f'{path} 末行无换行，终止'
    eol = b'\r\n' if data.endswith(b'\r\n') else b'\n'
    buf = b''.join((','.join(r) + '\n').encode('utf-8').replace(b'\n', eol) for r in rows)
    with open(path, 'ab') as f:
        f.write(buf)
    return len(rows)


# ---------- 1. indices.csv：美股 9/18 收盘 ----------
rows_idx = []
for x in d['us']:
    if x['close'] is None:
        print('SKIP 数据暂缺', x['code']); continue
    rows_idx.append(['us_index', US_DAY, NAME_MAP[x['code']], x['code'],
                     str(x['close']), str(x['pct_change']), '美股收盘'])

p = os.path.join(HIST, 'indices.csv')
exist = set()
with open(p, encoding='utf-8-sig') as f:
    for r in csv.reader(f):
        exist.add(tuple(r))
add = [r for r in rows_idx if tuple(r) not in exist]
n = append_rows(p, add)
print(f'indices.csv +{n} 行 (候选 {len(rows_idx)})')
for r in add:
    print('   ', r)

# ---------- 2. fund_nav.csv：(code, nav_date) 判重 ----------
p = os.path.join(HIST, 'fund_nav.csv')
exist = set()
with open(p, encoding='utf-8-sig') as f:
    for r in csv.reader(f):
        if len(r) >= 4:
            exist.add((r[1], r[3]))
add = []
for n_ in d['fund_navs']:
    if n_['nav_date'] < '2026-09-16':
        continue
    key = (n_['code'], n_['nav_date'])
    if key in exist:
        continue
    exist.add(key)
    add.append([TODAY, n_['code'], n_['name'], n_['nav_date'], str(round(n_['nav'], 4)),
                '' if n_['pct'] is None else str(n_['pct'])])
n = append_rows(p, add, expect_bom=False)
print(f'fund_nav.csv +{n} 行')
for r in sorted(add, key=lambda y: (y[3], y[1])):
    print('   ', r)
