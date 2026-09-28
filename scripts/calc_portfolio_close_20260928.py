# -*- coding: utf-8 -*-
"""2026-09-28 盘后：组合收盘估算（链式法，§3.79/§3.97/§3.100/§3.102/§3.107/§3.111 口径）

base = portfolio_close_20260924_fix.json（9/24 收盘真实净值修正口径 = 377,630.12 元）
  §3.111 强制：还原式由「机器可验证判据」选出（本轮实测 mv0+est_pnl 全赛道 dev=0.00 → 采用）
  ⚠️ 9/25 为「混合档」、9/27 为「纯非交易日」、9/28 盘前/盘中均不产出 portfolio 产物
     → 9/24 修正件即为本档唯一基准（港股 9/25 跌幅在 9/28 复市首日一次性定价）

本档定价覆盖：
  · 场内（ETF/个股）= 9/28 收盘价（hq 直连，15:00/16:00 收盘）
  · 场外 17 只出 9/28 真实净值
  · 002708（大摩健康产业A）9/28 净值未出 → 「同侪法」估算（161616/000727 已出真实净值）
  · 001180（广发医药卫生联接A）9/28 净值未出 → 按所跟踪指数 000933（中证医药）代理（§3.103）
  · 002742（泓德裕祥债券A，9.4 元）→ 计 0
  · 000369/016280（QDII 广发全球医疗 A/C，4 行）最新净值日 = 9/23 = 基准已含 → 计 0（连续第 5 档未出库）
  · 164906（交银海外互联 LOF，2 行）新到 9/24 净值 0.8864 → 真实兑现 −0.5945%
输出：portfolio_close_20260928.json
"""
import json, os, re

BASE = '/Users/jieyang/Documents/WealthHub'
HIST = os.path.join(BASE, 'data/processed/history')
TODAY = '2026-09-28'
TODAYC = TODAY.replace('-', '')

base = json.load(open(os.path.join(HIST, 'portfolio_close_20260924_fix.json'), encoding='utf-8'))
cur = json.load(open(os.path.join(HIST, 'close_' + TODAYC + '.json'), encoding='utf-8'))
navj = json.load(open(os.path.join(HIST, 'fundnav_close_' + TODAYC + '.json'), encoding='utf-8'))

# ---------- 0. 基准还原式：机器可验证判据（§3.111） ----------
tr = base['tracks']
RULES = [('mv0+pnl', lambda x: x.get('mv0', 0) + (x.get('est_pnl') or 0)),
         ('mv+pnl', lambda x: x.get('mv', 0) + (x.get('est_pnl') or 0))]
restore_rule, restore_dev = None, None
for name, fn in RULES:
    devs = []
    for t in tr:
        s = sum(fn(x) for x in base['detail'] if x['track'] == t)
        devs.append(round(s - tr[t]['mv'], 2))
    if all(abs(d) < 1.5 for d in devs):
        restore_rule, restore_dev = name, devs
        break
if restore_rule is None:
    raise SystemExit('两种还原式均未通过硬守卫，拒绝继续（§3.111）')
print(f'✅ 还原式判据：{restore_rule}，逐赛道 dev = {restore_dev}')

FN = RULES[[n for n, _ in RULES].index(restore_rule)][1]
base_val = [round(FN(x), 2) for x in base['detail']]
BASE_TOTAL = round(float(base['total_mv']), 2)
tot = round(sum(base_val), 2)
if abs(tot - BASE_TOTAL) >= 1.5:
    raise SystemExit(f'基准还原失败 {tot} vs {BASE_TOTAL}')
print(f'✅ 基准还原校验：Σ = {tot:,.2f} = total_mv {BASE_TOTAL:,.2f}（{len(base_val)} 行）')
if abs(round(sum(x['est_pnl'] for x in base['detail']), 2) - base['est_total_pnl']) >= 1.5:
    raise SystemExit('基准 Σpnl 守卫失败（§3.109）')
print(f'✅ Σ tracks.pnl 守卫通过（{base["est_total_pnl"]:+,.2f} 元）')

# ---------- 1. 价格表 ----------
PX = {}
for x in cur['etf'] + cur['stocks']:
    PX[x['code'].replace('sh', '').replace('sz', '')] = x['close']

NAV = {}
for n in navj['fund_navs']:
    if n['code'] not in NAV or n['nav_date'] > NAV[n['code']][0]:
        NAV[n['code']] = (n['nav_date'], n['nav'])

# ---------- 2. 板块/指数代理（9/28 收盘） ----------
BRD = {x['code']: x['pct'] for x in cur['boards']}
ETFP = {x['code']: x['pct'] for x in cur['etf']}
IDXP = {x['code']: x['pct'] for x in cur['indices']}
BOARD_MED = round((BRD['sh000933'] + BRD['sz399989'] + ETFP['sh512170'] + ETFP['sz159938']) / 4, 4)
LEADER_MED = BRD['sh000913']            # 300医药
LAG_MED = round((BRD['sh000933'] + BRD['sz399989'] + ETFP['sh512170']) / 3, 4)

# ---------- 3. 002708 同侪法估算 ----------
P161, P727 = -0.88, -0.83
PEER_AVG = round((P161 + P727) / 2, 4)          # -0.8550
PEER_BEST, PEER_WORST = max(P161, P727), min(P161, P727)
K_MED, K_MIN, K_MAX = 1.304, 0.773, 2.010       # 近 11 样本实测（§3.97 折中口径）
EST_2708 = {'central': round(PEER_AVG * K_MED, 4),
            'best': round(PEER_BEST * 1.00, 4),
            'worst': round(PEER_WORST * K_MAX, 4)}
print(f'002708 同侪法：peer_avg={PEER_AVG}% k_med={K_MED} → {EST_2708}')

# 001180 按 000933 代理（§3.103：代理指数 = 实际跟踪指数）
PROXY_180 = {'central': round(BRD['sh000933'], 4),
             'best': round(BRD['sh000933'] + 0.14, 4),
             'worst': round(BRD['sh000933'] - 0.04, 4)}
print(f'001180 代理 000933={BRD["sh000933"]}% → {PROXY_180}')

detail, missing, qdii_applied, nav28 = [], [], [], []
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
        src = f'场内收盘 9/28 {PX[code6]}'
    elif code6 == '002708':
        pct = EST_2708['central']; pct_best = EST_2708['best']; pct_worst = EST_2708['worst']
        src = (f'9/28 净值未出(最新 9/24) → 同侪法：peer_avg({P161}%,{P727}%)={PEER_AVG}%'
               f' × k 中位 {K_MED} = {pct}%（区间 {pct_best}% ~ {pct_worst}%）')
        missing.append((code6, x['name'], '2026-09-24', 'A股医药主动基净值未出→同侪法估算'))
    elif code6 == '001180':
        pct, pct_best, pct_worst = (PROXY_180['central'], PROXY_180['best'], PROXY_180['worst'])
        src = f'9/28 净值未出(最新 9/24) → 按跟踪指数 000933 中证医药代理 {pct}%（§3.103）'
        missing.append((code6, x['name'], '2026-09-24', '被动联接净值未出→按跟踪指数代理'))
    elif code6 == '002742':
        src = '9/28 净值未出(最新 9/24) → 计 0（债券类，持仓 9.40 元）'
        missing.append((code6, x['name'], '2026-09-24', '债券类未出净值→计0'))
    elif code6 in NAV:
        nd, nav = NAV[code6]
        imp = v0 / sh
        # §3.105：基准已含的净值日必须从 price_src 解析；本档 base 有「2026-09-24」与「9/24」两种写法
        srcs = str(x.get('price_src', ''))
        base_nd = None
        m = re.search(r'(\d{4})-(\d{2})-(\d{2})', srcs)
        if m:
            base_nd = m.group(0)
        else:
            m2 = re.search(r'净值\s*(\d{1,2})/(\d{1,2})', srcs)
            if m2:
                base_nd = f'2026-{int(m2.group(1)):02d}-{int(m2.group(2)):02d}'
        if nd == TODAY:
            pct = pct_best = pct_worst = round((nav / imp - 1) * 100, 4)
            src = f'净值 9/28 ({nav})，基准净值日 {base_nd}'
            nav28.append((code6, x['name'], nav, pct, round(imp, 4)))
        elif base_nd and nd > base_nd:
            pct = pct_best = pct_worst = round((nav / imp - 1) * 100, 4)
            src = f'LOF/QDII 新净值 {nd} ({nav}) 真实兑现（基准为 {base_nd}）'
            qdii_applied.append((code6, x['name'], nd, nav, pct))
        else:
            src = f'净值未更新(nd={nd}，基准 {base_nd}) → 计 0（基准已含）'
            missing.append((code6, x['name'], nd, 'QDII T+2 未出库→计0'))
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

# ---- 硬守卫（三道） ----
assert abs(round(sum(v['mv'] for v in tracks.values()), 2) - new_total) < 1.5, 'Σ tracks.mv 守卫失败'
assert abs(round(sum(v['pnl'] for v in tracks.values()), 2) - total_pnl) < 1.5, 'Σ tracks.pnl 守卫失败'
print('✅ 三道硬守卫全部通过')

# ---- 港股暴露双层拆解（§3.108） ----
HK_ROWS = {'012348': 'pure', '513180': 'pure', '513050': 'concept', '164906': 'concept',
           '000071': 'broad', '159920': 'broad'}
hk = {'pure': 0.0, 'concept': 0.0, 'broad': 0.0}
hk_pnl = {'pure': 0.0, 'concept': 0.0, 'broad': 0.0}
for d in detail:
    c6 = ''.join(c for c in str(d['code']) if c.isdigit())
    if c6 in HK_ROWS:
        hk[HK_ROWS[c6]] += d['mv0_new'] + d['est_pnl']
        hk_pnl[HK_ROWS[c6]] += d['est_pnl']

# ---- 主动医药基真实倍数（161616 / 000727 为真实净值，002708 为估算） ----
active_mult = {}
for c, nm in (('002708', '大摩健康产业A'), ('161616', '融通医疗保健'), ('000727', '融通健康产业')):
    rows = [d for d in detail if ''.join(ch for ch in str(d['code']) if ch.isdigit()) == c]
    if rows:
        active_mult[c] = {'name': nm, 'real_pct': rows[0]['est_pct'],
                          'mult_vs_board_med': round(rows[0]['est_pct'] / BOARD_MED, 3) if BOARD_MED else None,
                          'mult_vs_300med': round(rows[0]['est_pct'] / LEADER_MED, 3) if LEADER_MED else None,
                          'estimated': c == '002708'}

# ---- 被动联接类偏差检验（§3.103） ----
proxy_check = {}
for c, idx, lab in (('012323', BRD['sz399989'], '中证医疗'), ('001551', None, '中证医药100')):
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

out = {'date': TODAY, 'as_of': '2026-09-28收盘', 'base_total': BASE_TOTAL,
       'base_file': 'portfolio_close_20260924_fix.json',
       'restore_rule_used': restore_rule, 'restore_dev': restore_dev,
       'est_total_pnl': total_pnl, 'est_total_pct': round(total_pct, 2),
       'est_total_pct_raw': total_pct,
       'est_total_pnl_best': pnl_best, 'est_total_pnl_worst': pnl_worst,
       'est_total_pct_best_raw': round(pnl_best / BASE_TOTAL * 100, 4),
       'est_total_pct_worst_raw': round(pnl_worst / BASE_TOTAL * 100, 4),
       'total_mv': new_total, 'tracks': tracks,
       'med_exposure': med, 'med_pct': round(med / new_total * 100, 2),
       'threshold_all_med': threshold_all, 'threshold_a_sh_med': threshold_sh,
       'board_med': BOARD_MED, 'leader_med': LEADER_MED, 'lag_med': LAG_MED,
       'board_detail': {'000933': BRD['sh000933'], '399989': BRD['sz399989'],
                        '512170': ETFP['sh512170'], '159938': ETFP['sz159938'],
                        '000913': BRD['sh000913'], '399997': BRD['sz399997'],
                        '000932': IDXP['sh000932'], '399975': BRD['sz399975'],
                        '000934': BRD['sh000934'], '000827': BRD['sh000827']},
       'active_mult': active_mult, 'proxy_check': proxy_check,
       'est_2708': EST_2708, 'peer_avg_2708': PEER_AVG, 'k_2708': {'med': K_MED, 'min': K_MIN, 'max': K_MAX},
       'proxy_180': PROXY_180,
       'hk_split': {k: round(v, 2) for k, v in hk.items()},
       'hk_split_pnl': {k: round(v, 2) for k, v in hk_pnl.items()},
       'hk_total': round(sum(hk.values()), 2), 'hk_total_pct': round(sum(hk.values()) / new_total * 100, 2),
       'qdii_applied': [{'code': c, 'name': n, 'nav_date': d, 'nav': v, 'pct': p} for c, n, d, v, p in qdii_applied],
       'nav28': [{'code': c, 'name': n, 'nav': v, 'pct': p, 'imp': i} for c, n, v, p, i in nav28],
       'detail': detail,
       'proxy_used': [{'code': c, 'name': n, 'nd': nd, 'reason': r} for c, n, nd, r in missing],
       'note': ('9/28 复市首日 A股+港股同日收盘；17 只场外基金出 9/28 真实净值；'
                '002708 净值未出→同侪法估算；001180→按 000933 代理；002742→计0；'
                '000369/016280 最新净值日仍 9/23（基准已含）→计 0（连续第 5 档未出库）；'
                '164906 新到 9/24 净值 0.8864→真实兑现 −0.5945%')}

json.dump(out, open(os.path.join(HIST, 'portfolio_close_' + TODAYC + '.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)

print('\n未出净值/需估算:', [(m[0], m[1], m[3]) for m in missing])
print(f'\n★ 组合 {total_pct:+.4f}% ({total_pnl:+,.2f} 元)  总资产 {new_total:,.2f} (基准 {BASE_TOTAL:,.2f})')
print(f'  上界(最优) {round(pnl_best/BASE_TOTAL*100,4):+.4f}% ({pnl_best:+,.2f} 元) ~ 下界(最差) {round(pnl_worst/BASE_TOTAL*100,4):+.4f}% ({pnl_worst:+,.2f} 元)')
print(f'  BOARD_MED={BOARD_MED}  300医药={LEADER_MED}  LAG_MED={LAG_MED}')
print(f'  002708 估算 {EST_2708["central"]:+.4f}%（同侪均值 {PEER_AVG:+.4f}% × k {K_MED}）')
print(f'  医药敞口 {out["med_pct"]:.2f}%  门槛(全部医药) {threshold_all:+.2f}% / (仅A股医药) {threshold_sh:+.2f}%')
print(f'\n港股双层拆解：纯恒科 {hk["pure"]:,.2f} / 中概互联 {hk["concept"]:,.2f} / 宽基恒生系 {hk["broad"]:,.2f} → 合计 {sum(hk.values()):,.2f} 元 ({sum(hk.values())/new_total*100:.2f}%)')
print(f'  当日盈亏：纯恒科 {hk_pnl["pure"]:+,.2f} / 中概互联 {hk_pnl["concept"]:+,.2f} / 宽基恒生系 {hk_pnl["broad"]:+,.2f}')
print('\n赛道:')
for k, v in sorted(tracks.items(), key=lambda kv: -kv[1]['mv0']):
    print(f"  {k:10s} mv0={v['mv0']:>11,.2f} w={v['pct_of_total']:>6.2f}% day={v['day_pct']:+.3f}% pnl={v['pnl']:>+10,.2f} ({v['pnl_best']:+,.2f}~{v['pnl_worst']:+,.2f})")
print('\n主动医药基当日幅度 vs 板块代理:')
for c, v in active_mult.items():
    print(f"  {c} {v['name'][:10]:10s} {v['real_pct']:+.3f}%  ×BOARD_MED={v['mult_vs_board_med']}  ×300医药={v['mult_vs_300med']}  {'[估算]' if v['estimated'] else '[真实]'}")
print('\n个券贡献（按 |pnl| 排序前 26）:')
for d in sorted(detail, key=lambda y: -abs(y['est_pnl']))[:26]:
    print(f"  {d['track']:10s} {d['name'][:22]:22s} {str(d['code']):9s} {d['est_pct']:+8.3f}% pnl={d['est_pnl']:>+10,.2f}  [{d['price_src'][:70]}]")
