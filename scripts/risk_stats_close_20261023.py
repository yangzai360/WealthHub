# -*- coding: utf-8 -*-
"""2026-10-23 周五盘后档（正常交易日收盘 · A股 15:00 收盘 + 港股 16:00 收盘）: 链路累计/W43累计/夏普/最大回撤
⚠️ 10/1-10/7 长假内「混合档」产物为 `portfolio_pending_*`（刻意避开 `portfolio_close_*` glob）
   → 不向链式序列插入 0% 行（§3.108 条款 22）
⚠️ 10/23 为正常交易日（A股 + 港股 同开同收）→ 计入链式序列；W43 窗口（10/19-10/25）本档为第 5 个交易日
同日期以 `_fix` 为准 —— 显式优先级判断（禁止依赖 glob/sorted 顺序，§3.98）
⚠️ 周窗口（§3.125a）：10/16 属 W42（10/12-10/18）已收官；W43（10/19-10/25）本档第 4 日（10/19/10/20/10/21/10/23）
"""
import json, os, glob, re
import statistics as st

BASE = '/Users/jieyang/Documents/WealthHub'
HIST = os.path.join(BASE, 'data/processed/history')
TODAY = '2026-10-23'
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
print(f'W41（10/5-10/11，{len(w41k)} 日，已收官）累计: {(w41-1)*100:.2f}%  ' + ' / '.join(f'{d[5:]} {p:+.4f}%' for d, p in w41k))

w42 = 1.0
w42k = [(d, p) for d, p, *_ in rows if '2026-10-12' <= d <= '2026-10-18']  # W42 窗口起点固定为周一 10/12（§3.125a）
for d, p in w42k:
    w42 *= (1 + p / 100)
print(f'W42（10/12-10/18，{len(w42k)} 日，已收官）累计: {(w42-1)*100:.2f}%  ' + ' / '.join(f'{d[5:]} {p:+.4f}%' for d, p in w42k))
assert len(w42k) == 5, f'W42 行数异常：{w42k}'

w43 = 1.0
w43k = [(d, p) for d, p, *_ in rows if '2026-10-19' <= d <= '2026-10-25']
for d, p in w43k:
    w43 *= (1 + p / 100)
print(f'W43（10/19-10/25，{len(w43k)} 日）累计: {(w43-1)*100:.2f}%  ' + ' / '.join(f'{d[5:]} {p:+.4f}%' for d, p in w43k))
assert len(w43k) == 5, f'W43 行数异常（应为 10/19-10/23 五个交易日）：{w43k}'

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

# 期末赛道结构（取链路末行 = 10/23 收盘口径）
fix = json.load(open(os.path.join(HIST, 'portfolio_close_20261023.json'), encoding='utf-8'))
tracks = {k: {'mv': round(v['mv'], 2), 'pct_of_total': round(v['mv'] / float(fix['total_mv']) * 100, 2)}
          for k, v in fix['tracks'].items()}
assert abs(sum(v['mv'] for v in fix['tracks'].values()) - fix['total_mv']) < 1.5, '§3.107 硬守卫失败'
# §3.146a ②：med_pct 一律由 mv 求和现算，禁止引用（可能陈旧的）pct_of_total
med_mv = round(fix['tracks']['A股医药']['mv'] + fix['tracks']['美股标普医药']['mv'], 2)
med_pct = round(med_mv / float(fix['total_mv']) * 100, 2)
med_pct_field_check = round(fix['med_pct'], 2)
assert abs(med_pct - med_pct_field_check) < 0.05, f'med_pct 现算 {med_pct} vs 产物字段 {med_pct_field_check} 不一致'
print(f'\n期末赛道结构（10/23 收盘口径，tracks.mv 求和 = {sum(v["mv"] for v in fix["tracks"].values()):,.2f} / total_mv = {fix["total_mv"]:,.2f}）')
for k, v in sorted(tracks.items(), key=lambda kv: -kv[1]['pct_of_total']):
    print(f"  {k:12s} {v['pct_of_total']:>6.2f}%  {v['mv']:>12,.2f}")
print(f'  医药总敞口 {med_pct:.2f}%')

out = {'date': TODAY, 'chain_cum_pct': round((cum-1)*100, 2), 'chain_days': len(rows),
       'chain_0pct_row_inserted': False,
       'chain_gap_note': ('10/1-10/7 长假「混合档」产物均为 portfolio_pending_*（不匹配 portfolio_close_* glob）'
                          '→ 链式序列无 0% 行插入；10/23 正常交易日以 portfolio_close_20261023.json 接续 '
                          '10/22 **修正件**末行（portfolio_close_20261022_fix.json = 365,851.37 元 / −1.5820%，§3.108：同日期以 _fix 为准）'),
       'w39_cum_pct': round((w39-1)*100, 2), 'w39_days': len(w39k),
       'w40_cum_pct': round((w40-1)*100, 2), 'w40_days': len(w40k),
       'w41_cum_pct': round((w41-1)*100, 2), 'w41_days': len(w41k),
       'w41_daily': [f'{d[5:]} {p:+.4f}%' for d, p in w41k],
       'w42_cum_pct': round((w42-1)*100, 2), 'w42_days': len(w42k),
       'w43_cum_pct': round((w43-1)*100, 2), 'w43_days': len(w43k),
       'w43_daily': [{'date': d, 'pct': p} for d, p in w43k],
       'w42_daily': [f'{d[5:]} {p:+.4f}%' for d, p in w42k],
       'sharpe': round(sharpe, 2) if sharpe else None,
       'sharpe_n': n, 'daily_mean': round(mean, 4), 'daily_sd': round(sd, 4),
       'max_dd_pct': round(mdd*100, 2), 'max_dd_peak': mdd_peak_d, 'max_dd_trough': mdd_trough_d,
       'last5_cum_pct': round((cum5-1)*100, 2), 'last10_cum_pct': round((cum10-1)*100, 2),
       'rf_pct': RF, 'rf_note': '中国 10Y 国债硬编码 1.68%（本地 10Y 序列自 2026-08-11 后未维护，缺口待补）',
       'tracks_end': tracks, 'med_pct_end': med_pct,
       'total_mv_end': fix['total_mv'],
       'fix_applied': [s for _, _, _, _, s in rows if '_fix' in str(s)],
       'override_rule': '显式优先级（_fix 优先）+ `est_total_pct_raw is not None` 显式判空（§3.98/§3.102）',
       'tracks_end_note': '赛道权重一律由 mv / total_mv 现算（§3.146a ①）；med_pct 亦由 mv 求和现算（§3.146a ②）',
       'note': ('正常交易日（A股 15:00 收盘 + 港股 16:00 收盘 + 美股 10/23 未开盘）；末行 = 2026-10-23；'
                '本档**4 只 6 行未定价**（000248 双账户 + 002708 双账户 + 000051 + 002742，名义 61,440.08 元 = 16.55%，'
                '最新净值日 10/22 == 基准净值日 → 计 0，属「基准已含」口径 §3.105，20:00 首抓未出库、待兜底复抓）；'
                '场外 23 只中 19 只出 10/23 真实净值；QDII 000369/016280 的 10/22 净值本档释放（US 10/22 段核销 +942.55 元）；'
                '164906 的 10/22 净值 −3.24% 计入恒生科技腿；'
                '⚠️ 10/22 末行取 _fix 修正件（portfolio_close_20261022_fix.json，−5,880.66 元 / −1.5820%），'
                '非原始 portfolio_close_20261022.json（§3.108：同日期以 _fix 为准）')}
json.dump(out, open(os.path.join(HIST, 'risk_stats_close_' + TODAY.replace('-', '') + '.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
print(f'\n已保存 risk_stats_close_{TODAY.replace("-", "")}.json')
print('生效的 _fix 文件:', out['fix_applied'])
print('末 3 日日收益:', [f'{d[5:]} {p:+.4f}%' for d, p, *_ in rows[-3:]])
