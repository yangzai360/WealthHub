# -*- coding: utf-8 -*-
"""2026-10-20 盘后：组合收盘计算（链式法，§3.79/§3.105/§3.109/§3.111/§3.112a 口径）

档型 = **正常交易日收盘**（A股 10/20 15:00 收盘 + 港股 10/20 复市 16:00 收盘 + 美股 10/20 未开盘）
base = portfolio_close_20261019_fix.json（10/19 收盘修正件 = 372,163.96 元）

定价覆盖（本档为「全定价日」，除 2 只场外联接净值未推进外全部真实价格/净值）：
  · 场内（ETF/个股 12 行）= 10/20 收盘价
  · 场外 23 只中 18 只出 10/20 真实净值
  · QDII 000369 / 016280 = 净值自 10/16 推进至 **10/19**（−0.567% / −0.580%）→ 真实兑现
  · 164906（LOF）= 10/19 净值 0.8727 → 真实兑现（+0.02%）
  · 012348（天弘恒生科技联接A）= 净值仍停 10/19 → 计 0（基准已含），**未定价缺口**
产物：portfolio_close_20261020.json
"""
import json, os, re

BASE = '/Users/jieyang/Documents/WealthHub'
HIST = os.path.join(BASE, 'data/processed/history')
TODAY = '2026-10-20'
TODAYC = '20261020'
PREV = '2026-10-19'

base = json.load(open(os.path.join(HIST, 'portfolio_close_20261019_fix.json'), encoding='utf-8'))
cur = json.load(open(os.path.join(HIST, 'close_' + TODAYC + '.json'), encoding='utf-8'))
navj = json.load(open(os.path.join(HIST, 'fundnav_close_' + TODAYC + '.json'), encoding='utf-8'))


# ---------- 0. 基准还原式：机器可验证判据（§3.111 / §3.112a） ----------
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

# ---------- 1. 价格表（10/20 收盘） ----------
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


# ---------- 2. 板块/指数（10/20 收盘） ----------
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
pnl_best = pnl_worst = total_pnl

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

# ---------- 4. 纪律减仓台账（累计两笔已成交；本档判定恒科 4,250 已破位在案、4,000 观察线未破 → 无新增动作） ----------
DISC1 = 1882.46
DISC2 = 1904.44
DISC_CUM = round(DISC1 + DISC2, 2)
assert abs(DISC_CUM - 3786.90) < 0.01
HSTECH = next(x for x in cur['hk'] if x['code'] == 'HSTECH')
H_4250 = round((HSTECH['close'] / 4250 - 1) * 100, 4)
H_4000 = round((HSTECH['close'] / 4000 - 1) * 100, 4)
CONSUME = IDXCLOSE['sh000932']
C_12100 = round((CONSUME / 12100 - 1) * 100, 4)
print(f'恒生科技 {HSTECH["close"]}（{HSTECH["pct"]:+.2f}%）vs 4,250 = {H_4250}% / vs 4,000 = {H_4000}%')
print(f'中证消费 {CONSUME} vs 12,100 = {C_12100}%')

weight_after = {k: v['mv'] / new_total * 100 for k, v in tracks.items()}
weight_after['恒生科技'] -= DISC_CUM / new_total * 100
weight_after['现金'] += DISC_CUM / new_total * 100
weight_after = {k: round(v, 2) for k, v in weight_after.items()}
assert abs(sum(weight_after.values()) - 100) < 0.05, '减仓后权重合计守卫失败'
hk_after = round(tracks['恒生科技']['mv'] - DISC_CUM, 2)
cash_after = round(tracks['现金']['mv'] + DISC_CUM, 2)
assert abs(weight_after['恒生科技'] - hk_after / new_total * 100) < 0.02, '纪律后恒科权重与市值不自洽'
assert abs(weight_after['现金'] - cash_after / new_total * 100) < 0.02, '纪律后现金权重与市值不自洽'
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
                     'reason': ('恒生科技 **4,250 破位在案**（收盘 4,045.91 / −4.80%，较 10/16 stale 读数 −3.3355% 扩大），'
                                '**同一防线本季已触发 2 次（9/29、10/2）、同日只触发一次 → 本档不重复减仓（§3.114c）**；'
                                '**4,000 观察线未破**（+1.15%，日内低 4,026.90）→ 新防线未触发；'
                                '中证消费 12,422.96（距 12,100 +2.67%）安全；'
                                f'A股医药反向线新基线起算（板块代理 {BOARD_MED}% > −1.5%）→ 未触发')},
    'settle': '两笔均已按净值成交（价值中性，P&L 口径不变）；本档只重算纪律后权重',
    'hk_after': hk_after, 'cash_after': cash_after, 'weight_after': weight_after,
    'basis_note': ('累计口径 = 已成交 1,882.46 元 + 已成交 1,904.44 元（§3.123e / §3.125c）；'
                   '分母为「上一有效估值日基准总资产」×0.5%'),
    'defense': {
        'hstech_4250': {'close': HSTECH['close'], 'line': 4250, 'gap_pct': H_4250,
                        'state': 'close_level_break_widened', 'action': 'no_new_cut_same_line_used_twice'},
        'hstech_4000': {'close': HSTECH['close'], 'line': 4000, 'gap_pct': H_4000,
                        'state': 'above_observation_line', 'intraday_low': HSTECH['low']},
        'zz_consume_12100': {'close': CONSUME, 'line': 12100, 'gap_pct': C_12100,
                             'state': 'above_lower_line'},
        'a_med_reverse_1_5pct': {'board_proxy_pct': BOARD_MED, 'line': -1.5,
                                 'state': 'not_triggered', 'baseline_reset_on': '2026-10-19'},
    },
}

# ---------- 5. 港股暴露双层拆解（§3.108 条款 23） ----------
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

# ---------- 6. 主动医药基真实倍数 ----------
active_mult = {}
for c, nm in (('002708', '大摩健康产业A'), ('161616', '融通医疗保健'), ('000727', '融通健康产业'),
              ('001180', '广发医药卫生'), ('001551', '天弘医药100C')):
    rows = [d for d in detail if ''.join(ch for ch in str(d['code']) if ch.isdigit()) == c]
    if rows:
        active_mult[c] = {'name': nm, 'real_pct': rows[0]['est_pct'],
                          'mult_vs_board_med': round(rows[0]['est_pct'] / BOARD_MED, 3) if BOARD_MED else None,
                          'mult_vs_300med': round(rows[0]['est_pct'] / LEADER_MED, 3) if LEADER_MED else None,
                          'estimated': False}

# ---------- 7. 被动联接类偏差检验（§3.103） ----------
HSI_PCT = next((x['pct'] for x in cur['hk'] if x['code'] == 'HSI'), None)
proxy_check = {}
for c, idx, lab in (('012323', BRD['sz399989'], '中证医疗'), ('000051', IDXP['sh000300'], '沪深300'),
                    ('000071', HSI_PCT, '恒生指数(跨市场参考,§3.112i 禁互验)'),
                    ('001551', BRD['sh000933'], '中证医药(近似代理·中证医药100未入库)'),
                    ('001180', BRD['sh000933'], '中证医药(近似代理·中证医药卫生未入库)'),
                    ('110020', IDXP['sh000300'], '沪深300'),
                    ('012348', HSTECH['pct'], '恒生科技(跨市场参考,§3.112i 禁互验)')):
    rows = [d for d in detail if ''.join(ch for ch in str(d['code']) if ch.isdigit()) == c]
    if rows and isinstance(idx, float):
        proxy_check[c] = {'real': rows[0]['est_pct'], 'index': idx, 'label': lab,
                          'dev': round(rows[0]['est_pct'] - idx, 4)}

# ---------- 8. 医药敞口与门槛（§3.98 方程解法） ----------
med = round(tracks['A股医药']['mv'] + tracks['美股标普医药']['mv'], 2)
A, B = med, new_total - med
threshold_all = round(((0.40 / 0.60) * B / A - 1) * 100, 2)
A_sh = tracks['A股医药']['mv']
threshold_sh = round((((0.40 / 0.60) * B - (med - A_sh)) / A_sh - 1) * 100, 2)
med_pct = round(med / new_total * 100, 2)

# ---------- 9. 结构顺序 ----------
order = sorted([('300医药', BRD['sh000913']), ('中证医药', BRD['sh000933']), ('中证医疗', BRD['sz399989'])],
               key=lambda y: -y[1])

# ---------- 10. 未定价 / 待消化 ----------
unpriced, unpriced_total = [], 0.0
for d in detail:
    if d['price_src'].startswith(('净值未推进', '数据暂缺')):
        unpriced.append({'code': ''.join(c for c in str(d['code']) if c.isdigit()), 'name': d['name'],
                         'mv': round(d['mv0_new'], 2), 'reason': d['price_src']})
        unpriced_total += d['mv0_new']
unpriced_total = round(unpriced_total, 2)
priceable_total = round(new_total - unpriced_total, 2)
priceable_pct = round(priceable_total / new_total * 100, 2)

# 未定价缺口影子估算（仅披露、不并入主口径）：012348 按恒生科技 −1.52%×0.85（联接跟踪折扣）、164906 按中概权重股均值
shadow = []
d12348 = round(sum(x['mv0_new'] for x in detail
                   if ''.join(c for c in str(x['code']) if c.isdigit()) == '012348'), 2)
d164906 = round(sum(x['mv0_new'] for x in detail
                    if ''.join(c for c in str(x['code']) if c.isdigit()) == '164906'), 2)
shadow.append({'code': '012348', 'mv': d12348, 'proxy_pct': round(HSTECH['pct'] * 0.85, 2),
               'est_pnl': round(d12348 * HSTECH['pct'] * 0.85 / 100, 2),
               'note': '恒生科技 −1.52% × 0.85（联接跟踪折扣）；实际净值 10/21 出库'})
d000051 = round(sum(x['mv0_new'] for x in detail
                     if ''.join(c for c in str(x['code']) if c.isdigit()) == '000051'), 2)
shadow.append({'code': '000051', 'mv': d000051, 'proxy_pct': round(IDXP['sh000300'] * 0.98, 2),
               'est_pnl': round(d000051 * IDXP['sh000300'] * 0.98 / 100, 2),
               'note': '沪深300 −0.54% × 0.98（联接跟踪折扣）；10/20 净值未出库'})
shadow.append({'code': '164906', 'mv': d164906, 'proxy_pct': 0.0,
               'est_pnl': 0.0,
               'note': 'LOF 净值 T+1，10/20 净值未出库；其 10/19 净值 +0.02% 已在本档兑现'})
shadow_total = round(sum(s['est_pnl'] for s in shadow), 2)

# ---------- 11. QDII 挂账：US 10/19 段按真实净值核销 ----------
QDII_CODES = ('000369', '016280')
qdii_mv = round(tracks['美股标普医药']['mv'], 2)
IYH_1019 = -0.57
IYH_1016 = -0.38
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
coef_vs_1019 = {k: round(abs(v) / abs(IYH_1019), 4) for k, v in qdii_realized_pct.items()}
coef_vs_1016 = {k: round(abs(v) / abs(IYH_1016), 4) for k, v in qdii_realized_pct.items()}
qdii_pending = {
    'as_of': '2026-10-20 20:00',
    'booked_this_session': {
        'desc': ('QDII 000369/016280 自基准净值日 10/16 推进至 **10/19**（覆盖 10/16 → 10/19 共 1 个美股交易日区间）'
                 '＝ 前档登记的「US 10/19 挂账段」本档按真实净值核销'),
        'nav_date': '2026-10-19', 'nav': qdii_nav, 'pct': qdii_realized_pct,
        'amount': qdii_booked_amt,
        'pred_range': {'low': -313.14, 'mid': -250.51, 'high': -208.76},
        'coef_vs_IYH_1019': coef_vs_1019, 'coef_vs_IYH_1016': coef_vs_1016,
        'mapping_ambiguity': ('净值日 10/19 若映射 US 10/19（IYH −0.57%）→ 系数 '
                              + str(list(coef_vs_1019.values()))
                              + '；若映射 US 10/16（IYH −0.38%）→ 系数 '
                              + str(list(coef_vs_1016.values()))
                              + '。**两种映射不可能同时成立 → 传导系数继续 `pending`**（§3.118a）'),
        'suspect_placeholder': {c: (c in qdii_realized_pct) for c in QDII_CODES},
        'note': ('⚠️ 基准行 10/16 净值 2.6460 / 2.6000 与 10/15 完全相同（0.00%），而 IYH 同期 −0.38% → '
                 '**10/16 净值疑为占位**（10/19 档已登记 `suspect_placeholder`）。本档新净值 −0.567% / −0.580% '
                 '若按 IYH 10/19 计系数 ≈ 1.00（越区间上界 0.90）、若解释为「弥补 10/16 占位」则真实两日复合应为 '
                 '−0.38%×0.72 + −0.57% ≈ −0.84% → **两种口径均越界**'),
    },
    'remaining_pending': {
        'window': ['2026-10-20'],
        'estimate_low': None, 'estimate_high': None,
        'note': 'US 10/20 尚未开盘（北京 20:00 = 美东 08:00）→ 本档**无新增可量化挂账段**，按规则只登记不给数值（§3.120c）',
    },
    'unpriced_012348': {'mv': d12348, 'shadow_est_pnl': round(d12348 * HSTECH['pct'] * 0.85 / 100, 2),
                        'note': '场外港股联接净值 10/20 未出库 → 计入恒生科技腿的「未定价缺口」'},
    'unpriced_000051': {'mv': d000051, 'shadow_est_pnl': round(d000051 * IDXP['sh000300'] * 0.98 / 100, 2),
                        'note': '沪深300联接 10/20 净值未出库 → 计入其他/宽基的「未定价缺口」'},
}

# ---------- 12. 输出 ----------
out = {
    'date': TODAY, 'as_of': '2026-10-20 收盘（正常交易日：A股 15:00 收盘 + 港股复市 16:00 收盘 + 美股未开盘）',
    'session_type': 'normal_trading_day_close',
    'session_type_note': '档型：正常交易日收盘（A股 + 港股 同开）→ 产 portfolio_close_20261020.json 并计入链式序列',
    'base_total': BASE_TOTAL, 'base_file': 'portfolio_close_20261019_fix.json',
    'chain_0pct_row_inserted': False,
    'restore_rule_used': restore_rule, 'restore_dev': restore_dev,
    'detail_restore_rule': restore_rule,
    'detail_restore_dev': max(abs(x) for x in restore_dev),
    'detail_restore_total': tot,
    'detail_restore_note': '逐券还原式 = mv0_new + est_pnl（机器判据：mv0+pnl 偏差 %s 元被排除）' % dev_all['mv0+pnl'],
    'est_total_pnl': total_pnl, 'est_total_pct': round(total_pnl / BASE_TOTAL * 100, 2),
    'est_total_pct_raw': total_pct_raw,
    'est_total_pnl_best': pnl_best, 'est_total_pnl_worst': pnl_worst,
    'est_total_pnl_high': pnl_best, 'est_total_pnl_low': pnl_worst,
    'band_note': '本档为「准全定价日」——3 行未定价（012348 双行 / 000051，notional 23,006.75 元 = 6.17%），其余全部真实价格/净值 → 上下界 = 点值，未定价缺口另见 unpriced_shadow',
    'total_mv': new_total, 'tracks': tracks,
    'discipline': DISCIPLINE,
    'med_exposure': med, 'med_pct': med_pct,
    'threshold_all_med': threshold_all, 'threshold_a_sh_med': threshold_sh,
    'board_med': BOARD_MED, 'leader_med': LEADER_MED, 'lag_med': LAG_MED,
    'board_detail': {'中证医药': BRD['sh000933'], '中证医疗': BRD['sz399989'],
                     '医疗ETF': ETFP['sh512170'], '医药ETF': ETFP['sz159938'],
                     '300医药': BRD['sh000913'], '中证白酒': BRD['sz399997']},
    'idx': {k: {'name': x['name'], 'close': x['close'], 'pct': x['pct']}
            for k, x in [(x['code'], x) for x in cur['indices']]},
    'hk_mkt': {x['code']: {'name': x['name'], 'close': x['close'], 'pct': x['pct'],
                           'high': x['high'], 'low': x['low'], 'date_field': x.get('date_field'),
                           'time': x.get('time')} for x in cur['hk']},
    'hk_stocks': cur['hk_stocks'],
    'active_mult': active_mult, 'proxy_check': proxy_check,
    'structure_order': [{'index': a, 'pct': b} for a, b in order],
    'hk_split': hk, 'hk_split_pnl': hk_pnl, 'hk_split_rows': hk_rows,
    'hk_total': hk_total, 'hk_total_pct': hk_total_pct,
    'track_layer_hk_pct': track_layer_hk_pct,
    'qdii_applied': [{'code': c, 'name': n, 'nav_date': nd, 'nav': nav, 'pct': pct}
                     for c, n, nd, nav, pct, bnd, imp, v0 in qdii_applied],
    'qdii_pending': qdii_pending, 'qdii_mv': qdii_mv,
    'lof_164906_mv': d164906,
    'detail': detail, 'nav_today': [{'code': c, 'name': n, 'nav': v, 'pct': p} for c, n, v, p, imp in nav_today],
    'unpriced': unpriced, 'unpriced_total': unpriced_total,
    'priceable_total': priceable_total, 'priceable_pct': priceable_pct,
    'unpriced_shadow': {'rows': shadow, 'total_est_pnl': shadow_total,
                        'note': '影子估算只作披露、不并入主口径'},
    'pending_release': {
        'window': ['2026-10-20'], 'window_closed': True, 'refreshed': True,
        'closed_on': '2026-10-20',
        'note': ('港股 10/20 复市且已收盘 → 本档**当日定价已全部实现**（场内 ETF 用 A股 收盘价、'
                 '000071 用 10/20 真实净值 −1.25%），无「待消化」结转项；'
                 '012348 / 164906 净值未出库 → 单列为「未定价缺口」而非待消化'),
    },
    'fix_applied': ['portfolio_close_20261019_fix.json'],
    'note': ('正常交易日收盘档；基准 = 10/19 修正件 372,163.96 元；'
             '本档新增真实定价：A股 全量收盘 + 港股复市收盘 + QDII 10/19 净值 + 164906 LOF 10/19 净值；'
             '未定价 2 只 3 行（012348 双账户 / 000051，notional %s 元，占 %.2f%%）' % (f'{unpriced_total:,.2f}', 100 - priceable_pct)),
}
json.dump(out, open(os.path.join(HIST, 'portfolio_close_' + TODAYC + '.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
print('已保存 portfolio_close_20261020.json')
print('赛道:', {k: (v['mv'], v['pnl'], v['pct_of_total']) for k, v in tracks.items()})
print('医药敞口', med_pct, '门槛', threshold_all, '/', threshold_sh)
print('港联系', hk_total, hk_total_pct, hk)
print('QDII 兑现', qdii_booked_amt, qdii_realized_pct, 'coef', coef_vs_1019, coef_vs_1016)
print('未定价', unpriced_total, '影子', shadow_total)
print('未出净值:', [(c, n, nd) for c, n, nd, why in missing])
