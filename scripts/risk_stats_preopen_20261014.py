# -*- coding: utf-8 -*-
"""2026-10-14 周三盘前档（**档型③「正常交易日盘前」**：A股 + 港股 + 美股 均为正常交易日）:
链路累计 / W39 / W40 / W41（已收官）/ W42 / 夏普 / 最大回撤
⚠️ §3.121c：档型写成顶部常量 SESSION_TYPE，docstring 与产物 note 统一引用，消除语义复发
⚠️ 10/2、10/5、10/6、10/7「混合档」产物为 `portfolio_pending_*.json`（刻意避开 `portfolio_close_*` glob）
   → 不污染链式序列；10/1、10/3-10/4 无 portfolio 产物（A股休市 / 周末）→ 链式序列跳过，正确
⚠️ **10/13 为正常交易日 → `portfolio_close_20261013.json` / `_fix` 已计入链式序列**（末行由 10/12 推进至 10/13，+1 日；
   10/13 单日取 **`_fix` 件修正后 −0.6691% / −2,521.74 元**（§3.140a 跨档补正 −358.50 元）；原值 −0.5739% 已弃用）
⚠️ 本档不产 `portfolio_close_20261014.json`（档型③）→ **链式序列末行 = 2026-10-13**、
   W41（10/5-10/11）= 2 日（10/8 −1.6860% / 10/9 +0.6875%；已收官）、W42（10/12-10/18）= 2 日
   （10/12 −0.0344% / 10/13 −0.6691%）
⚠️ §3.125a：周窗口区间串须逐档核对 —— W39/W40/W41 保留（W41 已收官）、当周 W42 = 2 日（10/12、10/13）
⚠️ §3.98 条款 7 / §3.107 条款 26：同日期以 `_fix` 为准 —— 显式优先级判断（禁止依赖 glob/sorted 顺序）
"""
import json, os, glob, re
import statistics as st

BASE = '/Users/jieyang/Documents/WealthHub'
HIST = os.path.join(BASE, 'data/processed/history')
TODAY = '2026-10-14'
SESSION_TYPE = 'normal_trading_day_preopen'
SESSION_NOTE = ('档型③「正常交易日盘前」= A股 10/14 正常交易日 + 港股 10/14 正常交易日 + 美股 10/14 正常交易日（开盘前）；'
                '08:00 A股/港股均无当日价格 → **不产 `portfolio_close_*` 与 `portfolio_pending_*`**')
RF = 1.68


def pct_of(d):
    raw = d.get('est_total_pct_raw')
    if raw is not None:
        return float(raw)
    p = d.get('est_total_pct')
    return float(p) if p is not None else None


seen = {}
skipped = []
for p in glob.glob(os.path.join(HIST, 'portfolio_close_*.json')):
    m = re.search(r'(\d{8})', os.path.basename(p))
    if not m:
        continue
    ds = m.group(1)
    date = f'{ds[:4]}-{ds[4:6]}-{ds[6:]}'
    d = json.load(open(p, encoding='utf-8'))
    pct = pct_of(d)
    if pct is None:
        skipped.append(os.path.basename(p)); continue
    isfix = '_fix' in os.path.basename(p)
    if date not in seen or (isfix and not seen[date][1]):
        seen[date] = (pct, isfix, d.get('total_mv'), d.get('med_pct'), os.path.basename(p))

rows = sorted((d, v[0], v[2], v[3], v[4]) for d, v in seen.items())
if rows and rows[0][0] > '2026-08-06':
    rows.insert(0, ('2026-08-06', -0.68, 392555.65, None, 'manual-seed'))

print('日期        日收益%   总资产              来源')
for d, pct, mv, med, src in rows:
    mark = '★' if '_fix' in str(src) else ' '
    print(f'{mark} {d}  {pct:>7.4f}  {(mv if mv else 0):>12,.2f}   {src}')
print('跳过（pct 全缺失）:', skipped)
print(f'⚠️ 链式序列末行 = {rows[-1][0]}（**本档无新增定价行**，档型③不产 close；10/13 收盘行（`_fix` 修正值）已计入）')

cum = 1.0
for d, pct, *_ in rows:
    cum *= (1 + pct / 100)
print(f'\n链路累计（{rows[0][0]} 起 {len(rows)} 个交易日）: {(cum-1)*100:.2f}%')

w39 = 1.0
w39k = [(d, p) for d, p, *_ in rows if '2026-09-21' <= d <= '2026-09-27']
for d, p in w39k:
    w39 *= (1 + p / 100)
print(f'W39（9/21-9/27，{len(w39k)} 日）累计: {(w39-1)*100:.2f}%  ' + ' / '.join(f'{d[5:]} {p:+.4f}%' for d, p in w39k))

w40 = 1.0
w40k = [(d, p) for d, p, *_ in rows if '2026-09-28' <= d <= '2026-10-04']
for d, p in w40k:
    w40 *= (1 + p / 100)
print(f'W40（9/28-10/4，{len(w40k)} 日）累计: {(w40-1)*100:.2f}%  ' + ' / '.join(f'{d[5:]} {p:+.4f}%' for d, p in w40k))

w41 = 1.0
w41k = [(d, p) for d, p, *_ in rows if '2026-10-05' <= d <= '2026-10-11']
for d, p in w41k:
    w41 *= (1 + p / 100)
print(f'W41（10/5-10/11，{len(w41k)} 日）累计: {(w41-1)*100:.2f}%  ' +
      (' / '.join(f'{d[5:]} {p:+.4f}%' for d, p in w41k) if w41k else '（本档尚无已实现交易日 → 结构上为 0 日）'))

w42 = 1.0
w42k = [(d, p) for d, p, *_ in rows if '2026-10-12' <= d <= '2026-10-18']
for d, p in w42k:
    w42 *= (1 + p / 100)
print(f'W42（10/12-10/18，{len(w42k)} 日）累计: {(w42-1)*100:.2f}%  ' +
      (' / '.join(f'{d[5:]} {p:+.4f}%' for d, p in w42k) if w42k else '（本档尚无已实现交易日 → 结构上为 0 日）'))

rets = [p for _, p, *_ in rows]
n = len(rets); mean = st.mean(rets); sd = st.stdev(rets) if n > 1 else 0
rf_daily = RF / 252
sharpe = (mean - rf_daily) / sd * (252 ** 0.5) if sd else None
print(f'\n夏普比率: {sharpe:.2f}（{n} 个交易日样本, 日收益均值 {mean:.4f}%, 日标准差 {sd:.4f}%, rf={RF}%）')

nav = peak = 1.0; mdd = 0.0
peak_d = rows[0][0]; mdd_peak_d = mdd_trough_d = None
for d, pct, *_ in rows:
    nav *= (1 + pct / 100)
    if nav > peak:
        peak = nav; peak_d = d
    if nav / peak - 1 < mdd:
        mdd = nav / peak - 1; mdd_peak_d, mdd_trough_d = peak_d, d
print(f'最大回撤: {mdd*100:.2f}%（峰值 {mdd_peak_d} → 谷值 {mdd_trough_d}）')

cum5 = cum10 = 1.0
for _, p, *_ in rows[-5:]:
    cum5 *= (1 + p / 100)
for _, p, *_ in rows[-10:]:
    cum10 *= (1 + p / 100)
print(f'近 5 个交易日累计: {(cum5-1)*100:.2f}%')
print(f'近 10 个交易日累计: {(cum10-1)*100:.2f}%')

# 期末赛道结构（取链路末行 = 2026-10-13 收盘**修正件**口径，§3.95 末行优先 / §3.140a 跨档补正）
fix = json.load(open(os.path.join(HIST, 'portfolio_close_20261013_fix.json'), encoding='utf-8'))
tracks = {k: {'mv': round(v['mv'], 2),
                  'pct_of_total': round(100.0 * v['mv'] / fix['total_mv'], 2)} for k, v in fix['tracks'].items()}
# ⚠️ §3.144c：`_fix` 件内 `tracks[].pct_of_total` 为**修正前分母**（374,747.97 元）派生值、与 mv 不自洽
#   （例：A股医药 22.78% vs mv/total = 22.70%）→ 权重一律**现算**，并记入 stale_weight_fields。
stale_pct = {k: v['pct_of_total'] for k, v in fix['tracks'].items()
             if abs(v['pct_of_total'] - round(100.0 * v['mv'] / fix['total_mv'], 2)) > 0.01}
assert abs(sum(v['mv'] for v in fix['tracks'].values()) - fix['total_mv']) < 1.5, '§3.107 硬守卫失败'
med_pct = round(100.0 * (fix['tracks']['A股医药']['mv'] + fix['tracks']['美股标普医药']['mv'])
                 / fix['total_mv'], 2) if 'A股医药' in fix['tracks'] else None
print(f'\n期末赛道结构（2026-10-13 收盘**修正件**口径 = 链路末行，tracks.mv 求和 = {sum(v["mv"] for v in fix["tracks"].values()):,.2f} / total_mv = {fix["total_mv"]:,.2f}）')
for k, v in sorted(tracks.items(), key=lambda kv: -kv[1]['pct_of_total']):
    print(f"  {k:12s} {v['pct_of_total']:>6.2f}%  {v['mv']:>12,.2f}")
print(f'  医药总敞口 {med_pct:.2f}%')

out = {'date': TODAY, 'session': 'preopen', 'session_type': SESSION_TYPE,
       'session_type_note': SESSION_NOTE,
       'chain_cum_pct': round((cum-1)*100, 2), 'chain_days': len(rows),
       'chain_last_row_date': rows[-1][0],
       'chain_0pct_row_inserted': False,
       'w39_cum_pct': round((w39-1)*100, 2), 'w39_days': len(w39k),
       'w40_cum_pct': round((w40-1)*100, 2), 'w40_days': len(w40k),
       'w41_cum_pct': round((w41-1)*100, 2), 'w41_days': len(w41k),
       'w41_note': 'W41（10/5-10/11）已收官：2 个已实现交易日（10/8 −1.6860% / 10/9 +0.6875%，§3.127e 取 `_fix` 修正值）',
       'w42_cum_pct': round((w42-1)*100, 2), 'w42_days': len(w42k),
       'w42_note': '本档 W42（10/12-10/18）已有 2 个已实现交易日（10/12 −0.0344% / −129.64 元、10/13 −0.6691% / −2,521.74 元，取 `_fix` 修正值）',
       'sharpe': round(sharpe, 2) if sharpe else None,
       'sharpe_n': n, 'daily_mean': round(mean, 4), 'daily_sd': round(sd, 4),
       'max_dd_pct': round(mdd*100, 2), 'max_dd_peak': mdd_peak_d, 'max_dd_trough': mdd_trough_d,
       'last5_cum_pct': round((cum5-1)*100, 2), 'last10_cum_pct': round((cum10-1)*100, 2),
       'rf_pct': RF, 'rf_note': '中国 10Y 国债硬编码 1.68%（本地 10Y 序列自 2026-08-11 后未维护，缺口待补）',
       'tracks_end': tracks, 'med_pct_end': med_pct,
       'stale_weight_fields_in_fix': stale_pct,
       'weight_rule': ('赛道权重一律由 mv / total_mv 现算；`_fix` 件内 `pct_of_total` 为修正前分母派生值、'
                       '不得引用（§3.144c：同一指标不作两个字面量）'),
       'fix_applied': [s for _, _, _, _, s in rows if '_fix' in str(s)],
       'override_rule': '显式优先级（_fix 优先）+ `est_total_pct_raw is not None` 显式判空（§3.98/§3.102）',
       'note': (f'{SESSION_NOTE}；本档不产 `portfolio_close_*` → 链式序列末行 = {rows[-1][0]}'
                f'（10/13 收盘行（`_fix` 修正值）已计入，−0.6691% / −2,521.74 元）；'
                '10/2、10/5、10/6、10/7「混合档」产物为 portfolio_pending_*.json 不参与链式序列；'
                '10/1、10/3-10/4、10/10-10/11 均无 close 产物 → W41（10/5-10/11）收盘 2 日、W42（10/12-10/18）2 日')}
json.dump(out, open(os.path.join(HIST, 'risk_stats_' + TODAY.replace('-', '') + '_preopen' + '.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
print(f'\n已保存 risk_stats_{TODAY.replace("-", "")}_preopen.json')
print('生效的 _fix 文件:', out['fix_applied'])
print('末 3 日日收益:', [f'{d[5:]} {p:+.4f}%' for d, p, *_ in rows[-3:]])
