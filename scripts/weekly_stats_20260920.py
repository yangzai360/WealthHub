# -*- coding: utf-8 -*-
"""2026-09-20 周日：W38（9/14-9/18）周度统计
- 链路日收益样本：日期从【文件名】推导（§3.91）；起点 8/6 手工补入
- 夏普：rf 用「年化百分数 / 252」（§3.91，不再除 100）
- 赛道周度贡献：逐日 portfolio_close_*.json 的 tracks[k]['pnl'] 累加（9/18 用补更修正版）
"""
import json, os, csv, glob, math, re
from collections import defaultdict

BASE = '/Users/jieyang/Documents/WealthHub'
HIST = os.path.join(BASE, 'data/processed/history')
W_START, W_END = '2026-09-14', '2026-09-18'
RF_10Y = 1.69  # 10 年期国债收益率（年化百分数）

# ---------- 1. 链路日收益序列（文件名取日期） ----------
seq = []
for fp in sorted(glob.glob(os.path.join(HIST, 'portfolio_close_*.json'))):
    if fp.endswith('_fix.json'):
        continue
    m = re.search(r'(\d{4})(\d{2})(\d{2})', os.path.basename(fp))
    if not m:
        continue
    dt = f'{m.group(1)}-{m.group(2)}-{m.group(3)}'
    d = json.load(open(fp, encoding='utf-8'))
    seq.append([dt, d['est_total_pct'], d.get('total_mv') or d.get('total')])

# 9/18 用补更修正值
fix = json.load(open(os.path.join(HIST, 'portfolio_close_20260918_fix.json'), encoding='utf-8'))
for s in seq:
    if s[0] == '2026-09-18':
        s[1] = fix['est_total_pct']; s[2] = fix['total_mv']

# 起点 8/6（无 portfolio_close 产物，按已知值手工补入）
seq.insert(0, ['2026-08-06', -0.68, None])
# 过滤掉非交易日误入的产物
seq = [s for s in seq if s[0] >= '2026-08-06']

print('【链路日收益序列】')
for d, p, mv in seq:
    print(f'  {d}  {p:+.2f}%  mv={mv if mv is None else format(mv, ",.2f")}')
n_td = len(seq)
print(f'  交易日数 = {n_td}')

wk = [s for s in seq if W_START <= s[0] <= W_END]
cum = 1.0
for _, p, _ in wk:
    cum *= (1 + p / 100)
print(f'\n【W38 (9/14-9/18)】' + ' → '.join(f'{d[5:]} {p:+.2f}%' for d, p, _ in wk))
print(f'  周累计 {(cum - 1) * 100:+.2f}%   周收益额 {(seq[-1][2] - 373320.35):+,.2f} 元')
print(f'  周初 373,320.35 → 周末 {seq[-1][2]:,.2f}')

c = 1.0
for _, p, _ in seq:
    c *= (1 + p / 100)
print(f'\n链路累计(8/6起, {n_td} 交易日) {(c - 1) * 100:+.2f}%  ({seq[-1][2] - 387357.57 * 0:+,.0f})')

vals = [p / 100 for _, p, _ in seq]
n = len(vals)
mean = sum(vals) / n
sd = math.sqrt(sum((v - mean) ** 2 for v in vals) / (n - 1))
sharpe = (mean * 252 - RF_10Y / 100) / (sd * math.sqrt(252))
print(f'夏普(年化) {sharpe:.2f}   日均值 {mean * 100:+.4f}%   日波动 {sd * 100:.4f}%   n={n}')

mv = [s[2] for s in seq if s[2]]
nav = 1.0; peak = 1.0; mdd = 0.0; mdd_d = None
for s in seq:
    nav *= (1 + s[1] / 100)
    peak = max(peak, nav)
    v = (nav / peak - 1) * 100
    if v < mdd:
        mdd, mdd_d = v, s[0]
print(f'链路最大回撤(NAV序列口径,与 risk_stats 一致) {mdd:.2f}%  (谷底 {mdd_d})')

pos = sum(1 for _, p, _ in wk if p > 0)
print(f'\nW38 胜率 {pos}/{len(wk)}')

# ---------- 2. 赛道周度贡献 ----------
print('\n【赛道周度贡献】')
day_files = {d: os.path.join(HIST, 'portfolio_close_' + d.replace('-', '') + '.json') for d, _, _ in wk}
track_week = defaultdict(lambda: defaultdict(float))
track_mv_end = {}
for d, _, _ in wk:
    fp = day_files[d]
    if d == '2026-09-18':
        dd = fix
    else:
        dd = json.load(open(fp, encoding='utf-8'))
    for k, v in dd['tracks'].items():
        track_week[k][d] = v['pnl']
    if d == wk[-1][0]:
        track_mv_end = {k: v for k, v in dd['tracks'].items()}
for k in sorted(track_week, key=lambda x: -abs(sum(track_week[x].values()))):
    tot = sum(track_week[k].values())
    daily = ' / '.join(f"{d[5:]} {track_week[k][d]:+,.0f}" for d, _, _ in wk)
    pct = track_mv_end.get(k, {}).get('pct_of_total', 0)
    print(f'  {k:10s} 周贡献 {tot:>+10,.2f} 元 | 期末占比 {pct:>5.2f}% | {daily}')

print('\n【赛道期末占比（9/18 修正后）】')
for k, v in sorted(track_mv_end.items(), key=lambda kv: -kv[1]['pct_of_total']):
    print(f"  {k:10s} {v['pct_of_total']:>6.2f}%  mv={v['mv']:>11,.2f}  day={v['day_pct']:+.3f}%")

# ---------- 3. 指数窗口统计 ----------
rows = list(csv.reader(open(os.path.join(HIST, 'indices.csv'), encoding='utf-8-sig')))[1:]
by = defaultdict(list); usby = defaultdict(list)
for r in rows:
    if len(r) < 6 or not r[4] or r[5] in ('', None):
        continue
    try:
        if r[0] == 'index':
            by[r[3]].append((r[1], float(r[4])))
        elif r[0] == 'us_index':
            usby[r[3]].append((r[1], float(r[4])))
    except Exception:
        pass

print('\n【指数窗口（截至 9/18 收盘）】')


def win(v, label):
    v = sorted({d: c for d, c in v}.items())
    if len(v) >= 11:
        last = v[-1][1]
        print(f'  {label:12s} 末值 {last:>10.2f} ({v[-1][0]})  1日 {(last / v[-2][1] - 1) * 100:+.2f}%  '
              f'3日 {(last / v[-4][1] - 1) * 100:+.2f}%  5日 {(last / v[-6][1] - 1) * 100:+.2f}%  '
              f'10日 {(last / v[-11][1] - 1) * 100:+.2f}%')
    else:
        print(f'  {label:12s} 样本不足 n={len(v)}')


for code, name in [('000001', '上证指数'), ('399006', '创业板指'), ('000300', '沪深300'),
                   ('000932', '中证消费'), ('000933', '中证医药'), ('399989', '中证医疗'),
                   ('399997', '中证白酒'), ('HSTECH', '恒生科技'), ('HSI', '恒生指数')]:
    if code in by:
        win(by[code], name)
for code in ['XLV', 'IYH', 'QQQ', 'DIA', 'SPY', '.IXIC', '.DJI', '.INX']:
    if code in usby:
        win(usby[code], code)

# ---------- 4. W38 周内指数区间 ----------
print('\n【W38 周内指数变化（9/11 → 9/18）】')
for code, name in [('000001', '上证指数'), ('399006', '创业板指'), ('000932', '中证消费'),
                   ('000933', '中证医药'), ('399989', '中证医疗'), ('HSTECH', '恒生科技'),
                   ('HSI', '恒生指数')]:
    v = sorted({d: c for d, c in by.get(code, [])}.items())
    a = [x for x in v if x[0] <= '2026-09-11']
    b = [x for x in v if x[0] <= W_END]
    if a and b:
        print(f'  {name:10s} {a[-1][1]:>10.2f} ({a[-1][0]}) → {b[-1][1]:>10.2f} ({b[-1][0]})  '
              f'{(b[-1][1] / a[-1][1] - 1) * 100:+.2f}%')
for code in ['XLV', 'IYH', 'QQQ', 'DIA', 'SPY']:
    v = sorted({d: c for d, c in usby.get(code, [])}.items())
    a = [x for x in v if x[0] <= '2026-09-11']
    b = [x for x in v if x[0] <= '2026-09-18']
    if a and b:
        print(f'  {code:10s} {a[-1][1]:>10.2f} ({a[-1][0]}) → {b[-1][1]:>10.2f} ({b[-1][0]})  '
              f'{(b[-1][1] / a[-1][1] - 1) * 100:+.2f}%')
