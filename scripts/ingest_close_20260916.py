# -*- coding: utf-8 -*-
"""2026-09-16 盘后：增量写入 indices.csv / etf_intraday.csv / fund_nav.csv
判重：indices/etf 用整行；fund_nav 用 (code, nav_date) 二元组（§3.86 修正：不含写入日）
写入：字节追加，保留原 BOM 与行尾风格（§3.87 教训：禁止 csv 模块整表重写）"""
import json, os, csv

BASE = '/Users/jieyang/Documents/WealthHub'
HIST = os.path.join(BASE, 'data/processed/history')
TODAY = '2026-09-16'
NOTE = '收盘20:00'

d = json.load(open(os.path.join(HIST, 'close_' + TODAY.replace('-', '') + '.json'), encoding='utf-8'))


def append_rows(path, rows, expect_bom=True):
    """按字节追加，校验 BOM 与末行行尾（新行统一 LF）"""
    data = open(path, 'rb').read()
    if expect_bom:
        assert data[:3] == b'\xef\xbb\xbf', f'{path} 缺 BOM，终止'
    assert data.endswith(b'\n'), f'{path} 末行无换行，终止'
    buf = ''.join(','.join(r) + '\n' for r in rows).encode('utf-8')
    with open(path, 'ab') as f:
        f.write(buf)
    return len(rows)


def normalize_eol(path):
    """把遗留 CRLF 行尾统一为 LF（仅删除 \\r，不改变任何字段值），并校验数据行集合不变"""
    raw = open(path, 'rb').read()
    n_crlf = raw.count(b'\r\n')
    if n_crlf == 0:
        return 0
    rows_before = [l for l in raw.split(b'\n')]
    fixed = raw.replace(b'\r\n', b'\n')
    rows_after = [l for l in fixed.split(b'\n')]
    assert len(rows_before) == len(rows_after), '行数变化，终止'
    assert [l.rstrip(b'\r') for l in rows_before] == rows_after, '字段值变化，终止'
    with open(path, 'wb') as f:
        f.write(fixed)
    return n_crlf


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
n = append_rows(p, add)
print(f'indices.csv +{n} 行')

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
print(f'etf_intraday.csv +{n} 行')

# ---------- 3. fund_nav.csv（(code, nav_date) 二元组判重，§3.86） ----------
p = os.path.join(HIST, 'fund_nav.csv')
nfix = normalize_eol(p)
print(f'fund_nav.csv 行尾归一化（CRLF→LF）: {nfix} 行（仅删除 \\r，字段值不变）')
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
