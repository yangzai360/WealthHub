# -*- coding: utf-8 -*-
"""2026-09-13 周日: W37 周度统计 + 窗口统计 + 夏普/回撤"""
import json, os, csv, glob, math
from collections import defaultdict

BASE = '/Users/jieyang/Documents/WealthHub'
HIST = os.path.join(BASE, 'data/processed/history')

# ---------- 1. 链路日收益序列 ----------
seq = []
for fp in sorted(glob.glob(os.path.join(HIST, 'portfolio_close_*.json'))):
    d = json.load(open(fp, encoding='utf-8'))
    dt = d.get('date') or os.path.basename(fp).replace('portfolio_close_', '').replace('.json', '')
    dt = f'{dt[:4]}-{dt[4:6]}-{dt[6:8]}' if len(dt) == 8 else dt
    mv = d.get('total_mv') or d.get('total')
    seq.append((dt, d['est_total_pct'], mv))
print('【链路日收益序列】')
for d, p, mv in seq:
    print(f'  {d}  {p:+.2f}%  mv={mv}')
print(f'  交易日数 = {len(seq)}')

# W37 = 9/7-9/11
w37 = [s for s in seq if '2026-09-07' <= s[0] <= '2026-09-11']
cum = 1.0
for _, p, _ in w37:
    cum *= (1 + p / 100)
print(f'\n【W37 (9/7-9/11)】日: ' + ' / '.join(f'{d[5:]} {p:+.2f}%' for d, p, _ in w37))
print(f'  周累计 {(cum-1)*100:+.2f}%')

# 链路累计
c = 1.0
for _, p, _ in seq:
    c *= (1 + p / 100)
print(f'链路累计(8/6起) {(c-1)*100:+.2f}%')

# 夏普
vals = [p / 100 for _, p, _ in seq]
n = len(vals)
mean = sum(vals) / n
sd = math.sqrt(sum((v - mean) ** 2 for v in vals) / (n - 1))
rf = 0.0169
sharpe = (mean * 252 - rf) / (sd * math.sqrt(252))
print(f'夏普(年化) {sharpe:.2f}  日均值 {mean*100:+.4f}%  日波动 {sd*100:.4f}%  n={n}')

# 最大回撤（按 total_mv）
mv = [s[2] for s in seq if s[2]]
peak = mv[0]; mdd = 0
for v in mv:
    peak = max(peak, v)
    mdd = min(mdd, (v / peak - 1) * 100)
print(f'链路最大回撤 {mdd:.2f}%  (起点 {mv[0]:.2f} → 末 {mv[-1]:.2f})')

# ---------- 2. 窗口统计（指数口径） ----------
rows = list(csv.reader(open(os.path.join(HIST, 'indices.csv'), encoding='utf-8-sig')))[1:]
by = defaultdict(list)
for r in rows:
    if len(r) < 6 or r[0] != 'index' or not r[4] or r[5] in ('', None):
        continue
    try:
        by[(r[3], r[2])].append((r[1], float(r[4])))
    except Exception:
        pass
print('\n【窗口统计（9/11 收盘口径）】')
targets = [('000932', '中证消费'), ('000001', '上证指数'), ('399006', '创业板指'),
           ('HSTECH', '恒生科技'), ('HSI', '恒生指数')]
for code, name in targets:
    v = sorted(by.get((code, name), []), key=lambda x: x[0])
    if len(v) < 11:
        # 尝试只按 code 找
        for (c2, n2), vv in by.items():
            if c2 == code:
                v = sorted(vv, key=lambda x: x[0]); break
    if len(v) >= 11:
        last = v[-1][1]
        r3 = (last / v[-4][1] - 1) * 100
        r5 = (last / v[-6][1] - 1) * 100
        r10 = (last / v[-11][1] - 1) * 100
        print(f'  {name:8s} 3日 {r3:+.2f}%  5日 {r5:+.2f}%  10日 {r10:+.2f}%  (末值 {last})')
    else:
        print(f'  {name:8s} 样本不足 n={len(v)}')

# 美股 XLV/IYH
usby = defaultdict(list)
for r in rows:
    if len(r) < 6 or r[0] != 'us_index':
        continue
    try:
        usby[r[3]].append((r[1], float(r[4])))
    except Exception:
        pass
for code in ['XLV', 'IYH', 'QQQ', 'DIA']:
    v = sorted(usby.get(code, []), key=lambda x: x[0])
    # 去重（同日多条取最后）
    dd = {}
    for d, c in v:
        dd[d] = c
    v = sorted(dd.items())
    if len(v) >= 11:
        last = v[-1][1]
        r3 = (last / v[-4][1] - 1) * 100
        r5 = (last / v[-6][1] - 1) * 100
        r10 = (last / v[-11][1] - 1) * 100
        print(f'  {code:8s} 3日 {r3:+.2f}%  5日 {r5:+.2f}%  10日 {r10:+.2f}%  (末值 {last}, 末日 {v[-1][0]})')
