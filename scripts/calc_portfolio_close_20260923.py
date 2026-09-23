# -*- coding: utf-8 -*-
"""2026-09-23 盘后：组合收盘估算（链式法，§3.79/§3.85/§3.97/§3.99/§3.100/§3.101 口径）
base = portfolio_close_20260922_fix.json（9/22 收盘真实净值修正口径，总资产 383,598.81 元；其 detail.mv 已为 9/22 收盘市值）
day_pct 逐券 = 最新可得价 / base 隐含价 - 1
  · 场内 10 行 = 9/23 收盘价
  · 场外已出 9/23 净值 12 只 → 真实值（含主动医药基 002708/161616/000727，本档全部真实）
  · QDII/LOF（000369/016280/164906）→ 9/22 净值（T+1 真实兑现）
  · 其余 8 只（联接类）9/23 净值未出 → 被动指数联接按所跟踪指数直接代理（§3.98 偏差 ≤0.01pct）
输出：portfolio_close_20260923.json
"""
import json, os

BASE = '/Users/jieyang/Documents/WealthHub'
HIST = os.path.join(BASE, 'data/processed/history')
TODAY = '2026-09-23'
BASE_TOTAL = 383598.81
QDII = ('000369', '016280', '164906')

base = json.load(open(os.path.join(HIST, 'portfolio_close_20260922_fix.json'), encoding='utf-8'))
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

# ---- 板块代理（9/23 收盘）----
BRD = {x['code']: x['pct'] for x in cur['boards']}
ETF_PCT = {x['code']: x['pct'] for x in cur['etf']}
IDX = {x['code']: x['pct'] for x in cur['indices']}
HK = {x['code']: x['pct'] for x in cur['hk']}
BOARD_MED = round((BRD['sh000933'] + BRD['sz399989'] + ETF_PCT['sh512170'] + ETF_PCT['sz159938']) / 4, 4)
LEADER_MED = BRD['sh000913']                     # 300医药
LAG_MED = round((BRD['sh000933'] + BRD['sz399989'] + ETF_PCT['sh512170']) / 3, 4)

# 未出 9/23 净值的被动联接基金 → 按所跟踪指数直接代理（§3.98）
PROXY = {
    '000968': (IDX['sh000932'], f'中证消费 {IDX["sh000932"]:+.2f}%'),
    '002742': (0.00, '债券型→按 0.00%'),
    '004752': (ETF_PCT['sh512980'], f'传媒ETF(512980) {ETF_PCT["sh512980"]:+.2f}%'),
    '001180': (BRD['sh000933'], f'中证医药 {BRD["sh000933"]:+.2f}%'),
    '000051': (IDX['sh000300'], f'沪深300 {IDX["sh000300"]:+.2f}%'),
    '000071': (ETF_PCT['sz159920'], f'恒生ETF(159920) {ETF_PCT["sz159920"]:+.2f}%'),
    '001469': (BRD['sh000934'], f'中证金融 {BRD["sh000934"]:+.2f}%'),
    '012323': (BRD['sz399989'], f'中证医疗 {BRD["sz399989"]:+.2f}%'),
}

detail, missing, proxy_used = [], [], []
for x in base['detail']:
    code6 = ''.join(c for c in x['code'] if c.isdigit())
    sh = float(x['shares']) if x['shares'] else 0.0
    mv0 = float(x['mv'])
    if code6 == '' or sh == 0:
        pct, src, pct_low = 0.0, '现金', 0.0
    elif code6 in PX:
        pct = round((PX[code6] / (mv0 / sh) - 1) * 100, 4)
        src = f'场内收盘 {PX[code6]}'
        pct_low = pct
    elif code6 in NAV:
        nd, nav = NAV[code6]
        raw = round((nav / (mv0 / sh) - 1) * 100, 4)
        if nd == TODAY:
            pct, src = raw, f'净值 9/23 ({nav})'
            pct_low = pct
        elif code6 in QDII:
            pct, src = raw, f'QDII/LOF T+1 净值 {nd} ({nav})'
            pct_low = pct
        else:
            bench, lab = PROXY.get(code6, (0.0, '无代理规则→按0'))
            pct = round(bench, 4)
            pct_low = pct
            src = f'净值未更新({nd})→指数代理 {pct:+.2f}%｜{lab}'
            missing.append((code6, x['name'], nd))
            proxy_used.append((code6, x['name'], x['track'], mv0, pct))
    else:
        pct, src, pct_low = 0.0, '数据暂缺→按0', 0.0
        missing.append((code6, x['name'], None))
    detail.append({**x, 'est_pct': pct, 'est_pnl': round(mv0 * pct / 100, 2),
                   'est_pnl_low': round(mv0 * pct_low / 100, 2), 'price_src': src})

total_pnl = round(sum(d['est_pnl'] for d in detail), 2)
total_pct = round(total_pnl / BASE_TOTAL * 100, 4)
new_total = round(BASE_TOTAL + total_pnl, 2)

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

# ---- 主动医药基弹性实际倍数（本档首次取得「板块上涨日」的真实净值，§3.98/§3.100 规则再修正）----
active_mult = {}
for c, nm in (('002708', '大摩健康产业A'), ('161616', '融通医疗保健'), ('000727', '融通健康产业')):
    if c in NAV:
        nav = NAV[c][1]
        mvs = [x for x in base['detail'] if ''.join(ch for ch in x['code'] if ch.isdigit()) == c]
        if mvs:
            imp = float(mvs[0]['mv']) / float(mvs[0]['shares'])
            real = (nav / imp - 1) * 100
            active_mult[c] = {'real_pct': round(real, 4),
                              'mult_vs_board_med': round(real / BOARD_MED, 3) if BOARD_MED else None,
                              'mult_vs_300med': round(real / LEADER_MED, 3) if LEADER_MED else None,
                              'mult_vs_lagmed': round(real / LAG_MED, 3) if LAG_MED else None}

med = sum(v['mv'] for k, v in tracks.items() if k in ('A股医药', '美股标普医药'))
A = med
B = new_total - med
threshold_all = round(((0.40 / 0.60) * B / A - 1) * 100, 2)
A_sh = tracks['A股医药']['mv']
threshold_sh = round((((0.40 / 0.60) * B - (med - A_sh)) / A_sh - 1) * 100, 2)

out = {'date': TODAY, 'as_of': '2026-09-23收盘', 'base_total': BASE_TOTAL,
       'est_total_pnl': total_pnl, 'est_total_pct': round(total_pct, 2),
       'est_total_pct_raw': total_pct,
       'total_mv': new_total, 'tracks': tracks,
       'med_exposure': round(med, 2), 'med_pct': round(med / new_total * 100, 2),
       'threshold_all_med': threshold_all, 'threshold_a_sh_med': threshold_sh,
       'board_med': BOARD_MED, 'leader_med': LEADER_MED, 'lag_med': LAG_MED,
       'active_mult': active_mult,
       'detail': detail,
       'proxy_used': [{'code': c, 'name': n, 'track': t, 'mv0': m, 'est_pct': p}
                      for c, n, t, m, p in proxy_used],
       'note': '本档主动医药基 002708/161616/000727 全部取得 9/23 真实净值（无代理估算）；仅 8 只被动联接基金 9/23 净值未出，按所跟踪指数直接代理'}

json.dump(out, open(os.path.join(HIST, 'portfolio_close_' + TODAY.replace('-', '') + '.json'), 'w',
                    encoding='utf-8'), ensure_ascii=False, indent=1)

print('未出净值（指数代理）:', [(m[0], m[1]) for m in missing])
print(f'\n★ 组合 {total_pct:+.4f}% ({total_pnl:+,.2f} 元)  总资产 {new_total:,.2f} (基准 {BASE_TOTAL:,.2f})')
print(f'  BOARD_MED={BOARD_MED}  300医药={LEADER_MED}  滞后三口径 LAG_MED={LAG_MED}')
print(f'  医药敞口 {out["med_pct"]:.2f}%  门槛(全部医药) {threshold_all:+.2f}% / (仅A股医药) {threshold_sh:+.2f}%')
print('\n主动医药基真实倍数（vs 板块代理）:')
for c, v in active_mult.items():
    print(f"  {c} 真实 {v['real_pct']:+.3f}%  ×BOARD_MED={v['mult_vs_board_med']}  ×300医药={v['mult_vs_300med']}  ×LAG_MED={v['mult_vs_lagmed']}")
print('\n赛道:')
for k, v in sorted(tracks.items(), key=lambda kv: -kv[1]['mv0']):
    print(f"  {k:10s} mv0={v['mv0']:>11,.2f} w={v['pct_of_total']:>6.2f}% day={v['day_pct']:+.3f}% pnl={v['pnl']:>+9,.2f}")
print('\n个券贡献（按 |pnl| 排序前 26）:')
for d in sorted(detail, key=lambda y: -abs(y['est_pnl']))[:26]:
    print(f"  {d['track']:10s} {d['name'][:22]:22s} {d['code']:9s} {d['est_pct']:+.3f}% pnl={d['est_pnl']:>+9,.2f}  [{d['price_src']}]")
