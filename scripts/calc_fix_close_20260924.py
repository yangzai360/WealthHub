# -*- coding: utf-8 -*-
"""2026-09-24 收盘估值「净值补更修正」→ portfolio_close_20260924_fix.json

背景（9/25 盘前档发现）：
  base = portfolio_close_20260924.json
    ⚠️ 该文件 detail[].mv = 继承自 9/23_fix 的旧值（Σmv = 383,598.82，不可用）
       detail[].mv0 = 9/23 收盘市值（Σ = 383,039.01 ✓ = base_total）
       9/24 收盘市值 = detail[].mv0 + detail[].est_pnl（Σ = 378,183.23 ✓ = total_mv）
  三处当时不可得的净值，本档已出库：
    ① 000369 广发全球医疗A   9/23 净值 2.565（−0.62%）—— 9/24 盘后档记「T+2 未出库→计0」
    ② 016280 广发全球医疗C   9/23 净值 2.521（−0.67%）—— 同上
    ③ 002708 大摩健康产业A   9/24 净值 2.001（−3.80%）—— 9/24 盘后档用「板块基准×弹性1.35」估算 −3.2096%
  §3.105：QDII 券基准已含净值日须从基准行 price_src 解析 → 基准含 9/22，新净值日 9/23 > 9/22 → 计入
"""
import json, os, re

BASE = '/Users/jieyang/Documents/WealthHub'
HIST = os.path.join(BASE, 'data/processed/history')
TODAY = '2026-09-24'
BASE_TOTAL = 383039.00

base = json.load(open(os.path.join(HIST, 'portfolio_close_20260924.json'), encoding='utf-8'))

# 本档新到净值：(code, nav_date, nav, pct)
NEW_NAV = {
    '000369': ('2026-09-23', 2.565, -0.62),
    '016280': ('2026-09-23', 2.521, -0.67),
    '002708': ('2026-09-24', 2.001, -3.80),
}

# 9/24 当日盈亏的基准逐行 = detail.mv0（= 9/23 收盘市值口径）
base_v = [round(float(x['mv0']), 2) for x in base['detail']]
tot = round(sum(base_v), 2)
close_v = round(sum(float(x['mv0']) + float(x['est_pnl']) for x in base['detail']), 2)
assert abs(tot - BASE_TOTAL) < 1.5, f'基准还原失败 Σmv0={tot} vs 9/23 收盘 {BASE_TOTAL}'
assert abs(close_v - base['total_mv']) < 1.5, f'9/24 收盘还原失败 Σ(mv0+est_pnl)={close_v} vs {base["total_mv"]}'
print(f'✅ 基准还原校验通过：Σmv0 = {tot:,.2f}（= 9/23 收盘 {BASE_TOTAL:,.2f}）；'
      f'Σ(mv0+est_pnl) = {close_v:,.2f}（= 9/24 收盘 {base["total_mv"]:,.2f}）（{len(base_v)} 行）')

detail, applied = [], []
for i, x in enumerate(base['detail']):
    code6 = ''.join(c for c in str(x['code']) if c.isdigit())
    v0 = base_v[i]
    pct = float(x['est_pct'])
    src = x['price_src']
    if code6 in NEW_NAV:
        nd, nav, npct = NEW_NAV[code6]
        mbench = re.search(r'(\d{4}-\d{2}-\d{2})', str(x.get('price_src', '')))
        base_nd = mbench.group(1) if mbench else '—'
        assert nd > base_nd or code6 == '002708', f'{code6} 基准 {base_nd} 已含 {nd}'
        old = pct
        pct = npct
        src = (f"净值 {nd} ({nav}) 真实兑现"
               f"（原基准 {base_nd}）｜本档修正：{old:+.4f}% → {npct:+.4f}%")
        applied.append({'code': code6, 'name': x['name'], 'nav_date': nd, 'nav': nav,
                        'pct': npct, 'pct_before': old,
                        'delta_pnl': round(v0 * (npct - old) / 100, 2)})
    detail.append({**x, 'mv0': v0, 'est_pct': pct,
                   'est_pnl': round(v0 * pct / 100, 2),
                   'est_pnl_low': round(v0 * pct / 100, 2),
                   'price_src': src})

total_pnl = round(sum(d['est_pnl'] for d in detail), 2)
total_pct = round(total_pnl / BASE_TOTAL * 100, 4)
new_total = round(BASE_TOTAL + total_pnl, 2)

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

# 医药敞口与门槛（§3.98 方程）
med = round(tracks['A股医药']['mv'] + tracks['美股标普医药']['mv'], 2)
B = new_total - med
A_sh = tracks['A股医药']['mv']
threshold_all = round(((0.40 / 0.60) * B / med - 1) * 100, 2)
threshold_sh = round((((0.40 / 0.60) * B - (med - A_sh)) / A_sh - 1) * 100, 2)

# 主动基弹性复检（§3.100/§3.105）
BOARD_MED = base['board_med']
LEADER_MED = base['leader_med']
active_mult = {}
for c, nm in (('002708', '大摩健康产业A'), ('161616', '融通医疗保健'), ('000727', '融通健康产业')):
    rows = [d for d in detail if ''.join(ch for ch in str(d['code']) if ch.isdigit()) == c]
    if rows:
        active_mult[c] = {'name': nm, 'real_pct': rows[0]['est_pct'],
                          'mult_vs_board_med': round(rows[0]['est_pct'] / BOARD_MED, 3) if BOARD_MED else None,
                          'mult_vs_300med': round(rows[0]['est_pct'] / LEADER_MED, 3) if LEADER_MED else None,
                          'estimated': False}

delta_total = round(total_pnl - base['est_total_pnl'], 2)
out = {**{k: v for k, v in base.items() if k not in ('detail', 'tracks')},
       'as_of': '2026-09-24收盘(净值补更修正)',
       'est_total_pnl': total_pnl, 'est_total_pct': round(total_pct, 2),
       'est_total_pct_raw': total_pct,
       'est_total_pnl_low': total_pnl, 'est_total_pct_low_raw': total_pct,
       'total_mv': new_total, 'tracks': tracks,
       'med_exposure': med, 'med_pct': round(med / new_total * 100, 2),
       'threshold_all_med': threshold_all, 'threshold_a_sh_med': threshold_sh,
       'active_mult': active_mult, 'detail': detail,
       'nav_fix_applied': applied,
       'fix_note': (f"9/25 盘前档净值补更修正：Δ{delta_total:+,.2f} 元 "
                    f"（{base['est_total_pnl']:+,.2f} 元 → {total_pnl:+,.2f} 元）。"
                    "三处：000369/016280 补 9/23 真实净值（原「T+2 未出库→计0」）；"
                    "002708 补 9/24 真实净值 −3.80%（原弹性估算 −3.2096%）。"),
       'base_note': '基准=portfolio_close_20260924.json，detail.mv 为继承旧值不可用，'
                    '已按 §3.104 用 mv0+est_pnl 还原 9/24 收盘市值'}

json.dump(out, open(os.path.join(HIST, 'portfolio_close_' + TODAY.replace('-', '') + '_fix.json'),
                    'w', encoding='utf-8'), ensure_ascii=False, indent=1)

print(f'\n★ 9/24 收盘（修正后）: {total_pct:+.4f}% ({total_pnl:+,.2f} 元)  总资产 {new_total:,.2f}')
print(f'  修正前: {base["est_total_pct_raw"]:+.4f}% ({base["est_total_pnl"]:+,.2f} 元) / {base["total_mv"]:,.2f}')
print(f'  Δ = {delta_total:+,.2f} 元')
print('\n逐项修正:')
for a in applied:
    print(f"  {a['name'][:26]:26s} {a['code']} {a['nav_date']} nav={a['nav']}  "
          f"{a['pct_before']:+.4f}% → {a['pct']:+.4f}%  Δ={a['delta_pnl']:+,.2f} 元")
print(f'\n  医药敞口 {out["med_pct"]:.2f}%  门槛(全部医药) {threshold_all:+.2f}% / (仅A股医药) {threshold_sh:+.2f}%')
print(f'  BOARD_MED={BOARD_MED}  300医药={LEADER_MED}')
print('\n主动医药基弹性（全部真实净值）:')
for c, v in active_mult.items():
    print(f"  {c} {v['name'][:12]:12s} {v['real_pct']:+7.3f}%  ×BOARD_MED={v['mult_vs_board_med']}  ×300医药={v['mult_vs_300med']}")
print('\n赛道:')
for k, v in sorted(tracks.items(), key=lambda kv: -kv[1]['mv0']):
    print(f"  {k:10s} mv0={v['mv0']:>11,.2f} w={v['pct_of_total']:>6.2f}% day={v['day_pct']:+.3f}% pnl={v['pnl']:>+10,.2f}")
