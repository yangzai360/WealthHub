# -*- coding: utf-8 -*-
"""2026-10-15（周四）盘前档：组合策略计算 —— **A股/港股/美股三市场均为正常交易日**
SESSION_TYPE = 'normal_trading_day_preopen'（**档型③**：A股与港股当日均为正常交易日，但 08:00 双方均无新价格）
  → 依 §3.28 / §3.110 档型③：**不产 `portfolio_close_*`、不产 `portfolio_pending_*`**；
    **待消化不做新测算**（港股腿窗口已于 10/8 收口；QDII 腿**本档新增 US 10/14 单日段** → 给新区间）；
基准 = **10/14 收盘修正件（portfolio_close_20261014_fix.json）= 371,790.99 元**

★★★ 本档结构差异（派生后必检） ★★★
  ① 基准由「10/14 盘后档原值 372,383.85 元」**修正**为「10/14 收盘修正件 **371,790.99 元**」
     （**§3.140a 跨档补正 −592.86 元**：002708 大摩健康 10/14 净值 1.876 昨档未出库、本档 08:00 补正）；
     10/14 单日修正后 = **−2,598.48 元 / −0.6941%**；
     ⚠️ **该券连续第 2 个交易日同机制迟滞**（10/13 档同券亦于本档系列补正 −358.50 元）→ 登记为稳定特征、须逐档兜底复抓；
  ② 美股腿**本档有新增真实交易日**：**US 10/14 收盘成型于北京 10/15 04:00**
     → `indices.csv` **+8 行**（XLV 173.96 / IYH 73.16 等）；**下一未知交易日 = US 10/15（收盘成型于北京 10/16 04:00）**；
  ③ 恒生科技防线基准价更新为 10/14 收盘 **4,174.47**（+0.91%），距 4,250 = **−1.7772%**（较 10/13 的 −2.6675% **收窄 0.8903pct**）；
     下一观察线 4,000（距 **+4.3618%**）；
  ④ 中证消费 10/14 收 **12,362.5056**（+0.27%）→ 距 12,100 下沿 **+2.1695%**、距 12,000 **+3.0209%**；
  ⑤ A股医药板块代理 10/14 = **−0.85%** → 距反向兑现线（−1.5%）**+0.65pct**；被动减配预案维持作废（10/9 已按明文作废）；
  ⑥ **QDII 挂账给出「US 10/14 单日段」区间**：notional 58,690.46 元（§3.144a：取 `tracks['美股标普医药'].mv`）
     × IYH **+2.3360%** × 系数 0.60~0.90 → 区间 **+822.61 元 ~ +1,233.91 元**；
     **164906（中概互联 LOF）腿仍不给区间**（该券最新净值日 10/13、10/14 净值未出库）。
  ⑦ 不产 pending 台账（档型③）→ 产 `session_type` 标注 + `new_pending` 自证（**本档 new_pending = 1**）。
⚠️ §3.118a / §3.139：QDII 挂账**只给区间、禁止中枢点值**（系数 0.60~0.90，未按「≥4 券位 × ≥5 交易日」重估）。
⚠️ §3.123e 纪律累计口径：第 1 次 1,882.46 元（9/29 触发、9/30 成交）+ 第 2 次 1,904.44 元
   （10/2 触发、10/8 成交）= 累计 3,786.90 元（**本档无新增纪律动作**）。
⚠️ §3.112a / §3.111：逐券还原式**禁止按字段名取数** → 用机器判据在 `mv0_new+est_pnl` 与 `mv0+est_pnl` 之间二选一，
   并加硬守卫 `max|Σ_track(还原式) − tracks[track].mv| < 1.5`；未通过则终止本档计算。
   ⚠️ **本档基准为 `_fix` 件**：其 `detail[].mv` 语义未经逐档核对（§3.111 条款 30/33），故机器判据为**强制**步骤。
⚠️ §3.133a：展示类字段一律由数据源现算 + 自校验断言，禁止手写常量表。
"""
import json, os, csv as _csv

BASE = '/Users/jieyang/Documents/WealthHub'
HIST = os.path.join(BASE, 'data/processed/history')
TODAY = '2026-10-15'
SESSION_TYPE = 'normal_trading_day_preopen'
BASEFILE = 'portfolio_close_20261014_fix.json'
fix = json.load(open(os.path.join(HIST, BASEFILE), encoding='utf-8'))

TOTAL = fix['total_mv']
tracks = fix['tracks']
print(f'基准（10/14 收盘修正件）= {TOTAL:,.2f} 元  <- {BASEFILE}')
print('  [档型③] 正常交易日盘前（A股 + 港股 + 美股 三市场正常交易日）'
      ' -> 不产 close / 不产 pending、待消化不做新测算（§3.28 / §3.110）')
dev = abs(sum(v['mv'] for v in tracks.values()) - TOTAL)
print(f'  硬守卫 |SUM tracks.mv - total_mv| = {dev:.4f} 元  {"OK" if dev < 1.5 else "FAIL"}')
assert dev < 1.5, 'SUM tracks.mv 与 total_mv 不一致，终止本档计算（§3.104）'
assert abs(sum(v['pnl'] for v in tracks.values()) - fix['est_total_pnl']) < 1.5, \
    '§3.109 条款 26 硬守卫失败：Σ tracks.pnl != est_total_pnl'

for k, v in sorted(tracks.items(), key=lambda kv: -kv[1]['mv']):
    print(f"  {k:10s} mv={v['mv']:>11,.2f}  w={100.0*v['mv']/TOTAL:>6.2f}%  day={v['day_pct']:+.3f}%  pnl={v['pnl']:+.2f}")

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
print(f'  赛道层「恒生科技」{tracks["恒生科技"]["mv"]:,.2f} 元 = {100.0*tracks["恒生科技"]["mv"]/TOTAL:.2f}%'
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
      f'（{100.0*tracks["恒生科技"]["mv"]/TOTAL:.2f}% -> {hk_after/TOTAL*100:.2f}%）')
print(f'  现金     {tracks["现金"]["mv"]:,.2f} -> {cash_after:,.2f}'
      f'（{100.0*tracks["现金"]["mv"]/TOTAL:.2f}% -> {cash_after/TOTAL*100:.2f}%）')
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


US_LAST_US, us_cur, us_prev = last2('IYH')          # US 10/14 = 本档新增
IYH_PCT = round((us_cur[1] / us_prev[1] - 1) * 100, 4)
_xds = sorted(_ser['XLV'])
XLV_PCT = round((_ser['XLV'][_xds[-1]] / _ser['XLV'][_xds[-2]] - 1) * 100, 4)
print(f'\n美股本档新增真实收盘：IYH {us_cur[0]} {us_cur[1]}（{IYH_PCT:+.4f}%）'
      f' | XLV {_xds[-1]} {_ser["XLV"][_xds[-1]]}（{XLV_PCT:+.4f}%）')

# ---------- QDII 挂账（本档新增 US 10/14 单日段 → 给区间） ----------
# §3.144a：notional 必须取 tracks[].mv，禁止用 detail[].mv（陈旧继承值）；并加双向硬守卫自证陷阱存在。
QDII_MV_TRACK = float(tracks['美股标普医药']['mv'])
QDII_MV_DETAIL_RESTORED = round(sum(restore_val(d, RESTORE_RULE)
                                   for d in fix['detail'] if d['track'] == '美股标普医药'), 2)
QDII_MV_DETAIL_STALE = round(sum(float(d['mv']) for d in fix['detail']
                                 if d['track'] == '美股标普医药'), 2)
dev_restored = abs(QDII_MV_DETAIL_RESTORED - QDII_MV_TRACK)
print(f'\n[§3.144a] QDII notional 硬守卫：tracks[].mv = {QDII_MV_TRACK:,.2f} 元 ｜ '
      f'逐券还原式（{RESTORE_RULE}）= {QDII_MV_DETAIL_RESTORED:,.2f} 元（dev {dev_restored:.2f} 元）｜ '
      f'detail[].mv（陈旧继承值）= {QDII_MV_DETAIL_STALE:,.2f} 元')
assert dev_restored < 1.5, (
    f'[§3.144a] 逐券还原式 {QDII_MV_DETAIL_RESTORED:,.2f} != tracks[].mv {QDII_MV_TRACK:,.2f} → 终止')
assert abs(QDII_MV_DETAIL_STALE - QDII_MV_TRACK) > 1.5, (
    '[§3.144a 自证失败] detail[].mv 与 tracks[].mv 本应相差 > 1.5 元（陈旧继承值陷阱），'
    f'实测差 {abs(QDII_MV_DETAIL_STALE - QDII_MV_TRACK):.2f} 元 → 需人工复核 detail 语义')
QDII_MV = QDII_MV_TRACK
LOF_MV = round(sum(restore_val(d, RESTORE_RULE)
                   for d in fix['detail']
                   if ''.join(c for c in str(d.get('code', '')) if c.isdigit())[-6:] == '164906'), 2)
COEF_LO, COEF_MID, COEF_HI = 0.60, 0.72, 0.90
# §3.144c：与新闻台账条目（第 26 条 / `build_news_preopen_20261015.py` 区间自证）**必须同口径**。
# 口径细则：**两步取整** —— 先按 notional 规模把「单日敞口金额」取到分，再乘系数区间并取到分。
# ⚠️ 本档主口径取 **IYH 四位小数精确值**（+2.3360%）：新闻脚本已按精确值落盘（+822.61 ~ +1,233.91），
#    若本脚本改用两位小数（+2.34%）会产出**两个字面量**（§3.144c 硬约束）；
#    ⚠️ 与 10/14 档取法**相反**（该档 IYH = −1.4611%、主口径取两位小数 −1.46%）→ 取整路径**由新闻脚本锚定**。
IYH_PCT_PRECISE = IYH_PCT
IYH_PCT_2DP = round(IYH_PCT, 2)
_amt_1x = round(QDII_MV * IYH_PCT_PRECISE / 100, 2)
_a = round(_amt_1x * COEF_LO, 2)
_b = round(_amt_1x * COEF_HI, 2)
q_low, q_high = min(_a, _b), max(_a, _b)
q_mid = round(_amt_1x * COEF_MID, 2)
_amt_1x_2dp = round(QDII_MV * IYH_PCT_2DP / 100, 2)
_q_a2 = round(_amt_1x_2dp * COEF_LO, 2)
_q_b2 = round(_amt_1x_2dp * COEF_HI, 2)
q_low_2dp, q_high_2dp = min(_q_a2, _q_b2), max(_q_a2, _q_b2)
# §3.144c 硬守卫：本脚本区间必须与新闻脚本落盘区间一致
_news_low, _news_high = 822.61, 1233.91
assert abs(q_low - _news_low) < 0.01 and abs(q_high - _news_high) < 0.01, (
    '§3.144c 硬守卫失败：本脚本区间 %s~%s 与新闻脚本落盘区间 %s~%s 不一致 -> 终止'
    % (q_low, q_high, _news_low, _news_high))
print(f'\nQDII 挂账（§3.112f / §3.118a：只给区间、禁止中枢点值）')
print(f'  notional（= tracks["美股标普医药"].mv，§3.144a）= {QDII_MV:,.2f} 元')
print(f'  本档新增美股交易日 = US {us_cur[0]}（IYH {IYH_PCT:+.4f}% / XLV {XLV_PCT:+.4f}%）-> 新窗口可量化')
print(f'  单日敞口 = round({QDII_MV:,.2f} × {IYH_PCT_PRECISE}% , 2) = {_amt_1x:+,.2f} 元（与新闻脚本自证同值）')
print(f'  区间：{q_low:+,.2f} 元 ~ {q_high:+,.2f} 元（中枢参考 {q_mid:+,.2f} 元，系数 {COEF_LO}~{COEF_HI}，'
      f'IYH 取精确值 {IYH_PCT_PRECISE}%，与新闻台账条目一致）')
print(f'  [交叉参考] 以 IYH 两位小数 {IYH_PCT_2DP}% 计算 = {q_low_2dp:+,.2f} 元 ~ {q_high_2dp:+,.2f} 元'
      f'（差 {abs(q_low - q_low_2dp):.2f} 元，不替换主口径）')
_xlv_a = round(QDII_MV * XLV_PCT / 100 * COEF_LO, 2)
_xlv_b = round(QDII_MV * XLV_PCT / 100 * COEF_HI, 2)
print(f'  [交叉参考] 以 XLV {XLV_PCT:+.4f}% 为分母 = '
      f'{min(_xlv_a, _xlv_b):+,.2f} 元 ~ {max(_xlv_a, _xlv_b):+,.2f} 元'
      f'（仅作交叉参考、不替换主口径，§3.145c：主口径分母 = IYH）')
print(f'  [!] 164906（中概互联 LOF）notional {LOF_MV:,.2f} 元、最新净值日 2026-10-13（10/14 净值未出库）-> 该腿不给区间（§3.122e）')
print(f'  [!] 下一未知交易日 = US 10/15（收盘成型于北京 10/16 04:00）')
assert q_low <= q_mid <= q_high, '§3.116b 区间端点语义错误'

# ---------- 港股腿待消化：沿用上一档终值（档型③，不重算） ----------
PEND = fix.get('pending_release', {})
hk_low = PEND.get('window_estimate_low', -973.41)
hk_high = PEND.get('window_estimate_high', -758.58)
hk_mid = PEND.get('window_estimate_mid_proxy_avg', -866.14)
print('\n港股腿「待消化」= 已于 10/8 收口（4/4 全部定价、净值一次性兑现）（档型③不重算）')
print(f'  终值：{hk_low:+,.2f} 元 ~ {hk_high:+,.2f} 元（代理均值中枢 {hk_mid:+,.2f} 元）'
      f' | window_closed = {PEND.get("window_closed")}')
print('  [!] 10/14 收盘档 new_window_this_session = []（正常交易日按当日真实净值逐券定价）→ 无新增待消化项（§3.112i）')

# ---------- 三条防线（取 10/14 收盘口径；A股/港股 由 indices.csv 现算，防御细节引用 `_fix` 件自证） ----------
HS_DS = sorted(_ser['HSTECH'])
HS = _ser['HSTECH'][HS_DS[-1]]
HS_PREV = _ser['HSTECH'][HS_DS[-2]]
ZZ_DS = sorted(_ser['000932'])
ZZ = _ser['000932'][ZZ_DS[-1]]
ZZ_PREV = _ser['000932'][ZZ_DS[-2]]
SH_DS = sorted(_ser['000001'])
SH = _ser['000001'][SH_DS[-1]]
SH_PREV = _ser['000001'][SH_DS[-2]]
BMED = fix['defense']['a_med_reverse_1_5pct']['proxy_pct']
_DEF = fix['defense']
# 自证：现算值与 `_fix` 件内防御字段一致（防止两处数字分裂，§3.144c）
assert abs(HS - float(_DEF['hstech_4250']['close'])) < 0.02, '恒生科技收盘价与 _fix 件不一致'
assert abs(ZZ - float(_DEF['zz_consume_12100']['last'])) < 0.02, '中证消费收盘与 _fix 件不一致'
assert abs((HS / 4250 - 1) * 100 - float(_DEF['hstech_4250']['dist_pct'])) < 0.01, '恒生科技距防线 % 与 _fix 件不一致'
assert abs((ZZ / 12100 - 1) * 100 - float(_DEF['zz_consume_12100']['dist_pct'])) < 0.01, '中证消费距下沿 % 与 _fix 件不一致'
print('\n三条防线（全部取 10/14 收盘口径；A股 两项今日 09:30 后验证）：')
print(f'  (1) 恒生科技 4,250：10/14 收 {HS:,.2f}（前收 {HS_PREV:,.2f} / {(HS/HS_PREV-1)*100:+.4f}%）'
      f' -> 距防线 {HS-4250:+,.2f} 点 / {(HS/4250-1)*100:+.4f}%'
      f'【破位幅度由 10/13 的 −2.6675% **收窄至 −1.7772%**（收窄 0.8903pct，单日 +0.91%）】')
print(f'     下一观察线 4,000（距 {(HS/4000-1)*100:+.4f}%）'
      f' | 10/14 日内高 {_DEF["hstech_4250"]["intraday_high"]:,} < 4,250 -> intraday_touched_above = false（§3.129b）')
print(f'     -> 第 2 次减仓（{cut2_amt:,.2f} 元）已于 10/8 成交（累计 {cut_cum:,.2f} 元）；本档不新增动作')
print(f'  (2) 中证消费 12,100 下沿：10/14 收 {ZZ:,.4f}（前收 {ZZ_PREV:,.4f} / {(ZZ/ZZ_PREV-1)*100:+.4f}%）'
      f' -> {(ZZ/12100-1)*100:+.4f}%'
      f'（下一线 12,000 距 {(ZZ/12000-1)*100:+.4f}%）-> 今日 09:30 后可验证')
print(f'  (3) A股医药反向兑现线（line_pct = -1.5，触发 = 板块代理 <= -1.5%）：'
      f'10/14 板块代理 {BMED:+.4f}% -> 未触发（距线 {BMED-(-1.5):+.4f}pct）')
print(f'     [!] §3.136a：10/8 建立的「被动减配预案」已于 10/9 按明文「回调序列断裂、预案不启动」作废，本档维持作废')
_HSI = _ser.get('HSI', {})
_HSCEI = _ser.get('HSCEI', {})
print(f'  附：上证 10/14 收 {SH:,.4f}（{(SH/SH_PREV-1)*100:+.4f}%）；恒指 10/14 收 '
      f'{_HSI.get(sorted(_HSI)[-1], "n/a")}；恒生国企 10/14 收 {_HSCEI.get(sorted(_HSCEI)[-1], "n/a")}')

# ---------- 产物 ----------
out = {
    'date': TODAY, 'session': 'preopen', 'session_type': SESSION_TYPE,
    'session_type_note': ('档型③「正常交易日盘前」= A股 10/15（正常交易日）+ 港股 10/15（正常交易日）+ '
                          '美股 10/15（正常交易日）；08:00 A股/港股均无当日价格 -> 不产 portfolio_close_*、'
                          '不产 portfolio_pending_*；港股腿待消化窗口已于 10/8 收口、不做新测算；'
                          'QDII 挂账**本档新增 US 10/14 单日段**（区间 +822.61 元 ~ +1,233.91 元）；'
                          '本档新增真实定价 = US 10/14 收盘（indices.csv +8 行）；'
                          '基准 = 10/14 收盘**修正件**（§3.140a 跨档补正 −592.86 元，同一券连续第 2 日同机制迟滞）'),
    'calendar_verification': {
        'A股': 'stock_zh_index_daily(sh000001) 末行 = 2026-10-14（收 3,767.2271 / −0.8850%）-> 10/15 为正常交易日，09:30 开盘前无新价格',
        '港股': '新浪 hq rt_hkHSTECH 返回体日期字段 = 2026/10/14 16:08（收 4,174.47 / +0.91%）-> 10/15 今日待开 09:30（非休市）',
        '美股': 'stock_us_daily(IYH/XLV) 末行 = 2026-10-14（XLV 173.96 / IYH 73.16）-> US 10/14 收盘已于本档（10/15 盘前）写入 indices.csv；US 10/15 收盘成型于北京 10/16 04:00',
        'rule': '三市场各自独立验证、不得互相外推（§3.107 / §3.119b / §3.122b）'},
    'base_total': TOTAL, 'base_file': BASEFILE, 'base_guard_dev': round(dev, 4),
    'base_revision': {'prev_total': 372383.85, 'delta': round(TOTAL - 372383.85, 2),
                      'reason': '§3.140a 跨档补正：10/14 盘后档首抓时 002708（大摩健康产业混合A，sean/jasy 双账户）'
                                '10/14 净值尚未出库（按「基准已含 → 计 0」处理），本档 08:00 复抓确认 10/14 净值 '
                                '1.876（−2.2408%）已出库 → 以 `portfolio_close_20261014_fix.json` 覆盖修正；'
                                '组合当日损益由 −2,005.62 元 修正为 −2,598.48 元（Δ −592.86 元）、'
                                '总资产由 372,383.85 元 修正为 371,790.99 元；'
                                '⚠️ 同一券（002708）**连续第 2 个交易日出现同一机制迟滞**'
                                '（10/13 档亦由本档系列补正 −358.50 元）→ 已登记为稳定特征，须逐档兜底复抓'},
    'restore_rule_used': RESTORE_RULE, 'restore_rule_all_dev': rule_dev,
    'detail_restore_rule': RESTORE_RULE, 'detail_restore_dev': RESTORE_DEV,
    'detail_restore_note': ('§3.111 / §3.112a：逐券还原式由机器判据二选一（禁止按字段名取数）；'
                            f'本档采用 {RESTORE_RULE}（逐赛道最大偏差 {RESTORE_DEV:.4f} 元 < 1.5 元）。'
                            '⚠️ 本档基准为 `_fix` 件，其 `detail[].mv` 语义须逐档核对（§3.111 条款 30/33），'
                            '机器判据为强制步骤。'),
    # ⚠️ §3.144c / §3.146a：`_fix` 件内 `pct_of_total` 为修正前分母（372,383.85 元）派生值、与 mv 不自洽 → 一律现算
    'tracks': {k: {'mv': v['mv'], 'pct_of_total': round(100.0 * v['mv'] / TOTAL, 2),
                   'day_pct': v['day_pct'], 'pnl': v.get('pnl')} for k, v in tracks.items()},
    'stale_weight_fields_in_fix': {k: v['pct_of_total'] for k, v in tracks.items()
                                   if abs(v['pct_of_total'] - round(100.0 * v['mv'] / TOTAL, 2)) > 0.01},
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
        'prior_档口径': {'source': BASEFILE, 'hk_after': round(hk_after, 2), 'cash_after': round(cash_after, 2),
                        'note': '与基准同源（10/14 收盘修正件），无口径差'},
        'note': '本档无新增纪律动作（同日防线只触发一次，§3.114c）；两笔减仓均已成交、不可撤销；'
                '新增观察 = 下一道防线 4,000（10/14 收 4,174.47，距 +4.3618%）',
        'cumulative_selfcheck': {'sum_of_cuts': round(cut1_amt + cut2_amt, 2), 'cumulative_amount': cut_cum,
                                 'ok': abs(cut_cum - (cut1_amt + cut2_amt)) < 0.01},
    },
    'med_exposure': med, 'med_pct': round(med / TOTAL * 100, 2),
    'threshold_all_med': round(th_all, 2), 'threshold_a_sh_med': round(th_sh, 2),
    'non_med_total': round(B_nm, 2),
    'hk_total': round(hk_total, 2), 'hk_total_pct': round(hk_total / TOTAL * 100, 2),
    'hk_segments': {'pure_hstech': round(pure, 2), 'china_internet': round(cpo, 2),
                    'broad_hk': round(broad, 2)},
    'hk_layer_split': {'track_layer_pct': round(100.0 * tracks['恒生科技']['mv'] / TOTAL, 2),
                       'broad_layer_pct': round(broad / TOTAL * 100, 2),
                       'total_pct': round(hk_total / TOTAL * 100, 2),
                       'underreport_if_track_only_pct': round(broad / TOTAL * 100, 2)},
    'hk_southbound_gap': {'status': '常态（10/14 港股通正常）',
                          'resumed_data': '10/14 南向资金**小幅净卖出 1.35 亿港元**（结束 10/8 通道恢复以来的净买入序列）；'
                                          '当日恒指 −0.13%（收 24,314.17）、恒生科技 +0.91%（收 4,174.47）-> 「大盘微跌、科技跑赢」',
                          'note': '南向净卖出 1.35 亿港元与「美债利率与港股衍生品读数」非同源、不可互相验证（§3.107 同源纪律）；'
                                  '⚠️ 本档**未取得** 10/15 时段南向实时读数（港股 09:30 后开盘）'},
    'hk_leg_pending_carryover': {
        'carryover': True, 'recomputed': False,
        'source_file': BASEFILE + '#pending_release',
        'window': PEND.get('window'), 'window_closed': PEND.get('window_closed'),
        'total_low': hk_low, 'total_high': hk_high, 'mid_proxy_avg': hk_mid,
        'reason': ('档型③「正常交易日盘前」：A股与港股当日均为正常交易日、08:00 双方均无当日价格 -> '
                   '依 §3.110 待消化沿用上一档、不做新测算；'
                   '且该窗口已于 10/8 由场外港股联接净值一次性兑现并收口（window_closed = true）；'
                   '10/14 收盘档 new_window_this_session = []（§3.112i）'),
        'note': '窗口已于 10/8 收口（4/4 全部定价）；只给区间上下界、不得作方向判断（§3.108 条款 24 / §3.133e）',
    },
    'qdii_pending': {
        'as_of': '2026-10-15 08:00',
        'refreshed': True, 'carryover': False,
        'segment_us_medical': {
            'desc': 'US 10/14 单日段（IYH 口径）',
            'trade_dates_covered': [f'{us_cur[0]}(US)'],
            'iyh_pct': IYH_PCT_2DP, 'iyh_pct_precise': IYH_PCT_PRECISE, 'xlv_pct': XLV_PCT,
            'notional_mv': round(QDII_MV, 2),
            'notional_source': 'tracks["美股标普医药"].mv（§3.144a）；detail[].mv（陈旧继承值）= %s 元，已排除'
                               % f'{QDII_MV_DETAIL_STALE:,.2f}',
            'coef_range': [COEF_LO, COEF_HI], 'coef_mid_ref': COEF_MID,
            'pct_low': round(IYH_PCT_PRECISE * COEF_LO, 4), 'pct_high': round(IYH_PCT_PRECISE * COEF_HI, 4),
            'pct_mid_ref': round(IYH_PCT_PRECISE * COEF_MID, 4),
            'low': q_low, 'mid': q_mid, 'high': q_high,
            'low_alt_2dp_iyh': q_low_2dp, 'high_alt_2dp_iyh': q_high_2dp,
            'xlv_denominator_cross_ref': {'low': min(_xlv_a, _xlv_b), 'high': max(_xlv_a, _xlv_b),
                                          'role': '仅作交叉参考、不得替换主口径（§3.145c：主口径分母 = IYH）'},
            'codes': ['000369（广发全球医疗保健指数A）', '016280（广发全球医疗保健指数C）'],
            'coef_note': ('§3.118a / §3.139：传导系数不稳定（长假前后实测 1.25~1.29、常态 0.62）。'
                          '⚠️ **标注口径统一为「产生该段净值的美股交易日（US 段）」**（本档修正了 10/14 档「按净值出库日标注」'
                          '造成的 10/12 / 10/13 混淆）：US 10/09 段 0.6668 / 0.6788、US 10/12 段 1.0324 / 1.0503（越上界）、'
                          '**US 10/13 段 0.7451 / 0.7581（已回归区间内）**'
                          '→ **只给区间（0.60~0.90）、中枢仅作参考、禁止用于仓位决策**'),
        },
        'segment_cn_internet': {
            'desc': '164906（交银中证海外中国互联网指数 LOF）10/14 净值未出库',
            'notional_mv': round(LOF_MV, 2), 'range_given': False,
            'reason': ('该券跟踪「中证海外中国互联网指数」，**无单一稳定可复现代理指数** → '
                       '依 §3.122e 处置：**不给区间、只登记为「待兑现」**；'
                       '其最新净值日 = 2026-10-13（0.8790 / −0.2948%，已于 10/14 盘后档入账）→ '
                       '**10/14 净值尚未出库**（本档复抓最新净值日未推进），故自 US 10/14 起的未可观测段不给区间'),
        },
        'total_low': q_low, 'total_mid': q_mid, 'total_high': q_high,
        'range_given': True,
        'partial_range_note': ('§3.122e：本区间为**不完整区间** —— 只覆盖 000369 / 016280 两只全球医疗保健指数基金，'
                               '**不覆盖 164906（中概互联 LOF）腿**'),
        'unknown_sessions': ['2026-10-15(US)'],
        'new_sessions_since_prev': [f'{us_cur[0]}(US)'],
        'pending_codes': ['164906'],
        'applied_codes': [],
        'range_rule': ('QDII_LOW ≤ QDII_MID ≤ QDII_HIGH（§3.116b：对**结果值**取 min/max）；'
                       '取整口径 = **两步取整**（先按 notional 规模把单日敞口金额取到分，再乘 0.60~0.90 取到分），'
                       '该路径即新闻台账条目（第 26 条）的落盘路径（+822.61 ~ +1,233.91），并有 §3.144c 硬守卫逐值比对'),
        'coef_reestimate': {'status': 'pending', 'require': '≥4 券位 × ≥5 交易日',
                            'sample_label_rule': '键 = 产生该段净值的**美国交易日**（US 段口径），非净值出库日',
                            'observed_samples': {'US 2026-10-09': {'000369': 0.6668, '016280': 0.6788},
                                                 'US 2026-10-12': {'000369': 1.0324, '016280': 1.0503},
                                                 'US 2026-10-13': {'000369': 0.7451, '016280': 0.7581}}},
        'note': ('§3.112f / §3.118a：挂账只给区间、禁止中枢点值。'
                 '本档**新增 US 10/14 单日段**（US 10/13 段已于 10/14 盘后档由真实净值核销 **−651.49 元**、'
                 '实测隐含系数 0.7451 / 0.7581 落在 0.60~0.90 区间内）→ '
                 'refreshed = true（本档刷新，非沿用）。'
                 '下一可观测起点 = US 10/15 收盘（成型于北京 10/16 04:00）。'),
    },
    'pending_consume': {
        'hold_decision': 'no_action',
        'carryover': True,
        'reason': ('档型③：08:00 时点组合全部持仓标的不可定价（A股 09:30 前无价、场外基金净值收盘后发布、'
                   '美股 10/15 未开盘）-> 待消化不做新测算、沿用上一档；唯一可执行窗口 = 10/15 全天'),
        'estimated_combo_return_pct': 0.0,
        'estimated_combo_pnl': 0.0,
        'attribution': ('A股 10/15 09:30 前无价 + 港股 09:30 前无价 + 场外基金净值收盘后发布 + 美股 10/15 未开盘'
                        ' -> 当日可实现盈亏恒为 0 元，归因「标的不可定价」而非「市场持平」'
                        '（§3.107 条款 19 / §3.121d）'),
    },
    'defense_lines': {
        'hstech_4250': {'close': HS, 'prev_close': HS_PREV, 'line': 4250,
                        'state': _DEF['hstech_4250']['state'],
                        'dist_pct': round((HS / 4250 - 1) * 100, 4), 'dist_pts': round(HS - 4250, 2),
                        'break_trend': _DEF['hstech_4250']['break_trend'],
                        'intraday_touched_above': False,
                        'intraday_high': _DEF['hstech_4250']['intraday_high'],
                        'intraday_low': _DEF['hstech_4250']['intraday_low'],
                        'action_reserved': '无（第 2 次减仓已于 10/8 成交；同日防线只触发一次，§3.114c）',
                        'state_rule': '§3.145a：state 类字段禁止继承，由「本档 dist_pct vs 上一档 dist_pct」现算；'
                                      '本档 −1.7772% vs 上一档 −2.6675% -> 绝对值收窄 -> close_level_break_narrowed',
                        'verify_at': '2026-10-15 16:00（港股收盘价验证）',
                        'next_line': 4000, 'next_line_dist_pct': round((HS / 4000 - 1) * 100, 4),
                        'next_rule': '再破不叠加新纪律；下一道防线 4,000'},
        'zz_consume_12100': {'last': ZZ, 'as_of': '2026-10-14', 'state': 'above_lower_line',
                             'dist_pct': round((ZZ / 12100 - 1) * 100, 4),
                             'next_line': 12000, 'next_line_dist_pct': round((ZZ / 12000 - 1) * 100, 4),
                             'verify_at': '2026-10-15（A股 盘中/盘后档）',
                             'note': '中证消费 10/14 收 12,362.5056（+0.27%）、为本档组合主赛道代理中唯一收涨者；'
                                     '日内低 12,280.61 未破 12,100 下沿 -> 距下沿 **+2.1695%**（较 10/13 的 +1.8975% 走阔 0.2720pct）'},
        'a_med_reverse_1_5pct': {'proxy_pct': BMED, 'as_of': '2026-10-14', 'line_pct': -1.5,
                                 'dist_pct': round(BMED - (-1.5), 4),
                                 'state': 'not_triggered',
                                 'semantics': '§3.71：利好兑现后的回调观察线，非止损线 -> 处置 = 不执行主动减配',
                                 'action': 'active_take_profit = 0 / new_buy = 0',
                                 'contingency_closed': True,
                                 'contingency_triggered': False,
                                 'contingency_note': ('10/8 建立的「被动减配预案」已于 10/9 按预案明文'
                                                      '「回调序列断裂、预案不启动」作废（§3.136a 闭环）；'
                                                      '10/14 收盘代理 −0.8500%（中证医药 −0.68% / 中证医疗 −1.19% / '
                                                      '医药ETF −0.63%）→ 距 −1.5% 反向兑现线 **+0.65pct**，'
                                                      '为 10/9 以来首次「距离重新走阔」（10/13 曾收窄至 +0.3375pct）'),
                                 'verify_at': '2026-10-15（A股 收盘后）'},
        'sh_comp': {'last': SH, 'as_of': '2026-10-14', 'pct': round((SH / SH_PREV - 1) * 100, 4)},
    },
    'scenario': {
        'upside': ('① **美股医疗保健板块领涨全市场（+2.44%，标普 11 板块第一）** —— 礼来（LLY）+3.62% 收 1,208.74 美元、'
                   '默沙东与联合健康（UNH）Q3 业绩与指引双超预期（营收 1,130 亿美元 / 调整后 EPS 4.69 / 综合医疗赔付率降至 88.4%）'
                   '→ 拖累 XLV +2.5345%、IYH +2.3360%；**组合美股标普医药腿（15.79%）由上一档的「最大单腿利空」翻转为'
                   '本档「最大单腿利多」**，QDII 挂账区间 **+822.61 元 ~ +1,233.91 元**；'
                   '② **国内流动性端继续偏松**：央行公告 10/15 开展 7,000 亿元 6 个月（182 天）买断式逆回购、'
                   '**净投放 2,000 亿元** → A股 分母端支撑；③ **恒生科技 10/14 显著跑赢大市**：收 4,174.47（+0.91%、+37.84 点、'
                   '振幅 3.53%、盘中一度重返 4,200 上方），而恒指仅 −0.13% → 恒科腿情绪修复、距 4,250 防线的破位幅度'
                   '由 −2.6675% 收窄至 −1.7772%；④ **价格端数据边际改善**：中国 9 月 CPI 同比 +0.9%（涨幅扩大 0.1pct）、'
                   'PPI 同比 +5.0%（**涨幅扩大 1.2pct**）→ 反通缩叙事边际缓和；⑤ **三季报预喜潮延续**'
                   '（荣盛石化净利同比预增 778%~823%、嘉元科技 +1,197%~1,319%、德福科技 +5xx%）+ '
                   '**双十一今日（10/15）正式开启**（淘宝天猫 10:00 红包开抢、20:00 开启预售）→ 大消费腿催化窗口；'
                   '⑥ 国新办前三季度进出口发布会：工业机器人、电子元件等产品进出口合计超 10 万亿元 → 结构性亮点。'
                   '⚠️ **但本档 08:00 无 A股/港股 当日定价，上行判断仅为「情境」、不得作为方向依据**（§3.117d）'),
        'base': (f'档型③「正常交易日盘前」：组合账面基准 = 10/14 收盘修正件 {TOTAL:,.2f} 元'
                 f'（§3.140a 跨档补正 −592.86 元后；10/14 单日 −2,598.48 元 / −0.6941%）；'
                 f'医药敞口 {med/TOTAL*100:.2f}%、港联系总暴露 {hk_total/TOTAL*100:.2f}%'
                 f'（双层：赛道 {tracks["恒生科技"]["pct_of_total"]:.2f}% + 宽基 {broad/TOTAL*100:.2f}%）；'
                 f'待消化 = QDII 腿新窗口（US 10/14 单日段）区间 {q_low:+,.2f} 元 ~ {q_high:+,.2f} 元'
                 f'（港股腿窗口已于 10/8 收口）；A股与港股 10/15 当日价格待 09:30 后'),
        'downside': ('① **美国 9 月 CPI 同比 +3.7%（预期 3.6%）、核心 +2.6% 双双超预期** → 10 月加息押注由 21.6% 升至 43.7%'
                     '（盘中读数）→ **组合分母端本档最大宏观利空**；标普 500 −1.11%、纳指 −1.88%、QQQ −1.97% '
                     '（**注意：医疗 +2.44% 为逆势避险方向，与指数层面利空并不矛盾**）；'
                     '② **AI 硬件从「杀估值」推进到「杀信用」**：CoreWeave 2032 年到期无担保债券跌破面额 80 美分、'
                     '股价 −15%+（年内涨幅归零）→ A股 算力/光模块/PCB 链承压，10/14 已出现「一日半反转」；'
                     '③ **A股 10/14 缩量普跌**：上证 −0.88% 报 3,767.23、深证成指 −1.97% 报 12,110.59、'
                     '**创业板指 −3.10% 报 2,866.76** → 成长股杀跌为主、大盘价值相对抗跌；'
                     '④ **港股资金面转差**：南向资金转为小幅净卖出 1.35 亿港元；软硬件背离 —— '
                     '生物医药领跌（歌礼制药-B −12%+、乐普生物 −6%+、派格生物医药 −5%+）'
                     '→ **组合港联系（总暴露 13.35%）内部，医药与科技方向已背离**；'
                     '⑤ **A股医药整体收跌**：申万医药生物 −1.13% 报 7,583.55、医疗器械 −1.09%、生物医药 −1.51%、'
                     '医药生物板块主力资金净流出 21 亿元级 → 板块代理 −0.85% 距 −1.5% 反向兑现线 +0.65pct；'
                     '⑥ **大消费内部背离**：终端白酒价盘「九涨两跌一平」走强（打包总价 10,764 元、+29 元创 7 日新高）'
                     '而 A股 白酒股多数下跌（水井坊 −3.79%、金种子酒 −3.95%、舍得酒业 −3.55%）'
                     '→ 价格端与股价端背离、方向不可外推；'
                     '⑦ **商品分化**：WTI 原油 +1.01% 报 95.09 美元（三周高位）而贵金属重挫'
                     '→ 跨资产读数为「供给溢价 + 实际利率上行」复合、非单纯避险；'
                     '⑧ **标普 11 板块八跌三涨**（仅医疗 +2.44%、必需消费、能源收涨）→ 除医药腿外组合其余赛道开盘方向偏空'),
    },
    'action': {'new_buy': 0, 'active_take_profit': 0, 'discipline_cut_today': 0,
               'discipline_cut_pending': 0,
               'discipline_cut_cumulative_registered': cut_cum,
               'new_pending': 1,
               'contingency_plan_registered': 0,
               'contingency_plan_closed': 1,
               'note': ('档型③ 盘前：08:00 时点组合全部标的不可定价 -> 赛道级动作全部为 0；'
                        '10/15 全天为唯一可执行窗口，执行清单 = ① 复核恒生科技 4,250/4,000'
                        '（10/14 收 4,174.47，破位幅度收窄至 −1.7772%、距 4,000 +4.3618%）；'
                        '② 复核中证消费 12,100 下沿（10/14 收 12,362.5056，距 +2.1695%）；'
                        '③ 复核 A股医药反向兑现线（10/14 代理 −0.85%，距线 +0.65pct，距离重新走阔）；'
                        '④ 复核 QDII 000369/016280 的 US 10/14 段净值是否出库（出库则核销区间 +822.61 元 ~ +1,233.91 元）；'
                        '⑤ 登记中国 9 月 PPI/零售（09:30）、美国 9 月 PPI（20:30）、10/15 买断式逆回购 7,000 亿元落地 -> 只登记、不预判；'
                        '⑥ 医药敞口 38.28% 距上限 1.72pct（门槛 +7.47% / +12.71%）-> 任何正向催化均不构成加仓理由')},
    'calendar': {
        '2026-10-14（上一档）': 'A股 + 港股正常交易日（上证 −0.8850% 报 3,767.2271 / 深证成指 −1.97% / 创业板指 −3.10%；'
                                '恒指 −0.13% 报 24,314.17 / **恒生科技 +0.91% 报 4,174.47 跑赢大市**）；'
                                '组合当日 **−2,598.48 元（−0.6941%）**（含 §3.140a 跨档补正 −592.86 元）；'
                                'QDII US 10/13 段净值释放 **−651.49 元**（隐含系数 0.7451 / 0.7581）；'
                                'US 10/14 收盘成型于 10/15 04:00 并于本档归档（XLV +2.5345% / IYH +2.3360%）',
        '2026-10-15（今日）': 'A股 + 港股 + 美股**三市场均正常交易日**；'
                              '**中国 9 月 CPI/PPI（09:30）与零售数据、美国 9 月 PPI（北京时间 20:30）**；'
                              '央行 7,000 亿元 6 个月买断式逆回购（净投放 2,000 亿元）落地；'
                              '**第 140 届广交会开幕（10/15-11/4）**；**双十一正式开启**（淘宝天猫 10:00 红包 / 20:00 预售）',
        '2026-10-16': '国内成品油调价窗口（第 20 轮）；US 10/15 收盘（成型于北京 10/16 04:00）',
        '2026-10-19': '**2026 金融街论坛年会开幕（吴清作主题演讲）**；**港股重阳节翌日休市**（A股 正常）',
        '2026-10-27~28': 'FOMC 议息会议（CME：10 月维持不变概率约 82%）',
        '2026-12-09': 'FOMC 年末会议（CME：加息 25bp 概率约 84%）',
    },
    'calendar_by_market': {
        'A股': '10/1-10/7 休市 -> 10/8 复市 -> 10/9 正常 -> 10/10-10/11 周末 -> 10/12 正常 -> 10/13 正常 -> '
                '10/14 正常（缩量普跌）-> **10/15 正常交易日**',
        '港股': '10/1 休市 1 天 -> 10/8 起正常 -> 10/10-10/11 周末 -> 10/12 正常 -> 10/13 正常 -> 10/14 正常 -> '
                '**10/15 正常交易日**（10/19 重阳节翌日休）',
        '港股通(南向)': '10/1-10/7 暂停 -> 10/8 恢复（净买入）-> 10/14 转为小幅净卖出 1.35 亿港元 -> **10/15 正常**',
        '美股': 'US 10/13 已归档；**10/14 收盘成型于北京 10/15 04:00 并于本档归档（XLV 173.96 / IYH 73.16）**；'
                '**US 10/15 照常开市**，收盘成型于北京 10/16 04:00',
    },
    'data_hygiene': {
        'note': ('承接前档待办：① **10/14 收盘件 002708 净值遗漏已由本档 §3.140a 跨档补正闭环**'
                 '（`portfolio_close_20261014_fix.json`，Σmv dev / Σpnl dev / 还原式 dev 三重硬守卫全部通过）；'
                 '⚠️ **该券连续第 2 个交易日同机制迟滞** -> 已升级为「逐档必做兜底复抓」固定工序（§3.140a 第 3 例）；'
                 '② `portfolio_close_20260918_fix.json`（Σmv 差 -2,468.33 元）、'
                 '`portfolio_close_20260921_fix.json`（Σpnl 差 +333.12 元）两件不自洽（未闭环）；'
                 '③ `fund_nav.csv` 历史重复键；④ 中国 10Y 收益率序列缺口（rf 硬编码 1.68%）；'
                 '⑤ 且慢 `long-win-nav.csv` 源/本地口径分歧（本档 `qieman_rest_20261015.json` size = 0 空体 -> 且慢侧读数不可用）；'
                 '⑥ `indices.csv` 港股盘中/收盘双行物理并存（append-only，读取侧 last-wins，§3.133b）；'
                 '⑦ 事件库 19 条历史条目缺 `actual_date` 字段（`legacy_missing_actual_date = 19`）；'
                 '⑧ `sh000922`（中证红利）新浪日线末行 = 2019-01-30 -> 禁止用作任何窗口代理（§3.111b）；'
                 '`000933`（中证医药）distinct 交易日稀疏（16 日）-> 仅可用 1 日真实收盘、多日窗口须用 399006 代理（§3.112b）；'
                 '⑨ **164906（中概互联 LOF）最新净值日 = 2026-10-13、10/14 净值未出库** -> QDII 区间为不完整区间（§3.122e）；'
                 '⑩ **DeepSeek v4-flash 端点连续第 9 个交易日 HTTP 402**（本档 26/26 条为规则表标注）；'
                 '⑪ **新浪 hq 港股指数存在 rt_hk* / hk* 两套代码、同一时刻收盘值不同**'
                 '（HSTECH rt 4,174.470 vs hk 4,169.020、差 5.45pt；HSI 差 6.50pt；HSCEI 差 6.81pt）'
                 '-> 盘前对账必须与收盘档同用 **rt_hk 系列代码**，否则会误判「昨收被修正」（§3.150a 新增）。'),
    },
}

json.dump(out, open(os.path.join(HIST, f'portfolio_preopen_{TODAY.replace("-", "")}.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
print(f'\n已保存 portfolio_preopen_{TODAY.replace("-", "")}.json')
print(f'  OK 本档未产出 portfolio_close_{TODAY.replace("-", "")}.json（档型③不产 close）')
print(f'  OK 本档未产出 portfolio_pending_{TODAY.replace("-", "")}.json（档型③不产 pending；待消化沿用上一档）')
print(f'  OK new_pending = 1（QDII 新增 US 10/14 单日段，区间 {q_low:+,.2f} 元 ~ {q_high:+,.2f} 元）/ contingency_plan_closed = 1')
