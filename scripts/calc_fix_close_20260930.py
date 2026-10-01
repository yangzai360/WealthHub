# -*- coding: utf-8 -*-
"""2026-09-30 收盘估值「净值补更修正」→ portfolio_close_20260930_fix.json

背景（10/1 盘前档发现 —— 国庆长假首日、A股+港股均休市）：
  base = portfolio_close_20260930.json（9/30 盘后档产出，节前最后一个 A股交易日）
    ⚠️ 逐券还原式经机器判据选定为 `mv0_new + est_pnl`（§3.112a）

本档新到真实净值（9/30 20:15 后 → 10/1 08:00 前出库，共 7 只 / 8 行）：
  ① 002708 大摩健康产业混合A  9/30 净值 2.067（+3.4535%）—— 原「板块代理 × k1.64 = +4.8298%」高估 1.3763pct
  ② 161616 融通医疗保健行业A/B 9/30 净值 1.851（+3.1198%）—— 原「板块代理 × k1.29 = +3.7990%」高估 0.6792pct
  ③ 000727 融通健康产业A/B     9/30 净值 2.539（+1.3573%）—— 原「板块代理 × k0.81 = +2.3855%」高估 1.0282pct
  ④ 001180 广发医药卫生ETF联接A 9/30 净值 0.8198（+2.8220%）—— 原「中证医药指数代理 +2.87%」高估 0.0480pct
  ⑤ 110020 易方达沪深300联接A  9/30 净值 1.7943（+0.2907%）—— 原「沪深300 指数代理 +0.29%」≈无偏
  ⑥ 002742 泓德裕祥债券A       9/30 净值 1.2665（+0.1740%）—— 原「基准已含 9/28 → 计 0」
  ⑦ 004752 广发中证传媒ETF联接A 9/30 净值 0.7933（−0.4018%）—— 原「基准已含 9/29 → 计 0」

⚠️ 口径选择（本档明确声明，勿被下游误读）：
  QDII 000369/016280 的 **9/29 净值已于本档出库**（2.573 / −0.4642%、2.53 / −0.4330%），
  但本档 **不将其计入 9/30 收盘** —— 理由：① 9/30 档产物已登记「10/8 复市后一次性回填」口径；
  ② QDII「净值日 ↔ 美股行情日」对应关系存在歧义（§3.113c 记 D↔D，§3.114e 实测系数 0.62，
  本档反算 000369 9/29 净值/ IYH 9/29 = 1.29）→ 强行入账会把一个美股 9/29 交易日的损益记到 9/30 行。
  → 保持「净值未推进（基准已含至 9/28）」、pnl = 0，并在 pending 中量化披露该已可观测金额。

§3.105：逐券「基准已含净值日」须从基准行 price_src 解析，不得用固定日期常量比较。
§3.115a：`_fix` 起点必须取 base['base_total']（前一收盘），不是 base['total_mv']。
§3.109 / §3.112a：修正件必须同步重算 tracks[].pnl 并过双硬守卫 + 逐赛道还原偏差。
§3.117a：「挂账/未量化」类字段按当档「净值日是否推进」重算，禁止整段继承。
"""
import json, os, re

BASE = '/Users/jieyang/Documents/WealthHub'
HIST = os.path.join(BASE, 'data/processed/history')
TODAY = '2026-09-30'

base = json.load(open(os.path.join(HIST, 'portfolio_close_20260930.json'), encoding='utf-8'))
# ⚠️ 基准 = base['base_total']（= 9/29 修正后收盘 376,491.53），**不是** base['total_mv']（= 9/30 收盘）
BASE_TOTAL = float(base['base_total'])

# 本档新到真实净值：(code, nav_date, nav, 真实 pct)
NEW_NAV = {
    '002708': ('2026-09-30', 2.067, 3.4535),
    '161616': ('2026-09-30', 1.851, 3.1198),
    '000727': ('2026-09-30', 2.539, 1.3573),
    '001180': ('2026-09-30', 0.8198, 2.8220),
    '110020': ('2026-09-30', 1.7943, 0.2907),
    '002742': ('2026-09-30', 1.2665, 0.1740),
    '004752': ('2026-09-30', 0.7933, -0.4018),
}
# 保持挂账口径的券（净值日未相对 9/30 基准推进）
KEEP_PENDING = {'000369', '016280'}

base_v = [round(float(x['mv0_new']), 2) for x in base['detail']]
tot = round(sum(base_v), 2)
close_v = round(sum(float(x['mv0_new']) + float(x['est_pnl']) for x in base['detail']), 2)
assert abs(close_v - base['total_mv']) < 1.5, \
    f'9/30 收盘还原失败 Σ(mv0_new+est_pnl)={close_v} vs {base["total_mv"]}'
print(f'✅ 逐券还原式校验通过（规则 = mv0_new+pnl，§3.112a）：'
      f'Σ(mv0_new+est_pnl) = {close_v:,.2f}（= 9/30 收盘 {base["total_mv"]:,.2f}）（{len(base_v)} 行）')
print(f'   并列：Σmv0_new = {tot:,.2f}（= 9/29 修正后收盘，非本档起点）')


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

# 港股三层拆解（结构性字段随当档重算，§3.108 条款 23）
hk_split = dict(base.get('hk_split') or {})
hk_split = {k: round(float(v), 2) for k, v in hk_split.items()}
hk_total = round(sum(hk_split.values()), 2)
hk_total_pct = round(hk_total / new_total * 100, 2)

# proxy_used 重算（§3.117a：已取得真实净值的券必须从代理清单移除）
proxy_used_new = [p for p in (base.get('proxy_used') or [])
                  if ''.join(c for c in str(p.get('code', '')) if c.isdigit()) in KEEP_PENDING]
active_mult = {k: {**v, 'estimated': False, 'real_pct': NEW_NAV[k][2],
                   'note': '10/1 盘前档已取得 9/30 真实净值，代理估算闭环'}
               for k, v in (base.get('active_mult') or {}).items() if k in NEW_NAV}

# pending 重算（§3.117a：不得整段继承）
pend = dict(base.get('pending') or {})
qdii_old = float(pend.get('qdii_pnl_mid') or 0)
obs_amounts = []  # 已可观测但本档不入账
for code, nd, nav, pct in [('000369', '2026-09-29', 2.573, -0.4642),
                           ('016280', '2026-09-29', 2.53, -0.4330)]:
    for d in detail:
        c6 = ''.join(ch for ch in str(d['code']) if ch.isdigit())
        if c6 == code:
            obs_amounts.append({'code': code, 'nav_date': nd, 'nav': nav, 'pct': pct,
                                'mv0_new': d['mv0_new'],
                                'amount': round(d['mv0_new'] * pct / 100, 2)})
obs_total = round(sum(a['amount'] for a in obs_amounts), 2)
pend.update({
    'as_of': '2026-09-30',
    'settle_date': '2026-10-08',
    'qdii_observable_now': obs_amounts,
    'qdii_observable_amount': obs_total,
    'qdii_decision': ('QDII 000369 / 016280 的 9/29 净值已于 10/1 盘前档出库（−0.4642% / −0.4330%，'
                      '基准净值日 9/28），但**本档不将其计入 9/30 收盘**（保持「净值未推进」、pnl=0）：'
                      '① 9/30 档产物已登记 10/8 一次性回填口径；② QDII「净值日↔美股行情日」对应关系存在歧义'
                      '（本档反算 000369 9/29 净值 ÷ IYH 9/29 = 1.29，与 §3.114e 实测 0.62 冲突）。'
                      f'→ 该 {obs_total:+,.2f} 元 仍留在挂账口径内，由 10/8 档以「基准净值日 = 9/28」为起点回填。'),
    'unquantified': {
        'code': None, 'mv': 0.0, 'stale': True,
        'note': ('9/30 档的 164906 残留字段已在 9/30 盘后档作废（§3.117a）；10/1 档复核：'
                 '164906 最新净值日 = 9/29，已真实兑现计入「恒生科技」赛道，**无挂账项**。'
                 '本档未量化项清空，pending_codes ∩ applied_codes = ∅（断言见脚本）。'),
    },
    'unquantified_fixed_at': '2026-10-01 盘前档',
})
applied_codes = {a['code'] for a in (base.get('qdii_applied') or [])}
assert not (KEEP_PENDING & applied_codes), f'挂账集合与已兑现集合有交集：{KEEP_PENDING & applied_codes}'
print(f'✅ pending 断言通过：挂账 {sorted(KEEP_PENDING)} ∩ 已兑现 {sorted(applied_codes)} = ∅')

delta_total = round(total_pnl - base['est_total_pnl'], 2)
out = {**base,
       'as_of': '2026-09-30 收盘（10/1 盘前档 · 真实净值补更修正）',
       'est_total_pnl': total_pnl, 'est_total_pct': round(total_pct, 2),
       'est_total_pct_raw': total_pct,
       'est_total_pnl_best': total_pnl, 'est_total_pnl_worst': total_pnl,
       'est_total_pct_best_raw': total_pct, 'est_total_pct_worst_raw': total_pct,
       'total_mv': new_total, 'tracks': tracks,
       'med_exposure': med, 'med_pct': round(med / new_total * 100, 2),
       'threshold_all_med': threshold_all, 'threshold_a_sh_med': threshold_sh,
       'hk_split': hk_split, 'hk_total': hk_total, 'hk_total_pct': hk_total_pct,
       'detail': detail,
       'nav_fix_applied': applied,
       'proxy_used': proxy_used_new,
       'active_mult': active_mult,
       'pending': pend,
       'detail_restore_rule': 'mv0_new+pnl',
       'detail_restore_dev': dev,
       'detail_restore_total': close_v,
       'fix_note': (f"10/1 盘前档（国庆长假首日）净值补更修正：Δ{delta_total:+,.2f} 元 "
                    f"（{base['est_total_pnl']:+,.2f} 元 → {total_pnl:+,.2f} 元）。"
                    "7 只 / 8 行取得 9/30 真实净值（002708 +3.4535% / 161616 +3.1198% / 000727 +1.3573% / "
                    "001180 +2.8220% / 110020 +0.2907% / 002742 +0.1740% / 004752 −0.4018%）；"
                    "**三只主动医药基的「板块代理 × k 弹性」估算全部高估**（002708 高估 1.3763pct、"
                    "161616 高估 0.6792pct、000727 高估 1.0282pct）；被动联接 001180 指数代理偏差仅 −0.0480pct"
                    "（§3.103 口径再次成立）。QDII 000369/016280 的 9/29 净值虽已出库，"
                    "但按挂账口径留待 10/8 回填（见 pending.qdii_decision）。"),
       'base_note': ('基准 = portfolio_close_20260930.json，逐券基准行取 mv0_new（9/29 修正后收盘口径，'
                     '§3.112a 机器判据），起点取 base_total = 376,491.53 元（§3.115a）。')}
json.dump(out, open(os.path.join(HIST, 'portfolio_close_' + TODAY.replace('-', '') + '_fix.json'),
                    'w', encoding='utf-8'), ensure_ascii=False, indent=1)

print(f'\n★ 9/30 收盘（修正后）: {total_pct:+.4f}% ({total_pnl:+,.2f} 元)  总资产 {new_total:,.2f}')
print(f'  修正前: {base["est_total_pct_raw"]:+.4f}% ({base["est_total_pnl"]:+,.2f} 元) / {base["total_mv"]:,.2f}')
print(f'  Δ = {delta_total:+,.2f} 元')
print('\n逐项修正:')
for a in applied:
    print(f"  {a['name'][:26]:26s} {a['code']} {a['nav_date']} nav={a['nav']}  "
          f"{a['pct_before']:+.4f}% → {a['pct']:+.4f}%  Δ={a['delta_pnl']:+,.2f} 元")
print(f'\n  医药敞口 {out["med_pct"]:.2f}%（{med:,.2f} 元）  '
      f'门槛(全部医药) {threshold_all:+.2f}% / (仅A股医药) {threshold_sh:+.2f}%')
print(f'  港联系 {hk_total:,.2f} 元 = {hk_total_pct:.2f}%（{hk_split}）')
print(f'  QDII 已可观测但本档不入账：{obs_total:+,.2f} 元 {obs_amounts}')
print('\n赛道:')
for k, v in sorted(tracks.items(), key=lambda kv: -kv[1]['mv']):
    print(f"  {k:10s} mv={v['mv']:>11,.2f} w={v['pct_of_total']:>6.2f}% "
          f"day={v['day_pct']:+.3f}% pnl={v['pnl']:>+10,.2f}")
