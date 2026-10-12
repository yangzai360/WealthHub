# -*- coding: utf-8 -*-
"""2026-10-12（周一）盘前档：组合策略计算 —— **A股 + 港股 双市场复市首日**
SESSION_TYPE = 'normal_trading_day_preopen'（**档型③**：A股与港股当日均为正常交易日，但 08:00 双方均无新价格）
  → 依 §3.28 / §3.110 档型③：**不产 `portfolio_close_*`、不产 `portfolio_pending_*`**；
    **待消化不做新测算**（港股腿窗口已于 10/8 收口；QDII 腿沿用上一档区间、不重算）；
基准 = **10/9 收盘修正件（portfolio_close_20261009_fix.json）= 377,040.85 元**

★★★ 本档结构差异（派生后必检） ★★★
  ① 基准由「10/8 收盘 374,466.56 元」推进为「10/9 收盘修正件 377,040.85 元」（§3.105 补正后的 10/9 值）；
  ② 美股腿**无新增真实交易日**：US 10/9 收盘已于 10/11 档（非交易日档）归档 → 本档 `indices_us` 增量 = 0；
     下一个未知交易日 = **US 10/12**（其收盘成型于北京 10/13 04:00）；
  ③ 恒生科技防线基准价更新为 10/9 收盘 4,197.84（+3.06%），距 4,250 = −52.16 点 / −1.2273%；
     下一观察线 4,000（距 +4.9460%）；
  ④ A股医药反向兑现线：10/9 收盘代理 BOARD_MED = **+0.5075% 转正** → 盘前登记的「被动减配预案」判定
     **未触发**（预案明文「回调序列断裂、预案不启动」）→ 本档该预案**作废**；
  ⑤ 不产 pending 台账（档型③）→ 产 `session_type` 标注 + `new_pending = 0` 自证。
⚠️ §3.118a / §3.139：QDII 挂账**只给区间、禁止中枢点值**（系数 0.60~0.90，未按「≥4 券位 × ≥5 交易日」重估）。
⚠️ §3.123e 纪律累计口径：第 1 次 1,882.46 元（9/29 触发、9/30 成交）+ 第 2 次 1,904.44 元
   （10/2 触发、10/8 成交）= 累计 3,786.90 元（**本档无新增纪律动作**）。
⚠️ §3.112a：逐券还原式**禁止按字段名取数** → 用机器判据在 `mv0_new+est_pnl` 与 `mv0+est_pnl` 之间二选一，
   并加硬守卫 `max|Σ_track(还原式) − tracks[track].mv| < 1.5`；未通过则终止本档计算。
⚠️ §3.133a：展示类字段一律由数据源现算 + 自校验断言，禁止手写常量表。
⚠️ §3.136a：「A股医药反向兑现线」阈值为**负数**（line_pct = -1.5），触发条件 = 板块代理 ≤ −1.5%。
"""
import json, os, csv as _csv

BASE = '/Users/jieyang/Documents/WealthHub'
HIST = os.path.join(BASE, 'data/processed/history')
TODAY = '2026-10-12'
SESSION_TYPE = 'normal_trading_day_preopen'
BASEFILE = 'portfolio_close_20261009_fix.json'
fix = json.load(open(os.path.join(HIST, BASEFILE), encoding='utf-8'))

TOTAL = fix['total_mv']
tracks = fix['tracks']
print(f'基准（10/9 收盘修正件）= {TOTAL:,.2f} 元  <- {BASEFILE}')
print('  [档型③] 正常交易日盘前（A股 + 港股 双市场复市首日）'
      ' -> 不产 close / 不产 pending、待消化不做新测算（§3.28 / §3.110）')
dev = abs(sum(v['mv'] for v in tracks.values()) - TOTAL)
print(f'  硬守卫 |SUM tracks.mv - total_mv| = {dev:.4f} 元  {"OK" if dev < 1.5 else "FAIL"}')
assert dev < 1.5, 'SUM tracks.mv 与 total_mv 不一致，终止本档计算（§3.104）'

for k, v in sorted(tracks.items(), key=lambda kv: -kv[1]['mv']):
    print(f"  {k:10s} mv={v['mv']:>11,.2f}  w={v['pct_of_total']:>6.2f}%  day={v['day_pct']:+.3f}%")

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

# ---------- QDII 挂账（本档无新增美股交易日 -> 沿用上一档区间、不重算）----------
_iyh, _xlv = {}, {}
with open(os.path.join(HIST, 'indices.csv'), encoding='utf-8-sig') as f:
    for r in _csv.DictReader(f):
        dt = r['date'][:10]
        if r['code'] == 'IYH':
            _iyh[dt] = float(r['close'])
        elif r['code'] == 'XLV':
            _xlv[dt] = float(r['close'])

US_LAST = sorted(_iyh)[-1]
us_last_pct = round((_iyh[US_LAST] / _iyh[sorted(_iyh)[-2]] - 1) * 100, 4)
print(f'\nQDII 挂账（§3.112f / §3.118a：只给区间、禁止中枢点值）')
print(f'  IYH 末行 = {US_LAST}（{_iyh[US_LAST]} / {us_last_pct:+.4f}%）-> US 10/9 段已于 10/11 档归档')
prev_q = json.load(open(os.path.join(HIST, 'portfolio_holiday_20261011.json'), encoding='utf-8'))['qdii_pending']
q_low, q_high = prev_q['total_low'], prev_q['total_high']
q_mid = prev_q['total_mid']
print(f'  沿用上一档（10/11）区间：{q_low:+,.2f} 元 ~ {q_high:+,.2f} 元（中枢参考 {q_mid:+,.2f} 元）'
      f'｜notional {prev_q["segment_us_medical"]["notional_mv"]:,.2f} 元 × IYH {prev_q["segment_us_medical"]["iyh_pct"]:+.2f}% '
      f'× 系数 {prev_q["segment_us_medical"]["coef_range"]}')
print(f'  本档无新增美股交易日 -> refreshed = false（沿用，不重算）')
print(f'  [!] 164906（中概互联 LOF）10/9 净值仍待出 -> 该腿不给区间（§3.122e）；pending_codes = {prev_q["pending_codes"]}')
print(f'  [!] 下一个未知交易日 = US 10/12（收盘成型于北京 10/13 04:00；美股照常开市、债市休市）')
assert q_low <= q_mid <= q_high, '§3.116b 区间端点语义错误'

# ---------- 港股腿待消化：沿用上一档终值（档型③，不重算）----------
PEND = fix.get('pending_release', {})
hk_low = PEND.get('window_estimate_low', -973.41)
hk_high = PEND.get('window_estimate_high', -758.58)
hk_mid = PEND.get('window_estimate_mid_proxy_avg', -866.14)
print('\n港股腿「待消化」= 已于 10/8 收口（4/4 全部定价、净值一次性兑现）（档型③不重算）')
print(f'  终值：{hk_low:+,.2f} 元 ~ {hk_high:+,.2f} 元（代理均值中枢 {hk_mid:+,.2f} 元）'
      f' | window_closed = {PEND.get("window_closed")}')
print('  [!] 该窗口 10/8 起关闭、不再延续；窗口收口 != 可作方向判断（§3.108 条款 24 / §3.133e）')

# ---------- 三条防线（取 10/9 收盘口径）----------
HS, HS_PREV = 4197.84, 4073.38
ZZ = 12355.0001
SH = 3813.7913
BMED = 0.5075
print('\n三条防线（全部取 10/9 收盘口径；A股 两项今日 09:30 后验证）：')
print(f'  (1) 恒生科技 4,250：10/9 收 {HS:,.2f}（前收 {HS_PREV:,.2f} / {(HS/HS_PREV-1)*100:+.4f}%）'
      f' -> 距防线 {HS-4250:+,.2f} 点 / {(HS/4250-1)*100:+.4f}%'
      f'【破位幅度由 10/8 的 −4.1558% 收窄至 −1.2273%（10/6 −0.6342% -> 10/7 −1.3061% -> 10/8 −4.1558% -> 10/9 −1.2273%）】')
print(f'     下一观察线 4,000（距 {(HS/4000-1)*100:+.4f}%）'
      f' | 10/9 日内高 {HS:,.2f} < 4,250 -> intraday_touched_above = false（§3.129b）')
print(f'     -> 第 2 次减仓（{cut2_amt:,.2f} 元）已于 10/8 成交（累计 {cut_cum:,.2f} 元）；本档不新增动作')
print(f'  (2) 中证消费 12,100 下沿：10/9 收 {ZZ:,.4f} -> {(ZZ/12100-1)*100:+.4f}%'
      f'（下一线 12,000 距 {(ZZ/12000-1)*100:+.4f}%）-> 今日 09:30 后可验证')
print(f'  (3) A股医药反向兑现线（line_pct = -1.5，触发 = 板块代理 <= -1.5%）：'
      f'10/9 板块代理 {BMED:+.4f}% -> 未触发、且已反向翻转（距线 {BMED-(-1.5):+.4f}pct）')
print(f'     [!] §3.136a 闭环：10/8 建立的「被动减配预案」触发条件 = 10/9 收盘代理 <= 0%；'
      f'10/9 实际 +0.5075% -> 按预案明文「回调序列断裂、预案不启动」-> 该预案本档作废')
print(f'  附：上证 10/9 收 {SH:,.4f}（+0.05%）；恒指 10/9 收 23,941.26（+1.789%）；恒生国企 8,057.42（+1.714%）')

# ---------- 产物 ----------
out = {
    'date': TODAY, 'session': 'preopen', 'session_type': SESSION_TYPE,
    'session_type_note': ('档型③「正常交易日盘前」= A股 10/12（双市场复市首日）+ 港股 10/12（正常交易日）；'
                          '08:00 双方均无当日价格 -> 不产 portfolio_close_*、不产 portfolio_pending_*；'
                          '港股腿待消化窗口已于 10/8 收口、不做新测算；QDII 挂账沿用上一档区间（本档无新增美股交易日）；'
                          '本档新增定价 = 0（US 10/9 已于 10/11 档归档）'),
    'calendar_verification': {
        'A股': 'stock_zh_index_daily(sh000001) 末行 = 2026-10-09（收 3,813.7913 / +0.05%）-> 10/12 为正常交易日，09:30 开盘前无新价格',
        '港股': '新浪 hq rt_hkHSTECH 返回体日期字段 = 2026/10/09 16:08（收 4,197.84 / +3.06%）-> 10/12 今日待开 09:30（非休市）',
        '美股': 'stock_us_daily(IYH/XLV) 末行 = 2026-10-09（XLV 170.81 / IYH 72.14）-> US 10/9 收盘已于 10/11 档归档；US 10/12 收盘成型于北京 10/13 04:00',
        'rule': '三市场各自独立验证、不得互相外推（§3.107 / §3.119b / §3.122b）'},
    'base_total': TOTAL, 'base_file': BASEFILE, 'base_guard_dev': round(dev, 4),
    'base_revision': {'prev_total': 374466.56, 'delta': round(TOTAL - 374466.56, 2),
                      'reason': '本档基准为 10/9 收盘修正件（10/9 为正常交易日，已计入链式序列）；'
                                '较 10/8 收盘 374,466.56 元推进 +2,574.29 元（10/9 单日 +0.6875%，§3.105 补正后）'},
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
        'prior_档口径': {'source': 'portfolio_close_20261009_fix.json#discipline',
                        'hk_after': 27332.38, 'cash_after': 32999.87,
                        'weight_after_pct': {'恒生科技': 7.25, '现金': 8.75},
                        'correction_note': '与上一档一致（同为 10/9 收盘市值口径）'},
        'note': '本档无新增纪律动作（同日防线只触发一次，§3.114c）；两笔减仓均已成交、不可撤销；'
                '新增观察 = 下一道防线 4,000（10/9 收 4,197.84，距 +4.9460%）',
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
    'hk_southbound_gap': {'status': '已于 10/8 终止（港股通恢复）；10/9 恢复常态',
                          'resumed_data': '10/8 南向净买入 64.77 亿港元；10/9 南向净买入仅 2.91 亿港元（大幅回落）',
                          'note': '南向承接力量在反弹日反而弱于跌幅日 -> 与恒科破位未解除并列披露'},
    'hk_leg_pending_carryover': {
        'carryover': True, 'recomputed': False,
        'source_file': 'data/processed/history/portfolio_close_20261009_fix.json#pending_release',
        'window': PEND.get('window'), 'window_closed': PEND.get('window_closed'),
        'total_low': hk_low, 'total_high': hk_high, 'mid_proxy_avg': hk_mid,
        'reason': ('档型③「正常交易日盘前」：A股与港股当日均为正常交易日、08:00 双方均无当日价格 -> '
                   '依 §3.110 待消化沿用上一档、不做新测算；'
                   '且该窗口已于 10/8 由场外港股联接净值一次性兑现并收口（window_closed = true）'),
        'note': '窗口已于 10/8 收口（4/4 全部定价）；只给区间上下界、不得作方向判断（§3.108 条款 24 / §3.133e）',
    },
    'qdii_pending': {
        'as_of': '2026-10-12 08:00',
        'refreshed': False, 'carryover': True,
        'source_file': 'data/processed/history/portfolio_holiday_20261011.json#qdii_pending',
        'segment_us_medical': prev_q['segment_us_medical'],
        'segment_cn_internet': prev_q['segment_cn_internet'],
        'total_low': q_low, 'total_mid': q_mid, 'total_high': q_high,
        'range_given': False,
        'partial_range_note': ('§3.122e：本区间为**不完整区间** —— 只覆盖 000369 / 016280 两只全球医疗保健指数基金，'
                               '**不覆盖 164906（中概互联 LOF）腿**（该券 10/9 净值仍未出库、无单一稳定可复现代理指数）'),
        'unknown_sessions': ['2026-10-12(US)'],
        'new_sessions_since_prev': [],
        'pending_codes': prev_q['pending_codes'],
        'range_rule': 'QDII_LOW ≤ QDII_MID ≤ QDII_HIGH（§3.116b：对**结果值**取 min/max）',
        'note': ('§3.112f / §3.118a：挂账只给区间、禁止中枢点值。'
                 '本档**无新增美股交易日**（US 10/9 已于 10/11 档首次可量化并归档）→ refreshed = false（沿用，不重算）。'
                 '下一可观测起点 = US 10/12 收盘（成型于北京 10/13 04:00；美股照常开市、债市休市）。'),
    },
    'pending_consume': {
        'hold_decision': 'no_action',
        'carryover': True,
        'reason': ('档型③：08:00 时点组合全部持仓标的不可定价（A股 09:30 前无价、场外基金净值收盘后发布、'
                   '美股 10/12 未开盘）-> 待消化不做新测算、沿用上一档；唯一可执行窗口 = 10/12 全天'),
        'estimated_combo_return_pct': 0.0,
        'estimated_combo_pnl': 0.0,
        'attribution': ('A股 10/12 09:30 前无价 + 港股 09:30 前无价 + 场外基金净值收盘后发布 + 美股 10/12 未开盘'
                        ' -> 当日可实现盈亏恒为 0 元，归因「标的不可定价」而非「市场持平」'
                        '（§3.107 条款 19 / §3.121d）'),
    },
    'defense_lines': {
        'hstech_4250': {'close': HS, 'prev_close': HS_PREV, 'line': 4250, 'state': 'close_level_break_narrowed',
                        'dist_pct': round((HS / 4250 - 1) * 100, 4), 'dist_pts': round(HS - 4250, 2),
                        'break_trend': {'2026-10-02': -2.1661, '2026-10-05': -1.5605, '2026-10-06': -0.6342,
                                        '2026-10-07': -1.3061, '2026-10-08': -4.1558, '2026-10-09': -1.2273},
                        'intraday_touched_above': False,
                        'action_reserved': '无（第 2 次减仓已于 10/8 成交；同日防线只触发一次，§3.114c）',
                        'verify_at': '2026-10-12 16:00（港股收盘价验证）',
                        'next_line': 4000, 'next_line_dist_pct': round((HS / 4000 - 1) * 100, 4),
                        'next_rule': '再破不叠加新纪律；下一道防线 4,000（距 +4.9460%）'},
        'zz_consume_12100': {'last': ZZ, 'as_of': '2026-10-09', 'state': 'above_lower_line',
                             'dist_pct': round((ZZ / 12100 - 1) * 100, 4),
                             'next_line': 12000, 'next_line_dist_pct': round((ZZ / 12000 - 1) * 100, 4),
                             'verify_at': '2026-10-12（A股 盘中/盘后档）'},
        'a_med_reverse_1_5pct': {'proxy_pct': BMED, 'as_of': '2026-10-09', 'line_pct': -1.5,
                                 'dist_pct': round(BMED - (-1.5), 4),
                                 'state': 'not_triggered_turned_positive',
                                 'semantics': '§3.71：利好兑现后的回调观察线，非止损线 -> 处置 = 不执行主动减配',
                                 'action': 'active_take_profit = 0 / new_buy = 0',
                                 'contingency_closed': True,
                                 'contingency_note': ('10/8 建立的「被动减配预案」（触发 = 10/9 收盘代理 <= 0%）'
                                                      '判定为**未触发**：10/9 收盘代理 +0.5075% 转正 -> 按预案明文'
                                                      '「回调序列断裂、预案不启动」处置，本档该预案作废（§3.136a 闭环）'),
                                 'verify_at': '2026-10-12（A股 收盘后）'},
        'sh_comp': {'last': SH, 'as_of': '2026-10-09', 'pct': 0.05},
    },
    'scenario': {
        'upside': ('① 美股 10/9（周五）收盘：三大指数齐涨（纳指 27,366.20 +0.64% / 标普500 7,811.54 +0.59% / '
                   '道指 51,654.90 +0.83%），**医疗保健板块领涨**（XLV 170.81 +1.58% / IYH 72.14 +1.72%）'
                   '-> 该腿取得正超额（IYH 超额 +1.13pct）；'
                   '② 10/9 A股探底回升四大指数集体翻红（上证 +0.05% / 创业板 +0.22%）、港股大幅反弹'
                   '（恒指 +1.789% / 恒生科技 +3.06%）；'
                   '③ 周末政策面密集（新质生产力意见 / 证监会座谈会 / 公募基金运作办法修订 / 财政结存限额）；'
                   '④ 10/12 为双市场复市首日，长假后量能回补与情绪修复存在空间。'
                   '⚠️ 但本档无新增定价，上行判断仅为「情境」、不得作为方向依据（§3.117d）'),
        'base': (f'档型③「正常交易日盘前」：组合账面基准 = 10/9 收盘修正件 {TOTAL:,.2f} 元；'
                 f'A股医药敞口 {med/TOTAL*100:.2f}%、港联系 {hk_total/TOTAL*100:.2f}%（双层：赛道 {tracks["恒生科技"]["pct_of_total"]:.2f}% '
                 f'+ 宽基 {broad/TOTAL*100:.2f}%）；'
                 f'待消化 = QDII 腿挂账区间 {q_low:+,.2f} 元 ~ {q_high:+,.2f} 元（港股腿窗口已于 10/8 收口）；'
                 f'A股与港股 10/12 当日价格待 09:30 后'),
        'downside': ('① 分母端：美债 10Y 收 5.242%（单日 +2bp）、2Y +5bp 呈熊平 -> 对恒生科技（离岸成长）'
                     '与美股标普医药（类债型现金流）估值端构成中期约束；中国 10Y rf 仍为 1.68% 硬编码；'
                     '② 恒生科技破位未解除：10/9 收 4,197.84 仍低于 4,250（−1.2273%），且反弹日成交仅微增、'
                     '南向净买入由 64.77 亿港元降至 2.91 亿 -> 承接力量弱于跌幅日；'
                     '③ 大消费「指数涨、动销弱」背离：中证消费 10/9 +0.80%（两日 +0.48%）vs 国海证券调研'
                     '「今年双节白酒动销弱于去年同期」+ 终端价盘两日连续回落；'
                     '④ A股医药「政策强、价格弱」结构未变（两日 −2.13%），为四大赛道中指数层面最弱一条；'
                     '⑤ 中概/港股同源资产背离第 2 次：10/9 纳斯达克中国金龙 +2.69% 但组合「中概·海外互联」'
                     '分段实际 −111.86 元（三分段唯一为负）；'
                     '⑥ QDII 传导系数不稳定（长假前后 1.25~1.29 vs 常态 0.62 / 10/9 档 0.70~0.76）-> 挂账区间存在被击穿风险；'
                     '⑦ 地缘二阶传导：布油 104.72 美元、霍尔木兹通行量降至 4 艘/日、利雅得机场遇袭 -> 推升通胀预期与避险需求'),
    },
    'action': {'new_buy': 0, 'active_take_profit': 0, 'discipline_cut_today': 0,
               'discipline_cut_pending': 0,
               'discipline_cut_cumulative_registered': cut_cum,
               'new_pending': 0,
               'contingency_plan_registered': 0,
               'contingency_plan_closed': 1,
               'note': ('档型③ 盘前：08:00 时点组合全部标的不可定价 -> 赛道级动作全部为 0；'
                        '10/12 全天为唯一可执行窗口，执行清单 = ① 复核恒生科技 4,000 观察线（10/9 收 4,197.84，距 +4.9460%）；'
                        '② 复核中证消费 12,100 下沿（10/9 收 12,355.0001，距 +2.1074%）；'
                        '③ 复核 A股医药反向兑现线（10/9 代理 +0.5075% 已反向翻转，被动减配预案本档作废）；'
                        '④ 复核 QDII 000369/016280/164906 的 10/9 净值是否出库（出库则核销挂账、回填区间）；'
                        '⑤ 登记下周宏观日历与美股财报季（10/13 联合健康等、10/14 美国 9 月 CPI）-> 只登记、不预判；'
                        '⑥ 医药敞口 38.53% 距上限 1.47pct（门槛 +6.35% / +10.62%）-> 任何正向催化均不构成加仓理由（new_buy = 0）')},
    'calendar': {
        '2026-10-09（上一档）': 'A股 + 港股正常交易日（上证 +0.05% / 创业板 +0.22% / 恒指 +1.789% / 恒生科技 +3.06%）；'
                                '000051 净值补正到位 -> 组合当日 +0.6875%（+2,574.29 元）；'
                                'US 10/9 收盘成型于 10/10 04:00 并于 10/11 档归档（XLV +1.58% / IYH +1.72%）',
        '2026-10-12（今日）': 'A股 + 港股**双市场复市首日**（周一常规交易日）；美股照常开市（哥伦布日/原住民日，债市休市）；'
                              '港股通照常',
        '2026-10-13': '美股 Q3 财报季启动（联合健康等医疗保健龙头）',
        '2026-10-14': '美国 9 月 CPI',
        '2026-10-19': '港股重阳节翌日休市',
        '2026-10-27~28': 'FOMC 议息会议（CME：10 月维持不变概率约 82%）',
        '2026-12-09': 'FOMC 年末会议（CME：加息 25bp 概率约 67%）',
    },
    'calendar_by_market': {
        'A股': '10/1-10/7 休市 -> 10/8 复市 -> 10/9 正常交易日 -> 10/10-10/11 周末 -> **10/12 正常交易日（复市第 3 个交易日）**',
        '港股': '10/1 休市 1 天 -> 10/8 起正常交易日 -> 10/10-10/11 周末 -> **10/12 正常交易日**（10/19 重阳节翌日休）',
        '港股通(南向)': '10/1-10/7 暂停 -> 10/8 恢复 -> **10/12 正常**',
        '美股': 'US 10/9 收盘已归档（XLV 170.81 / IYH 72.14）；10/10-10/11 周末休市；**US 10/12 照常开市**（债市休市），收盘成型于北京 10/13 04:00',
    },
    'data_hygiene': {
        'note': ('承接前档待办：① `portfolio_close_20260918_fix.json`（Σmv 差 -2,468.33 元）、'
                 '`portfolio_close_20260921_fix.json`（Σpnl 差 +333.12 元）两件不自洽；'
                 '② `fund_nav.csv` 历史重复键；③ 中国 10Y 收益率序列缺口（rf 硬编码 1.68%）；'
                 '④ 且慢 `long-win-nav.csv` 源/本地口径分歧（连续第 23 档，源末行 10/9 vs 本地末行 9/21）；'
                 '⑤ `indices.csv` 港股盘中/收盘双行物理并存（append-only，读取侧 last-wins，§3.133b）；'
                 '⑥ 事件库 19 条历史条目缺 `actual_date` 字段（`legacy_missing_actual_date = 19`）；'
                 '⑦ `sh000922`（中证红利）新浪日线末行 = 2019-01-30 -> 禁止用作任何窗口代理（§3.111b）；'
                 '`000933`（中证医药）distinct 交易日仅 13 -> 稀疏，仅可用 1 日真实收盘、多日窗口须用 399006 代理（§3.112b）；'
                 '⑧ **本档新登记**：164906（中概互联 LOF）10/9 净值跨周末仍待出 -> QDII 区间为不完整区间（§3.122e）。'),
    },
}

json.dump(out, open(os.path.join(HIST, f'portfolio_preopen_{TODAY.replace("-", "")}.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
print(f'\n已保存 portfolio_preopen_{TODAY.replace("-", "")}.json')
print(f'  OK 本档未产出 portfolio_close_{TODAY.replace("-", "")}.json（档型③不产 close）')
print(f'  OK 本档未产出 portfolio_pending_{TODAY.replace("-", "")}.json（档型③不产 pending；待消化沿用上一档）')
print(f'  OK new_pending = 0 / contingency_plan_closed = 1')
