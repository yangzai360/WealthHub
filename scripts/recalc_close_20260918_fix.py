# -*- coding: utf-8 -*-
"""2026-09-20 周日：对 9/18 收盘估算做「净值补更修正」（不覆盖原产物）
背景：9/18 20:00 时点 002708 / 002742 的 9/18 净值未出、000369 的 9/17 净值未出，均按 0 计入。
      9/20 已可获取 → 补更后重算 9/18 组合收益，用于周末档披露口径修正。
输出 data/processed/history/portfolio_close_20260918_fix.json
"""
import json, os
from collections import defaultdict

BASE = '/Users/jieyang/Documents/WealthHub'
HIST = os.path.join(BASE, 'data/processed/history')

orig = json.load(open(os.path.join(HIST, 'portfolio_close_20260918.json'), encoding='utf-8'))
BASE_TOTAL = orig['base_total']

# 补更表：code -> (nav_date, nav, pct)  —— 来自 9/20 F10 抓取
FIX = {
    '002708': ('2026-09-18', 1.9740, 0.87),
    '002742': ('2026-09-18', 1.2636, 0.00),
    '000369': ('2026-09-17', 2.5650, 0.51),
}

detail = []
chg = []
for x in orig['detail']:
    code6 = ''.join(c for c in x['code'] if c.isdigit())
    mv0 = float(x['mv'])
    sh = float(x['shares']) if x['shares'] else 0.0
    est_pct, est_pnl, src = x['est_pct'], x['est_pnl'], x['price_src']
    if code6 in FIX and sh:
        nd, nav, _ = FIX[code6]
        old_nav = mv0 / sh
        new_pct = round((nav / old_nav - 1) * 100, 4)
        # 用「base 隐含价 → 新净值」重算（保持与原链式法一致：base mv 为基准）
        est_pct = new_pct
        est_pnl = round(mv0 * est_pct / 100, 2)
        src = f'补更 {nd} 净值 ({nav})｜原口径 {x["price_src"]}'
        chg.append((code6, x['name'], x['track'], x['est_pnl'], est_pnl, round(est_pnl - x['est_pnl'], 2)))
    detail.append({**x, 'est_pct_fix': est_pct, 'est_pnl_fix': est_pnl, 'price_src_fix': src,
                   'est_pct': est_pct, 'est_pnl': est_pnl})

total_pnl = round(sum(d['est_pnl'] for d in detail), 2)
total_pct = round(total_pnl / BASE_TOTAL * 100, 2)
new_total = round(BASE_TOTAL + total_pnl, 2)

tracks = defaultdict(lambda: {'mv': 0.0, 'pnl': 0.0})
for d in detail:
    tracks[d['track']]['mv'] += d['mv']
    tracks[d['track']]['pnl'] += d['est_pnl']
for k, v in tracks.items():
    v['mv'] = round(v['mv'], 2); v['pnl'] = round(v['pnl'], 2)
    v['pct_of_total'] = round(v['mv'] / new_total * 100, 2)
    v['day_pct'] = round(v['pnl'] / v['mv'] * 100, 3) if v['mv'] else 0.0

med = sum(v['mv'] for k, v in tracks.items() if k in ('A股医药', '美股标普医药'))
out = {'date': '2026-09-18', 'as_of': '2026-09-18收盘(净值补更修正)',
       'base_total': BASE_TOTAL, 'est_total_pnl': total_pnl, 'est_total_pct': total_pct,
       'total_mv': new_total, 'tracks': dict(tracks),
       'med_exposure': round(med, 2), 'med_pct': round(med / new_total * 100, 2),
       'detail': detail,
       'fix_applied': [{'code': c, 'name': n, 'track': t, 'pnl_old': o, 'pnl_new': nn, 'delta': dd}
                       for c, n, t, o, nn, dd in chg]}
json.dump(out, open(os.path.join(HIST, 'portfolio_close_20260918_fix.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)

print('原口径 9/18:', f"{orig['est_total_pct']:+.2f}% ({orig['est_total_pnl']:+,.2f} 元)  总资产 {orig['total_mv']:,.2f}")
print(f'补更后 9/18: {total_pct:+.2f}% ({total_pnl:+,.2f} 元)  总资产 {new_total:,.2f}')
print(f'修正量: {round(total_pnl - orig["est_total_pnl"], 2):+,.2f} 元  ({round(total_pct - orig["est_total_pct"], 3):+.3f} pct)')
print('\n补更明细:')
for c, n, t, o, nn, dd in chg:
    print(f'  {t:8s} {n[:22]:22s} {c}  {o:+.2f} → {nn:+.2f}  (Δ {dd:+.2f})')
print('\n赛道(修正后):')
for k, v in sorted(tracks.items(), key=lambda kv: -kv[1]['mv']):
    print(f"  {k:8s} mv={v['mv']:>11,.2f} pct={v['pct_of_total']:>6.2f}% day={v['day_pct']:+.3f}% pnl={v['pnl']:>+9,.2f}")
print(f"\n医药敞口 {out['med_pct']:.2f}%")
print('SAVED portfolio_close_20260918_fix.json')
