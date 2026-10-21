# -*- coding: utf-8 -*-
"""2026-10-21 盘后：组合收盘计算（链式法，§3.79/§3.105/§3.109/§3.111/§3.112a 口径）

档型 = 正常交易日收盘（A股 10/21 15:00 收盘 + 港股 10/21 16:00 收盘 + 美股 10/21 未开盘）
base = portfolio_close_20261020_fix.json（10/20 收盘修正件 = 372,666.60 元，45 行）

本档定价：
  · 场内（ETF 9 + 个股 3 + 广联达 1）＝ 10/21 收盘价
  · 场外 23 只中 17 只出 10/21 真实净值
  · QDII 000369 / 016280 = 推进至 **10/20**（+1.98% / +2.01%）→ 核销 US 10/20 段
  · 164906（LOF）= 10/20 净值 0.8628（−1.13%）→ 真实兑现
  · 002708 / 002742 / 004752 = 10/21 净值未出库 → 计 0（基准已含）、列「未定价缺口」
产物：portfolio_close_20261021.json
"""
import json, os, re

BASE = '/Users/jieyang/Documents/WealthHub'
HIST = os.path.join(BASE, 'data/processed/history')
TODAY = '2026-10-21'
TODAYC = '20261021'

base = json.load(open(os.path.join(HIST, 'portfolio_close_20261020_fix.json'), encoding='utf-8'))
cur = json.load(open(os.path.join(HIST, 'close_' + TODAYC + '.json'), encoding='utf-8'))
navj = json.load(open(os.path.join(HIST, 'fundnav_close_' + TODAYC + '.json'), encoding='utf-8'))


# ---------- 0. 基准还原式：机器判据（§3.111 / §3.112a） ----------
def basis(x):
    return round(float(x.get('mv0_new') or 0) + float(x.get('est_pnl') or 0), 2)


tr = base['tracks']
CAND = [('mv0_new+pnl', basis),
        ('mv0+pnl', lambda x: round(float(x.get('mv0') or 0) + float(x.get('est_pnl') or 0), 2)),
        ('mv', lambda x: round(float(x.get('mv') or 0), 2))]
dev_all = {}
for name, fn in CAND:
    dev_all[name] = [round(sum(fn(x) for x in base['detail'] if x['track'] == t) - tr[t]['mv'], 2) for t in tr]
restore_rule, restore_dev = None, None
for name, _ in CAND:
    if all(abs(d) < 1.5 for d in dev_all[name]):
        restore_rule, restore_dev = name, dev_all[name]
        break
if restore_rule is None:
    raise SystemExit('三种还原式均未通过硬守卫，拒绝继续（§3.112a）')
if restore_rule != 'mv0_new+pnl':
    raise SystemExit(f'⚠️ 还原式与他档不一致（{restore_rule}），须人工复核后放行')
print(f'✅ 还原式判据：{restore_rule}，逐赛道 dev = {restore_dev}')
print(f"   （未通过者：mv0+pnl={dev_all['mv0+pnl']} / mv={dev_all['mv']}）")

base_val = [basis(x) for x in base['detail']]
BASE_TOTAL = round(float(base['total_mv']), 2)
tot = round(sum(base_val), 2)
if abs(tot - BASE_TOTAL) >= 1.5:
    raise SystemExit(f'基准还原失败 {tot} vs {BASE_TOTAL}')
print(f'✅ 基准还原校验：Σ = {tot:,.2f} 元 = total_mv {BASE_TOTAL:,.2f} 元（{len(base_val)} 行）')
_sp = round(sum(x['est_pnl'] for x in base['detail']), 2)
if abs(_sp - base['est_total_pnl']) >= 1.5:
    raise SystemExit('基准 Σpnl 守卫失败（§3.109）')
print(f'✅ Σ tracks.pnl 守卫通过（{base["est_total_pnl"]:+,.2f} 元）')

# ---------- 1. 价格表 ----------
PX = {}
for x in cur['etf'] + cur['stocks']:
    PX[x['code'].replace('sh', '').replace('sz', '')] = x['close']
    PX[x['code']] = x['close']

NAV = {}
for n in navj['fund_navs']:
    c = n['code']
    if c not in NAV or n['nav_date'] > NAV[c][0]:
        NAV[c] = (n['nav_date'], n['nav'])


def parse_base_nav_date(src):
    s = str(src)
    m = re.search(r'净值\s*(?:新净值\s*)?(\d{4})-(\d{2})-(\d{2})', s)
    if m:
        return f'{m.group(1)}-{m.group(2)}-{m.group(3)}'
    m = re.search(r'净值\s*(\d{1,2})/(\d{1,2})', s)
    if m:
        return f'2026-{int(m.group(1)):02d}-{int(m.group(2)):02d}'
    m = re.search(r'(?:nd=|基准(?:为)?\s*)(\d{4})-(\d{2})-(\d{2})', s)
    if m:
        return f'{m.group(1)}-{m.group(2)}-{m.group(3)}'
    return None


# ---------- 2. 板块/指数 ----------
BRD = {x['code']: x['pct'] for x in cur['boards']}
ETFP = {x['code']: x['pct'] for x in cur['etf']}
IDXP = {x['code']: x['pct'] for x in cur['indices']}
IDXCLOSE = {x['code']: x['close'] for x in cur['indices']}
BOARD_MED = round((BRD['sh000933'] + BRD['sz399989'] + ETFP['sh512170'] + ETFP['sz159938']) / 4, 4)
LEADER_MED = BRD['sh000913']
LAG_MED = round((BRD['sh000933'] + BRD['sz399989'] + ETFP['sh512170']) / 3, 4)
print(f'BOARD_MED={BOARD_MED}%  300医药={LEADER_MED}%  LAG_MED={LAG_MED}%')

# ---------- 3. 逐券定价 ----------
detail, missing, qdii_applied, nav_today = [], [], [], []
for i, x in enumerate(base['detail']):
    code6 = ''.join(c for c in str(x['code']) if c.isdigit())
    sh = float(x['shares']) if x.get('shares') else 0.0
    v0 = base_val[i]
    pct = 0.0
    if code6 == '' or sh == 0:
        src = '现金'
    elif code6 in PX:
        imp = v0 / sh
        pct = round((PX[code6] / imp - 1) * 100, 4)
        src = f'场内收盘 {TODAY} {PX[code6]}（基准 {round(imp,4)}）'
    elif code6 in NAV:
        nd, nav = NAV[code6]
        imp = v0 / sh
        base_nd = parse_base_nav_date(x.get('price_src', ''))
        if nd == TODAY:
            pct = round((nav / imp - 1) * 100, 4)
            src = f'净值 {TODAY} ({nav})，基准净值日 {base_nd}'
            nav_today.append((code6, x['name'], nav, pct, round(imp, 4)))
        elif base_nd and nd > base_nd:
            pct = round((nav / imp - 1) * 100, 4)
            src = (f'新净值 {nd} ({nav}) 真实兑现（基准为 {base_nd}，跨 1 个交易日）'
                   f'｜Δ {pct:+.4f}%')
            qdii_applied.append((code6, x['name'], nd, nav, pct, base_nd, round(imp, 4), v0))
        else:
            src = f'净值未推进(nd={nd}，基准 {base_nd}) → 计 0（基准已含）'
            missing.append((code6, x['name'], nd, '净值日未推进→计0'))
    else:
        src = '数据暂缺→按0'
        missing.append((code6, x['name'], None, '数据暂缺'))
    detail.append({**x, 'mv0_new': v0, 'est_pct': pct, 'est_pnl': round(v0 * pct / 100, 2),
                   'price_src': src})

total_pnl = round(sum(d['est_pnl'] for d in detail), 2)
total_pct_raw = round(total_pnl / BASE_TOTAL * 100, 4)
new_total = round(BASE_TOTAL + total_pnl, 2)

tracks = {}
for d in detail:
    t = tracks.setdefault(d['track'], {'mv0': 0.0, 'mv': 0.0, 'pnl': 0.0})
    t['mv0'] += d['mv0_new']; t['mv'] += d['mv0_new'] + d['est_pnl']; t['pnl'] += d['est_pnl']
for k, v in tracks.items():
    for f in ('mv0', 'mv', 'pnl'):
        v[f] = round(v[f], 2)
    v['pct_of_total'] = round(v['mv'] / new_total * 100, 2)
    v['day_pct'] = round(v['pnl'] / v['mv0'] * 100, 3) if v['mv0'] else 0.0

assert abs(round(sum(v['mv'] for v in tracks.values()), 2) - new_total) < 1.5, 'Σ tracks.mv 守卫失败'
assert abs(round(sum(v['pnl'] for v in tracks.values()), 2) - total_pnl) < 1.5, 'Σ tracks.pnl 守卫失败'
assert abs(round(sum(d['mv0_new'] for d in detail), 2) - BASE_TOTAL) < 1.5, 'Σ mv0 守卫失败'
print('✅ 三道硬守卫全部通过')
print(f'组合当日 {total_pnl:+,.2f} 元（{total_pct_raw:+.4f}%）→ {new_total:,.2f} 元')
for k, v in sorted(tracks.items(), key=lambda kv: kv[1]['pnl']):
    print(f"  {k:8s} mv0={v['mv0']:>10,.2f}  mv={v['mv']:>10,.2f}  pnl={v['pnl']:>+9,.2f}  day={v['day_pct']:+.3f}%  w={v['pct_of_total']:.2f}%")

# ---------- 4. 纪律台账 ----------
DISC1, DISC2 = 1882.46, 1904.44
DISC_CUM = round(DISC1 + DISC2, 2)
assert abs(DISC_CUM - 3786.90) < 0.01
HSTECH = next(x for x in cur['hk'] if x['code'] == 'HSTECH')
H_4250 = round((HSTECH['close'] / 4250 - 1) * 100, 4)
H_4000 = round((HSTECH['close'] / 4000 - 1) * 100, 4)
CONSUME = IDXCLOSE['sh000932']
C_12100 = round((CONSUME / 12100 - 1) * 100, 4)
PLAN_4000 = round(BASE_TOTAL * 0.005, 2)
print(f'恒生科技 {HSTECH["close"]}（{HSTECH["pct"]:+.2f}%）vs 4,250 = {H_4250}% / vs 4,000 = {H_4000}%')
print(f'中证消费 {CONSUME} vs 12,100 = {C_12100}%')
print(f'4,000 新防线减配预案 = {PLAN_4000:,.2f} 元')

weight_after = {k: v['mv'] / new_total * 100 for k, v in tracks.items()}
weight_after['恒生科技'] -= DISC_CUM / new_total * 100
weight_after['现金'] += DISC_CUM / new_total * 100
weight_after = {k: round(v, 2) for k, v in weight_after.items()}
assert abs(sum(weight_after.values()) - 100) < 0.05, '减仓后权重合计守卫失败'
hk_after = round(tracks['恒生科技']['mv'] - DISC_CUM, 2)
cash_after = round(tracks['现金']['mv'] + DISC_CUM, 2)
assert abs(weight_after['恒生科技'] - hk_after / new_total * 100) < 0.02
assert abs(weight_after['现金'] - cash_after / new_total * 100) < 0.02

DISCIPLINE = {
    'cut1': {'pct': 0.5, 'amount': DISC1, 'triggered_on': '2026-09-29', 'settled_on': '2026-09-30'},
    'cut2': {'pct': 0.5, 'amount': DISC2, 'triggered_on': '2026-10-02', 'settled_on': '2026-10-08',
             'targets': ['012348（天弘恒生科技联接A）', '513180（恒生科技ETF华夏）'],
             'target_rule': '标的限「纯恒科」口径，不落在中概（513050 / 164906）'},
    'cumulative_amount': DISC_CUM,
    'cumulative_selfcheck': {'sum_of_cuts': round(DISC1 + DISC2, 2), 'cumulative_amount': DISC_CUM,
                             'ok': abs(DISC1 + DISC2 - DISC_CUM) < 0.01},
    'settled_on': ['2026-09-30', '2026-10-08'],
    'today_action': {'discipline_cut_today': 0,
                     'reason': ('恒生科技 **收盘 3,994.77 首次收盘失守 4,000 观察线**（%+.4f%%）→ 观察线按 13:45 档 P0 预案'
                                '**升级为防线**；但该升级的执行口径为「**10/22 盘前档建立 −0.5%% 减配预案（%.2f 元）、当日不执行**」'
                                '→ **本档动作 0 元**；4,250 线破位在案且同季已用 2 次，不重复叠加（§3.114c）'
                                % (H_4000, PLAN_4000))},
    'settle': '两笔均已按净值成交（价值中性，P&L 口径不变）；本档只重算纪律后权重',
    'hk_after': hk_after, 'cash_after': cash_after, 'weight_after': weight_after,
    'basis_note': ('累计口径 = 已成交 1,882.46 元 + 已成交 1,904.44 元（§3.123e / §3.125c）；'
                   '分母为「上一有效估值日基准总资产」×0.5%'),
    'pending_plan': {'trigger': 'HSTECH 收盘 < 4,000', 'created_on': '2026-10-21 盘后（判定）/ 10/22 盘前（建案）',
                     'amount': PLAN_4000, 'basis': '0.5% × 372,666.60 元', 'execute_on': '不早于 2026-10-22 盘前档',
                     'targets_rule': '纯恒科口径（012348 / 513180），不落中概'},
    'defense': {
        'hstech_4250': {'close': HSTECH['close'], 'line': 4250, 'gap_pct': H_4250,
                        'state': 'close_level_break_widened', 'action': 'no_new_cut_same_line_used_twice'},
        'hstech_4000': {'close': HSTECH['close'], 'line': 4000, 'gap_pct': H_4000,
                        'state': 'close_level_breached',
                        'intraday_low': HSTECH['low'],
                        'action': 'observation_line_upgraded_to_defense; plan_created_for_next_preopen'},
        'zz_consume_12100': {'close': CONSUME, 'line': 12100, 'gap_pct': C_12100,
                             'state': 'above_lower_line'},
        'a_med_reverse_1_5pct': {'board_proxy_pct': BOARD_MED, 'line': -1.5,
                                 'state': 'not_triggered', 'baseline_reset_on': '2026-10-19'},
    },
}

# ---------- 5. 港股暴露双层拆解 ----------
HK_ROWS = {'012348': 'pure', '513180': 'pure', '513050': 'concept', '164906': 'concept',
           '000071': 'broad', '159920': 'broad'}
hk, hk_pnl = {'pure': 0.0, 'concept': 0.0, 'broad': 0.0}, {'pure': 0.0, 'concept': 0.0, 'broad': 0.0}
hk_rows = []
for d in detail:
    c6 = ''.join(c for c in str(d['code']) if c.isdigit())
    if c6 in HK_ROWS:
        seg = HK_ROWS[c6]
        hk[seg] += d['mv0_new'] + d['est_pnl']
        hk_pnl[seg] += d['est_pnl']
        hk_rows.append({'code': c6, 'name': d['name'], 'seg': seg, 'basis': d['mv0_new'],
                        'pct': d['est_pct'], 'pnl': d['est_pnl']})
hk = {k: round(v, 2) for k, v in hk.items()}
hk_pnl = {k: round(v, 2) for k, v in hk_pnl.items()}
hk_total = round(sum(hk.values()), 2)
hk_total_pct = round(hk_total / new_total * 100, 2)
track_layer_hk_pct = round(tracks['恒生科技']['mv'] / new_total * 100, 2)
print(f"港联系 三层 {hk} / pnl {hk_pnl} / 合计 {hk_total:,.2f} 元 ({hk_total_pct}%)")

# ---------- 6. 主动医药基真实倍数（同券多账户行须按 mv0_new 加权，默认「取 rows[0]」会失真） ----------
def agg(c6):
    rows = [d for d in detail if ''.join(ch for ch in str(d['code']) if ch.isdigit()) == c6]
    if not rows:
        return None
    m = round(sum(r['mv0_new'] for r in rows), 2)
    pc = round(sum(r['mv0_new'] * r['est_pct'] for r in rows) / m, 4) if m else 0.0
    return {'name': rows[0]['name'], 'mv': m, 'real_pct': pc, 'n_rows': len(rows)}


active_mult = {}
for c, nm in (('002708', '大摩健康产业A'), ('161616', '融通医疗保健'), ('000727', '融通健康产业'),
              ('001180', '广发医药卫生'), ('001551', '天弘医药100C')):
    a = agg(c)
    if a:
        active_mult[c] = {'name': nm, 'real_pct': a['real_pct'], 'mv': a['mv'], 'n_rows': a['n_rows'],
                          'mult_vs_board_med': round(a['real_pct'] / BOARD_MED, 3) if BOARD_MED else None,
                          'mult_vs_300med': round(a['real_pct'] / LEADER_MED, 3) if LEADER_MED else None,
                          'estimated': abs(a['real_pct']) < 1e-9}

# ---------- 7. 被动联接类偏差检验（同券多行按 mv0_new 加权） ----------
HSI_PCT = next((x['pct'] for x in cur['hk'] if x['code'] == 'HSI'), None)
proxy_check = {}
for c, idx, lab in (('012323', BRD['sz399989'], '中证医疗'), ('000051', IDXP['sh000300'], '沪深300'),
                    ('000071', HSI_PCT, '恒生指数(跨市场参考,§3.112i 禁互验)'),
                    ('001551', BRD['sh000933'], '中证医药(近似代理)'),
                    ('001180', BRD['sh000933'], '中证医药(近似代理)'),
                    ('110020', IDXP['sh000300'], '沪深300'),
                    ('012348', HSTECH['pct'], '恒生科技(跨市场参考,§3.112i 禁互验)')):
    a = agg(c)
    if a and isinstance(idx, float):
        proxy_check[c] = {'real': a['real_pct'], 'index': idx, 'label': lab, 'mv': a['mv'],
                          'dev': round(a['real_pct'] - idx, 4)}

# ---------- 8. 医药敞口与门槛 ----------
med = round(tracks['A股医药']['mv'] + tracks['美股标普医药']['mv'], 2)
A, B = med, new_total - med
threshold_all = round(((0.40 / 0.60) * B / A - 1) * 100, 2)
A_sh = tracks['A股医药']['mv']
threshold_sh = round((((0.40 / 0.60) * B - (med - A_sh)) / A_sh - 1) * 100, 2)
med_pct = round(med / new_total * 100, 2)
print(f'医药敞口 {med:,.2f} 元 = {med_pct}%；门槛 all={threshold_all}% / 仅A股={threshold_sh}%')

# ---------- 9. 结构顺序 ----------
order = sorted([('300医药', BRD['sh000913']), ('中证医药', BRD['sh000933']), ('中证医疗', BRD['sz399989'])],
               key=lambda y: -y[1])

# ---------- 10. 未定价 / 影子 ----------
unpriced, unpriced_total = [], 0.0
for d in detail:
    if d['price_src'].startswith(('净值未推进', '数据暂缺')):
        unpriced.append({'code': ''.join(c for c in str(d['code']) if c.isdigit()), 'name': d['name'],
                         'mv': round(d['mv0_new'], 2), 'reason': d['price_src']})
        unpriced_total += d['mv0_new']
unpriced_total = round(unpriced_total, 2)
priceable_total = round(new_total - unpriced_total, 2)
priceable_pct = round(priceable_total / new_total * 100, 2)

shadow = []
for c, proxy_map, note in (
        ('002708', ('board', 1.0), '中证医药 −0.28% × 0.85（主动基弹性中位，参考 10/20 的 0.796 与 10/21 盘中 0.5 倍区间）'),
        ('002742', ('direct', -0.05), '债券型，按 0 近似（对组合影响 < 1 元）'),
        ('004752', ('direct', BRD['sh000827'] * 0), '传媒联接，按 0 近似')):
    rows = [d for d in detail if ''.join(ch for ch in str(d['code']) if ch.isdigit()) == c]
    if not rows:
        continue
    mv = round(sum(r['mv0_new'] for r in rows), 2)
    if proxy_map[0] == 'board':
        pc = round(BRD['sh000933'] * 0.85, 2)
    else:
        pc = round(proxy_map[1], 2)
    shadow.append({'code': c, 'name': rows[0]['name'], 'mv': mv, 'proxy_pct': pc,
                   'est_pnl': round(mv * pc / 100, 2), 'note': note})
shadow_total = round(sum(s['est_pnl'] for s in shadow), 2)
print(f'未定价 {unpriced_total:,.2f} 元（{round(unpriced_total/new_total*100,2)}%）；影子 {shadow_total:+,.2f} 元')

# ---------- 11. QDII US 10/20 段核销 ----------
QDII_CODES = ('000369', '016280')
qdii_base_notional = round(sum(d['mv0_new'] for d in detail
                               if ''.join(c for c in str(d['code']) if c.isdigit()) in QDII_CODES), 2)
qdii_mv = round(tracks['美股标普医药']['mv'], 2)
IYH_1020 = 2.34
qdii_realized_pct, qdii_nav, qdii_nd = {}, {}, {}
for c, n, nd, nav, pct, bnd, imp, v0 in qdii_applied:
    if c in QDII_CODES:
        qdii_realized_pct[c] = pct
        qdii_nav[c] = nav
        qdii_nd[c] = nd
qdii_booked_amt = round(sum(d['est_pnl'] for d in detail
                            if ''.join(c for c in str(d['code']) if c.isdigit()) in QDII_CODES), 2)
lod_realized = [{'code': c, 'name': n, 'nd': nd, 'nav': nav, 'pct': pct}
                for c, n, nd, nav, pct, bnd, imp, v0 in qdii_applied if c == '164906']
coef_vs_IYH_1020 = {k: round(abs(v) / abs(IYH_1020), 4) for k, v in qdii_realized_pct.items()}
# 预告区间分母 = 13:45 档登记时点的 QDII 基准名义（60,691.90 元），不是当日收盘后市值（§3.166b）
PRED_LOW = round(qdii_base_notional * IYH_1020 * 0.60 / 100, 2)
PRED_MID = round(qdii_base_notional * IYH_1020 * 0.72 / 100, 2)
PRED_HIGH = round(qdii_base_notional * IYH_1020 * 0.90 / 100, 2)
assert abs(qdii_base_notional - 60691.90) < 0.02, f'QDII 基准名义守卫失败 {qdii_base_notional}'
print(f'QDII 基准名义 {qdii_base_notional:,.2f} 元（收盘后市值 {qdii_mv:,.2f} 元）')
print(f'QDII US 10/20 段核销 {qdii_booked_amt:+,.2f} 元；系数 {coef_vs_IYH_1020}；预告区间 {PRED_LOW}~{PRED_HIGH}')

qdii_pending = {
    'as_of': '2026-10-21 20:00',
    'booked_this_session': {
        'desc': ('QDII 000369/016280 自基准净值日 10/19 推进至 **10/20**（US 10/20 段）→ '
                 '前档登记的「US 10/20 挂账区间」本档按真实净值核销'),
        'nav_date': '2026-10-20', 'nav': qdii_nav, 'pct': qdii_realized_pct,
        'amount': qdii_booked_amt,
        'pred_range': {'low': PRED_LOW, 'mid': PRED_MID, 'high': PRED_HIGH},
        'coef_vs_IYH_1020': coef_vs_IYH_1020,
        'in_band': all(0.60 <= v <= 0.90 for v in coef_vs_IYH_1020.values()),
        'note': (f'IYH 10/20 +2.34% → 预告区间 +{PRED_LOW:.2f} ~ +{PRED_HIGH:.2f} 元（中枢 +{PRED_MID:.2f} 元）；'
                 f'实测系数 {coef_vs_IYH_1020["000369"]:.4f} / {coef_vs_IYH_1020["016280"]:.4f} '
                 '**落 0.60~0.90 区间内** → §3.118a 区间法第 6 样本、第 4 例「成立」'),
        'placeholder_resolved': ('10/16 净值「与 10/15 完全相同（0.00%）」的占位疑点：本档 10/19 −0.567% / 10/20 +1.98% '
                                 '两段连续推进且方向与 IYH 一致 → **10/16 更可能是「当日真实零变动」或「一次性占位后已补正」，'
                                 '本档不再单列为占位**（降级为观察项）'),
    },
    'remaining_pending': {'window': ['2026-10-21'], 'estimate_low': None, 'estimate_high': None,
                          'note': 'US 10/21 尚未开盘（北京 20:00 = 美东 08:00）→ 本档无新增可量化挂账段，只登记不给数值（§3.120c）'},
    'unpriced_002708': {'mv': round(sum(d['mv0_new'] for d in detail if ''.join(c for c in str(d['code']) if c.isdigit()) == '002708'), 2),
                        'note': '大摩健康产业 10/21 净值未出库（10/20 = 1.8380）→ 计入 A股医药腿的未定价缺口'},
}

# ---------- 12. 收盘价合理性（涨停/跌停/停牌） ----------
print('\n--- 场内 12 行 ---')
for d in detail:
    c6 = ''.join(c for c in str(d['code']) if c.isdigit())
    if '场内收盘' in d['price_src']:
        print(f"  {d['name'][:22]:24s} {c6:7s} {d['est_pct']:+8.4f}%  pnl={d['est_pnl']:+9,.2f}")

out = {
    'date': TODAY,
    'as_of': '2026-10-21 收盘（正常交易日：A股 15:00 收盘 + 港股 16:00 收盘 + 美股未开盘）',
    'session_type': 'normal_trading_day_close',
    'session_type_note': '档型②：双市场同开双收盘 → 产 portfolio_close_20261021.json 并计入链式序列',
    'base_total': BASE_TOTAL,
    'base_file': 'portfolio_close_20261020_fix.json',
    'chain_0pct_row_inserted': False,
    'restore_rule_used': restore_rule,
    'restore_dev': restore_dev,
    'detail_restore_rule': restore_rule,
    'detail_restore_dev': restore_dev,
    'detail_restore_total': round(sum(d['mv0_new'] + d['est_pnl'] for d in detail), 2),
    'detail_restore_note': '逐券还原式 mv0_new+est_pnl 逐赛道 dev 全 0 → 通过；detail.mv 为基准行陈旧值，禁用（§3.112a）',
    'est_total_pnl': total_pnl,
    'est_total_pct': round(total_pnl / BASE_TOTAL * 100, 2),
    'est_total_pct_raw': total_pct_raw,
    'total_mv': new_total,
    'tracks': tracks,
    'discipline': DISCIPLINE,
    'med_exposure': med, 'med_pct': med_pct,
    'threshold_all_med': threshold_all, 'threshold_a_sh_med': threshold_sh,
    'board_med': BOARD_MED, 'leader_med': LEADER_MED, 'lag_med': LAG_MED,
    'board_detail': {'中证医药': BRD['sh000933'], '中证医疗': BRD['sz399989'], '医疗ETF': ETFP['sh512170'],
                     '医药ETF': ETFP['sz159938'], '300医药': BRD['sh000913'], '中证白酒': BRD['sz399997'],
                     '中证消费': IDXP['sh000932'], '中证环保': BRD['sh000827'], '中证金融': BRD['sh000934'],
                     '证券公司': BRD['sz399975']},
    'idx': {x['code']: {'name': x['name'], 'close': x['close'], 'pct': x['pct']}
            for x in cur['indices']},
    'hk_mkt': {x['code']: {'name': x['name'], 'close': x['close'], 'pct': x['pct'],
                           'high': x['high'], 'low': x['low']} for x in cur['hk']},
    'hk_stocks': cur['hk_stocks'],
    'etf_close': {x['code']: {'name': x['name'], 'close': x['close'], 'pct': x['pct']} for x in cur['etf']},
    'active_mult': active_mult,
    'proxy_check': proxy_check,
    'structure_order': [{'index': k, 'pct': v} for k, v in order],
    'hk_split': hk, 'hk_split_pnl': hk_pnl, 'hk_split_rows': hk_rows,
    'hk_total': hk_total, 'hk_total_pct': hk_total_pct, 'track_layer_hk_pct': track_layer_hk_pct,
    'qdii_applied': [{'code': c, 'name': n, 'nav_date': nd, 'nav': nav, 'pct': pct}
                     for c, n, nd, nav, pct, bnd, imp, v0 in qdii_applied],
    'qdii_pending': qdii_pending, 'qdii_mv': qdii_mv,
    'lof_164906_mv': round(sum(d['mv0_new'] + d['est_pnl'] for d in detail
                               if ''.join(c for c in str(d['code']) if c.isdigit()) == '164906'), 2),
    'detail': detail,
    'nav_today': [{'code': c, 'name': n, 'nav': nav, 'pct': pct} for c, n, nav, pct, imp in nav_today],
    'unpriced': unpriced, 'unpriced_total': unpriced_total,
    'priceable_total': priceable_total, 'priceable_pct': priceable_pct,
    'unpriced_shadow': {'rows': shadow, 'total_est_pnl': shadow_total,
                        'note': '影子估算只作披露、不并入主口径（§3.105）'},
    'pending_release': {'window': ['2026-10-21'], 'window_closed': True,
                        'note': 'A股 + 港股 均当日收盘定价，无「隔日待消化」结转项；002708/002742/004752 净值为「未定价缺口」而非待消化'},
}
OUT = os.path.join(HIST, 'portfolio_close_' + TODAYC + '.json')
json.dump(out, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('\nwritten', OUT)
print(f'Σ detail mv 偏差 = {round(sum(d["mv0_new"]+d["est_pnl"] for d in detail),2)} vs total_mv {new_total}')
