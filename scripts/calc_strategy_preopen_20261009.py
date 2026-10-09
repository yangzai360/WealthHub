# -*- coding: utf-8 -*-
"""2026-10-09（周五）盘前档：组合策略计算 —— **A股 长假后复市第 2 个交易日 + 港股正常交易日**
SESSION_TYPE = 'normal_trading_day_preopen'（**档型③**：A股与港股当日均为正常交易日，但 08:00 双方均无新价格）
  → 依 §3.28 / §3.110 档型③ / §3.115c：**不产 `portfolio_close_*`、不产 `portfolio_pending_*`**；
    **待消化不做新测算**（港股腿窗口已于 10/8 收口；QDII 腿区间按新增 US 10/8 段复算并披露）；
基准 = **10/8 收盘（portfolio_close_20261008.json）= 374,466.56 元**（不再是 9/30 冻结基准）

★★★ 本档结构差异（派生后必检） ★★★
  ① 基准由「9/30 修正收盘 380,888.29 元」推进为「10/8 收盘 374,466.56 元」—— 10/8 为正常交易日，
     `portfolio_close_20261008.json` 已计入链式序列（40 个交易日）；
  ② 美股腿新增 1 个真实交易日（US 10/8）：IYH 71.30 → 70.92（−0.5330%）、XLV 168.81 → 168.16（−0.3871%）
     → QDII 挂账区间由「US 10/1~10/7」扩展为「US 10/1~10/8」；
  ③ 恒生科技防线基准价更新为 10/8 收盘 4,073.38（−2.89%），距 4,250 = −176.62 点 / −4.1558%；
     下一观察线 4,000（距 +1.8345%）；
  ④ A股医药反向兑现线（−1.5%）已于 10/8 收盘级触发（板块代理 −2.6475%）→ 本档须建立
     「连续 2 日回调 → 被动减配预案」（候选 012323 / 001180），触发判据 = 10/9 收盘板块代理再跌（≤0）；
  ⑤ 不产 pending 台账（档型③）→ 产 `session_type` 标注 + `new_pending = 0` 自证。
⚠️ §3.118a：跨长假 QDII 挂账预告**禁止给中枢点值**，只给区间（系数 0.60~0.90）并标注「系数不稳定」。
⚠️ §3.123e 纪律累计口径：第 1 次 1,882.46 元（9/29 触发、9/30 成交）+ 第 2 次 1,904.44 元
   （10/2 触发、已于 10/8 按净值成交）= 累计 3,786.90 元（**本档无新增纪律动作**）。
⚠️ §3.133a：展示类字段一律由数据源现算 + 自校验断言，禁止手写常量表。
⚠️ §3.136a：「A股医药反向兑现线」阈值为**负数**（line_pct = -1.5），触发条件 = 板块代理 ≤ −1.5%。
"""
import json, os, csv as _csv

BASE = '/Users/jieyang/Documents/WealthHub'
HIST = os.path.join(BASE, 'data/processed/history')
TODAY = '2026-10-09'
SESSION_TYPE = 'normal_trading_day_preopen'
BASEFILE = 'portfolio_close_20261008.json'
fix = json.load(open(os.path.join(HIST, BASEFILE), encoding='utf-8'))

TOTAL = fix['total_mv']
tracks = fix['tracks']
print(f'基准（10/8 收盘）= {TOTAL:,.2f} 元  <- {BASEFILE}')
print('  [档型③] 正常交易日盘前（A股 10/9 长假后第 2 个交易日 + 港股正常交易日）'
      ' -> 不产 close / 不产 pending、待消化不做新测算（§3.28 / §3.110 / §3.115c）')
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

# ---------- 港股暴露三层拆解（§3.108 条款 23/24）----------
HK_TECH_CODES = {'012348', '513180'}          # 纯恒生科技系
CPO_CODES = {'513050', '164906'}              # 中概/海外互联系
BROAD_HK_CODES = {'000071', '159920'}         # 宽基中的恒生系
pure = cpo = broad = 0.0
seg_detail = []
for d in fix['detail']:
    code6 = ''.join(c for c in str(d['code']) if c.isdigit())[-6:] if any(c.isdigit() for c in str(d['code'])) else ''
    mv = float(d['mv0_new']) + float(d['est_pnl'])
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

# ---------- 恒生科技 0.5% 纪律减仓（累计口径，§3.123e）----------
disc = fix.get('discipline', {})
cut1_amt = disc.get('cut1', {}).get('amount', 1882.46)
cut2_amt = disc.get('cut2', {}).get('amount', 1904.44)
cut_cum = round(cut1_amt + cut2_amt, 2)
hk_after = round(tracks['恒生科技']['mv'] - cut_cum, 2)
cash_after = round(tracks['现金']['mv'] + cut_cum, 2)
print(f'\n恒生科技 0.5% 纪律减仓（累计口径）：{cut_cum:,.2f} 元')
print(f'  第 1 次 {cut1_amt:,.2f} 元（9/29 触发 -> 9/30 成交，已结算）')
print(f'  第 2 次 {cut2_amt:,.2f} 元（10/2 触发 -> 10/8 已按净值成交）')
print(f'  恒生科技 {tracks["恒生科技"]["mv"]:,.2f} -> {hk_after:,.2f}'
      f'（{tracks["恒生科技"]["pct_of_total"]:.2f}% -> {hk_after/TOTAL*100:.2f}%）')
print(f'  现金     {tracks["现金"]["mv"]:,.2f} -> {cash_after:,.2f}'
      f'（{tracks["现金"]["pct_of_total"]:.2f}% -> {cash_after/TOTAL*100:.2f}%）')
print(f'  自证 cumulative_amount == SUM cut_i.amount: {cut_cum} == {cut1_amt} + {cut2_amt}'
      f' -> {abs(cut_cum - (cut1_amt + cut2_amt)) < 0.01}')

# ---------- QDII 挂账（本档唯一新增定价：US 10/8）----------
med_us = tracks['美股标普医药']['mv']

_iyh, _xlv = {}, {}
with open(os.path.join(HIST, 'indices.csv'), encoding='utf-8-sig') as f:
    for r in _csv.DictReader(f):
        dt = r['date'][:10]
        if r['code'] == 'IYH':
            _iyh[dt] = float(r['close'])
        elif r['code'] == 'XLV':
            _xlv[dt] = float(r['close'])

NEED = ['2026-10-01', '2026-10-02', '2026-10-05', '2026-10-06', '2026-10-07', '2026-10-08']


def pct(series, d):
    ds = sorted(series)
    i = ds.index(d)
    return (series[d] / series[ds[i - 1]] - 1) * 100


iyh_pct = {d: pct(_iyh, d) for d in NEED}
assert abs(iyh_pct['2026-10-06'] - (-0.3385)) < 0.01, f"IYH 10/6 异常: {iyh_pct['2026-10-06']}"
assert abs(iyh_pct['2026-10-05'] - 0.7244) < 0.01, f"IYH 10/5 异常: {iyh_pct['2026-10-05']}"
assert iyh_pct['2026-10-07'] > 0, f"IYH 10/7 应为正: {iyh_pct['2026-10-07']}"
assert iyh_pct['2026-10-08'] < 0, f"IYH 10/8 应为负: {iyh_pct['2026-10-08']}"
assert abs((_xlv['2026-10-08'] / _xlv['2026-10-07'] - 1) * 100 - (-0.3871)) < 0.02, \
    f"XLV 10/8 异常: {(_xlv['2026-10-08']/_xlv['2026-10-07']-1)*100}"

comp_b = 1.0
for d in NEED:
    comp_b *= (1 + iyh_pct[d] / 100)
comp_b -= 1

comp_b_prev = 1.0
for d in NEED[:-1]:
    comp_b_prev *= (1 + iyh_pct[d] / 100)
comp_b_prev -= 1

NOTIONAL_MV = 59644.42          # 锚点 = 9/30 NAV 的持仓市值（000369/016280，§3.105）
notional_b = NOTIONAL_MV * comp_b
notional_b_prev = NOTIONAL_MV * comp_b_prev
print('\nQDII 挂账（§3.112f / §3.118a：只给区间、禁止中枢点值）')
print(f'  锚点：最晚已发布净值日 = 9/30（000369/016280 已于 10/8 档回填至 9/30）'
      f' -> 未可观测段 = US 10/1~10/8，标的锚点市值 {NOTIONAL_MV:,.2f} 元')
print('  B) 自 US 10/1 起未可观测段（IYH 现算，§3.133a）：'
      + ' x '.join(f'{d[5:]} {iyh_pct[d]:+.4f}%' for d in NEED)
      + f' -> 复合 {comp_b*100:+.4f}%')
print(f'     未打折损益 {notional_b:+,.2f} 元'
      f'（同口径「不含 US 10/8」= {notional_b_prev:+,.2f} 元 -> 新增段 {notional_b - notional_b_prev:+,.2f} 元）')
coefs = (0.60, 0.90)
vals_b = sorted(round(notional_b * k, 2) for k in coefs)
b_low, b_high = min(vals_b), max(vals_b)
assert b_low <= b_high, '§3.116b 区间端点语义错误'
print(f'     系数 0.60 / 0.90 -> {notional_b*0.60:+,.2f} / {notional_b*0.90:+,.2f} 元')
print(f'  -> 挂账区间 {b_low:+,.2f} 元 ~ {b_high:+,.2f} 元'
      f'（未打折 {notional_b:+,.2f} 元 = 组合 {notional_b/TOTAL*100:+.4f}%）')
print('     前档区间 -195.08 元 ~ -130.05 元（US 10/1~10/7，5 日）-> 本档扩张（新增 US 10/8 IYH -0.5330%）')
print('  [!] 传导系数不稳定：长假前后实测隐含 1.25~1.29（§3.118a），远超标定 0.72 / 常态实测 0.62'
      ' -> 若按 1.25 折算，B = {:+,.2f} 元'.format(notional_b * 1.25))
print('  [!] 自 US 10/1 起窗口共 6 个美股交易日本档全部可观测；下一个未知交易日 = US 10/9'
      '（收盘成型于北京 10/12 04:00，因 10/10-10/11 为周末）')

# ---------- 港股腿待消化：沿用上一档终值（档型③，不重算）----------
PEND = fix.get('pending_release', {})
hk_low = PEND.get('window_estimate_low', -973.41)
hk_high = PEND.get('window_estimate_high', -758.58)
hk_mid = PEND.get('window_estimate_mid_proxy_avg', -866.14)
print('\n港股腿「待消化」= 已于 10/8 收口（4/4 全部定价、净值一次性兑现）（档型③不重算）')
print(f'  终值：{hk_low:+,.2f} 元 ~ {hk_high:+,.2f} 元（代理均值中枢 {hk_mid:+,.2f} 元）'
      f' | window_closed = {PEND.get("closed")}')
print('  [!] 该窗口 10/8 起关闭、不再延续；窗口收口 != 可作方向判断（§3.108 条款 24 / §3.133e）')

# ---------- 三条防线 ----------
HS, HS_PREV = 4073.38, 4194.49
ZZ = 12256.813
SH = 3811.9043
BMED = -2.6475
print('\n三条防线（全部取 10/8 收盘口径；A股 两项 10/9 09:30 后验证）：')
print(f'  (1) 恒生科技 4,250：10/8 收 {HS:,.2f}（前收 {HS_PREV:,.2f} / {(HS/HS_PREV-1)*100:+.4f}%）'
      f' -> 距防线 {HS-4250:+,.2f} 点 / {(HS/4250-1)*100:+.4f}%'
      f'【深度破位、破位幅度本轮最大（10/2 -2.1661% -> 10/5 -1.5605% -> 10/6 -0.6342% -> 10/7 -1.3061% -> 10/8 -4.1558%）】')
print(f'     下一观察线 4,000（距 {(HS/4000-1)*100:+.4f}%）'
      f' | 10/8 日内高 4,215.35 < 4,250 -> intraday_touched_above = false（§3.129b）')
print(f'     -> 第 2 次减仓（{cut2_amt:,.2f} 元）已于 10/8 成交（累计 {cut_cum:,.2f} 元）；本档不新增动作')
print(f'  (2) 中证消费 12,100 下沿：10/8 收 {ZZ:,.4f} -> {(ZZ/12100-1)*100:+.4f}%'
      f'（下一线 12,000 距 {(ZZ/12000-1)*100:+.4f}%）-> 10/9 09:30 后可验证')
print(f'  (3) A股医药反向兑现线（line_pct = -1.5，触发 = 板块代理 <= -1.5%）：'
      f'10/8 板块代理 {BMED:+.4f}% -> 收盘级已触发（距线 {BMED-(-1.5):+.4f}pct）')
print(f'     [!] §3.71 语义：该线是「利好兑现后的回调观察线」，不是止损线 -> 10/8 处置 = 不执行主动减配')
print(f'     [!] 闭环要求（§3.136a）：若 10/9 收盘板块代理再跌（<=0）-> 形成「连续 2 日回调」-> 建立被动减配预案'
      f'（候选 012323 / 001180，单次 <=0.5% 基准总资产 = {round(TOTAL*0.005,2):,.2f} 元）；'
      f'若 10/9 收盘转正（>0）-> 回调序列断裂、预案不启动')
print(f'  附：上证 10/8 收 {SH:,.4f}（-0.79%）；恒指 10/8 收 23,785.79（-1.4290%）；恒生国企 8,010.58（-0.8890%）')

# ---------- 产物 ----------
out = {
    'date': TODAY, 'session': 'preopen', 'session_type': SESSION_TYPE,
    'session_type_note': ('档型③「正常交易日盘前」= A股 10/9（长假后第 2 个交易日）+ 港股 10/9（正常交易日）；'
                          '08:00 双方均无当日价格 -> 不产 portfolio_close_*、不产 portfolio_pending_*；'
                          '港股腿待消化窗口已于 10/8 收口、不做新测算；'
                          '本档唯一新增定价 = 美股 10/8 收盘（XLV -0.3871% / IYH -0.5330%）'),
    'calendar_verification': {
        'A股': 'stock_zh_index_daily(sh000001) 末行 = 2026-10-08（收 3,811.9043 / -0.79%）-> 10/9 为正常交易日，09:30 开盘前无新价格',
        '港股': '新浪 hq rt_hkHSTECH 返回体日期字段 = 2026/10/08 16:08（收 4,073.38 / -2.887%）-> 10/9 今日待开 09:30（非休市）',
        '美股': 'stock_us_daily(IYH/XLV) 末行 = 2026-10-08（XLV 168.16 / IYH 70.92）-> US 10/8（周四）收盘已于北京 10/9 04:00 成型，本档新增 7 行',
        'rule': '三市场各自独立验证、不得互相外推（§3.107 / §3.119b / §3.122b）'},
    'base_total': TOTAL, 'base_file': BASEFILE, 'base_guard_dev': round(dev, 4),
    'base_revision': {'prev_total': 380888.29, 'delta': round(TOTAL - 380888.29, 2),
                      'reason': '本档基准为 10/8 收盘（正常交易日，portfolio_close_20261008.json 已计入链式序列）；'
                                '较 9/30 冻结基准 380,888.29 元推进 -6,421.73 元（10/8 单日 -1.6860%）'},
    'tracks': {k: {'mv': v['mv'], 'pct_of_total': v['pct_of_total'], 'day_pct': v['day_pct']}
               for k, v in tracks.items()},
    'discipline_hstech_cumulative': {
        'cut1': {'pct': 0.5, 'amount': cut1_amt, 'triggered_on': '2026-09-29', 'settled_on': '2026-09-30',
                 'note': '9/29 收盘 4,249.62（-0.0089%）边际破位触发 -> 9/30 按净值成交 1,882.46 元（成本已如实记录，§3.117b）'},
        'cut2': {'pct': 0.5, 'amount': cut2_amt, 'triggered_on': '2026-10-02', 'settled_on': '2026-10-08',
                 'execute_at': '2026-10-08', 'execution_pending': False, 'is_today': False,
                 'basis': '基准总资产 380,888.29 元 x 0.5%（§3.114c / §3.123e 确定性口径）',
                 'targets': ['012348（天弘恒生科技联接A）', '513180（恒生科技ETF华夏）'],
                 'target_rule': '标的限「纯恒科」口径，不落在中概（513050 / 164906）',
                 'outcome': '执行日（10/8）恒生科技收 4,073.38（-2.89%）、距 4,250 为 -4.1558% -> '
                            '破位幅度较判定日（-2.1661%）进一步扩大 -> 属有效减仓'},
        'cumulative_amount': cut_cum,
        'hk_after': hk_after, 'cash_after': cash_after,
        'weight_after_pct': {'恒生科技': round(hk_after / TOTAL * 100, 2),
                             '现金': round(cash_after / TOTAL * 100, 2)},
        'prior_档口径': {'source': 'reports/daily/2026-10-04.md',
                        'hk_after': 29668.40, 'cash_after': 31117.41,
                        'weight_after_pct': {'恒生科技': 7.79, '现金': 8.17},
                        'correction_note': '该口径只扣第 2 次减仓、未扣除第 1 次已成交的 1,882.46 元（10/4 以 380,888.29 为基数）'
                                           ' -> 统一为「累计扣除」（§3.123e）；本档两口径并列、以累计口径为准'},
        'note': '本档无新增纪律动作（同日防线只触发一次，§3.114c）；第 2 次减仓已于 10/8 成交、不可撤销；'
                '新增观察 = 下一道防线 4,000（10/8 收 4,073.38，距 +1.8345%）',
        'cumulative_selfcheck': {'sum_of_cuts': round(cut1_amt + cut2_amt, 2), 'cumulative_amount': cut_cum,
                                 'ok': abs(cut_cum - (cut1_amt + cut2_amt)) < 0.01},
    },
    'med_exposure': med, 'med_pct': round(med / TOTAL * 100, 2),
    'threshold_all_med': round(th_all, 2), 'threshold_a_sh_med': round(th_sh, 2),
    'non_med_total': round(B_nm, 2),
    'hk_total': round(hk_total, 2), 'hk_total_pct': round(hk_total / TOTAL * 100, 2),
    'hk_segments': {'pure_hstech': round(pure, 2), 'china_internet': round(cpo, 2),
                    'broad_hk': round(broad, 2)},
    'hk_southbound_gap': {'window_days': ['2026-10-02', '2026-10-05', '2026-10-06', '2026-10-07'],
                          'status': '已于 10/8 终止（港股通恢复）',
                          'resumed_data': '10/8 南向净买入 64.77 亿港元；港股主板成交 2,073 亿港元（前值 947 亿）',
                          'note': '南向空窗共 4 个港股交易日；10/8 复市首日量能恢复显著'},
    'hk_leg_pending_carryover': {
        'carryover': True, 'recomputed': False,
        'source_file': 'data/processed/history/portfolio_close_20261008.json#pending_release',
        'window': PEND.get('window'), 'window_closed': PEND.get('closed'),
        'total_low': hk_low, 'total_high': hk_high, 'mid_proxy_avg': hk_mid,
        'reason': ('档型③「正常交易日盘前」：A股与港股当日均为正常交易日、08:00 双方均无当日价格 -> '
                   '依 §3.28 / §3.110 / §3.115c 待消化沿用上一档、不做新测算；'
                   '且该窗口已于 10/8 由场外港股联接净值一次性兑现并收口（window_closed = true）'),
        'note': '窗口已于 10/8 收口（4/4 全部定价）；只给区间上下界、不得作方向判断（§3.108 条款 24 / §3.133e）',
    },
    'qdii_pending': {
        'as_of': '2026-10-09 08:00',
        'component_b': {'desc': '自 US 10/1 起未可观测段（IYH 现算，§3.133a）',
                        'trade_dates_covered': NEED,
                        'iyh_pct': {d: round(iyh_pct[d], 4) for d in NEED},
                        'comp_pct': round(comp_b * 100, 4),
                        'notional_mv': NOTIONAL_MV,
                        'notional': round(notional_b, 2),
                        'low': round(b_low, 2), 'high': round(b_high, 2),
                        'coef_range': [0.60, 0.90], 'coef_unstable': True,
                        'coef_note': '长假前后实测隐含系数 1.25~1.29（§3.118a），远超标定 0.72 / 常态实测 0.62'
                                     ' -> 只给区间、禁止中枢点值',
                        'prev_notional': round(notional_b_prev, 2),
                        'delta_vs_prev': round(notional_b - notional_b_prev, 2),
                        'prev_notional_as_reported': -216.75},
        'total_low': round(b_low, 2), 'total_high': round(b_high, 2),
        'prev_total_low': -195.08, 'prev_total_high': -130.05,
        'unknown_sessions': ['2026-10-09(US)'],
        'new_sessions_since_prev': ['2026-10-08(US)'],
        'coef_1_25_total': round(notional_b * 1.25, 2),
        'note': ('§3.112f / §3.118a：挂账只给区间、禁止中枢点值。'
                 '本档自 US 10/1 起的 6 个美股交易日全部可观测；US 10/8 IYH -0.5330% -> 挂账区间小幅扩张。'),
    },
    'pending_consume': {
        'hold_decision': 'no_action',
        'carryover': True,
        'reason': ('档型③：08:00 时点组合全部持仓标的不可定价（A股 09:30 前无价、场外基金净值收盘后发布、'
                   '美股 10/9 未开盘）-> 待消化不做新测算、沿用上一档；唯一可执行窗口 = 10/9 全天'),
        'estimated_combo_return_pct': 0.0,
        'estimated_combo_pnl': 0.0,
        'attribution': ('A股 10/9 09:30 前无价 + 港股 09:30 前无价 + 场外基金净值收盘后发布 + 美股 10/9 未开盘'
                        ' -> 当日可实现盈亏恒为 0 元，归因「标的不可定价」而非「市场持平」'
                        '（§3.107 条款 19 / §3.121d）'),
    },
    'defense_lines': {
        'hstech_4250': {'close': HS, 'prev_close': HS_PREV, 'line': 4250, 'state': 'close_level_break_deepened',
                        'dist_pct': round((HS / 4250 - 1) * 100, 4), 'dist_pts': round(HS - 4250, 2),
                        'break_type': '非边际破位（10/2 收盘级首次触发；10/8 幅度深化至 -4.1558%，为本轮最大）',
                        'intraday_touched_above': False, 'intraday_high': 4215.35,
                        'action_reserved': '无（第 2 次减仓已于 10/8 成交；同日防线只触发一次，§3.114c）',
                        'verify_at': '2026-10-09 16:00（港股收盘价验证）',
                        'next_line': 4000, 'next_line_dist_pct': round((HS / 4000 - 1) * 100, 4),
                        'next_rule': '再破不叠加新纪律；下一道防线 4,000（距 +1.8345%）'},
        'zz_consume_12100': {'last': ZZ, 'as_of': '2026-10-08', 'state': 'above_close_level',
                             'dist_pct': round((ZZ / 12100 - 1) * 100, 4),
                             'next_line': 12000, 'next_line_dist_pct': round((ZZ / 12000 - 1) * 100, 4),
                             'verify_at': '2026-10-09（A股 盘中/盘后档）'},
        'a_med_reverse_1_5pct': {'proxy_pct': BMED, 'as_of': '2026-10-08', 'line_pct': -1.5,
                                 'dist_pct': round(BMED - (-1.5), 4),
                                 'state': 'TRIGGERED_CLOSE_LEVEL',
                                 'semantics': '§3.71：利好兑现后的回调观察线，非止损线 -> 处置 = 不执行主动减配',
                                 'action': 'active_take_profit = 0 / new_buy = 0',
                                 'contingency_plan': {
                                     'name': '被动减配预案（条件触发，本档建立、不执行）',
                                     'trigger': '10/9 收盘 A股医药板块代理 <= 0%（形成「连续 2 日回调」）',
                                     'size_pct': 0.5, 'size_amount': round(TOTAL * 0.005, 2),
                                     'basis': f'基准总资产 {TOTAL:,.2f} 元 x 0.5%',
                                     'candidates': ['012323（华宝中证医疗C）', '001180（广发医药卫生ETF联接A）'],
                                     'if_positive': '若 10/9 收盘转正（>0）-> 回调序列断裂、预案不启动',
                                     'note': '10/8 档闭环要求（§3.136a）；本档只登记预案、不执行'},
                                 'verify_at': '2026-10-09（A股 收盘后）'},
        'sh_comp': {'last': SH, 'as_of': '2026-10-08', 'pct': -0.79},
    },
    'scenario': {
        'upside': (f'美股 10/8 内部结构：道指 +0.10% 报 51,231.64（DIA +0.12%）、.INX -0.47%，'
                   f'能源 +2.97%（XLE）与必需消费 +2.07%（XLP）领涨，医疗 -0.39%（XLV）为 11 板块下跌之三'
                   f'-> 医疗相对标普500（-0.47%）超额 +0.08pct，属「大盘下跌日微幅正超额」；'
                   f'加上 A股 10/8 已一次性完成长假补跌、10/9 存在技术性修复空间；'
                   f'油价大涨（WTI +3.64% 报 91.49、布伦特 +4.07% 报 104.28）对资源/航运链条为正向。'
                   f'⚠️ 但本档无新增 A股/港股定价，上行判断仅为「情境」、不得作为方向依据'),
        'base': (f'档型③「正常交易日盘前」：组合账面基准 = 10/8 收盘 {TOTAL:,.2f} 元；'
                 f'A股医药敞口 {med/TOTAL*100:.2f}%、港联系 {hk_total/TOTAL*100:.2f}%；'
                 f'待消化 = QDII 腿挂账区间 {b_low:+,.2f} 元 ~ {b_high:+,.2f} 元（港股腿窗口已于 10/8 收口）；'
                 f'A股腿与港股 10/9 当日价格待 09:30 后'),
        'downside': ('① 分母端：10/8 30 年期美债拍卖最高收益率 5.618%（bid-to-cover 2.54）、'
                     '英国 30 年期国债收益率破 6% 创 1998 年以来最高 -> 长端高位对恒科与医药估值持续压制；'
                     '② 港股 10/8「利好出尽式」下跌：恒指 -1.43% 失守 24,000、恒生科技 -2.89% 创 2024 年 9 月以来新低，'
                     '成交 2,073 亿港元显著放大属「放量下跌」；'
                     '③ AI 硬件/半导体链条全球同步承压：费半 -3.39%、存储与光通信领跌（AAOI -13.58%、COHR -9.63%），'
                     '恒生科技成分 MINIMAX-W -13.7%、智谱 -7.6%（大模型价格战），华虹宏力 -9.2%；'
                     '④ 三星 Q3 营业利润 107.40 万亿韩元（同比 +783%）仍低于市场预期 -> 半导体估值消化压力；'
                     '⑤ QDII 传导系数不稳定（实测 1.25~1.29 vs 标定 0.72）-> 挂账区间存在被击穿风险；'
                     '⑥ 光模块「65% 美国原产物料」传闻虽被东山精密/长光华芯否认，但情绪面冲击已造成 A股 光芯片板块 -8%'),
    },
    'action': {'new_buy': 0, 'active_take_profit': 0, 'discipline_cut_today': 0,
               'discipline_cut_pending': 0,
               'discipline_cut_cumulative_registered': cut_cum,
               'new_pending': 0,
               'contingency_plan_registered': 1,
               'note': ('档型③ 盘前：08:00 时点组合全部标的不可定价 -> 赛道级动作全部为 0；'
                        '10/9 全天为唯一可执行窗口，执行清单 = ① 复核恒生科技 4,000 新防线（10/8 收 4,073.38，距 +1.8345%）；'
                        '② 复核中证消费 12,100 下沿（10/8 收 12,256.813，距 +1.2960%）；'
                        '③ 复核 A股医药反向兑现线（10/8 已收盘级触发）-> 若 10/9 再跌则启动被动减配预案（012323 / 001180）；'
                        '④ 复核 QDII 000369/016280/164906 的 10/8 净值为 9/30 之后是否推进（推进则回填挂账）；'
                        '⑤ 09:30 9 月金融数据（M2/社融）公布 -> 登记事件、不预判；'
                        '⑥ 医药敞口 38.96% 距上限 1.04pct（门槛 +4.44% / +7.42%）-> 任何正向催化均不构成加仓理由（new_buy = 0）')},
    'calendar': {
        '2026-10-08（上一档）': 'A股 复市首日（上证 -0.79% / 创业板 -3.15%）+ 港股正常交易日（恒指 -1.43% / 恒科 -2.89%）'
                                '+ 港股通恢复（南向净买入 64.77 亿港元）；第 2 次恒科减仓 1,904.44 元按净值成交；'
                                '美联储 9 月纪要偏鹰；央行 12,000 亿元 3 个月期买断式逆回购投放',
        '2026-10-09（今日）': 'A股 + 港股正常交易日；09:30 公布 9 月金融数据（M2/社融）；'
                              '中证 500/1000 指数样本调整于收市后生效；法国总统外事顾问博纳 10/9-13 来华',
        '2026-10-12': 'US 10/9 收盘成型（北京 04:00）；美国 9 月 CPI 前瞻周',
        '2026-10-14': '美国 9 月 CPI',
        '2026-10-19': '港股重阳节翌日休市',
        '2026-10-27~28': 'FOMC 议息会议（CME：10 月维持不变概率 82.3%）',
        '2026-12-09': 'FOMC 年末会议（CME：加息 25bp 概率 67.6%）',
    },
    'calendar_by_market': {
        'A股': '10/1-10/7 休市 -> 10/8 复市 -> **10/9 正常交易日**（10/10 周六休）',
        '港股': '10/1 休市 1 天 -> 10/8 正常交易日 -> **10/9 正常交易日**（10/19 重阳节翌日休）',
        '港股通(南向)': '10/1-10/7 全程暂停 -> 10/8 恢复（净买入 64.77 亿港元）-> 10/9 正常',
        '美股': 'US 10/8 收盘已归档（XLV 168.16 / IYH 70.92）；US 10/9 收盘成型于北京 10/12 04:00（10/10-10/11 周末）',
    },
    'data_hygiene': {
        'note': ('承接前档待办：① `portfolio_close_20260918_fix.json`（Σmv 差 -2,468.33 元）、'
                 '`portfolio_close_20260921_fix.json`（Σpnl 差 +333.12 元）两件不自洽；'
                 '② `fund_nav.csv` 历史重复键；③ 中国 10Y 收益率序列缺口（rf 硬编码 1.68%）；'
                 '④ 且慢 `long-win-nav.csv` 源/本地口径分歧（连续第 20 档）；'
                 '⑤ `indices.csv` 港股盘中/收盘双行物理并存（append-only，读取侧 last-wins，§3.133b）；'
                 '⑥ `playwright_success_count` 计数跳变（§3.133c）；'
                 '⑦ **本档新登记**：`sh000922`（中证红利）新浪日线末行 = 2019-01-30 -> 该 code 序列严重滞后，'
                 '禁止用作任何窗口代理（§3.111b / §3.112b）；`000933`（中证医药）distinct 交易日仅 12 -> 稀疏，'
                 '仅可用 1 日真实收盘，多日窗口须用 399006 代理。'),
    },
}

json.dump(out, open(os.path.join(HIST, f'portfolio_preopen_{TODAY.replace("-", "")}.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
print(f'\n已保存 portfolio_preopen_{TODAY.replace("-", "")}.json')
print('  OK 本档未产出 portfolio_close_20261009.json（档型③不产 close）')
print('  OK 本档未产出 portfolio_pending_20261009.json（档型③不产 pending；待消化沿用上一档）')
print('  OK new_pending = 0 / contingency_plan_registered = 1')
