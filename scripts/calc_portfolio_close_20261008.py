# -*- coding: utf-8 -*-
"""2026-10-08 盘后：组合收盘估算（链式法，§3.79/§3.97/§3.105/§3.109/§3.111/§3.112a/§3.112i 口径）

base = portfolio_close_20260930_fix.json（9/30 修正收盘 = 380,888.29 元）
  §3.111/§3.112a 强制：逐券还原式由「机器可验证判据」选出（track 级 Σ(mv0_new+pnl) == tracks[].mv）

本档定价覆盖（10/8 正常交易日 · A股 长假后复市首日 + 港股正常交易日；A股 15:00 / 港股 16:00 收盘）：
  · 场内（ETF/个股 10 行）= 10/8 收盘价（hq 直连）
  · 场外 19 只出 10/8 真实净值（含 161616 −3.08% / 000727 −2.40% / 002708 −3.19% 三只 A股主动医药基）
  · 002742（债券 9.4 元）/ 004752（0.95 元）→ 极小值，按净值计
  · 000071 / 012348（场外港股联接，4 行）= 10/8 净值**一次性体现 9/30→10/8 跨长假累积**（5 个港股交易日）
  · 000369 / 016280（QDII 广发全球医疗 A/C，4 行）= 最新净值日 9/30 > 基准净值日 9/28
        → §3.105 真实兑现（挂账口径按 pending.qdii_decision「以基准净值日 9/28 为起点回填」执行）
  · 164906（交银海外互联 LOF，2 行）= 最新净值日 9/30 > 基准净值日 9/29 → 真实兑现

⚠️ 10/8 执行「恒生科技 0.5% 纪律减仓 1,904.44 元」（10/2 收盘级破位判定、执行日 10/8）：
   按「全额持有参与 10/8 收益（P&L 口径不变）+ 减仓后权重单列」处理（价值中性，总额不变）
输出：portfolio_close_20261008.json
"""
import json, os, re

BASE = '/Users/jieyang/Documents/WealthHub'
HIST = os.path.join(BASE, 'data/processed/history')
TODAY = '2026-10-08'
TODAYC = TODAY.replace('-', '')

base = json.load(open(os.path.join(HIST, 'portfolio_close_20260930_fix.json'), encoding='utf-8'))
cur = json.load(open(os.path.join(HIST, 'close_' + TODAYC + '.json'), encoding='utf-8'))
navj = json.load(open(os.path.join(HIST, 'fundnav_close_' + TODAYC + '.json'), encoding='utf-8'))


# ---------- 0. 基准还原式：机器可验证判据（§3.111 / §3.112a） ----------
def basis(x):
    """行级价值基准 = mv0_new + est_pnl（基准日修正后的收盘价值）"""
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
if abs(round(sum(x['est_pnl'] for x in base['detail']), 2) - base['est_total_pnl']) >= 1.5:
    raise SystemExit('基准 Σpnl 守卫失败（§3.109）')
print(f'✅ Σ tracks.pnl 守卫通过（{base["est_total_pnl"]:+,.2f} 元）')

# ---------- 1. 价格表（10/8 收盘） ----------
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
    """§3.105：基准已含哪一日净值必须从 price_src 解析，禁止用固定日期常量。
    优先级：① 「净值 <YYYY-MM-DD>」（含「新净值」，= 基准档实际计入的净值日）
            ② 「净值 M/D」（短日期记法）
            ③ 「nd=YYYY-MM-DD」/「基准(为)? YYYY-MM-DD」（兜底，用于「净值未推进」类文案）"""
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


# ---------- 2. 板块/指数（10/8 收盘） ----------
BRD = {x['code']: x['pct'] for x in cur['boards']}
ETFP = {x['code']: x['pct'] for x in cur['etf']}
IDXP = {x['code']: x['pct'] for x in cur['indices']}
BOARD_MED = round((BRD['sh000933'] + BRD['sz399989'] + ETFP['sh512170'] + ETFP['sz159938']) / 4, 4)
LEADER_MED = BRD['sh000913']            # 300医药
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
        src = f'场内收盘 10/8 {PX[code6]}（基准 {round(imp,4)}）'
    elif code6 in NAV:
        nd, nav = NAV[code6]
        imp = v0 / sh
        base_nd = parse_base_nav_date(x.get('price_src', ''))
        if nd == TODAY:
            pct = round((nav / imp - 1) * 100, 4)
            src = f'净值 10/8 ({nav})，基准净值日 {base_nd}'
            nav_today.append((code6, x['name'], nav, pct, round(imp, 4)))
        elif base_nd and nd > base_nd:
            pct = round((nav / imp - 1) * 100, 4)
            src = (f'新净值 {nd} ({nav}) 真实兑现（基准为 {base_nd}，跨度含长假）'
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
# 本档全部为真实价格/真实净值（无代理估算）→ 上下界 = 点值
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

# ---------- 4. 纪律减仓（cut1 已成交 + cut2 今日成交） ----------
DISC1 = 1882.46
DISC2 = 1904.44
DISC_CUM = round(DISC1 + DISC2, 2)
assert abs(DISC_CUM - 3786.90) < 0.01
weight_after = {k: v['mv'] / new_total * 100 for k, v in tracks.items()}
weight_after['恒生科技'] -= DISC_CUM / new_total * 100
weight_after['现金'] += DISC_CUM / new_total * 100
weight_after = {k: round(v, 2) for k, v in weight_after.items()}
assert abs(sum(weight_after.values()) - 100) < 0.05, '减仓后权重合计守卫失败'
DISCIPLINE = {
    'cut1': {'pct': 0.5, 'amount': DISC1, 'triggered_on': '2026-09-29', 'settled_on': '2026-09-30'},
    'cut2': {'pct': 0.5, 'amount': DISC2, 'triggered_on': '2026-10-02', 'settled_on': TODAY,
             'is_today': True, 'targets': ['012348（天弘恒生科技联接A）', '513180（恒生科技ETF华夏）']},
    'cumulative_amount': DISC_CUM,
    'settle': '按 10/8 净值成交（价值中性，P&L 口径不变）',
    'weight_after': weight_after,
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
proxy_check = {}
for c, idx, lab in (('012323', BRD['sz399989'], '中证医疗'), ('000051', IDXP['sh000300'], '沪深300'),
                    ('000071', IDXP['sh000300'], '沪深300(A股口径,参考)'), ('001551', BRD['sh000933'], '中证医药'),
                    ('001180', BRD['sh000933'], '中证医药'), ('110020', IDXP['sh000300'], '沪深300')):
    rows = [d for d in detail if ''.join(ch for ch in str(d['code']) if c) == c]
    if rows and isinstance(idx, float):
        proxy_check[c] = {'real': rows[0]['est_pct'], 'index': idx, 'label': lab,
                          'dev': round(rows[0]['est_pct'] - idx, 4)}

# ---------- 8. 医药敞口与门槛（§3.98 方程解法） ----------
med = round(tracks['A股医药']['mv'] + tracks['美股标普医药']['mv'], 2)
A, B = med, new_total - med
threshold_all = round(((0.40 / 0.60) * B / A - 1) * 100, 2)
A_sh = tracks['A股医药']['mv']
threshold_sh = round((((0.40 / 0.60) * B - (med - A_sh)) / A_sh - 1) * 100, 2)

# ---------- 9. 结构顺序（300医药 / 中证医药 / 中证医疗） ----------
order = sorted([('300医药', BRD['sh000913']), ('中证医药', BRD['sh000933']), ('中证医疗', BRD['sz399989'])],
               key=lambda y: -y[1])

# ---------- 10. 待消化收口（长假港股腿 → 10/8 一次性兑现） ----------
prev_pending = json.load(open(os.path.join(HIST, 'portfolio_pending_20261007.json'), encoding='utf-8'))
carry = (json.load(open(os.path.join(HIST, 'portfolio_preopen_20261008.json'), encoding='utf-8'))
         .get('hk_leg_pending_carryover', {}))
HSTECH_0930, HSTECH_1008 = 4253.89, 4073.38
hstech_holiday_cum = round(((4073.38 / 4253.89) - 1) * 100, 4)   # 含 10/8 单日
hstech_holiday_only = -1.4050                                     # 10/2~10/7 四段几何复合（前档口径 −1.3963%）
pending_release = {
    'source_file': 'portfolio_pending_20261007.json',
    'window': ['2026-10-02', '2026-10-05', '2026-10-06', '2026-10-07'],
    'window_estimate_low': carry.get('total_low', -973.41),
    'window_estimate_high': carry.get('total_high', -758.58),
    'window_estimate_mid_proxy_avg': carry.get('mid_proxy_avg', -866.14),
    'consumed_on': TODAY,
    'consume_rule': ('§3.112i：场外港股联接（000071 / 012348）10/8 净值**一次性体现 9/30→10/8 跨长假累积**'
                     '（5 个港股交易日）→ 长假「待消化」窗口随净值发布自动收口；本档按真实净值计入，'
                     '不再单列待消化金额'),
    'realized_by_row': [
        {'code': r['code'], 'name': r['name'], 'seg': r['seg'], 'pct': r['pct'], 'pnl': r['pnl']}
        for r in hk_rows],
    'hstech_full_window_pct': hstech_holiday_cum,
    'hstech_full_window_note': (f'HSTECH 9/30 收 4,253.89 → 10/8 收 4,073.38 = {hstech_holiday_cum:+.4f}%'
                                f'（长假四段 {hstech_holiday_only:+.4f}% + 10/8 单日 −2.89%）；'
                                f'012348 实际净值 −4.0517%、513180 实际 −3.3708%'),
    'closed': True,
}

# ---------- 11. QDII 挂账更新（本档回填 US 9/29+9/30，余 US 10/1~10/7 待观测） ----------
qdii_mv = round(sum(d['mv0_new'] for d in detail
                    if ''.join(c for c in str(d['code']) if c.isdigit()) in ('000369', '016280')), 2)
IYH = {'2026-10-01': -1.621, '2026-10-02': 0.0, '2026-10-05': 0.7244, '2026-10-06': -0.3385,
       '2026-10-07': 0.8915}
comp = 1.0
for v in IYH.values():
    comp *= (1 + v / 100)
comp_pct = round((comp - 1) * 100, 4)
notional = round(comp_pct / 100 * qdii_mv, 2)
qdii_pending = {
    'as_of': '2026-10-08 20:00',
    'booked_this_session': {
        'desc': 'QDII 000369/016280 自基准净值日 9/28 起回填至最新净值日 9/30（覆盖 US 9/29 + 9/30）',
        'nav_date': '2026-09-30', 'nav': {'000369': 2.5440, '016280': 2.5010},
        'pct': {'000369': -1.5851, '016280': -1.5742},
        'amount': round(sum(d['est_pnl'] for d in detail
                            if ''.join(c for c in str(d['code']) if c.isdigit()) in ('000369', '016280')), 2),
        'note': '实际兑现显著劣于 10/8 盘前档挂账估算（component_a+US9/30 段估算约 −755 元）→ '
                '§3.118a「实测隐含系数远高于标定 0.72」再次被证实'
    },
    'remaining': {
        'desc': '自 US 10/1 起未可观测段（IYH 口径，§3.133a 精确值现算）',
        'trade_dates_covered': ['2026-10-01', '2026-10-02', '2026-10-05', '2026-10-06', '2026-10-07'],
        'iyh_pct': IYH, 'comp_pct': comp_pct, 'notional_mv': qdii_mv,
        'notional': notional, 'low': round(notional * 0.9, 2), 'mid': round(notional * 0.72, 2),
        'high': round(notional * 0.6, 2), 'coef_range': [0.6, 0.9],
    },
    'unknown_sessions': ['2026-10-08(US)'],
    'note': '§3.112f / §3.118a：跨长假只给区间、禁止中枢点值；系数未重估前基于该系数的一切仓位决策无效',
}

# ---------- 12. 风险/防线线位 ----------
defense = {
    'hstech_4250': {
        'close': HSTECH_1008, 'prev_close': 4194.49, 'line': 4250,
        'dist_pts': round(HSTECH_1008 - 4250, 2),
        'dist_pct': round((HSTECH_1008 / 4250 - 1) * 100, 4),
        'state': 'close_level_break_deepened',
        'note': '破位幅度由 10/7 的 −1.3061% **扩大至 −4.1558%**（10/8 单日 −2.89%）；'
                '第 2 次 0.5% 减仓已于本档按 10/8 净值执行（纪律不可撤销，§3.114c）',
    },
    'zz_consume_12100': {
        'last': 12256.813, 'as_of': TODAY, 'dist_pct': round((12256.813 / 12100 - 1) * 100, 4),
        'state': 'above_lower_line', 'next_line': 12000,
        'next_line_dist_pct': round((12256.813 / 12000 - 1) * 100, 4),
    },
    'a_med_reverse_1_5pct': {
        'proxy_pct': BRD['sh000933'], 'as_of': TODAY, 'state': 'not_triggered',
        'note': '中证医药 10/8 单日 −2.55%（未触发 +1.5% 反转线）；300医药 −1.86% / 中证医疗 −2.73%',
    },
    'sh_comp': {'last': 3811.9043, 'as_of': TODAY, 'pct': IDXP['sh000001']},
}

note = ('10/8 正常交易日（A股 长假后复市首日 + 港股正常交易日；港股通/南向恢复首日）；'
        '场内 10 行按 10/8 收盘价；场外 19 只出 10/8 真实净值（A股主动医药基 002708/161616/000727 全部真实，'
        '本档**无代理估算** → 上下界 = 点值）；000071/012348（场外港股联接）10/8 净值一次性体现跨长假累积；'
        '000369/016280（QDII）自基准净值日 9/28 回填至 9/30、164906 自 9/29 回填至 9/30；'
        '⚠️ 第 2 次恒生科技 0.5% 纪律减仓 1,904.44 元于本档成交（累计 3,786.90 元），'
        '按「价值中性、权重单列」处理（P&L 口径不变）')

out = {
    'date': TODAY, 'as_of': '2026-10-08 收盘',
    'session_type': 'normal_trading_day_close_first_after_holiday',
    'base_total': BASE_TOTAL, 'base_file': 'portfolio_close_20260930_fix.json',
    'restore_rule_used': restore_rule, 'restore_dev': restore_dev,
    'restore_rule_all': dev_all,
    'detail_restore_rule': 'mv0_new+pnl',
    'detail_restore_dev': restore_dev,
    'detail_restore_total': new_total,
    'detail_restore_note': '逐券价值基准 = mv0_new + est_pnl（基准日修正后收盘价值）；由 track 级机器判据选定（§3.112a）',
    'est_total_pnl': total_pnl, 'est_total_pct': round(total_pct_raw, 2), 'est_total_pct_raw': total_pct_raw,
    'est_total_pnl_best': pnl_best, 'est_total_pnl_worst': pnl_worst,
    'est_total_pnl_high': pnl_best, 'est_total_pnl_low': pnl_worst,
    'band_note': '本档全部标的均为真实价格/真实净值（无代理估算）→ best == worst == 点值（§3.116b）',
    'total_mv': new_total, 'tracks': tracks,
    'discipline': DISCIPLINE,
    'med_exposure': med, 'med_pct': round(med / new_total * 100, 2),
    'threshold_all_med': threshold_all, 'threshold_a_sh_med': threshold_sh,
    'board_med': BOARD_MED, 'leader_med': LEADER_MED, 'lag_med': LAG_MED,
    'board_detail': {'000933': BRD['sh000933'], '399989': BRD['sz399989'],
                     '512170': ETFP['sh512170'], '159938': ETFP['sz159938'],
                     '000913': BRD['sh000913'], '399997': BRD['sz399997'],
                     '000932': IDXP['sh000932'], '399975': BRD['sz399975'],
                     '000934': BRD['sh000934'], '000827': BRD['sh000827']},
    'idx': {'000001': IDXP['sh000001'], '399006': IDXP['sz399006'], '000300': IDXP['sh000300'],
            '000688': IDXP['sh000688'], '399001': IDXP['sz399001'], '399005': IDXP['sz399005'],
            'HSTECH': [x['pct'] for x in cur['hk'] if x['code'] == 'HSTECH'][0],
            'HSI': [x['pct'] for x in cur['hk'] if x['code'] == 'HSI'][0],
            'HSCEI': [x['pct'] for x in cur['hk'] if x['code'] == 'HSCEI'][0],
            'HSHCI': [x['pct'] for x in cur['hk'] if x['code'] == 'HSHCI'][0]},
    'hk_mkt': {x['code']: {'close': x['close'], 'pct': x['pct'], 'high': x['high'], 'low': x['low']}
               for x in cur['hk']},
    'hk_stocks': {x['name']: {'close': x['close'], 'pct': x['pct']} for x in cur['hk_stocks']},
    'active_mult': active_mult, 'proxy_check': proxy_check,
    'peer_2708_pct': None, 'est_peer': {}, 'k_elastic': {}, 'est_band': 0.0,
    'structure_order': [o[0] for o in order], 'structure_pct': {o[0]: o[1] for o in order},
    'hk_split': {k: round(v, 2) for k, v in hk.items()},
    'hk_split_pnl': {k: round(v, 2) for k, v in hk_pnl.items()},
    'hk_split_rows': hk_rows,
    'hk_total': round(sum(hk.values()), 2),
    'hk_total_pct': round(sum(hk.values()) / new_total * 100, 2),
    'track_layer_hk_pct': round(tracks['恒生科技']['mv'] / new_total * 100, 2),
    'qdii_applied': [{'code': c, 'name': n, 'nav_date': d, 'nav': v, 'pct': p,
                      'base_nav_date': b, 'base_nav': i, 'basis': m} for c, n, d, v, p, b, i, m in qdii_applied],
    'nav30': [{'code': c, 'name': n, 'nav': v, 'pct': p, 'base_nav': i} for c, n, v, p, i in nav_today],
    'detail': detail,
    'proxy_used': [{'code': c, 'name': n, 'nd': nd, 'reason': r} for c, n, nd, r in missing],
    'pending_release': pending_release,
    'qdii_pending': qdii_pending,
    'defense': defense,
    'note': note,
}

json.dump(out, open(os.path.join(HIST, 'portfolio_close_' + TODAYC + '.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)

print('\n未出净值/需估算:', [(m[0], m[1], m[3]) for m in missing])
print(f'\n★ 组合 {total_pct_raw:+.4f}% ({total_pnl:+,.2f} 元)  总资产 {new_total:,.2f} 元 (基准 {BASE_TOTAL:,.2f} 元)')
print('\n赛道:')
for k, v in sorted(tracks.items(), key=lambda kv: -kv[1]['mv0']):
    print(f"  {k:10s} mv0={v['mv0']:>11,.2f} w={v['pct_of_total']:>6.2f}% day={v['day_pct']:+.3f}% pnl={v['pnl']:>+10,.2f}")
print('\n减仓后权重: ' + ' / '.join(f'{k} {v:.2f}%' for k, v in weight_after.items()))
print(f'\n医药敞口 {out["med_pct"]:.2f}%  门槛(全部医药) {threshold_all:+.2f}% / (仅A股医药) {threshold_sh:+.2f}%')
print(f'\n港股双层拆解：纯恒科 {hk["pure"]:,.2f} / 中概互联 {hk["concept"]:,.2f} / 宽基恒生系 {hk["broad"]:,.2f} '
      f'→ 合计 {sum(hk.values()):,.2f} 元 ({sum(hk.values())/new_total*100:.2f}%)')
print(f'  当日盈亏：纯恒科 {hk_pnl["pure"]:+,.2f} / 中概互联 {hk_pnl["concept"]:+,.2f} / 宽基恒生系 {hk_pnl["broad"]:+,.2f}')
print('\n结构顺序:', ' > '.join(f'{o[0]} {o[1]:+.2f}%' for o in order))
print('\n主动/被动医药基真实幅度 vs 板块:')
for c, v in active_mult.items():
    print(f"  {c} {v['name'][:12]:12s} {v['real_pct']:+.3f}%  ×BOARD_MED={v['mult_vs_board_med']}  ×300医药={v['mult_vs_300med']}")
print('\n被动联接偏差检验（真实净值 vs 指数）:')
for c, v in proxy_check.items():
    print(f"  {c} 真实 {v['real']:+.4f}% vs {v['label']} {v['index']:+.2f}% → dev {v['dev']:+.4f}pct")
print('\nQDII 挂账: 本档回填', qdii_pending['booked_this_session']['amount'], '元；'
      f"剩余区间 {qdii_pending['remaining']['low']:+,.2f} ~ {qdii_pending['remaining']['high']:+,.2f} 元")
print('\n个券贡献（按 |pnl| 排序前 26）:')
for d in sorted(detail, key=lambda y: -abs(y['est_pnl']))[:26]:
    print(f"  {d['track']:10s} {d['name'][:22]:22s} {str(d['code']):9s} {d['est_pct']:+8.3f}% "
          f"pnl={d['est_pnl']:>+9,.2f}  [{d['price_src'][:72]}]")
