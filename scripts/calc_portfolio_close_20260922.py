# -*- coding: utf-8 -*-
"""2026-09-22 盘后：组合收盘估算（链式法，§3.79/§3.85/§3.97/§3.98/§3.99 口径）
base = portfolio_close_20260921_fix.json 的 detail（= 9/21 收盘修正口径，含净值补更）
BASE_TOTAL = 383,064.00（9/21 盘后链式修正值）
day_pct 逐券 = 最新可得价 / base 隐含价 - 1
  · 场内 = 9/22 收盘价
  · 场外已出 9/22 净值（18 只）→ 真实值
  · QDII/LOF（000369/016280/164906）→ 9/21 净值（T+1 真实兑现，对应美股 9/21 收盘）
  · 主动医药基 161616 / 000727 的 9/22 净值未出 → 按 全样本中位弹性 × 板块代理 估算（§3.99 D2 否定 → 弹性下修档）
输出：portfolio_close_20260922.json
"""
import json, os

BASE = '/Users/jieyang/Documents/WealthHub'
HIST = os.path.join(BASE, 'data/processed/history')
TODAY = '2026-09-22'
BASE_TOTAL = 383064.00
QDII = ('000369', '016280', '164906')

base = json.load(open(os.path.join(HIST, 'portfolio_close_20260921_fix.json'), encoding='utf-8'))
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

# ---- 板块代理（9/22 收盘）----
BRD = {x['code']: x['pct'] for x in cur['boards']}
ETF_PX = {x['code']: x['pct'] for x in cur['etf']}
BOARD_MED = round((BRD['sh000933'] + BRD['sz399989'] + ETF_PX['sh512170'] + ETF_PX['sz159938']) / 4, 4)
LEADER_MED = BRD['sh000913']
# 主动医药基弹性：§3.99 D2 延续日否定 → 下修至全样本中位档（§3.97 口径）
PROXY = {                                      # code -> (benchmark_pct, elasticity, label)
    '161616': (BOARD_MED, 1.09, f'板块代理 {BOARD_MED:+.3f}% ×1.09（§3.99 D2否定→全样本中位档）'),
    '000727': (BOARD_MED, 0.82, f'板块代理 {BOARD_MED:+.3f}% ×0.82（§3.99 D2否定→全样本中位档）'),
    '002708': (BOARD_MED, 1.39, f'板块代理 {BOARD_MED:+.3f}% ×1.39（§3.99 D2否定→全样本中位档）'),
    '002742': (0.00, 1.00, '债券型，与股指无关→按 0.00%'),
}

detail, missing, proxy_used = [], [], []
for x in base['detail']:
    code6 = ''.join(c for c in x['code'] if c.isdigit())
    sh = float(x['shares']) if x['shares'] else 0.0
    mv0 = float(x['mv'])
    pct_low = 0.0   # 下界口径（缺失按 0）
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
            pct, src = raw, f'净值 9/22 ({nav})'
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
total_pct = round(total_pnl / BASE_TOTAL * 100, 4)
total_pct_low = round(total_pnl_low / BASE_TOTAL * 100, 4)
new_total = round(BASE_TOTAL + total_pnl, 2)

tracks = {}
for d in detail:
    t = tracks.setdefault(d['track'], {'mv0': 0.0, 'mv': 0.0, 'pnl': 0.0, 'pnl_low': 0.0})
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

# ---- 弹性敏感性（§3.98）：主动医药基改口径的下界/上界 ----
low_tracks = {}
for d in detail:
    t = low_tracks.setdefault(d['track'], 0.0)
low_tracks = None
sens_low = sum(d['est_pnl_low'] for d in detail)

# 下界：主动医药基按 300医药 龙头口径（LEADER_MED × 弹性）
def active_pnl(bench_pct, elasticities):
    tot = 0.0
    for d in detail:
        c = ''.join(ch for ch in d['code'] if ch.isdigit())
        if c in elasticities:
            tot += d['mv'] * (bench_pct * elasticities[c]) / 100
    return tot

E = {'002708': 1.39, '161616': 1.09, '000727': 0.82}
base_active = active_pnl(BOARD_MED, E)
low_active = active_pnl(LEADER_MED, E)      # 龙头口径（300医药）
high_active = active_pnl(0.0, E)            # 主动基持平 0
sens_low = round(total_pnl - base_active + low_active, 2)
sens_high = round(total_pnl - base_active + high_active, 2)

med = sum(v['mv'] for k, v in tracks.items() if k in ('A股医药', '美股标普医药'))
A = med
B = new_total - med
threshold_all = round(((0.40 / 0.60) * B / A - 1) * 100, 2)
# 仅 A股医药 单独上攻：A_sh(1+r) + 美股不动 = 0.4/(0.6) * B
A_sh = tracks['A股医药']['mv']
threshold_sh = round((((0.40 / 0.60) * B - (med - A_sh)) / A_sh - 1) * 100, 2)

out = {'date': TODAY, 'as_of': '2026-09-22收盘', 'base_total': BASE_TOTAL,
       'est_total_pnl': total_pnl, 'est_total_pct': round(total_pct, 2),
       'est_total_pct_raw': total_pct,
       'est_total_pnl_low': total_pnl_low, 'est_total_pct_low': round(total_pct_low, 2),
       'sens_low': sens_low, 'sens_high': sens_high,
       'total_mv': new_total, 'tracks': tracks, 'med_exposure': round(med, 2),
       'med_pct': round(med / new_total * 100, 2),
       'threshold_all_med': threshold_all, 'threshold_a_sh_med': threshold_sh,
       'board_med': BOARD_MED, 'leader_med': LEADER_MED,
       'detail': detail,
       'proxy_used': [{'code': c, 'name': n, 'track': t, 'mv0': m, 'est_pct': p}
                      for c, n, t, m, p in proxy_used],
       'note': '主动医药基 161616/000727 的 9/22 净值 20:00 时点未出库 → 按板块代理×全样本中位弹性估算；下界口径按 0；待 9/23 盘前档用真实净值兜底修正'}

json.dump(out, open(os.path.join(HIST, 'portfolio_close_' + TODAY.replace('-', '') + '.json'), 'w',
                    encoding='utf-8'), ensure_ascii=False, indent=1)

print('未出净值（代理估算）:', [(m[1], m[2]) for m in missing])
print(f'\n★ 主口径 组合 {total_pct:+.4f}% ({total_pnl:+,.2f} 元)  总资产 {new_total:,.2f} (基准 {BASE_TOTAL:,.2f})')
print(f'  下界口径(缺失按0) {total_pct_low:+.4f}% ({total_pnl_low:+,.2f} 元)  区间宽度 {total_pct-total_pct_low:.2f}pct')
print(f'  弹性敏感性: 下界 {sens_low:+,.2f} 元 / 基准 {total_pnl:+,.2f} / 上界 {sens_high:+,.2f}')
print(f'  BOARD_MED={BOARD_MED}  300医药={LEADER_MED}')
print(f'  医药敞口 {out["med_pct"]:.2f}%  门槛(全部医药) {threshold_all:+.2f}% / (仅A股医药) {threshold_sh:+.2f}%')
print('\n赛道:')
for k, v in sorted(tracks.items(), key=lambda kv: -kv[1]['mv0']):
    print(f"  {k:8s} mv0={v['mv0']:>11,.2f} w={v['pct_of_total']:>6.2f}% day={v['day_pct']:+.3f}% (low {v['day_pct_low']:+.3f}%) pnl={v['pnl']:>+9,.2f} ({v['pnl_low']:>+9,.2f})")
print('\n个券贡献（按 |pnl| 排序前 26）:')
for d in sorted(detail, key=lambda y: -abs(y['est_pnl']))[:26]:
    print(f"  {d['track']:8s} {d['name'][:22]:22s} {d['code']:9s} {d['est_pct']:+.3f}% pnl={d['est_pnl']:>+9,.2f}  [{d['price_src']}]")
