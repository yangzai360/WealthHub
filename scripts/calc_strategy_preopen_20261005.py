# -*- coding: utf-8 -*-
"""2026-10-05（周一 · 国庆长假第 5 日 · **混合档**：A股休市 + 港股续市）盘前档：组合策略计算
SESSION_TYPE = 'mixed_day_preopen'（档型②：A股休市 + 港股开市 → §3.108 条款 22 / AGENTS #22 / §3.121b）
基准 = 9/30 修正收盘（portfolio_close_20260930_fix.json）= 380,888.29 元
输出：
  - portfolio_preopen_20261005.json —— 敞口、门槛方程、港联系三层拆解、**待消化（mixed-day）**、防线台账、日历
  - portfolio_pending_20261005.json —— 混合档台账（**state = preopen_estimate / finalized = false**，
    港股 10/5 收盘价 16:00 后成型 → 由 10/5 20:00 盘后档覆盖为正式版）
⚠️ 档型②（混合档：A股休市 + 港股开市）→ **必做待消化测算**（§3.108 条款 22）。
   ⚠️ 时段归属澄清：08:00 盘前时刻港股尚未开盘 → 本档 pending 仅含
      「美股/QDII 腿」（已定价）与「港股腿（未定价）」两段，港股段显式标 `priced: false`。
⚠️ §3.107：QDII/LOF 券「基准已含哪一日净值」从 price_src 字符串解析，不得用固定日期常量。
⚠️ §3.118a：跨长假 QDII 挂账预告**禁止给中枢点值**，只给区间（系数 0.60~0.90）并显式标注「系数不稳定」。
⚠️ 本档口径更正（§3.123e 精神）：**纪律类金额须「累计扣除」** ——
   第 1 次 1,882.46 元（9/29 破位触发、9/30 成交）+ 第 2 次 1,904.44 元（10/2 破位触发、执行待 10/8）
   = 累计 3,786.90 元；10/4 档曾记「纪律后 29,668.40 元 = 7.79% / 现金 31,117.41 元 = 8.17%」，
   该口径**只扣第 2 次、未扣已成交的第 1 次** → 本档显式更正并统一为「累计扣除」。
"""
import json, os

BASE = '/Users/jieyang/Documents/WealthHub'
HIST = os.path.join(BASE, 'data/processed/history')
TODAY = '2026-10-05'
SESSION_TYPE = 'mixed_day_preopen'
BASEFILE = 'portfolio_close_20260930_fix.json'
fix = json.load(open(os.path.join(HIST, BASEFILE), encoding='utf-8'))

TOTAL = fix['total_mv']
tracks = fix['tracks']
print(f'基准（9/30 修正收盘）= {TOTAL:,.2f} 元  ← {BASEFILE}')
print('  ⚠️ 档型②「混合档」（A股 10/1-10/7 休市 + 港股 10/5 续市）'
      '→ 产 pending 台账、**必做待消化**（§3.108 条款 22 / §3.121b）')
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
print('  ⚠️ 本档两医药赛道（A股 + 美股）均**无新增定价**（A股休市、美股 10/3-10/4 周末）'
      '→ 门槛沿用 10/2/10/4 档口径、方向上不收紧')

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
print('  ⚠️ 港联系「南向空窗」= 10/2、10/5、10/6、10/7 共 4 个港股交易日（港股通 10/1-10/7 关闭）'
      '→ 本档进入**第 2 个**空窗交易日，波动率须按「外资主导」建模（§3.113a/§3.115d/§3.121e）')

# ---------- 恒生科技 0.5% 纪律减仓（累计口径，§3.123e）----------
cut1 = fix.get('discipline', {})
cut1_amt = cut1.get('amount', 1882.46)          # 第 1 次：9/29 破位触发 → 9/30 成交
cut2_amt = round(TOTAL * 0.005, 2)               # 第 2 次：10/2 破位触发 → 执行待 10/8
cut_cum = round(cut1_amt + cut2_amt, 2)
hk_after = tracks['恒生科技']['mv'] - cut_cum
cash_after = tracks['现金']['mv'] + cut_cum
print(f'\n恒生科技 0.5% 纪律减仓（**累计口径**）：{cut_cum:,.2f} 元')
print(f'  第 1 次 {cut1_amt:,.2f} 元（9/29 收盘级破位触发 → 9/30 按净值成交，已结算）')
print(f'  第 2 次 {cut2_amt:,.2f} 元（10/2 收盘级破位触发 → 判定已成立，**执行待 10/8**）')
print(f'  恒生科技 {tracks["恒生科技"]["mv"]:,.2f} → {hk_after:,.2f}'
      f'（{tracks["恒生科技"]["pct_of_total"]:.2f}% → {hk_after/TOTAL*100:.2f}%）')
print(f'  现金     {tracks["现金"]["mv"]:,.2f} → {cash_after:,.2f}'
      f'（{tracks["现金"]["pct_of_total"]:.2f}% → {cash_after/TOTAL*100:.2f}%）')
print('  ⚠️ 口径更正：10/4 档曾记「纪律后 29,668.40 元 = 7.79% / 现金 31,117.41 元 = 8.17%」，'
      '该值 = 31,572.84 − 1,904.44（**只扣第 2 次、漏扣第 1 次已成交**）→ 本档统一为累计扣除并一并披露两个口径')

# ---------- 待消化（混合档核心；§3.112f / §3.123b 只给区间、不给方向）----------
med_us = tracks['美股标普医药']['mv']
IYH_0930, IYH_1001, IYH_1002 = -1.17, -1.62, 0.00
comp_b = (1 + IYH_0930 / 100) * (1 + IYH_1001 / 100) * (1 + IYH_1002 / 100) - 1   # 自 US 9/30 起（A 已覆盖 9/29）
qdii_out = fix.get('pending', {}).get('qdii_observable_amount', -267.82)   # component A
notional_b = med_us * comp_b
print('\n待消化 / 挂账（混合档 = 必做；§3.112f / §3.118a：只给区间、禁止中枢点值）')
print(f'  A) QDII 000369/016280 的 9/29 净值已出库但按既定口径挂账：{qdii_out:+,.2f} 元'
      f'（基准净值日 9/28 → 已覆盖 US 9/29，不得在 B 中重复计入）')
print(f'  B) 自 US 9/30 起未可观测段：IYH 9/30 {IYH_0930:+.2f}% × 10/1 {IYH_1001:+.2f}% × 10/2 {IYH_1002:+.2f}%'
      f' → 复合 {comp_b*100:+.4f}%')
print(f'     标的市值 {med_us:,.2f} 元 → 未打折损益 {notional_b:+,.2f} 元')
coefs = (0.60, 0.72, 0.90)
vals_b = sorted(round(notional_b * k, 2) for k in coefs)          # 负值：系数越大越负
b_high, b_mid, b_low = max(vals_b), (notional_b * 0.72), min(vals_b)
print(f'     系数 0.60 / 0.72 / 0.90 → {notional_b*0.60:+,.2f} / {b_mid:+,.2f} / {notional_b*0.90:+,.2f} 元')
tot_high, tot_mid, tot_low = qdii_out + b_high, qdii_out + b_mid, qdii_out + b_low
print(f'  → A+B 合计区间 {tot_high:+,.2f} 元 ~ {tot_low:+,.2f} 元（中枢 {tot_mid:+,.2f} 元 = 组合 {tot_mid/TOTAL*100:+.4f}%）')
print('  ⚠️ 传导系数不稳定：长假前后实测隐含系数 1.25~1.29（§3.118a），远超标定 0.72 / 实测 0.62'
      ' → 若按 1.25 折算，B = {:+,.2f} 元、A+B 合计 {:+,.2f} 元，**区间上/下界均可能被击穿**'
      .format(notional_b * 1.25, qdii_out + notional_b * 1.25))
print('  ⚠️ 仍未量化：US 10/5、10/6、10/7 共 3 个美股交易日完全未知（US 10/2 已含 0.00%）')
print('  ⚠️ 港股腿（港联系 {:.2f} 元 = {:.2f}%）本档**未定价**：港股 10/5 09:30 开盘、16:00 收盘'
      ' → 待 20:00 盘后档以实际收盘价计入'.format(hk_total, hk_total / TOTAL * 100))

# ---------- 港股腿「已定价段」的三段法区间（§3.123b：对合计值取 min/max）----------
SEG_1002 = {
    'pure_ret': -2.2556,
    'concept_ret': (-2.8087, -2.3517),      # 最差（8 名等权）/ 最优（6 名大市值平台）
    'broad_ret': (-2.6042, -2.5776),        # 最差（恒生指数）/ 最优（恒生综合）
}
outs = []
for pr in (SEG_1002['pure_ret'],):
    for cr in SEG_1002['concept_ret']:
        for br in SEG_1002['broad_ret']:
            outs.append(round(pure * pr / 100 + cpo * cr / 100 + broad * br / 100, 2))
hk1002_low, hk1002_high = min(outs), max(outs)
hk1002_mid = round(sum(outs) / len(outs), 2)
assert hk1002_low <= hk1002_mid <= hk1002_high, '§3.123b 区间端点语义错误'
print(f'\n港股腿「已定价段」= 10/2（累积窗口第 1 日 / 共 4 日）：{hk1002_low:+,.2f} 元 ~ {hk1002_high:+,.2f} 元'
      f'（代理均值中枢 {hk1002_mid:+,.2f} 元，共 {len(outs)} 组笛卡尔积）')
print(f'  纯恒科 {pure:,.2f} × {SEG_1002["pure_ret"]:+.4f}% = {pure*SEG_1002["pure_ret"]/100:+,.2f} 元')
print(f'  中概   {cpo:,.2f} × [{SEG_1002["concept_ret"][0]:+.4f}%, {SEG_1002["concept_ret"][1]:+.4f}%]'
      f' = {cpo*SEG_1002["concept_ret"][1]/100:+,.2f} 元 ~ {cpo*SEG_1002["concept_ret"][0]/100:+,.2f} 元')
print(f'  宽基   {broad:,.2f} × [{SEG_1002["broad_ret"][0]:+.4f}%, {SEG_1002["broad_ret"][1]:+.4f}%]'
      f' = {broad*SEG_1002["broad_ret"][0]/100:+,.2f} 元 ~ {broad*SEG_1002["broad_ret"][1]/100:+,.2f} 元')
print('  ⚠️ 10/5 段（第 2 日）08:00 尚无收盘价 → **不可测算**，待 20:00 盘后档；'
      '累积区间 = 上述值 + 10/5 未知项（禁止作方向判断，§3.108 条款 24）')

# ---------- 三条防线（10/2 收盘口径 + 本档可验证项分列）----------
HS, ZZ, SH, HS_PREV = 4157.94, 12295.9591, 3842.1946, 4253.89
MED933_1D = (8009.6669 / 7786.2255 - 1) * 100
print('\n三条防线（10/2 收盘口径；本档可验证项分列）：')
print(f'  ① 恒生科技 4,250：10/2 收 {HS:,.2f} → {(HS/4250-1)*100:+.4f}%'
      f'【**非边际破位**（距防线 {HS-4250:,.2f} 点）】→ 第 2 次 0.5% 减仓（{cut2_amt:,.2f} 元）'
      f'**判定已成立、执行待 10/8**；**本档不重复判定**（§3.114c/§3.123a）')
print(f'  ② 中证消费 12,100 下沿：9/30 收 {ZZ:,.4f} → {(ZZ/12100-1)*100:+.4f}%'
      f'（下一线 12,000 距 {(ZZ/12000-1)*100:+.2f}%）→ **A股休市，10/5 不可验证，待 10/8**')
print(f'  ③ A股医药反向兑现线（板块代理单日 ≥1.5% 跌幅）：9/30 板块代理 {MED933_1D:+.4f}% → 未触发'
      f'（方向相反）；**A股休市，10/5 不可验证**')
print(f'  附：上证 9/30 收 {SH:,.4f}；恒指 10/2 收 23,972.289（−2.604%）')

# ---------- 产物 ----------
out = {
    'date': TODAY, 'session': 'preopen', 'session_type': SESSION_TYPE,
    'session_type_note': ('档型②「混合档」= A股休市（10/1-10/7）+ 港股开市（10/5 周一续市，非复市首日）；'
                          '08:00 盘前时刻港股尚未开盘（09:30 开）→ 本档 pending 台账中「美股/QDII 腿」已定价、'
                          '「港股腿」标 priced=false，16:00 收盘后由 20:00 盘后档覆盖为正式版'),
    'calendar_verification': {
        'A股': 'stock_zh_index_daily(sh000001) 末行 = 2026-09-30（收 3,842.195）→ 国庆长假休市（第 5 日）',
        '港股': '新浪 hq rt_hkHSTECH 返回体日期字段 = 2026/10/02 16:08 → 10/3-10/4 为周末、10/5 今日待开（非休市）',
        '美股': 'stock_us_daily(IYH/XLV) 末行 = 2026-10-02 → 10/3-10/4 周末、10/5 当日收盘成型于北京 10/6 04:00',
        'rule': '三市场各自独立验证、不得互相外推（§3.107 / §3.119b / §3.122b）'},
    'base_total': TOTAL, 'base_file': BASEFILE,
    'base_revision': {'prev_total': None, 'delta': 0.0,
                      'reason': '本档交易日三验：A股 末行 = 2026-09-30（3,842.1946）、HSTECH 末行 = 2026-10-02（4,157.94）、'
                                'XLV 末行 = 2026-10-02（166.18）→ 基准与上一有效估值日一致、无修正'},
    'tracks': {k: {'mv': v['mv'], 'pct_of_total': v['pct_of_total'], 'day_pct': v['day_pct']}
               for k, v in tracks.items()},
    'discipline_hstech_cumulative': {
        'cut1': {'pct': 0.5, 'amount': cut1_amt, 'triggered_on': '2026-09-29', 'settled_on': '2026-09-30',
                 'note': '9/29 收盘 4,249.62（−0.0089%）边际破位触发 → 9/30 按净值成交'},
        'cut2': {'pct': 0.5, 'amount': cut2_amt, 'triggered_on': '2026-10-02', 'settled_on': None,
                 'execute_at': '2026-10-08', 'execution_pending': True,
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
                        'correction_note': '该口径 = 31,572.84 − 1,904.44（只扣第 2 次减仓），'
                                           '未扣除第 1 次已成交的 1,882.46 元 → 本档统一为「累计扣除」'
                                           '（31,572.84 − 3,786.90 = 27,785.94 元 = 7.30%）；'
                                           '两口径并列披露、以累计口径为准（§3.123e）'},
        'note': '**本档不重复计入任何一次减仓**；第 2 次的判定权已于 10/2 收盘级锁定、执行权归 10/8'},
    'med_exposure': med, 'med_pct': round(med / TOTAL * 100, 2),
    'threshold_all_med': round(th_all, 2), 'threshold_a_sh_med': round(th_sh, 2),
    'non_med_total': round(B_nm, 2),
    'hk_total': round(hk_total, 2), 'hk_total_pct': round(hk_total / TOTAL * 100, 2),
    'hk_segments': {'pure_hstech': round(pure, 2), 'china_internet': round(cpo, 2),
                    'broad_hk': round(broad, 2)},
    'hk_southbound_gap_days': ['2026-10-02', '2026-10-05', '2026-10-06', '2026-10-07'],
    'hk_gap_day_index_today': 2,
    'hk_leg_pending': {
        'window_days': ['2026-10-02', '2026-10-05', '2026-10-06', '2026-10-07'],
        'priced_days': ['2026-10-02'], 'unpriced_days_today': ['2026-10-05'],
        'priced_segment_1002': {'low': hk1002_low, 'mid': hk1002_mid, 'high': hk1002_high,
                                'method': '三段法笛卡尔积（1×2×2 = 4 组）后对**合计值**取 min/max（§3.123b）',
                                'segments': {'pure_hstech': {'exposure': round(pure, 2), 'ret_pct': SEG_1002['pure_ret']},
                                             'china_internet': {'exposure': round(cpo, 2),
                                                                'ret_range_pct': list(SEG_1002['concept_ret'])},
                                             'broad_hk': {'exposure': round(broad, 2),
                                                          'ret_range_pct': list(SEG_1002['broad_ret'])}}},
        'unpriced_note': ('10/5（空窗第 2 日）08:00 尚无收盘价 → **不可测算**；'
                          '累积区间 = 10/2 已定价段 + 10/5/10/6/10/7 三个未知交易日；'
                          '**静态测算只可给区间上下界、不得作方向判断**（§3.108 条款 24）'),
        'priced': False, 'priced_for_today': False},
    'pending': {
        'as_of': '2026-10-05 08:00', 'state': 'preopen_estimate', 'finalized': False,
        'finalize_at': '2026-10-05 20:00（港股收盘后）',
        'settle_date': '2026-10-08',
        'component_a': {'desc': 'QDII 000369/016280 的 9/29 净值（基准净值日 9/28）→ 已覆盖 US 9/29',
                        'amount': qdii_out, 'trade_date_covered': '2026-09-29'},
        'component_b': {'desc': f'自 US 9/30 起未可观测段：IYH 9/30 {IYH_0930:+.2f}% × 10/1 {IYH_1001:+.2f}%'
                                f' × 10/2 {IYH_1002:+.2f}% 复合 {comp_b*100:+.4f}%',
                        'trade_dates_covered': ['2026-09-30', '2026-10-01', '2026-10-02'],
                        'notional': round(notional_b, 2),
                        'low': round(b_low, 2), 'mid': round(b_mid, 2), 'high': round(b_high, 2),
                        'coef_range': [0.60, 0.90], 'coef_unstable': True,
                        'coef_note': '长假前后实测隐含系数 1.25~1.29（§3.118a），远超标定 0.72 / 实测 0.62'},
        'total_low': round(tot_low, 2), 'total_mid': round(tot_mid, 2), 'total_high': round(tot_high, 2),
        'unknown_sessions': ['2026-10-05', '2026-10-06', '2026-10-07'],
        'hk_leg': {'exposure': round(hk_total, 2), 'pct': round(hk_total / TOTAL * 100, 2),
                   'priced': False, 'reason': '港股 10/5 09:30 开盘、16:00 收盘 → 08:00 无当日价格',
                   'priced_segment_ref': 'hk_leg_pending.priced_segment_1002',
                   'note': '南向空窗（10/2/10/5/10/6/10/7，本档为第 2 日）；静态测算只可给区间上下界、不得作方向判断（§3.108 条款 24）'},
        'unquantified': {'code': None, 'mv': 0.0, 'stale': False,
                         'note': '164906 最新净值日 = 9/29 且已真实兑现计入「恒生科技」赛道 → 无挂账项；'
                                 'pending_codes ∩ applied_codes = ∅'},
        'note': ('§3.112f / §3.118a：跨长假只给区间、禁止中枢点值。A 覆盖 US 9/29（不得在 B 重复）；'
                 'B 自 US 9/30 起（含 10/2 的 0.00%）。港股腿本档未定价；'
                 'US 10/5、10/6、10/7 共 3 个交易日完全未知。')},
    'pending_consume': {
        'hold_decision': 'no_action',
        'reason': ('混合档必做待消化，但 08:00 时点可定价部分仅美股/QDII 腿（已在挂账口径内），'
                   '港股腿未定价；且组合唯一可执行的交易窗口 = 10/8（A股 + 南向 + 港股通同时恢复）→ '
                   '本档不做任何赛道级调整'),
        'estimated_combo_return_pct': 0.0,
        'estimated_combo_pnl': 0.0,
        'attribution': 'A股 10/1-10/7 休市 → 场外基金无净值、场内无成交价；港股 10/5 尚未开盘 → '
                       '**当日可实现盈亏恒为 0，归因「标的不可定价」而非「市场持平」**（§3.107 / §3.121d）'},
    'defense_lines': {
        'hstech_4250': {'last': HS, 'prev_close': HS_PREV, 'state': 'close_level_break_confirmed',
                        'dist_pct': round((HS / 4250 - 1) * 100, 4), 'dist_pts': round(HS - 4250, 2),
                        'break_type': '非边际破位（10/2 收盘级，距防线 −2.1661%）',
                        'action_reserved': f'第 2 次 0.5% 纪律减仓 {cut2_amt:,.2f} 元（执行待 10/8）',
                        'verify_at': '2026-10-05 16:00（港股续市，收盘价验证）',
                        'next_rule': '再破不叠加新纪律（同日防线只触发一次）；若回升站上 4,250 亦**不撤销**已登记减仓（§3.114c）'},
        'zz_consume_12100': {'last': ZZ, 'state': 'abv_line_last_known',
                             'dist_pct': round((ZZ / 12100 - 1) * 100, 4),
                             'next_line': 12000, 'next_line_dist_pct': round((ZZ / 12000 - 1) * 100, 2),
                             'verify_at': '2026-10-08（A股 复市）'},
        'a_med_reverse_1_5pct': {'proxy_pct': round(MED933_1D, 4), 'state': 'not_triggered',
                                 'verify_at': '2026-10-08（A股 复市）'},
        'sh_comp': {'last': SH}},
    'scenario': {
        'upside': ('港股 10/5 承接「美股 10/2 三大指数齐涨（纳指 +1.19% 创盘中新高）+ 欧股全线上涨 + 美债 10Y 5.283% 未破 5.3%」'
                   '且人民币汇率稳定 → 恒生科技或自 4,157.94 低位修复；若恒生科技收复 4,250，'
                   '**已登记的第 2 次减仓 1,904.44 元仍须于 10/8 执行**（纪律不可撤销，§3.114c）'),
        'base': ('混合档盘前：A股休市、港股 09:30 待开。组合账面基准冻结在 9/30 修正收盘 380,888.29 元；'
                 '已定价增量仅「美股/QDII 腿」（挂账区间 {:.2f} 元 ~ {:.2f} 元），'
                 '港股 10/2 已定价段 {:.2f} 元 ~ {:.2f} 元、10/5 段未知，A股腿待 10/8')
                .format(tot_high, tot_low, hk1002_low, hk1002_high),
        'downside': ('① **中东二次升级（胡塞袭沙特阿美炼油厂 + 也门军事行动 + 美向沙特卡塔尔增派爱国者）**'
                     '→ 油价二次冲高风险 → 通胀与长端利率反向压制恒科与美股标普医药；'
                     '② **港股 10/2 收盘级破位（4,157.94，非边际）** + 南向空窗第 2 日 + '
                     '部分在港中资券商清理内地客户业务（「只卖不买」）→ 承接力量最薄；'
                     '③ **美联储官员口径分歧显性化（洛根「至少再加息 50bp」）** 与市场定价（10 月不加息概率约 77%~78%）'
                     '形成显著缺口 → 12 月路径不确定性上升；'
                     '④ **美银 Hartnett 警示 AI 集中度类比 2000 年泡沫** vs 英伟达创新高 → 方向相反、须并列；'
                     '⑤ US 10/5、10/6、10/7 三个交易日未知，QDII 挂账区间可能被系数漂移击穿'),
    },
    'action': {'new_buy': 0, 'active_take_profit': 0, 'discipline_cut_today': 0,
               'discipline_cut_cumulative_registered': cut_cum,
               'note': ('混合档 + 盘前：A股 休市、港股未开盘 → 赛道级动作全部为 0；'
                        '恒生科技 0.5% 纪律减仓累计 3,786.90 元已登记（第 1 次 9/30 已成交、第 2 次执行待 10/8），'
                        '**本档不重复计入**；医药敞口 39.23% 距 40% 上限 0.77pct，且两医药赛道本档均无新增定价 → '
                        '门槛方向不变；现金 7.67%（累计纪律后 8.66%）维持长假缓冲；'
                        '**唯一可执行窗口 = 10/8**（A股 + 南向 + 港股通同时恢复）')},
    'calendar': {'2026-10-01': 'A股休市 + 港股休市（国庆日）+ 港股通关闭；美股照常交易',
                 '2026-10-02': 'A股休市；**港股复市（周五）**；港股通关闭；美股照常；**美国 9 月非农（北京 20:30）**',
                 '2026-10-03~10-04': 'A股/港股/美股均休（周末）',
                 '2026-10-05（今日）': 'A股休市；**港股续市（周一）**；港股通关闭；**美股 10/5 交易日（收盘成型于北京 10/6 04:00）**；'
                                   '今晚 21:45 美国 9 月标普全球服务业 PMI 终值 / 22:00 美国 9 月 ISM 非制造业 PMI',
                 '2026-10-06~10-07': 'A股休市；港股交易（南向空窗）；港股通关闭；美股照常',
                 '2026-10-08': 'A股复市 + 港股通恢复 → 挂账一次性释放与对账（唯一可执行窗口）；'
                               '央行 12,000 亿元 3 个月期买断式逆回购投放'},
    'calendar_by_market': {
        'A股': '10/1-10/7 休市 → 10/8 复市（10/10 周六休）',
        '港股': '10/1 休市 1 天 → 10/2 复市 → 10/3-4 周末 → **10/5-10/7 正常交易**（10/19 重阳节翌日休）',
        '港股通(南向)': '10/1-10/7 全程暂停 → 10/8 恢复',
        '美股': '10/1-10/7 照常交易（5 个交易日）'},
}

json.dump(out, open(os.path.join(HIST, f'portfolio_preopen_{TODAY.replace("-", "")}.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
print(f'\n已保存 portfolio_preopen_{TODAY.replace("-", "")}.json')

pend = {
    'date': TODAY,
    'as_of': '2026-10-05 08:00（盘前）',
    'state': 'preopen_estimate',
    'finalized': False,
    'finalize_at': '2026-10-05 20:00（港股 10/5 收盘价 16:00 后成型）',
    'finalized_note': ('§3.121b：混合档 `portfolio_pending_<DATE>.json` 的正式版归属当日 20:00 盘后档，'
                       '以港股 10/5 收盘价重算并覆盖同文件名；本档为 08:00 预登记版（state=preopen_estimate），'
                       '**港股腿未经收盘价定价**'),
    'session_type': '混合档（A股休市 + 港股续市）',
    'base_total': TOTAL, 'base_file': BASEFILE,
    'base_guard_dev': round(dev, 4), 'base_guard_rule': '|Σ tracks.mv − total_mv| < 1.5',
    'base_note': '9/30 修正收盘口径（tracks[].mv 求和校验通过）',
    'realized_pnl': 0.0, 'realized_pct': 0.0,
    'realized_note': ('A股 10/1-10/7 休市（场外基金无净值发布、场内 ETF 无成交价）；'
                      '港股 10/5 09:30 开盘，08:00 尚无当日价格 → 本档账面可实现盈亏恒为 0，'
                      '属「标的不可定价」而非「市场持平」（§3.107 / §3.121d）'),
    'hk_close': {'index': 'HSTECH', 'date': '2026-10-02', 'close': HS, 'prev_close': HS_PREV, 'pct': -2.2556,
                 'priced_for_today': False,
                 'note': '10/2 为港股上一交易日；本档 08:00 时点 10/5 尚未开盘 → 引用 10/2 收盘作基准，'
                         '不得当作 10/5 价格'},
    'hk_leg': {'exposure': round(hk_total, 2), 'pct': round(hk_total / TOTAL * 100, 2),
               'priced': False, 'segments': out['hk_segments'],
               'priced_segment_1002': out['hk_leg_pending']['priced_segment_1002']},
    'pending_consume': out['pending_consume'],
    'qdii_forecast': {'component_a': out['pending']['component_a'],
                      'component_b': out['pending']['component_b'],
                      'total_low': out['pending']['total_low'], 'total_mid': out['pending']['total_mid'],
                      'total_high': out['pending']['total_high'],
                      'unknown_sessions': out['pending']['unknown_sessions'],
                      'coef_note': out['pending']['component_b']['coef_note']},
    'tracks': out['tracks'],
    'weights': {k: v['pct_of_total'] for k, v in out['tracks'].items()},
    'tracks_weight_after_cumulative_discipline': out['discipline_hstech_cumulative']['weight_after_pct'],
    'discipline_hstech_cumulative': out['discipline_hstech_cumulative'],
    'med_exposure': med, 'med_pct': out['med_pct'],
    'threshold_all_med': out['threshold_all_med'], 'threshold_a_sh_med': out['threshold_a_sh_med'],
    'defense': out['defense_lines'],
    'chain_0pct_row_inserted': False,
    'note': ('混合档盘前台账（**非正式版**）：仅「美股/QDII 腿」已定价，「港股腿」与「A股腿」均未定价；'
             '20:00 盘后档将以港股 10/5 收盘价重算并覆盖本文件（§3.121b / AGENTS #80）；'
             '未向链式序列插入 0% 行（`chain_0pct_row_inserted: false`，§3.108 条款 22）'),
}
json.dump(pend, open(os.path.join(HIST, f'portfolio_pending_{TODAY.replace("-", "")}.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
print(f'已保存 portfolio_pending_{TODAY.replace("-", "")}.json（state=preopen_estimate, finalized=false）')
