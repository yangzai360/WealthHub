# -*- coding: utf-8 -*-
"""2026-09-21 盘后: 链路累计/W39起累计/夏普比率/最大回撤（几何链式，§3.55/§3.91/§3.95 口径）
本次为 33 个交易日样本；9/18 采用净值补更修正值（portfolio_close_20260918_fix.json，同日期后写覆盖）
"""
import json, os, glob, re
import statistics as st

BASE = '/Users/jieyang/Documents/WealthHub'
HIST = os.path.join(BASE, 'data/processed/history')
TODAY = '2026-09-21'

vals = {}
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
    # 同日期后写覆盖（_fix 文件排序在后 → 生效），符合「修正优先」口径（§3.95）
    vals[date] = (float(pct), d.get('total_mv') or d.get('total'), d.get('med_pct'),
                  os.path.basename(p))
rows = sorted((d, v[0], v[1], v[2], v[3]) for d, v in vals.items())
if rows and rows[0][0] > '2026-08-06':
    rows.insert(0, ('2026-08-06', -0.68, 392555.65, None, 'manual-seed'))

print('日期        日收益%   总资产              来源')
for d, pct, mv, med, src in rows:
    print(f'  {d}  {pct:>7.2f}  {(mv if mv else 0):>12,.2f}   {src}')

cum = 1.0
for d, pct, *_ in rows:
    cum *= (1 + pct / 100)
print(f'\n链路累计（{rows[0][0]} 起 {len(rows)} 个交易日）: {(cum-1)*100:.2f}%')

w = 1.0
wk = [(d, p) for d, p, *_ in rows if d >= '2026-09-14' and d <= '2026-09-18']
for d, p in wk:
    w *= (1 + p / 100)
print(f'W38（9/14-9/18，{len(wk)} 日）累计: {(w-1)*100:.2f}%  ' + ' / '.join(f'{d[5:]} {p:+.2f}%' for d, p in wk))

w39 = 1.0
w39k = [(d, p) for d, p, *_ in rows if d >= '2026-09-21']
for d, p in w39k:
    w39 *= (1 + p / 100)
print(f'W39（9/21 起，{len(w39k)} 日）累计: {(w39-1)*100:.2f}%  ' + ' / '.join(f'{d[5:]} {p:+.2f}%' for d, p in w39k))

rets = [p for _, p, *_ in rows]
n = len(rets); mean = st.mean(rets); sd = st.stdev(rets) if n > 1 else 0
rf_daily = 1.68 / 252
sharpe = (mean - rf_daily) / sd * (252 ** 0.5) if sd else None
print(f'\n夏普比率: {sharpe:.2f}（{n} 个交易日样本, 日收益均值 {mean:.4f}%, 日标准差 {sd:.4f}%, rf=1.68%）')

nav = peak = 1.0; mdd = 0.0
for d, pct, *_ in rows:
    nav *= (1 + pct / 100)
    peak = max(peak, nav)
    mdd = min(mdd, nav / peak - 1)
print(f'最大回撤: {mdd*100:.2f}%')

cum5 = cum10 = 1.0
for _, p, *_ in rows[-5:]:
    cum5 *= (1 + p / 100)
for _, p, *_ in rows[-10:]:
    cum10 *= (1 + p / 100)
print(f'近 5 个交易日累计: {(cum5-1)*100:.2f}%')
print(f'近 10 个交易日累计: {(cum10-1)*100:.2f}%')

out = {'date': TODAY, 'chain_cum_pct': round((cum-1)*100, 2), 'chain_days': len(rows),
       'w38_cum_pct': round((w-1)*100, 2), 'w38_days': len(wk),
       'w39_cum_pct': round((w39-1)*100, 2), 'w39_days': len(w39k),
       'sharpe': round(sharpe, 2) if sharpe else None,
       'sharpe_n': n, 'daily_mean': round(mean, 4), 'daily_sd': round(sd, 4),
       'max_dd_pct': round(mdd*100, 2),
       'last5_cum_pct': round((cum5-1)*100, 2), 'last10_cum_pct': round((cum10-1)*100, 2),
       'fix_applied': 'portfolio_close_20260918_fix.json（9/18 净值补更修正值 +0.57%）'}
json.dump(out, open(os.path.join(HIST, 'risk_stats_' + TODAY.replace('-', '') + '_close.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
print('\n已保存 risk_stats_' + TODAY.replace('-', '') + '_close.json')
# 连续性抽查（§3.95）：与上一档 chain 对比
try:
    prev = json.load(open(os.path.join(HIST, 'risk_stats_20260921.json'), encoding='utf-8'))
    print(f"连续性抽查：上一档（盘前）chain={prev['chain_cum_pct']:.2f}% / {prev['chain_days']} 日 → 本档 {out['chain_cum_pct']:.2f}% / {out['chain_days']} 日，差分 {out['chain_cum_pct']-prev['chain_cum_pct']:+.2f}pct（应≈当日日收益 {rets[-1]:+.2f}%）")
except Exception as e:
    print('连续性抽查跳过:', e)
