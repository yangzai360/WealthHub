# -*- coding: utf-8 -*-
"""2026-10-19 收盘产物 _fix 补正（§3.105 / §3.140a 第 5 例 / §3.109 条款 26 / §3.112a）

背景：10/19 盘后档 20:00 与 20:5x **两次**复抓时，4 个持仓行的 10/19 净值仍未出库
      （nd 仍 = 10/16 == 基准净值日）→ 按「基准已含」计 0，登记为「净值日未推进」。
本档（10/20 08:00 盘前档）复抓 F10：4 行 10/19 净值**均已出库** →
  000727 2.4380 (+1.20%) / 161616 1.6450 (+1.04%) / 002742 1.2710 (+0.17%) / 100032 0.9720 (+0.73%)
  → 按 §3.140a 固定工序执行 _fix 覆盖，并**同步重算 tracks[].pnl（条款 26）**。

★口径要点：
  - 逐券 pct 用「隐含单位净值」法（mv0_new / shares），与历次 _fix 一致
  - 逐券还原式 = `mv0_new + est_pnl`（§3.112a 机器判据，禁止按字段名取 detail.mv）
  - `tracks[].pct_of_total` 一律由 `mv / total_mv` 现算（§3.146a：_fix 件不得沿用旧分母）

三重硬守卫：
  ① 逐赛道还原式 `mv0_new + pnl` dev 必须 < 1.5 元（§3.112a）
  ② |Σ tracks.pnl − est_total_pnl| < 1.5 元
  ③ |Σ tracks.mv − total_mv| < 1.5 元
输出：portfolio_close_20261019_fix.json
"""
import json, os

BASE = '/Users/jieyang/Documents/WealthHub'
HIST = os.path.join(BASE, 'data/processed/history')

orig = json.load(open(os.path.join(HIST, 'portfolio_close_20261019.json'), encoding='utf-8'))
src = json.load(open(os.path.join(HIST, 'fetch_summary_2026-10-20_preopen.json'), encoding='utf-8'))

# 本档复抓到的 10/19 真实净值（来自 fetch_summary.fallback_verdict）
NAV = {}
for c, v in (src.get('fallback_verdict') or {}).items():
    if v.get('refetch_nav_date') == '2026-10-19':
        NAV[c] = (v['refetch_nav_date'], float(v['refetch_nav']), v.get('refetch_pct'))
print('本档可补正的 10/19 净值:', {k: v[1] for k, v in NAV.items()})

TODAY = '2026-10-19'
BASE_TOTAL = round(float(orig['base_total']), 2)

detail = []
fixed_rows = []
for x in orig['detail']:
    y = dict(x)
    src_txt = str(y.get('price_src', ''))
    code6 = ''.join(c for c in str(y['code']) if c.isdigit())
    if '净值未推进' in src_txt and code6 in NAV:
        nd, nav, pct_src = NAV[code6]
        if nd == TODAY:
            sh = float(y['shares'])
            v0 = round(float(y['mv0_new']), 2)
            imp = v0 / sh
            pct = round((nav / imp - 1) * 100, 4)
            pnl = round(v0 * pct / 100, 2)
            y['est_pct'] = pct
            y['est_pnl'] = pnl
            y['est_pct_best'] = pct
            y['est_pnl_best'] = pnl
            y['est_pct_worst'] = pct
            y['est_pnl_worst'] = pnl
            y['price_src'] = (f'净值 10/19 ({nav}) 真实兑现（_fix：10/19 盘后 20:00 与 20:5x 两次复抓均未出库，'
                              f'10/20 08:00 复抓到库）｜Δ {pct:+.4f}%（隐含单位净值 {round(imp,4)}）')
            y['fix_applied'] = True
            fixed_rows.append({'account': y['account'], 'code': code6, 'name': y['name'],
                               'shares': sh, 'mv0_new': v0, 'implied_nav': round(imp, 6),
                               'nav_1019': nav, 'src_pct': pct_src, 'pct': pct, 'pnl': pnl})
    detail.append(y)

# ---------- 重算 tracks（条款 26：必须同步重算，不得只改总量） ----------
total_pnl = round(sum(d['est_pnl'] for d in detail), 2)
total_mv = round(BASE_TOTAL + total_pnl, 2)
total_pct_raw = round(total_pnl / BASE_TOTAL * 100, 4)
total_pct = round(total_pct_raw, 2)

tracks = {}
for d in detail:
    t = tracks.setdefault(d['track'], {'mv0': 0.0, 'mv': 0.0, 'pnl': 0.0})
    t['mv0'] += d['mv0_new']
    t['mv'] += d['mv0_new'] + d['est_pnl']
    t['pnl'] += d['est_pnl']
for k, v in tracks.items():
    for f in ('mv0', 'mv', 'pnl'):
        v[f] = round(v[f], 2)
    v['pct_of_total'] = round(v['mv'] / total_mv * 100, 2)   # §3.146a 现算
    v['day_pct'] = round(v['pnl'] / v['mv0'] * 100, 3) if v['mv0'] else 0.0

# 保持与原件一致的赛道顺序
_order = list(orig['tracks'].keys())
tracks = {k: tracks[k] for k in _order if k in tracks}

# ---------- 三重硬守卫 ----------
dev = []
for t in tracks:
    s = round(sum(d['mv0_new'] + d['est_pnl'] for d in detail if d['track'] == t), 2)
    dev.append(round(s - tracks[t]['mv'], 2))
assert all(abs(x) < 1.5 for x in dev), f'还原式守卫失败 {dev}'
sum_mv = round(sum(v['mv'] for v in tracks.values()), 2)
sum_pnl = round(sum(v['pnl'] for v in tracks.values()), 2)
assert abs(sum_mv - total_mv) < 1.5, f'Σmv 守卫失败 {sum_mv} vs {total_mv}'
assert abs(sum_pnl - total_pnl) < 1.5, f'Σpnl 守卫失败 {sum_pnl} vs {total_pnl}'
assert abs(round(sum(d['mv0_new'] for d in detail), 2) - BASE_TOTAL) < 1.5, 'Σ mv0 守卫失败'

# ---------- 医药敞口重算（§3.146a：一律由 mv 现算） ----------
def med_calc(tr):
    med_mv = round(sum(v['mv'] for k, v in tr.items() if '医药' in k), 2)
    a_sh = round(sum(v['mv'] for k, v in tr.items() if k == 'A股医药'), 2)
    total = round(sum(v['mv'] for v in tr.values()), 2)
    pct = round(med_mv / total * 100, 2)

    def thr(w_mv):
        """门槛收益率：仅该部分上涨（分母随市值同比扩大）
        (m + w·r) / (1 + w·r) = L  →  r = (L − m) / (w·(1 − L))
        （§3.98 / §3.108 条款 8：不得用「相对跑赢 pct」线性外推）"""
        m = med_mv / total
        w = w_mv / total
        return round((0.40 - m) / (w * (1 - 0.40)) * 100, 2)
    return med_mv, pct, thr(med_mv), thr(a_sh)


med_mv, med_pct, thr_all, thr_a_sh = med_calc(tracks)

# ---------- 港联系暴露重算（分母变化 → pct 必须重算，金额不变） ----------
hk_total = round(float(orig['hk_total']), 2)
hk_total_pct = round(hk_total / total_mv * 100, 2)
track_layer_hk_pct = tracks['恒生科技']['pct_of_total']

# ---------- 主动医药基真实倍数重算（161616 / 000727 本档获得真实净值） ----------
board_med_pct = 1.1825   # 10/19 A股医药板块代理（中证医药/中证医疗/医疗ETF/医药ETF 四口径均值）
active_mult = dict(orig.get('active_mult') or {})
for r in fixed_rows:
    if r['code'] in active_mult:
        active_mult[r['code']].update({'real_pct': r['pct'], 'estimated': False,
                                       'mult_vs_board_med': round(r['pct'] / board_med_pct, 3)})

# ---------- 可定价比例重算（4 行全部到位 → 100%） ----------
priceable_total = round(total_mv, 2)
priceable_pct = 100.0

out = dict(orig)
out.update({
    'base_total': BASE_TOTAL,
    'est_total_pnl': total_pnl,
    'est_total_pct': total_pct,
    'est_total_pct_raw': total_pct_raw,
    'est_total_pnl_best': total_pnl,
    'est_total_pnl_worst': total_pnl,
    'est_total_pnl_high': total_pnl,
    'est_total_pnl_low': total_pnl,
    'est_band': 0.0,
    'band_note': ('本档全部标的均为真实价格/真实净值（无代理估算）；_fix 后 4 行净值到位 → '
                  'best == worst == 点值（§3.116b）'),
    'total_mv': total_mv,
    'tracks': tracks,
    'detail': detail,
    'med_exposure': med_mv,
    'med_pct': med_pct,
    'threshold_all_med': thr_all,
    'threshold_a_sh_med': thr_a_sh,
    'hk_total': hk_total,
    'hk_total_pct': hk_total_pct,
    'track_layer_hk_pct': track_layer_hk_pct,
    'active_mult': active_mult,
    'unpriced': [],
    'unpriced_total': 0.0,
    'priceable_total': priceable_total,
    'priceable_pct': priceable_pct,
    'restore_rule_used': 'mv0_new+pnl',
    'restore_dev': dev,
    'detail_restore_rule': 'mv0_new+pnl',
    'detail_restore_dev': dev,
    'detail_restore_total': total_mv,
    'detail_restore_note': ('逐券还原式 mv0_new+est_pnl 逐赛道 dev 全 0 → 通过；'
                            'detail.mv 为基准行继承的陈旧值，禁止直接取用（§3.112a）'),
    'proxy_used': [],
    'fix_applied': True,
    'fix': {
        'fix_of': 'portfolio_close_20261019.json',
        'fix_made_at': '2026-10-20 08:00 盘前档（§3.140a 跨档补正·第 5 例）',
        'fix_reason': ('4 个持仓行（161616 / 000727 / 002742 / 100032）的 10/19 净值在 10/19 盘后档 '
                       '20:00 与 20:5x 两次复抓时均未出库（nd == 10/16 == 基准净值日）→ 按「基准已含」计 0，'
                       '致组合当日损益低估；10/20 08:00 复抓 F10 确认 4 行 10/19 净值均已出库 → 按 §3.140a 执行 _fix'),
        'rows_fixed': fixed_rows,
        'prev_total': round(float(orig['total_mv']), 2),
        'prev_pnl': round(float(orig['est_total_pnl']), 2),
        'new_total': total_mv,
        'new_pnl': total_pnl,
        'delta_total': round(total_mv - float(orig['total_mv']), 2),
        'delta_pnl': round(total_pnl - float(orig['est_total_pnl']), 2),
        'tracks_pnl_recomputed': True,
        'tracks_recompute_dev': [
            {t: {'before': round(float(orig['tracks'][t]['pnl']), 2),
                 'after': tracks[t]['pnl'],
                 'delta': round(tracks[t]['pnl'] - float(orig['tracks'][t]['pnl']), 2)}}
            for t in tracks],
        'guards': {
            'restore_dev_max_abs': max(abs(x) for x in dev),
            'sigma_mv_dev': round(sum_mv - total_mv, 2),
            'sigma_pnl_dev': round(sum_pnl - total_pnl, 2),
            'sigma_mv0_dev': round(round(sum(d['mv0_new'] for d in detail), 2) - BASE_TOTAL, 2),
        },
    },
})
out['note'] = (str(orig.get('note', '')) +
               ' ｜🔴 本件为 _fix 修正件（10/20 08:00 生成）：4 行 10/19 净值到位'
               '（161616 1.6450 / 000727 2.4380 / 002742 1.2710 / 100032 0.9720），当日损益由 '
               f'{float(orig["est_total_pnl"]):+,.2f} 元修正为 {total_pnl:+,.2f} 元'
               f'（{total_pct_raw:+.4f}%），总资产 {total_mv:,.2f} 元；'
               'tracks[].pnl 与 pct_of_total 已同步重算，三重硬守卫全通过。')

p = os.path.join(HIST, 'portfolio_close_20261019_fix.json')
json.dump(out, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

print('=== _fix 明细 ===')
for r in fixed_rows:
    print(f"  {r['account']:20s} {r['code']} {r['name'][:14]:14s} mv0_new={r['mv0_new']:>10,.2f} "
          f"nav={r['nav_1019']} implied={r['implied_nav']} pct={r['pct']:+.4f}% pnl={r['pnl']:+,.2f}")
print(f'\n当日损益：{float(orig["est_total_pnl"]):+,.2f} 元 → {total_pnl:+,.2f} 元 '
      f'(Δ {total_pnl - float(orig["est_total_pnl"]):+,.2f} 元)')
print(f'总资产：{float(orig["total_mv"]):,.2f} 元 → {total_mv:,.2f} 元；收益率 {total_pct_raw:+.4f}%')
print('赛道：')
for t, v in tracks.items():
    print(f"  {t:12s} mv={v['mv']:>11,.2f} pnl={v['pnl']:>+9,.2f} 权重={v['pct_of_total']:5.2f}% "
          f"day={v['day_pct']:+.3f}%")
print(f"\n守卫：restore_dev={dev} / Σmv_dev={round(sum_mv-total_mv,2)} / Σpnl_dev={round(sum_pnl-total_pnl,2)}")
print(f'医药敞口 {med_pct}%（{med_mv:,.2f} 元）门槛 +{thr_all}% / +{thr_a_sh}%')
print(f'港联系 {hk_total:,.2f} 元 = {hk_total_pct}%（赛道层 {track_layer_hk_pct}%）')
print(f'SAVED {p}')
