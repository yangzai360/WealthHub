# -*- coding: utf-8 -*-
"""2026-09-30 盘后：组合收盘估算（链式法，§3.79/§3.97/§3.100/§3.105/§3.109/§3.111/§3.112a 口径）

base = portfolio_close_20260929_fix.json（9/29 修正收盘 = 376,491.53 元）
  §3.111/§3.112a 强制：逐券还原式由「机器可验证判据」选出

本档定价覆盖（9/30 正常交易日 · 国庆长假前最后一个 A股交易日；A股 15:00 / 港股 16:00 收盘）：
  · 场内（ETF/个股 10 行）= 9/30 收盘价（hq 直连）
  · 场外 13 只出 9/30 真实净值
  · 000727 / 161616（A股主动医药基）9/30 净值未出 → 板块代理 × §3.97 折中弹性（±1.00pct 带）
  · 002708（A股主动医药基，2 行）9/30 净值未出 → 同上
  · 001180（被动联接）9/30 未出 → 中证医药指数代理（§3.103）
  · 110020（沪深300联接）未出 → 沪深300 代理
  · 002742（债券，9.4 元）/ 004752（0.95 元）→ 计 0
  · 000369 / 016280（QDII 广发全球医疗 A/C，4 行）= 净值日仍停 9/28 → 计 0（US 9/29 挂账）
  · 164906（交银海外互联 LOF，2 行）= 净值日停 9/28 → 计 0

⚠️ 9/30 执行「恒生科技 0.5% 纪律减仓 1,882.46 元」（9/29 收盘级破位触发）：
   按「全额持有参与 9/30 收益（P&L 口径不变）+ 减仓后权重单列」处理（价值中性，总额不变）
输出：portfolio_close_20260930.json
"""
import json, os, re

BASE = '/Users/jieyang/Documents/WealthHub'
HIST = os.path.join(BASE, 'data/processed/history')
TODAY = '2026-09-30'
TODAYC = TODAY.replace('-', '')

base = json.load(open(os.path.join(HIST, 'portfolio_close_20260929_fix.json'), encoding='utf-8'))
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

# ---------- 1. 价格表（9/30 收盘） ----------
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


# ---------- 2. 板块/指数代理（9/30 收盘） ----------
BRD = {x['code']: x['pct'] for x in cur['boards']}
ETFP = {x['code']: x['pct'] for x in cur['etf']}
IDXP = {x['code']: x['pct'] for x in cur['indices']}
BOARD_MED = round((BRD['sh000933'] + BRD['sz399989'] + ETFP['sh512170'] + ETFP['sz159938']) / 4, 4)
LEADER_MED = BRD['sh000913']            # 300医药
LAG_MED = round((BRD['sh000933'] + BRD['sz399989'] + ETFP['sh512170']) / 3, 4)
print(f'BOARD_MED={BOARD_MED}%  300医药={LEADER_MED}%  LAG_MED={LAG_MED}%')

# ---------- 3. 未出净值主动基：板块代理 × §3.97 折中弹性（±1.00pct 带） ----------
# §3.97 折中口径弹性：002708 / 161616 / 000727 = 1.64 / 1.29 / 0.81（相对 BOARD_MED）
# ⚠️ 本档无「同侪真实锚」（A股主动医药基 9/30 净值全部未出）→ 退化为板块代理口径，
#    并显式给出 ±1.00pct 带（依据：9/23-9/24 两档实测「代理 vs 真实」偏差上界约 0.45~0.90pct）
K = {'002708': 1.64, '161616': 1.29, '000727': 0.81}
BAND = 1.00
EST_PEER = {}
for c in K:
    central = round(BOARD_MED * K[c], 4)
    EST_PEER[c] = {'central': central, 'best': round(central + BAND, 4), 'worst': round(central - BAND, 4)}
print(f'板块代理口径（无同侪真实锚）：002708={EST_PEER["002708"]["central"]:+.4f}% / '
      f'161616={EST_PEER["161616"]["central"]:+.4f}% / 000727={EST_PEER["000727"]["central"]:+.4f}%（band ±{BAND}pct）')

# ---------- 3b. 被动联接的指数代理（§3.103：代理指数 = 标的实际跟踪指数） ----------
PASSIVE_PROXY = {'001180': ('中证医药', BRD['sh000933']), '110020': ('沪深300', IDXP['sh000300'])}

# ---------- 4. 逐券定价 ----------
detail, missing, qdii_applied, nav30 = [], [], [], []
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
        src = f'场内收盘 9/30 {PX[code6]}（基准 {round(imp,4)}）'
    elif code6 in EST_PEER:
        pct = EST_PEER[code6]['central']
        pct_best = EST_PEER[code6]['best']
        pct_worst = EST_PEER[code6]['worst']
        src = (f'9/30 净值未出(最新 {NAV.get(code6, (None,))[0]}) → 板块代理口径：BOARD_MED {BOARD_MED:+.4f}% × k{K[code6]} '
               f'= {pct:+.4f}%（带 ±{BAND}pct：{pct_worst:+.4f}% ~ {pct_best:+.4f}%）')
        missing.append((code6, x['name'], NAV.get(code6, (None,))[0], 'A股主动医药基净值未出→板块代理估算'))
    elif code6 in PASSIVE_PROXY:
        lab, idxp = PASSIVE_PROXY[code6]
        pct = pct_best = pct_worst = round(idxp, 4)
        src = f'9/30 净值未出 → {lab} 指数代理 {idxp:+.2f}%（§3.103 被动联接按指数代理）'
        missing.append((code6, x['name'], NAV.get(code6, (None,))[0], f'被动联接未出→{lab}指数代理'))
    elif code6 in NAV:
        nd, nav = NAV[code6]
        imp = v0 / sh
        base_nd = parse_base_nav_date(x.get('price_src', ''))
        if nd == TODAY:
            pct = pct_best = pct_worst = round((nav / imp - 1) * 100, 4)
            src = f'净值 9/30 ({nav})，基准净值日 {base_nd}'
            nav30.append((code6, x['name'], nav, pct, round(imp, 4)))
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
# §3.116b：按「结果值 min/max」判定 low/high，禁止把弹性常量硬绑定到档位
scen_low, scen_high = sorted([pnl_best, pnl_worst])

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

# ---- 9/30「恒生科技 0.5% 纪律减仓 1,882.46 元」的减仓后权重（价值中性，P&L 口径不变） ----
DISCIPLINE = {'date': TODAY, 'kind': '恒生科技 0.5% 纪律减仓（9/29 收盘级破位触发）',
              'amount': 1882.46, 'settle': '按 9/30 净值成交（价值中性，P&L 口径不变）',
              'target': '纯恒科口径（012348 优先 / 513180 备选）',
              'not_target': '513050 / 164906（中概口径，与触发源不一致）'}
weight_after = {k: v['mv'] / new_total * 100 for k, v in tracks.items()}
weight_after['恒生科技'] -= DISCIPLINE['amount'] / new_total * 100
weight_after['现金'] += DISCIPLINE['amount'] / new_total * 100
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
                          'estimated': True}

# ---- 被动联接类偏差检验（§3.103） ----
proxy_check = {}
for c, idx, lab in (('012323', BRD['sz399989'], '中证医疗'), ('000051', IDXP['sh000300'], '沪深300'),
                    ('000071', IDXP['sh000300'], '沪深300(A股口径,参考)'), ('001551', BRD['sh000933'], '中证医药')):
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

# ---- 结构与顺序（300医药 / 中证医疗 / 中证医药 三级） ----
order = sorted([('300医药', BRD['sh000913']), ('中证医疗', BRD['sz399989']), ('中证医药', BRD['sh000933'])],
               key=lambda y: -y[1])

out = {'date': TODAY, 'as_of': '2026-09-30收盘',
       'session_type': 'normal_trading_day_close_last_before_holiday',
       'base_total': BASE_TOTAL, 'base_file': 'portfolio_close_20260929_fix.json',
       'restore_rule_used': restore_rule, 'restore_dev': restore_dev,
       'restore_rule_all': {k: v for k, v in dev_all.items()},
       'est_total_pnl': total_pnl, 'est_total_pct': round(total_pct, 2),
       'est_total_pct_raw': total_pct,
       'est_total_pnl_best': pnl_best, 'est_total_pnl_worst': pnl_worst,
       'est_total_pnl_high': scen_high, 'est_total_pnl_low': scen_low,
       'est_total_pct_best_raw': round(pnl_best / BASE_TOTAL * 100, 4),
       'est_total_pct_worst_raw': round(pnl_worst / BASE_TOTAL * 100, 4),
       'total_mv': new_total, 'tracks': tracks,
       'discipline': {**DISCIPLINE, 'weight_after': weight_after},
       'med_exposure': med, 'med_pct': round(med / new_total * 100, 2),
       'threshold_all_med': threshold_all, 'threshold_a_sh_med': threshold_sh,
       'board_med': BOARD_MED, 'leader_med': LEADER_MED, 'lag_med': LAG_MED,
       'board_detail': {'000933': BRD['sh000933'], '399989': BRD['sz399989'],
                        '512170': ETFP['sh512170'], '159938': ETFP['sz159938'],
                        '000913': BRD['sh000913'], '399997': BRD['sz399997'],
                        '000932': IDXP['sh000932'], '399975': BRD['sz399975'],
                        '000934': BRD['sh000934'], '000827': BRD['sh000827']},
       'idx': {'000001': IDXP['sh000001'], '399006': IDXP['sz399006'],
               '000300': IDXP['sh000300'], '000688': IDXP['sh000688'],
               '399001': IDXP['sz399001'],
               'HSTECH': [x['pct'] for x in cur['hk'] if x['code'] == 'HSTECH'][0],
               'HSI': [x['pct'] for x in cur['hk'] if x['code'] == 'HSI'][0],
               'HSHCI': [x['pct'] for x in cur['hk'] if x['code'] == 'HSHCI'][0]},
       'hk_mkt': {x['code']: {'close': x['close'], 'pct': x['pct'], 'high': x['high'], 'low': x['low']}
                  for x in cur['hk']},
       'hk_stocks': {x['name']: {'close': x['close'], 'pct': x['pct']} for x in cur['hk_stocks']},
       'active_mult': active_mult, 'proxy_check': proxy_check,
       'peer_2708_pct': None, 'est_peer': EST_PEER, 'k_elastic': K, 'est_band': BAND,
       'structure_order': [o[0] for o in order], 'structure_pct': {o[0]: o[1] for o in order},
       'hk_split': {k: round(v, 2) for k, v in hk.items()},
       'hk_split_pnl': {k: round(v, 2) for k, v in hk_pnl.items()},
       'hk_total': round(sum(hk.values()), 2), 'hk_total_pct': round(sum(hk.values()) / new_total * 100, 2),
       'qdii_applied': [{'code': c, 'name': n, 'nav_date': d, 'nav': v, 'pct': p,
                         'base_nav_date': b, 'base_nav': i} for c, n, d, v, p, b, i in qdii_applied],
       'nav30': [{'code': c, 'name': n, 'nav': v, 'pct': p, 'base_nav': i} for c, n, v, p, i in nav30],
       'detail': detail,
       'proxy_used': [{'code': c, 'name': n, 'nd': nd, 'reason': r} for c, n, nd, r in missing],
       'note': ('9/30 正常交易日（节前最后一个 A股交易日）；场内 10 行按 9/30 收盘价；场外 13 只出 9/30 真实净值；'
                '002708/161616/000727（A股主动医药基）净值未出 → 板块代理口径（BOARD_MED × k，带 ±1.00pct）；'
                '001180 → 中证医药指数代理、110020 → 沪深300 指数代理；002742/004752 计 0；'
                '000369/016280/164906 净值日仍停 9/28 → 计 0（US 9/29 挂账）。'
                '⚠️ 恒生科技 0.5% 纪律减仓 1,882.46 元按「价值中性、权重单列」处理（P&L 口径不变）')}

json.dump(out, open(os.path.join(HIST, 'portfolio_close_' + TODAYC + '.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)

print('\n未出净值/需估算:', [(m[0], m[1], m[3]) for m in missing])
print(f'\n★ 组合 {total_pct:+.4f}% ({total_pnl:+,.2f} 元)  总资产 {new_total:,.2f} 元 (基准 {BASE_TOTAL:,.2f} 元)')
print(f'  上界 {round(scen_high/BASE_TOTAL*100,4):+.4f}% ({scen_high:+,.2f} 元) ~ 下界 {round(scen_low/BASE_TOTAL*100,4):+.4f}% ({scen_low:+,.2f} 元)')
print(f'\n赛道:')
for k, v in sorted(tracks.items(), key=lambda kv: -kv[1]['mv0']):
    print(f"  {k:10s} mv0={v['mv0']:>11,.2f} w={v['pct_of_total']:>6.2f}% day={v['day_pct']:+.3f}% pnl={v['pnl']:>+10,.2f} ({v['pnl_worst']:+,.2f}~{v['pnl_best']:+,.2f})")
print(f'\n减仓后权重: ' + ' / '.join(f'{k} {v:.2f}%' for k, v in weight_after.items()))
print(f'\n医药敞口 {out["med_pct"]:.2f}%  门槛(全部医药) {threshold_all:+.2f}% / (仅A股医药) {threshold_sh:+.2f}%')
print(f'\n港股双层拆解：纯恒科 {hk["pure"]:,.2f} / 中概互联 {hk["concept"]:,.2f} / 宽基恒生系 {hk["broad"]:,.2f} → 合计 {sum(hk.values()):,.2f} 元 ({sum(hk.values())/new_total*100:.2f}%)')
print(f'  当日盈亏：纯恒科 {hk_pnl["pure"]:+,.2f} / 中概互联 {hk_pnl["concept"]:+,.2f} / 宽基恒生系 {hk_pnl["broad"]:+,.2f}')
print('\n结构顺序:', ' > '.join(f'{o[0]} {o[1]:+.2f}%' for o in order))
print('\n主动医药基当日幅度（全部为板块代理估算） vs 板块代理:')
for c, v in active_mult.items():
    print(f"  {c} {v['name'][:10]:10s} {v['real_pct']:+.3f}%  ×BOARD_MED={v['mult_vs_board_med']}  ×300医药={v['mult_vs_300med']}")
print('\n被动联接偏差检验（真实净值 vs 指数）:')
for c, v in proxy_check.items():
    print(f"  {c} 真实 {v['real']:+.4f}% vs {v['label']} {v['index']:+.2f}% → dev {v['dev']:+.4f}pct")
print('\n个券贡献（按 |pnl| 排序前 26）:')
for d in sorted(detail, key=lambda y: -abs(y['est_pnl']))[:26]:
    print(f"  {d['track']:10s} {d['name'][:22]:22s} {str(d['code']):9s} {d['est_pct']:+8.3f}% pnl={d['est_pnl']:>+9,.2f}  [{d['price_src'][:70]}]")
