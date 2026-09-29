# -*- coding: utf-8 -*-
"""2026-09-28 收盘估值「净值补更修正」→ portfolio_close_20260928_fix.json

背景（9/29 盘前档发现）：
  base = portfolio_close_20260928.json
    ⚠️ 该文件逐券还原式经机器判据选定为 `mv0_new + est_pnl`（§3.112a）
       Σmv0 = 383,039.01（= 9/23 收盘，为修正日前一收盘口径，非本档基准）
       Σmv0_new = 377,630.13（= 9/24 修正后收盘 = base_total 377,630.12 ✓ 本档基准口径）
       Σ(mv0_new + est_pnl) = 375,523.98（= total_mv 375,523.97 ✓）

本档新到真实净值（9/28 盘后至 9/29 盘前出库）：
  ① 002708 大摩(摩根士丹利)健康产业混合A  9/28 净值 1.995（−0.30%）
     —— 9/28 盘后档用「同侪法」估算 −1.1149%（peer_avg −0.855% × 中位弹性 1.304）→ 高估跌幅 0.8149pct
  ② 001180 广发医药卫生ETF联接A        9/28 净值 0.7965（−0.04%）
     —— 9/28 盘后档按跟踪指数 000933 中证医药（+0.26%）代理 → 偏差 0.30pct
  ③ 002742 泓德裕祥债券A              9/28 净值 1.2632（−0.01%）
     —— 9/28 盘后档记「计 0」（持仓仅 9.40 元，量级可忽略，但为口径完整仍修正）
  ④ 000369 / 016280 广发全球医疗A/C    9/24 净值 2.572 / 2.528（+0.27% / +0.28%）
     —— 9/28 盘后档基准净值日 = 2026-09-23，新净值日 9/24 > 9/23 → 按 §3.105 计入
        该 9/24 净值即为「跨中秋休市」的第 1 个待兑现交易日（对应 US 9/24 会话）

§3.105：QDII 券「基准已含净值日」须逐券从基准行 price_src 解析，不得用固定日期常量比较。
"""
import json, os, re

BASE = '/Users/jieyang/Documents/WealthHub'
HIST = os.path.join(BASE, 'data/processed/history')
TODAY = '2026-09-28'
BASE_TOTAL = 377630.12

base = json.load(open(os.path.join(HIST, 'portfolio_close_20260928.json'), encoding='utf-8'))

# 本档新到净值：(code, nav_date, nav, pct, 说明)
NEW_NAV = {
    '002708': ('2026-09-28', 1.995, -0.30),
    '001180': ('2026-09-28', 0.7965, -0.04),
    '002742': ('2026-09-28', 1.2632, -0.01),
    '000369': ('2026-09-24', 2.572, 0.27),
    '016280': ('2026-09-24', 2.528, 0.28),
}

# 逐行基准 = mv0_new（= 9/24 修正后收盘市值，已由 §3.112a 机器判据验证）
base_v = [round(float(x['mv0_new']), 2) for x in base['detail']]
tot = round(sum(base_v), 2)
close_v = round(sum(float(x['mv0_new']) + float(x['est_pnl']) for x in base['detail']), 2)
assert abs(tot - BASE_TOTAL) < 1.5, f'基准还原失败 Σmv0_new={tot} vs 9/24 修正收盘 {BASE_TOTAL}'
assert abs(close_v - base['total_mv']) < 1.5, f'9/28 收盘还原失败 Σ(mv0_new+est_pnl)={close_v} vs {base["total_mv"]}'
print(f'✅ 基准还原校验通过：Σmv0_new = {tot:,.2f}（= 9/24 修正后收盘 {BASE_TOTAL:,.2f}）；'
      f'Σ(mv0_new+est_pnl) = {close_v:,.2f}（= 9/28 收盘 {base["total_mv"]:,.2f}）（{len(base_v)} 行）')

def parse_base_nd(src):
    """§3.105: 从基准行 price_src 解析「基准已含的净值日」
    优先级：① 「最新 M/D」/「最新 ISO」（未出库类）② 「基准净值日 ISO」③ 首个 ISO 日期
    ⚠️ 不得直接取首个 M/D —— 未出库类 src 的首个 M/D 是「参考日期」而非净值日
    """
    s = str(src)
    m = re.search(r'最新\s*(20\d{2}-\d{2}-\d{2}|\d{1,2}/\d{1,2})', s)
    if m:
        t = m.group(1)
        if '-' in t:
            return t
        a, b = t.split('/')
        return f'2026-{int(a):02d}-{int(b):02d}'
    m = re.search(r'基准净值日\s*(20\d{2}-\d{2}-\d{2})', s)
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
        assert base_nd == '—' or base_nd in ('2026-09-23', '2026-09-24'), f'{code6} 基准日异常 {base_nd}'
        old = pct
        pct = npct
        src = (f"净值 {nd} ({nav}) 真实兑现"
               f"（原基准 {base_nd}）｜本档修正：{old:+.4f}% → {npct:+.4f}%")
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

# 医药敞口与门槛（§3.98 方程）
med = round(tracks['A股医药']['mv'] + tracks['美股标普医药']['mv'], 2)
B = new_total - med
A_sh = tracks['A股医药']['mv']
threshold_all = round(((0.40 / 0.60) * B / med - 1) * 100, 2)
threshold_sh = round((((0.40 / 0.60) * B - (med - A_sh)) / A_sh - 1) * 100, 2)

delta_total = round(total_pnl - base['est_total_pnl'], 2)
out = {**{k: v for k, v in base.items() if k not in ('detail', 'tracks')},
       'as_of': '2026-09-28收盘(净值补更修正)',
       'est_total_pnl': total_pnl, 'est_total_pct': round(total_pct, 2),
       'est_total_pct_raw': total_pct,
       'est_total_pnl_best': total_pnl, 'est_total_pnl_worst': total_pnl,
       'est_total_pct_best_raw': total_pct, 'est_total_pct_worst_raw': total_pct,
       'total_mv': new_total, 'tracks': tracks,
       'med_exposure': med, 'med_pct': round(med / new_total * 100, 2),
       'threshold_all_med': threshold_all, 'threshold_a_sh_med': threshold_sh,
       'detail': detail,
       'nav_fix_applied': applied,
       'fix_note': (f"9/29 盘前档净值补更修正：Δ{delta_total:+,.2f} 元 "
                    f"（{base['est_total_pnl']:+,.2f} 元 → {total_pnl:+,.2f} 元）。"
                    "四处：002708 补 9/28 真实净值 −0.30%（原同侪法估算 −1.1149%，高估跌幅 0.8149pct）；"
                    "001180 补 9/28 真实净值 −0.04%（原按 000933 代理 +0.26%）；"
                    "002742 补 9/28 真实净值 −0.01%（原记 0）；"
                    "000369/016280 补 9/24 真实净值 +0.27%/+0.28%（原「基准已含 9/23 → 计 0」）。"),
       'base_note': '基准=portfolio_close_20260928.json，逐券基准行取 mv0_new（9/24 修正后收盘口径，'
                    '§3.112a 机器判据），非 mv0（= 9/23 收盘）'}
json.dump(out, open(os.path.join(HIST, 'portfolio_close_' + TODAY.replace('-', '') + '_fix.json'),
                    'w', encoding='utf-8'), ensure_ascii=False, indent=1)

print(f'\n★ 9/28 收盘（修正后）: {total_pct:+.4f}% ({total_pnl:+,.2f} 元)  总资产 {new_total:,.2f}')
print(f'  修正前: {base["est_total_pct_raw"]:+.4f}% ({base["est_total_pnl"]:+,.2f} 元) / {base["total_mv"]:,.2f}')
print(f'  Δ = {delta_total:+,.2f} 元')
print('\n逐项修正:')
for a in applied:
    print(f"  {a['name'][:26]:26s} {a['code']} {a['nav_date']} nav={a['nav']}  "
          f"{a['pct_before']:+.4f}% → {a['pct']:+.4f}%  Δ={a['delta_pnl']:+,.2f} 元")
print(f'\n  医药敞口 {out["med_pct"]:.2f}%（{med:,.2f} 元）  门槛(全部医药) {threshold_all:+.2f}% / (仅A股医药) {threshold_sh:+.2f}%')
print('\n赛道:')
for k, v in sorted(tracks.items(), key=lambda kv: -kv[1]['mv']):
    print(f"  {k:10s} mv={v['mv']:>11,.2f} w={v['pct_of_total']:>6.2f}% day={v['day_pct']:+.3f}% pnl={v['pnl']:>+10,.2f}")
