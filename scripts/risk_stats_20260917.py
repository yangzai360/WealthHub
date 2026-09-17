# -*- coding: utf-8 -*-
"""2026-09-17 盘后: 链路累计/W38周累计/夏普比率/最大回撤（date 缺失时从文件名推导 §3.55）
本次为 31 个交易日样本"""
import json, os, glob, re
import statistics as st

BASE = '/Users/jieyang/Documents/WealthHub'
HIST = os.path.join(BASE, 'data/processed/history')
TODAY = '2026-09-17'

rows = []
for p in sorted(glob.glob(os.path.join(HIST, 'portfolio_close_*.json'))):
    m = re.search(r'(\d{8})', os.path.basename(p))
    if not m:
        continue
    ds = m.group(1)
    date = f'{ds[:4]}-{ds[4:6]}-{ds[6:]}'
    d = json.load(open(p, encoding='utf-8'))
    pct = d.get('est_total_pct')
    if pct is None:
        continue
    rows.append((date, float(pct), d.get('total_mv') or d.get('total'), d.get('med_pct')))
rows.sort(key=lambda x: x[0])
if rows and rows[0][0] > '2026-08-06':
    rows.insert(0, ('2026-08-06', -0.68, 392555.65, None))

print('日期        日收益%   总资产')
for d, pct, mv, med in rows:
    print(f'  {d}  {pct:>7.2f}  {(mv if mv else 0):>12,.2f}')

cum = 1.0
for d, pct, mv, med in rows:
    cum *= (1 + pct / 100)
print(f'\n链路累计（{rows[0][0]} 起 {len(rows)} 个交易日）: {(cum-1)*100:.2f}%')

w = 1.0
wk = [(d, p) for d, p, _, _ in rows if d >= '2026-09-14']
for d, p in wk:
    w *= (1 + p / 100)
print(f'本周 W38（9/14 起 {len(wk)} 日）累计: {(w-1)*100:.2f}%  ' + ' / '.join(f'{d[5:]} {p:+.2f}%' for d, p in wk))

rets = [p for _, p, _, _ in rows]
n = len(rets); mean = st.mean(rets); sd = st.stdev(rets) if n > 1 else 0
rf_daily = 1.69 / 252
sharpe = (mean - rf_daily) / sd * (252 ** 0.5) if sd else None
print(f'\n夏普比率: {sharpe:.2f}（{n} 个交易日样本, 日收益均值 {mean:.4f}%, 日标准差 {sd:.4f}%, rf=1.69%）')

nav = peak = 1.0; mdd = 0.0
for d, pct, mv, med in rows:
    nav *= (1 + pct / 100)
    peak = max(peak, nav)
    mdd = min(mdd, nav / peak - 1)
print(f'最大回撤: {mdd*100:.2f}%')

cum5 = cum10 = 1.0
for _, p, _, _ in rows[-5:]:
    cum5 *= (1 + p / 100)
for _, p, _, _ in rows[-10:]:
    cum10 *= (1 + p / 100)
print(f'近 5 个交易日累计: {(cum5-1)*100:.2f}%')
print(f'近 10 个交易日累计: {(cum10-1)*100:.2f}%')

out = {'date': TODAY, 'chain_cum_pct': round((cum-1)*100, 2), 'chain_days': len(rows),
       'w38_cum_pct': round((w-1)*100, 2), 'w38_days': len(wk),
       'sharpe': round(sharpe, 2) if sharpe else None,
       'sharpe_n': n, 'daily_mean': round(mean, 4), 'daily_sd': round(sd, 4),
       'max_dd_pct': round(mdd*100, 2),
       'last5_cum_pct': round((cum5-1)*100, 2), 'last10_cum_pct': round((cum10-1)*100, 2)}
json.dump(out, open(os.path.join(HIST, 'risk_stats_' + TODAY.replace('-','') + '.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('\n已保存 risk_stats_' + TODAY.replace('-', '') + '.json')
