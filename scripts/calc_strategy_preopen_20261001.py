# -*- coding: utf-8 -*-
"""2026-10-01（周四 · 国庆长假首日 · 纯非交易日）盘前档：组合策略计算
基准 = 9/30 修正收盘（portfolio_close_20260930_fix.json）= 380,888.29 元
输出：portfolio_preopen_20261001.json —— 敞口、门槛方程、港联系三层拆解、假期挂账区间、节后预案
⚠️ 档型①（纯非交易日：A股 + 港股均休市）：
   → 不产出 portfolio_close_* 也不产出 portfolio_pending_*、不做「待消化」测算（§3.109 / AGENTS.md #25）；
   → 基准直接取最近收盘修正件（tracks[].mv 求和校验）；
   → 本文件仅作「盘前敞口快照 + 挂账区间披露」，账面无新增定价。
⚠️ §3.107：QDII/LOF 券「基准已含哪一日净值」从 price_src 字符串解析，不得用固定日期常量。
"""
import json, os, re

BASE = '/Users/jieyang/Documents/WealthHub'
HIST = os.path.join(BASE, 'data/processed/history')
TODAY = '2026-10-01'
BASEFILE = 'portfolio_close_20260930_fix.json'
fix = json.load(open(os.path.join(HIST, BASEFILE), encoding='utf-8'))

TOTAL = fix['total_mv']
tracks = fix['tracks']
print(f'基准（9/30 修正收盘）= {TOTAL:,.2f} 元  ← {BASEFILE}')
print(f'  ⚠️ 档型①「纯非交易日」（A股 10/1-10/7 全休 + 港股 10/1 休）→ 不产 close / pending 产物、不做待消化测算')
# 硬守卫：Σ tracks.mv 与 total_mv 一致（§3.104 / §3.107）
dev = abs(sum(v['mv'] for v in tracks.values()) - TOTAL)
print(f'  硬守卫 |Σ tracks.mv − total_mv| = {dev:.4f} 元  {"✅" if dev < 1.5 else "❌ 终止"}')
assert dev < 1.5, 'Σ tracks.mv 与 total_mv 不一致，终止本档计算（§3.104）'

for k, v in sorted(tracks.items(), key=lambda kv: -kv[1]['mv']):
    print(f"  {k:10s} mv={v['mv']:>11,.2f}  w={v['pct_of_total']:>6.2f}%  day={v['day_pct']:+.3f}%")

# ---------- 医药敞口与门槛方程（§3.98 / §3.112）----------
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
print('  ⚠️ 港联系「南向空窗」= 10/2、10/5、10/6、10/7 共 4 个港股交易日（港股通关闭），'
      '该窗口波动率须按「外资主导」建模（§3.113a/§3.115d）')

# ---------- 恒生科技 0.5% 纪律减仓（9/30 已执行，价值中性）----------
cut = fix.get('discipline', {})
cut_pct, cut_amt = 0.5, cut.get('amount', 1882.46)
hk_after = tracks['恒生科技']['mv'] - cut_amt
cash_after = tracks['现金']['mv'] + cut_amt
print(f'\n恒生科技 {cut_pct}% 纪律减仓（9/30 已执行结算）：{cut_amt:,.2f} 元')
print(f'  恒生科技 {tracks["恒生科技"]["mv"]:,.2f} → {hk_after:,.2f}（{tracks["恒生科技"]["pct_of_total"]:.2f}% → {hk_after/TOTAL*100:.2f}%）')
print(f'  现金     {tracks["现金"]["mv"]:,.2f} → {cash_after:,.2f}（{tracks["现金"]["pct_of_total"]:.2f}% → {cash_after/TOTAL*100:.2f}%）')
print(f'  口径：{cut.get("settle","")}')

# ---------- 假期挂账区间（§3.112f：只给区间、不给方向）----------
med_us = tracks['美股标普医药']['mv']
IYH_0929, IYH_0930 = -0.36, -1.17
comp = (1 + IYH_0929 / 100) * (1 + IYH_0930 / 100) - 1
qdii_out = fix.get('pending', {}).get('qdii_observable_amount', -267.82)
print(f'\n假期挂账区间（10/8 一次性释放；§3.112f 只给区间、不给方向）')
print(f'  A) QDII 000369/016280 的 9/29 净值已出库但挂账：{qdii_out:+,.2f} 元（基准净值日 9/28）')
print(f'  B) US 9/29 (IYH {IYH_0929:+.2f}%) + US 9/30 (IYH {IYH_0930:+.2f}%) 复合 {comp*100:+.4f}%')
print(f'     标的市值 {med_us:,.2f} 元 → 未打折损益 {med_us*comp:+,.2f} 元')
for k in (0.62, 0.72, 0.90):
    print(f'     传导系数 {k:.2f}: {med_us*comp*k:+,.2f} 元')
lo_b = med_us * comp * 0.90   # 系数越大负值越大 → 下界
hi_b = med_us * comp * 0.62
mid_b = med_us * comp * 0.72
print(f'  → B 区间 {hi_b:+,.2f} 元 ~ {lo_b:+,.2f} 元（中枢 {mid_b:+,.2f} 元）')
print(f'  → A+B 合计区间 {qdii_out+hi_b:+,.2f} 元 ~ {qdii_out+lo_b:+,.2f} 元（中枢 {qdii_out+mid_b:+,.2f} 元）'
      f' = 组合 {(qdii_out+mid_b)/TOTAL*100:+.4f}%')
print('  ⚠️ 未量化：US 10/1、10/2、10/5、10/6、10/7 共 5 个交易日完全未知 → 区间可能显著放大，不得作方向依据')
print('  ⚠️ 场外 QDII 在 A股 休市期不发布净值 → 10/8 实际可回填的净值日可能仍停在 9/30，'
      '10/1-10/7 的 5 个美股交易日将顺延至 10/8 之后的净值周期（§3.117a）')

# ---------- 三条防线（9/30 收盘口径）----------
HS, ZZ, SH = 4253.89, 12295.9591, 3842.1946
MED933_1D = (8009.6669 / 7786.2255 - 1) * 100
print('\n三条防线（9/30 收盘口径）：')
print(f'  ① 恒生科技 4,250：9/30 收 {HS:,.2f} → {(HS/4250-1)*100:+.4f}% 【贴线收复，安全垫仅 {HS-4250:,.2f} 点】')
print(f'  ② 中证消费 12,100 下沿：9/30 收 {ZZ:,.4f} → {(ZZ/12100-1)*100:+.4f}% 【收复且拉开 1.62pct；'
      f'下一线 12,000 距 {(ZZ/12000-1)*100:+.2f}%】')
print(f'  ③ A股医药反向兑现线（板块代理单日 ≥1.5% 跌幅）：9/30 板块代理 {MED933_1D:+.4f}% → 未触发（方向相反）')
print(f'  附：上证 9/30 收 {SH:,.4f}')

# ---------- 情景（本档为纯非交易日 → 无 A股/港股 定价）----------
out = {
    'date': TODAY, 'session': 'preopen', 'session_type': 'pure_non_trading_day_preopen',
    'base_total': TOTAL, 'base_file': BASEFILE,
    'base_revision': {
        'prev_total': 381437.68, 'delta': round(TOTAL - 381437.68, 2),
        'reason': '7 只 / 8 行取得 9/30 真实净值补更（002708 / 161616 / 001180 / 000727 / 110020 / 002742 / 004752）'},
    'tracks': {k: {'mv': v['mv'], 'pct_of_total': v['pct_of_total'], 'day_pct': v['day_pct']}
               for k, v in tracks.items()},
    'tracks_weight_after_discipline': {
        '恒生科技': round(hk_after / TOTAL * 100, 2), '现金': round(cash_after / TOTAL * 100, 2)},
    'med_exposure': med, 'med_pct': round(med / TOTAL * 100, 2),
    'threshold_all_med': round(th_all, 2), 'threshold_a_sh_med': round(th_sh, 2),
    'non_med_total': round(B, 2),
    'hk_total': round(hk_total, 2), 'hk_total_pct': round(hk_total / TOTAL * 100, 2),
    'hk_segments': {'pure_hstech': round(pure, 2), 'china_internet': round(cpo, 2),
                    'broad_hk': round(broad, 2)},
    'hk_southbound_gap_days': ['2026-10-02', '2026-10-05', '2026-10-06', '2026-10-07'],
    'discipline_hstech': {'pct': cut_pct, 'amount': cut_amt, 'settled_on': '2026-09-30',
                          'hk_after': round(hk_after, 2), 'cash_after': round(cash_after, 2),
                          'note': '9/29 收盘级破位触发 → 9/30 结算；价值中性、P&L 口径不变，仅权重单列'},
    'holiday_pending': {
        'window': ['2026-09-29', '2026-09-30', '2026-10-01', '2026-10-02', '2026-10-05',
                   '2026-10-06', '2026-10-07'],
        'n_us_sessions': 7,
        'settle_date': '2026-10-08',
        'component_a': {'desc': 'QDII 000369/016280 的 9/29 净值（基准净值日 9/28）', 'amount': qdii_out},
        'component_b': {'desc': f'US 9/29 + 9/30（IYH 复合 {comp*100:+.4f}%）× 传导系数',
                        'notional': round(med_us * comp, 2),
                        'low': round(lo_b, 2), 'mid': round(mid_b, 2), 'high': round(hi_b, 2)},
        'total_low': round(qdii_out + lo_b, 2), 'total_mid': round(qdii_out + mid_b, 2),
        'total_high': round(qdii_out + hi_b, 2),
        'known_sessions_only': True,
        'unknown_sessions': ['2026-10-01', '2026-10-02', '2026-10-05', '2026-10-06', '2026-10-07'],
        'note': ('§3.112f：只给区间、不给方向。仅 US 9/29 + 9/30 两日可确认；'
                 '10/1-10/7 的 5 个美股交易日完全未知。场外 QDII 在 A股 休市期不发布净值，'
                 '10/8 实际可回填净值日可能仍停在 9/30（§3.117a）。')},
    'defense_lines': {
        'hstech_4250': {'last': HS, 'state': 'restored_close_level_close_to_line',
                        'dist_pct': round((HS / 4250 - 1) * 100, 4), 'cushion_pts': round(HS - 4250, 2)},
        'zz_consume_12100': {'last': ZZ, 'state': 'restored_close_level',
                             'dist_pct': round((ZZ / 12100 - 1) * 100, 4),
                             'next_line': 12000, 'next_line_dist_pct': round((ZZ / 12000 - 1) * 100, 2)},
        'a_med_reverse_1_5pct': {'proxy_pct': round(MED933_1D, 4), 'state': 'not_triggered'},
        'sh_comp': {'last': SH}},
    'scenario': {
        'upside': ('隔夜美股（US 9/30）防御补跌为「季节性与权重股事件驱动」（礼来数据 + 联合健康），'
                   '若 10/2 非农不及预期 → 加息预期进一步降温 → 10/8 复市恒生科技收复 4,250 并拉开安全垫，'
                   'A股医药延续 9/30 的 BD / 政策双线吸金'),
        'base': ('长假首日 A股 + 港股 均休市，无本地定价；组合账面冻结在 9/30 修正收盘 380,888.29 元；'
                 '唯一可观测增量 = 隔夜美股（US 9/30）与挂账窗口'),
        'downside': ('① 隔夜防御双杀（必需消费 −1.68% / 医疗 −1.39%）延续至 10/1-10/7 → 挂账区间显著超预期；'
                     '② 美债长端「逆 PCE 上行」持续（10Y 5.29% / 30Y 5.63%）压制成长贴现率；'
                     '③ 港股 10/2 复市后 4 个交易日「南向空窗」由外资主导定价，波动率放大；'
                     '④ 9/30 A股医药 +2.96% 由 CRO/重组蛋白主题资金驱动，节后主题退潮回撤幅度将大于板块指数'),
    },
    'action': {'new_buy': 0, 'active_take_profit': 0, 'discipline_cut': 0,
               'settled_discipline_cut': cut_amt,
               'note': ('本档为纯非交易日，A股/港股 均无交易 → 赛道级动作全部为 0；'
                        '恒生科技 0.5% 纪律减仓已于 9/30 结算，纪律不改回；'
                        '医药敞口 39.23% 距 40% 上限仅 0.77pct，节后不主动加仓；'
                        '现金 7.67%（纪律后 8.16%）维持长假缓冲')},
    'calendar': {'2026-10-01': 'A股休市 + 港股休市 + 港股通关闭（长假首日）；美股照常交易',
                 '2026-10-02': 'A股休市；港股复市；港股通关闭；美股 9 月非农（北京 20:30）',
                 '2026-10-03~10-04': 'A股/港股/美股均休（周末）',
                 '2026-10-05~10-07': 'A股休市；港股交易（南向空窗）；美股照常',
                 '2026-10-08': 'A股复市 + 港股通恢复 → 挂账一次性释放与对账'},
}
json.dump(out, open(os.path.join(HIST, f'portfolio_preopen_{TODAY.replace("-", "")}.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
print(f'\n已保存 portfolio_preopen_{TODAY.replace("-", "")}.json')
print('⚠️ 本档不产出 portfolio_close_* / portfolio_pending_* 产物，不做待消化测算（§3.109 档型①）')
