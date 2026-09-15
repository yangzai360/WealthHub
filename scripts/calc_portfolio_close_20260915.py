# -*- coding: utf-8 -*-
"""2026-09-15 盘后：组合收盘估算（链式法，§3.79 口径）
base = 9/15 盘前 detail（= 9/14 收盘值，合计 375,444.27）
BASE_TOTAL = 375,841.62（9/14 盘后归档链式值，当日涨跌基准）
day_pct 逐券 = 最新可得价 / base 隐含价 - 1（场内=9/15收盘；场外=最新净值；QDII=补更累计）"""
import json, os
from collections import defaultdict

BASE = '/Users/jieyang/Documents/WealthHub'
HIST = os.path.join(BASE, 'data/processed/history')
TODAY = '2026-09-15'
BASE_TOTAL = 375841.62

base = json.load(open(os.path.join(HIST, 'portfolio_preopen_20260915.json'), encoding='utf-8'))
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

# QDII/LOF 补更（净值日 T 反映美股 T 日收盘，T+1 在 A股次日盘后可得）
CATCHUP = {'000369': (2.5200, 2.5560, '9/11→9/14'),
           '016280': (2.4770, 2.5130, '9/11→9/14'),
           '164906': (0.8850, 0.8833, '9/11→9/14')}

detail = []
missing = []
for x in base['detail']:
    code6 = ''.join(c for c in x['code'] if c.isdigit())
    sh = float(x['shares']) if x['shares'] else 0.0
    mv0 = float(x['mv'])
    if code6 == '' or sh == 0:
        pct, src = 0.0, '现金'
    elif code6 in CATCHUP:
        b, n, tag = CATCHUP[code6]
        pct, src = round((n / b - 1) * 100, 4), f'QDII补更 {tag} ({b}→{n})'
    elif code6 in PX:
        pct, src = round((PX[code6] / (mv0 / sh) - 1) * 100, 4), f'场内收盘 {PX[code6]}'
    elif code6 in NAV:
        nd, nav = NAV[code6]
        pct, src = round((nav / (mv0 / sh) - 1) * 100, 4), f'净值 {nd} ({nav})'
    else:
        pct, src = 0.0, '数据暂缺→按0'
        missing.append((code6, x['name']))
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
    v['day_pct'] = round(v['pnl'] / v['mv'] * 100, 3)

med = sum(v['mv'] for k, v in tracks.items() if k in ('A股医药', '美股标普医药'))
out = {'date': TODAY, 'as_of': '2026-09-15收盘', 'base_total': BASE_TOTAL,
       'est_total_pnl': total_pnl, 'est_total_pct': total_pct, 'total_mv': new_total,
       'tracks': dict(tracks), 'med_exposure': round(med, 2),
       'med_pct': round(med / new_total * 100, 2), 'detail': detail}
json.dump(out, open(os.path.join(HIST, 'portfolio_close_' + TODAY.replace('-', '') + '.json'), 'w',
                    encoding='utf-8'), ensure_ascii=False, indent=1)

print(f'缺失: {missing}')
print(f'\n组合 {total_pct:+.2f}% ({total_pnl:+,.2f} 元)  总资产 {new_total:,.2f} (基准 {BASE_TOTAL:,.2f})')
print(f'医药敞口 {out["med_pct"]:.2f}%')
print('\n赛道:')
for k, v in sorted(tracks.items(), key=lambda kv: -kv[1]['mv']):
    print(f"  {k:8s} mv={v['mv']:>11,.2f} pct={v['pct_of_total']:>6.2f}% day={v['day_pct']:+.3f}% pnl={v['pnl']:>+9,.2f}")
print('\n个券贡献（按 |pnl| 排序）:')
for d in sorted(detail, key=lambda y: -abs(y['est_pnl']))[:20]:
    print(f"  {d['track']:8s} {d['name'][:22]:22s} {d['code']:9s} {d['est_pct']:+.3f}% pnl={d['est_pnl']:>+9,.2f}  [{d['price_src']}]")
