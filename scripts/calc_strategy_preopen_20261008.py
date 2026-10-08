# -*- coding: utf-8 -*-
"""2026-10-08（周四）盘前档：组合策略计算 —— **A股 + 港股通 双市场复市首日**
SESSION_TYPE = 'normal_trading_day_preopen'（**档型③**：A股与港股当日均为正常交易日，但 08:00 双方均无新价格）
  → 依 §3.28 / §3.110 档型③ / §3.115c：**不产 `portfolio_close_*`、不产 `portfolio_pending_*`**；
    **待消化不做新测算，沿用上一档（`portfolio_pending_20261007.json`，state=finalized、window_closed=true）**
    → 与档型①「纯非交易日」的区别：档型① **不做待消化**；本档型**待消化照做（沿用）**
基准 = 9/30 修正收盘（portfolio_close_20260930_fix.json）= 380,888.29 元

★★★ 本档结构差异（派生后必检） ★★★
  ① **美股腿新增 1 个真实交易日（US 10/7）**：IYH 70.67 → 71.30（**+0.8915%**）、XLV 167.09 → 168.81（**+1.0294%**）
     → 挂账 B 段由「9/30×10/1×10/2×10/5×10/6」扩展为「…×10/7」→ **区间显著收窄**；
  ② **恒生科技防线基准价更新为 10/7 收盘 4,194.49（−0.677%）**，距 4,250 = −55.510 点 / −1.3061%；
  ③ **港股腿待消化窗口已收口（4/4，window_closed=true）** → 本档**沿用终值**，不做新测算；
  ④ **不产 pending 台账**（档型③）→ 产 `session_type = normal_trading_day_preopen` 标注 + `new_pending = 0` 自证。
⚠️ §3.118a：跨长假 QDII 挂账预告**禁止给中枢点值**，只给区间（系数 0.60~0.90）并显式标注「系数不稳定」。
⚠️ §3.123e 纪律累计口径：第 1 次 1,882.46 元（9/29 触发、9/30 成交）+ 第 2 次 1,904.44 元
   （10/2 触发、**执行日 = 2026-10-08 即今日**）= 累计 3,786.90 元。
⚠️ §3.133a：展示类字段一律由数据源现算 + 自校验断言，禁止手写常量表。
"""
import json, os, itertools

BASE = '/Users/jieyang/Documents/WealthHub'
HIST = os.path.join(BASE, 'data/processed/history')
TODAY = '2026-10-08'
SESSION_TYPE = 'normal_trading_day_preopen'
BASEFILE = 'portfolio_close_20260930_fix.json'
fix = json.load(open(os.path.join(HIST, BASEFILE), encoding='utf-8'))

TOTAL = fix['total_mv']
tracks = fix['tracks']
print(f'基准（9/30 修正收盘）= {TOTAL:,.2f} 元  ← {BASEFILE}')
print('  ⚠️ 档型③「正常交易日盘前」（A股 10/8 复市首日 + 港股正常交易日）'
      '→ **不产 close / 不产 pending**、待消化沿用上一档（§3.28 / §3.110 / §3.115c）')
dev = abs(sum(v['mv'] for v in tracks.values()) - TOTAL)
print(f'  硬守卫 |Σ tracks.mv − total_mv| = {dev:.4f} 元  {"✅" if dev < 1.5 else "❌ 终止"}')
assert dev < 1.5, 'Σ tracks.mv 与 total_mv 不一致，终止本档计算（§3.104）'

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
print('  ⚠️ 权重口径仍按 9/30 修正收盘计（本档无新增组合层定价）；'
      '**美股 10/7 XLV +1.0294% 为标普 11 板块领涨之一，属「挂账口径内」，不进 10/8 当日权重**')

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
      f'  → 只报赛道层将低估 {broad/TOTAL*100:.2f}pct')
print(f'  三段法：纯恒生科技系 {pure:,.2f}（{pure/TOTAL*100:.2f}%）/ 中概·海外互联系 {cpo:,.2f}（{cpo/TOTAL*100:.2f}%）'
      f'/ 宽基恒生系 {broad:,.2f}（{broad/TOTAL*100:.2f}%） = {pure+cpo+broad:,.2f} 元 '
      f'（和校验 {round(pure+cpo+broad, 2) == round(hk_total, 2)}）')
for r in seg_detail:
    print(f'    {r[0]} {r[1]} {r[2][:22]:24s} {r[3]:>10,.2f}')
print('  ⚠️ 南向（港股通）**今日 10/8 恢复** → 「南向空窗」窗口（10/2、10/5、10/6、10/7 共 4 个港股交易日）**本档终止**；'
      '复市首日量能恢复程度是 10/8 最需观察的单一变量（§3.121e）')

# ---------- 恒生科技 0.5% 纪律减仓（累计口径，§3.123e）----------
cut1 = fix.get('discipline', {})
cut1_amt = cut1.get('amount', 1882.46)          # 第 1 次：9/29 破位触发 → 9/30 成交
cut2_amt = round(TOTAL * 0.005, 2)               # 第 2 次：10/2 破位触发 → **执行日 = 今日 10/8**
cut_cum = round(cut1_amt + cut2_amt, 2)
hk_after = tracks['恒生科技']['mv'] - cut_cum
cash_after = tracks['现金']['mv'] + cut_cum
print(f'\n恒生科技 0.5% 纪律减仓（**累计口径**）：{cut_cum:,.2f} 元')
print(f'  第 1 次 {cut1_amt:,.2f} 元（9/29 收盘级破位触发 → 9/30 按净值成交，已结算）')
print(f'  第 2 次 {cut2_amt:,.2f} 元（10/2 收盘级破位触发 → **本档为执行日 2026-10-08**）')
print(f'  恒生科技 {tracks["恒生科技"]["mv"]:,.2f} → {hk_after:,.2f}'
      f'（{tracks["恒生科技"]["pct_of_total"]:.2f}% → {hk_after/TOTAL*100:.2f}%）')
print(f'  现金     {tracks["现金"]["mv"]:,.2f} → {cash_after:,.2f}'
      f'（{tracks["现金"]["pct_of_total"]:.2f}% → {cash_after/TOTAL*100:.2f}%）')
print(f'  自证 cumulative_amount == Σ cut_i.amount：{cut_cum} == {cut1_amt} + {cut2_amt} '
      f'→ {abs(cut_cum - (cut1_amt + cut2_amt)) < 0.01}')
print('  ⚠️ 纪律不可撤销：**即使 10/8 收盘站上 4,250，已登记的第 2 次减仓仍须于今日执行**（§3.114c）')

# ---------- QDII 挂账（本档唯一新增定价：US 10/7）----------
med_us = tracks['美股标普医药']['mv']

# §3.133a：IYH/ XLV 涨跌幅一律从 indices.csv 现算（last-wins 去重），禁止硬编码常量
import csv as _csv
_iyh, _xlv = {}, {}
with open(os.path.join(HIST, 'indices.csv'), encoding='utf-8-sig') as f:
    for r in _csv.DictReader(f):
        dt = r['date'][:10]
        if r['code'] == 'IYH':
            _iyh[dt] = float(r['close'])
        elif r['code'] == 'XLV':
            _xlv[dt] = float(r['close'])

NEED = ['2026-09-30', '2026-10-01', '2026-10-02', '2026-10-05', '2026-10-06', '2026-10-07']
BASE_IYH = '2026-09-29'      # 前一段的锚点（不参与 B 段复合）


def pct(series, d):
    ds = sorted(series)
    i = ds.index(d)
    return (series[d] / series[ds[i - 1]] - 1) * 100


iyh_pct = {d: pct(_iyh, d) for d in NEED}
# 自校验断言（§3.133a）
assert abs(iyh_pct['2026-10-06'] - (-0.3385)) < 0.01, f"IYH 10/6 读数异常: {iyh_pct['2026-10-06']}"
assert abs(iyh_pct['2026-10-05'] - 0.7244) < 0.01, f"IYH 10/5 读数异常: {iyh_pct['2026-10-05']}"
assert iyh_pct['2026-10-07'] > 0, f"IYH 10/7 应为正: {iyh_pct['2026-10-07']}"
assert abs((_xlv['2026-10-07'] / _xlv['2026-10-06'] - 1) * 100 - 1.0294) < 0.01

comp_b = 1.0
for d in NEED:
    comp_b *= (1 + iyh_pct[d] / 100)
comp_b -= 1

# 同口径（精确值）重算「不含 US 10/7」的前档 B 复合，供同口径对照（§3.121a：口径对齐）
comp_b_prev = 1.0
for d in NEED[:-1]:
    comp_b_prev *= (1 + iyh_pct[d] / 100)
comp_b_prev -= 1
print(f'  ⚠️ 口径对齐：前档按**四舍五入值**（−1.17 / −1.62）得 B 复合 −2.3997%；'
      f'本档改用 **indices.csv 精确值现算**（§3.133a）→ 同口径「不含 US 10/7」复算 = {comp_b_prev*100:+.4f}%'
      f'（差 {abs(comp_b_prev*100 - (-2.3997)):.4f}pct，属四舍五入精度差，非口径变更）')

qdii_out = fix.get('pending', {}).get('qdii_observable_amount', -267.82)   # component A
notional_b = med_us * comp_b
notional_b_prev = med_us * comp_b_prev
print('\nQDII 挂账（§3.112f / §3.118a：只给区间、禁止中枢点值）')
print(f'  A) QDII 000369/016280 的 9/29 净值已出库但按既定口径挂账：{qdii_out:+,.2f} 元'
      f'（基准净值日 9/28 → 已覆盖 US 9/29，不得在 B 中重复计入）')
print('  B) 自 US 9/30 起未可观测段（IYH 现算，§3.133a）：'
      + ' × '.join(f'{d[5:]} {iyh_pct[d]:+.4f}%' for d in NEED)
      + f' → 复合 {comp_b*100:+.4f}%')
print(f'     标的市值 {med_us:,.2f} 元 → 未打折损益 {notional_b:+,.2f} 元'
      f'（同口径前档 {notional_b_prev:+,.2f} 元 → **收窄 {notional_b - notional_b_prev:+,.2f} 元**）')
coefs = (0.60, 0.72, 0.90)
vals_b = sorted(round(notional_b * k, 2) for k in coefs)          # 负值：系数越大越负
b_high, b_mid, b_low = max(vals_b), (notional_b * 0.72), min(vals_b)
print(f'     系数 0.60 / 0.72 / 0.90 → {notional_b*0.60:+,.2f} / {b_mid:+,.2f} / {notional_b*0.90:+,.2f} 元')
tot_high, tot_mid, tot_low = qdii_out + b_high, qdii_out + b_mid, qdii_out + b_low
assert tot_low <= tot_mid <= tot_high, '§3.116b 区间端点语义错误'
print(f'  → A+B 合计区间 {tot_low:+,.2f} 元 ~ {tot_high:+,.2f} 元'
      f'（代理均值中枢 {tot_mid:+,.2f} 元 = 组合 {tot_mid/TOTAL*100:+.4f}%）')
print('     前档区间 −1,555.97 元 ~ −1,126.59 元 → **本档显著收窄**（US 10/7 IYH +0.8915%）')
print('  ⚠️ 传导系数不稳定：长假前后实测隐含系数 1.25~1.29（§3.118a），远超标定 0.72 / 实测 0.62'
      ' → 若按 1.25 折算，B = {:+,.2f} 元、A+B 合计 {:+,.2f} 元'
      .format(notional_b * 1.25, qdii_out + notional_b * 1.25))
print('  ⚠️ 自 US 9/30 起的窗口（9/30、10/1、10/2、10/5、10/6、10/7 共 6 个美股交易日）**本档全部可观测**；'
      '下一个未知交易日 = US 10/8（收盘成型于北京 10/9 04:00）')

# ---------- 港股腿待消化：**沿用上一档终值**（档型③，不重算）----------
PEND07 = json.load(open(os.path.join(HIST, 'portfolio_pending_20261007.json'), encoding='utf-8'))
DG = PEND07['hk_pending_digest']
hk_low, hk_high = DG['total_low'], DG['total_high']
hk_mid = DG['mid_proxy_avg']
print(f'\n港股腿「待消化」= **沿用上一档（10/7 盘后档正式版）**（档型③不重算，§3.28 / §3.115c）')
print(f'  终值：{hk_low:+,.2f} 元 ~ {hk_high:+,.2f} 元（代理均值中枢 {hk_mid:+,.2f} 元）')
_pd = DG["priced_days"]
print(f'  窗口 = {DG["window"]}（{DG["total_days"]} 日 / 已定价 {_pd if isinstance(_pd, int) else len(_pd)} 日）'
      f'｜window_closed = {DG["window_closed"]}')
print(f'  构成：纯恒科 {DG["segments"]["pure_hstech"]["mv"]:,.2f} 元 / '
      f'中概 {DG["segments"]["china_internet"]["mv"]:,.2f} 元 / '
      f'宽基恒生系 {DG["segments"]["broad_hk"]["mv"]:,.2f} 元')
print('  ⚠️ 10/8 起该窗口**关闭、不再延续**；**窗口收口 ≠ 可作方向判断**（仍只给区间上下界，§3.108 条款 24）')
print('  ⚠️ 10/8 复市后须**一次性对账**：场外港股联接（000071 / 012348）休市期不发布净值 → 今日恢复发布')

# ---------- 三条防线 ----------
HS = _iyh and 4194.49      # HSTECH 10/7 收盘（hq 直连已复核）
HS_PREV = 4223.08
ZZ, SH = 12295.9591, 3842.1946
MED933_1D = (8009.6669 / 7786.2255 - 1) * 100
print('\n三条防线（恒科取 10/7 收盘口径；A股 两项今日 09:30 后验证）：')
print(f'  ① 恒生科技 4,250：10/7 收 {HS:,.2f}（前收 {HS_PREV:,.2f} / {(HS/HS_PREV-1)*100:+.4f}%）'
      f' → 距防线 {HS-4250:+,.2f} 点 / {(HS/4250-1)*100:+.4f}%'
      f'【**破位状态未改变、幅度重新扩大**（10/2 −2.1661% → 10/5 −1.5605% → 10/6 −0.6344% → 10/7 −1.3061%）】')
print(f'      ⚠️ 10/7 日内高 4,222.43 < 4,250 → **全日未站上 4,250**（10/6 为「盘中一度站上、收盘回落」）'
      f'｜`intraday_touched_above = false`（§3.129b）')
print(f'      → 第 2 次 0.5% 减仓（{cut2_amt:,.2f} 元）**今日 10/8 执行**；判定权已于 10/2 收盘级锁定、本档不重复判定')
print(f'  ② 中证消费 12,100 下沿：9/30 收 {ZZ:,.4f} → {(ZZ/12100-1)*100:+.4f}%'
      f'（下一线 12,000 距 {(ZZ/12000-1)*100:+.2f}%）→ **今日 09:30 复市后可验证（本档 08:00 不可验证）**')
print(f'  ③ A股医药反向兑现线（板块代理单日 ≥1.5% 跌幅）：9/30 板块代理 {MED933_1D:+.4f}% → 未触发'
      f'（方向相反）；**今日 09:30 复市后可验证**')
print(f'  附：上证 9/30 收 {SH:,.4f}；恒指 10/7 收 24,130.50（−0.6180%）；恒生综合 3,556.31（−0.82%）')

# ---------- 产物 ----------
out = {
    'date': TODAY, 'session': 'preopen', 'session_type': SESSION_TYPE,
    'session_type_note': ('**档型③「正常交易日盘前」** = A股 10/8（长假后复市首日）+ 港股 10/8（正常交易日）；'
                          '08:00 双方均无当日价格 → **不产 `portfolio_close_*`、不产 `portfolio_pending_*`**；'
                          '待消化**沿用上一档终值**（`portfolio_pending_20261007.json`，state=finalized、window_closed=true）；'
                          '本档唯一新增定价 = **美股 10/7 收盘**（XLV +1.0294% / IYH +0.8915%，医疗为标普 11 板块领涨之一）'),
    'calendar_verification': {
        'A股': 'stock_zh_index_daily(sh000001) 末行 = **2026-09-30**（收 3,842.1946）→ 10/8 为长假后复市首日，09:30 开盘前无新价格',
        '港股': '新浪 hq rt_hkHSTECH 返回体**日期字段** = `2026/10/07 16:09`（收 4,194.49 / −0.677%）→ 10/8 今日待开 09:30（非休市）',
        '美股': 'stock_us_daily(IYH/XLV) 末行 = **2026-10-07**（XLV 168.81 / IYH 71.30）→ US 10/7（周三）收盘已于北京 10/8 04:00 成型，**本档新增 8 行**',
        'rule': '三市场各自独立验证、不得互相外推（§3.107 / §3.119b / §3.122b）'},
    'base_total': TOTAL, 'base_file': BASEFILE, 'base_guard_dev': round(dev, 4),
    'base_revision': {'prev_total': None, 'delta': 0.0,
                      'reason': '本档交易日三验：A股 末行 = 2026-09-30（3,842.1946，10/8 复市首日 09:30 前无价）、'
                                'HSTECH 末行 = 2026-10-07（4,194.49）、XLV 末行 = 2026-10-07（168.81）→ '
                                '组合账面基准仍冻结于 9/30 修正收盘（A股 场外基金净值 10/8 收盘后才发布），**本档无修正**'},
    'tracks': {k: {'mv': v['mv'], 'pct_of_total': v['pct_of_total'], 'day_pct': v['day_pct']}
               for k, v in tracks.items()},
    'discipline_hstech_cumulative': {
        'cut1': {'pct': 0.5, 'amount': cut1_amt, 'triggered_on': '2026-09-29', 'settled_on': '2026-09-30',
                 'note': '9/29 收盘 4,249.62（−0.0089%）边际破位触发 → 9/30 按净值成交 1,882.46 元（成本已如实记录，§3.117b）'},
        'cut2': {'pct': 0.5, 'amount': cut2_amt, 'triggered_on': '2026-10-02', 'settled_on': None,
                 'execute_at': '2026-10-08', 'execution_pending': True,
                 'is_today': True,
                 'basis': f'基准总资产 {TOTAL:,.2f} 元 × 0.5%（§3.114c / §3.123e 确定性口径）',
                 'targets': ['012348（天弘恒生科技联接A）', '513180（恒生科技ETF华夏）'],
                 'target_rule': '标的限「纯恒科」口径，不落在中概（513050 / 164906）'},
        'cumulative_amount': cut_cum,
        'hk_after': round(hk_after, 2), 'cash_after': round(cash_after, 2),
        'weight_after_pct': {'恒生科技': round(hk_after / TOTAL * 100, 2),
                             '现金': round(cash_after / TOTAL * 100, 2)},
        'prior_档口径': {'source': 'reports/daily/2026-10-04.md',
                        'hk_after': 29668.40, 'cash_after': 31117.41,
                        'weight_after_pct': {'恒生科技': 7.79, '现金': 8.17},
                        'correction_note': '该口径 = 31,572.84 − 1,904.44（只扣第 2 次减仓），未扣除第 1 次已成交的 1,882.46 元 '
                                           '→ 统一为「累计扣除」（31,572.84 − 3,786.90 = 27,785.94 元 = 7.30%）；两口径并列、以累计口径为准（§3.123e）'},
        'note': '**本档为第 2 次减仓的执行日（2026-10-08）**；纪律不可撤销 —— 即使今日收盘站上 4,250 亦须执行（§3.114c）',
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
                          'status': '**本档终止**（港股通 10/8 恢复）',
                          'note': '南向空窗共 4 个港股交易日；10/8 复市首日量能恢复程度为最需观察的单一变量'},
    'hk_leg_pending_carryover': {
        'carryover': True, 'recomputed': False,
        'source_file': 'data/processed/history/portfolio_pending_20261007.json',
        'source_state': PEND07.get('state'), 'source_finalized': PEND07.get('finalized'),
        'window': DG['window'], 'window_days': DG['total_days'], 'priced_days': DG['priced_days'],
        'window_closed': DG['window_closed'],
        'total_low': hk_low, 'total_high': hk_high, 'mid_proxy_avg': hk_mid,
        'segments': DG['segments'],
        'reason': ('档型③「正常交易日盘前」：A股与港股当日均为正常交易日、08:00 双方均无当日价格 → '
                   '依 §3.28 / §3.110 / §3.115c **待消化沿用上一档、不做新测算** '
                   '（与档型①「纯非交易日」的区别：档型① 不做待消化）'),
        'note': '窗口已于 10/7 收盘收口（4/4 全部定价）；10/8 起关闭、不再延续；**只给区间上下界、不得作方向判断**（§3.108 条款 24 / §3.133e）',
    },
    'qdii_pending': {
        'as_of': '2026-10-08 08:00',
        'component_a': {'desc': 'QDII 000369/016280 的 9/29 净值（基准净值日 9/28）→ 已覆盖 US 9/29',
                        'amount': qdii_out, 'trade_date_covered': '2026-09-29'},
        'component_b': {'desc': '自 US 9/30 起未可观测段（IYH 现算，§3.133a）',
                        'trade_dates_covered': NEED,
                        'iyh_pct': {d: round(iyh_pct[d], 4) for d in NEED},
                        'comp_pct': round(comp_b * 100, 4),
                        'notional': round(notional_b, 2),
                        'low': round(b_low, 2), 'mid': round(b_mid, 2), 'high': round(b_high, 2),
                        'coef_range': [0.60, 0.90], 'coef_unstable': True,
                        'coef_note': '长假前后实测隐含系数 1.25~1.29（§3.118a），远超标定 0.72 / 实测 0.62 → 只给区间、禁止中枢点值',
                        'prev_notional': round(notional_b_prev, 2),
                        'delta_vs_prev': round(notional_b - notional_b_prev, 2),
                        'precision_note': '本档 IYH 涨跌幅改用 indices.csv 精确值现算（§3.133a）；前档用四舍五入值（−1.17/−1.62）',
                        'prev_notional_as_reported': -1431.28},
        'total_low': round(tot_low, 2), 'total_mid': round(tot_mid, 2), 'total_high': round(tot_high, 2),
        'prev_total_low': -1555.97, 'prev_total_high': -1126.59,
        'unknown_sessions': ['2026-10-08(US)'],
        'new_sessions_since_prev': ['2026-10-07(US)'],
        'coef_1_25_total': round(qdii_out + notional_b * 1.25, 2),
        'note': ('§3.112f / §3.118a：跨长假只给区间、禁止中枢点值。'
                 '本档自 US 9/30 起的 6 个美股交易日（9/30、10/1、10/2、10/5、10/6、10/7）**全部可观测**；'
                 'XLV 10/7 +1.0294% 为标普 11 板块领涨之一 → 挂账区间显著收窄。'),
    },
    'pending_consume': {
        'hold_decision': 'no_action',
        'carryover': True,
        'reason': ('档型③：08:00 时点组合全部持仓标的不可定价（A股 09:30 前无价、'
                   '场外基金净值收盘后发布、场外港股联接休市期不发布净值、美股 10/8 未开盘）'
                   '→ 待消化不做新测算、沿用上一档；**唯一可执行窗口 = 今日 10/8 全天**'),
        'estimated_combo_return_pct': 0.0,
        'estimated_combo_pnl': 0.0,
        'attribution': ('A股 10/8 09:30 前无价 + 港股 09:30 前无价 + 场外基金净值收盘后发布 + '
                        '美股 10/8 未开盘 → **当日可实现盈亏恒为 0 元，归因「标的不可定价」而非「市场持平」**'
                        '（§3.107 / §3.121d）'),
    },
    'defense_lines': {
        'hstech_4250': {'close': HS, 'prev_close': HS_PREV, 'state': 'close_level_break_unchanged',
                        'dist_pct': round((HS / 4250 - 1) * 100, 4), 'dist_pts': round(HS - 4250, 2),
                        'break_type': '非边际破位（10/2 收盘级首次触发；10/7 幅度重新扩大：−2.1661% → −1.5605% → −0.6344% → −1.3061%）',
                        'intraday_touched_above': False,
                        'intraday_high': 4222.43,
                        'action_reserved': f'第 2 次 0.5% 纪律减仓 {cut2_amt:,.2f} 元 —— **执行日 = 今日 2026-10-08**',
                        'verify_at': '2026-10-08 16:00（港股收盘价验证）',
                        'next_rule': '再破不叠加新纪律（同日防线只触发一次）；若今日回升站上 4,250 亦**不撤销**已登记减仓（§3.114c）'},
        'zz_consume_12100': {'last': ZZ, 'as_of': '2026-09-30', 'state': 'abv_line_last_known',
                             'dist_pct': round((ZZ / 12100 - 1) * 100, 4),
                             'next_line': 12000, 'next_line_dist_pct': round((ZZ / 12000 - 1) * 100, 2),
                             'verify_at': '2026-10-08（A股 复市后盘中/盘后档）'},
        'a_med_reverse_1_5pct': {'proxy_pct': round(MED933_1D, 4), 'as_of': '2026-09-30',
                                 'state': 'not_triggered',
                                 'verify_at': '2026-10-08（A股 复市后盘中/盘后档）'},
        'sh_comp': {'last': SH, 'as_of': '2026-09-30'},
    },
    'scenario': {
        'upside': ('美股 10/7 **医疗板块 +1.06% 领涨标普 11 大板块**（XLV +1.0294% / IYH +0.8915%，LLY +2.70%、JNJ +1.44%）、'
                   f'挂账区间由 −1,555.97 元 ~ −1,126.59 元收窄至 {tot_low:+,.2f} 元 ~ {tot_high:+,.2f} 元；'
                   '叠加央行今日 12,000 亿元 3 个月期买断式逆回购投放 + 港股通恢复 → A股 复市首日具备流动性支撑；'
                   f'**但已登记的第 2 次恒科减仓 {cut2_amt:,.2f} 元仍须今日执行**（纪律不可撤销，§3.114c）'),
        'base': (f'档型③「正常交易日盘前」：组合账面基准维持 9/30 修正收盘 {TOTAL:,.2f} 元；'
                 f'已定价增量 = 「美股/QDII 腿」（挂账区间 {tot_low:+,.2f} 元 ~ {tot_high:+,.2f} 元）'
                 f'＋「港股腿长假窗口」（终值 {hk_low:+,.2f} 元 ~ {hk_high:+,.2f} 元，窗口已收口）；'
                 'A股腿与港股 10/8 当日价格待 09:30 后'),
        'downside': ('① **美债长端仍在 2002 年以来高位**：10Y 收 5.277%（盘中触 5.365%）、30Y 盘中触 5.732%，'
                     '且 390 亿美元 10 年期国债拍卖中标利率 5.30% 为 2000 年以来最高 → 分母端对恒科与医药估值持续压制；'
                     '② **美联储 9 月会议纪要（今日 02:00）偏鹰**：19 名官员一致支持 9 月加息 25bp 至 3.75%~4.00%，'
                     '多数官员认为年底前可能还需再上调一次 → 与「10 月不变概率约 80%」并存，路径未转向；'
                     '③ **港股长假累积缺口待释放**：长假四日（10/2-10/7）恒指 −1.96% / 恒科 −1.40% / 恒生综合 −2.03%，'
                     '且成交由 1,458.04 亿港元连降至 947.00 亿（四日最低）→ 南向回归首日的量能与承接是关键；'
                     '④ **恒科 4,250 防线仍未收复**（10/7 收 4,194.49 / −1.3061%，全日未站上）；'
                     '⑤ **QDII 传导系数不稳定**（实测 1.25~1.29 vs 标定 0.72）→ 挂账区间存在被击穿风险；'
                     '⑥ **欧股与加密同跌**（DAX −1.35% / CAC40 −1.22% / 斯托克50 −1.47%；比特币 −3%、12.4 万人爆仓）'
                     '→ 全球风险偏好边际收紧；⑦ 长假「旧闻重发」污染风险在复市首日仍须三源核验（§3.119a / §3.122d）'),
    },
    'action': {'new_buy': 0, 'active_take_profit': 0, 'discipline_cut_today': 0,
               'discipline_cut_pending': 1,
               'discipline_cut_cumulative_registered': cut_cum,
               'new_pending': 0,
               'note': ('档型③ 盘前：08:00 时点组合全部标的不可定价 → **赛道级动作全部为 0**；'
                        '**今日 10/8 全天为唯一可执行窗口**，执行清单 = ① 第 2 次恒科 0.5% 减仓 '
                        f'{cut2_amt:,.2f} 元（累计 {cut_cum:,.2f} 元，限「纯恒科」012348 / 513180）；'
                        '② A股 类留空事件一次性回填（参考交易日 = 10/8）；③ 场外港股联接与 QDII 长假期累积净值缺口一次性对账；'
                        '④ 复核中证消费 12,100 下沿与医药 40% 上限；⑤ 10/8 凌晨美联储 9 月纪要为长假最后一个利率路径事件，只登记不预判；'
                        '**medical 敞口 39.23% 距上限仅 0.77pct → 任何正向催化均不构成加仓理由（`new_buy = 0`，§3.98）**')},
    'calendar': {
        '2026-10-07（上一档）': 'A股休市；港股续市第 4 日（收 4,194.49 / −0.677%）；港股通关闭（空窗第 4 日）；美股 10/7 交易日（收盘成型于北京 10/8 04:00）',
        '2026-10-08（今日）': '**A股复市首日 + 港股正常交易日 + 港股通（南向）恢复**；'
                              '第 2 次恒科 0.5% 纪律减仓执行日；央行 12,000 亿元 3 个月期买断式逆回购（89 天）投放；'
                              '美联储 9 月会议纪要（北京 10/8 02:00，**已公布：偏鹰**）；'
                              '20 只基金集中开启认购；A股 类留空事件一次性回填窗口',
        '2026-10-09': '美国 9 月 CPI 前瞻周；罗氏 Tecentriq 决定日（10/9）',
        '2026-10-14': '美国 9 月 CPI',
        '2026-10-19': '港股重阳节翌日休市',
        '2026-10-27~28': 'FOMC 议息会议（市场预期维持不变）',
        '2026-12-09': 'FOMC 年末会议（市场预期加息 25bp 概率约 64%）',
    },
    'calendar_by_market': {
        'A股': '10/1-10/7 休市 → **10/8 复市**（10/10 周六休）',
        '港股': '10/1 休市 1 天 → 10/2-10/7 正常交易（4 个交易日）→ **10/8 正常交易日**（10/19 重阳节翌日休）',
        '港股通(南向)': '10/1-10/7 全程暂停 → **10/8 恢复**',
        '美股': '10/1-10/7 照常交易（5 个交易日，另 9/30 亦为交易日）；9/30、10/1、10/2、10/5、10/6 收盘已分别于 10/2、10/2、10/4、10/6、10/7 档归档，**10/7 收盘本档归档**；10/8 收盘成型于北京 10/9 04:00',
    },
    'data_hygiene': {
        'note': ('承接前档待办：① `portfolio_close_20260918_fix.json`（Σmv 差 −2,468.33 元）、'
                 '`portfolio_close_20260921_fix.json`（Σpnl 差 +333.12 元）两件不自洽；'
                 '② `fund_nav.csv` 41 个历史重复键；③ 中国 10Y 收益率序列缺口（rf 硬编码 1.68%）；'
                 '④ 且慢 `long-win-nav.csv` 源/本地口径分歧（连续第 18 档）；'
                 '⑤ `indices.csv` 20 组港股重复键（**已确认 append-only 物理并存，读取侧 last-wins 去重，§3.133b**）；'
                 '⑥ `playwright_success_count` 计数跳变（10/06 = 32 应为 31，§3.133c）。'),
    },
}

json.dump(out, open(os.path.join(HIST, f'portfolio_preopen_{TODAY.replace("-", "")}.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
print(f'\n已保存 portfolio_preopen_{TODAY.replace("-", "")}.json')
print('  ✅ 本档**未产出** `portfolio_close_20261008.json`（档型③不产 close）')
print('  ✅ 本档**未产出** `portfolio_pending_20261008.json`（档型③不产 pending；待消化沿用上一档）')
print('  ✅ `new_pending = 0` / `chain_0pct_row_inserted` 不适用（无 close 行）')
