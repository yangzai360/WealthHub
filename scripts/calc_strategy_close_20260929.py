# -*- coding: utf-8 -*-
"""2026-09-29 盘后档：策略判定产物（基准 = 9/28 修正收盘 375,885.31 元 → 9/29 收盘 376,574.96 元）
输出：portfolio_strategy_close_20260929.json —— 三条防线的收盘级判定（判定权由 20:00 盘后档接管，§3.113i）、
      纪律执行台账、敞口/门槛、港股暴露三层拆解、待消化、操作清单

⚠️ §3.113i：盘中档只做「盘中破位确认」，判定权与执行权移交盘后档（以收盘价为准）；
   本档为最终判定，不得被盘中档预判覆盖。
⚠️ 防线距离口径（§知识库 line 1244）：下沿防线（跌破才触发）用 (收盘 − 防线)/防线。
"""
import json, os

BASE = '/Users/jieyang/Documents/WealthHub'
HIST = os.path.join(BASE, 'data/processed/history')
TODAY = '2026-09-29'

fix = json.load(open(os.path.join(HIST, 'portfolio_close_20260928_fix.json'), encoding='utf-8'))
pf = json.load(open(os.path.join(HIST, 'portfolio_close_20260929.json'), encoding='utf-8'))
BASE_TOTAL, TOTAL = fix['total_mv'], pf['total_mv']
print(f'基准（9/28 修正收盘）= {BASE_TOTAL:,.2f} 元  →  9/29 收盘 = {TOTAL:,.2f} 元（{pf["est_total_pct"]:+.4f}%）')

# ---------- ① 三条防线：收盘级判定 ----------
ZZ_C, HST = 12107.1705, 4249.62          # 中证消费 / 恒生科技 9/29 收盘
MED_PROXY = pf['board_med']               # A股医药板块代理单日涨跌（%）
zz_dist = (ZZ_C / 12100 - 1) * 100
hst_dist = (HST / 4250 - 1) * 100
lines = {
    'zz_consume_12100': {
        'line': 12100.0, 'close': ZZ_C, 'dist_pct': round(zz_dist, 4),
        'state': 'restored_close_level' if ZZ_C >= 12100 else 'broken_close_level',
        'verdict': ('收盘 12,107.1705 收复 12,100（+0.0593%）→ 9/28 执行的 0.5% 兑现'
                    '**事后确认为「技术性误触」**（假破位），显式记录，**纪律不改回**、不补回仓位；'
                    '防线回归 12,100（下一线 12,000）'),
    },
    'hstech_4250': {
        'line': 4250.0, 'close': HST, 'dist_pct': round(hst_dist, 4),
        'state': 'broken_close_level' if HST < 4250 else 'intact',
        'verdict': ('收盘 4,249.62 低于防线 4,250（-0.0089%）→ **收盘级有效跌破成立**；'
                    '按 9/24 防线设立时预设的纪律「收盘级跌破 → 重启 0.5% 减仓」，'
                    '**本档判定执行**（执行权属下一可交易档 9/30 盘前）'),
    },
    'a_med_reverse_1_5pct': {
        'line_pct': -1.5, 'proxy_pct': MED_PROXY,
        'state': 'not_triggered' if MED_PROXY > -1.5 else 'triggered',
        'verdict': f'板块代理单日 {MED_PROXY:+.4f}% > -1.5% → 未触发（该线为「利好兑现回调观察线」非止损线）',
    },
}
for k, v in lines.items():
    print(f"  {k:22s} {v['state']:22s} {v.get('dist_pct', v.get('proxy_pct'))}")

# ---------- ② 纪律执行台账（0.5% = 组合总资产的 0.5pct，口径同 9/28 大消费兑现）----------
CUT_PCT = 0.5
cut_amt = round(TOTAL * CUT_PCT / 100, 2)
print(f'\n纪律减仓金额 = {TOTAL:,.2f} × {CUT_PCT}% = {cut_amt:,.2f} 元'
      f'（口径：组合总资产 × 0.5pct，与 9/28 大消费 {round(BASE_TOTAL*0.005,2):,.2f} 元同式）')

# 恒生科技赛道层逐券（按 §3.112a 还原式 mv0_new + est_pnl 取市值）
hk_rows = []
for d in pf['detail']:
    if d['track'] == '恒生科技':
        hk_rows.append({'code': str(d['code']), 'name': d['name'],
                        'shares': d['shares'], 'mv': round(d['mv0_new'] + d['est_pnl'], 2),
                        'est_pct': d['est_pct']})
hk_rows.sort(key=lambda r: -r['mv'])
for r in hk_rows:
    print(f"  {r['code']:10s} {r['name'][:30]:32s} mv={r['mv']:>10,.2f}  {r['est_pct']:+.4f}%")
print(f"  赛道层合计 = {sum(r['mv'] for r in hk_rows):,.2f} 元（tracks.mv = {pf['tracks']['恒生科技']['mv']:,.2f}）")

# ---------- ③ 敞口与门槛方程（§3.98）----------
tracks = pf['tracks']
med = pf['med_exposure']
B = TOTAL - med
print(f'\n医药总敞口 {med:,.2f} 元 = {pf["med_pct"]:.2f}%  距 40% 上限 {40 - pf["med_pct"]:.2f}pct')
print(f'  门槛：两医药赛道同涨 {pf["threshold_all_med"]:+.2f}%  /  仅 A股医药 {pf["threshold_a_sh_med"]:+.2f}%')

# ---------- ④ 港股暴露三层拆解（§3.108 条款 23/24）----------
hk = pf['hk_split']
hkp = pf['hk_split_pnl']
print(f'\n港股暴露（三层）：总 {pf["hk_total"]:,.2f} 元 = {pf["hk_total_pct"]:.2f}%')
for k, label in (('pure', '纯恒生科技系'), ('concept', '中概/海外互联系'), ('broad', '宽基恒生系')):
    print(f'  {label:14s} {hk[k]:>10,.2f} 元 = {hk[k]/TOTAL*100:>5.2f}%   当日盈亏 {hkp[k]:>+9.2f} 元')
print(f'  → 当日合计 {sum(hkp.values()):+,.2f} 元；只报赛道层 {tracks["恒生科技"]["pct_of_total"]:.2f}% '
      f'会低估 {hk["broad"]/TOTAL*100:.2f}pct')

# ---------- ⑤ 待消化 ----------
dis = {
    'close_or_pending_emitted': 'portfolio_close_20260929.json（正常交易日 → 产出 `close`，不产 `pending`）',
    'new_pending': 0.0,
    'unquantified': [{
        'code': '164906', 'name': '交银中证海外中国互联网(LOF)A + 交银海外互联A',
        'reason': 'US 9/25-9/28 两日净值挂账，传导系数未标定 → 不计入待消化合计，仅作披露',
        'ref_index': '纳斯达克中国金龙指数（9/25 -0.64% / 9/28 +1.12%，复合 +0.47%）',
        'approx': '+44 元（量级，全档不变）',
    }],
    'qdii_warehouse_closed': '000369 / 016280 的 9/28 净值已出库 → 挂账闭环（真实兑现 +302.77 元）',
}

out = {
    'date': TODAY, 'as_of': '2026-09-29收盘',
    'base_total': BASE_TOTAL, 'base_file': 'portfolio_close_20260928_fix.json',
    'total_mv': TOTAL, 'est_total_pnl': pf['est_total_pnl'], 'est_total_pct': pf['est_total_pct'],
    'defense_lines': lines,
    'defense_lines_note': ('判定权由 20:00 盘后档接管（§3.113i）；防线触发条件一律以「收盘价」为准，'
                           '盘中破位仅作预警（知识库「盘中破位 vs 收盘确认」固化规则）'),
    'discipline': {
        'trigger': '恒生科技 9/29 收盘 4,249.62 跌破 4,250 防线（-0.0089%，收盘级）',
        'pct': CUT_PCT, 'amount': cut_amt, 'base_used': TOTAL,
        'base_rule': '组合总资产 × 0.5pct（与 9/28 大消费兑现同式，基准取「防线判定日收盘总资产」）',
        'target_primary': '012348 天弘恒生科技联接A（被动联接，纯恒科口径，优先）',
        'target_alt': '513180 恒指科技（场内 ETF，纯恒科口径）',
        'not_target': '164906 / 513050（中概互联口径）—— 防线对应 HSTECH，减仓应落在纯恒科，不落在中概',
        'settle': '9/30（节前最后一个 A股交易日）按 9/30 净值成交；场外联接净值只在 A股交易日发布',
        'margin_note': ('⚠️ 本次为「边际破位」（仅低于防线 0.38 点 / -0.0089%），为防线设立以来最贴线的一次；'
                        '但仍满足「收盘价 < 防线」的二元判据，按纪律执行，不引入主观容差（避免规则漂移）'),
    },
    'exposure': {
        'med_total': med, 'med_pct': pf['med_pct'], 'med_limit_pct': 40.0,
        'threshold_all_med_pct': pf['threshold_all_med'],
        'threshold_a_sh_med_pct': pf['threshold_a_sh_med'],
        'non_med_total': round(B, 2),
    },
    'hk_exposure': {'split': hk, 'pnl': hkp, 'total': pf['hk_total'], 'pct': pf['hk_total_pct'],
                    'note': '三层拆解（纯恒科 / 中概互联 / 宽基恒生系）；只报赛道层会低估宽基层'},
    'risk': json.load(open(os.path.join(HIST, 'risk_stats_close_20260929.json'), encoding='utf-8')),
    'pending': dis,
    'action': {
        'new_buy': 0, 'active_take_profit': 0,
        'discipline_cut': cut_amt, 'discipline_cut_target': '012348 天弘恒生科技联接A',
        'note': ('除 9/29 盘前档已触发的大消费 0.5% 兑现（1,879.43 元）与本档判定的恒生科技 0.5% 减仓'
                 f'（{cut_amt:,.2f} 元）外，其余赛道动作 0；两条纪律单合计约 {1879.43 + cut_amt:,.2f} 元'),
    },
    'note': ('⚠️ 「技术性误触」口径落地：中证消费 9/29 收盘 12,107.1705 收复 12,100 → 9/28 兑现定性为假破位，'
             '记录而不改回；⚠️ 恒生科技 4,250 收盘级跌破 → 执行 0.5% 减仓，标的限纯恒科（012348/513180）'),
}
json.dump(out, open(os.path.join(HIST, f'portfolio_strategy_close_{TODAY.replace("-", "")}.json'), 'w',
                    encoding='utf-8'), ensure_ascii=False, indent=1)
print(f'\n已保存 portfolio_strategy_close_{TODAY.replace("-", "")}.json')
