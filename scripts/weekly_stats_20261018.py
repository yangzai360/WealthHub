# -*- coding: utf-8 -*-
"""2026-10-18 周日·纯非交易日档：链路/风险指标重算 + W42 周度统计
背景：10/18 完成 `portfolio_close_20261016_fix.json`（4 行净值到位，当日损益
      -509.68 元 → -107.81 元）→ **末行估值变化，链路/夏普/回撤/W42 必须重算**（§3.107 / §3.127e）

守卫：
  ① Σ 赛道周盈亏 == 首尾市值差（< 1.5 元）
  ② W42 几何链式 == 首尾直算（< 0.01pct）
  ③ |Σ tracks.mv − total_mv| < 1.5（末行）
输出：risk_stats_close_20261018.json + weekly_stats_20261018.json
"""
import json, os, glob, re
import statistics as st

BASE = '/Users/jieyang/Documents/WealthHub'
HIST = os.path.join(BASE, 'data/processed/history')
TODAY = '2026-10-18'
RF = 1.68


def pct_of(d):
    raw = d.get('est_total_pct_raw')
    if raw is not None:
        return float(raw)
    p = d.get('est_total_pct')
    return float(p) if p is not None else None


seen = {}
for p in glob.glob(os.path.join(HIST, 'portfolio_close_*.json')):
    m = re.search(r'(\d{8})', os.path.basename(p))
    if not m:
        continue
    ds = m.group(1)
    date = f'{ds[:4]}-{ds[4:6]}-{ds[6:]}'
    d = json.load(open(p, encoding='utf-8'))
    pct = pct_of(d)
    if pct is None:
        continue
    isfix = '_fix' in os.path.basename(p)
    if date not in seen or (isfix and not seen[date][1]):
        seen[date] = (pct, isfix, d.get('total_mv'), d.get('med_pct'), os.path.basename(p))

rows = sorted((d, v[0], v[2], v[3], v[4]) for d, v in seen.items())
if rows and rows[0][0] > '2026-08-06':
    rows.insert(0, ('2026-08-06', -0.68, 392555.65, None, 'manual-seed'))

print('日期        日收益%   总资产              来源')
for d, pct, mv, med, src in rows[-8:]:
    mark = '★' if '_fix' in str(src) else ' '
    print(f'{mark} {d}  {pct:>7.4f}  {(mv if mv else 0):>12,.2f}   {src}')

cum = 1.0
for d, pct, *_ in rows:
    cum *= (1 + pct / 100)
print(f'\n链路累计（{rows[0][0]} 起 {len(rows)} 个交易日）: {(cum-1)*100:.2f}%')

def week(lo, hi):
    k = [(d, p) for d, p, *_ in rows if lo <= d <= hi]
    v = 1.0
    for _, p in k:
        v *= (1 + p / 100)
    return v, k

w41, w41k = week('2026-10-05', '2026-10-11')
w42, w42k = week('2026-10-12', '2026-10-18')
print(f'W41（10/5-10/11，{len(w41k)} 日，已收官）: {(w41-1)*100:.2f}%  ' + ' / '.join(f'{d[5:]} {p:+.4f}%' for d, p in w41k))
print(f'W42（10/12-10/18，{len(w42k)} 日）: {(w42-1)*100:.2f}%  ' + ' / '.join(f'{d[5:]} {p:+.4f}%' for d, p in w42k))
assert len(w42k) == 5, f'W42 行数异常：{w42k}'

rets = [p for _, p, *_ in rows]
n = len(rets); mean = st.mean(rets); sd = st.stdev(rets) if n > 1 else 0
rf_daily = RF / 252
sharpe = (mean - rf_daily) / sd * (252 ** 0.5) if sd else None
print(f'\n夏普 {sharpe:.2f}（n={n}, 均值 {mean:.4f}%, 标准差 {sd:.4f}%, rf={RF}%）')

nav = peak = 1.0; mdd = 0.0
peak_d = rows[0][0]; mdd_peak_d = mdd_trough_d = None
for d, pct, *_ in rows:
    nav *= (1 + pct / 100)
    if nav > peak:
        peak = nav; peak_d = d
    if nav / peak - 1 < mdd:
        mdd = nav / peak - 1; mdd_peak_d, mdd_trough_d = peak_d, d
print(f'最大回撤 {mdd*100:.2f}%（峰值 {mdd_peak_d} → 谷值 {mdd_trough_d}）')

cum5 = cum10 = 1.0
for _, p, *_ in rows[-5:]:
    cum5 *= (1 + p / 100)
for _, p, *_ in rows[-10:]:
    cum10 *= (1 + p / 100)
print(f'近 5 日 {(cum5-1)*100:.2f}%  近 10 日 {(cum10-1)*100:.2f}%')

# ---------- W42 周度：赛道归因（_fix 优先） ----------
DAYS = ['20261012', '20261013', '20261014', '20261015', '20261016']
files = {}
for ds in DAYS:
    fp = os.path.join(HIST, f'portfolio_close_{ds}_fix.json')
    if not os.path.exists(fp):
        fp = os.path.join(HIST, f'portfolio_close_{ds}.json')
    files[ds] = json.load(open(fp, encoding='utf-8'))
    print(f'  {ds} ← {os.path.basename(fp)}')

base_total = round(float(files['20261012']['base_total']), 2)   # = 10/9 修正件 total_mv
end_total = round(float(files['20261016']['total_mv']), 2)
print(f'\nW42 基准 {base_total:,.2f} 元（10/9 收盘修正件）→ 期末 {end_total:,.2f} 元')

track_daily = {}
for ds in DAYS:
    d = f'{ds[:4]}-{ds[4:6]}-{ds[6:]}'
    for t, v in files[ds]['tracks'].items():
        track_daily.setdefault(t, {})[d] = round(float(v['pnl']), 2)
track_week = {t: round(sum(v.values()), 2) for t, v in track_daily.items()}
sum_week = round(sum(track_week.values()), 2)
first_last = round(end_total - base_total, 2)
assert abs(sum_week - first_last) < 1.5, f'守卫失败：Σ赛道 {sum_week} vs 首尾 {first_last}'

wk_pct = round((end_total / base_total - 1) * 100, 4)
chain_wk = round((w42 - 1) * 100, 4)
assert abs(wk_pct - chain_wk) < 0.01, f'链式 {chain_wk} vs 直算 {wk_pct}'

end_tracks = files['20261016']['tracks']
sum_mv = round(sum(float(v['mv']) for v in end_tracks.values()), 2)
assert abs(sum_mv - end_total) < 1.5, f'末行 Σmv 守卫失败 {sum_mv} vs {end_total}'

print(f'\nW42 周收益 {wk_pct:+.4f}%（{first_last:+,.2f} 元）；链式 {chain_wk:+.4f}%')
print('赛道周盈亏：')
for t, v in sorted(track_week.items(), key=lambda x: -x[1]):
    print(f'  {t:12s} {v:>+10,.2f} 元  期末权重 {float(end_tracks[t]["mv"])/end_total*100:5.2f}%')

risk = {
    'date': TODAY, 'chain_cum_pct': round((cum - 1) * 100, 2), 'chain_days': len(rows),
    'chain_0pct_row_inserted': False,
    'chain_gap_note': ('10/1-10/7 长假「混合档」产物为 portfolio_pending_*（不匹配 portfolio_close_* glob）→ 无 0% 行；'
                       '**10/18 已生成 portfolio_close_20261016_fix.json（4 行净值到位）→ 末行估值由 369,750.74 元 '
                       '修订为 370,152.61 元，本档按 §3.107 / §3.127e 全量重算链路/夏普/回撤（非沿用 10/16 旧值）**'),
    'w41_cum_pct': round((w41 - 1) * 100, 2), 'w41_days': len(w41k),
    'w42_cum_pct': round((w42 - 1) * 100, 2), 'w42_days': len(w42k),
    'w42_daily': [f'{d[5:]} {p:+.4f}%' for d, p in w42k],
    'sharpe': round(sharpe, 2), 'sharpe_n': n,
    'daily_mean': round(mean, 4), 'daily_sd': round(sd, 4),
    'max_dd_pct': round(mdd * 100, 2), 'max_dd_peak': mdd_peak_d, 'max_dd_trough': mdd_trough_d,
    'last5_cum_pct': round((cum5 - 1) * 100, 2), 'last10_cum_pct': round((cum10 - 1) * 100, 2),
    'rf_pct': RF,
    'rf_note': '中国 10Y 国债硬编码 1.68%（本地 10Y 序列自 2026-08-11 后未维护，缺口待补）',
    'tracks_end': {k: {'mv': round(float(v['mv']), 2),
                       'pct_of_total': round(float(v['mv']) / end_total * 100, 2)}
                   for k, v in end_tracks.items()},
    'med_pct_end': round((float(end_tracks['A股医药']['mv']) + float(end_tracks['美股标普医药']['mv'])) / end_total * 100, 2),
    'total_mv_end': end_total,
    'fix_applied': [v[4] for _, _, _, _, v in rows if '_fix' in str(v[4])],
    'recompute_note': '本档为**纯非交易日**，但 10/16 末行已 _fix 修订 → 风险指标全量重算（§3.127e 口径一致原则）。',
    'override_rule': '显式优先级（_fix 优先）+ `est_total_pct_raw is not None` 显式判空（§3.98/§3.102）',
}
json.dump(risk, open(os.path.join(HIST, f'risk_stats_close_{TODAY.replace("-", "")}.json'), 'w',
                     encoding='utf-8'), ensure_ascii=False, indent=1)

wk = {
    'date': TODAY, 'week': '2026-W42', 'week_range': '2026-10-12 ~ 2026-10-18',
    'base_total': base_total, 'base_date': '2026-10-09', 'end_total': end_total, 'end_date': '2026-10-16',
    'w42': {'cum_pct': wk_pct, 'chain_cum_pct': chain_wk, 'days': 5,
            'daily': [f'{d[5:]} {p:+.4f}%' for d, p in w42k],
            'pnl': first_last, 'negative_days': sum(1 for _, p in w42k if p < 0),
            'note': '5 个定价日（10/12-10/16 全周）；10/17-10/18 周末无定价，不计入；10/16 取 _fix 修正件'},
    'track_week_pnl': track_week, 'track_week_daily': track_daily,
    'track_end_weights': {k: round(float(v['mv']) / end_total * 100, 2) for k, v in end_tracks.items()},
    'risk': {k: risk[k] for k in ('chain_cum_pct', 'chain_days', 'sharpe', 'sharpe_n', 'daily_mean',
                                  'daily_sd', 'max_dd_pct', 'max_dd_peak', 'max_dd_trough',
                                  'last5_cum_pct', 'last10_cum_pct', 'rf_pct', 'med_pct_end')},
    'guards': {'sigma_track_week': sum_week, 'first_last': first_last,
               'dev': round(sum_week - first_last, 2), 'chain_dev': round(chain_wk - wk_pct, 4)},
    'note': 'W42 = 10/12-10/18（5 个定价日）；赛道周盈亏求和与首尾市值差通过 <1.5 元守卫',
}
json.dump(wk, open(os.path.join(HIST, f'weekly_stats_{TODAY.replace("-", "")}.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
print(f'\n✅ risk_stats_close_20261018.json / weekly_stats_20261018.json 已写入')
print('守卫：Σ赛道周盈亏 %.2f vs 首尾 %.2f（dev %.2f）；链式 dev %.4f'
      % (sum_week, first_last, sum_week - first_last, chain_wk - wk_pct))
