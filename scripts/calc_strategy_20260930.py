# -*- coding: utf-8 -*-
"""2026-09-30（周三 · 国庆长假前最后一个交易日）盘前档：组合策略计算
基准 = 9/29 修正收盘（portfolio_close_20260929_fix.json）= 376,491.53 元
输出：portfolio_preopen_20260930.json —— 敞口、门槛方程、港联系三层拆解、QDII 挂账预告、9/30 操作预案
⚠️ 档型③（正常交易日盘前、当日尚无价格）：不产出 portfolio_close_* 也不产出 portfolio_pending_*，
   待消化沿用上一档口径并在报告声明「本档无新增定价」（AGENTS.md #28 / §3.110）。
"""
import json, os

BASE = '/Users/jieyang/Documents/WealthHub'
HIST = os.path.join(BASE, 'data/processed/history')
TODAY = '2026-09-30'
fix = json.load(open(os.path.join(HIST, 'portfolio_close_20260929_fix.json'), encoding='utf-8'))

TOTAL = fix['total_mv']
tracks = fix['tracks']
print(f'基准（9/29 修正收盘）= {TOTAL:,.2f} 元')
print(f"  （修正前 376,574.96 元；Δ {TOTAL - 376574.96:+,.2f} 元 来自 161616/000727/002742 的 9/29 真实净值补更）")
for k, v in sorted(tracks.items(), key=lambda kv: -kv[1]['mv']):
    print(f"  {k:10s} mv={v['mv']:>11,.2f}  w={v['pct_of_total']:>6.2f}%  day={v['day_pct']:+.3f}%")

# ---------- 医药敞口与门槛方程（§3.98）----------
med = round(tracks['A股医药']['mv'] + tracks['美股标普医药']['mv'], 2)
B = TOTAL - med
A_sh = tracks['A股医药']['mv']
th_all = ((0.40 / 0.60) * B / med - 1) * 100
th_sh = (((0.40 / 0.60) * B - (med - A_sh)) / A_sh - 1) * 100
print(f'\n医药敞口 {med:,.2f} 元 = {med/TOTAL*100:.2f}%  距 40% 上限 {40-med/TOTAL*100:.2f}pct')
print(f'  门槛：两医药赛道同涨 {th_all:+.2f}%  /  仅 A股医药 {th_sh:+.2f}%')
print(f'  非医药对手盘 {B:,.2f} 元')

# ---------- 港股暴露三层拆解（§3.108 条款 23/24）----------
HK_TECH_CODES = {'012348', '513180'}          # 纯恒生科技系
CPO_CODES = {'513050', '164906'}              # 中概/海外互联系
BROAD_HK_CODES = {'000071', '159920'}         # 宽基中的恒生系
pure = cpo = broad = 0.0
seg_detail = []
for d in fix['detail']:
    code6 = ''.join(c for c in str(d['code']) if c.isdigit())
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
print('  ⚠️ 港联系「南向空窗」= 10/2、10/5、10/6、10/7 共 4 个港股交易日（港股通关闭），'
      '该窗口波动率须按「外资主导」建模（§3.113a）')

# ---------- QDII 挂账预告（US 9/29）----------
med_us = tracks['美股标普医药']['mv']
IYH_0929 = -0.36
print(f'\nQDII 挂账预告：US 9/29 IYH {IYH_0929:+.2f}% × 传导系数')
for k in (0.60, 0.62, 0.72, 0.90):
    print(f'  系数 {k:.2f}: {IYH_0929*k:+.4f}% → {med_us*IYH_0929/100*k:+,.2f} 元')
q_mid = med_us * IYH_0929 / 100 * 0.72
q_lo = med_us * IYH_0929 / 100 * 0.90        # 系数越大，负值越大（下界）
q_hi = med_us * IYH_0929 / 100 * 0.60
q_622 = med_us * IYH_0929 / 100 * 0.62
print(f'  中枢（0.72）{q_mid:+,.2f} 元；参照 §3.114e 实测 0.62 → {q_622:+,.2f} 元；'
      f'区间（0.60~0.90）{q_hi:+,.2f} 元 ~ {q_lo:+,.2f} 元')
print(f'  ⚠️ 方向为负（与前档 +302.77 元相反）；挂账窗口 = US 9/29 单个交易日'
      f'（基准已含 000369/016280 的 9/28 净值）')
print(f'  ⚠️ 未量化挂账项：164906 交银海外互联（持仓 9,243.73 元）的 US 9/29 挂账未计入合计'
      f'（传导系数未标定；参照纳斯达克中国金龙 9/29 −1.55% 量级约 −90 元）')

# ---------- 9/30 待消化合计（档型③：无新增定价）----------
print(f'\n9/30 待消化合计（仅 QDII 挂账，档型③本档无新增定价）：'
      f'{q_hi:+,.2f} 元 ~ {q_lo:+,.2f} 元（中枢 {q_mid:+,.2f} 元）= 组合 {q_mid/TOTAL*100:+.4f}%')

# ---------- 9/30 执行项：恒生科技 0.5% 纪律减仓（9/29 档已触发，本档结算）----------
cut_pct = 0.5
cut_amt = round(TOTAL * cut_pct / 100, 2)
cut_amt_prev = round(376574.96 * cut_pct / 100, 2)
print(f'\n恒生科技 0.5% 纪律减仓（9/29 盘后档判定 → 9/30 结算）')
print(f'  按修正后基准 {TOTAL:,.2f} 元 × 0.5pct = {cut_amt:,.2f} 元'
      f'（原按 376,574.96 元算 = {cut_amt_prev:,.2f} 元，Δ {cut_amt-cut_amt_prev:+,.2f} 元）')
hk = tracks['恒生科技']['mv']; cash = tracks['现金']['mv']
print(f'  恒生科技 {hk:,.2f} → {hk-cut_amt:,.2f}（{hk/TOTAL*100:.2f}% → {(hk-cut_amt)/TOTAL*100:.2f}%）')
print(f'  现金     {cash:,.2f} → {cash+cut_amt:,.2f}（{cash/TOTAL*100:.2f}% → {(cash+cut_amt)/TOTAL*100:.2f}%）')

# ---------- 三条防线（9/29 收盘口径）----------
ZZ = 12107.1705
HS = 4249.62
print('\n三条防线（9/29 收盘口径）：')
print(f'  ① 恒生科技 4,250：9/29 收 {HS:,.2f} → {(HS/4250-1)*100:+.4f}% 【收盘级跌破 → 执行 0.5% 减仓】')
print(f'  ② 中证消费 12,100 下沿：9/29 收 {ZZ:,.4f} → {(ZZ/12100-1)*100:+.4f}% 【收复 → 假破位确认，'
      f'不改回；下一线 12,000 距 {(ZZ/12000-1)*100:+.2f}%】')
print('  ③ A股医药反向兑现线（板块代理单日 ≥1.5% 跌幅）：9/29 板块代理 −0.0825% → 未触发')

# ---------- 情景 ----------
out = {
    'date': TODAY, 'session': 'preopen', 'session_type': 'normal_trading_day_preopen',
    'base_total': TOTAL, 'base_file': 'portfolio_close_20260929_fix.json',
    'base_revision': {'prev_total': 376574.96, 'delta': round(TOTAL - 376574.96, 2),
                      'reason': '161616 / 000727 / 002742 的 9/29 真实净值补更'},
    'tracks': {k: {'mv': v['mv'], 'pct_of_total': v['pct_of_total'], 'day_pct': v['day_pct']}
               for k, v in tracks.items()},
    'med_exposure': med, 'med_pct': round(med / TOTAL * 100, 2),
    'threshold_all_med': round(th_all, 2), 'threshold_a_sh_med': round(th_sh, 2),
    'non_med_total': round(B, 2),
    'hk_total': round(hk_total, 2), 'hk_total_pct': round(hk_total / TOTAL * 100, 2),
    'hk_segments': {'pure_hstech': round(pure, 2), 'china_internet': round(cpo, 2),
                    'broad_hk': round(broad, 2)},
    'hk_southbound_gap_days': ['2026-10-02', '2026-10-05', '2026-10-06', '2026-10-07'],
    'qdii_pending': {'sessions': ['2026-09-29'], 'iyh_pct': [IYH_0929],
                     'coef_mid': 0.72, 'pnl_mid': round(q_mid, 2),
                     'pnl_low': round(q_lo, 2), 'pnl_high': round(q_hi, 2),
                     'pnl_at_062': round(q_622, 2),
                     'note': ('QDII 000369/016280 最新出库净值日 = 2026-09-28（本档盘前已补入 9/29 修正件），'
                              'US 9/29 为唯一挂账交易日；按 IYH −0.36% × 传导系数预告，'
                              '区间取系数 0.60~0.90（§3.114e 实测 0.62 作为参照点）')},
    'unquantified_pending': {'code': '164906', 'mv': 9183.25,
                             'note': 'US 9/29 挂账未计入合计（传导系数未标定），参照纳斯达克中国金龙 9/29 −1.55% 量级约 −90 元'},
    'new_pending': 0,
    'discipline_hstech': {'pct': cut_pct, 'amount': cut_amt, 'amount_prev': cut_amt_prev,
                          'trigger': '恒生科技 9/29 收盘 4,249.62 < 防线 4,250（−0.0089%，收盘级）',
                          'settle': '9/30 按 9/30 净值成交（节前最后一个 A 股交易日）',
                          'target_primary': '012348 天弘恒生科技联接A（纯恒科口径）',
                          'target_alt': '513180 恒指科技（场内 ETF）',
                          'not_target': '513050 / 164906（中概口径，与触发源不一致）',
                          'margin_note': '边际破位（仅 −0.0089%），仍按二元判据执行、不引入主观容差（§3.114c）'},
    'defense_lines': {
        'hstech_4250': {'last': HS, 'state': 'broken_close_level',
                        'dist_pct': round((HS / 4250 - 1) * 100, 4)},
        'zz_consume_12100': {'last': ZZ, 'state': 'restored_close_level',
                             'dist_pct': round((ZZ / 12100 - 1) * 100, 4),
                             'next_line': 12000, 'next_line_dist_pct': round((ZZ / 12000 - 1) * 100, 2)},
        'a_med_reverse_1_5pct': {'proxy_pct': -0.0825, 'state': 'not_triggered'}},
    'scenario': {
        'upside': '威廉姆斯鸽派 + CME 加息概率降至 50% 以下 传导 → 恒科超跌反弹收复 4,250、A股 PMI 超预期 → 宽基与恒科双向修复',
        'base': '节前最后一个交易日、成交延续 1.4 万亿级地量，指数窄幅震荡；风格延续「红利/地产/传媒强、油气/煤炭/航运弱」',
        'downside': '30Y 美债 5.567% 连涨 6 日 + 中秋/国庆双假期海外定价缺失 → 持币过节抛压致上证失守 3,800；医药催化密度高但板块不响应',
    },
    'action': {'new_buy': 0, 'active_take_profit': 0, 'discipline_cut': cut_amt,
               'note': '9/30 唯一动作 = 恒生科技 0.5% 纪律减仓（9/29 收盘级破位触发）；其余赛道动作 0；'
                       '不因中证消费收复而补回仓位；现金维持长假缓冲'},
    'calendar': {'2026-09-30': 'A股 + 港股 + 美股均交易（节前最后一个 A 股交易日）',
                 '2026-10-01': 'A股休市 + 港股休市（港股通关闭）',
                 '2026-10-02~10-07': 'A股休市；港股 10/2、10/5、10/6、10/7 交易；港股通关闭；美股照常',
                 '2026-10-08': 'A股复市 + 港股通恢复（美股类事件一次性回填）'},
}
json.dump(out, open(os.path.join(HIST, f'portfolio_preopen_{TODAY.replace("-", "")}.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
print(f'\n已保存 portfolio_preopen_{TODAY.replace("-", "")}.json')
