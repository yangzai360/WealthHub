# -*- coding: utf-8 -*-
"""2026-09-18 盘后：组合收盘估算（链式法，§3.79/§3.85/§3.88 口径）
base = portfolio_preopen_20260918.json 的 detail（= 9/17 收盘值：场内 9/17 收盘、场外 A股类 9/17 净值、QDII/LOF 9/16 净值）
BASE_TOTAL = 376,270.08（9/17 盘后归档链式值 = 当日涨跌基准）
day_pct 逐券 = 最新可得价 / base 隐含价 - 1
  · 场内 = 9/18 收盘价
  · 场外 A股类 = 9/18 净值（18 只已出）
  · QDII/LOF（000369/016280/164906）= 最新可得（164906→9/17、000369/016280→9/16）
  · 002708 / 002742 9/18 净值未出 → 按 0 并标注（待 9/21 盘前兜底）
"""
import json, os
from collections import defaultdict

BASE = '/Users/jieyang/Documents/WealthHub'
HIST = os.path.join(BASE, 'data/processed/history')
TODAY = '2026-09-18'
BASE_TOTAL = 376270.08
QDII = ('000369', '016280', '164906')

base = json.load(open(os.path.join(HIST, 'portfolio_preopen_20260918.json'), encoding='utf-8'))
cur = json.load(open(os.path.join(HIST, 'close_' + TODAY.replace('-', '') + '.json'), encoding='utf-8'))

PX = {x['code'].replace('sh', '').replace('sz', ''): x['close'] for x in cur['etf']}
for x in cur['stocks']:
    PX[x['code'].replace('sh', '').replace('sz', '')] = x['close']

NAV = {}
for n in cur['fund_navs']:
    if n['nav_date'] < '2026-09-11':
        continue
    if n['code'] not in NAV or n['nav_date'] > NAV[n['code']][0]:
        NAV[n['code']] = (n['nav_date'], n['nav'])

detail = []
missing = []
for x in base['detail']:
    code6 = ''.join(c for c in x['code'] if c.isdigit())
    sh = float(x['shares']) if x['shares'] else 0.0
    mv0 = float(x['mv'])
    if code6 == '' or sh == 0:
        pct, src = 0.0, '现金'
    elif code6 in PX:
        pct, src = round((PX[code6] / (mv0 / sh) - 1) * 100, 4), f'场内收盘 {PX[code6]}'
    elif code6 in NAV:
        nd, nav = NAV[code6]
        pct = round((nav / (mv0 / sh) - 1) * 100, 4)
        if nd == TODAY:
            src = f'净值 9/18 ({nav})'
        elif code6 in QDII:
            src = f'QDII/LOF T+1 净值 {nd} ({nav})'
        else:
            src = f'净值未更新({nd})→按0'
            missing.append((code6, x['name'], nd))
            pct = 0.0
    else:
        pct, src = 0.0, '数据暂缺→按0'
        missing.append((code6, x['name'], None))
    detail.append({**x, 'est_pct': pct, 'est_pnl': round(mv0 * pct / 100, 2), 'price_src': src})

total_pnl = round(sum(d['est_pnl'] for d in detail), 2)
total_pct = round(total_pnl / BASE_TOTAL * 100, 2)
new_total = round(BASE_TOTAL + total_pnl, 2)

tracks = defaultdict(lambda: {'mv': 0.0, 'pnl': 0.0})
for d in detail:
    tracks[d['track']]['mv'] += d['mv']
    tracks[d['track']]['pnl'] += d['est_pnl']
for k, v in tracks.items():
    v['mv'] = round(v['mv'], 2); v['pnl'] = round(v['pnl'], 2)
    v['pct_of_total'] = round(v['mv'] / BASE_TOTAL * 100, 2)
    v['day_pct'] = round(v['pnl'] / v['mv'] * 100, 3) if v['mv'] else 0.0

med = sum(v['mv'] for k, v in tracks.items() if k in ('A股医药', '美股标普医药'))
out = {'date': TODAY, 'as_of': '2026-09-18收盘', 'base_total': BASE_TOTAL,
       'est_total_pnl': total_pnl, 'est_total_pct': total_pct, 'total_mv': new_total,
       'tracks': dict(tracks), 'med_exposure': round(med, 2),
       'med_pct': round(med / new_total * 100, 2), 'detail': detail}
json.dump(out, open(os.path.join(HIST, 'portfolio_close_' + TODAY.replace('-', '') + '.json'), 'w',
                    encoding='utf-8'), ensure_ascii=False, indent=1)

print('按0/暂缺项:', missing)
print(f'\n组合 {total_pct:+.2f}% ({total_pnl:+,.2f} 元)  总资产 {new_total:,.2f} (基准 {BASE_TOTAL:,.2f})')
print(f'医药敞口 {out["med_pct"]:.2f}%')
print('\n赛道:')
for k, v in sorted(tracks.items(), key=lambda kv: -kv[1]['mv']):
    print(f"  {k:8s} mv={v['mv']:>11,.2f} pct={v['pct_of_total']:>6.2f}% day={v['day_pct']:+.3f}% pnl={v['pnl']:>+9,.2f}")
print('\n个券贡献（按 |pnl| 排序）:')
for d in sorted(detail, key=lambda y: -abs(y['est_pnl']))[:24]:
    print(f"  {d['track']:8s} {d['name'][:22]:22s} {d['code']:9s} {d['est_pct']:+.3f}% pnl={d['est_pnl']:>+9,.2f}  [{d['price_src']}]")
