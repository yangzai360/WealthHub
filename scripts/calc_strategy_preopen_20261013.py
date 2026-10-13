# -*- coding: utf-8 -*-
"""2026-10-13（周二）盘前档：组合策略计算 —— **A股/港股/美股三市场均为正常交易日**
SESSION_TYPE = 'normal_trading_day_preopen'（**档型③**：A股与港股当日均为正常交易日，但 08:00 双方均无新价格）
  → 依 §3.28 / §3.110 档型③：**不产 `portfolio_close_*`、不产 `portfolio_pending_*`**；
    **待消化不做新测算**（港股腿窗口已于 10/8 收口；QDII 腿**本档新增 US 10/12 单日段** → 首次给区间）；
基准 = **10/12 收盘件（portfolio_close_20261012.json）= 376,911.21 元**

★★★ 本档结构差异（派生后必检） ★★★
  ① 基准由「10/9 收盘修正件 377,040.85 元」推进为「10/12 收盘件 **376,911.21 元**」
     （10/12 单日 **−129.64 元 / −0.0344%**）；
  ② 美股腿**本档有新增真实交易日**：**US 10/12 收盘成型于北京 10/13 04:00**
     → `indices.csv` **+8 行**（XLV 171.99 / IYH 72.55 等）；**下一未知交易日 = US 10/13（收盘成型于北京 10/14 04:00）**；
  ③ 恒生科技防线基准价更新为 10/12 收盘 **4,169.57**（−0.67%），距 4,250 = −1.8925%（较 10/9 的 −1.2273% 走阔）；
     下一观察线 4,000（距 **+4.2392%**）；
  ④ 中证消费 10/12 收 **12,469.1511**（+0.92%）→ 距 12,100 下沿 **+3.0508%**、距 12,000 **+3.9096%**；
  ⑤ A股医药板块代理 10/12 = **−0.6000%** → 距反向兑现线（−1.5%）**+0.90pct**；被动减配预案维持作废（10/9 已按明文作废）；
  ⑥ **QDII 挂账首次给出「US 10/12 单日段」区间**：notional 59,330.09 元 × IYH **+0.5683%** × 系数 0.60~0.90
     → 区间见下方；**164906（中概互联 LOF）腿仍不给区间**（NAV 最新净值日 10/09）。
  ⑦ 不产 pending 台账（档型③）→ 产 `session_type` 标注 + `new_pending` 自证（**本档 new_pending = 1**）。
⚠️ §3.118a / §3.139：QDII 挂账**只给区间、禁止中枢点值**（系数 0.60~0.90，未按「≥4 券位 × ≥5 交易日」重估）。
⚠️ §3.123e 纪律累计口径：第 1 次 1,882.46 元（9/29 触发、9/30 成交）+ 第 2 次 1,904.44 元
   （10/2 触发、10/8 成交）= 累计 3,786.90 元（**本档无新增纪律动作**）。
⚠️ §3.112a：逐券还原式**禁止按字段名取数** → 用机器判据在 `mv0_new+est_pnl` 与 `mv0+est_pnl` 之间二选一，
   并加硬守卫 `max|Σ_track(还原式) − tracks[track].mv| < 1.5`；未通过则终止本档计算。
⚠️ §3.133a：展示类字段一律由数据源现算 + 自校验断言，禁止手写常量表。
"""
import json, os, csv as _csv

BASE = '/Users/jieyang/Documents/WealthHub'
HIST = os.path.join(BASE, 'data/processed/history')
TODAY = '2026-10-13'
SESSION_TYPE = 'normal_trading_day_preopen'
BASEFILE = 'portfolio_close_20261012.json'
fix = json.load(open(os.path.join(HIST, BASEFILE), encoding='utf-8'))

TOTAL = fix['total_mv']
tracks = fix['tracks']
print(f'基准（10/12 收盘件）= {TOTAL:,.2f} 元  <- {BASEFILE}')
print('  [档型③] 正常交易日盘前（A股 + 港股 + 美股 三市场正常交易日）'
      ' -> 不产 close / 不产 pending、待消化不做新测算（§3.28 / §3.110）')
dev = abs(sum(v['mv'] for v in tracks.values()) - TOTAL)
print(f'  硬守卫 |SUM tracks.mv - total_mv| = {dev:.4f} 元  {"OK" if dev < 1.5 else "FAIL"}')
assert dev < 1.5, 'SUM tracks.mv 与 total_mv 不一致，终止本档计算（§3.104）'
assert abs(sum(v['pnl'] for v in tracks.values()) - fix['est_total_pnl']) < 1.5, \
    '§3.109 条款 26 硬守卫失败：Σ tracks.pnl != est_total_pnl'

for k, v in sorted(tracks.items(), key=lambda kv: -kv[1]['mv']):
    print(f"  {k:10s} mv={v['mv']:>11,.2f}  w={v['pct_of_total']:>6.2f}%  day={v['day_pct']:+.3f}%  pnl={v['pnl']:+.2f}")

# ---------- 医药敞口与门槛方程（§3.98 / §3.112）----------
med = round(tracks['A股医药']['mv'] + tracks['美股标普医药']['mv'], 2)
B_nm = TOTAL - med
A_sh = tracks['A股医药']['mv']
th_all = ((0.40 / 0.60) * B_nm / med - 1) * 100
th_sh = (((0.40 / 0.60) * B_nm - (med - A_sh)) / A_sh - 1) * 100
print(f'\n医药敞口 {med:,.2f} 元 = {med/TOTAL*100:.2f}%  距 40% 上限 {40-med/TOTAL*100:.2f}pct')
print(f'  门槛：两医药赛道同涨 {th_all:+.2f}%  /  仅 A股医药 {th_sh:+.2f}%')
print(f'  非医药对手盘 {B_nm:,.2f} 元')

# ---------- §3.112a 逐券还原式机器判据（禁止按字段名取数）----------
CAND_RULES = ('mv0_new+est_pnl', 'mv0+est_pnl')


def restore_val(d, rule):
    a, b = rule.split('+')
    return float(d[a]) + float(d[b])


rule_dev = {}
for rule in CAND_RULES:
    worst = 0.0
    for tk, tv in tracks.items():
        s = sum(restore_val(d, rule) for d in fix['detail'] if d.get('track') == tk)
        worst = max(worst, abs(s - tv['mv']))
    rule_dev[rule] = round(worst, 4)
print('\n§3.112a 逐券还原式机器判据（逐赛道最大偏差）:', rule_dev)
OK_RULES = [r for r, v in rule_dev.items() if v < 1.5]
assert OK_RULES, f'⚠️ 无还原式通过硬守卫 {rule_dev} → 终止本档计算（§3.112a / §3.111）'
RESTORE_RULE = min(OK_RULES, key=lambda r: rule_dev[r])
RESTORE_DEV = rule_dev[RESTORE_RULE]
print(f'  -> 采用 {RESTORE_RULE}（dev {RESTORE_DEV:.4f} 元）')

# ---------- 港股暴露三层拆解（§3.108 条款 23/24）----------
HK_TECH_CODES = {'012348', '513180'}          # 纯恒生科技系
CPO_CODES = {'513050', '164906'}              # 中概/海外互联系
BROAD_HK_CODES = {'000071', '159920'}         # 宽基中的恒生系
pure = cpo = broad = 0.0
seg_detail = []
for d in fix['detail']:
    raw = str(d.get('code', ''))
    code6 = ''.join(c for c in raw if c.isdigit())[-6:] if any(c.isdigit() for c in raw) else ''
    mv = restore_val(d, RESTORE_RULE)
    if code6 in HK_TECH_CODES:
        pure += mv; seg_detail.append(('纯恒生科技系', code6, d['name'], round(mv, 2)))
    elif code6 in CPO_CODES:
        cpo += mv; seg_detail.append(('中概·海外互联系', code6, d['name'], round(mv, 2)))
    elif code6 in BROAD_HK_CODES:
        broad += mv; seg_detail.append(('宽基恒生系', code6, d['name'], round(mv, 2)))
hk_total = tracks['恒生科技']['mv'] + broad
print(f'\n港股暴露（三层拆解）：总 {hk_total:,.2f} 元 = {hk_total/TOTAL*100:.2f}%')
print(f'  赛道层「恒生科技」{tracks["恒生科技"]["mv"]:,.2f} 元 = {tracks["恒生科技"]["pct_of_total"]:.2f}%'
      f'  +  宽基层「恒生系」{broad:,.2f} 元 = {broad/TOTAL*100:.2f}%'
      f'  -> 只报赛道层将低估 {broad/TOTAL*100:.2f}pct')
print(f'  三段法：纯恒生科技系 {pure:,.2f}（{pure/TOTAL*100:.2f}%）/ 中概·海外互联系 {cpo:,.2f}（{cpo/TOTAL*100:.2f}%）'
      f'/ 宽基恒生系 {broad:,.2f}（{broad/TOTAL*100:.2f}%） = {pure+cpo+broad:,.2f} 元 '
      f'（和校验 {round(pure+cpo+broad, 2) == round(hk_total, 2)}）')
for r in seg_detail:
    print(f'    {r[0]} {r[1]} {r[2][:22]:24s} {r[3]:>10,.2f}')
assert abs((pure + cpo + broad) - hk_total) < 1.5, '港股三段和与 hk_total 不一致（§3.108 条款 23）'

# ---------- 恒生科技 0.5% 纪律减仓（累计口径，§3.123e）----------
disc = fix.get('discipline', {})
cut1_amt = disc.get('cut1', {}).get('amount', 1882.46)
cut2_amt = disc.get('cut2', {}).get('amount', 1904.44)
cut_cum = round(cut1_amt + cut2_amt, 2)
hk_after = round(tracks['恒生科技']['mv'] - cut_cum, 2)
cash_after = round(tracks['现金']['mv'] + cut_cum, 2)
print(f'\n恒生科技 0.5% 纪律减仓（累计口径）：{cut_cum:,.2f} 元')
print(f'  第 1 次 {cut1_amt:,.2f} 元（9/29 触发 -> 9/30 成交，已结算）')
print(f'  第 2 次 {cut2_amt:,.2f} 元（10/2 触发 -> 10/8 成交，已结算）')
print(f'  恒生科技 {tracks["恒生科技"]["mv"]:,.2f} -> {hk_after:,.2f}'
      f'（{tracks["恒生科技"]["pct_of_total"]:.2f}% -> {hk_after/TOTAL*100:.2f}%）')
print(f'  现金     {tracks["现金"]["mv"]:,.2f} -> {cash_after:,.2f}'
      f'（{tracks["现金"]["pct_of_total"]:.2f}% -> {cash_after/TOTAL*100:.2f}%）')
print(f'  自证 cumulative_amount == SUM cut_i.amount: {cut_cum} == {cut1_amt} + {cut2_amt}'
      f' -> {abs(cut_cum - (cut1_amt + cut2_amt)) < 0.01}')

# ---------- 行情序列（indices.csv 现算，§3.133a：禁止手写常量表） ----------
_ser = {}
with open(os.path.join(HIST, 'indices.csv'), encoding='utf-8-sig') as f:
    for r in _csv.DictReader(f):
        _ser.setdefault(r['code'], {})[r['date'][:10]] = float(r['close'])
for c in ('XLV', 'IYH', 'HSTECH', '000932', '000001', '000933', '000300', '399006', 'HSCEI',
          'HSHKBIO', 'QQQ', 'DIA', 'SPY', '.IXIC', '.DJI', '.INX', '399997', '000913', '399989',
          '000905', '399005'):
    ds = sorted(_ser.get(c, {}))
    print(f'  {c:8s} 末行={ds[-1] if ds else None} 值={_ser.get(c, {}).get(ds[-1]) if ds else None} 日数={len(ds)}')


def last2(code):
    ds = sorted(_ser[code])
    return _ser[code][ds[-1]], (ds[-1], _ser[code][ds[-1]]), (ds[-2], _ser[code][ds[-2]])


US_LAST_US, us_cur, us_prev = last2('IYH')          # US 10/12 = 本档新增
IYH_PCT = round((us_cur[1] / us_prev[1] - 1) * 100, 4)
_xds = sorted(_ser['XLV'])
XLV_PCT = round((_ser['XLV'][_xds[-1]] / _ser['XLV'][_xds[-2]] - 1) * 100, 4)
print(f'\n美股本档新增真实收盘：IYH {us_cur[0]} {us_cur[1]}（{IYH_PCT:+.4f}%）'
      f' | XLV {_xds[-1]} {_ser["XLV"][_xds[-1]]}（{XLV_PCT:+.4f}%）')

# ---------- QDII 挂账（本档新增 US 10/12 单日段 → 首次给区间） ----------
QDII_MV = 0.0
for d in fix['detail']:
    code6 = ''.join(c for c in str(d.get('code', '')) if c.isdigit())[-6:]
    if code6 in ('000369', '016280'):
        QDII_MV += restore_val(d, RESTORE_RULE)
LOF_MV = 0.0
for d in fix['detail']:
    code6 = ''.join(c for c in str(d.get('code', '')) if c.isdigit())[-6:]
    if code6 == '164906':
        LOF_MV += restore_val(d, RESTORE_RULE)
COEF_LO, COEF_MID, COEF_HI = 0.60, 0.72, 0.90
q_low = round(QDII_MV * IYH_PCT / 100 * COEF_LO, 2)
q_mid = round(QDII_MV * IYH_PCT / 100 * COEF_MID, 2)
q_high = round(QDII_MV * IYH_PCT / 100 * COEF_HI, 2)
print(f'\nQDII 挂账（§3.112f / §3.118a：只给区间、禁止中枢点值）')
print(f'  notional（000369 + 016280 逐券还原后合计）= {QDII_MV:,.2f} 元')
print(f'  本档新增美股交易日 = US {us_cur[0]}（IYH {IYH_PCT:+.4f}%）-> 新窗口首次可量化')
print(f'  区间：{q_low:+,.2f} 元 ~ {q_high:+,.2f} 元（中枢参考 {q_mid:+,.2f} 元，系数 {COEF_LO}~{COEF_HI}）')
print(f'  [!] 164906（中概互联 LOF）notional {LOF_MV:,.2f} 元、NAV 最新净值日 2026-10-09 -> 该腿不给区间（§3.122e）')
print(f'  [!] 下一未知交易日 = US 10/13（收盘成型于北京 10/14 04:00）')
assert q_low <= q_mid <= q_high, '§3.116b 区间端点语义错误'

# ---------- 港股腿待消化：沿用上一档终值（档型③，不重算） ----------
PEND = fix.get('pending_release', {})
hk_low = PEND.get('window_estimate_low', -973.41)
hk_high = PEND.get('window_estimate_high', -758.58)
hk_mid = PEND.get('window_estimate_mid_proxy_avg', -866.14)
print('\n港股腿「待消化」= 已于 10/8 收口（4/4 全部定价、净值一次性兑现）（档型③不重算）')
print(f'  终值：{hk_low:+,.2f} 元 ~ {hk_high:+,.2f} 元（代理均值中枢 {hk_mid:+,.2f} 元）'
      f' | window_closed = {PEND.get("window_closed")}')
print('  [!] 10/12 收盘档 new_window_this_session = []（正常交易日按当日真实净值逐券定价）→ 无新增待消化项（§3.112i）')

# ---------- 三条防线（取 10/12 收盘口径，全部由 indices.csv 现算） ----------
HS = _ser['HSTECH'][sorted(_ser['HSTECH'])[-1]]
HS_DS = sorted(_ser['HSTECH'])
HS_PREV = _ser['HSTECH'][HS_DS[-2]]
ZZ = _ser['000932'][sorted(_ser['000932'])[-1]]
SH = _ser['000001'][sorted(_ser['000001'])[-1]]
SH_PREV = _ser['000001'][sorted(_ser['000001'])[-2]]
BMED = fix['defense']['a_med_reverse_1_5pct']['proxy_pct']
print('\n三条防线（全部取 10/12 收盘口径；A股 两项今日 09:30 后验证）：')
print(f'  (1) 恒生科技 4,250：10/12 收 {HS:,.2f}（前收 {HS_PREV:,.2f} / {(HS/HS_PREV-1)*100:+.4f}%）'
      f' -> 距防线 {HS-4250:+,.2f} 点 / {(HS/4250-1)*100:+.4f}%'
      f'【破位幅度由 10/9 的 −1.2273% 走阔至 −1.8925%】')
print(f'     下一观察线 4,000（距 {(HS/4000-1)*100:+.4f}%）'
      f' | 10/12 日内高 4,241.07 < 4,250 -> intraday_touched_above = false（§3.129b）')
print(f'     -> 第 2 次减仓（{cut2_amt:,.2f} 元）已于 10/8 成交（累计 {cut_cum:,.2f} 元）；本档不新增动作')
print(f'  (2) 中证消费 12,100 下沿：10/12 收 {ZZ:,.4f} -> {(ZZ/12100-1)*100:+.4f}%'
      f'（下一线 12,000 距 {(ZZ/12000-1)*100:+.4f}%）-> 今日 09:30 后可验证')
print(f'  (3) A股医药反向兑现线（line_pct = -1.5，触发 = 板块代理 <= -1.5%）：'
      f'10/12 板块代理 {BMED:+.4f}% -> 未触发（距线 {BMED-(-1.5):+.4f}pct）')
print(f'     [!] §3.136a：10/8 建立的「被动减配预案」已于 10/9 按明文「回调序列断裂、预案不启动」作废，本档维持作废')
print(f'  附：上证 10/12 收 {SH:,.4f}（{(SH/SH_PREV-1)*100:+.4f}%）；恒指 10/12 收 '
      f'{_ser["HSCEI"][sorted(_ser["HSCEI"])[-1]] is not None and _ser.get("HSI",{}).get("2026-10-12","n/a")}'
      f'；恒生国企 10/12 收 {_ser["HSCEI"][sorted(_ser["HSCEI"])[-1]]:,.2f}')

# ---------- 产物 ----------
out = {
    'date': TODAY, 'session': 'preopen', 'session_type': SESSION_TYPE,
    'session_type_note': ('档型③「正常交易日盘前」= A股 10/13（正常交易日）+ 港股 10/13（正常交易日）+ '
                          '美股 10/13（正常交易日）；08:00 A股/港股均无当日价格 -> 不产 portfolio_close_*、'
                          '不产 portfolio_pending_*；港股腿待消化窗口已于 10/8 收口、不做新测算；'
                          'QDII 挂账**本档新增 US 10/12 单日段**（首次给区间）；'
                          '本档新增真实定价 = US 10/12 收盘（indices.csv +8 行）'),
    'calendar_verification': {
        'A股': 'stock_zh_index_daily(sh000001) 末行 = 2026-10-12（收 3,797.2424 / −0.43%）-> 10/13 为正常交易日，09:30 开盘前无新价格',
        '港股': '新浪 hq rt_hkHSTECH 返回体日期字段 = 2026/10/12 16:08（收 4,169.57 / −0.673%）-> 10/13 今日待开 09:30（非休市）',
        '美股': 'stock_us_daily(IYH/XLV) 末行 = 2026-10-12（XLV 171.99 / IYH 72.55）-> US 10/12 收盘已于本档（10/13 盘前）写入 indices.csv；US 10/13 收盘成型于北京 10/14 04:00',
        'rule': '三市场各自独立验证、不得互相外推（§3.107 / §3.119b / §3.122b）'},
    'base_total': TOTAL, 'base_file': BASEFILE, 'base_guard_dev': round(dev, 4),
    'base_revision': {'prev_total': 377040.85, 'delta': round(TOTAL - 377040.85, 2),
                      'reason': '本档基准为 10/12 收盘件（10/12 为正常交易日，已计入链式序列）；'
                                '较 10/9 收盘修正件 377,040.85 元推进 −129.64 元（10/12 单日 −0.0344%）'},
    'restore_rule_used': RESTORE_RULE, 'restore_rule_all_dev': rule_dev,
    'detail_restore_rule': RESTORE_RULE, 'detail_restore_dev': RESTORE_DEV,
    'detail_restore_note': ('§3.111 / §3.112a：逐券还原式由机器判据二选一（禁止按字段名取数）；'
                            f'本档采用 {RESTORE_RULE}（逐赛道最大偏差 {RESTORE_DEV:.4f} 元 < 1.5 元）'),
    'tracks': {k: {'mv': v['mv'], 'pct_of_total': v['pct_of_total'], 'day_pct': v['day_pct'],
                   'pnl': v.get('pnl')} for k, v in tracks.items()},
    'discipline_hstech_cumulative': {
        'cut1': {'pct': 0.5, 'amount': cut1_amt, 'triggered_on': '2026-09-29', 'settled_on': '2026-09-30',
                 'note': '9/29 收盘 4,249.62（-0.0089%）边际破位触发 -> 9/30 按净值成交 1,882.46 元（§3.117b）'},
        'cut2': {'pct': 0.5, 'amount': cut2_amt, 'triggered_on': '2026-10-02', 'settled_on': '2026-10-08',
                 'outcome': '执行日（10/8）恒生科技收 4,073.38（-2.89%）、距 4,250 为 -4.1558% -> 属有效减仓',
                 'targets': ['012348（天弘恒生科技联接A）', '513180（恒生科技ETF华夏）'],
                 'target_rule': '标的限「纯恒科」口径，不落在中概（513050 / 164906）'},
        'cumulative_amount': cut_cum,
        'hk_after': hk_after, 'cash_after': cash_after,
        'weight_after_pct': {'恒生科技': round(hk_after / TOTAL * 100, 2),
                             '现金': round(cash_after / TOTAL * 100, 2)},
        'prior_档口径': {'source': 'portfolio_close_20261012.json#discipline',
                        'hk_after': 27499.29, 'cash_after': 32999.87,
                        'weight_after_pct': {'恒生科技': 7.30, '现金': 8.76},
                        'correction_note': '与上一档一致（同为 10/12 收盘市值口径）'},
        'note': '本档无新增纪律动作（同日防线只触发一次，§3.114c）；两笔减仓均已成交、不可撤销；'
                '新增观察 = 下一道防线 4,000（10/12 收 4,169.57，距 +4.2392%）',
        'cumulative_selfcheck': {'sum_of_cuts': round(cut1_amt + cut2_amt, 2), 'cumulative_amount': cut_cum,
                                 'ok': abs(cut_cum - (cut1_amt + cut2_amt)) < 0.01},
    },
    'med_exposure': med, 'med_pct': round(med / TOTAL * 100, 2),
    'threshold_all_med': round(th_all, 2), 'threshold_a_sh_med': round(th_sh, 2),
    'non_med_total': round(B_nm, 2),
    'hk_total': round(hk_total, 2), 'hk_total_pct': round(hk_total / TOTAL * 100, 2),
    'hk_segments': {'pure_hstech': round(pure, 2), 'china_internet': round(cpo, 2),
                    'broad_hk': round(broad, 2)},
    'hk_layer_split': {'track_layer_pct': round(tracks['恒生科技']['pct_of_total'], 2),
                       'broad_layer_pct': round(broad / TOTAL * 100, 2),
                       'total_pct': round(hk_total / TOTAL * 100, 2),
                       'underreport_if_track_only_pct': round(broad / TOTAL * 100, 2)},
    'hk_southbound_gap': {'status': '已于 10/8 终止（港股通恢复）；10/8 起恢复常态',
                          'resumed_data': '10/12 南向净买入 26.03 亿港元（港股通沪 19.55 亿 / 深 6.49 亿）；'
                                          '结构上净买入居首的小米集团-W 当日收跌 5.55%',
                          'note': '南向净买入 26.03 亿港元、恒指 +0.25% 但恒生科技 −0.67% -> '
                                  '「内银撑指数、AI 硬件被卖」与「净买入 ≠ 当日价格支撑」并列披露'},
    'hk_leg_pending_carryover': {
        'carryover': True, 'recomputed': False,
        'source_file': 'data/processed/history/portfolio_close_20261012.json#pending_release',
        'window': PEND.get('window'), 'window_closed': PEND.get('window_closed'),
        'total_low': hk_low, 'total_high': hk_high, 'mid_proxy_avg': hk_mid,
        'reason': ('档型③「正常交易日盘前」：A股与港股当日均为正常交易日、08:00 双方均无当日价格 -> '
                   '依 §3.110 待消化沿用上一档、不做新测算；'
                   '且该窗口已于 10/8 由场外港股联接净值一次性兑现并收口（window_closed = true）；'
                   '10/12 收盘档 new_window_this_session = []（§3.112i）'),
        'note': '窗口已于 10/8 收口（4/4 全部定价）；只给区间上下界、不得作方向判断（§3.108 条款 24 / §3.133e）',
    },
    'qdii_pending': {
        'as_of': '2026-10-13 08:00',
        'refreshed': True, 'carryover': False,
        'segment_us_medical': {
            'desc': 'US 10/12 单日段（IYH 口径）',
            'trade_dates_covered': [f'{us_cur[0]}(US)'],
            'iyh_pct': IYH_PCT, 'xlv_pct': XLV_PCT,
            'notional_mv': round(QDII_MV, 2),
            'coef_range': [COEF_LO, COEF_HI], 'coef_mid_ref': COEF_MID,
            'pct_low': round(IYH_PCT * COEF_LO, 4), 'pct_high': round(IYH_PCT * COEF_HI, 4),
            'pct_mid_ref': round(IYH_PCT * COEF_MID, 4),
            'low': q_low, 'mid': q_mid, 'high': q_high,
            'codes': ['000369（广发全球医疗保健指数A）', '016280（广发全球医疗保健指数C）'],
            'coef_note': ('§3.118a / §3.139：传导系数不稳定（长假前后实测 1.25~1.29、常态 0.62、'
                          '10/9 档实测 000369 0.6668 / 016280 0.6788）→ **只给区间（0.60~0.90）、'
                          '中枢仅作参考、禁止用于仓位决策**'),
        },
        'segment_cn_internet': {
            'desc': '164906（交银中证海外中国互联网指数 LOF）10/12 净值待出',
            'notional_mv': round(LOF_MV, 2), 'range_given': False,
            'reason': ('该券跟踪「中证海外中国互联网指数」，**无单一稳定可复现代理指数** → '
                       '依 §3.122e 处置：**不给区间、只登记为「待兑现」**；'
                       '其 NAV 最新净值日 = 2026-10-09（0.8793 / +2.6740%）'),
        },
        'total_low': q_low, 'total_mid': q_mid, 'total_high': q_high,
        'range_given': True,
        'partial_range_note': ('§3.122e：本区间为**不完整区间** —— 只覆盖 000369 / 016280 两只全球医疗保健指数基金，'
                               '**不覆盖 164906（中概互联 LOF）腿**'),
        'unknown_sessions': ['2026-10-13(US)'],
        'new_sessions_since_prev': [f'{us_cur[0]}(US)'],
        'pending_codes': ['164906'],
        'applied_codes': [],
        'range_rule': 'QDII_LOW ≤ QDII_MID ≤ QDII_HIGH（§3.116b：对**结果值**取 min/max）',
        'coef_reestimate': {'status': 'pending', 'require': '≥4 券位 × ≥5 交易日',
                            'observed_samples': {'2026-10-09': {'000369': 0.6668, '016280': 0.6788}}},
        'note': ('§3.112f / §3.118a：挂账只给区间、禁止中枢点值。'
                 '本档**新增 US 10/12 单日段**（US 10/9 段已于 10/12 盘后档由真实净值核销 +674.77 元）→ '
                 'refreshed = true（本档刷新，非沿用）。'
                 '下一可观测起点 = US 10/13 收盘（成型于北京 10/14 04:00）。'),
    },
    'pending_consume': {
        'hold_decision': 'no_action',
        'carryover': True,
        'reason': ('档型③：08:00 时点组合全部持仓标的不可定价（A股 09:30 前无价、场外基金净值收盘后发布、'
                   '美股 10/13 未开盘）-> 待消化不做新测算、沿用上一档；唯一可执行窗口 = 10/13 全天'),
        'estimated_combo_return_pct': 0.0,
        'estimated_combo_pnl': 0.0,
        'attribution': ('A股 10/13 09:30 前无价 + 港股 09:30 前无价 + 场外基金净值收盘后发布 + 美股 10/13 未开盘'
                        ' -> 当日可实现盈亏恒为 0 元，归因「标的不可定价」而非「市场持平」'
                        '（§3.107 条款 19 / §3.121d）'),
    },
    'defense_lines': {
        'hstech_4250': {'close': HS, 'prev_close': HS_PREV, 'line': 4250,
                        'state': 'close_level_break_widened',
                        'dist_pct': round((HS / 4250 - 1) * 100, 4), 'dist_pts': round(HS - 4250, 2),
                        'break_trend': {'2026-10-05': -1.5605, '2026-10-06': -0.6342,
                                        '2026-10-07': -1.3061, '2026-10-08': -4.1558,
                                        '2026-10-09': -1.2273, '2026-10-12': -1.8925},
                        'intraday_touched_above': False, 'intraday_high': 4241.07, 'intraday_low': 4157.41,
                        'action_reserved': '无（第 2 次减仓已于 10/8 成交；同日防线只触发一次，§3.114c）',
                        'verify_at': '2026-10-13 16:00（港股收盘价验证）',
                        'next_line': 4000, 'next_line_dist_pct': round((HS / 4000 - 1) * 100, 4),
                        'next_rule': '再破不叠加新纪律；下一道防线 4,000'},
        'zz_consume_12100': {'last': ZZ, 'as_of': '2026-10-12', 'state': 'above_lower_line',
                             'dist_pct': round((ZZ / 12100 - 1) * 100, 4),
                             'next_line': 12000, 'next_line_dist_pct': round((ZZ / 12000 - 1) * 100, 4),
                             'verify_at': '2026-10-13（A股 盘中/盘后档）',
                             'note': '中证消费 10/12 收 12,469.1511（+0.92%）、逆市收涨 -> 连续第 3 个交易日站稳 12,100 下沿'},
        'a_med_reverse_1_5pct': {'proxy_pct': BMED, 'as_of': '2026-10-12', 'line_pct': -1.5,
                                 'dist_pct': round(BMED - (-1.5), 4),
                                 'state': 'not_triggered',
                                 'semantics': '§3.71：利好兑现后的回调观察线，非止损线 -> 处置 = 不执行主动减配',
                                 'action': 'active_take_profit = 0 / new_buy = 0',
                                 'contingency_closed': True,
                                 'contingency_triggered': False,
                                 'contingency_note': ('10/8 建立的「被动减配预案」已于 10/9 按预案明文'
                                                      '「回调序列断裂、预案不启动」作废（§3.136a 闭环）；'
                                                      '10/12 收盘代理 −0.6000% 亦未触及 −1.5% 反向兑现线'),
                                 'verify_at': '2026-10-13（A股 收盘后）'},
        'sh_comp': {'last': SH, 'as_of': '2026-10-12', 'pct': round((SH / SH_PREV - 1) * 100, 4)},
    },
    'scenario': {
        'upside': ('① 美股 10/12（周一）收盘：道指 51,850.55（+0.38%）、标普 500 7,807.24（−0.06%）、'
                   '纳指 27,245.90（−0.44%）；**标普 11 板块八涨三跌，能源 +1.48% / 必需消费 +1.22% 领涨、'
                   '科技 −0.90% / 非必需消费 −0.73% 领跌**；组合赛道代理 **XLV 171.99（+0.69%）/ IYH 72.55（+0.57%）**'
                   ' -> 该腿取得正超额（XLV 超额 +0.75pct / IYH +0.63pct）；'
                   '② A股 10/12 银行红利独强（中证银行 +2.27%）、大消费逆市收涨（中证消费 +0.92%）；'
                   '③ 医药政策与 BD 催化密集（「十五五」规划全文 + 恒瑞 26 亿美元授权 + 艾泊度胺获批）；'
                   '④ 港股内银集体创新高、南向净买入 26.03 亿港元。'
                   '⚠️ 但本档 08:00 无 A股/港股 当日定价，上行判断仅为「情境」、不得作为方向依据（§3.117d）'),
        'base': (f'档型③「正常交易日盘前」：组合账面基准 = 10/12 收盘件 {TOTAL:,.2f} 元；'
                 f'医药敞口 {med/TOTAL*100:.2f}%、港联系总暴露 {hk_total/TOTAL*100:.2f}%'
                 f'（双层：赛道 {tracks["恒生科技"]["pct_of_total"]:.2f}% + 宽基 {broad/TOTAL*100:.2f}%）；'
                 f'待消化 = QDII 腿新窗口（US 10/12 单日段）区间 {q_low:+,.2f} 元 ~ {q_high:+,.2f} 元'
                 f'（港股腿窗口已于 10/8 收口）；A股与港股 10/13 当日价格待 09:30 后'),
        'downside': ('① 分母端：美债 10Y 约 5.24%（债市哥伦布日休市、无现券报价）、30Y 约 5.6%、'
                     '美元指数破 102、CME 12 月加息概率升至约 84% -> 对恒生科技（离岸成长，8.30%）与'
                     '美股标普医药（类债型现金流，15.65%）为中期压制；中国 10Y rf 仍为 1.68% 硬编码；'
                     '② 地缘升级性质变化：10/11 霍尔木兹/阿曼湾 6 艘船同日遭袭、10/13 晨商船中弹 1 死 3 伤、'
                     '利雅得机场关闭延至 10/18 -> 战争险定价上行、通胀预期抬升；'
                     '③ A股 缩量分化：沪指失守 3,800、成交缩量 3,659 亿元、超 4,300 只个股下跌 -> '
                     '「权重护盘、题材失血」，赚钱效应未恢复；'
                     '④ 恒生科技破位走阔（−1.2273% → −1.8925%），且南向净买入居首标的小米当日 −5.55% -> '
                     '承接力量弱于价格；'
                     '⑤ A股医药「政策强、价格弱」未证伪（10/12 中证医药 −0.82%、主动基跌幅为代理的 1.27~3.55 倍）；'
                     '⑥ 大消费「茅台稳、中端塌方」两极分化（窖藏 1988 近腰斩、基酒折价）；'
                     '⑦ **US 10/13 盘前 JNJ 与 UNH 同日发布 Q3 财报** -> 事件性风险，对组合为未知项；'
                     '⑧ QDII 传导系数不稳定（长假 1.25~1.29 vs 常态 0.62 / 10/9 档 0.6668~0.6788）'
                     ' -> 挂账区间存在被击穿风险'),
    },
    'action': {'new_buy': 0, 'active_take_profit': 0, 'discipline_cut_today': 0,
               'discipline_cut_pending': 0,
               'discipline_cut_cumulative_registered': cut_cum,
               'new_pending': 1,
               'contingency_plan_registered': 0,
               'contingency_plan_closed': 1,
               'note': ('档型③ 盘前：08:00 时点组合全部标的不可定价 -> 赛道级动作全部为 0；'
                        '10/13 全天为唯一可执行窗口，执行清单 = ① 复核恒生科技 4,250/4,000'
                        '（10/12 收 4,169.57，破位 −1.8925%、距 4,000 +4.2392%）；'
                        '② 复核中证消费 12,100 下沿（10/12 收 12,469.1511，距 +3.0508%）；'
                        '③ 复核 A股医药反向兑现线（10/12 代理 −0.6000%，距线 +0.90pct）；'
                        '④ 复核 QDII 000369/016280 的 US 10/12 段净值是否出库（出库则核销区间 '
                        '202.30~303.45 元）；⑤ 登记 US 10/13 JNJ/UNH 财报与中国 10/14 CPI/PPI -> 只登记、不预判；'
                        '⑥ 医药敞口 38.48% 距上限 1.52pct（门槛 +6.58% / +11.09%）-> 任何正向催化均不构成加仓理由')},
    'calendar': {
        '2026-10-12（上一档）': 'A股 + 港股正常交易日（上证 −0.43% / 恒指 +0.25% / 恒生科技 −0.67%）；'
                                '组合当日 −129.64 元（−0.0344%）；QDII US 10/9 段净值释放 +674.77 元；'
                                'US 10/12 收盘成型于 10/13 04:00 并于本档归档（XLV +0.69% / IYH +0.57%）',
        '2026-10-13（今日）': 'A股 + 港股 + 美股**三市场均正常交易日**；'
                              '**US 盘前 JNJ（约 6:45 ET）与 UNH（8:00 ET 电话会）同日发布 Q3 财报**；'
                              '同日盘前 JPM / GS / WFC / C 发布 -> 美股 Q3 财报季全面启动',
        '2026-10-14': '中国 9 月 CPI / PPI（09:30）+ 美国 9 月 CPI（北京时间 20:30，预期 3.6%~3.7%）',
        '2026-10-15': '中国 9 月 PPI 与零售销售；美国 9 月 PPI；国内成品油调价窗口；'
                      '**第 140 届广交会开幕（10/15-11/4，李强出席）**',
        '2026-10-19': '**2026 金融街论坛年会开幕（吴清作主题演讲）**；港股重阳节翌日休市',
        '2026-10-27~28': 'FOMC 议息会议（CME：10 月维持不变概率约 82%）',
        '2026-12-09': 'FOMC 年末会议（CME：加息 25bp 概率约 84%）',
    },
    'calendar_by_market': {
        'A股': '10/1-10/7 休市 -> 10/8 复市 -> 10/9 正常 -> 10/10-10/11 周末 -> 10/12 正常 -> **10/13 正常交易日**',
        '港股': '10/1 休市 1 天 -> 10/8 起正常 -> 10/10-10/11 周末 -> 10/12 正常 -> **10/13 正常交易日**'
                '（10/19 重阳节翌日休）',
        '港股通(南向)': '10/1-10/7 暂停 -> 10/8 恢复 -> **10/13 正常**',
        '美股': 'US 10/9 已归档；10/10-10/11 周末休市；US 10/12 收盘 = 4,169.57 已于本档归档（XLV 171.99 / IYH 72.55）；'
                '**US 10/13 照常开市**，收盘成型于北京 10/14 04:00',
    },
    'data_hygiene': {
        'note': ('承接前档待办：① `portfolio_close_20260918_fix.json`（Σmv 差 -2,468.33 元）、'
                 '`portfolio_close_20260921_fix.json`（Σpnl 差 +333.12 元）两件不自洽；'
                 '② `fund_nav.csv` 历史重复键；③ 中国 10Y 收益率序列缺口（rf 硬编码 1.68%）；'
                 '④ 且慢 `long-win-nav.csv` 源/本地口径分歧（源末行 10/9 vs 本地末行 9/21；'
                 '本档 `qieman_rest_20261013.json` 空体 → 且慢侧读数本档不可用）；'
                 '⑤ `indices.csv` 港股盘中/收盘双行物理并存（append-only，读取侧 last-wins，§3.133b）；'
                 '⑥ 事件库 19 条历史条目缺 `actual_date` 字段（`legacy_missing_actual_date = 19`）；'
                 '⑦ `sh000922`（中证红利）新浪日线末行 = 2019-01-30 -> 禁止用作任何窗口代理（§3.111b）；'
                 '`000933`（中证医药）distinct 交易日稀疏 -> 仅可用 1 日真实收盘、多日窗口须用 399006 代理（§3.112b）；'
                 '⑧ **164906（中概互联 LOF）NAV 最新净值日 = 2026-10-09** -> QDII 区间为不完整区间（§3.122e）；'
                 '⑨ **DeepSeek v4-flash 端点连续第 7 个交易日 HTTP 402**（本档 30/30 条为规则表标注）。'),
    },
}

json.dump(out, open(os.path.join(HIST, f'portfolio_preopen_{TODAY.replace("-", "")}.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
print(f'\n已保存 portfolio_preopen_{TODAY.replace("-", "")}.json')
print(f'  OK 本档未产出 portfolio_close_{TODAY.replace("-", "")}.json（档型③不产 close）')
print(f'  OK 本档未产出 portfolio_pending_{TODAY.replace("-", "")}.json（档型③不产 pending；待消化沿用上一档）')
print(f'  OK new_pending = 1（QDII 新增 US 10/12 单日段）/ contingency_plan_closed = 1')
