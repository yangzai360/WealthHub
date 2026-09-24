# -*- coding: utf-8 -*-
"""2026-09-24 盘后：组合收盘估算（链式法，§3.79/§3.85/§3.97/§3.100/§3.102/§3.104 口径）

base = portfolio_close_20260923_fix.json（9/23 收盘真实净值修正口径）
  ⚠️ §3.104：该文件 detail[].mv 是 mv0（=9/22 收盘市值）口径，不是 9/23 收盘市值
     → 9/23 收盘市值 = mv + est_pnl；base_total = total_mv = 383,039.00 元
逐券当日涨跌 = 最新可得价 / (mv+est_pnl)/shares − 1
  · 场内（ETF/个股）= 9/24 收盘价（hq 直连）
  · 场外已出 9/24 真实净值 19 只（含 161616/000727/001180/001551/012323 等 A股医药全员）
  · 002708 大摩健康产业 9/24 净值未出 → 按「板块基准 × 历史分方向弹性」估算（§3.100 规则）
  · 000369/016280（QDII）最新仍为 9/22 净值 = 基准已含 → 计 0（T+2 未出库）
  · 164906（LOF）9/23 净值 0.8917 本档出库 → 真实兑现 −1.25%
输出：portfolio_close_20260924.json
"""
import json, os, re

BASE = '/Users/jieyang/Documents/WealthHub'
HIST = os.path.join(BASE, 'data/processed/history')
TODAY = '2026-09-24'
BASE_TOTAL = 383039.00          # 9/23 收盘修正口径（total_mv）

base = json.load(open(os.path.join(HIST, 'portfolio_close_20260923_fix.json'), encoding='utf-8'))
cur = json.load(open(os.path.join(HIST, 'close_' + TODAY.replace('-', '') + '.json'), encoding='utf-8'))

# ---- 9/23 收盘市值（还原，§3.104）----
# ⚠️ 同一 code 可能有多行（A/C 份额或不同渠道），必须按行序一一对应，不得用 (code,name,track) 作键
base_val = [round(float(x['mv']) + float(x['est_pnl']), 2) for x in base['detail']]
tot = round(sum(base_val), 2)
assert abs(tot - BASE_TOTAL) < 1.5, f'基准还原失败 {tot} vs {BASE_TOTAL}'
print(f'✅ 基准还原校验通过：Σ(mv+est_pnl) = {tot:,.2f} vs total_mv {BASE_TOTAL:,.2f}（{len(base_val)} 行）')

PX = {x['code'].replace('sh', '').replace('sz', ''): x['close'] for x in cur['etf']}
for x in cur['stocks']:
    PX[x['code'].replace('sh', '').replace('sz', '')] = x['close']

NAV = {}
for n in cur['fund_navs']:
    if n['nav_date'] < '2026-09-14':
        continue
    if n['code'] not in NAV or n['nav_date'] > NAV[n['code']][0]:
        NAV[n['code']] = (n['nav_date'], n['nav'])

# ---- 板块/指数代理（9/24 收盘）----
BRD = {x['code']: x['pct'] for x in cur['boards']}
ETF_PCT = {x['code']: x['pct'] for x in cur['etf']}
IDX = {x['code']: x['pct'] for x in cur['indices']}
BOARD_MED = round((BRD['sh000933'] + BRD['sz399989'] + ETF_PCT['sh512170'] + ETF_PCT['sz159938']) / 4, 4)
LEADER_MED = BRD['sh000913']                                   # 300医药
LAG_MED = round((BRD['sh000933'] + BRD['sz399989'] + ETF_PCT['sh512170']) / 3, 4)

# ---- 仅 002708 需弹性估算（§3.100：下跌日按 [1.0, 实测最大倍数] 区间 + 中央档）----
# 实测 6 样本（9/15-9/22）vs 三口径板块中位：median 1.42 / 下跌日 1.13~1.18 / 全样本 1.13~4.91
MULT = {'central': 1.35, 'low': 1.15, 'high': 1.70}
EST_2708 = {k: round(BOARD_MED * v, 4) for k, v in MULT.items()}

detail, missing, proxy_used, qdii_applied = [], [], [], []
for i, x in enumerate(base['detail']):
    code6 = ''.join(c for c in str(x['code']) if c.isdigit())
    sh = float(x['shares']) if x['shares'] else 0.0
    v0 = base_val[i]                                           # 9/23 收盘市值（逐行对应）
    pct_low = pct = 0.0
    if code6 == '' or sh == 0:
        pct, pct_low, src = 0.0, 0.0, '现金'
    elif code6 in PX:
        imp = v0 / sh
        pct = pct_low = round((PX[code6] / imp - 1) * 100, 4)
        src = f'场内收盘 {PX[code6]}'
    elif code6 == '002708':
        nd = NAV.get(code6, ('-', 0))[0]
        pct, pct_low = EST_2708['central'], EST_2708['high']    # 下界取绝对值更大的 high
        src = (f'9/24 净值未出(最新 {nd}) → 板块基准 {BOARD_MED:+.4f}% × 弹性'
               f'[×{MULT["low"]} ~ ×{MULT["high"]}] 中央 ×{MULT["central"]}')
        missing.append((code6, x['name'], None, '主动基净值未出→弹性估算'))
    elif code6 in NAV:
        nd, nav = NAV[code6]
        imp = v0 / sh
        # 基准行 src 中标注的净值日 = 基准已含的净值（§3.104 同源：mv 为 mv0 口径时，
        # 基准 est_pct 已把该日净值兑现进 est_pnl，故只有「更新的净值日」才能再计入）
        mbench = re.search(r'(\d{4}-\d{2}-\d{2})', str(x.get('price_src', '')))
        base_nd = mbench.group(1) if mbench else None
        if nd == TODAY:
            pct = pct_low = round((nav / imp - 1) * 100, 4)
            src = f'净值 9/24 ({nav})'
        elif base_nd and nd > base_nd:
            pct = pct_low = round((nav / imp - 1) * 100, 4)
            src = f'LOF/QDII T+1 净值 {nd} ({nav}) 真实兑现（基准为 {base_nd}）'
            qdii_applied.append((code6, x['name'], nd, nav, pct))
        else:
            src = f'净值未更新(nd={nd}，基准 {base_nd}) → 计 0（基准已含）'
            missing.append((code6, x['name'], nd, 'QDII T+2 未出库→计0'))
    else:
        pct, pct_low, src = 0.0, 0.0, '数据暂缺→按0'
        missing.append((code6, x['name'], None, '数据暂缺'))
    detail.append({**x, 'mv0': v0, 'est_pct': pct, 'est_pnl': round(v0 * pct / 100, 2),
                   'est_pnl_low': round(v0 * pct_low / 100, 2), 'price_src': src})

total_pnl = round(sum(d['est_pnl'] for d in detail), 2)
total_pct = round(total_pnl / BASE_TOTAL * 100, 4)
new_total = round(BASE_TOTAL + total_pnl, 2)
pnl_low = round(sum(d['est_pnl_low'] for d in detail), 2)

tracks = {}
for d in detail:
    t = tracks.setdefault(d['track'], {'mv0': 0.0, 'mv': 0.0, 'pnl': 0.0})
    t['mv0'] += d['mv0']
    t['mv'] += d['mv0'] + d['est_pnl']
    t['pnl'] += d['est_pnl']
for k, v in tracks.items():
    for f in ('mv0', 'mv', 'pnl'):
        v[f] = round(v[f], 2)
    v['pct_of_total'] = round(v['mv'] / new_total * 100, 2)
    v['day_pct'] = round(v['pnl'] / v['mv0'] * 100, 3) if v['mv0'] else 0.0

# ---- 主动医药基真实倍数（本档 161616/000727 为真实净值）----
active_mult = {}
for c, nm in (('002708', '大摩健康产业A'), ('161616', '融通医疗保健'), ('000727', '融通健康产业')):
    rows = [d for d in detail if ''.join(ch for ch in str(d['code']) if ch.isdigit()) == c]
    if rows:
        active_mult[c] = {'name': nm, 'real_pct': rows[0]['est_pct'],
                          'mult_vs_board_med': round(rows[0]['est_pct'] / BOARD_MED, 3) if BOARD_MED else None,
                          'mult_vs_300med': round(rows[0]['est_pct'] / LEADER_MED, 3) if LEADER_MED else None,
                          'estimated': c == '002708'}

# 被动联接类（真实净值）vs 所跟踪指数偏差（§3.103 检验）
proxy_check = {}
for c, idx, lab in (('001180', BRD['sh000933'], '中证医药'), ('012323', BRD['sz399989'], '中证医疗'),
                    ('001551', 'n/a', '中证医药100'), ('000968', 'n/a', '养老产业')):
    rows = [d for d in detail if ''.join(ch for ch in str(d['code']) if ch.isdigit()) == c]
    if rows and isinstance(idx, float):
        proxy_check[c] = {'real': rows[0]['est_pct'], 'index': idx, 'label': lab,
                          'dev': round(rows[0]['est_pct'] - idx, 4)}

med = round(tracks['A股医药']['mv'] + tracks['美股标普医药']['mv'], 2)
A = med
B = new_total - med
threshold_all = round(((0.40 / 0.60) * B / A - 1) * 100, 2)
A_sh = tracks['A股医药']['mv']
threshold_sh = round((((0.40 / 0.60) * B - (med - A_sh)) / A_sh - 1) * 100, 2)

out = {'date': TODAY, 'as_of': '2026-09-24收盘', 'base_total': BASE_TOTAL,
       'est_total_pnl': total_pnl, 'est_total_pct': round(total_pct, 2),
       'est_total_pct_raw': total_pct, 'est_total_pnl_low': pnl_low,
       'est_total_pct_low_raw': round(pnl_low / BASE_TOTAL * 100, 4),
       'total_mv': new_total, 'tracks': tracks,
       'med_exposure': med, 'med_pct': round(med / new_total * 100, 2),
       'threshold_all_med': threshold_all, 'threshold_a_sh_med': threshold_sh,
       'board_med': BOARD_MED, 'leader_med': LEADER_MED, 'lag_med': LAG_MED,
       'active_mult': active_mult, 'proxy_check': proxy_check,
       'est_2708': EST_2708, 'mult_2708': MULT,
       'qdii_applied': [{'code': c, 'name': n, 'nav_date': d, 'nav': v, 'pct': p} for c, n, d, v, p in qdii_applied],
       'detail': detail,
       'proxy_used': [{'code': c, 'name': n, 'nd': nd, 'reason': r} for c, n, nd, r in missing],
       'note': ('9/24：19 只场外基金出 9/24 真实净值（A股医药主动/被动全员真实）；'
                '002708 净值未出→板块基准×弹性估算；000369/016280 T+2 未出库→计0；'
                '164906 出 9/23 净值→真实兑现 −1.25%'),
       'base_note': '基准=portfolio_close_20260923_fix.json，detail.mv 为 mv0 口径，已按 §3.104 用 mv+est_pnl 还原'}

json.dump(out, open(os.path.join(HIST, 'portfolio_close_' + TODAY.replace('-', '') + '.json'), 'w',
                    encoding='utf-8'), ensure_ascii=False, indent=1)

print('未出净值/需估算:', [(m[0], m[1], m[3]) for m in missing])
print(f'\n★ 组合 {total_pct:+.4f}% ({total_pnl:+,.2f} 元)  总资产 {new_total:,.2f} (基准 {BASE_TOTAL:,.2f})')
print(f'  敏感性下界（002708 取 ×{MULT["high"]}）: {round(pnl_low/BASE_TOTAL*100,4):+.4f}% ({pnl_low:+,.2f} 元)')
print(f'  BOARD_MED={BOARD_MED}  300医药={LEADER_MED}  LAG_MED={LAG_MED}')
print(f'  002708 估算 {EST_2708["central"]:+.2f}%（区间 {EST_2708["low"]:+.2f}% ~ {EST_2708["high"]:+.2f}%）')
print(f'  医药敞口 {out["med_pct"]:.2f}%  门槛(全部医药) {threshold_all:+.2f}% / (仅A股医药) {threshold_sh:+.2f}%')
print('\n主动医药基当日幅度（vs 板块代理）:')
for c, v in active_mult.items():
    print(f"  {c} {v['name'][:10]:10s} {v['real_pct']:+.3f}%  ×BOARD_MED={v['mult_vs_board_med']}  ×300医药={v['mult_vs_300med']}"
          f"  {'[估算]' if v['estimated'] else '[真实]'}")
print('\n被动联接类偏差检验（§3.103）:', proxy_check)
print('\n赛道:')
for k, v in sorted(tracks.items(), key=lambda kv: -kv[1]['mv0']):
    print(f"  {k:10s} mv0={v['mv0']:>11,.2f} w={v['pct_of_total']:>6.2f}% day={v['day_pct']:+.3f}% pnl={v['pnl']:>+10,.2f}")
print('\n个券贡献（按 |pnl| 排序前 26）:')
for d in sorted(detail, key=lambda y: -abs(y['est_pnl']))[:26]:
    print(f"  {d['track']:10s} {d['name'][:22]:22s} {str(d['code']):9s} {d['est_pct']:+8.3f}% pnl={d['est_pnl']:>+10,.2f}  [{d['price_src']}]")
