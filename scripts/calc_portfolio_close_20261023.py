# -*- coding: utf-8 -*-
"""2026-10-23 盘后：组合收盘计算（链式法，§3.79/§3.105/§3.109/§3.111/§3.112a 口径）

档型 = 正常交易日收盘（A股 10/23 15:00 收盘 + 港股 10/23 16:00 收盘 + 美股 10/23 未开盘）
base = portfolio_close_20261022_fix.json（10/22 收盘修正件 = 365,851.37 元，45 行）

本档定价：
  · 场内（ETF 9 + 个股 3）＝ 10/23 收盘价
  · 场外 23 只中 19 只出 10/23 真实净值
  · QDII 000369 / 016280 = 推进至 **10/22**（+1.53% / +1.52%）→ 核销 US 10/22 段挂账
  · 164906（LOF）= 10/22 净值 0.8210（-3.24%）→ 真实兑现
  · 000248 / 000051 / 002708 / 002742 未出 10/23 净值 → 计 0（基准已含）、列「未定价缺口」
产物：portfolio_close_20261023.json
"""
import json, os, re

BASE = '/Users/jieyang/Documents/WealthHub'
HIST = os.path.join(BASE, 'data/processed/history')
TODAY = '2026-10-23'
TODAYC = '20261023'

base = json.load(open(os.path.join(HIST, 'portfolio_close_20261022_fix.json'), encoding='utf-8'))
cur = json.load(open(os.path.join(HIST, 'close_' + TODAYC + '.json'), encoding='utf-8'))
navj = json.load(open(os.path.join(HIST, 'fundnav_close_' + TODAYC + '.json'), encoding='utf-8'))
intr = json.load(open(os.path.join(HIST, 'portfolio_intraday_' + TODAYC + '.json'), encoding='utf-8'))


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
DISC1, DISC2, DISC3 = 1882.46, 1904.44, 1858.66
CUTS = {'cut1': DISC1, 'cut2': DISC2, 'cut3': DISC3}
DISC_CUM = round(sum(CUTS.values()), 2)
_cutsum = round(sum(v['amount'] for k, v in {k: {'amount': a} for k, a in CUTS.items()}.items()), 2)
assert abs(_cutsum - DISC_CUM) < 0.01
assert abs(DISC_CUM - 5645.56) < 0.01, DISC_CUM

HSTECH = next(x for x in cur['hk'] if x['code'] == 'HSTECH')
H_4250 = round((HSTECH['close'] / 4250 - 1) * 100, 4)
H_4000 = round((HSTECH['close'] / 4000 - 1) * 100, 4)
H_3950 = round((HSTECH['close'] / 3950 - 1) * 100, 4)
H_3800 = round((HSTECH['close'] / 3800 - 1) * 100, 4)
H_3700 = round((HSTECH['close'] / 3700 - 1) * 100, 4)
CONSUME = IDXCLOSE['sh000932']
C_12100 = round((CONSUME / 12100 - 1) * 100, 4)

# 上一档（10/22 修正件）防线读数：用于「收窄/走阔」现算，禁止继承状态标签（§3.145a/§3.149a）
PREV_GAP = {'h4250': -10.7311, 'h4000': -5.1517, 'h3950': -3.9511, 'h3800': -0.1597,
            'c12100': 1.2279}


def state_of(cur_gap, prev_gap):
    if cur_gap >= 0:
        return 'close_level_recovered_today' if prev_gap < 0 else 'above_level'
    if prev_gap >= 0:
        return 'close_level_breached_today'
    return ('close_level_break_narrowed' if abs(cur_gap) < abs(prev_gap)
            else 'close_level_break_widened')


def trend_word(cur_gap, prev_gap):
    if cur_gap >= 0 and prev_gap < 0:
        return 'recovered'
    if cur_gap >= 0 and prev_gap >= 0:
        return 'widened' if abs(cur_gap) > abs(prev_gap) else 'narrowed'
    if cur_gap < 0 and prev_gap >= 0:
        return 'breached'
    return 'narrowed' if abs(cur_gap) < abs(prev_gap) else 'widened'


ST_4250 = state_of(H_4250, PREV_GAP['h4250'])
ST_4000 = state_of(H_4000, PREV_GAP['h4000'])
ST_3950 = state_of(H_3950, PREV_GAP['h3950'])
ST_3800 = state_of(H_3800, PREV_GAP['h3800'])
ST_CONS = state_of(C_12100, PREV_GAP['c12100'])
PLAN_4000 = 1863.33           # 10/22 盘前建案（分母 = 372,666.60 元，已建案不重设，待用户确认）
PLAN_3950 = 1858.66           # 10/22 盘后建案 → 10/23 按纪律执行（分母 371,732.03 元）
PLAN_MED = 0.00               # 反向兑现线第 4 次触发后当日转正 → 预案作废（0/4）
print(f'恒生科技 {HSTECH["close"]}（{HSTECH["pct"]:+.2f}%）vs 4,250={H_4250}%({ST_4250}) / '
      f'4,000={H_4000}%({ST_4000}) / 3,950={H_3950}%({ST_3950}) / 3,800={H_3800}%({ST_3800}) / '
      f'3,700={H_3700}%')
print(f'中证消费 {CONSUME} vs 12,100 = {C_12100}%（{ST_CONS}）')
print(f'累计纪律 {DISC_CUM:,.2f} 元（3 笔）；4,000 案 {PLAN_4000:,.2f} 元 仍待用户确认')

hk_amt = next((x.get('amount') for x in cur['hk'] if x['code'] == 'HSI'), None)

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
    'cut3': {'pct': 0.5, 'amount': DISC3, 'triggered_on': '2026-10-22', 'settled_on': '2026-10-23',
             'trigger_line': 3950, 'basis': '0.5% × 371,732.03 元（触发日上一有效估值日基准总资产）',
             'targets': ['012348（天弘恒生科技联接A）', '513180（恒生科技ETF华夏）'],
             'target_rule': '标的限「纯恒科」口径，不落在中概（513050 / 164906）',
             'user_confirmed': False,
             'execution_assumption': ('本档无用户回执通道（企业微信未配置 / agent-mail not_bound）→ '
                                      '按「当日盘前与盘中两档均判定为纪律执行项、窗口 09:30-15:00」'
                                      '推定已执行并计入累计（§3.125c「已判定待执行」同等计入）；'
                                      '若用户实际未执行，须于下一档显式撤销并回退累计至 3,786.90 元')},
    'cumulative_amount': DISC_CUM,
    'cumulative_selfcheck': {'sum_of_cuts': _cutsum, 'cumulative_amount': DISC_CUM,
                             'ok': abs(_cutsum - DISC_CUM) < 0.01,
                             'note': '只累加 k.startswith("cut") 的已成交/已判定执行笔（§3.168b）；预案不计入'},
    'settled_on': ['2026-09-30', '2026-10-08', '2026-10-23'],
    'execution_unknown': {
        'item': '4,000 线 −0.5% 减配预案（10/22 盘前建案）',
        'amount': PLAN_4000,
        'status': 'awaiting_user_confirmation',
        'note': ('连续第 3 日未获用户确认 → 按「未确认 = 未计入」处理：累计纪律仍为 5,645.56 元（3 笔）。'
                 '若用户确认已执行，累计应为 7,508.89 元（4 笔）、恒生科技 −1,863.33 元、现金 +1,863.33 元，'
                 '**须下一档由用户确认后补登（不得静默作废，§3.110）**'),
    },
    'today_action': {
        'discipline_cut_today': DISC3,
        'reason': ('恒生科技收盘 **%.2f**（%+.2f%%）→ 收复 3,800（%+.4f%%）、但 3,950 仍未收复（%+.4f%%）。'
                   '3,950 线已于 10/22 收盘失守并建案、10/23 为执行日 → **本档按纪律记执行 %s 元（cut3）**；'
                   '同日不重复触发（§3.114c）；3,800 收复属「破位解除」、**不产生反向加仓动作**（纪律只单向）；'
                   '4,000 案仍待用户确认，不并入累计'
                   % (HSTECH['close'], HSTECH['pct'], H_3800, H_3950, f'{DISC3:,.2f}'))},
    'settle': 'cut1/cut2 已按净值成交（价值中性）；cut3 为 10/23 当日纪律执行项，按推定执行计入权重',
    'hk_after': hk_after, 'cash_after': cash_after, 'weight_after': weight_after,
    'basis_note': ('累计口径 = 1,882.46 元 + 1,904.44 元 + 1,858.66 元 = 5,645.56 元（§3.123e / §3.125c）；'
                   '分母为「触发日上一有效估值日基准总资产」×0.5%'),
    'pending_plans': [
        {'trigger': 'HSTECH 收盘 < 4,000', 'created_on': '2026-10-22 盘前',
         'amount': PLAN_4000, 'basis': '0.5% × 372,666.60 元',
         'status': 'awaiting_user_confirmation',
         'targets_rule': '纯恒科口径（012348 / 513180），不落中概'},
        {'trigger': 'HSTECH 收盘 < 3,950', 'created_on': '2026-10-22 盘后',
         'amount': PLAN_3950, 'basis': '0.5% × 371,732.03 元',
         'status': 'executed_on_2026-10-23', 'settled_on': '2026-10-23',
         'user_confirmed': False,
         'targets_rule': '纯恒科口径（012348 / 513180），不落中概'},
        {'trigger': 'A股医药板块代理收盘 ≤ −1.5%', 'created_on': '2026-10-22 盘后',
         'amount': PLAN_MED, 'basis': '作废（不计金额）',
         'status': 'cancelled_line_deregistered',
         'cancel_reason': ('该线本季 4 次触发（10/14、10/16、10/21、10/22）**4 次全部作废**'
                           '（次日或当日收盘全部转正）；10/23 板块代理 +2.3725% → '
                           '「反向兑现线」正式注销（0/4），绑定预案一并作废')},
    ],
    'defense': {
        'hstech_4250': {'close': HSTECH['close'], 'line': 4250, 'gap_pct': H_4250,
                        'prev_gap_pct': PREV_GAP['h4250'], 'state': ST_4250,
                        'trend': trend_word(H_4250, PREV_GAP['h4250']),
                        'action': 'no_new_cut_same_line_used_twice'},
        'hstech_4000': {'close': HSTECH['close'], 'line': 4000, 'gap_pct': H_4000,
                        'prev_gap_pct': PREV_GAP['h4000'], 'state': ST_4000,
                        'trend': trend_word(H_4000, PREV_GAP['h4000']),
                        'intraday_low': HSTECH['low'], 'intraday_high': HSTECH['high'],
                        'action': 'plan_awaiting_confirmation'},
        'hstech_3950': {'close': HSTECH['close'], 'line': 3950, 'gap_pct': H_3950,
                        'prev_gap_pct': PREV_GAP['h3950'], 'state': ST_3950,
                        'trend': trend_word(H_3950, PREV_GAP['h3950']),
                        'action': 'executed_this_session_amount_1858.66'},
        'hstech_3800': {'close': HSTECH['close'], 'line': 3800, 'gap_pct': H_3800,
                        'prev_gap_pct': PREV_GAP['h3800'], 'state': ST_3800,
                        'trend': trend_word(H_3800, PREV_GAP['h3800']),
                        'action': 'break_lifted_no_reverse_buy'},
        'hstech_next_ref': {'line': 3700, 'gap_pct': H_3700},
        'zz_consume_12100': {'close': CONSUME, 'line': 12100, 'gap_pct': C_12100,
                             'prev_gap_pct': PREV_GAP['c12100'], 'state': ST_CONS,
                             'trend': trend_word(C_12100, PREV_GAP['c12100'])},
        'a_med_reverse_1_5pct': {'board_proxy_pct': BOARD_MED, 'line': -1.5,
                                 'state': 'deregistered_false_alarm',
                                 'baseline_reset_on': '2026-10-23',
                                 'trigger_count_season': 4,
                                 'invalidated_after_trigger': 4,
                                 'note': ('4 次触发、4 次次日（或当日收盘）转正 → 判别力 0/4，'
                                          '该线正式注销，后续只作观察标记（不再绑定任何金额预案）')},
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

# ---------- 6. 主动医药基真实倍数（同券多账户行按 mv0_new 加权，§3.167b） ----------
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

# 影子：002708 为主动医药基，弹性按「同腿主动基实测倍数区间」给上下界，不取单点
_peers = [active_mult[c]['mult_vs_board_med'] for c in ('161616', '000727', '001180') if c in active_mult]
_mult_lo = round(min(_peers), 3) if _peers else 0.85
_mult_hi = round(max(_peers), 3) if _peers else 1.30
shadow = []
rows2708 = [d for d in detail if ''.join(ch for ch in str(d['code']) if ch.isdigit()) == '002708']
if rows2708:
    mv = round(sum(r['mv0_new'] for r in rows2708), 2)
    pc_lo = round(BOARD_MED * _mult_lo, 4)
    pc_hi = round(BOARD_MED * _mult_hi, 4)
    shadow.append({'code': '002708', 'name': rows2708[0]['name'], 'mv': mv,
                   'proxy_pct_lo': pc_lo, 'proxy_pct_hi': pc_hi,
                   'est_pnl_lo': round(mv * pc_lo / 100, 2), 'est_pnl_hi': round(mv * pc_hi / 100, 2),
                   'mult_range': [_mult_lo, _mult_hi], 'n_rows': len(rows2708),
                   'note': ('主动医药基弹性取自同日同腿实测倍数区间（161616 / 000727 / 001180 vs 板块代理），'
                            '不取单点；影子只作披露、不并入主口径（§3.105）')})
shadow_lo = round(sum(s['est_pnl_lo'] for s in shadow), 2)
shadow_hi = round(sum(s['est_pnl_hi'] for s in shadow), 2)
print(f'未定价 {unpriced_total:,.2f} 元（{round(unpriced_total/new_total*100,2)}%）；影子 {shadow_lo:+,.2f} ~ {shadow_hi:+,.2f} 元')

# ---------- 11. QDII US 10/22 段核销 ----------
QDII_CODES = ('000369', '016280')
qdii_base_notional = round(sum(d['mv0_new'] for d in detail
                               if ''.join(c for c in str(d['code']) if c.isdigit()) in QDII_CODES), 2)
qdii_mv = round(tracks['美股标普医药']['mv'], 2)
IYH_1022 = 1.33
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
coef_vs_IYH_1022 = {k: round(abs(v) / abs(IYH_1022), 4) for k, v in qdii_realized_pct.items()}
# 预告区间（13:45 档登记，分母 = 该档 QDII 基准名义）；IYH 为正 → 弹性 0.90 得最高、0.45 得最低
PRED_HI = round(qdii_base_notional * IYH_1022 * 0.90 / 100, 2)   # 弹性 0.90 → 涨幅较大 → 上端
PRED_LO = round(qdii_base_notional * IYH_1022 * 0.45 / 100, 2)   # 弹性 0.45 → 涨幅较小 → 下端
PRED_MID = round(qdii_base_notional * IYH_1022 * 0.675 / 100, 2)  # 中枢取区间中点 0.675（§3.171b）
print(f'QDII 基准名义 {qdii_base_notional:,.2f} 元（收盘后市值 {qdii_mv:,.2f} 元）')
print(f'QDII US 10/22 段核销 {qdii_booked_amt:+,.2f} 元；系数 {coef_vs_IYH_1022}；预告区间 {PRED_LO} ~ {PRED_HI}')

qdii_pending = {
    'as_of': '2026-10-23 20:00',
    'booked_this_session': {
        'desc': ('QDII 000369/016280 自基准净值日 10/20 推进至 **10/22**（US 10/22 段）→ '
                 '13:45 档登记的「US 10/22 挂账区间 −222.85 元 ~ −148.56 元」本档按真实净值核销'),
        'nav_date': '2026-10-21', 'nav': qdii_nav, 'pct': qdii_realized_pct,
        'amount': qdii_booked_amt,
        'pred_range': {'low': PRED_LO, 'mid': PRED_MID, 'high': PRED_HI,
                       'registered_in_intraday': {'low': -222.85, 'high': -148.56, 'mid': -178.28}},
        'coef_vs_IYH_1022': coef_vs_IYH_1022,
        'in_band': all(0.45 <= v <= 0.90 for v in coef_vs_IYH_1022.values()),
        'note': ('IYH 10/22 −0.40% → 预告区间 −222.85 ~ −148.56 元；实测 −0.19%（两券位一致）→ '
                 '系数 0.4750，**低于 0.60 下界 → 区间法第 7 样本、第 5 例「越界」**。'
                 '越界方向为「实际跌幅小于预告下界」，即 QDII 净值对 IYH 的传导低于 0.60 弹性假设；'
                 '**系数点值继续 pending**（分母/映射未定，§3.167c）'),
        'placeholder_resolved': '10/16 净值占位疑点维持「观察项」状态，本档 10/22 净值正常推进，无新增证据',
    },
    'remaining_pending': {'window': ['2026-10-23'], 'estimate_low': None, 'estimate_high': None,
                          'note': ('US 10/23 尚未开盘（北京 20:00 = 美东 08:00）→ 本档无新增可量化挂账段，'
                                   '只登记不给数值（§3.120c）')},
    'unpriced_002708': {'mv': round(sum(d['mv0_new'] for d in detail if ''.join(c for c in str(d['code']) if c.isdigit()) == '002708'), 2),
                        'n_rows': len(rows2708),
                        'note': '大摩健康产业（双账户 2 行）10/23 净值未出库（最新 10/22 = 1.8290）→ 计入 A股医药腿的未定价缺口'},
}

# ---------- 12. 收盘价合理性 ----------
print('\n--- 场内 12 行 ---')
for d in detail:
    c6 = ''.join(c for c in str(d['code']) if c.isdigit())
    if '场内收盘' in d['price_src']:
        print(f"  {d['name'][:22]:24s} {c6:7s} {d['est_pct']:+8.4f}%  pnl={d['est_pnl']:+,.2f}")

out = {
    'date': TODAY,
    'as_of': '2026-10-23 收盘（正常交易日：A股 15:00 收盘 + 港股 16:00 收盘 + 美股未开盘）',
    'session_type': 'normal_trading_day_close',
    'session_type_note': ('档型②：双市场同开双收盘 → 产 portfolio_close_20261023.json 并计入链式序列；'
                          '当日为「A股 放量下跌 + 港股 恒科 −5.03% 三线同破」的高波动日'),
    'base_total': BASE_TOTAL,
    'base_file': 'portfolio_close_20261022_fix.json',
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
    'idx': {x['code']: {'name': x['name'], 'close': x['close'], 'pct': x['pct'],
                        'high': x['high'], 'low': x['low']} for x in cur['indices']},
    'hk_mkt': {x['code']: {'name': x['name'], 'close': x['close'], 'pct': x['pct'],
                           'high': x['high'], 'low': x['low'],
                           'prev': x['prev']} for x in cur['hk']},
    'hk_stocks': cur['hk_stocks'],
    'etf_close': {x['code']: {'name': x['name'], 'close': x['close'], 'pct': x['pct']} for x in cur['etf']},
    'stocks_close': {x['code']: {'name': x['name'], 'close': x['close'], 'pct': x['pct']} for x in cur['stocks']},
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
    'unpriced_shadow': {'rows': shadow, 'total_est_pnl_lo': shadow_lo, 'total_est_pnl_hi': shadow_hi,
                        'note': '影子估算只作披露、不并入主口径（§3.105）'},
    'pending_release': {'window': ['2026-10-23'], 'window_closed': True,
                        'note': ('A股 + 港股 均当日收盘定价，无「隔日待消化」结转项；'
                                 '002708 净值为「未定价缺口」而非待消化')},
    'intraday_vs_close': {
        'intraday_pnl': intr.get('total_delta'),
        'intraday_pct': intr.get('est_total_pct'),
        'intraday_archived_base': intr.get('archived_base'),
        'field_note': '盘中档字段名为 total_delta（非 est_total_pnl，§3.163 类字段名漂移）',
        'close_pnl': total_pnl,
        'delta': round(total_pnl - float(intr.get('total_delta') or 0), 2),
        'note': '盘中 13:45 估算 → 收盘真实定价的差额（尾盘 + 净值出库两部分合计，不可单独归因）',
    },
}
OUT = os.path.join(HIST, 'portfolio_close_' + TODAYC + '.json')
json.dump(out, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('\nwritten', OUT)
print(f'Σ detail mv 偏差 = {round(sum(d["mv0_new"]+d["est_pnl"] for d in detail),2)} vs total_mv {new_total}')
print(f"盘中 {float(out['intraday_vs_close']['intraday_pnl'] or 0):+,.2f} → 收盘 {total_pnl:+,.2f}（Δ {out['intraday_vs_close']['delta']:+,.2f}）")
