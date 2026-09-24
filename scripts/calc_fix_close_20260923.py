# -*- coding: utf-8 -*-
"""2026-09-24 盘前：9/23 组合收盘「真实净值兜底修正」
背景：9/23 盘后档 calc_portfolio_close_20260923.py 对 8 只被动联接/债券类基金用「指数代理」
      （§3.98 口径，偏差 ≤0.01pct）；本档取得 9/23 真实净值后做兜底修正。
方法：以 portfolio_close_20260923.json 的 detail 为基准，仅替换 8 只 REAL_NAV 券的 est_pct，
      重算赛道与总资产；其余行原样保留（保持与盘后档一致）。
输出：portfolio_close_20260923_fix.json（9/24 盘前基准）
"""
import json, os

BASE = '/Users/jieyang/Documents/WealthHub'
HIST = os.path.join(BASE, 'data/processed/history')
TODAY = '2026-09-23'

# 9/23 真实净值（F10 直连，本档新增入库）
REAL_NAV = {
    '000968': ('2026-09-23', 0.8219, -0.75, '广发养老产业'),
    '002742': ('2026-09-23', 1.2634, -0.07, '泓德裕祥债券A'),
    '004752': ('2026-09-23', 0.8151, -2.41, '广发传媒ETF联接A'),
    '001180': ('2026-09-23', 0.8165, 0.13, '广发医药卫生'),
    '000051': ('2026-09-23', 1.7310, -0.57, '华夏沪深300'),
    '000071': ('2026-09-23', 1.4665, -0.92, '华夏恒生ETF联接A'),
    '001469': ('2026-09-23', 1.2483, -0.52, '广发金融地产'),
    '012323': ('2026-09-23', 0.6012, 0.30, '华宝中证医疗C'),
}

p = json.load(open(os.path.join(HIST, 'portfolio_close_20260923.json'), encoding='utf-8'))
base_total = 383598.81  # 9/22 收盘修正口径

detail = []
report = []
for x in p['detail']:
    code6 = ''.join(c for c in str(x['code']) if c.isdigit())
    d = dict(x)
    old = d['est_pct']
    if code6 in REAL_NAV:
        nd, nav, pct_f10, nm = REAL_NAV[code6]
        sh = float(d['shares']) if d['shares'] else 0.0
        if sh:
            implied = float(d['mv']) / sh
            real_pct = round((nav / implied - 1) * 100, 4)
        else:
            real_pct = pct_f10
        d['est_pct'] = real_pct
        d['price_src'] = f'净值 9/23 ({nav}) [兜底修正]'
        report.append((code6, d['name'], old, real_pct, d['mv'], real_pct - old))
    d['est_pnl'] = round(float(d['mv']) * d['est_pct'] / 100, 2)
    detail.append(d)

total_pnl = round(sum(d['est_pnl'] for d in detail), 2)
total_pct = round(total_pnl / base_total * 100, 4)
new_total = round(base_total + total_pnl, 2)

tracks = {}
for d in detail:
    t = tracks.setdefault(d['track'], {'mv0': 0.0, 'mv': 0.0, 'pnl': 0.0})
    t['mv0'] += d['mv']
    t['mv'] += d['mv'] + d['est_pnl']
    t['pnl'] += d['est_pnl']
for k, v in tracks.items():
    for f in ('mv0', 'mv', 'pnl'):
        v[f] = round(v[f], 2)
    v['pct_of_total'] = round(v['mv'] / new_total * 100, 2)
    v['day_pct'] = round(v['pnl'] / v['mv0'] * 100, 3) if v['mv0'] else 0.0

med = round(tracks['A股医药']['mv'] + tracks['美股标普医药']['mv'], 2)
A = med
B = new_total - med
threshold_all = round(((0.40 / 0.60) * B / A - 1) * 100, 2)
A_sh = tracks['A股医药']['mv']
threshold_sh = round((((0.40 / 0.60) * B - (med - A_sh)) / A_sh - 1) * 100, 2)

out = {
    'date': TODAY, 'as_of': '2026-09-23收盘(净值补更修正)',
    'base_total': base_total, 'est_total_pnl': total_pnl,
    'est_total_pct': round(total_pct, 2), 'est_total_pct_raw': total_pct,
    'total_mv': new_total, 'tracks': tracks,
    'med_exposure': med, 'med_pct': round(med / new_total * 100, 2),
    'threshold_all_med': threshold_all, 'threshold_a_sh_med': threshold_sh,
    'correction_note': (
        f'9/23 盘后档代理估算 -0.1393% (-534.19 元) → 真实净值修正 {total_pct:.4f}% '
        f'({total_pnl:+.2f} 元)；修正量 {total_pct - (-0.1393):+.4f}pct / {total_pnl - (-534.19):+.2f} 元；'
        '8 只被动联接/债券类由指数代理改为 9/23 真实净值'),
    'fix_source': 'fetch_preopen_20260924（F10 直连真实净值）',
    'detail': detail,
}
json.dump(out, open(os.path.join(HIST, 'portfolio_close_20260923_fix.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)

print('=== 8 只代理券兜底修正明细 ===')
for code6, nm, old, new, mv, diff in report:
    print(f'  {code6} {nm:22s} 代理 {old:+.2f}% → 真实 {new:+.4f}%  (差 {diff:+.4f}pct, mv={mv:,.2f})')
tot_diff = sum(d[3] - d[2] for d in report)
print(f'  修正合计影响：代理口径 {sum(d[3] for d in report):+.2f}pct(加权) / 直接盈亏差 ')
print()
print(f'★ 9/23 组合修正后 {total_pct:+.4f}% ({total_pnl:+,.2f} 元)  总资产 {new_total:,.2f} (基准 {base_total:,.2f})')
print(f'  医药敞口 {out["med_pct"]:.2f}%  门槛(全部医药) {threshold_all:+.2f}% / (仅A股医药) {threshold_sh:+.2f}%')
print('\n赛道:')
for k, v in sorted(tracks.items(), key=lambda kv: -kv[1]['mv0']):
    print(f"  {k:10s} mv0={v['mv0']:>11,.2f} w={v['pct_of_total']:>6.2f}% day={v['day_pct']:+.3f}% pnl={v['pnl']:>+9,.2f}")
print('\n个券贡献（按 |pnl| 排序前 20）:')
for d in sorted(detail, key=lambda y: -abs(y['est_pnl']))[:20]:
    print(f"  {d['track']:10s} {d['name'][:24]:24s} {d['code']:9s} {d['est_pct']:+.4f}% pnl={d['est_pnl']:>+9,.2f}  [{d['price_src']}]")
