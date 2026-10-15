# -*- coding: utf-8 -*-
"""fix_portfolio_close_20261014.py — 补正 2026-10-14 收盘产物（002708 净值迟滞到位）

背景（§3.140a / §3.146b / §3.105 / §3.139e）：
  10/14 20:00 盘后档首抓时 `002708`（大摩健康产业混合A，sean/jasy **双账户**）**10/14 净值尚未发布**
  （最新净值日仍为 10/13 = 基准净值日）→ 该券两行按「基准已含（净值日未推进）→ 计 0」处理，
  组合 10/14 当日损益被系统性低估。10/14 档产物 `note` 已显式登记「**已列入次档兜底补抓**」。
  本档（10/15 08:00 盘前）复抓 F10 确认 **10/14 净值 = 1.876（−2.24%，基准 10/13 = 1.919）已出库**
  → 按 §3.140a（跨档补正）执行 `_fix`，避免该跌幅被错误计入 10/15。
  ⚠️ 这是 §3.140a 的**第 3 例**（前两例：10/13 档 002708 −358.50 元、10/9 档 000051 +15.79 元），
     且为**同一券连续两档迟滞**（10/13、10/14）→ 该券属「净值出库晚于 20:00」的稳定特征，须逐档兜底。

硬守卫（§3.115a / §3.109 条款 26 / §3.112a / §3.146a）：
  ① `|Σ tracks.mv − total_mv| < 1.5`
  ② `|Σ tracks.pnl − est_total_pnl| < 1.5`
  ③ `_fix` 总量起点必须取 `base['base_total']`（= 前一收盘 374,389.47 元），**不得用 `base['total_mv']`**
  ④ 逐券还原式 `mv0_new + est_pnl` 逐赛道 dev < 1.5（机器判据，§3.112a）
  ⑤ `tracks[].pct_of_total` 一律由 `mv / total_mv` **现算**（§3.146a：修正件改 mv 后原权重必失真）
"""
import copy
import json
import os

ROOT = '/Users/jieyang/Documents/WealthHub'
HIST = os.path.join(ROOT, 'data/processed/history')
SRC = os.path.join(HIST, 'portfolio_close_20261014.json')
DST = os.path.join(HIST, 'portfolio_close_20261014_fix.json')
TODAY = '2026-10-15'
FIX_TARGET = '2026-10-14'

OLD_NAV = 1.919          # 10/13 净值（基准净值日）
NEW_NAV = 1.876          # 10/14 净值（本次补抓）
NEW_NAV_DATE = '2026-10-14'
OLD_NAV_DATE = '2026-10-13'
PCT = round((NEW_NAV / OLD_NAV - 1) * 100, 4)

base = json.load(open(SRC, encoding='utf-8'))
d = copy.deepcopy(base)

rows = [x for x in d['detail'] if str(x['code']).split('.')[0] == '002708']
assert len(rows) == 2, f'002708 应命中 2 行（双账户），实际 {len(rows)} 行'

print(f'002708 大摩健康产业混合A：{OLD_NAV}({OLD_NAV_DATE}) → {NEW_NAV}({NEW_NAV_DATE})  pct={PCT}%')
old_est_pnl = d['est_total_pnl']
old_total_mv = d['total_mv']
old_track_pnl = d['tracks']['A股医药']['pnl']
old_track_mv = d['tracks']['A股医药']['mv']
old_med_pct = d['med_pct']
old_thr_all = d['threshold_all_med']
old_thr_sh = d['threshold_a_sh_med']
old_weights = {k: v.get('pct_of_total') for k, v in d['tracks'].items()}

items, TOTAL_PNL = [], 0.0
for row in rows:
    v0 = round(float(row['mv0_new']), 2)
    # 份额口径优先取产物自带 `shares`（真相源），反算式仅作一致性交叉校验（§3.140a）
    shares = round(float(row['shares']), 2)
    shares_rev = round(v0 / OLD_NAV, 2)
    assert abs(shares * OLD_NAV - v0) < 1.5, f'shares 与 mv0_new 不自洽: {shares} × {OLD_NAV} vs {v0}'
    assert abs(shares - shares_rev) < 0.05, f'shares 与反算式偏离过大: {shares} vs {shares_rev}'
    new_mv = round(shares * NEW_NAV, 2)
    pnl = round(new_mv - v0, 2)
    TOTAL_PNL = round(TOTAL_PNL + pnl, 2)
    print(f'  {row["account"]:>20}  shares={shares}（反算 {shares_rev}）  mv0_new={v0:,.2f} 元  →  '
          f'new_mv={new_mv:,.2f} 元  est_pnl={pnl:+,.2f} 元（原 0 元）')
    row['price_src'] = (f'净值 10/14 ({NEW_NAV}，{PCT}%)，基准净值日 {OLD_NAV_DATE}'
                        '（§3.140a 补正：10/14 档 20:00 首抓时未出库 → 计 0，本档 08:00 复抓到位）')
    row['est_pct'] = PCT
    row['est_pnl'] = pnl
    row['est_pct_best'] = PCT
    row['est_pnl_best'] = pnl
    row['est_pct_worst'] = PCT
    row['est_pnl_worst'] = pnl
    row['est_pnl_low'] = pnl
    row['mv'] = new_mv                                   # 置为权威式 mv0_new + est_pnl（详见 detail_mv_policy）
    row['fix_applied'] = True
    items.append({'code': '002708', 'name': row['name'], 'account': row['account'], 'track': 'A股医药',
                  'shares': shares, 'base_nav': OLD_NAV, 'base_nav_date': OLD_NAV_DATE,
                  'new_nav': NEW_NAV, 'new_nav_date': NEW_NAV_DATE,
                  'est_pct': PCT, 'est_pnl_元': pnl, 'before_est_pnl_元': 0.0, 'mv0_new_元': v0})

# ---- 赛道行同步重算（§3.115a / §3.109 条款 26）
d['tracks']['A股医药']['pnl'] = round(old_track_pnl + TOTAL_PNL, 2)
d['tracks']['A股医药']['mv'] = round(old_track_mv + TOTAL_PNL, 2)

# ---- 总量修正（起点 = base_total 前一收盘）
d['est_total_pnl'] = round(old_est_pnl + TOTAL_PNL, 2)
d['total_mv'] = round(old_total_mv + TOTAL_PNL, 2)
d['est_total_pct_raw'] = round(d['est_total_pnl'] / d['base_total'] * 100, 4)
d['est_total_pct'] = round(d['est_total_pct_raw'], 2)
d['est_total_pnl_best'] = round(float(base.get('est_total_pnl_best', old_est_pnl)) + TOTAL_PNL, 2)
d['est_total_pnl_worst'] = round(float(base.get('est_total_pnl_worst', old_est_pnl)) + TOTAL_PNL, 2)
d['est_total_pnl_high'] = d['est_total_pnl_best']
d['est_total_pnl_low'] = d['est_total_pnl_worst']
d['band_note'] = (base.get('band_note', '') +
                  f' ｜§3.140a 补正后 best == worst == 点值（{d["est_total_pnl"]:,.2f} 元）：'
                  '002708 10/14 净值已出库，全部标的不再存在代理估算项。')

# ---- 医药敞口与门槛同步重算（§3.98 方程解法，与 calc_portfolio_close 同式）
med = round(d['tracks']['A股医药']['mv'] + d['tracks']['美股标普医药']['mv'], 2)
A, B = med, d['total_mv'] - med
A_sh = d['tracks']['A股医药']['mv']
d['med_exposure'] = med
d['med_pct'] = round(med / d['total_mv'] * 100, 2)
d['threshold_all_med'] = round(((0.40 / 0.60) * B / A - 1) * 100, 2)
d['threshold_a_sh_med'] = round((((0.40 / 0.60) * B - (med - A_sh)) / A_sh - 1) * 100, 2)

# ---- §3.146a：权重一律 mv/total_mv 现算（禁止沿用修正前分母派生值）
for t, v in d['tracks'].items():
    v['pct_of_total'] = round(v['mv'] / d['total_mv'] * 100, 2)
new_weights = {k: v['pct_of_total'] for k, v in d['tracks'].items()}

# ---- 硬守卫
sum_track_mv = round(sum(v['mv'] for v in d['tracks'].values()), 2)
sum_track_pnl = round(sum(v['pnl'] for v in d['tracks'].values()), 2)
dev_mv = round(sum_track_mv - d['total_mv'], 2)
dev_pnl = round(sum_track_pnl - d['est_total_pnl'], 2)
print(f'\n[守卫①] Σtracks.mv = {sum_track_mv:,.2f} 元  vs total_mv = {d["total_mv"]:,.2f} 元  → dev = {dev_mv}')
print(f'[守卫②] Σtracks.pnl = {sum_track_pnl:,.2f} 元  vs est_total_pnl = {d["est_total_pnl"]:,.2f} 元  → dev = {dev_pnl}')
assert abs(dev_mv) < 1.5, f'守卫①未通过：{dev_mv}'
assert abs(dev_pnl) < 1.5, f'守卫②未通过：{dev_pnl}'
print('  ✅ 双硬守卫通过')

# ---- 守卫④ 逐券还原式 mv0_new+est_pnl 逐赛道 dev
dev_restore = {}
for t in d['tracks']:
    s = round(sum(round(float(x['mv0_new']) + float(x['est_pnl']), 2)
                  for x in d['detail'] if x['track'] == t), 2)
    dev_restore[t] = round(s - d['tracks'][t]['mv'], 2)
print(f'[守卫④] 还原式 mv0_new+pnl 逐赛道 dev = {dev_restore}')
assert all(abs(v) < 1.5 for v in dev_restore.values()), f'守卫④未通过：{dev_restore}'
print('  ✅ 还原式守卫通过')

# ---- 起点守卫
assert abs(d['base_total'] - 374389.47) < 0.01, f'base_total 异常: {d["base_total"]}'
assert abs(d['base_total'] + d['est_total_pnl'] - d['total_mv']) < 1.5, '总量还原式不成立'
print(f"  ✅ 还原式 base_total({d['base_total']:,.2f} 元) + est_total_pnl({d['est_total_pnl']:+,.2f} 元) = total_mv({d['total_mv']:,.2f} 元)")

# ---- 补正元数据（§3.140a 基准修订四字段 + §3.146a 权重自证）
d['stale_weight_fields_in_fix'] = {
    'note': ('§3.146a：修正件改写 `tracks[].mv` / `total_mv` 后，原 `pct_of_total` 必然失真。'
             '本档**已同步现算**为 mv/total_mv，故『修正前 / 修正后』权重并列于 fix.delta.weights_pct；'
             '下游引用本件权重时无需再自行换算。'),
    'weights_before_pct': old_weights,
    'weights_after_pct': new_weights,
}
d['detail_mv_policy'] = {
    'note': ('§3.112a：`detail[].mv` 在原始产物中为「基准行原样继承的陈旧值」，与 `mv0_new+est_pnl` 不自洽，'
             '**禁止按字段名取数**；权威式恒为 `mv0_new + est_pnl`（守卫④已逐赛道验证 dev < 1.5）。'
             '本修正件对 002708 两行**直接写权威式值**，故该两行 `mv == mv0_new + est_pnl` 自洽；'
             '其余行沿用原始产物的继承值不变。'),
    'authoritative_expr': 'mv0_new + est_pnl',
    'rows_rewritten_to_authoritative': 2,
}
d['fix'] = {
    'fix_of': f'portfolio_close_{FIX_TARGET.replace("-", "")}.json',
    'fix_made_at': f'{TODAY} 08:00 盘前档（档型③ 正常交易日盘前）',
    'fix_reason': ('002708（大摩健康产业混合A，sean/jasy 双账户）10/14 净值在 10/14 档 20:00 首抓时尚未出库，'
                   '按「基准已含（净值日未推进）→ 计 0」处理致组合当日损益低估；'
                   f'本档 08:00 复抓 F10 确认 10/14 净值 1.876（{PCT}%）已出库 → 按 §3.140a / §3.105 执行 _fix 补正。'
                   '⚠️ 同一券连续两档（10/13 / 10/14）迟滞 → 已登记为稳定特征，须逐档兜底复抓。'),
    'base_revision': {
        'prev_file': 'portfolio_close_20261014.json',
        'prev_total_元': old_total_mv,
        'delta_元': TOTAL_PNL,
        'reason': '跨档补正：昨档缺失净值（002708 10/14）于本档到位，按 §3.140a 回填至事件日当日',
    },
    'fix_items': items,
    'before': {'est_total_pnl_元': old_est_pnl, 'est_total_pct': base['est_total_pct'],
               'total_mv_元': old_total_mv, 'A股医药_pnl_元': old_track_pnl, 'A股医药_mv_元': old_track_mv,
               'med_pct': old_med_pct, 'threshold_all_med': old_thr_all, 'threshold_a_sh_med': old_thr_sh},
    'after': {'est_total_pnl_元': d['est_total_pnl'], 'est_total_pct': d['est_total_pct'],
              'total_mv_元': d['total_mv'], 'A股医药_pnl_元': d['tracks']['A股医药']['pnl'],
              'A股医药_mv_元': d['tracks']['A股医药']['mv'],
              'med_pct': d['med_pct'], 'threshold_all_med': d['threshold_all_med'],
              'threshold_a_sh_med': d['threshold_a_sh_med']},
    'delta': {'est_total_pnl_元': TOTAL_PNL,
              'est_total_pct': round(d['est_total_pct'] - base['est_total_pct'], 4),
              'total_mv_元': round(d['total_mv'] - old_total_mv, 2),
              'weights_pct': {k: {'before': old_weights[k], 'after': new_weights[k],
                                  'delta': round(new_weights[k] - old_weights[k], 2)} for k in old_weights}},
    'guards': {'dev_sum_track_mv_vs_total_mv': dev_mv, 'dev_sum_track_pnl_vs_est_total_pnl': dev_pnl,
               'dev_restore_by_track': dev_restore,
               'restore_from': f"base_total（前一收盘 {d['base_total']:,.2f} 元），非 total_mv"},
    'restore_rule_used': base.get('restore_rule_used'),
    'detail_restore_rule': base.get('detail_restore_rule'),
    'chain_0pct_row_inserted': False,
    'note': ('本补正件**不覆盖**原产物 portfolio_close_20261014.json，另存 _fix 供链式序列与周报取用'
             '（§3.108 条款 22：同日期以 _fix 为准）。派生字段 med_pct / threshold_* / pct_of_total 已同步重算。'),
}

with open(DST, 'w', encoding='utf-8') as f:
    json.dump(d, f, ensure_ascii=False, indent=1)

print(f'\n✅ 写盘 {DST}')
print(f'   组合当日损益：{old_est_pnl:+,.2f} 元 → {d["est_total_pnl"]:+,.2f} 元（Δ {TOTAL_PNL:+,.2f} 元）')
print(f'   组合当日涨幅：{base["est_total_pct"]:.2f}% → {d["est_total_pct"]:.2f}%（raw {base["est_total_pct_raw"]:.4f}% → {d["est_total_pct_raw"]:.4f}%）')
print(f'   组合总资产：  {old_total_mv:,.2f} 元 → {d["total_mv"]:,.2f} 元')
print(f'   医药敞口：    {old_med_pct}% → {d["med_pct"]}%（门槛 {old_thr_all}% → {d["threshold_all_med"]}%）')
print(f'   A股医药 pnl：{old_track_pnl:+,.2f} 元 → {d["tracks"]["A股医药"]["pnl"]:+,.2f} 元')
print(f'   权重（before→after）：{ {k: (old_weights[k], new_weights[k]) for k in old_weights} }')
