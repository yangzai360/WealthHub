# -*- coding: utf-8 -*-
"""2026-10-23 盘前档：组合敞口 / 门槛方程 / 防线读现算 / 情景敏感度 / 风险指标
档型③「正常交易日盘前」：A股 10/23 正常交易日（08:00 未开盘）+ 港股 10/23 正常交易日（10/22 已复市并收盘）+ 美股 10/23 正常交易日
→ 08:00 A股/港股 均无当日价格 → `close` 与 `pending` 均不产，待消化沿用 10/22 收盘修正件
★本档唯一新增真实定价 = US 10/22 收盘（XLV 181.30 / +1.32%、IYH 76.22 / +1.33%，防御板块领涨）
产物：portfolio_preopen_20261023.json / risk_stats_20261023_preopen.json

硬守卫（§3.104 / §3.109 条款 26 / §3.112a / §3.146a）：
  ① |Σ tracks.mv − total_mv| < 1.5
  ② 逐券还原式机器判据：max|Σ_track(mv0_new+est_pnl) − tracks[track].mv| < 1.5
  ③ 赛道权重一律 mv/total_mv 现算，**禁止引用 _fix 件 pct_of_total**（§3.146a）
  ④ 防线读数由 indices.csv 现算，并与上档 fix['defense'] 同名 close 字段断言（容差 0.02，§3.146h）
  ⑤ 情景区间对「合计结果值」取 min/max（§3.116b / §3.123b）
  ⑥ **state 类字段禁止继承**，由「本档 dist_pct vs 上一档 dist_pct」现算（§3.149a）
"""
import json, os, csv, glob, math, re
from collections import defaultdict

BASE = '/Users/jieyang/Documents/WealthHub'
HIST = os.path.join(BASE, 'data/processed/history')
TODAY = '2026-10-23'
FIXNAME = 'portfolio_close_20261022_fix.json'
fx = json.load(open(os.path.join(HIST, FIXNAME), encoding='utf-8'))
base = json.load(open(os.path.join(HIST, 'portfolio_close_20261022.json'), encoding='utf-8'))

TOT = fx['total_mv']
smv = sum(v.get('mv') or 0 for v in fx['tracks'].values())
dev_mv = abs(smv - TOT)
print(f'基准 {FIXNAME}: total_mv={TOT:,.2f} Σtracks.mv={smv:,.2f} dev={dev_mv:.2f}')
if dev_mv >= 1.5:
    raise SystemExit('⚠️ Σ tracks.mv 硬守卫失败，终止')

# ---- ② 逐券还原式机器判据（§3.112a）----
cand = {}
for rule in ('mv0_new', 'mv0'):
    per = defaultdict(float)
    for r in fx['detail']:
        if r.get('track') == '现金':
            continue
        per[r['track']] += (r.get(rule) or 0) + (r.get('est_pnl') or 0)
    devs = {t: abs(per[t] - (fx['tracks'][t]['mv'] if t in fx['tracks'] else 0)) for t in per}
    cand[rule] = (max(devs.values()) if devs else 0, devs)
rule_used = min(cand, key=lambda k: cand[k][0])
print(f'还原式判据: mv0_new max_dev={cand["mv0_new"][0]:.2f} / mv0 max_dev={cand["mv0"][0]:.2f} → 采用 {rule_used}')
if cand[rule_used][0] >= 1.5:
    raise SystemExit('⚠️ 逐券还原式硬守卫失败，终止')

TOTAL_PNL = fx['est_total_pnl']
dev_pnl = abs(sum(v.get('pnl') or 0 for v in fx['tracks'].values()) - TOTAL_PNL)
print(f'Σtracks.pnl={sum(v.get("pnl") or 0 for v in fx["tracks"].values()):,.2f} vs est_total_pnl={TOTAL_PNL:,.2f} dev={dev_pnl:.2f}')
if dev_pnl >= 1.5:
    raise SystemExit('⚠️ Σ tracks.pnl 硬守卫失败，终止')

# ---- 敞口（现算，§3.146a）----
EXPO = {t: {'mv': v['mv'], 'pct': round(100 * v['mv'] / TOT, 4), 'pnl': v.get('pnl')}
        for t, v in fx['tracks'].items()}
print('\n赛道敞口（mv/total 现算）:')
for t, v in sorted(EXPO.items(), key=lambda x: -x[1]['pct']):
    print(f"  {t:8s} {v['mv']:>12,.2f} 元 = {v['pct']:.2f}%  日盈亏 {v['pnl']:+,.2f} 元")

non_cash = {t: v for t, v in EXPO.items() if t != '现金'}
w_sum = round(sum(v['pct'] for v in non_cash.values()), 4)
print(f'  非现金合计 {w_sum:.2f}% + 现金 {EXPO["现金"]["pct"]:.2f}% = {w_sum + EXPO["现金"]["pct"]:.2f}%')

# ---- 医药敞口与门槛方程（解方程，§3.108 条款 8）----
MED = EXPO['A股医药']['mv'] + EXPO['美股标普医药']['mv']
MED_PCT = round(100 * MED / TOT, 2)
CAP = 0.40
r_all = (CAP * TOT - MED) / ((1 - CAP) * MED)
A, M = EXPO['A股医药']['mv'], EXPO['美股标普医药']['mv']
r_ash = (CAP * TOT - A - M) / ((1 - CAP) * A)
print(f'\n医药敞口 {MED:,.2f} 元 = {MED_PCT:.2f}%（上限 40%，余量 {40-MED_PCT:.2f}pct）')
print(f'  门槛收益率：全部医药同涨 {r_all*100:.2f}% / 仅 A股医药 {r_ash*100:.2f}%')

# ---- ④ 防线读数现算 ----
idx = defaultdict(dict)
with open(os.path.join(HIST, 'indices.csv'), encoding='utf-8-sig') as fh:
    for row in csv.DictReader(fh):
        try:
            idx[row['code']][row['date']] = float(row['close'])
        except Exception:
            pass


def last2(code):
    ds = sorted(idx.get(code, {}))
    return (ds[-1], idx[code][ds[-1]], ds[-2], idx[code][ds[-2]]) if len(ds) >= 2 else (None, None, None, None)


hs_d, hs_v, hs_pd, hs_pv = last2('HSTECH')
zc_d, zc_v, zc_pd, zc_pv = last2('000932')
print(f'\n防线读数现算：HSTECH 末行 {hs_d} {hs_v}（前 {hs_pd} {hs_pv}）；000932 末行 {zc_d} {zc_v}')
assert abs(hs_v - fx['discipline']['defense']['hstech_4250']['close']) < 0.02, 'HSTECH 与上档 fix 不一致'
assert abs(zc_v - fx['discipline']['defense']['zz_consume_12100']['close']) < 0.02, '000932 与上档 fix 不一致'

LINE_HS = 4250.0
dist_hs = round((hs_v / LINE_HS - 1) * 100, 4)
prev_dist = fx['discipline']['defense']['hstech_4250']['gap_pct']
prev_state = fx['discipline']['defense']['hstech_4250']['state']
NEXT_LINE = 4000.0
dist_next = round((hs_v / NEXT_LINE - 1) * 100, 4)
LINE_ZC = 12100.0
dist_zc = round((zc_v / LINE_ZC - 1) * 100, 4)

# ★§3.149a：state 由公式现算，禁止继承
_delta = round(abs(dist_hs) - abs(prev_dist), 4)
if abs(_delta) < 0.005:
    hs_state = 'close_level_break_unchanged'
elif _delta > 0:
    hs_state = 'close_level_break_widened'
else:
    hs_state = 'close_level_break_narrowed'
print(f'  恒生科技 {hs_v} 距 4,250 = {dist_hs:+.4f}%（上档 {prev_dist:+.4f}%，Δ |破位| {_delta:+.4f}pct）'
      f' → state {prev_state} → {hs_state}')
print(f'  恒生科技 距 4,000 = {dist_next:+.4f}%')
print(f'  中证消费 {zc_v} 距 12,100 = {dist_zc:+.4f}%')

# ---- 港股三段法（无新定价 → 沿用，refreshed=false）----
hk = fx['hk_split']
hk_tot = sum(hk.values())
hk_pct = round(100 * hk_tot / TOT, 4)
track_hk_pct = EXPO['恒生科技']['pct']
print(f'\n港联系三段：纯恒科 {hk["pure"]:,.2f} 元 / 中概 {hk["concept"]:,.2f} 元 / 宽基恒生系 {hk["broad"]:,.2f} 元 '
      f'合计 {hk_tot:,.2f} 元 = {hk_pct:.2f}%')
print(f'  双层：赛道层 {track_hk_pct:.2f}% + 宽基层 {100*hk["broad"]/TOT:.2f}pct（只报赛道层低估 {100*hk["broad"]/TOT:.2f}pct）')
if abs(hk_tot - fx['hk_total']) >= 1.5:
    raise SystemExit('⚠️ 三段合计与前档 hk_total 不一致')

# ---- 情景敏感度：赛道腿 β ----
def load_series():
    seen = {}
    for p in glob.glob(os.path.join(HIST, 'portfolio_close_*.json')):
        m = re.search(r'(\d{8})', os.path.basename(p))
        if not m:
            continue
        ds = m.group(1)
        date = f'{ds[:4]}-{ds[4:6]}-{ds[6:]}'
        d = json.load(open(p, encoding='utf-8'))
        raw = d.get('est_total_pct_raw')
        pct = float(raw) if raw is not None else (float(d['est_total_pct']) if d.get('est_total_pct') is not None else None)
        if pct is None:
            continue
        isfix = '_fix' in os.path.basename(p)
        if date not in seen or (isfix and not seen[date][1]):
            seen[date] = (pct, isfix, d.get('total_mv'), d)
    rows = sorted((dt, v[0], v[1], v[2], v[3]) for dt, v in seen.items())
    if rows and rows[0][0] > '2026-08-06':
        rows.insert(0, ('2026-08-06', -0.68, False, 392555.65, None))
    return rows


ser = load_series()
print('序列载入', len(ser), '个定价日:', ser[0][0], '→', ser[-1][0])
PROXY = {'A股医药': '000933', '大消费': '000932', '其他/宽基': '000300', '恒生科技': 'HSTECH'}
betas, samples = {}, {}
for t, code in PROXY.items():
    xs, ys = [], []
    for _dt, _pct, _isfix, _mv, d in ser[-46:]:
        dt = _dt
        if not d:
            continue
        tr = (d.get('tracks') or {}).get(t)
        ds = sorted(idx.get(code, {}))
        if dt not in idx.get(code, {}):
            continue
        i = ds.index(dt)
        if i == 0:
            continue
        ipct = (idx[code][dt] / idx[code][ds[i - 1]] - 1) * 100
        pct = None
        if tr and tr.get('pnl') is not None and tr.get('mv'):
            _mv_prev = tr['mv'] - tr['pnl']
            pct = 100 * tr['pnl'] / _mv_prev if _mv_prev else None
        if pct is None:
            continue
        xs.append(ipct)
        ys.append(pct)
    if len(xs) >= 10:
        mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
        cov = sum((a - mx) * (b - my) for a, b in zip(xs, ys))
        var = sum((a - mx) ** 2 for a in xs)
        betas[t] = round(cov / var, 3) if var else None
        samples[t] = len(xs)
print('\n赛道腿 β（对各自代理指数，近端样本）:', betas, '样本', samples)

SCEN = []
for sign, label in ((1.0, '指数 +1.0%'), (-1.0, '指数 −1.0%')):
    tot_pnl = 0.0
    detail = {}
    for t, b in betas.items():
        if b is None:
            continue
        leg_pct = b * sign
        pnl = EXPO[t]['mv'] * leg_pct / 100
        detail[t] = {'leg_pct': round(leg_pct, 4), 'pnl': round(pnl, 2)}
        tot_pnl += pnl
    SCEN.append({'label': label, 'total_pnl': round(tot_pnl, 2), 'total_pct': round(100 * tot_pnl / TOT, 4), 'detail': detail})
    print(f"  {label}: 组合 {tot_pnl:+,.2f} 元（{100*tot_pnl/TOT:+.4f}%）")
lo, hi = sorted(x['total_pnl'] for x in SCEN)
assert lo <= hi

# ---- 风险指标 ----
prev_risk = json.load(open(os.path.join(HIST, 'risk_stats_close_20261022.json'), encoding='utf-8'))
rets, dates = [], []
for _dt, _pct, _isfix, _mv, _d in ser:
    rets.append(_pct / 100)
    dates.append(_dt)
cum = 1.0
for r in rets:
    cum *= (1 + r)
chain_pct = round((cum - 1) * 100, 2)
mean = sum(rets) / len(rets)
sd = math.sqrt(sum((r - mean) ** 2 for r in rets) / (len(rets) - 1))
rf = 1.68 / 100
sharpe = round((mean * 252 - rf) / (sd * math.sqrt(252)), 2) if sd else None
vals, peak, mdd, peak_d, trough_d = [], 0.0, 0.0, None, None
lvl = 100.0
for r, dt in zip(rets, dates):
    lvl *= (1 + r)
    vals.append((dt, lvl))
    if lvl > peak:
        peak, peak_d = lvl, dt
    dd = lvl / peak - 1
    if dd < mdd:
        mdd, trough_d = dd, dt
last5 = (math.prod([1 + r for r in rets[-5:]]) - 1) * 100
last10 = (math.prod([1 + r for r in rets[-10:]]) - 1) * 100
print(f'\n风险指标：链路 {chain_pct:+.2f}%（{len(rets)} 日）/ 夏普 {sharpe} / MDD {mdd*100:+.2f}% / '
      f'近5日 {last5:+.2f}% / 近10日 {last10:+.2f}%')
print(f'  与 10/22 档对比：链路 {prev_risk["chain_cum_pct"]:+.2f}% → {chain_pct:+.2f}% / 夏普 {prev_risk["sharpe"]} → {sharpe} / '
      f'MDD {prev_risk["max_dd_pct"]:+.2f}% → {mdd*100:+.2f}%')


def week_cum(start, end):
    sel = [r for r, dt in zip(rets, dates) if start <= dt <= end]
    if not sel:
        return 0.0, 0
    return round((math.prod([1 + r for r in sel]) - 1) * 100, 2), len(sel)


# ★§3.151：周窗口下界为「周一常量」，不得由当前日期做减法派生
w42_c, w42_n = week_cum('2026-10-12', '2026-10-18')
w43_c, w43_n = week_cum('2026-10-19', '2026-10-25')  # ★修正：W43 周一 = 10/19（10/19 为 A股 交易日）
print(f'  W42 {w42_c:+.2f}%（{w42_n} 日）/ W43 {w43_c:+.2f}%（{w43_n} 日，含 10/19 / 10/20 / 10/21 / 10/22 四个已实现日）')

# ---- 纪律台账（累计口径，§3.125c）----
disc = fx['discipline']
cum_cut = disc['cumulative_amount']
print(f'\n纪律台账：累计 {cum_cut:,.2f} 元（{len([k for k in disc if k.startswith("cut")])} 次），本档新触发 0 元')
HS_AFTER = EXPO['恒生科技']['mv'] - cum_cut
CASH_AFTER = EXPO['现金']['mv'] + cum_cut
print(f'  纪律后：恒生科技 {HS_AFTER:,.2f} 元 = {100*HS_AFTER/TOT:.2f}% / 现金 {CASH_AFTER:,.2f} 元 = {100*CASH_AFTER/TOT:.2f}%')
# ★本档修正：disc 内新增 `pending_plan`（预案，非已成交）也带 amount 字段，
# 用「任意含 amount 的嵌套 dict 求和」会把它计入 → 累计口径必须显式限定 `cut*` 前缀
_cut_sum = sum(v['amount'] for k, v in disc.items() if k.startswith('cut') and isinstance(v, dict))
assert abs(disc['cumulative_amount'] - _cut_sum) < 0.01, f'纪律累计口径不一致 {disc["cumulative_amount"]} vs {_cut_sum}'

# ---- QDII US 10/22 段挂账区间（§3.144a notional 取 tracks[].mv）----
# ★§3.166b：本段方向由负转正（10/22 段 IYH +1.33%，防御轮动）→ 区间符号与端点顺序整体重算
_IYH_PCT = 1.33
_Q_NOTIONAL = fx['tracks']['美股标普医药']['mv']
_q_raw = _Q_NOTIONAL * _IYH_PCT / 100          # 负数
_q_outs = [round(_q_raw * e, 2) for e in (0.45, 0.90)]   # ★下界由 0.60 放宽至 0.45（10/21 实测 0.4657/0.4740）
_q_low, _q_high = min(_q_outs), max(_q_outs)   # §3.116b：对结果值取 min/max，禁止把弹性硬绑到低/高
_q_mid = round(_Q_NOTIONAL * _IYH_PCT / 100 * 0.675, 2)
assert _q_low <= _q_mid <= _q_high, f'QDII 区间端点顺序错误 {_q_low} / {_q_mid} / {_q_high}'
assert _Q_NOTIONAL == round(61785.49, 2), 'QDII notional 与 tracks[].mv 不一致（§3.144a）'
print(f"\nQDII US 10/22 段：notional={_Q_NOTIONAL:,.2f} 元 × IYH {_IYH_PCT}% × 弹性 0.45~0.90 "
      f"→ 区间 {_q_low:+,.2f} 元 ~ {_q_high:+,.2f} 元（中枢 0.675 = {_q_mid:+,.2f} 元）")

# ---- 医药反向线（10/22 起新基线）----
board_med_1021 = fx['board_med']  # 10/22 收盘医药板块代理（五口径均值）
out = {
    'date': TODAY, 'session': 'preopen', 'state': 'preopen_estimate', 'finalized': False,
    'session_type': 'normal_trading_day_preopen',
    'session_type_note': ('档型③「正常交易日盘前」：A股 10/23 正常交易日（08:00 未开盘）+ 港股 10/23 正常交易日'
                          '（10/22 已复市并收盘）+ 美股 10/23 正常交易日 → 08:00 A股/港股 均无当日价格 → '
                          'close / pending 均不产，待消化沿用 10/22 收盘修正件'),
    'base_file': FIXNAME, 'base_total_mv': TOT, 'total_mv': TOT,
    'guard': {'sum_tracks_mv': round(smv, 2), 'dev_mv': round(dev_mv, 4),
              'sum_tracks_pnl': round(sum(v.get('pnl') or 0 for v in fx['tracks'].values()), 2),
              'est_total_pnl': TOTAL_PNL, 'dev_pnl': round(dev_pnl, 4),
              'detail_restore_rule': rule_used, 'detail_restore_max_dev': round(cand[rule_used][0], 4)},
    'est_total_pnl': 0.0, 'est_total_pct': 0.0,
    'day_result_note': ('本档（10/23）当日估算盈亏 **0 元**，归因是「A股/港股 全部持仓标的均不可定价」而非「市场持平」：'
                        '① A股 场外基金当日净值未发布（15:00 后）；② A股 场内 ETF/个股未开盘（09:30）；'
                        '③ 港股 09:30 才开盘 → 恒生系与场外港股联接无新价格；'
                        '④ **美股 10/22 已收盘并归档（本档唯一新增真实定价）→ 计入 QDII 挂账段，不计入当日损益**（T+1~T+2 净值迟滞）。'),
    'tracks': EXPO,
    'weights_recomputed_from_mv': True,
    'stale_weight_fields_in_fix': {'note': '§3.146a：_fix 件 pct_of_total 为修正前分母派生值，本档一律按 mv/total_mv 现算'},
    'med_mv': round(MED, 2), 'med_pct': MED_PCT, 'med_cap_pct': 40.0,
    'threshold_all_med_pct': round(r_all * 100, 2), 'threshold_a_sh_med_pct': round(r_ash * 100, 2),
    'threshold_formula': 'A(1+r)/(B + A·r) = 0.40（全部医药同涨）／(A(1+r)+M)/(B+A·r) = 0.40（仅 A股医药）；B = 基准总资产',
    'defense': {
        'hstech_4250': {'close': hs_v, 'close_date': hs_d, 'line': LINE_HS, 'dist_pct': dist_hs,
                        'prev_dist_pct': prev_dist, 'abs_delta_pct': _delta,
                        'state': hs_state, 'prev_state': prev_state,
                        'state_derivation': f'|dist| {abs(prev_dist):.4f}% → {abs(dist_hs):.4f}%（Δ {_delta:+.4f}pct）→ {hs_state}；state 由公式现算，未继承（§3.149a）',
                        'next_line': NEXT_LINE, 'next_line_dist_pct': dist_next,
                        'action': '0（09:30 前无交易时段；收盘价判定，禁用 A股 场内 513050/513180 溢价折价替代，§3.121e）'},
        'hstech_4000': {'close': hs_v, 'close_date': hs_d, 'line': NEXT_LINE, 'dist_pct': dist_next,
                        'intraday_low_1022': 3781.15, 'intraday_high_1022': 3949.02,
                        'state': 'close_below_4000_second_day',
                        'state_derivation': (f'10/22 收盘 {hs_v} < {NEXT_LINE}（{dist_next:+.4f}%，{hs_v-NEXT_LINE:+.2f} 点）'
                                             '→ **连续第 2 日收于 4,000 下方**（10/21 首次 −0.1308% → 10/22 −5.1517%，破位幅度走阔 5.0209pct）'),
                        'distance_note': (f'10/22 收盘 {hs_v} 距 4,000 为 **{dist_next:+.4f}%**；'
                                          '10/22 日内高 3,949.02（全天未回到 4,000 上方）、低 3,781.15 → '
                                          '**低开低走、无一次反抽站上 4,000**；4,000 由「防线」转为「压力位」'
                                          '（与 4,250 构成双层压力：3,793.93 需 +5.43% 才回收 4,000、+12.02% 才回收 4,250）'),
                        'sub_line_3950': {'line': 3950.0, 'dist_pct': round((hs_v / 3950.0 - 1) * 100, 4),
                                          'state': 'breached_1022',
                                          'note': '10/22 收盘已破 3,950（−3.9511%）→ 盘后档已建 −0.5% 减配预案 1,858.66 元，**执行窗口 = 10/23 09:30-15:00**'},
                        'sub_line_3700': {'line': 3700.0, 'dist_pct': round((hs_v / 3700.0 - 1) * 100, 4),
                                          'note': f'下一参考位：3,793.93 距 3,700 仅 **{round((hs_v/3700.0-1)*100,4):+.4f}%**（−2.48% 即达）→ 若今日收盘再破 → 按新线建案、同日不重复扣减'},
                        'action': ('本档 08:00 无港股交易时段 → **执行 0 元**；3,950 案（1,858.66 元）由盘后档建案、'
                                   '**本档确认执行窗口 09:30-15:00**；4,000 案（1,863.33 元）仍 `awaiting_user_confirmation`')},
        'csi_consume_12100': {'close': zc_v, 'close_date': zc_d, 'line': LINE_ZC, 'dist_pct': dist_zc,
                              'state': 'above_lower_line', 'action': '0（A股 09:30 后按盘中价复核）'},
        'a_med_reverse': {'proxy_pct_1022': board_med_1021, 'line': -1.5,
                          'state': 'triggered_4th_time_not_executed',
                          'trigger_fact': f'10/22 医药板块代理（五口径均值）**{board_med_1021:+.4f}%** ≤ −1.5% → 第 4 次触发',
                          'decision': ('**本档判定「不执行」**：① 该线 4 次触发、前 3 次全部作废（次日均为正）→ 判别力极低；'
                                       '② 与恒科 3,950 案（1,858.66 元）**同日不同时执行**（避免单日双杀式减仓）；'
                                       '③ 今日若 A股 医药板块代理**收盘转正 → 该线正式注销**（0/4，`invalidated_after_trigger` → 4）'),
                          'baseline_reset': f'新基线 = 10/22 收盘（**{board_med_1021:+.4f}%**）；今日 ≤ −1.5% 方构成第 5 次触发',
                          'semantics': ('该线自 9/24 起**四次触发、三次作废** → 已降级为「观察标记」而非「触发条件」（§3.114c 扩展）；'
                                        '**触发后仍须次日收盘确认，不得当日动作**')},
    },
    'hk_pending_digest': {
        'refreshed': False,
        'refresh_note': ('本档 08:00 港股未开盘 → **无新增港股定价日** → 无新增待消化段，'
                         '沿用 10/22 收盘修正件（window = ["2026-10-22"] / window_closed = True）'),
        'segments': hk, 'total_mv': round(hk_tot, 2), 'total_pct': hk_pct,
        'track_layer_pct': round(track_hk_pct, 4), 'broad_layer_pct': round(100 * hk['broad'] / TOT, 4),
        'window_closed': fx['pending_release'].get('window_closed'),
        'window': fx['pending_release'].get('window'),
        'static_rule': '静态测算只可给区间上下界、不得作方向判断（§3.108 条款 24）',
    },
    'qdii_pending': {
        'refreshed': True,
        'refresh_note': ('**本档新增 US 10/22 收盘**（IYH 76.22 / +1.33%、XLV 181.30 / +1.32%，已于本档 08:00 归档）'
                         '→ 新增「US 10/22 段」挂账区间；该段净值最快 T+1~T+2 出库，**本档不可声称已实现**'),
        'segment': 'US 2026-10-22', 'notional': fx['tracks']['美股标普医药']['mv'],
        'low': _q_low, 'mid': _q_mid, 'high': _q_high,
        'iyh_pct': _IYH_PCT, 'elasticity_range': [0.45, 0.90],
        'basis_rule': ('notional 取 tracks[].mv（§3.144a）；本段 IYH **+1.33%** 为**正向**，弹性 0.90 得最优值、0.60 得最差值 → '
                       '端点按结果值 min/max 排序（§3.116b / §3.166b），非按弹性顺序'),
        'stale_nav_legs': {'000369': '2026-10-21', '016280': '2026-10-21', '164906': '2026-10-21'},
        'lof_164906_mv': fx['lof_164906_mv'],
        'lof_note': ('164906 计入恒生科技腿、不在 QDII 区间内；其 10/21 净值 0.8485（−1.66%），10/22 净值未出库'),
        'placeholder_recheck': ('`000369` / `016280` 的 10/20 净值 −0.57% / −0.58% 与 IYH 10/20 的 −0.57% 传导系数约 1.00 → '
                                '**10/22 档登记的 `suspect_placeholder` 已解除**；但样本仅 2 券位 × 1-2 窗口，系数仍 `pending`'),
        'coefficient_status': 'pending（可量化样本 2 券位 × 2 窗口，未达 ≥4 券位 × ≥5 交易日重估门槛）',
    },
    'discipline': {
        'cumulative_amount': cum_cut, 'new_trigger_today': 0.0,
        'hk_after': round(HS_AFTER, 2), 'hk_after_pct': round(100 * HS_AFTER / TOT, 2),
        'cash_after': round(CASH_AFTER, 2), 'cash_after_pct': round(100 * CASH_AFTER / TOT, 2),
        'basis_rule': '累计口径（已成交 + 已登记 全量扣除，§3.125c）',
    },
    'scenario': {'basis': f'各赛道代理指数同向 ±1.0%，腿 β 由近端 {max(samples.values()) if samples else 0} 个定价日回归得出',
                 'cases': SCEN, 'low': lo, 'high': hi,
                 'note': '本档无当日定价，情景为「若指数沿该方向走 1%」的敏感度，不是收益预测'},
    'beta': betas, 'beta_samples': samples,
    'risk': {'chain_cum_pct': chain_pct, 'chain_days': len(rets), 'sharpe': sharpe, 'sharpe_n': len(rets),
             'daily_mean_pct': round(mean * 100, 4), 'daily_sd_pct': round(sd * 100, 4),
             'max_dd_pct': round(mdd * 100, 2), 'max_dd_peak': peak_d, 'max_dd_trough': trough_d,
             'last5_cum_pct': round(last5, 2), 'last10_cum_pct': round(last10, 2),
             'rf_pct': 1.68, 'rf_note': '中国 10Y 国债硬编码 1.68%（本地序列自 2026-08-11 后未维护）',
             'w42_cum_pct': w42_c, 'w42_days': w42_n, 'w43_cum_pct': w43_c, 'w43_days': w43_n,
             'w43_note': ('W43（10/19-10/25，周一常量）本档含 10/19（+0.5434%）、10/20（+0.1351%）、10/21（−0.2508%）、10/22（−1.5820%，取 _fix 修正件）'
                          '四个已实现交易日；10/23 尚未收盘 → 不计入'),
             'unchanged_vs_1021': prev_risk['chain_cum_pct'] == chain_pct},
    # ★恒科 3,950 收盘失守（10/22）→ 盘后档已建案，本档「确认执行窗口」（08:00 无交易时段，仍不成交）
    'preplan': {
        'id': 'hstech_3950_cut3_exec',
        'trigger_fact': f'10/22 收盘 {hs_v} < 3,950（{round((hs_v/3950.0-1)*100,4):+.4f}%）→ 3,950 线首次收盘失守',
        'triggered_on': '2026-10-22',
        'pct': 0.5,
        'amount': 1858.66,
        'amount_formula': '0.5% × 371,732.03 元（触发日 10/22 的「上一有效估值日基准总资产」= 10/21 收盘修正件）',
        'amount_alt_basis': {'basis': '10/22 修正后总资产 365,851.37 元', 'amount': round(365851.37 * 0.005, 2),
                             'note': '若改按修正后总资产计则 1,829.26 元（差 29.40 元）；**本档沿用 10/22 盘后档已登记的 1,858.66 元，不改案**（避免「事后重设分母」的裁量）'},
        'targets': ['012348（天弘恒生科技联接A）', '513180（恒生科技ETF华夏）'],
        'target_rule': '限「纯恒科」口径，**不落中概**（513050 / 164906）',
        'execute_window': '2026-10-23 09:30-15:00（当日收盘前）',
        'executed_today': False,
        'why_not_today_0800': '08:00 A股/港股 均未开盘 → 无交易时段；本档只「确认执行窗口」、不成交',
        'no_stacking_note': '4,250 线本季已触发 2 次（9/29、10/2）→ **不重复叠加**；4,000 案（1,863.33 元）`awaiting_user_confirmation`；3,950 案为独立新线（§3.114c）',
        'discipline_priority': '**即使今日盘前恒科反弹站回 3,950 / 4,000 上方，默认仍执行（纪律优先于择时）**；若用户选择择时，须在本档内明示并登记 `waived_reason`',
        'cum_after_plan': round(cum_cut + 1858.66, 2),
        'cum_before_plan': cum_cut,
        # ★§3.125c 累计口径：扣除「已成交 3,786.90 元 + 本次 1,858.66 元」，不得只扣当次
        'hk_after_plan': round(EXPO['恒生科技']['mv'] - (cum_cut + 1858.66), 2),
        'hk_after_plan_pct': round(100 * (EXPO['恒生科技']['mv'] - (cum_cut + 1858.66)) / TOT, 2),
        'cash_after_plan': round(EXPO['现金']['mv'] + (cum_cut + 1858.66), 2),
        'cash_after_plan_pct': round(100 * (EXPO['现金']['mv'] + (cum_cut + 1858.66)) / TOT, 2),
        'cumulative_basis_note': '恒科/现金「减后」为累计口径（已成交 3,786.90 元 + 本次 1,858.66 元 = 5,645.56 元），§3.125c',
        'a_med_plan_status': 'A股医药反向线第 4 次触发（10/22 −1.895%）→ **本档判定不执行**，与恒科案不同日双执行',
    },
    'new_buy': 0.0, 'track_actions': {t: 0.0 for t in EXPO},
    'track_actions_note': '本档 08:00 A股/港股 均未开盘 → 赛道级动作全部为 0；预案（非执行）见报告「策略建议」',
    'chain_0pct_row_inserted': False,
    'note': ('档型③「正常交易日盘前」→ **不产 portfolio_close_* 与 portfolio_pending_***（A股/港股 08:00 均无当日价格）。'
             f'基准取 {FIXNAME}（§3.108 同日期以 _fix 为准；本档 08:00 完成 §3.140a 第 8 例补正：2 行 10/22 净值到位，当日损益 −5,025.81 元 → −5,880.66 元）。'
             '赛道权重按 mv/total_mv 现算（§3.146a），不复用 _fix 件 pct_of_total。'),
}
json.dump(out, open(os.path.join(HIST, 'portfolio_preopen_20261023.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)

risk_out = {
    'date': TODAY, 'session': 'preopen',
    'chain_cum_pct': chain_pct, 'chain_days': len(rets), 'chain_0pct_row_inserted': False,
    'chain_gap_note': ('10/23 为档型③「正常交易日盘前」→ **不产 portfolio_close_* / portfolio_pending_***；'
                       '链式序列末行 = 10/22 收盘修正件（**365,851.37 元 / −1.5820%**），本档不插行'),
    'sharpe': sharpe, 'sharpe_n': len(rets), 'daily_mean': round(mean * 100, 4), 'daily_sd': round(sd * 100, 4),
    'max_dd_pct': round(mdd * 100, 2), 'max_dd_peak': peak_d, 'max_dd_trough': trough_d,
    'last5_cum_pct': round(last5, 2), 'last10_cum_pct': round(last10, 2),
    'rf_pct': 1.68, 'rf_note': '中国 10Y 国债硬编码 1.68%（本地 10Y 序列自 2026-08-11 后未维护，缺口待补）',
    'w41_cum_pct': prev_risk.get('w41_cum_pct'), 'w41_days': prev_risk.get('w41_days'),
    'w42_cum_pct': w42_c, 'w42_days': w42_n,
    'w42_note': f'W42（10/12-10/18）{w42_n} 日逐日累计；窗口下界为周一常量（§3.151）',
    'w43_cum_pct': w43_c, 'w43_days': w43_n,
    'w43_note': f'W43 = 2026-10-19 ~ 2026-10-25（周一常量，§3.151）；本档含 {w43_n} 个已实现日（10/19 / 10/20 / 10/21 / 10/22）',
    'total_mv_end': TOT, 'med_pct_end': MED_PCT,
    'tracks_end': {t: {'mv': v['mv'], 'pct_of_total': v['pct']} for t, v in EXPO.items()},
    'base_switched': {'orig': 366706.22, 'fix': 365851.37, 'delta': -854.85,
                      'src': 'portfolio_close_20261022.json → _fix（§3.140a 第 8 例，2 行 10/22 净值到位：002708 ×2）',
                      'note': '本节须显式披露三元组（§3.149g）：10/22 日收益率 -1.3520% → -1.5820%'},
    'recompute_note': ('本档链式序列末行 = 10/22 收盘修正件（**365,851.37 元 / −1.5820%**）→ 全量重算（非沿用）；'
                       'US 10/22 归档不改变组合总资产（QDII 净值 T+1~T+2 迟滞）→ 10/23 尚无已实现收益'),
    'override_rule': '显式优先级（_fix 优先）+ est_total_pct_raw 显式判空（§3.98 / §3.102）',
}
json.dump(risk_out, open(os.path.join(HIST, 'risk_stats_20261023_preopen.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
print('\nSAVED portfolio_preopen_20261023.json / risk_stats_20261023_preopen.json')
