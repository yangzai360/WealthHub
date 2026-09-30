# -*- coding: utf-8 -*-
"""2026-09-29 收盘估值「净值补更修正」→ portfolio_close_20260929_fix.json

背景（9/30 盘前档发现）：
  base = portfolio_close_20260929.json（9/29 盘后档产出，正常交易日）
    ⚠️ 逐券还原式经机器判据选定为 `mv0_new + est_pnl`（§3.112a）
       Σ(mv0_new + est_pnl) 应为 total_mv = 376,574.96 元

本档新到真实净值（9/29 20:00 后 → 9/30 08:00 前出库，共 3 只）：
  ① 161616 融通医疗保健行业混合A/B  9/29 净值 1.795（−0.33%）
     —— 9/29 盘后档用「同侪锚定法」估算 +0.1180%（锚 002708 真实 +0.15% × k1.29/k1.64）
        → 方向反了，高估 +0.4512pct（估算 +0.1180% vs 真实 −0.3332%）
  ② 000727 融通健康产业灵活配置A/B  9/29 净值 2.505（−0.08%）
     —— 9/29 盘后档同侪锚定法估算 +0.0741% → 高估 +0.1539pct
  ③ 002742 泓德裕祥债券A           9/29 净值 1.2643（+0.09%）
     —— 9/29 盘后档记「计 0」（基准已含 9/28；持仓仅 9.40 元）

§3.105：逐券「基准已含净值日」须从基准行 price_src 解析，不得用固定日期常量比较。
§3.112a：修正件必须同步重算 tracks[].pnl 并过双硬守卫。
"""
import json, os, re

BASE = '/Users/jieyang/Documents/WealthHub'
HIST = os.path.join(BASE, 'data/processed/history')
TODAY = '2026-09-29'

base = json.load(open(os.path.join(HIST, 'portfolio_close_20260929.json'), encoding='utf-8'))
# ⚠️ 基准 = base['base_total']（= 9/28 修正后收盘），**不是** base['total_mv']（= 9/29 收盘）
#    否则会把当日 P&L 重复计入（本档首跑踩坑：new_total 多算 689.65 元，双守卫拦截）
BASE_TOTAL = float(base['base_total'])

# 本档新到真实净值：(code, nav_date, nav, 真实 pct, 说明)
NEW_NAV = {
    '161616': ('2026-09-29', 1.795, -0.3332),
    '000727': ('2026-09-29', 2.505, -0.0798),
    '002742': ('2026-09-29', 1.2643, 0.0871),
}

# 逐行基准 = mv0_new（§3.112a 机器判据已验证为 mv0_new+pnl）
base_v = [round(float(x['mv0_new']), 2) for x in base['detail']]
tot = round(sum(base_v), 2)
close_v = round(sum(float(x['mv0_new']) + float(x['est_pnl']) for x in base['detail']), 2)
assert abs(close_v - base['total_mv']) < 1.5, \
    f'9/29 收盘还原失败 Σ(mv0_new+est_pnl)={close_v} vs {base["total_mv"]}'
print(f'✅ 逐券还原式校验通过（规则 = mv0_new+pnl，§3.112a）：'
      f'Σ(mv0_new+est_pnl) = {close_v:,.2f}（= 9/29 收盘 {base["total_mv"]:,.2f}）（{len(base_v)} 行）')
print(f'   并列：Σmv0 = {tot:,.2f}（= 9/28 修正后收盘，非本档基准口径）')


def parse_base_nd(src):
    """§3.105: 从基准行 price_src 解析「基准已含的净值日」"""
    s = str(src)
    m = re.search(r'最新\s*(20\d{2}-\d{2}-\d{2}|\d{1,2}/\d{1,2})', s)
    if m:
        t = m.group(1)
        if '-' in t:
            return t
        a, b = t.split('/')
        return f'2026-{int(a):02d}-{int(b):02d}'
    m = re.search(r'净值(?:日)?\s*(20\d{2}-\d{2}-\d{2})', s)
    if m:
        return m.group(1)
    m = re.search(r'基准\s*(20\d{2}-\d{2}-\d{2})', s)
    if m:
        return m.group(1)
    m = re.search(r'(20\d{2}-\d{2}-\d{2})', s)
    if m:
        return m.group(1)
    return '—'


detail, applied = [], []
for i, x in enumerate(base['detail']):
    code6 = ''.join(c for c in str(x['code']) if c.isdigit())
    v0 = base_v[i]
    pct = float(x['est_pct'])
    src = x['price_src']
    if code6 in NEW_NAV:
        nd, nav, npct = NEW_NAV[code6]
        base_nd = parse_base_nd(src)
        assert base_nd == '—' or nd > base_nd, f'{code6} 基准已含 {nd}（基准日 {base_nd}）'
        old = pct
        pct = npct
        src = (f"净值 {nd} ({nav}) 真实兑现（原基准 {base_nd}）"
               f"｜本档修正：{old:+.4f}% → {npct:+.4f}%")
        applied.append({'code': code6, 'name': x['name'], 'nav_date': nd, 'nav': nav,
                        'pct': npct, 'pct_before': old,
                        'delta_pnl': round(v0 * (npct - old) / 100, 2)})
    detail.append({**x, 'mv0_new': v0, 'est_pct': pct,
                   'est_pnl': round(v0 * pct / 100, 2),
                   'est_pnl_best': round(v0 * pct / 100, 2),
                   'est_pnl_worst': round(v0 * pct / 100, 2),
                   'price_src': src})

total_pnl = round(sum(d['est_pnl'] for d in detail), 2)
total_pct = round(total_pnl / BASE_TOTAL * 100, 4)
new_total = round(BASE_TOTAL + total_pnl, 2)

tracks = {}
for d in detail:
    t = tracks.setdefault(d['track'], {'mv0': 0.0, 'mv': 0.0, 'pnl': 0.0})
    t['mv0'] += d['mv0_new']
    t['mv'] += d['mv0_new'] + d['est_pnl']
    t['pnl'] += d['est_pnl']
for k, v in tracks.items():
    for f in ('mv0', 'mv', 'pnl'):
        v[f] = round(v[f], 2)
    v['pct_of_total'] = round(v['mv'] / new_total * 100, 2)
    v['day_pct'] = round(v['pnl'] / v['mv0'] * 100, 3) if v['mv0'] else 0.0

# 双硬守卫（§3.107 / §3.109 / §3.112a）
sum_mv = round(sum(v['mv'] for v in tracks.values()), 2)
sum_pnl = round(sum(v['pnl'] for v in tracks.values()), 2)
assert abs(sum_mv - new_total) < 1.5, f'Σtracks.mv={sum_mv} vs total_mv={new_total}'
assert abs(sum_pnl - total_pnl) < 1.5, f'Σtracks.pnl={sum_pnl} vs est_total_pnl={total_pnl}'
print(f'✅ 双硬守卫通过：Σtracks.mv = {sum_mv:,.2f} ↔ total_mv {new_total:,.2f}；'
      f'Σtracks.pnl = {sum_pnl:,.2f} ↔ est_total_pnl {total_pnl:,.2f}')

# 逐赛道偏差复验（§3.112a：detail 还原式 × tracks）
dev = {}
for tname in tracks:
    r = round(sum(float(d['mv0_new']) + float(d['est_pnl'])
                  for d in detail if d['track'] == tname), 2)
    dev[tname] = round(r - tracks[tname]['mv'], 2)
maxdev = max(abs(v) for v in dev.values())
assert maxdev < 1.5, f'逐赛道还原偏差超限 {dev}'
print(f'✅ 逐赛道还原偏差全部 < 1.5 元：max = {maxdev:.2f} 元')

# 医药敞口与门槛（§3.98 方程）
med = round(tracks['A股医药']['mv'] + tracks['美股标普医药']['mv'], 2)
B = new_total - med
A_sh = tracks['A股医药']['mv']
threshold_all = round(((0.40 / 0.60) * B / med - 1) * 100, 2)
threshold_sh = round((((0.40 / 0.60) * B - (med - A_sh)) / A_sh - 1) * 100, 2)

delta_total = round(total_pnl - base['est_total_pnl'], 2)
out = {**{k: v for k, v in base.items() if k not in ('detail', 'tracks')},
       'as_of': '2026-09-29收盘(净值补更修正)',
       'est_total_pnl': total_pnl, 'est_total_pct': round(total_pct, 2),
       'est_total_pct_raw': total_pct,
       'est_total_pnl_best': total_pnl, 'est_total_pnl_worst': total_pnl,
       'est_total_pct_best_raw': total_pct, 'est_total_pct_worst_raw': total_pct,
       'total_mv': new_total, 'tracks': tracks,
       'med_exposure': med, 'med_pct': round(med / new_total * 100, 2),
       'threshold_all_med': threshold_all, 'threshold_a_sh_med': threshold_sh,
       'detail': detail,
       'nav_fix_applied': applied,
       'detail_restore_rule': 'mv0_new+pnl',
       'detail_restore_dev': dev,
       'detail_restore_total': close_v,
       'fix_note': (f"9/30 盘前档净值补更修正：Δ{delta_total:+,.2f} 元 "
                    f"（{base['est_total_pnl']:+,.2f} 元 → {total_pnl:+,.2f} 元）。"
                    "三处：161616 补 9/29 真实净值 −0.33%（原同侪锚定法估算 +0.1180%，"
                    "高估 +0.4512pct，**估算方向与真实相反**）；"
                    "000727 补 9/29 真实净值 −0.08%（原同侪锚定法估算 +0.0741%）；"
                    "002742 补 9/29 真实净值 +0.09%（原「基准已含 9/28 → 计 0」）。"),
       'base_note': '基准=portfolio_close_20260929.json，逐券基准行取 mv0_new（9/28 修正后收盘口径，'
                    '§3.112a 机器判据），非 mv0'}
json.dump(out, open(os.path.join(HIST, 'portfolio_close_' + TODAY.replace('-', '') + '_fix.json'),
                    'w', encoding='utf-8'), ensure_ascii=False, indent=1)

print(f'\n★ 9/29 收盘（修正后）: {total_pct:+.4f}% ({total_pnl:+,.2f} 元)  总资产 {new_total:,.2f}')
print(f'  修正前: {base["est_total_pct_raw"]:+.4f}% ({base["est_total_pnl"]:+,.2f} 元) / {base["total_mv"]:,.2f}')
print(f'  Δ = {delta_total:+,.2f} 元')
print('\n逐项修正:')
for a in applied:
    print(f"  {a['name'][:26]:26s} {a['code']} {a['nav_date']} nav={a['nav']}  "
          f"{a['pct_before']:+.4f}% → {a['pct']:+.4f}%  Δ={a['delta_pnl']:+,.2f} 元")
print(f'\n  医药敞口 {out["med_pct"]:.2f}%（{med:,.2f} 元）  '
      f'门槛(全部医药) {threshold_all:+.2f}% / (仅A股医药) {threshold_sh:+.2f}%')
print('\n赛道:')
for k, v in sorted(tracks.items(), key=lambda kv: -kv[1]['mv']):
    print(f"  {k:10s} mv={v['mv']:>11,.2f} w={v['pct_of_total']:>6.2f}% "
          f"day={v['day_pct']:+.3f}% pnl={v['pnl']:>+10,.2f}")
