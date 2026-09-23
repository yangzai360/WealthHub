# -*- coding: utf-8 -*-
"""2026-09-22 盘后: 链路累计/W39起累计/夏普比率/最大回撤（几何链式，§3.55/§3.91/§3.95/§3.98 口径）
同日期以 `_fix` 为准 —— 使用显式优先级判断（禁止依赖 glob/sorted 顺序，§3.98）
"""
import json, os, glob, re
import statistics as st

BASE = '/Users/jieyang/Documents/WealthHub'
HIST = os.path.join(BASE, 'data/processed/history')
TODAY = '2026-09-22'

seen = {}
for p in glob.glob(os.path.join(HIST, 'portfolio_close_*.json')):
    m = re.search(r'(\d{8})', os.path.basename(p))
    if not m:
        continue
    ds = m.group(1)
    date = f'{ds[:4]}-{ds[4:6]}-{ds[6:]}'
    d = json.load(open(p, encoding='utf-8'))
    pct = d.get('est_total_pct_raw', d.get('est_total_pct'))
    if pct is None:
        continue
    isfix = '_fix' in os.path.basename(p)
    if date not in seen or (isfix and not seen[date][1]):
        seen[date] = (float(pct), isfix, d.get('total_mv'), d.get('med_pct'),
                      os.path.basename(p))

rows = sorted((d, v[0], v[2], v[3], v[4]) for d, v in seen.items())
if rows and rows[0][0] > '2026-08-06':
    rows.insert(0, ('2026-08-06', -0.68, 392555.65, None, 'manual-seed'))

print('日期        日收益%   总资产              来源')
for d, pct, mv, med, src in rows:
    mark = '★' if '_fix' in str(src) else ' '
    print(f'{mark} {d}  {pct:>7.4f}  {(mv if mv else 0):>12,.2f}   {src}')

cum = 1.0
for d, pct, *_ in rows:
    cum *= (1 + pct / 100)
print(f'\n链路累计（{rows[0][0]} 起 {len(rows)} 个交易日）: {(cum-1)*100:.2f}%')

w = 1.0
wk = [(d, p) for d, p, *_ in rows if '2026-09-14' <= d <= '2026-09-18']
for d, p in wk:
    w *= (1 + p / 100)
print(f'W38（9/14-9/18，{len(wk)} 日）累计: {(w-1)*100:.2f}%')

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
       'fix_applied': [s for _, _, _, _, s in rows if '_fix' in str(s)],
       'override_rule': '显式优先级（_fix 优先），未依赖 glob/sorted 顺序（§3.98）'}
json.dump(out, open(os.path.join(HIST, 'risk_stats_' + TODAY.replace('-', '') + '_close.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
print('\n已保存 risk_stats_' + TODAY.replace('-', '') + '_close.json')
print('生效的 _fix 文件:', out['fix_applied'])
print(f'\n连续性抽查：盘前档 chain=-2.69% / 33 日 → 本档 {out["chain_cum_pct"]:.2f}% / {out["chain_days"]} 日，'
      f'差分 {out["chain_cum_pct"]-(-2.69):+.2f}pct（应≈当日日收益 {rets[-1]:+.2f}%）')
print('末 3 日日收益:', [f'{d[5:]} {p:+.4f}%' for d, p, *_ in rows[-3:]])
