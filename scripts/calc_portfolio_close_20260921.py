# -*- coding: utf-8 -*-
"""2026-09-21 盘后：组合收盘估算（链式法，§3.79/§3.85/§3.88 口径）
base = portfolio_preopen_20260921.json 的 detail（= 9/18 收盘值：场内 9/18 收盘、场外 A股类 9/18 净值、QDII 9/17 净值）
BASE_TOTAL = 378,405.26（9/18 盘后归档链式值，含 §3.94 净值补更修正）
day_pct 逐券 = 最新可得价 / base 隐含价 - 1
  · 场内 = 9/21 收盘价
  · 场外已出 9/21 净值（13 只）→ 真实值
  · QDII/LOF（000369/016280/164906）→ 9/18 净值（T+1 真实兑现，对应美股 9/18 收盘）
  · 场外 A股类 9/21 净值未出（7 只）→ 按赛道代理 × 弹性估算并显式标注（下界口径 = 按 0）
输出：portfolio_close_20260921.json（含 tracks 的 mv0/mv，§3.96）
"""
import json, os, sys
from collections import defaultdict

BASE = '/Users/jieyang/Documents/WealthHub'
HIST = os.path.join(BASE, 'data/processed/history')
TODAY = '2026-09-21'
BASE_TOTAL = 378405.26
QDII = ('000369', '016280', '164906')

base = json.load(open(os.path.join(HIST, 'portfolio_preopen_20260921.json'), encoding='utf-8'))
cur = json.load(open(os.path.join(HIST, 'close_' + TODAY.replace('-', '') + '.json'), encoding='utf-8'))

PX = {x['code'].replace('sh', '').replace('sz', ''): x['close'] for x in cur['etf']}
for x in cur['stocks']:
    PX[x['code'].replace('sh', '').replace('sz', '')] = x['close']

NAV = {}
for n in cur['fund_navs']:
    if n['nav_date'] < '2026-09-14':
        continue
    if n['code'] not in NAV or n['nav_date'] > NAV[n['code']][0]:
        NAV[n['code']] = (n['nav_date'], n['nav'])

# ---- 赛道代理与弹性（用于 9/21 净值未出的场外 A股类基金）----
# 主口径：以「同赛道当日已出净值的被动指数基均值」为锚（比板块指数更贴近净值口径），
#         乘以该主动基在历史「强势上行日」相对被动基的经验倍数（近 22 个交易日实测，见下）
BOARD_MED = round((3.04 + 2.63 + 2.35 + 3.31) / 4, 4)   # 中证医药/中证医疗/医疗ETF/医药ETF广发 均值 = +2.8325%
PASSIVE_MED = round((2.46 + 2.98 + 2.67) / 3, 4)        # 9/21 已出被动基均值：012323 +2.46% / 001180 +2.98% / 001551 +2.67% = +2.7033%
# 经验倍数取「强势上行日均值」与「近23个交易日全样本中位」的折中（强势上行日样本仅 n=2，单独使用易高估）：
#   002708: 强上行日均值 1.89 / 全样本中位 1.39 → 折中 1.64
#   161616: 强上行日均值 1.48 / 全样本中位 1.09 → 折中 1.29
#   000727: 强上行日均值 0.80 / 全样本中位 0.82 → 折中 0.81
PROXY = {                                                # code -> (benchmark_pct, elasticity, label)
    '002708': (PASSIVE_MED, 1.64, '同赛道被动基均值 +2.70% ×1.64（强上行日/全样本中位折中）'),
    '161616': (PASSIVE_MED, 1.29, '同赛道被动基均值 +2.70% ×1.29（强上行日/全样本中位折中）'),
    '000727': (PASSIVE_MED, 0.81, '同赛道被动基均值 +2.70% ×0.81（强上行日/全样本中位折中）'),
    '000248': (0.88, 0.95, '中证消费 +0.88% ×0.95（历史跟踪比）'),
    '110020': (0.71, 0.97, '沪深300 +0.71% ×0.97（历史跟踪比）'),
    '000051': (0.71, 0.97, '沪深300 +0.71% ×0.97（历史跟踪比）'),
    '002742': (0.00, 1.00, '债券型，与股指无关→按 0.00%'),
}

detail, missing, proxy_used = [], [], []
for x in base['detail']:
    code6 = ''.join(c for c in x['code'] if c.isdigit())
    sh = float(x['shares']) if x['shares'] else 0.0
    mv0 = float(x['mv'])
    pct0 = 0.0   # 下界口径（缺失按 0）
    if code6 == '' or sh == 0:
        pct, src = 0.0, '现金'
        pct_low = 0.0
    elif code6 in PX:
        pct = round((PX[code6] / (mv0 / sh) - 1) * 100, 4)
        src = f'场内收盘 {PX[code6]}'
        pct_low = pct
    elif code6 in NAV:
        nd, nav = NAV[code6]
        raw = round((nav / (mv0 / sh) - 1) * 100, 4)
        if nd == TODAY:
            pct, src = raw, f'净值 9/21 ({nav})'
            pct_low = pct
        elif code6 in QDII:
            pct, src = raw, f'QDII/LOF T+1 净值 {nd} ({nav})'
            pct_low = pct
        else:
            bench, k, lab = PROXY.get(code6, (0.0, 0.0, '无代理规则→按0'))
            pct = round(bench * k, 4)
            pct_low = 0.0
            src = f'净值未更新({nd})→代理估算 {pct:+.2f}%｜{lab}'
            missing.append((code6, x['name'], nd))
            proxy_used.append((code6, x['name'], x['track'], mv0, pct))
    else:
        pct, src = 0.0, '数据暂缺→按0'
        pct_low = 0.0
        missing.append((code6, x['name'], None))
    detail.append({**x, 'est_pct': pct, 'est_pnl': round(mv0 * pct / 100, 2),
                   'est_pnl_low': round(mv0 * pct_low / 100, 2), 'price_src': src})

total_pnl = round(sum(d['est_pnl'] for d in detail), 2)
total_pnl_low = round(sum(d['est_pnl_low'] for d in detail), 2)
total_pct = round(total_pnl / BASE_TOTAL * 100, 2)
total_pct_low = round(total_pnl_low / BASE_TOTAL * 100, 2)
new_total = round(BASE_TOTAL + total_pnl, 2)

tracks = defaultdict(lambda: {'mv0': 0.0, 'mv': 0.0, 'pnl': 0.0, 'pnl_low': 0.0})
for d in detail:
    t = tracks[d['track']]
    t['mv0'] += d['mv']
    t['mv'] += d['mv'] + d['est_pnl']
    t['pnl'] += d['est_pnl']
    t['pnl_low'] += d['est_pnl_low']
for k, v in tracks.items():
    for f in ('mv0', 'mv', 'pnl', 'pnl_low'):
        v[f] = round(v[f], 2)
    v['pct_of_total'] = round(v['mv'] / new_total * 100, 2)
    v['day_pct'] = round(v['pnl'] / v['mv0'] * 100, 3) if v['mv0'] else 0.0
    v['day_pct_low'] = round(v['pnl_low'] / v['mv0'] * 100, 3) if v['mv0'] else 0.0

med = sum(v['mv'] for k, v in tracks.items() if k in ('A股医药', '美股标普医药'))
out = {'date': TODAY, 'as_of': '2026-09-21收盘', 'base_total': BASE_TOTAL,
       'est_total_pnl': total_pnl, 'est_total_pct': total_pct,
       'est_total_pnl_low': total_pnl_low, 'est_total_pct_low': total_pct_low,
       'total_mv': new_total, 'tracks': dict(tracks), 'med_exposure': round(med, 2),
       'med_pct': round(med / new_total * 100, 2), 'detail': detail,
       'proxy_used': [{'code': c, 'name': n, 'track': t, 'mv0': m, 'est_pct': p}
                      for c, n, t, m, p in proxy_used],
       'note': '场外 A股类 7 只 9/21 净值 20:00 时点未出库 → 按赛道代理×弹性估算；下界口径按 0；待 9/22 盘前档用真实净值兜底修正'}

json.dump(out, open(os.path.join(HIST, 'portfolio_close_' + TODAY.replace('-', '') + '.json'), 'w',
                    encoding='utf-8'), ensure_ascii=False, indent=1)

print('未出净值（代理估算）:', [(m[1], m[2]) for m in missing])
print(f'\n★ 主口径 组合 {total_pct:+.2f}% ({total_pnl:+,.2f} 元)  总资产 {new_total:,.2f} (基准 {BASE_TOTAL:,.2f})')
print(f'  下界口径(缺失按0) {total_pct_low:+.2f}% ({total_pnl_low:+,.2f} 元)  区间宽度 {total_pct-total_pct_low:.2f}pct')
print(f'  医药敞口 {out["med_pct"]:.2f}%')
print('\n赛道（mv0=估算前 / mv=估算后）:')
for k, v in sorted(tracks.items(), key=lambda kv: -kv[1]['mv0']):
    print(f"  {k:8s} mv0={v['mv0']:>11,.2f} w={v['pct_of_total']:>6.2f}% day={v['day_pct']:+.3f}% (low {v['day_pct_low']:+.3f}%) pnl={v['pnl']:>+9,.2f} ({v['pnl_low']:>+9,.2f})")
print('\n个券贡献（按 |pnl| 排序）:')
for d in sorted(detail, key=lambda y: -abs(y['est_pnl']))[:26]:
    print(f"  {d['track']:8s} {d['name'][:22]:22s} {d['code']:9s} {d['est_pct']:+.3f}% pnl={d['est_pnl']:>+9,.2f}  [{d['price_src']}]")

if any('@' in str(v) for v in [total_pct]):
    sys.exit(1)
