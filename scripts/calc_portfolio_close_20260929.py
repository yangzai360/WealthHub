# -*- coding: utf-8 -*-
"""2026-09-29 盘后：组合收盘估算（链式法，§3.79/§3.97/§3.100/§3.105/§3.109/§3.111/§3.112a 口径）

base = portfolio_close_20260928_fix.json（9/28 收盘真实净值修正口径 = 375,885.31 元）
  §3.112a 强制：还原式由「机器可验证判据」选出（mv0_new+est_pnl 逐赛道 dev<1.5 通过）

本档定价覆盖（9/29 正常交易日，A股 15:00 / 港股 16:00 收盘）：
  · 场内（ETF/个股 10 行）= 9/29 收盘价（hq 直连）
  · 场外 17 只出 9/29 真实净值
  · 161616 / 000727（A股主动医药基）9/29 净值未出 → 「同侪锚定法」估算（锚 = 002708 真实净值 +0.15%）
  · 002742（泓德裕祥债券A，9.4 元，基准 9/28）→ 计 0（净值日未推进）
  · 000369 / 016280（QDII 广发全球医疗 A/C，4 行）新到 9/28 净值 → 真实兑现（基准含 9/24）
  · 164906（交银海外互联 LOF，2 行）新到 9/28 净值 0.8806 → 真实兑现

⚠️ 9/29 盘前档已触发「大消费 0.5% 纪律兑现 1,879.43 元」：
   本档按「全额持有参与 9/29 收益（P&L 口径不变）+ 兑现后权重单列」处理（价值中性，总额不变）。
输出：portfolio_close_20260929.json
"""
import json, os, re

BASE = '/Users/jieyang/Documents/WealthHub'
HIST = os.path.join(BASE, 'data/processed/history')
TODAY = '2026-09-29'
TODAYC = TODAY.replace('-', '')

base = json.load(open(os.path.join(HIST, 'portfolio_close_20260928_fix.json'), encoding='utf-8'))
cur = json.load(open(os.path.join(HIST, 'close_' + TODAYC + '.json'), encoding='utf-8'))
navj = json.load(open(os.path.join(HIST, 'fundnav_close_' + TODAYC + '.json'), encoding='utf-8'))

# ---------- 0. 基准还原式：机器可验证判据（§3.111 / §3.112a） ----------
tr = base['tracks']
RULES = [('mv0_new+pnl', lambda x: x.get('mv0_new', 0) + (x.get('est_pnl') or 0)),
         ('mv0+pnl', lambda x: x.get('mv0', 0) + (x.get('est_pnl') or 0)),
         ('mv+pnl', lambda x: x.get('mv', 0) + (x.get('est_pnl') or 0))]
restore_rule, restore_dev, dev_all = None, None, {}
for name, fn in RULES:
    dev_all[name] = [round(sum(fn(x) for x in base['detail'] if x['track'] == t) - tr[t]['mv'], 2) for t in tr]
for name, fn in RULES:
    devs = dev_all[name]
    if all(abs(d) < 1.5 for d in devs):
        restore_rule, restore_dev = name, devs
        break
if restore_rule is None:
    raise SystemExit('三种还原式均未通过硬守卫，拒绝继续（§3.112a）')
print(f'✅ 还原式判据：{restore_rule}，逐赛道 dev = {restore_dev}')
print(f"   （未通过者：mv0+pnl={dev_all['mv0+pnl']} / mv+pnl={dev_all['mv+pnl']}）")

FN = dict(RULES)[restore_rule]
base_val = [round(FN(x), 2) for x in base['detail']]
BASE_TOTAL = round(float(base['total_mv']), 2)
tot = round(sum(base_val), 2)
if abs(tot - BASE_TOTAL) >= 1.5:
    raise SystemExit(f'基准还原失败 {tot} vs {BASE_TOTAL}')
print(f'✅ 基准还原校验：Σ = {tot:,.2f} 元 = total_mv {BASE_TOTAL:,.2f} 元（{len(base_val)} 行）')
if abs(round(sum(x['est_pnl'] for x in base['detail']), 2) - base['est_total_pnl']) >= 1.5:
    raise SystemExit('基准 Σpnl 守卫失败（§3.109）')
print(f'✅ Σ tracks.pnl 守卫通过（{base["est_total_pnl"]:+,.2f} 元）')

# ---------- 1. 价格表（9/29 收盘） ----------
PX = {}
for x in cur['etf'] + cur['stocks']:
    PX[x['code'].replace('sh', '').replace('sz', '')] = x['close']

NAV = {}
for n in navj['fund_navs']:
    if n['code'] not in NAV or n['nav_date'] > NAV[n['code']][0]:
        NAV[n['code']] = (n['nav_date'], n['nav'])


def parse_base_nav_date(src):
    """§3.105：基准已含哪一日净值必须从 price_src 解析，禁止用固定日期常量"""
    s = str(src)
    m = re.search(r'净值\s*(?:新净值\s*)?(\d{4})-(\d{2})-(\d{2})', s)
    if m:
        return f'{m.group(1)}-{m.group(2)}-{m.group(3)}'
    m = re.search(r'净值\s*(\d{1,2})/(\d{1,2})', s)
    if m:
        return f'2026-{int(m.group(1)):02d}-{int(m.group(2)):02d}'
    return None


# ---------- 2. 板块/指数代理（9/29 收盘） ----------
BRD = {x['code']: x['pct'] for x in cur['boards']}
ETFP = {x['code']: x['pct'] for x in cur['etf']}
IDXP = {x['code']: x['pct'] for x in cur['indices']}
BOARD_MED = round((BRD['sh000933'] + BRD['sz399989'] + ETFP['sh512170'] + ETFP['sz159938']) / 4, 4)
LEADER_MED = BRD['sh000913']            # 300医药
LAG_MED = round((BRD['sh000933'] + BRD['sz399989'] + ETFP['sh512170']) / 3, 4)
print(f'BOARD_MED={BOARD_MED}%  300医药={LEADER_MED}%  LAG_MED={LAG_MED}%')

# ---------- 3. 未出净值主动基：同侪锚定法 ----------
# 锚 = 002708 大摩健康产业 9/29 真实净值 +0.15%（同为 A股主动医药基）
PEER_2708 = None
for n in navj['fund_navs']:
    if n['code'] == '002708' and n['nav_date'] == TODAY:
        PEER_2708 = n['pct']
if PEER_2708 is None:
    raise SystemExit('002708 9/29 净值未出，同侪锚不可用，拒绝估算（§3.97 样本<5 不得单独使用）')
# §3.97 折中口径弹性：002708 / 161616 / 000727 = 1.64 / 1.29 / 0.81
K = {'002708': 1.64, '161616': 1.29, '000727': 0.81}
EST_PEER = {}
for c in ('161616', '000727'):
    central = round(PEER_2708 * K[c] / K['002708'], 4)
    board_based = round(BOARD_MED * K[c], 4)              # 下界：板块代理口径（本档为负）
    EST_PEER[c] = {'central': central,
                   'best': round(max(central, board_based, 0.0) + 0.15, 4),
                   'worst': round(min(central, board_based, 0.0) - 0.15, 4)}
print(f'002708 9/29 真实净值 = {PEER_2708:+.2f}% → 同侪锚定：161616={EST_PEER["161616"]["central"]:+.4f}% / 000727={EST_PEER["000727"]["central"]:+.4f}%')
print(f'   板块代理口径对照（BOARD_MED × k）：161616={round(BOARD_MED*K["161616"],4):+.4f}% / 000727={round(BOARD_MED*K["000727"],4):+.4f}%')

# ---------- 4. 逐券定价 ----------
detail, missing, qdii_applied, nav29 = [], [], [], []
for i, x in enumerate(base['detail']):
    code6 = ''.join(c for c in str(x['code']) if c.isdigit())
    sh = float(x['shares']) if x.get('shares') else 0.0
    v0 = base_val[i]
    pct = pct_best = pct_worst = 0.0
    if code6 == '' or sh == 0:
        src = '现金'
    elif code6 in PX:
        imp = v0 / sh
        pct = pct_best = pct_worst = round((PX[code6] / imp - 1) * 100, 4)
        src = f'场内收盘 9/29 {PX[code6]}（基准 {round(imp,4)}）'
    elif code6 in EST_PEER:
        pct = EST_PEER[code6]['central']
        pct_best = EST_PEER[code6]['best']
        pct_worst = EST_PEER[code6]['worst']
        src = (f'9/29 净值未出(最新 9/28) → 同侪锚定法：002708 真实 {PEER_2708:+.2f}% × k{k[code6] if False else K[code6]}/k1.64 = {pct:+.4f}%'
               f'（区间 {pct_worst:+.4f}% ~ {pct_best:+.4f}%）')
        missing.append((code6, x['name'], '2026-09-28', 'A股主动医药基净值未出→同侪锚定估算'))
    elif code6 in NAV:
        nd, nav = NAV[code6]
        imp = v0 / sh
        base_nd = parse_base_nav_date(x.get('price_src', ''))
        if nd == TODAY:
            pct = pct_best = pct_worst = round((nav / imp - 1) * 100, 4)
            src = f'净值 9/29 ({nav})，基准净值日 {base_nd}'
            nav29.append((code6, x['name'], nav, pct, round(imp, 4)))
        elif base_nd and nd > base_nd:
            pct = pct_best = pct_worst = round((nav / imp - 1) * 100, 4)
            src = f'LOF/QDII 新净值 {nd} ({nav}) 真实兑现（基准为 {base_nd}，Δ {round((nav/imp-1)*100,4):+.4f}%）'
            qdii_applied.append((code6, x['name'], nd, nav, pct, base_nd, round(imp, 4)))
        else:
            src = f'净值未推进(nd={nd}，基准 {base_nd}) → 计 0（基准已含）'
            missing.append((code6, x['name'], nd, '净值日未推进→计0'))
    else:
        src = '数据暂缺→按0'
        missing.append((code6, x['name'], None, '数据暂缺'))
    detail.append({**x, 'mv0_new': v0, 'est_pct': pct, 'est_pnl': round(v0 * pct / 100, 2),
                   'est_pct_best': pct_best, 'est_pnl_best': round(v0 * pct_best / 100, 2),
                   'est_pct_worst': pct_worst, 'est_pnl_worst': round(v0 * pct_worst / 100, 2),
                   'price_src': src})

total_pnl = round(sum(d['est_pnl'] for d in detail), 2)
total_pct = round(total_pnl / BASE_TOTAL * 100, 4)
new_total = round(BASE_TOTAL + total_pnl, 2)
pnl_best = round(sum(d['est_pnl_best'] for d in detail), 2)
pnl_worst = round(sum(d['est_pnl_worst'] for d in detail), 2)

tracks = {}
for d in detail:
    t = tracks.setdefault(d['track'], {'mv0': 0.0, 'mv': 0.0, 'pnl': 0.0,
                                       'pnl_best': 0.0, 'pnl_worst': 0.0})
    t['mv0'] += d['mv0_new']; t['mv'] += d['mv0_new'] + d['est_pnl']; t['pnl'] += d['est_pnl']
    t['pnl_best'] += d['est_pnl_best']; t['pnl_worst'] += d['est_pnl_worst']
for k, v in tracks.items():
    for f in ('mv0', 'mv', 'pnl', 'pnl_best', 'pnl_worst'):
        v[f] = round(v[f], 2)
    v['pct_of_total'] = round(v['mv'] / new_total * 100, 2)
    v['day_pct'] = round(v['pnl'] / v['mv0'] * 100, 3) if v['mv0'] else 0.0

# ---- 三道硬守卫（§3.107/§3.109） ----
assert abs(round(sum(v['mv'] for v in tracks.values()), 2) - new_total) < 1.5, 'Σ tracks.mv 守卫失败'
assert abs(round(sum(v['pnl'] for v in tracks.values()), 2) - total_pnl) < 1.5, 'Σ tracks.pnl 守卫失败'
assert abs(round(sum(d['mv0_new'] for d in detail), 2) - BASE_TOTAL) < 1.5, 'Σ mv0 守卫失败'
print('✅ 三道硬守卫全部通过')

# ---- 9/29 盘前档「大消费 0.5% 纪律兑现」的兑现后权重（价值中性，P&L 口径不变） ----
DISCIPLINE_CASH = 1879.43
dc = next(d for d in detail if ''.join(c for c in str(d['code']) if c.isdigit()) == '000248' and d['track'] == '大消费')
dc_val = dc['mv0_new'] + dc['est_pnl']
r_dc = dc['est_pct'] / 100
weight_after = {}
for k, v in tracks.items():
    weight_after[k] = v['mv'] / new_total * 100
weight_after['大消费'] -= DISCIPLINE_CASH * (1 + r_dc) / new_total * 100
weight_after['现金'] += DISCIPLINE_CASH * (1 + r_dc) / new_total * 100
weight_after = {k: round(v, 2) for k, v in weight_after.items()}

# ---- 港股暴露双层拆解（§3.108 条款 4） ----
HK_ROWS = {'012348': 'pure', '513180': 'pure', '513050': 'concept', '164906': 'concept',
           '000071': 'broad', '159920': 'broad'}
hk = {'pure': 0.0, 'concept': 0.0, 'broad': 0.0}
hk_pnl = {'pure': 0.0, 'concept': 0.0, 'broad': 0.0}
for d in detail:
    c6 = ''.join(c for c in str(d['code']) if c.isdigit())
    if c6 in HK_ROWS:
        hk[HK_ROWS[c6]] += d['mv0_new'] + d['est_pnl']
        hk_pnl[HK_ROWS[c6]] += d['est_pnl']

# ---- 主动医药基真实倍数 ----
active_mult = {}
for c, nm in (('002708', '大摩健康产业A'), ('161616', '融通医疗保健'), ('000727', '融通健康产业')):
    rows = [d for d in detail if ''.join(ch for ch in str(d['code']) if ch.isdigit()) == c]
    if rows:
        active_mult[c] = {'name': nm, 'real_pct': rows[0]['est_pct'],
                          'mult_vs_board_med': round(rows[0]['est_pct'] / BOARD_MED, 3) if BOARD_MED else None,
                          'mult_vs_300med': round(rows[0]['est_pct'] / LEADER_MED, 3) if LEADER_MED else None,
                          'estimated': c in EST_PEER}

# ---- 被动联接类偏差检验（§3.103） ----
proxy_check = {}
for c, idx, lab in (('012323', BRD['sz399989'], '中证医疗'), ('000051', IDXP['sh000300'], '沪深300'),
                    ('000071', IDXP['sh000300'], '沪深300(A股口径)'), ('001180', BRD['sh000933'], '中证医药')):
    rows = [d for d in detail if ''.join(ch for ch in str(d['code']) if ch.isdigit()) == c]
    if rows and isinstance(idx, float):
        proxy_check[c] = {'real': rows[0]['est_pct'], 'index': idx, 'label': lab,
                          'dev': round(rows[0]['est_pct'] - idx, 4)}

# ---- 医药敞口与门槛（§3.98 方程解法） ----
med = round(tracks['A股医药']['mv'] + tracks['美股标普医药']['mv'], 2)
A, B = med, new_total - med
threshold_all = round(((0.40 / 0.60) * B / A - 1) * 100, 2)
A_sh = tracks['A股医药']['mv']
threshold_sh = round((((0.40 / 0.60) * B - (med - A_sh)) / A_sh - 1) * 100, 2)

out = {'date': TODAY, 'as_of': '2026-09-29收盘', 'base_total': BASE_TOTAL,
       'base_file': 'portfolio_close_20260928_fix.json',
       'restore_rule_used': restore_rule, 'restore_dev': restore_dev,
       'restore_rule_all': {k: v for k, v in dev_all.items()},
       'est_total_pnl': total_pnl, 'est_total_pct': round(total_pct, 2),
       'est_total_pct_raw': total_pct,
       'est_total_pnl_best': pnl_best, 'est_total_pnl_worst': pnl_worst,
       'est_total_pct_best_raw': round(pnl_best / BASE_TOTAL * 100, 4),
       'est_total_pct_worst_raw': round(pnl_worst / BASE_TOTAL * 100, 4),
       'total_mv': new_total, 'tracks': tracks,
       'discipline': {'date': TODAY, 'kind': '大消费 0.5% 纪律兑现（9/29 盘前档触发）',
                      'amount': DISCIPLINE_CASH, 'settle': '按 9/29 净值成交（价值中性，P&L 口径不变）',
                      'weight_after': weight_after},
       'med_exposure': med, 'med_pct': round(med / new_total * 100, 2),
       'threshold_all_med': threshold_all, 'threshold_a_sh_med': threshold_sh,
       'board_med': BOARD_MED, 'leader_med': LEADER_MED, 'lag_med': LAG_MED,
       'board_detail': {'000933': BRD['sh000933'], '399989': BRD['sz399989'],
                        '512170': ETFP['sh512170'], '159938': ETFP['sz159938'],
                        '000913': BRD['sh000913'], '399997': BRD['sz399997'],
                        '000932': IDXP['sh000932'], '399975': BRD['sz399975'],
                        '000934': BRD['sh000934'], '000827': BRD['sh000827']},
       'idx': {'000001': IDXP['sh000001'], '399006': IDXP['sz399006'],
               'HSTECH': [x['pct'] for x in cur['hk'] if x['code'] == 'HSTECH'][0],
               'HSI': [x['pct'] for x in cur['hk'] if x['code'] == 'HSI'][0]},
       'active_mult': active_mult, 'proxy_check': proxy_check,
       'peer_2708_pct': PEER_2708, 'est_peer': EST_PEER, 'k_elastic': K,
       'hk_split': {k: round(v, 2) for k, v in hk.items()},
       'hk_split_pnl': {k: round(v, 2) for k, v in hk_pnl.items()},
       'hk_total': round(sum(hk.values()), 2), 'hk_total_pct': round(sum(hk.values()) / new_total * 100, 2),
       'qdii_applied': [{'code': c, 'name': n, 'nav_date': d, 'nav': v, 'pct': p,
                         'base_nav_date': b, 'base_nav': i} for c, n, d, v, p, b, i in qdii_applied],
       'nav29': [{'code': c, 'name': n, 'nav': v, 'pct': p, 'base_nav': i} for c, n, v, p, i in nav29],
       'detail': detail,
       'proxy_used': [{'code': c, 'name': n, 'nd': nd, 'reason': r} for c, n, nd, r in missing],
       'note': ('9/29 正常交易日；场内 10 行按 9/29 收盘价；场外 17 只出 9/29 真实净值；'
                '161616/000727 净值未出→同侪锚定法（锚 002708 真实 +0.15%）；002742 计 0；'
                '000369/016280 新到 9/28 净值真实兑现（基准含 9/24）；164906 新到 9/28 净值真实兑现。'
                '⚠️ 大消费 0.5% 纪律兑现按「价值中性、权重单列」处理（P&L 口径不变）')}

json.dump(out, open(os.path.join(HIST, 'portfolio_close_' + TODAYC + '.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)

print('\n未出净值/需估算:', [(m[0], m[1], m[3]) for m in missing])
print(f'\n★ 组合 {total_pct:+.4f}% ({total_pnl:+,.2f} 元)  总资产 {new_total:,.2f} 元 (基准 {BASE_TOTAL:,.2f} 元)')
print(f'  上界(最优) {round(pnl_best/BASE_TOTAL*100,4):+.4f}% ({pnl_best:+,.2f} 元) ~ 下界(最差) {round(pnl_worst/BASE_TOTAL*100,4):+.4f}% ({pnl_worst:+,.2f} 元)')
print(f'\nQDII/LOF 真实兑现 {len(qdii_applied)} 行:')
for c, n, d, v, p, b, i in qdii_applied:
    print(f'   {c} {n[:20]:20s} {b} → {d} ({v})  {p:+.4f}%')
print(f'\n赛道:')
for k, v in sorted(tracks.items(), key=lambda kv: -kv[1]['mv0']):
    print(f"  {k:10s} mv0={v['mv0']:>11,.2f} w={v['pct_of_total']:>6.2f}% day={v['day_pct']:+.3f}% pnl={v['pnl']:>+10,.2f} ({v['pnl_worst']:+,.2f}~{v['pnl_best']:+,.2f})")
print(f'\n兑现后权重: ' + ' / '.join(f'{k} {v:.2f}%' for k, v in weight_after.items()))
print(f'\n医药敞口 {out["med_pct"]:.2f}%  门槛(全部医药) {threshold_all:+.2f}% / (仅A股医药) {threshold_sh:+.2f}%')
print(f'\n港股双层拆解：纯恒科 {hk["pure"]:,.2f} / 中概互联 {hk["concept"]:,.2f} / 宽基恒生系 {hk["broad"]:,.2f} → 合计 {sum(hk.values()):,.2f} 元 ({sum(hk.values())/new_total*100:.2f}%)')
print(f'  当日盈亏：纯恒科 {hk_pnl["pure"]:+,.2f} / 中概互联 {hk_pnl["concept"]:+,.2f} / 宽基恒生系 {hk_pnl["broad"]:+,.2f}')
print('\n主动医药基当日幅度 vs 板块代理:')
for c, v in active_mult.items():
    print(f"  {c} {v['name'][:10]:10s} {v['real_pct']:+.3f}%  ×BOARD_MED={v['mult_vs_board_med']}  ×300医药={v['mult_vs_300med']}  {'[估算]' if v['estimated'] else '[真实]'}")
print('\n被动联接偏差检验:')
for c, v in proxy_check.items():
    print(f"  {c} 真实 {v['real']:+.4f}% vs {v['label']} {v['index']:+.2f}% → dev {v['dev']:+.4f}pct")
print('\n个券贡献（按 |pnl| 排序前 26）:')
for d in sorted(detail, key=lambda y: -abs(y['est_pnl']))[:26]:
    print(f"  {d['track']:10s} {d['name'][:22]:22s} {str(d['code']):9s} {d['est_pct']:+8.3f}% pnl={d['est_pnl']:>+9,.2f}  [{d['price_src'][:66]}]")
