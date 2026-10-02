# -*- coding: utf-8 -*-
"""2026-10-02（周五 · 国庆长假第 2 日 · **混合档**：A股休市 + 港股复市首日）盘前档：组合策略计算
基准 = 9/30 修正收盘（portfolio_close_20260930_fix.json）= 380,888.29 元
输出：
  - portfolio_preopen_20261002.json —— 敞口、门槛方程、港联系三层拆解、**待消化（mixed-day）**、防线台账、日历
  - portfolio_pending_20261002.json —— 混合档台账（**state = preopen_estimate / finalized = false**，
    港股 10/2 收盘价 16:00 后成型 → 由 20:00 盘后档覆盖为正式版）
⚠️ 档型②（混合档：A股休市 + 港股开市）→ **必做待消化测算**（§3.108 条款 22 / AGENTS #22）。
   ⚠️ 时段归属澄清：08:00 盘前时刻港股尚无 10/2 收盘价 → 本档 pending 仅含
      「美股/QDII 腿」（已定价）与「港股腿（未定价）」两段，港股段显式标 `priced: false`。
⚠️ §3.107：QDII/LOF 券「基准已含哪一日净值」从 price_src 字符串解析，不得用固定日期常量。
⚠️ §3.118a：跨长假 QDII 挂账预告**禁止给中枢点值**，只给区间（系数 0.60~0.90）并显式标注「系数不稳定」。
⚠️ 本档口径更正（§3.121a）：挂账 component A 已覆盖 US 9/29（净值日 9/28 → 9/29）→
   component B **自 US 9/30 起**，不得再把 9/29 计入 B（10/1 档曾重复覆盖 9/29）。
"""
import json, os, re

BASE = '/Users/jieyang/Documents/WealthHub'
HIST = os.path.join(BASE, 'data/processed/history')
TODAY = '2026-10-02'
BASEFILE = 'portfolio_close_20260930_fix.json'
fix = json.load(open(os.path.join(HIST, BASEFILE), encoding='utf-8'))

TOTAL = fix['total_mv']
tracks = fix['tracks']
print(f'基准（9/30 修正收盘）= {TOTAL:,.2f} 元  ← {BASEFILE}')
print('  ⚠️ 档型②「混合档」（A股 10/1-10/7 休市 + 港股 10/1 休 / 10/2 复市）'
      '→ 产 pending 台账、**必做待消化**（§3.108 条款 22）')
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
print('  ⚠️ 本档美股标普医药（15.66%）已被 US 10/1（IYH −1.62%）确认为**负向**，'
      '「被动突破 40% 上限」的门槛在本档方向上是**放宽**的')

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
print('  ⚠️ 港联系「南向空窗」= 10/2、10/5、10/6、10/7 共 4 个港股交易日（港股通关闭）'
      '→ 波动率须按「外资主导」建模（§3.113a/§3.115d）')

# ---------- 恒生科技 0.5% 纪律减仓（9/30 已执行结算，价值中性）----------
cut = fix.get('discipline', {})
cut_pct, cut_amt = 0.5, cut.get('amount', 1882.46)
hk_after = tracks['恒生科技']['mv'] - cut_amt
cash_after = tracks['现金']['mv'] + cut_amt
print(f'\n恒生科技 {cut_pct}% 纪律减仓（9/30 已执行结算）：{cut_amt:,.2f} 元')
print(f'  恒生科技 {tracks["恒生科技"]["mv"]:,.2f} → {hk_after:,.2f}'
      f'（{tracks["恒生科技"]["pct_of_total"]:.2f}% → {hk_after/TOTAL*100:.2f}%）')
print(f'  现金     {tracks["现金"]["mv"]:,.2f} → {cash_after:,.2f}'
      f'（{tracks["现金"]["pct_of_total"]:.2f}% → {cash_after/TOTAL*100:.2f}%）')
print(f'  口径：{cut.get("settle","")}')

# ---------- 待消化（混合档核心；§3.112f 只给区间、不给方向）----------
med_us = tracks['美股标普医药']['mv']
IYH_0929, IYH_0930, IYH_1001 = -0.36, -1.17, -1.62
comp_b = (1 + IYH_0930 / 100) * (1 + IYH_1001 / 100) - 1          # 自 US 9/30 起（A 已覆盖 9/29）
qdii_out = fix.get('pending', {}).get('qdii_observable_amount', -267.82)   # component A
notional_b = med_us * comp_b
print('\n待消化（混合档 = 必做；§3.112f / §3.118a：只给区间、禁止中枢点值）')
print(f'  A) QDII 000369/016280 的 9/29 净值已出库但按既定口径挂账：{qdii_out:+,.2f} 元'
      f'（基准净值日 9/28 → 已覆盖 US 9/29，不得在 B 中重复计入）')
print(f'  B) 自 US 9/30 起未可观测段：IYH 9/30 {IYH_0930:+.2f}% × 10/1 {IYH_1001:+.2f}%'
      f' → 复合 {comp_b*100:+.4f}%')
print(f'     标的市值 {med_us:,.2f} 元 → 未打折损益 {notional_b:+,.2f} 元')
coefs = (0.60, 0.72, 0.90)
vals_b = sorted(round(notional_b * k, 2) for k in coefs)          # 负值：系数越大越负
b_high, b_mid, b_low = max(vals_b), (notional_b * 0.72), min(vals_b)
print(f'     系数 0.60 / 0.72 / 0.90 → {notional_b*0.60:+,.2f} / {b_mid:+,.2f} / {notional_b*0.90:+,.2f} 元')
tot_high, tot_mid, tot_low = qdii_out + b_high, qdii_out + b_mid, qdii_out + b_low
print(f'  → A+B 合计区间 {tot_high:+,.2f} 元 ~ {tot_low:+,.2f} 元（中枢 {tot_mid:+,.2f} 元 = 组合 {tot_mid/TOTAL*100:+.4f}%）')
implied = (qdii_out * 0 + notional_b / ((IYH_0930 + IYH_1001) / 100 * med_us)) if False else None
print('  ⚠️ 传导系数不稳定：长假前后实测隐含系数 1.25~1.29（§3.118a），远超标定 0.72 / 实测 0.62'
      ' → 若按 1.25 折算，B = {:+,.2f} 元、A+B 合计 {:+,.2f} 元，**区间上/下界均可能被击穿**'
      .format(notional_b * 1.25, qdii_out + notional_b * 1.25))
print('  ⚠️ 仍未量化：US 10/2、10/5、10/6、10/7 共 4 个美股交易日完全未知')
print('  ⚠️ 港股腿（港联系 {:.2f} 元 = {:.2f}%）本档**未定价**：港股 10/2 09:30 开盘、16:00 收盘'
      ' → 待 20:00 盘后档以实际收盘价计入'.format(hk_total, hk_total / TOTAL * 100))
print('  ⚠️ 场外 QDII 在 A股 休市期不发布净值 → 10/8 实际可回填净值日可能仍停在 9/29/9/30（§3.117a）')

# ---------- 三条防线（9/30 收盘口径 + 港股复市后首验）----------
HS, ZZ, SH = 4253.89, 12295.9591, 3842.1946
MED933_1D = (8009.6669 / 7786.2255 - 1) * 100
print('\n三条防线（9/30 收盘口径；恒科 10/2 复市后首次验证）：')
print(f'  ① 恒生科技 4,250：9/30 收 {HS:,.2f} → {(HS/4250-1)*100:+.4f}%'
      f'【贴线收复，安全垫仅 {HS-4250:,.2f} 点】→ **10/2 任一幅度收跌即再度触发 0.5% 减仓**')
print(f'  ② 中证消费 12,100 下沿：9/30 收 {ZZ:,.4f} → {(ZZ/12100-1)*100:+.4f}%'
      f'（下一线 12,000 距 {(ZZ/12000-1)*100:+.2f}%）→ **本档 A股 休市，不可验证**')
print(f'  ③ A股医药反向兑现线（板块代理单日 ≥1.5% 跌幅）：9/30 板块代理 {MED933_1D:+.4f}% → 未触发'
      f'（方向相反）；**本档 A股 休市，不可验证**')
print(f'  附：上证 9/30 收 {SH:,.4f}')

# ---------- 情景 ----------
out = {
    'date': TODAY, 'session': 'preopen', 'session_type': 'mixed_day_preopen',
    'session_type_note': ('档型②「混合档」= A股休市（10/1-10/7）+ 港股开市（10/2 复市首日）；'
                          '08:00 盘前时刻港股尚无 10/2 收盘价 → 本档 pending 台账中「美股/QDII 腿」已定价、'
                          '「港股腿」标 priced=false，16:00 收盘后由 20:00 盘后档覆盖为正式版'),
    'base_total': TOTAL, 'base_file': BASEFILE,
    'base_revision': {'prev_total': None, 'delta': 0.0,
                      'reason': '本档交易日双验：A股 末行 = 2026-09-30（3,842.1946）、HSTECH 末行 = 2026-09-30（4,253.89）'
                                '→ 基准与上一有效估值日一致、无修正'},
    'tracks': {k: {'mv': v['mv'], 'pct_of_total': v['pct_of_total'], 'day_pct': v['day_pct']}
               for k, v in tracks.items()},
    'tracks_weight_after_discipline': {
        '恒生科技': round(hk_after / TOTAL * 100, 2), '现金': round(cash_after / TOTAL * 100, 2)},
    'med_exposure': med, 'med_pct': round(med / TOTAL * 100, 2),
    'threshold_all_med': round(th_all, 2), 'threshold_a_sh_med': round(th_sh, 2),
    'non_med_total': round(B_nm, 2),
    'hk_total': round(hk_total, 2), 'hk_total_pct': round(hk_total / TOTAL * 100, 2),
    'hk_segments': {'pure_hstech': round(pure, 2), 'china_internet': round(cpo, 2),
                    'broad_hk': round(broad, 2)},
    'hk_southbound_gap_days': ['2026-10-02', '2026-10-05', '2026-10-06', '2026-10-07'],
    'discipline_hstech': {'pct': cut_pct, 'amount': cut_amt, 'settled_on': '2026-09-30',
                          'hk_after': round(hk_after, 2), 'cash_after': round(cash_after, 2),
                          'weight_after_pct': {'恒生科技': round(hk_after / TOTAL * 100, 2),
                                               '现金': round(cash_after / TOTAL * 100, 2)},
                          'note': '9/29 收盘级破位触发 → 9/30 结算；价值中性、P&L 口径不变，仅权重单列；'
                                  '**本档不得再计一次**'},
    'pending': {
        'as_of': '2026-10-02 08:00', 'state': 'preopen_estimate', 'finalized': False,
        'finalize_at': '2026-10-02 20:00（港股收盘后）',
        'settle_date': '2026-10-08',
        'component_a': {'desc': 'QDII 000369/016280 的 9/29 净值（基准净值日 9/28）→ 已覆盖 US 9/29',
                        'amount': qdii_out, 'trade_date_covered': '2026-09-29'},
        'component_b': {'desc': f'自 US 9/30 起未可观测段：IYH 9/30 {IYH_0930:+.2f}% × 10/1 {IYH_1001:+.2f}%'
                                f' 复合 {comp_b*100:+.4f}%',
                        'trade_dates_covered': ['2026-09-30', '2026-10-01'],
                        'notional': round(notional_b, 2),
                        'low': round(b_low, 2), 'mid': round(b_mid, 2), 'high': round(b_high, 2),
                        'coef_range': [0.60, 0.90], 'coef_unstable': True,
                        'coef_note': '长假前后实测隐含系数 1.25~1.29（§3.118a），远超标定 0.72 / 实测 0.62'},
        'total_low': round(tot_low, 2), 'total_mid': round(tot_mid, 2), 'total_high': round(tot_high, 2),
        'unknown_sessions': ['2026-10-02', '2026-10-05', '2026-10-06', '2026-10-07'],
        'hk_leg': {'exposure': round(hk_total, 2), 'pct': round(hk_total / TOTAL * 100, 2),
                   'priced': False, 'reason': '港股 10/2 09:30 开盘、16:00 收盘 → 08:00 无当日价格',
                   'note': '南向空窗（10/2/10/5/10/6/10/7）；静态测算只可给区间上下界、不得作方向判断（§3.108 条款 24）'},
        'unquantified': {'code': None, 'mv': 0.0, 'stale': False,
                         'note': '164906 最新净值日 = 9/29 且已真实兑现计入「恒生科技」赛道 → 无挂账项；'
                                 'pending_codes ∩ applied_codes = ∅'},
        'note': ('§3.112f / §3.118a：跨长假只给区间、禁止中枢点值。A 覆盖 US 9/29（不得在 B 重复）；'
                 'B 自 US 9/30 起。港股腿本档未定价；US 10/2、10/5、10/6、10/7 共 4 个交易日完全未知。')},
    'pending_consume': {
        'hold_decision': 'no_action',
        'reason': ('混合档必做待消化，但 08:00 时点可定价部分仅美股/QDII 腿（已在挂账口径内），'
                   '港股腿未定价；且组合唯一可执行的交易窗口 = 10/8（A股 + 南向 + 港股通同时恢复）→ '
                   '本档不做任何赛道级调整'),
        'estimated_combo_return_pct': 0.0,
        'estimated_combo_pnl': 0.0,
        'attribution': 'A股 10/1-10/7 休市 → 场外基金无净值、场内无成交价；港股 10/2 尚未开盘 → '
                       '**当日可实现盈亏恒为 0，归因「标的不可定价」而非「市场持平」**（§3.107）'},
    'defense_lines': {
        'hstech_4250': {'last': HS, 'state': 'restored_close_level_close_to_line',
                        'dist_pct': round((HS / 4250 - 1) * 100, 4), 'cushion_pts': round(HS - 4250, 2),
                        'verify_at': '2026-10-02 16:00（港股复市后首次收盘验证）',
                        'next_trigger': '收盘价 < 4,250 → 第 2 次 0.5% 纪律减仓（标的限纯恒科口径）'},
        'zz_consume_12100': {'last': ZZ, 'state': 'restored_close_level',
                             'dist_pct': round((ZZ / 12100 - 1) * 100, 4),
                             'next_line': 12000, 'next_line_dist_pct': round((ZZ / 12000 - 1) * 100, 2),
                             'verify_at': '2026-10-08（A股 复市）'},
        'a_med_reverse_1_5pct': {'proxy_pct': round(MED933_1D, 4), 'state': 'not_triggered',
                                 'verify_at': '2026-10-08（A股 复市）'},
        'sh_comp': {'last': SH}},
    'scenario': {
        'upside': ('10/1 美股指数收涨（标普500 +0.19%）+ 10Y 收盘回落至 5.24%（−约 5bp）+ 埃森哲 +16% 领涨 → '
                   '若 10/2 港股复市承接「美股软件/光通信走强 → 港股科技映射」且恒生科技收复 4,250 并拉开安全垫，'
                   '则 10/8 组合可维持零动作'),
        'base': ('混合档：A股休市、港股复市首日。组合账面基准冻结在 9/30 修正收盘 380,888.29 元；'
                 '已定价增量仅「美股/QDII 腿」（挂账区间 {:.2f} 元 ~ {:.2f} 元），'
                 '港股腿待 16:00 定价、A股腿待 10/8').format(tot_high, tot_low),
        'downside': ('① **医疗保健连续第 2 日领跌标普 500（10/1 −1.30%、9/30 −1.39%）** → '
                     '组合美股标普医药（15.66%）为「上涨日负超额」，挂账区间方向明确为负；'
                     '② **恒生科技距 4,250 仅 +0.0915%（3.89 点）**，10/2 复市在「南向空窗 + 外资主导」下任一跌幅即触发第 2 次减仓；'
                     '③ 油价单日 +4.37%（布伦特重回 100 上方）→ 通胀端与长端利率反向风险；'
                     '④ 美国 9 月非农（10/2 20:30）落在 A股 休市窗口 → 定价推迟至 10/8；'
                     '⑤ US 10/2、10/5、10/6、10/7 共 4 个美股交易日未知，挂账区间可能显著放大'),
    },
    'action': {'new_buy': 0, 'active_take_profit': 0, 'discipline_cut': 0,
               'settled_discipline_cut': 0,
               'note': ('混合档 + 盘前：A股 休市、港股未开盘 → 赛道级动作全部为 0；'
                        '恒生科技 0.5% 纪律减仓已于 9/30 结算（本档不重复计入）；'
                        '医药敞口 39.23% 距 40% 上限 0.77pct，且美股腿已确认为负向 → 门槛方向上放宽；'
                        '现金 7.67%（纪律后 8.16%）维持长假缓冲；'
                        '**唯一可执行窗口 = 10/8**（A股 + 南向 + 港股通同时恢复）')},
    'calendar': {'2026-10-01': 'A股休市 + 港股休市（国庆日）+ 港股通关闭；美股照常交易',
                 '2026-10-02（今日）': 'A股休市；**港股复市（周五）**；港股通关闭；美股照常；'
                                   '**今晚 20:30 美国 9 月非农**',
                 '2026-10-03~10-04': 'A股/港股/美股均休（周末）',
                 '2026-10-05~10-07': 'A股休市；港股交易（南向空窗）；港股通关闭；美股照常',
                 '2026-10-08': 'A股复市 + 港股通恢复 → 挂账一次性释放与对账（唯一可执行窗口）'},
    'calendar_by_market': {
        'A股': '10/1-10/7 休市 → 10/8 复市（10/10 周六休）',
        '港股': '10/1 休市 1 天 → **10/2 复市** → 10/3-4 周末 → 10/5-10/7 正常交易（10/19 重阳节翌日休）',
        '港股通(南向)': '10/1-10/7 全程暂停 → 10/8 恢复',
        '美股': '10/1-10/7 照常交易（5 个交易日）'},
}

json.dump(out, open(os.path.join(HIST, f'portfolio_preopen_{TODAY.replace("-", "")}.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
print(f'\n已保存 portfolio_preopen_{TODAY.replace("-", "")}.json')

pend = {
    'date': TODAY,
    'as_of': '2026-10-02 08:00（盘前）',
    'state': 'preopen_estimate',
    'finalized': False,
    'finalize_at': '2026-10-02 20:00（港股 10/2 收盘价 16:00 后成型）',
    'session_type': '混合档（A股休市 + 港股复市首日）',
    'base_total': TOTAL, 'base_file': BASEFILE,
    'base_note': '9/30 修正收盘口径（tracks[].mv 求和校验通过）',
    'realized_pnl': 0.0, 'realized_pct': 0.0,
    'realized_note': ('A股 10/1-10/7 休市（场外基金无净值发布、场内 ETF 无成交价）；'
                      '港股 10/2 09:30 开盘，08:00 尚无当日价格 → 本档账面可实现盈亏恒为 0，'
                      '属「标的不可定价」而非「市场持平」（§3.107）'),
    'hk_close': {'index': 'HSTECH', 'date': '2026-09-30', 'close': HS, 'pct': 0.10,
                 'priced_for_1002': False,
                 'note': '10/1 港股休市；本档 08:00 时点 10/2 尚未开盘 → 引用 9/30 收盘作基准，'
                         '不得当作 10/2 价格'},
    'hk_leg': {'exposure': round(hk_total, 2), 'pct': round(hk_total / TOTAL * 100, 2),
               'priced': False, 'segments': out['hk_segments']},
    'pending_consume': out['pending_consume'],
    'qdii_forecast': {'component_a': out['pending']['component_a'],
                      'component_b': out['pending']['component_b'],
                      'total_low': out['pending']['total_low'], 'total_mid': out['pending']['total_mid'],
                      'total_high': out['pending']['total_high'],
                      'unknown_sessions': out['pending']['unknown_sessions'],
                      'coef_note': out['pending']['component_b']['coef_note']},
    'tracks': out['tracks'],
    'weights': {k: v['pct_of_total'] for k, v in out['tracks'].items()},
    'med_exposure': med, 'med_pct': out['med_pct'],
    'threshold_all_med': out['threshold_all_med'], 'threshold_a_sh_med': out['threshold_a_sh_med'],
    'defense': out['defense_lines'],
    'note': ('混合档盘前台账（非正式版）：仅「美股/QDII 腿」已定价，「港股腿」与「A股腿」均未定价；'
             '20:00 盘后档将以港股 10/2 收盘价重算并覆盖本文件（§3.108 条款 22 + 本档时段归属澄清）'),
}
json.dump(pend, open(os.path.join(HIST, f'portfolio_pending_{TODAY.replace("-", "")}.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
print(f'已保存 portfolio_pending_{TODAY.replace("-", "")}.json（state=preopen_estimate, finalized=false）')
