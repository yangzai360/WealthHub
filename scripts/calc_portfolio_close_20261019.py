# -*- coding: utf-8 -*-
"""2026-10-19 盘后：组合收盘计算（链式法，§3.79/§3.97/§3.105/§3.109/§3.111/§3.112a/§3.121b 口径）

档型 = **②反向混合档**（A股 10/19 正常交易日 15:00 收盘 + 港股重阳节翌日休市 + 美股 10/19 未开盘）
base = portfolio_close_20261016_fix.json（10/16 收盘修正件 = 370,152.61 元）

定价覆盖：
  · 场内（ETF/个股 12 行）= 10/19 收盘价
  · 场外 23 只中 16 只出 10/19 真实净值（含港股联接 000071 / 012348：−0.02% / −0.02%）
  · 000369 / 016280（QDII）= 净值日推进至 10/16 但 Δ0.00%（疑似占位）→ 按源侧口径计 0 并标注
  · 164906（LOF）= 10/16 净值 0.8725（+0.8437%）真实兑现
  · 002742 / 000727 / 100032 / 161616 = 10/19 净值未出库 → 计 0（基准已含，§3.105）
产物：portfolio_close_20261019.json
"""
import json, os, re

BASE = '/Users/jieyang/Documents/WealthHub'
HIST = os.path.join(BASE, 'data/processed/history')
TODAY = '2026-10-19'
TODAYC = TODAY.replace('-', '')
PREV = '2026-10-16'

base = json.load(open(os.path.join(HIST, 'portfolio_close_20261016_fix.json'), encoding='utf-8'))
stale = json.load(open(os.path.join(HIST, 'close_20261016.json'), encoding='utf-8'))
STALE_HK = {x['code']: x for x in stale['hk']}
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
_sp = round(sum(x['est_pnl'] for x in base['detail']), 2)
if abs(_sp - base['est_total_pnl']) >= 1.5:
    raise SystemExit('基准 Σpnl 守卫失败（§3.109）')
print(f'✅ Σ tracks.pnl 守卫通过（{base["est_total_pnl"]:+,.2f} 元）')

# ---------- 1. 价格表（10/16 收盘） ----------
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


# ---------- 2. 板块/指数（10/16 收盘） ----------
BRD = {x['code']: x['pct'] for x in cur['boards']}
ETFP = {x['code']: x['pct'] for x in cur['etf']}
IDXP = {x['code']: x['pct'] for x in cur['indices']}
IDXCLOSE = {x['code']: x['close'] for x in cur['indices']}
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

# ---------- 4. 纪律减仓台账（两次均已成交；本档无新增动作） ----------
DISC1 = 1882.46
DISC2 = 1904.44
DISC_CUM = round(DISC1 + DISC2, 2)
assert abs(DISC_CUM - 3786.90) < 0.01
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
                     'reason': ('本档无新增防线触发（恒科收盘 4,108.24 距 4,250 为 −3.3355%，较 10/15 的 '
                                '−4.4473% **收窄**但仍在破位区间；同日防线只触发一次，§3.114c）；'
                                '**A股医药反向兑现线（−1.5%）本档收盘级触发**（板块代理 −1.8025%）→ '
                                '该线属「利好兑现后的回调观察线、非止损线」（§3.71 / §3.136a），'
                                '处置 = 主动减配 0 元、只登记 + 移交下一档闭环判定')},
    'settle': '两笔均已按净值成交（价值中性，P&L 口径不变）；本档只重算纪律后权重',
    'hk_after': hk_after, 'cash_after': cash_after, 'weight_after': weight_after,
    'basis_note': ('累计口径 = 已成交 1,882.46 元 + 已成交 1,904.44 元（§3.123e / §3.125c）；'
                   '分母为「上一有效估值日基准总资产」×0.5%'),
    'prior_档口径': {'source': 'portfolio_close_20261016_fix.json#discipline',
                     'hk_after': base['discipline'].get('hk_after'),
                     'cash_after': base['discipline'].get('cash_after'),
                     'weight_after_pct': {'恒生科技': base['discipline']['weight_after'].get('恒生科技'),
                                          '现金': base['discipline']['weight_after'].get('现金')},
                     'correction_note': '本档按 10/16 收盘市值重算纪律后权重（与前档口径并列、以本档为准）'},
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
_HSI_PCT = None   # 港股 10/19 休市 → 恒指无当日读数 → 000071 代理比对本档失效（§3.112i 禁互验）
# ⚠️ §3.103：代理指数必须是「该基金实际跟踪指数」——000968（广发养老产业）无对应入库指数，
#    一律不作代理比对（历史曾误用中证消费致 −0.4787pct 偏差）；001551/001180 为近似代理，须标注。
for c, idx, lab in (('012323', BRD['sz399989'], '中证医疗'), ('000051', IDXP['sh000300'], '沪深300'),
                    ('000071', _HSI_PCT, '恒生指数(跨市场参考,§3.112i 禁互验)'),
                    ('001551', BRD['sh000933'], '中证医药(近似代理·中证医药100未入库)'),
                    ('001180', BRD['sh000933'], '中证医药(近似代理·中证医药卫生未入库)'),
                    ('110020', IDXP['sh000300'], '沪深300')):
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

# ---------- 9. 结构顺序（300医药 / 中证医药 / 中证医疗） ----------
order = sorted([('300医药', BRD['sh000913']), ('中证医药', BRD['sh000933']), ('中证医疗', BRD['sz399989'])],
               key=lambda y: -y[1])
# ---------- 4. 纪律减仓台账（两次均已成交；本档无新增动作） ----------
DISC1 = 1882.46
DISC2 = 1904.44
DISC_CUM = round(DISC1 + DISC2, 2)
assert abs(DISC_CUM - 3786.90) < 0.01
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
                     'reason': ('本档无新增纪律动作：**恒生科技 4,250 破位判定今日不可作出**（港股休市，无当日收盘）'
                                '→ 判定顺延 10/20 收盘（§3.121b 反向混合档）；'
                                '**A股医药反向兑现线（−1.5%）闭环判定 = 不成立**（收盘板块代理 +1.1825% > 0%）→ '
                                '反向线状态回落为「单日触发」、10/16 的破位确认为**假破位**（§3.114c 对称处置），'
                                '**10/20 不建立减配预案**（原预案金额 1,851.30 元作废）')},
    'settle': '两笔均已按净值成交（价值中性，P&L 口径不变）；本档只重算纪律后权重',
    'hk_after': hk_after, 'cash_after': cash_after, 'weight_after': weight_after,
    'basis_note': ('累计口径 = 已成交 1,882.46 元 + 已成交 1,904.44 元（§3.123e / §3.125c）；'
                   '分母为「上一有效估值日基准总资产」×0.5%'),
    'prior_档口径': {'source': 'portfolio_close_20261016_fix.json#discipline',
                     'hk_after': base['discipline'].get('hk_after'),
                     'cash_after': base['discipline'].get('cash_after'),
                     'weight_after_pct': {'恒生科技': base['discipline']['weight_after'].get('恒生科技'),
                                          '现金': base['discipline']['weight_after'].get('现金')},
                     'correction_note': '本档按 10/19 收盘市值重算纪律后权重（与前档口径并列、以本档为准）'},
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

# ---------- 10. 港股腿：休市日「无新增待消化窗口」（§3.121b 镜像情形） ----------
prev_release = base.get('pending_release', {})
pending_release = {
    'source_file': 'portfolio_close_20261016_fix.json#pending_release',
    'window': prev_release.get('window', ['2026-10-02', '2026-10-05', '2026-10-06', '2026-10-07']),
    'window_closed': True, 'closed_on': '2026-10-08', 'refreshed': False,
    'window_estimate_low': prev_release.get('window_estimate_low'),
    'window_estimate_high': prev_release.get('window_estimate_high'),
    'new_window_this_session': [],
    'zero_reason': ('2026-10-19 为**港股重阳节翌日休市**（沪深港通双向关闭、10/20 恢复）→ '
                    '当日**不存在港股交易时段** → 结构化地「无新增待消化段」，非漏做测算（§3.121b / §3.124a）'),
    'realized_by_row_this_session': [
        {'code': r['code'], 'name': r['name'], 'seg': r['seg'], 'pct': r['pct'], 'pnl': r['pnl']}
        for r in hk_rows],
    'note': ('⚠️ 本档港联系 6 个券位**全部按真实价格/真实净值定价**：场内 3 只（513050 / 513180 / 159920）'
             '用 10/19 A股 收盘价（其变动为**标的休市下的溢价折价**，禁止外推港股方向，§3.121e）；'
             '场外 2 只（000071 / 012348）用 10/19 真实净值（−0.02% / −0.02%，休市日净值近似冻结）；'
             '164906（LOF）用 10/16 净值 +0.84%。→ **港股腿无「未定价」缺口、亦无新待消化项**。'),
}

# ---------- 11. QDII 挂账：US 10/16 段核销（实测 0 元）+ US 10/19 段未开盘 ----------
QDII_CODES = ('000369', '016280')
qdii_mv = round(tracks['美股标普医药']['mv'], 2)
Lof_mv = round(sum(d['mv0_new'] + d['est_pnl'] for d in detail
                   if ''.join(c for c in str(d['code']) if c.isdigit()) == '164906'), 2)
IYH_1016 = round((74.21 / 74.49 - 1) * 100, 4)      # IYH US 10/15 → 10/16（本档核销段）
XLV_1016 = round((176.71 / 177.19 - 1) * 100, 4)    # XLV 同段（仅对照，§3.106 禁作分母）
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
implied_coef = {k: round(abs(v) / abs(IYH_1016), 4) for k, v in qdii_realized_pct.items()}
implied_coef_xlv = {k: round(abs(v) / abs(XLV_1016), 4) for k, v in qdii_realized_pct.items()}
_coef_breach = {k: ('越上界' if v > 0.9 else ('越下界' if v < 0.6 else '区间内')) for k, v in implied_coef.items()}
# 前档（10/19 盘前/盘中档）预告区间
PRED_LOW, PRED_MID, PRED_HIGH = -206.50, -165.20, -137.65
QDII_SUSPECT = {c: (v == 0.0) for c, v in qdii_realized_pct.items()}
qdii_pending = {
    'as_of': '2026-10-19 20:00',
    'booked_this_session': {
        'desc': ('QDII 000369/016280 自基准净值日 10/15 推进至最新净值日 **10/16**（覆盖 US 10/16 共 1 个美股交易日）'
                 '＝ 前档登记的「US 10/16 挂账段」本档按真实净值核销'),
        'nav_date': '2026-10-16', 'nav': qdii_nav,
        'pct': qdii_realized_pct, 'amount': qdii_booked_amt,
        'pred_range': {'low': PRED_LOW, 'mid': PRED_MID, 'high': PRED_HIGH},
        'pred_vs_realized': {
            'realized': qdii_booked_amt,
            'vs_low_pct': round((qdii_booked_amt / PRED_LOW - 1) * 100, 2) if PRED_LOW else None,
            'verdict': ('**实测 0.00 元，高于区间上界 −137.65 元** —— 即「US 10/16 段的亏损未兑现」；'
                        '**§3.118a 区间法第 5 个可检验样本、方向为「上界越界」的第 3 例（前两例为正收益越上界）**'),
        },
        'suspect_placeholder': QDII_SUSPECT,
        'note': ('🔴 **异常须显式披露**：000369 与 016280 的 10/16 净值分别为 2.6460 / 2.6000，'
                 '**与 10/15 完全相同、日增长率 0.00%**，而同期 IYH 为 ' + ('%+.4f%%' % IYH_1016)
                 + '、XLV 为 ' + ('%+.4f%%' % XLV_1016) + '。**双源（天天基金 F10 直连 + akshare 同源接口）读数一致**，'
                 '故按源侧口径登记为「净值日推进、金额 0 元」，但**标注为疑似「净值未实际更新/占位」**：'
                 '隐含传导系数 000369 = ' + str(implied_coef.get('000369')) + ' / 016280 = ' + str(implied_coef.get('016280'))
                 + '（**全部越下界 0.60**，判定 = ' + str(_coef_breach) + '）。'
                 '→ **本档不据此下调 0.72 中枢，也不宣布「US 10/16 挂账已消除」**；'
                 '下一档（10/20）须复核该两券 10/16 净值是否被事后修订（§3.155a / §3.157f）。'),
    },
    'remaining': {
        'desc': '自 US 10/19 起未可观测段',
        'trade_dates_covered': ['2026-10-19(US)'],
        'iyh_pct': {}, 'comp_pct': 0.0, 'notional_mv': qdii_mv,
        'notional': 0.0, 'low': 0.0, 'mid': 0.0, 'high': 0.0, 'coef_range': [0.6, 0.9],
        'zero_reason': ('本档结束时点（北京 10/19 20:00）＝ 美东 10/19 08:00，**美股尚未开盘**、IYH 无读数'
                        '→ 按 0 计并显式声明，**非「挂账已消失」**（§3.124a / §3.120c 同类）。'),
    },
    'unknown_sessions': ['2026-10-19(US)'],
    'coef_reestimate': {'status': 'pending', 'require': '≥4 券位 × ≥5 交易日',
                        'observed_samples': {'2026-10-09': {'000369': 0.6668, '016280': 0.6787},
                                             '2026-10-12': {'000369': 1.0324, '016280': 1.0503},
                                             '2026-10-14': {'000369': 0.8735, '016280': 0.8721},
                                             '2026-10-15': {'000369': 0.5037, '016280': 0.5026},
                                             '2026-10-16': implied_coef}},
    'lof_164906_realized': lod_realized,
    'pending_codes': [], 'applied_codes': ['000369', '016280', '164906'],
    'note': ('§3.112f / §3.118a：挂账只给区间、禁止中枢点值。本档为 **US 10/16 段的核销档**：'
             '000369/016280 净值日推进至 10/16（金额 0 元、疑似占位，见 booked_this_session.note），'
             '164906 同步释放（10/16 净值 +0.8437%，计入恒生科技腿）。'
             '下一可观测起点 = US 10/19 收盘（成型于北京 10/20 04:00）。'
             '⚠️ 断言自证：`pending_codes ∩ applied_codes == ∅`（§3.117a）本档成立。'),
}

# ---------- 12. 防线线位（港股两条顺延 / A股两条本档判定） ----------
HS = STALE_HK['HSTECH']
HSTECH_STALE = HS['close']                 # 4,108.24（10/16 收盘，本档唯一可用读数）
HSI_STALE = STALE_HK['HSI']
HSCEI_STALE = STALE_HK['HSCEI']
HSHCI_STALE = STALE_HK['HSHCI']
_hs_dist = round((HSTECH_STALE / 4250 - 1) * 100, 4)
ZZ_CONSUME = IDXCLOSE['sh000932']
SH_COMP_CLOSE = IDXCLOSE['sh000001']
ZZ_PCT = IDXP['sh000932']
ZZ_LOW = [x['low'] for x in cur['indices'] if x['code'] == 'sh000932'][0]
_med_closed = BOARD_MED <= 0
defense = {
    'hstech_4250': {
        'close': HSTECH_STALE, 'stale_basis': '2026-10-16', 'line': 4250,
        'dist_pts': round(HSTECH_STALE - 4250, 2),
        'dist_pct': _hs_dist,
        'state': 'deferred_hk_closed',
        'judgement_deferred_to': '2026-10-20 close',
        'break_trend': {'2026-10-02': -2.1661, '2026-10-05': -1.5605, '2026-10-06': -0.6342,
                        '2026-10-07': -1.3061, '2026-10-08': -4.1558, '2026-10-09': -1.2273,
                        '2026-10-12': -1.8925, '2026-10-13': -2.6675, '2026-10-14': -1.7772,
                        '2026-10-15': -4.4473, '2026-10-16': _hs_dist},
        'action_reserved': '无（港股无交易时段；同日防线只触发一次，§3.114c）',
        'next_line': 4000, 'next_line_dist_pct': round((HSTECH_STALE / 4000 - 1) * 100, 4),
        'note': ('**本档无港股收盘价**（重阳节翌日休市）→ 4,250 破位 / 4,000 观察线**均无合法当日读数**，'
                 '沿用 10/16 收盘 ' + format(HSTECH_STALE, ',.2f') + '（距 4,250 ' + ('%+.4f' % _hs_dist) + '%）'
                 '**仅作参照、不作判定**；**判定权移交 10/20 收盘**。'
                 '⚠️ 禁用 A股 场内 513050 / 513180 的当日溢价折价变动替代港股方向（§3.121e）。'),
    },
    'zz_consume_12100': {
        'last': ZZ_CONSUME, 'as_of': TODAY, 'dist_pct': round((ZZ_CONSUME / 12100 - 1) * 100, 4),
        'state': 'above_lower_line', 'next_line': 12000,
        'next_line_dist_pct': round((ZZ_CONSUME / 12000 - 1) * 100, 4),
        'note': ('中证消费 10/19 收 ' + format(ZZ_CONSUME, ',.4f') + '（' + ('%+.2f' % ZZ_PCT) + '%），日内低 '
                 + format(ZZ_LOW, ',.2f') + ' 未破 12,100 下沿 → 安全边际 +'
                 + ('%.4f' % round((ZZ_CONSUME / 12100 - 1) * 100, 4)) + '%'
                 '（较 10/16 的 +3.2202% **收窄 ' + ('%.4f' % round(3.2202 - (ZZ_CONSUME / 12100 - 1) * 100, 4)) + 'pct**）；'
                 '⚠️ 结构：中证白酒 ' + ('%+.2f' % BRD['sz399997']) + '% > 中证消费 ' + ('%+.2f' % ZZ_PCT)
                 + '% → **「白酒独强、非酒类拖累」第 2 日延续**（缺口 '
                 + ('%.2f' % round(BRD['sz399997'] - ZZ_PCT, 2)) + 'pct）'),
    },
    'a_med_reverse_1_5pct': {
        'proxy_pct': BOARD_MED, 'as_of': TODAY, 'line_pct': -1.5,
        'dist_pct': round(BOARD_MED - (-1.5), 4),
        'state': 'not_triggered_today',
        'closure_verdict': ('closed_false_break' if not _med_closed else 'closed_confirmed_2day_pullback'),
        'contingency_closed': True, 'contingency_triggered': False,
        'action': 'active_take_profit = 0 / new_buy = 0',
        'semantics': '§3.71 / §3.136a：利好兑现后的回调观察线，**非止损线** → 处置 = 不执行主动减配',
        'closure_note': ('**闭环判定（本档终局）**：10/19 收盘板块代理 = ' + ('%+.4f' % BOARD_MED) + '% > 0% → '
                         '**「连续 2 日回调」不成立** → 10/16 的第三次触发被确认为**假破位（单日触发）**，'
                         '状态按 §3.114c 对称处置回落；**10/20 盘前档不建立 0.5% 被动减配预案**'
                         '（原登记金额 1,851.30 元作废，须在 10/20 档显式注销）。'),
        'trigger_count_since_inception': 3,
        'trigger_history': [{'date': '2026-09-24', 'proxy_pct': -2.3775, 'note': '首次触发（§3.104）'},
                            {'date': '2026-10-08', 'proxy_pct': -2.6475,
                             'note': '第 2 次触发 → 10/9 盘前档建立预案、10/9 收盘按「回调序列断裂」作废'},
                            {'date': '2026-10-16', 'proxy_pct': -1.8025,
                             'note': '**第 3 次触发 → 10/19 收盘闭环判定为假破位（本档）**'}],
        'note': ('A股医药收盘代理 BOARD_MED = ' + ('%+.4f' % BOARD_MED) + '%（中证医药 ' + ('%+.2f' % BRD['sh000933'])
                 + '% / 中证医疗 ' + ('%+.2f' % BRD['sz399989']) + '% / 医疗ETF ' + ('%+.2f' % ETFP['sh512170'])
                 + '% / 医药ETF ' + ('%+.2f' % ETFP['sz159938'])
                 + '%）→ 收盘级**未跌破** −1.5% 反向兑现线（距线 ' + ('%+.4f' % round(BOARD_MED + 1.5, 4)) + 'pct）；'
                 '结构：300医药 ' + ('%+.2f' % LEADER_MED) + '% / 中证医药 ' + ('%+.2f' % BRD['sh000933'])
                 + '% / 中证医疗 ' + ('%+.2f' % BRD['sz399989']) + '% → 内部离散度 '
                 + ('%.4f' % round(LEADER_MED - LAG_MED, 4)) + 'pct（较 10/16 的 3.13pct 大幅收敛）'),
    },
    'sh_comp': {'last': SH_COMP_CLOSE, 'as_of': TODAY, 'pct': IDXP['sh000001']},
}

# ---------- 13. 未定价券清单与可定价比例 ----------
unpriced = []
for c, n, nd, reason in missing:
    rows = [d for d in detail if ''.join(ch for ch in str(d['code']) if ch.isdigit()) == c]
    v = round(sum(r['mv0_new'] for r in rows), 2)
    unpriced.append({'code': c, 'name': n, 'nav_date': nd, 'reason': reason,
                     'rows': len(rows), 'notional': v})
UNPRICED_TOTAL = round(sum(u['notional'] for u in unpriced), 2)
priceable_total = round(new_total - UNPRICED_TOTAL, 2)
priceable_pct = round(priceable_total / new_total * 100, 2)

note = ('10/19 为**档型②反向混合档**（A股 长假后第 8 个正常交易日 15:00 收盘 + **港股重阳节翌日休市**）；'
        '场内 12 行按 10/19 收盘价（含 513050 / 513180 / 159920 三只跟踪港股标的的 ETF → 其变动为溢价折价，非港股方向）；'
        '场外 23 只中 **16 只**出 10/19 真实净值；000071 / 012348（港股联接）10/19 净值 −0.02% / −0.02% 已按真值计价；'
        '000369 / 016280（QDII）净值日推进至 10/16 但金额 0 元（疑似占位，须次档复核）、164906（LOF）10/16 净值 +0.8437% 已兑现；'
        '**4 只 A股 基金（002742 / 000727 / 100032 / 161616）10/19 净值 20:0x 首抓未出库 → 计 0（基准已含，§3.105）**，'
        '已列入 10/20 盘前档兜底复抓清单（§3.155a 固定工序）；'
        '⚠️ 第 2 次恒生科技 0.5% 纪律减仓 1,904.44 元已于 10/8 成交（累计 3,786.90 元），本档无新增纪律动作；'
        '🔴 **A股医药反向兑现线闭环判定 = 假破位**（收盘代理 ' + ('%+.4f' % BOARD_MED) + '% > 0%）'
        '→ 10/16 第三次触发按 §3.114c 对称处置回落，10/20 不建减配预案')

out = {
    'date': TODAY, 'as_of': '2026-10-19 收盘',
    'session_type': 'reverse_mixed_closed_hk',
    'session_type_note': ('反向混合档收盘（A股 10/19 正常交易日 15:00 收盘 + 港股重阳节翌日休市、'
                          '美股 10/19 未开盘）—— 与「A股休市 + 港股开市」互为镜像（§3.121b）'),
    'base_total': BASE_TOTAL, 'base_file': 'portfolio_close_20261016_fix.json',
    'stale_weight_fields_in_fix': {
        'source': 'portfolio_close_20261016_fix.json#tracks[].pct_of_total',
        'values': {k: v.get('pct_of_total') for k, v in base['tracks'].items()},
        'recomputed': {k: round(v['mv'] / float(base['total_mv']) * 100, 2) for k, v in base['tracks'].items()},
        'note': ('§3.146a：`_fix` 件只改 mv、未重算权重 → `pct_of_total` 为修正前分母（'
                 + format(float(base.get('base_total') or 0), ',.2f') + ' 元）派生值。'
                 '**本档及后续各档权重一律 `mv / total_mv` 现算，禁止引用该字段**。'),
    },
    'chain_0pct_row_inserted': False,
    'chain_note': ('A股 有当日真实收盘、场外基金有当日真实净值 → **本档计入链式序列**（非 0% 占位行）；'
                   '港股腿当日无交易时段 → 其「0 变动」属**真实无交易**、非 stale 污染（§3.121b）'),
    'restore_rule_used': restore_rule, 'restore_dev': restore_dev,
    'restore_rule_all': dev_all,
    'detail_restore_rule': 'mv0_new+pnl',
    'detail_restore_dev': restore_dev,
    'detail_restore_total': new_total,
    'detail_restore_note': '逐券价值基准 = mv0_new + est_pnl（基准日修正后收盘价值）；由 track 级机器判据选定（§3.112a）',
    'est_total_pnl': total_pnl, 'est_total_pct': round(total_pct_raw, 2), 'est_total_pct_raw': total_pct_raw,
    'est_total_pnl_best': pnl_best, 'est_total_pnl_worst': pnl_worst,
    'est_total_pnl_high': pnl_best, 'est_total_pnl_low': pnl_worst,
    'band_note': '场内与已出库场外均按真实价格/真实净值计价；未出库 4 只按基准计 0 → best == worst == 点值（§3.116b）',
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
            'HSTECH': HS['pct'], 'HSI': HSI_STALE['pct'], 'HSCEI': HSCEI_STALE['pct'],
            'HSHCI': HSHCI_STALE['pct']},
    'idx_stale_basis': {'HSTECH': '2026-10-16', 'HSI': '2026-10-16',
                        'HSCEI': '2026-10-16', 'HSHCI': '2026-10-16',
                        'note': '港股 10/19 休市 → 四个港股指数均为 10/16 收盘的 stale 值，禁止写当日行（§3.159）'},
    'hk_mkt': {'closed': True, 'reason': '2026-10-19 重阳节翌日休市（沪深港通双向关闭、10/20 恢复）',
               'stale': {k: {'close': STALE_HK[k]['close'], 'pct': STALE_HK[k]['pct'],
                             'date_field': STALE_HK[k].get('date_field')}
                         for k in ('HSTECH', 'HSI', 'HSCEI', 'HSHCI') if k in STALE_HK}},
    'hk_stocks': {},
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
    'unpriced': unpriced, 'unpriced_total': UNPRICED_TOTAL,
    'priceable_total': priceable_total, 'priceable_pct': priceable_pct,
    'pending_release': pending_release,
    'qdii_pending': qdii_pending,
    'qdii_mv': qdii_mv, 'lof_164906_mv': Lof_mv, 'iyh_1016_pct': IYH_1016, 'xlv_1016_pct': XLV_1016,
    'ex_div_adjustment': None,
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
print('\nQDII US 10/16 段核销:', qdii_booked_amt, '元；隐含系数', implied_coef, '→', _coef_breach)
print('\n防线:', json.dumps({k: (v.get('dist_pct') if 'dist_pct' in v else v.get('proxy_pct')) for k, v in defense.items()}, ensure_ascii=False))
print(f'\n未定价 {len(unpriced)} 只 / {UNPRICED_TOTAL:,.2f} 元 → 可定价比例 {priceable_pct:.2f}%')
print('\n个券贡献（按 |pnl| 排序前 26）:')
for d in sorted(detail, key=lambda y: -abs(y['est_pnl']))[:26]:
    print(f"  {d['track']:10s} {d['name'][:22]:22s} {str(d['code']):9s} {d['est_pct']:+8.3f}% "
          f"pnl={d['est_pnl']:>+9,.2f}  [{d['price_src'][:72]}]")
