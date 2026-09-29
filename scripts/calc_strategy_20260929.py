# -*- coding: utf-8 -*-
"""2026-09-29 盘前档：组合策略计算（基准 = 9/28 修正收盘 375,885.31 元）
输出：portfolio_preopen_20260929.json —— 敞口、门槛方程、港联系三层拆解、QDII 挂账预告、9/29 操作预案
"""
import json, os

BASE = '/Users/jieyang/Documents/WealthHub'
HIST = os.path.join(BASE, 'data/processed/history')
TODAY = '2026-09-29'
fix = json.load(open(os.path.join(HIST, 'portfolio_close_20260928_fix.json'), encoding='utf-8'))

TOTAL = fix['total_mv']
tracks = fix['tracks']
print(f'基准（9/28 修正收盘）= {TOTAL:,.2f} 元')
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

# ---------- 港股暴露双层拆解 + 三段法（§3.108 条款 23）----------
HK_TECH_CODES = {'012348', '513180'}          # 纯恒生科技系（场内 513180 + 场外联接 012348）
CPO_CODES = {'513050', '164906'}              # 中概/海外互联系（513050 中概互联 + 164906 交银海外互联）
BROAD_HK_CODES = {'000071', '159920'}         # 宽基中的恒生系
pure, cpo, broad, detail_hk = 0.0, 0.0, 0.0, []
for d in fix['detail']:
    code6 = ''.join(c for c in str(d['code']) if c.isdigit())
    mv = float(d['mv0_new']) + float(d['est_pnl'])
    if code6 in HK_TECH_CODES:
        pure += mv; detail_hk.append(('纯恒生科技系', code6, d['name'], round(mv, 2)))
    elif code6 in CPO_CODES:
        cpo += mv; detail_hk.append(('中概/海外互联系', code6, d['name'], round(mv, 2)))
    elif code6 in BROAD_HK_CODES:
        broad += mv; detail_hk.append(('宽基恒生系', code6, d['name'], round(mv, 2)))
hk_total = tracks['恒生科技']['mv'] + broad   # 双层拆解：赛道层 + 宽基层
print(f'\n港股暴露（§3.108 双层拆解）：总 {hk_total:,.2f} 元 = {hk_total/TOTAL*100:.2f}%')
print(f'  赛道层「恒生科技」{tracks["恒生科技"]["mv"]:,.2f} 元 = {tracks["恒生科技"]["pct_of_total"]:.2f}%'
      f'  +  宽基层「恒生系」{broad:,.2f} 元 = {broad/TOTAL*100:.2f}%')
print(f'  三段法：纯恒生科技系 {pure:,.2f}（{pure/TOTAL*100:.2f}%）/ 中概·海外互联系 {cpo:,.2f}（{cpo/TOTAL*100:.2f}%）'
      f'/ 宽基恒生系 {broad:,.2f}（{broad/TOTAL*100:.2f}%） = {pure+cpo+broad:,.2f} 元 '
      f'（{round(pure+cpo+broad, 2) == round(hk_total, 2)}）')
for r in detail_hk:
    print(f'    {r[0]} {r[1]} {r[2][:22]:24s} {r[3]:>10,.2f}')
print(f'  ⚠️ 口径说明：164906（交银海外互联）已计入「中概/海外互联系」（CPO_CODES）；'
      f'南向空窗（10/2、10/5、10/6、10/7 共 4 个港股交易日）的影响集中在纯恒生科技系与宽基恒生系')

# ---------- QDII 挂账预告（US 9/25 + US 9/28）----------
med_us = tracks['美股标普医药']['mv']
IYH_0925, IYH_0928 = 0.50, 0.32
comp = (1 + IYH_0925 / 100) * (1 + IYH_0928 / 100) - 1
for k in (0.60, 0.72, 0.90):
    print(f'  QDII 预告（传导系数 {k:.2f}）: {comp*100:+.4f}% × {k:.2f} = {comp*k*100:+.4f}% '
          f'→ {med_us*comp*k:+,.2f} 元')
q_mid = med_us * comp * 0.72
q_lo, q_hi = med_us * comp * 0.60, med_us * comp * 0.90
print(f'\nQDII 挂账预告（US 9/25 +0.50% 与 US 9/28 +0.32% 复合 {comp*100:+.4f}%）：'
      f'中枢 {q_mid:+,.2f} 元，区间 {q_lo:+,.2f} 元 ~ {q_hi:+,.2f} 元（敞口 {med_us:,.2f} 元）')

# ---------- 待消化合计（9/29 无新增定价，仅有 QDII 挂账）----------
print(f'\n9/29 待消化合计：{q_lo:+,.2f} 元 ~ {q_hi:+,.2f} 元（中枢 {q_mid:+,.2f} 元）'
      f'  = 组合 {q_mid/TOTAL*100:+.4f}%')

# ---------- 大消费 0.5% 纪律兑现 ----------
cut_pct = 0.5
cut_amt = round(TOTAL * cut_pct / 100, 2)
big = tracks['大消费']['mv']
cash = tracks['现金']['mv']
print(f'\n大消费 0.5% 纪律兑现（按修正后基准 {TOTAL:,.2f} 元）：{cut_amt:,.2f} 元')
print(f'  大消费 {big:,.2f} → {big-cut_amt:,.2f}（{big/TOTAL*100:.2f}% → {(big-cut_amt)/(TOTAL)*100:.2f}%）')
print(f'  现金    {cash:,.2f} → {cash+cut_amt:,.2f}（{cash/TOTAL*100:.2f}% → {(cash+cut_amt)/(TOTAL)*100:.2f}%）')

# ---------- 三条防线 ----------
print('\n三条防线（9/29 盘前基准）：')
print(f"  ① 中证消费 12,100 下沿：9/28 收 12,096.0166（已收盘级下破 −0.033%）→ 已破，"
      f"重新收复需 {(12100/12096.0166-1)*100:+.3f}%；下一线 12,000 距 {(12096.0166/12000-1)*100:+.2f}%")
print(f"  ② 恒生科技 4,250：9/28 收 4,296.00 → 距 {(4296.0/4250-1)*100:+.2f}%")
print(f"  ③ 美股标普医药 QDII 折价/汇率线：动态跟踪（历史 IYH 传导率 0.36~0.94）")

out = {
    'date': TODAY, 'session': 'preopen',
    'base_total': TOTAL, 'base_file': 'portfolio_close_20260928_fix.json',
    'tracks': {k: {'mv': v['mv'], 'pct_of_total': v['pct_of_total'], 'day_pct': v['day_pct']}
               for k, v in tracks.items()},
    'med_exposure': med, 'med_pct': round(med / TOTAL * 100, 2),
    'threshold_all_med': round(th_all, 2), 'threshold_a_sh_med': round(th_sh, 2),
    'hk_total': round(hk_total, 2), 'hk_total_pct': round(hk_total / TOTAL * 100, 2),
    'hk_segments': {'pure_hstech': round(pure, 2), 'china_internet': round(cpo, 2),
                    'broad_hk': round(broad, 2)},
    'qdii_pending': {'sessions': ['2026-09-25', '2026-09-28'], 'iyh_pct': [IYH_0925, IYH_0928],
                     'compound_pct': round(comp * 100, 4), 'coef_mid': 0.72,
                     'pnl_mid': round(q_mid, 2), 'pnl_low': round(q_lo, 2), 'pnl_high': round(q_hi, 2),
                     'note': ('QDII 000369/016280 最新出库净值日 = 2026-09-24，US 9/25 与 US 9/28 两个'
                              '交易日为挂账；按 IYH 复合 × 传导系数 0.72 预告，区间取系数 0.60~0.90')},
    'cut_big_consume': {'pct': cut_pct, 'amount': cut_amt,
                        'target': '000248 汇添富中证主要消费ETF联接A（被动联接，优先）',
                        'trigger': '中证消费 9/28 收盘级跌破 12,100（12,096.0166，−0.033%）'},
    'defense_lines': {'zz_consume_12100': {'last': 12096.0166, 'state': 'broken_close_level',
                                           'dist_pct': -0.033},
                      'hstech_4250': {'last': 4296.0, 'state': 'intact',
                                      'dist_pct': round((4296.0 / 4250 - 1) * 100, 2)}},
    'scenario': {
        'upside': '恒生科技收复 4,400 + 中证消费收复 12,100 + 医药不追高',
        'base': '指数缩量整固（成交 < 1.5 万亿）、结构延续防御（医药/必需消费/高股息）',
        'downside': '美债 5.25% 传导 + 解禁高峰 + 节前取现 → 上证失守 3,800 后加速',
    },
    'action': {'new_buy': 0, 'active_take_profit': 0, 'discipline_cut': cut_amt,
               'note': '除 9/28 已触发的大消费 0.5% 纪律兑现外，其余赛道实际动作 0'},
}
json.dump(out, open(os.path.join(HIST, f'portfolio_preopen_{TODAY.replace("-", "")}.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
print(f'\n已保存 portfolio_preopen_{TODAY.replace("-", "")}.json')
