# -*- coding: utf-8 -*-
"""2026-09-18 盘后：增量写入 indices.csv / etf_intraday.csv / fund_nav.csv
判重：indices/etf 用整行；fund_nav 用 (code, nav_date) 二元组（§3.86）
写入：字节追加，保留原 BOM 与「末行行尾」风格（§3.87/§3.89 教训：禁止整表重写/归一化）
本档 indices 含 indices(6) + boards(7) + hk(2)；盘中档已写入的 board 行由整行判重自动跳过。
"""
import json, os, csv

BASE = '/Users/jieyang/Documents/WealthHub'
HIST = os.path.join(BASE, 'data/processed/history')
TODAY = '2026-09-18'
NOTE = '收盘20:00'

d = json.load(open(os.path.join(HIST, 'close_' + TODAY.replace('-', '') + '.json'), encoding='utf-8'))


def append_rows(path, rows, expect_bom=True):
    """按字节追加；BOM 校验可选；新行行尾 = 原末行行尾（§3.89 固化）"""
    data = open(path, 'rb').read()
    if expect_bom:
        assert data[:3] == b'\xef\xbb\xbf', f'{path} 缺 BOM，终止'
    assert data.endswith(b'\n'), f'{path} 末行无换行，终止'
    eol = b'\r\n' if data.endswith(b'\r\n') else b'\n'
    buf = b''.join((','.join(r) + '\n').encode('utf-8').replace(b'\n', eol) for r in rows)
    with open(path, 'ab') as f:
        f.write(buf)
    return len(rows)


# ---------- 1. indices.csv ----------
IDX = {x['code']: x for x in d['indices']}
BRD = {x['code']: x for x in d['boards']}
HK = {x['code']: x for x in d['hk']}
rows_idx = []
idx_meta = [('sh000001', '上证指数', '000001'), ('sz399001', '深证成指', '399001'),
            ('sz399006', '创业板指', '399006'), ('sh000300', '沪深300', '000300'),
            ('sh000932', '中证消费', '000932'), ('sh000688', '科创50', '000688')]
brd_meta = [('sh000933', '中证医药', '000933'), ('sz399989', '中证医疗', '399989'),
            ('sz399997', '中证白酒', '399997'), ('sh000827', '中证环保', '000827'),
            ('sh000934', '中证金融', '000934'), ('sh000913', '300医药', '000913'),
            ('sz399975', '证券公司', '399975')]
for sym, name, code in idx_meta:
    x = IDX.get(sym)
    if not x:
        print('MISS index', name); continue
    rows_idx.append(['index', TODAY, name, code, str(x['close']), str(x['pct']), NOTE + '(新浪hq直取)'])
for sym, name, code in brd_meta:
    x = BRD.get(sym)
    if not x:
        print('MISS board', name); continue
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
n = append_rows(p, add)
print(f'indices.csv +{n} 行 (候选 {len(rows_idx)})')

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
n = append_rows(p, add)
print(f'etf_intraday.csv +{n} 行 (候选 {len(rows_etf)})')

# ---------- 3. fund_nav.csv（(code, nav_date) 二元组判重，§3.86） ----------
p = os.path.join(HIST, 'fund_nav.csv')
exist = set()
with open(p, encoding='utf-8-sig') as f:
    for r in csv.reader(f):
        if len(r) >= 4:
            exist.add((r[1], r[3]))
add = []
for n_ in d['fund_navs']:
    if n_['nav_date'] < '2026-09-11':
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
