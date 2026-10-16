# -*- coding: utf-8 -*-
"""fix_portfolio_close_20261015.py — 补正 2026-10-15 收盘产物（**5 只场外基金 / 7 个持仓行** 净值迟滞到位）

背景（§3.140a / §3.146b / §3.105 / §3.139e / §3.150b）：
  10/15 20:00 盘后档首抓时，以下 **5 只场外基金** 的 **10/15 净值尚未发布**
  （`price_src` = 「净值未推进(nd=2026-10-14，基准 2026-10-14) → 计 0（基准已含）」）：
    000248 汇添富中证主要消费ETF联接A / 汇添富中证主要消费联接A（sean + jasy 各 1 行）
    519915 富国消费主题混合A（sean + jasy 各 1 行）
    161616 融通医疗保健行业混合A/B（sean）
    000727 融通健康产业灵活配置A/B（jasy）
    002742 泓德裕祥债券A（sean，市值 9.41 元）
  → 共 **7 个持仓行**，组合 10/15 当日损益被系统性低估。本档（10/16 08:00 盘前）复抓 F10 确认
     上述 5 只 **10/15 净值均已出库** → 按 §3.140a（跨档补正）执行 `_fix`。
  ⚠️ 这是 §3.140a 的**第 4 例**，且**首次出现「多券同时迟滞」**（前 3 例均为单券：
     10/9 档 000051 +15.79 元、10/13 档 002708 −358.50 元、10/14 档 002708 −592.86 元）
     → **固定工序须由「逐档复抓 002708」升级为「逐档复抓全部『收盘档计 0』行」**（§3.150b 扩展）。

硬守卫（§3.115a / §3.109 条款 26 / §3.112a / §3.146a）：
  ① `|Σ tracks.mv − total_mv| < 1.5`
  ② `|Σ tracks.pnl − est_total_pnl| < 1.5`
  ③ `base_total + est_total_pnl == total_mv`（起点 = 前一收盘 371,790.99 元，**不得用 total_mv**）
  ④ 逐券还原式 `mv0_new + est_pnl` 逐赛道 dev < 1.5（机器判据，§3.112a）
  ⑤ `tracks[].pct_of_total` 一律由 `mv / total_mv` **现算**（§3.146a）
"""
import copy, csv, json, os, re

ROOT = '/Users/jieyang/Documents/WealthHub'
HIST = os.path.join(ROOT, 'data/processed/history')
SRC = os.path.join(HIST, 'portfolio_close_20261015.json')
DST = os.path.join(HIST, 'portfolio_close_20261015_fix.json')
TODAY = '2026-10-16'
FIX_TARGET = '2026-10-15'
NEW_NAV_DATE = '2026-10-15'
PREV_CLOSE_TOTAL = 371790.99           # = base_total（10/14 修正件）

# ---- 载入净值库（判重键 = (code, nav_date)，§3.52 / §3.116a）----
navdb = {}
with open(os.path.join(HIST, 'fund_nav.csv'), encoding='utf-8-sig') as f:
    for r in csv.DictReader(f):
        try:
            navdb[(r['code'], r['nav_date'][:10])] = float(r['nav'])
        except Exception:
            pass

base = json.load(open(SRC, encoding='utf-8'))
d = copy.deepcopy(base)
assert abs(d['base_total'] - PREV_CLOSE_TOTAL) < 0.01, f'base_total 异常: {d["base_total"]}'

# ---- 扫描「收盘档计 0」行 ----
stale = [x for x in d['detail'] if ('未推进' in str(x.get('price_src', '')))
         or ('计 0（基准已含）' in str(x.get('price_src', '')))]
print(f'扫描到「收盘档计 0」行 {len(stale)} 条')
assert stale, '未发现计 0 行，须人工确认是否为「本档无迟滞」档'

total_pnl = 0.0
fix_rows, by_track = [], {}
skipped = []
for row in stale:
    code = ''.join(c for c in str(row['code']) if c.isdigit())[-6:]
    ps = str(row.get('price_src', ''))
    m = re.search(r'(?:nd=|基准 )(\d{4}-\d{2}-\d{2})', ps)
    base_nd = m.group(1) if m else None
    base_nav = navdb.get((code, base_nd)) if base_nd else None
    new_nav = navdb.get((code, NEW_NAV_DATE))
    if base_nav is None or new_nav is None:
        skipped.append({'code': code, 'name': row['name'], 'base_nav_date': base_nd,
                        'base_nav': base_nav, 'new_nav': new_nav})
        print(f'  SKIP {code} {row["name"]}: base_nav={base_nav} new_nav={new_nav}（{NEW_NAV_DATE} 净值仍未出库）')
        continue
    v0 = round(float(row['mv0_new']), 2)
    shares = round(float(row['shares']), 2)
    pct = round((new_nav / base_nav - 1) * 100, 4)
    shares_rev = round(v0 / base_nav, 2)
    assert abs(shares * base_nav - v0) < 1.5, f'shares 与 mv0_new 不自洽: {shares} × {base_nav} vs {v0}'
    assert abs(shares - shares_rev) < 0.5, f'shares 与反算式偏离过大: {shares} vs {shares_rev}'
    pnl = round(v0 * pct / 100, 2)
    pnl_by_shares = round(shares * (new_nav - base_nav), 2)
    assert abs(pnl - pnl_by_shares) < 1.5, f'两法 pnl 偏离: {pnl} vs {pnl_by_shares}'
    total_pnl = round(total_pnl + pnl, 2)
    by_track[row['track']] = round(by_track.get(row['track'], 0.0) + pnl, 2)
    print(f'  {row["account"]:>20} {code} {row["name"][:20]:22s} {base_nav}({base_nd}) → {new_nav}({NEW_NAV_DATE})'
          f'  pct={pct:+.4f}%  mv0_new={v0:,.2f} 元  est_pnl={pnl:+,.2f} 元（原 0 元）')
    row['price_src'] = (f'净值 10/15 ({new_nav}，{pct:+.4f}%)，基准净值日 {base_nd}'
                        '（§3.140a 补正：10/15 档 20:00 首抓时未出库 → 计 0，本档 08:00 复抓到位）')
    row['est_pct'] = pct
    row['est_pnl'] = pnl
    row['est_pct_best'] = row['est_pct_worst'] = pct
    row['est_pnl_best'] = row['est_pnl_worst'] = pnl
    row['est_pnl_low'] = pnl
    row['mv'] = round(v0 + pnl, 2)
    row['fix_applied'] = True
    fix_rows.append({'code': code, 'name': row['name'], 'account': row['account'], 'track': row['track'],
                     'shares': shares, 'base_nav': base_nav, 'base_nav_date': base_nd,
                     'new_nav': new_nav, 'new_nav_date': NEW_NAV_DATE, 'est_pct': pct,
                     'est_pnl_元': pnl, 'before_est_pnl_元': 0.0, 'mv0_new_元': v0})

print(f'\n合计补正 {total_pnl:+,.2f} 元；按赛道 {by_track}；未出库跳过 {len(skipped)} 条')

old = {k: {'mv': d['tracks'][k]['mv'], 'pnl': d['tracks'][k]['pnl']} for k in d['tracks']}
old_total_mv, old_total_pnl, old_total_pct = d['total_mv'], d['est_total_pnl'], d['est_total_pct']
old_med_pct, old_thr_all, old_thr_sh = d['med_pct'], d['threshold_all_med'], d['threshold_a_sh_med']
old_weights = {k: v.get('pct_of_total') for k, v in d['tracks'].items()}

# ---- 赛道行同步重算（§3.115a / §3.109 条款 26）----
for t, dp in by_track.items():
    d['tracks'][t]['pnl'] = round(d['tracks'][t]['pnl'] + dp, 2)
    d['tracks'][t]['mv'] = round(d['tracks'][t]['mv'] + dp, 2)

d['est_total_pnl'] = round(old_total_pnl + total_pnl, 2)
d['total_mv'] = round(old_total_mv + total_pnl, 2)
d['est_total_pct_raw'] = round(d['est_total_pnl'] / d['base_total'] * 100, 4)
d['est_total_pct'] = round(d['est_total_pct_raw'], 2)
d['est_total_pnl_best'] = round(float(base.get('est_total_pnl_best', old_total_pnl)) + total_pnl, 2)
d['est_total_pnl_worst'] = round(float(base.get('est_total_pnl_worst', old_total_pnl)) + total_pnl, 2)
d['est_total_pnl_high'] = d['est_total_pnl_best']
d['est_total_pnl_low'] = d['est_total_pnl_worst']
d['band_note'] = (str(base.get('band_note', '')) +
                  f' ｜§3.140a 补正后 best == worst == 点值（{d["est_total_pnl"]:,.2f} 元）：'
                  '5 只迟滞基金 10/15 净值已出库，全部标的不再存在代理估算项。')

# ---- 医药敞口与门槛同步重算（§3.98 方程解法，与 calc 同式）----
med = round(d['tracks']['A股医药']['mv'] + d['tracks']['美股标普医药']['mv'], 2)
A_sh = d['tracks']['A股医药']['mv']
B = d['total_mv'] - med
d['med_exposure'] = med
d['med_pct'] = round(med / d['total_mv'] * 100, 2)
d['threshold_all_med'] = round(((0.40 / 0.60) * B / med - 1) * 100, 2)
d['threshold_a_sh_med'] = round((((0.40 / 0.60) * B - (med - A_sh)) / A_sh - 1) * 100, 2)

# ---- §3.146a：权重一律 mv/total_mv 现算 ----
for t, v in d['tracks'].items():
    v['pct_of_total'] = round(v['mv'] / d['total_mv'] * 100, 2)
new_weights = {k: v['pct_of_total'] for k, v in d['tracks'].items()}

# ---- 硬守卫 ----
sum_mv = round(sum(v['mv'] for v in d['tracks'].values()), 2)
sum_pnl = round(sum(v['pnl'] for v in d['tracks'].values()), 2)
dev_mv, dev_pnl = round(sum_mv - d['total_mv'], 2), round(sum_pnl - d['est_total_pnl'], 2)
print(f'\n[守卫①] Σtracks.mv {sum_mv:,.2f} vs total_mv {d["total_mv"]:,.2f} → dev {dev_mv}')
print(f'[守卫②] Σtracks.pnl {sum_pnl:,.2f} vs est_total_pnl {d["est_total_pnl"]:,.2f} → dev {dev_pnl}')
assert abs(dev_mv) < 1.5 and abs(dev_pnl) < 1.5
dev_restore = {}
for t in d['tracks']:
    s = round(sum(round(float(x['mv0_new']) + float(x['est_pnl']), 2)
                  for x in d['detail'] if x['track'] == t), 2)
    dev_restore[t] = round(s - d['tracks'][t]['mv'], 2)
print(f'[守卫④] 还原式 mv0_new+est_pnl 逐赛道 dev = {dev_restore}')
assert all(abs(v) < 1.5 for v in dev_restore.values())
assert abs(d['base_total'] + d['est_total_pnl'] - d['total_mv']) < 1.5
print(f'  ✅ 三重硬守卫通过；还原式 {d["base_total"]:,.2f} + ({d["est_total_pnl"]:,.2f}) = {d["total_mv"]:,.2f}')

d['stale_weight_fields_in_fix'] = {
    'note': ('§3.146a：修正件改写 `tracks[].mv` / `total_mv` 后原 `pct_of_total` 必失真；'
             '本档已同步现算为 mv/total_mv，故无需下游换算。'),
    'weights_before_pct': old_weights, 'weights_after_pct': new_weights}
d['detail_mv_policy'] = {
    'note': ('§3.112a：`detail[].mv` 在原始产物中为「基准行原样继承的陈旧值」，与 `mv0_new+est_pnl` 不自洽，'
             '**禁止按字段名取数**；权威式恒为 `mv0_new + est_pnl`。本修正件对 7 个迟滞行直接写权威式值。'),
    'authoritative_expr': 'mv0_new + est_pnl',
    'rows_rewritten_to_authoritative': len(fix_rows)}
d['fix'] = {
    'fix_of': f'portfolio_close_{FIX_TARGET.replace("-", "")}.json',
    'fix_made_at': f'{TODAY} 08:00 盘前档（档型③ 正常交易日盘前）',
    'fix_reason': ('**5 只场外基金 / 7 个持仓行**（000248 ×2、519915 ×2、161616、000727、002742）的 10/15 净值'
                   '在 10/15 档 20:00 首抓时尚未出库，按「基准已含（净值日未推进）→ 计 0」处理致组合当日损益低估；'
                   f'本档 08:00 复抓 F10 确认 10/15 净值均已出库 → 按 §3.140a / §3.105 执行 _fix 补正。'
                   '⚠️ §3.140a **第 4 例**，且**首次多券同时迟滞** → 固定工序扩展为「逐档复抓全部『收盘档计 0』行」。'),
    'base_revision': {'prev_file': f'portfolio_close_{FIX_TARGET.replace("-", "")}.json',
                      'prev_total_元': old_total_mv, 'delta_元': total_pnl,
                      'reason': '跨档补正：昨档缺失净值（5 只基金 10/15）于本档到位，按 §3.140a 回填至事件日当日'},
    'fix_items': fix_rows,
    'skipped_still_pending': skipped,
    'before': {'est_total_pnl_元': old_total_pnl, 'est_total_pct': old_total_pct, 'total_mv_元': old_total_mv,
               'med_pct': old_med_pct, 'threshold_all_med': old_thr_all, 'threshold_a_sh_med': old_thr_sh},
    'after': {'est_total_pnl_元': d['est_total_pnl'], 'est_total_pct': d['est_total_pct'],
              'total_mv_元': d['total_mv'], 'med_pct': d['med_pct'],
              'threshold_all_med': d['threshold_all_med'], 'threshold_a_sh_med': d['threshold_a_sh_med']},
    'delta': {'est_total_pnl_元': total_pnl,
              'est_total_pct': round(d['est_total_pct'] - old_total_pct, 4),
              'total_mv_元': round(d['total_mv'] - old_total_mv, 2),
              'by_track_pnl_元': by_track,
              'weights_pct': {k: {'before': old_weights[k], 'after': new_weights[k],
                                  'delta': round(new_weights[k] - old_weights[k], 2)} for k in old_weights}},
    'guards': {'dev_sum_track_mv_vs_total_mv': dev_mv, 'dev_sum_track_pnl_vs_est_total_pnl': dev_pnl,
               'dev_restore_by_track': dev_restore,
               'restore_from': f"base_total（前一收盘 {d['base_total']:,.2f} 元），非 total_mv"},
    'chain_0pct_row_inserted': False,
    'note': ('本补正件**不覆盖**原产物，另存 _fix 供链式序列与周报取用（§3.108 条款 22：同日期以 _fix 为准）。'
             '派生字段 med_pct / threshold_* / pct_of_total 已同步重算。')}

json.dump(d, open(DST, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(f'\n✅ 写盘 {DST}')
print(f'   组合当日损益：{old_total_pnl:+,.2f} 元 → {d["est_total_pnl"]:+,.2f} 元（Δ {total_pnl:+,.2f} 元）')
print(f'   组合当日涨幅：{old_total_pct:.2f}% → {d["est_total_pct"]:.2f}%（raw → {d["est_total_pct_raw"]:.4f}%）')
print(f'   组合总资产：  {old_total_mv:,.2f} 元 → {d["total_mv"]:,.2f} 元')
print(f'   医药敞口：    {old_med_pct}% → {d["med_pct"]}%（门槛 {old_thr_all}% → {d["threshold_all_med"]}%）')
print(f'   权重（before→after）：{ {k: (old_weights[k], new_weights[k]) for k in old_weights} }')
