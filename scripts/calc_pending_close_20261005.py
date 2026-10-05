# -*- coding: utf-8 -*-
"""2026-10-05 盘后档：组合台账（档型②混合档 · A股休市 + 港股续市第 2 日收盘）
① 基准 = portfolio_close_20260930_fix.json（380,888.29 元，tracks[].mv 求和硬守卫）
② 港股 10/5 **收盘**已成型 → 产出 `portfolio_pending_20261005.json` **正式版**（state=finalized / finalized=true，
   覆盖 08:00 预登记版 state=preopen_estimate）（§3.121b）
③ 当日可实现盈亏 = 0 元（归因「标的不可定价」，§3.107；A股 休市 → 场外无净值、场内无成交价）
④ 恒生科技 4,250 防线：**破位状态未改变**（10/5 收 4,183.68 < 4,250），
   第 2 次 0.5% 纪律减仓 1,904.44 元 判定已于 10/2 锁定、执行待 10/8（§3.114c 不重复判定、不叠加）
⑤ 待消化（港股腿三段法，**累积窗口第 2 日 = 10/2 收盘 × 10/5 收盘，几何复合**，§3.126c）：
   只给区间上下界（low = min(结果值) / high = max(结果值)，§3.116b / §3.123b）
⑥ QDII 挂账（本档无新增美股交易日 → 沿用上一档并声明；§3.122c③）
⑦ 情绪双口径（名义净分 + 暴露加权）
⑧ 医药敞口 + 门槛（§3.98 方程解法）
⚠️ 混合档不产 portfolio_close_*、不向链式序列插入 0% 行（§3.108 条款 22、§3.122c）
⚠️ §3.126d：结构化字段必检清单 = 周窗口串 / hk_pending_digest 结构 / 路径类文件名 / 段级 min-max
⚠️ 本次为全新撰写（非 sed 派生），读写路径 = 20261005 / 2026-10-05
"""
import json, os, csv, itertools
from collections import defaultdict

BASE = '/Users/jieyang/Documents/WealthHub'
TODAY = '2026-10-05'
HIST = os.path.join(BASE, 'data/processed/history')

# ---------- 1. 基准 ----------
fix = json.load(open(os.path.join(HIST, 'portfolio_close_20260930_fix.json'), encoding='utf-8'))
total_mv = fix.get('total_mv')
tracks_fix = fix.get('tracks') or {}
restored = {tr: v.get('mv') for tr, v in tracks_fix.items() if v.get('mv') is not None}
s = sum(restored.values())
BASE_TOTAL = total_mv
print(f'基准 total_mv(文件) = {total_mv:,.2f}    Σ tracks.mv = {s:,.2f}    dev = {s-total_mv:+.4f}')
assert abs(s - total_mv) < 1.5, f'硬守卫失败: Σ tracks[].mv {s:.2f} vs total_mv {total_mv}'
print('✅ 硬守卫通过：|Σ tracks[track].mv − total_mv| < 1.5')
for k, v in sorted(restored.items(), key=lambda x: -x[1]):
    print(f'  {k:12s} {v:>12,.2f} 元  {v/BASE_TOTAL*100:>6.2f}%')

# ---------- 2. 港股收盘 ----------
hq = json.load(open(os.path.join(HIST, 'close_hq_20261005.json'), encoding='utf-8'))
hk = hq['indices_hk']
stk = hq['hk_stocks']
print('\n=== 港股指数（2026-10-05 收盘）===')
for k, v in hk.items():
    print(f"  {k:10s} {v['cur']:>11.3f} {v['pct']:>+7.2f}%  H{v['high']} L{v['low']}  date_field={v['date_field']}")
print('=== 港股权重股（收盘）===')
for k, v in stk.items():
    print(f"  {k:16s} {v['cur']:>9.2f} {v['pct']:>+7.2f}%")


def pct(cur, prev):
    return round((cur / prev - 1) * 100, 4)


HSTECH_CUR, HSTECH_PREV = hk['恒生科技']['cur'], hk['恒生科技']['prev']
HSTECH_PCT = pct(HSTECH_CUR, HSTECH_PREV)
HSI_PCT = pct(hk['恒生指数']['cur'], hk['恒生指数']['prev'])
HSCI_PCT = pct(hk['恒生综合']['cur'], hk['恒生综合']['prev'])
print(f"\n收盘口径涨跌：HSTECH {HSTECH_PCT:+.4f}%（新浪报告 {hk['恒生科技']['pct']:+.2f}%）｜"
      f"HSI {HSI_PCT:+.4f}%｜HSCI {HSCI_PCT:+.4f}%")

NET8 = ['腾讯控股', '阿里巴巴-W', '小米集团-W', '京东集团-SW', '美团-W', '网易-S', '快手-W', '百度集团-SW']
NET6 = ['腾讯控股', '阿里巴巴-W', '京东集团-SW', '美团-W', '网易-S', '百度集团-SW']
p8 = sum(stk[c]['pct'] for c in NET8) / len(NET8)
p6 = sum(stk[c]['pct'] for c in NET6) / len(NET6)
print(f'中概互联代理（收盘）：8 名等权 = {p8:+.4f}%（最差代理）；6 名大市值平台 = {p6:+.4f}%（最优代理）')

# 10/2 收盘段（上一档已定价段，来自 portfolio_pending_20261002.json 的 hk_pending_digest）
PREV = {'pure_hstech': -2.2556, 'china_internet': [-2.8087, -2.3517], 'broad_hk': [-2.6042, -2.5776]}

# ---------- 3. 当日可实现盈亏 ----------
UNPRICED = [
    'A股 10/1-10/7 休市 → 20 只 A股类场外基金不发布净值、A股指数无新收盘（末行仍 = 2026-09-30）',
    '场内 ETF / LOF（513050 / 513180 / 159920 / 159928 等，沪深交易所）无交易时段 → 无成交价（本档实测 date_field 全部 = 2026-09-30）',
    '场外港股联接（000071 / 012348）在 A股休市期不发布净值（§3.112i）',
    '港股 10/5 已开市并收盘（恒生科技 4,183.68 / +0.62%），但组合未直接持有港股正股或港交所上市工具 → 港股行情不产生组合层当日定价',
    '美股 10/5 未收盘（北京 10/5 20:00 = 美东 10/5 08:00 EDT），US 10/2 收盘已于 10/4 档入库，其组合传导属 QDII 挂账项、不在本档基准内',
]
print('\n=== 组合当日估算（混合档盘后）===')
print('全部持仓标的不可定价 → 当日可实现盈亏 = 0.00 元（0.000%）；估算总资产维持 '
      f'{BASE_TOTAL:,.2f} 元（归因「标的不可定价」而非「市场持平」，§3.107）')
for i, r in enumerate(UNPRICED, 1):
    print(f'  归因{i}: {r}')

# ---------- 4. 待消化（港股腿三段法 · 累积窗口第 2 日，几何复合） ----------
hk_seg = {'pure_hstech': 17017.68, 'china_internet': 14555.16, 'broad_hk': 18451.42}
HK_TOTAL = sum(hk_seg.values())
print(f'\n=== 港股腿「待消化」三段法（累积窗口第 2 日 / 共 4 日：10/2、10/5、10/6、10/7）===')
print(f'  港联系总暴露 {HK_TOTAL:,.2f} 元 = {HK_TOTAL/BASE_TOTAL*100:.2f}%'
      f'（赛道层 {hk_seg["pure_hstech"]+hk_seg["china_internet"]:,.2f} 元 = '
      f'{(hk_seg["pure_hstech"]+hk_seg["china_internet"])/BASE_TOTAL*100:.2f}%；'
      f'宽基恒生系 {hk_seg["broad_hk"]:,.2f} 元 = {hk_seg["broad_hk"]/BASE_TOTAL*100:.2f}%）')


def cum(r1, r2):
    """§3.126c：跨档累积一律几何复合"""
    return ((1 + r1 / 100) * (1 + r2 / 100) - 1) * 100


LEG = {
    'pure_hstech': {'nm': '纯恒生科技系（012348 ×2 + 513180）',
                    'prev': [PREV['pure_hstech']], 'today': [HSTECH_PCT]},
    'china_internet': {'nm': '中概·海外互联系（513050 + 164906 ×2）',
                       'prev': PREV['china_internet'], 'today': [p8, p6]},
    'broad_hk': {'nm': '宽基恒生系（000071 ×2 + 159920）',
                 'prev': PREV['broad_hk'], 'today': [HSCI_PCT, HSI_PCT]},
}
rows = {}
for leg, mv in hk_seg.items():
    lp = LEG[leg]
    combos = [cum(a, b) for a in lp['prev'] for b in lp['today']]
    outs = [mv * c / 100 for c in combos]
    rows[leg] = {'mv': mv, 'prev': lp['prev'], 'today': lp['today'],
                 'cum': combos, 'outs': outs}
    print(f"  {lp['nm']:38s} {mv:>11,.2f} 元  上一段 " + ' / '.join(f'{p:+.4f}%' for p in lp['prev']) +
          '  × 本段 ' + ' / '.join(f'{p:+.4f}%' for p in lp['today']) +
          '\n' + ' ' * 41 + '累积 ' + ' / '.join(f'{c:+.4f}%' for c in combos) +
          '  →  ' + ' / '.join(f'{o:+.2f} 元' for o in outs))
# ⚠️ §3.116b / §3.123b / §3.126d：low/high 必须按「合计结果值」的 min/max，禁止对各段极值直接取 min/max
combos_all = [sum(c) for c in itertools.product(*[rows[l]['outs'] for l in ('pure_hstech', 'china_internet', 'broad_hk')])]
HK_LOW, HK_HIGH = min(combos_all), max(combos_all)
# 参考中枢（代理均值口径，非点值预告）
mid_exact = (hk_seg['pure_hstech'] * cum(PREV['pure_hstech'], HSTECH_PCT) / 100
             + hk_seg['china_internet'] * cum(sum(PREV['china_internet']) / 2, (p8 + p6) / 2) / 100
             + hk_seg['broad_hk'] * cum(sum(PREV['broad_hk']) / 2, (HSCI_PCT + HSI_PCT) / 2) / 100)
print(f"  {'港联系合计（三段）':38s} {HK_TOTAL:>11,.2f} 元  组合数 {len(combos_all)}  "
      f"low {HK_LOW:>+9,.2f} 元 ｜ high {HK_HIGH:>+9,.2f} 元 ｜ 代理均值口径参考中枢 {mid_exact:>+9,.2f} 元")
assert HK_LOW <= mid_exact <= HK_HIGH, f'⚠️ 中枢 {mid_exact:.2f} 未落在区间 [{HK_LOW:.2f}, {HK_HIGH:.2f}] 内 → 终止'
print(f"  → 区间 {HK_LOW:+,.2f} 元 ~ {HK_HIGH:+,.2f} 元（占基准 {HK_LOW/BASE_TOTAL*100:+.3f}% ~ {HK_HIGH/BASE_TOTAL*100:+.3f}%）")

track_combos = [hk_seg['pure_hstech'] * cum(PREV['pure_hstech'], HSTECH_PCT) / 100
                + hk_seg['china_internet'] * cum(a, b) / 100
                for a in PREV['china_internet'] for b in (p8, p6)]
track_low, track_high = min(track_combos), max(track_combos)
broad_combos = [hk_seg['broad_hk'] * cum(a, b) / 100 for a in PREV['broad_hk'] for b in (HSCI_PCT, HSI_PCT)]
print(f"  （仅赛道层 {hk_seg['pure_hstech']+hk_seg['china_internet']:,.2f} 元）区间 {track_low:+,.2f} 元 ~ {track_high:+,.2f} 元")
print(f"  （宽基恒生系单列）区间 {min(broad_combos):+,.2f} 元 ~ {max(broad_combos):+,.2f} 元")

# 单日段（10/5 当日，仅作对照，不入区间）
d_track = [hk_seg['pure_hstech'] * HSTECH_PCT / 100 + hk_seg['china_internet'] * b / 100 for b in (p8, p6)]
d_broad = [hk_seg['broad_hk'] * b / 100 for b in (HSCI_PCT, HSI_PCT)]
print(f"  （对照）10/5 单日段区间 {min(d_track)+min(d_broad):+,.2f} 元 ~ {max(d_track)+max(d_broad):+,.2f} 元")

# ---------- 5. 恒生科技防线（状态确认，非重新判定） ----------
print('\n=== 恒生科技 4,250 防线（状态确认，判定权已于 10/2 锁定）===')
Dv = HSTECH_CUR - 4250
print(f"  收盘 {HSTECH_CUR}（前收 {HSTECH_PREV}，{HSTECH_PCT:+.4f}%）距 4,250 = {Dv:+.3f} 点 / {Dv/4250*100:+.4f}%")
TRIGGER_NOW = HSTECH_CUR < 4250
print(f"  本档状态 = {'🔴 收盘价仍 < 4,250（破位状态未改变）' if TRIGGER_NOW else '🟢 已收回 4,250 上方（纪律不可撤销，§3.114c）'}")
print(f"  距 4,400 = {(HSTECH_CUR-4400)/4400*100:+.4f}%  距 4,300 = {(HSTECH_CUR-4300)/4300*100:+.4f}%"
      f"  自 9/22 高点 4,510.06 = {(HSTECH_CUR/4510.06-1)*100:+.4f}%")
print(f"  日内区间 {hk['恒生科技']['low']} ~ {hk['恒生科技']['high']}"
      f"（收盘距日内低 {((HSTECH_CUR-hk['恒生科技']['low'])/hk['恒生科技']['low']*100):+.3f}%、"
      f"距日内高 {((HSTECH_CUR-hk['恒生科技']['high'])/hk['恒生科技']['high']*100):+.3f}%）")
CUT_AMT = 1904.44          # 判定已于 10/2 锁定：380,888.29 × 0.5%
CUT1 = 1882.46             # 第 1 次（9/29 判定、9/30 成交）
CUM_CUT = round(CUT1 + CUT_AMT, 2)
print(f"  第 2 次 0.5% 纪律减仓额 = {CUT_AMT:,.2f} 元（判定锁定于 10/2，本档不重算、不叠加）")
HK_AFTER = round(31572.84 - CUM_CUT, 2)
CASH_AFTER = round(29212.97 + CUM_CUT, 2)
print(f"  累计纪律（§3.123e 累计口径）：{CUT1:,.2f} 元 + {CUT_AMT:,.2f} 元 = {CUM_CUT:,.2f} 元")
print(f"  纪律后（待 10/8 成交）：恒生科技 {HK_AFTER:,.2f} 元 = {HK_AFTER/BASE_TOTAL*100:.2f}%，"
      f"现金 {CASH_AFTER:,.2f} 元 = {CASH_AFTER/BASE_TOTAL*100:.2f}%")

# ---------- 6. 情绪（盘后窗口 14:00-20:00） ----------
sent = json.load(open(os.path.join(BASE, f'data/processed/news/sentiment-{TODAY}.json'), encoding='utf-8'))
WIN = '盘后(14:00-20:00)'
win = [x for x in sent['items'] if x.get('window') == WIN]
if not win:
    raise SystemExit('⚠️ 盘后窗口 sentiment 为 0 条 → 终止')
print(f'\n=== 情绪（盘后窗口 {len(win)} 条）===')
byt = defaultdict(lambda: {'n': 0, 'net': 0, 'sum': 0, 'pos': 0, 'neg': 0, 'neu': 0})
for x in win:
    t = byt[x['track']]
    t['n'] += 1
    t['sum'] += x['strength']
    if x['direction'] == '利多':
        t['net'] += x['strength']; t['pos'] += 1
    elif x['direction'] == '利空':
        t['net'] -= x['strength']; t['neg'] += 1
    else:
        t['neu'] += 1
nominal = sum(v['net'] for v in byt.values())
print(f'名义净情绪分（Σ利多强度 − Σ利空强度）= {nominal:+.1f}')
wsum = 0.0
wdetail = {}
for t, v in sorted(byt.items(), key=lambda x: -x[1]['n']):
    w = restored.get(t)
    if w is None:
        print(f"{t:12s} n={v['n']:>2d} 均值{v['sum']/v['n']:>6.1f} 净分{v['net']:>+7.1f}   (无直接暴露)        —")
        continue
    wt = w / BASE_TOTAL
    contrib = wt * (v['net'] / v['n'])
    wsum += contrib
    wdetail[t] = {'n': v['n'], 'mean_strength': round(v['sum'] / v['n'], 1), 'net': v['net'],
                  'weight_pct': round(wt * 100, 2), 'contrib': round(contrib, 3)}
    print(f"{t:12s} n={v['n']:>2d} 均值{v['sum']/v['n']:>6.1f} 净分{v['net']:>+7.1f} {wt*100:>6.2f}% {contrib:>+8.3f}")
print(f'暴露加权净分 = {wsum:+.3f}（名义的 {wsum/nominal*100 if nominal else 0:+.1f}%）')
sp = [x for x in win if x['direction'] == '利多' and x['strength'] >= 70]
sn = [x for x in win if x['direction'] == '利空' and x['strength'] >= 70]
print(f"强正 n={len(sp)} 均值 {round(sum(x['strength'] for x in sp)/len(sp),1) if sp else 0}")
print(f"强负 n={len(sn)} 均值 {round(sum(x['strength'] for x in sn)/len(sn),1) if sn else 0}")
alln = sent['items']
an = len(alln)
a_pos = sum(1 for x in alln if x['direction'] == '利多')
a_neg = sum(1 for x in alln if x['direction'] == '利空')
a_neu = sum(1 for x in alln if x['direction'] == '中性')
a_nom = sum(x['strength'] for x in alln if x['direction'] == '利多') - sum(x['strength'] for x in alln if x['direction'] == '利空')
a_mean = sum(x['strength'] for x in alln) / an
a_sp = [x for x in alln if x['direction'] == '利多' and x['strength'] >= 70]
a_sn = [x for x in alln if x['direction'] == '利空' and x['strength'] >= 70]
print(f'合并全档 {an} 条：{a_pos} 利多 / {a_neu} 中性 / {a_neg} 利空；净分 {a_nom:+d}；均值强度 {a_mean:.2f}；'
      f'强正 n={len(a_sp)} 均值 {round(sum(x["strength"] for x in a_sp)/len(a_sp),1) if a_sp else 0}；'
      f'强负 n={len(a_sn)} 均值 {round(sum(x["strength"] for x in a_sn)/len(a_sn),1) if a_sn else 0}')
bywin = defaultdict(lambda: {'n': 0, 'net': 0, 'sum': 0})
for x in alln:
    bw = bywin[x['window']]
    bw['n'] += 1
    bw['sum'] += x['strength']
    if x['direction'] == '利多':
        bw['net'] += x['strength']
    elif x['direction'] == '利空':
        bw['net'] -= x['strength']
for k, v in bywin.items():
    print(f"  窗口 {k}: n={v['n']} 净分={v['net']:+d} 均值={v['sum']/v['n']:.1f}")

# ---------- 7. 防线 / 敞口（其余） ----------
idx = defaultdict(dict)
with open(os.path.join(HIST, 'indices.csv'), encoding='utf-8-sig') as fh:
    for row in csv.DictReader(fh):
        try:
            idx[row['code']][row['date']] = float(row['close'])
        except Exception:
            pass
zz = idx.get('000932', {}).get('2026-09-30')
sh = idx.get('000001', {}).get('2026-09-30')
print(f'\n=== 其余防线 ===')
print(f'  中证消费 000932 = {zz}（9/30 收盘；A股 休市无更新）距 12,100 = {(zz-12100)/12100*100:+.4f}%、距 12,000 = {(zz-12000)/12000*100:+.4f}%')
print(f'  上证 000001 = {sh}（9/30 收盘）')
print(f'  A股医药反向兑现线：板块代理 +2.8697%（9/30 收盘口径）→ 未触发（方向相反）；下一验证 = 10/8')

med_mv = restored['A股医药'] + restored['美股标普医药']
med_pct = med_mv / BASE_TOTAL * 100
non_med = sum(v for k, v in restored.items() if k not in ('A股医药', '美股标普医药'))
A_sh, A_us = restored['A股医药'], restored['美股标普医药']
target = 0.40 * non_med / 0.60
th_all = (target / med_mv - 1) * 100
th_a = (target - A_us) / A_sh * 100 - 100
print(f'\n=== 医药敞口（§3.98 方程解法）===')
print(f'  总敞口 {med_mv:,.2f} 元 = {med_pct:.2f}%，距 40% 上限 {40-med_pct:.2f}pct；非医药对手盘 = {non_med:,.2f} 元；触线目标 = {target:,.2f} 元')
print(f'  门槛：医药两赛道单日同涨 +{th_all:.2f}% / 仅 A股医药 +{th_a:.2f}%（美股标普医药按 0）')

# ---------- 8. 敏感性（累积窗口 4 日，已定价 2 日） ----------
print('\n=== 敏感性：港联系累积窗口（4 日，已定价 2 日）===')
SENS = {}
for nm, p in (('bull_-1.0pct', -1.0), ('base_mid', mid_exact / HK_TOTAL * 100),
              ('bear_-5.0pct', -5.0), ('tail_-8.0pct', -8.0)):
    v = HK_TOTAL * p / 100
    SENS[nm] = round(v, 2)
    print(f'  {nm:20s} 累积 {p:+.3f}% → {v:>+11,.2f} 元（占基准 {v/BASE_TOTAL*100:+.3f}%）')

# ---------- 9. 输出（正式版 pending，覆盖预登记版） ----------
out = {
    'date': TODAY,
    'as_of': '2026-10-05 20:00（港股收盘后）',
    'state': 'finalized',
    'finalized': True,
    'finalized_at': '2026-10-05 20:00',
    'finalized_note': ('§3.121b：混合档 `portfolio_pending_<DATE>.json` 的正式版归属当日 20:00 盘后档，'
                       '以港股 10/5 收盘价重算并覆盖同文件名；本档已覆盖 08:00 预登记版（state=preopen_estimate）'),
    'session': 'close',
    'session_type': 'mixed_day_close',
    'session_type_note': ('档型②「混合档」= A股 休市（10/1-10/7）+ 港股续市第 2 个交易日**已收盘**（10/5 09:30-16:00）；'
                          '组合全部持仓标的仍不可定价（A股 休市 → 场外无净值、场内无成交价；组合未直接持有港交所上市工具）'),
    'base_total': BASE_TOTAL,
    'base_file': 'portfolio_close_20260930_fix.json',
    'base_guard_dev': round(s - total_mv, 4),
    'base_guard_rule': '|Σ tracks.mv − total_mv| < 1.5',
    'tracks': {k: {'mv': v, 'pct_of_total': round(v / BASE_TOTAL * 100, 2)} for k, v in restored.items()},
    'weights': {k: round(v / BASE_TOTAL * 100, 2) for k, v in restored.items()},
    'tracks_weight_after_cumulative_discipline': {'恒生科技': round(HK_AFTER / BASE_TOTAL * 100, 2),
                                                  '现金': round(CASH_AFTER / BASE_TOTAL * 100, 2)},
    'day_result': {
        'est_pnl': 0.0, 'est_pct': 0.0,
        'attribution': '全部持仓标的不可定价（非市场持平）',
        'reasons': UNPRICED,
        'note': '「0 元」是账面冻结，不构成任何方向判断（§3.107 / §3.117a / §3.118b）',
    },
    'hk_close': {
        'index': 'HSTECH', 'date': TODAY, 'close': HSTECH_CUR, 'prev_close': HSTECH_PREV,
        'pct': HSTECH_PCT, 'pct_sina_reported': hk['恒生科技']['pct'],
        'day_high': hk['恒生科技']['high'], 'day_low': hk['恒生科技']['low'],
        'date_field': hk['恒生科技']['date_field'], 'time_field': hk.get('恒生科技', {}).get('time_field'),
        'priced_for_today': True,
        'others': {k: {'close': v['cur'], 'pct': v['pct']} for k, v in hk.items()},
        'turnover_hkd_bn': 981.02,
        'southbound': '港股通（南向）10/1-10/7 全程暂停、10/8 恢复 → 本档为南向空窗第 2 日',
        'note': ('港股 10/5 收盘数据（新浪 hq 直连、返回体日期字段 2026/10/05 16:08:26），'
                 '已写入 indices.csv 真实收盘行并覆盖 13:45 伪收盘行（§3.122a / §3.126a）'),
    },
    'defense_hstech_4250': {
        'close': HSTECH_CUR, 'prev_close': HSTECH_PREV, 'line': 4250,
        'dist_pts': round(Dv, 3), 'dist_pct': round(Dv / 4250 * 100, 4),
        'state': 'close_level_break_unchanged' if TRIGGER_NOW else 'recovered_above_4250_but_discipline_locked',
        'trigger_recheck': False,
        'trigger_recheck_note': ('§3.114c：判定权已于 10/2 收盘级锁定（4,157.94 破位 −2.1661%），'
                                 '本档只做「破位状态未改变」的事实确认，**不重复判定、不叠加新纪律**；'
                                 '同日防线只触发一次，即使收盘站上 4,250 已登记的第 2 次减仓亦须于 10/8 执行'),
        'break_type': '非边际破位（10/2 距防线 −2.1661%）；10/5 收盘距防线 −1.5605%，破位幅度收窄但仍成立',
        'action': '第 2 次 0.5% 纪律减仓',
        'cut_pct': 0.5, 'cut_amount': CUT_AMT,
        'cut_basis': f'{BASE_TOTAL:,.2f} 元 × 0.5%（§3.114c / §3.123e 确定性口径，判定锁定于 10/2）',
        'cut_targets': ['012348（天弘恒生科技联接A）', '513180（恒生科技ETF华夏）'],
        'cut_target_rule': '标的限「纯恒科」口径，不落在中概（513050 / 164906）',
        'executed': False, 'execution_pending': True, 'execute_at': '2026-10-08（A股 + 港股通复市首日）',
        'execution_note': ('A股 休市期组合不可交易：场内 ETF 无交易时段、场外联接不发净值、港股通关闭 → '
                           '本档仅完成「状态确认」，实际成交与结算待 10/8 按当日净值执行'),
        'prev_intraday_ref': {'as_of': '2026-10-05 13:45', 'price': 4163.63,
                              'note': '盘中档报 +0.14%；收盘 4,183.68 / +0.62%，尾盘走高（低开高走形态）'},
        'correction_note': ('⚠️ 口径更正披露：10/4 档记「纪律后 恒生科技 29,668.40 元 = 7.79% / 现金 31,117.41 元 = 8.17%」，'
                            '该口径只扣第 2 次减仓、未扣第 1 次已成交的 1,882.46 元 → 本档统一为累计口径（§3.123e）'),
    },
    'hk_pending_digest': {
        'window': ['2026-10-02', '2026-10-05', '2026-10-06', '2026-10-07'],
        'priced_days': 2, 'total_days': 4,
        'as_of': '2026-10-05 收盘（港股真实收盘价，累计 10/2 + 10/5 两段）',
        'cumulative_note': '累积口径 = 各段代理涨跌**几何复合**（§3.126c），非简单相加',
        'segments': {
            leg: {'mv': rows[leg]['mv'],
                  'prev_segment_pct': [round(p, 4) for p in rows[leg]['prev']],
                  'today_segment_pct': [round(p, 4) for p in rows[leg]['today']],
                  'cum_pct': [round(c, 4) for c in rows[leg]['cum']],
                  'outs': [round(o, 2) for o in rows[leg]['outs']]} for leg in rows},
        'proxies_used': {'pure_hstech': 'HSTECH 收盘涨跌',
                         'china_internet': '8 名等权（最差）/ 6 名大市值平台（最优）',
                         'broad_hk': '恒生综合 / 恒生指数（四组合取 min/max 于**合计结果值**上，§3.116b / §3.123b）'},
        'hk_total': HK_TOTAL, 'hk_pct': round(HK_TOTAL / BASE_TOTAL * 100, 2),
        'total_low': round(HK_LOW, 2), 'total_high': round(HK_HIGH, 2),
        'mid_proxy_avg': round(mid_exact, 2),
        'track_only_low': round(track_low, 2), 'track_only_high': round(track_high, 2),
        'broad_hk_low': round(min(broad_combos), 2), 'broad_hk_high': round(max(broad_combos), 2),
        'day_only_1005_low': round(min(d_track) + min(d_broad), 2),
        'day_only_1005_high': round(max(d_track) + max(d_broad), 2),
        'finalized': True,
        'rule': ('§3.108 条款 23/24 + §3.116b + §3.126c：三段法 + 几何复合 + low=min(结果值)/high=max(结果值)、'
                 '只给区间上下界、不得作方向判断；本档为累积窗口第 2 日（10/2、10/5、10/6、10/7 共 4 日），尚有 2 日未走完'),
        'holiday_rule_note': ('10/6、10/7 两个港股交易日南向资金仍缺席（港股通 10/1-10/7 暂停、10/8 恢复）→ '
                              '按「外资 + 本地资金主导定价、波动率上修」建模（§3.115d / §3.121e）；'
                              '10/5 成交 981.02 亿港元、较 10/2 的 1,458.04 亿缩量 32.7%，承接变薄证据'),
    },
    'qdii_pending': {
        'refreshed': False,
        'reason': '本档无新增美股交易日入库（US 10/3-10/4 为周末、US 10/5 收盘成型于北京 10/6 04:00；北京 10/5 20:00 = 美东 10/5 08:00，尚未开盘，§3.120c）→ 挂账区间沿用上一档值',
        'component_a': {'desc': 'QDII 000369/016280 的 9/29 净值（基准净值日 9/28）', 'amount': -267.82,
                        'trade_date_covered': '2026-09-29'},
        'component_b': {'desc': 'US 9/30 −1.17% × 10/1 −1.62% × 10/2 +0.00% 复合 −2.7710%（IYH 口径）',
                        'trade_dates_covered': ['2026-09-30', '2026-10-01', '2026-10-02'],
                        'notional': -1652.77,
                        'low': -1487.5, 'mid': -1190.0, 'high': -991.66, 'coef_range': [0.6, 0.9]},
        'total_low': -1755.32, 'total_mid': -1457.82, 'total_high': -1259.48,
        'unknown_sessions': ['2026-10-05', '2026-10-06', '2026-10-07'],
        'coef_note': ('§3.118a：长假前后实测隐含系数 1.25~1.29，远超标定 0.72 / 常态实测 0.62（§3.114e）'
                      '→ 只给区间、禁止中枢点值；系数未重估前基于该系数的一切仓位决策无效'),
        'us_leg_fact': {'as_of': '美东 10/2', 'XLV': -0.0120, 'IYH': 0.0,
                        'note': '10/2 标普 11 大板块十涨一跌，医疗 −0.04% 为唯一下跌 → 组合唯一有可观测价格的美股腿为「上涨日负超额」'},
    },
    'sentiment': {
        'window': WIN, 'n': len(win), 'nominal_net': nominal, 'exposure_weighted_net': round(wsum, 3),
        'weighted_ratio_pct': round(wsum / nominal * 100, 1) if nominal else None,
        'by_track': {t: {'n': v['n'], 'net': v['net'], 'mean_strength': round(v['sum'] / v['n'], 1),
                         'pos': v['pos'], 'neg': v['neg'], 'neu': v['neu']} for t, v in byt.items()},
        'exposure_detail': wdetail,
        'strong_pos': {'n': len(sp), 'mean': round(sum(x['strength'] for x in sp) / len(sp), 1) if sp else None},
        'strong_neg': {'n': len(sn), 'mean': round(sum(x['strength'] for x in sn) / len(sn), 1) if sn else None},
        'merged_all': {'n': an, 'pos': a_pos, 'neu': a_neu, 'neg': a_neg, 'nominal_net': a_nom,
                       'mean_strength': round(a_mean, 2),
                       'strong_pos_n': len(a_sp),
                       'strong_pos_mean': round(sum(x['strength'] for x in a_sp) / len(a_sp), 1) if a_sp else None,
                       'strong_neg_n': len(a_sn),
                       'strong_neg_mean': round(sum(x['strength'] for x in a_sn) / len(a_sn), 1) if a_sn else None},
        'by_window': {k: {'n': v['n'], 'net': v['net'], 'mean': round(v['sum'] / v['n'], 1)} for k, v in bywin.items()},
        'note': ('⚠️ 本档为「零定价」档（除港股外全部标的不可定价）→ 情绪与价格无法做当日方向验证'
                 '（§3.85 前提不成立），10/8 方可开始验证。⚠️ DeepSeek 情绪标注在第 4、5 批返回 HTTP 402 '
                 '（额度/计费）→ 该 8 条退化为写入时的原始标签，须在报告披露（§3.127b）。'),
    },
    'other_defense_lines': {
        'zz_consume_12100': {'last': zz, 'dist_pct': round((zz - 12100) / 12100 * 100, 4),
                             'state': 'restored_close_level', 'next_line': 12000,
                             'next_line_dist_pct': round((zz - 12000) / 12000 * 100, 3),
                             'verify_at': '2026-10-08（A股复市）'},
        'a_med_reverse_1_5pct': {'proxy_pct': 2.8697, 'state': 'not_triggered', 'verify_at': '2026-10-08（A股复市）'},
        'sh_comp': {'last': sh},
        'hshci_hk_healthcare': {'close': hk['恒生医疗保健']['cur'], 'pct': hk['恒生医疗保健']['pct'],
                                'note': '组合零港股医药暴露 → 零直接损益；对 10/8 A股医药为弱正向情绪映射'},
        'hscei': {'close': hk['恒生国企']['cur'], 'pct': hk['恒生国企']['pct']},
        'hsi': {'close': hk['恒生指数']['cur'], 'pct': hk['恒生指数']['pct'],
                'note': '10/5 收于全日最高 24,040.34，重上 24,000 点整数关'},
    },
    'med_exposure': {'mv': round(med_mv, 2), 'pct': round(med_pct, 2), 'non_med_total': round(non_med, 2),
                     'threshold_all_med_pct': round(th_all, 2), 'threshold_a_sh_med_pct': round(th_a, 2),
                     'rule': '§3.98 方程解法 A(1+r)/(B+A(1+r)) = 40%'},
    'hk_exposure': {'total': HK_TOTAL, 'pct': round(HK_TOTAL / BASE_TOTAL * 100, 2), 'segments': hk_seg,
                    'southbound_gap_days': ['2026-10-05', '2026-10-06', '2026-10-07'],
                    'rule_hint': '只报赛道层 8.29% 将低估 4.84pct（宽基层），§3.108 条款 23'},
    'sensitivity': SENS,
    'pending_consume': {
        'hold_decision': 'no_action',
        'reason': ('混合档必做待消化；本档港股腿已按 10/5 收盘价完成累积第 2 日计算（区间 '
                   f'{HK_LOW:,.2f} 元 ~ {HK_HIGH:,.2f} 元）。但组合唯一可执行的交易窗口 = 10/8'
                   '（A股 + 港股通 + 南向同时恢复）→ 本档不做任何赛道级调整；'
                   '恒生科技 0.5% 减仓为 10/2 已锁定的第 2 次触发、执行待 10/8'),
        'estimated_combo_return_pct': 0.0, 'estimated_combo_pnl': 0.0,
        'attribution': ('A股 10/1-10/7 休市 → 场外基金无净值、场内无成交价；组合未直接持有港交所上市工具 → '
                        '港股行情不产生组合层当日定价 → 当日可实现盈亏恒为 0，归因「标的不可定价」而非「市场持平」（§3.107）'),
        'new_action_count': 0,
        'new_action_detail': '本档无新增纪律动作（恒科破位判定已于 10/2 锁定、不重复判定、不叠加）',
        'carried_over_action': f'恒生科技 0.5% 纪律减仓 {CUT_AMT:,.2f} 元（10/2 判定，执行待 10/8）',
    },
    'action': {'new_buy': 0, 'active_take_profit': 0, 'discipline_cut_pending': 1,
               'discipline_cut_amount': CUT_AMT, 'settled_discipline_cut': 0, 'new_pending': 0,
               'cumulative_discipline_amount': CUM_CUT,
               'note': '赛道级动作：0 买入 / 0 主动止盈 / 1 项纪律减仓（10/2 判定、执行待 10/8）'},
    'chain_0pct_row_inserted': False,
    'chain_note': '混合档不产 portfolio_close_*、不向链式序列插入 0% 行（§3.108 条款 22 / §3.122c）；链式末行仍 = 2026-09-30（_fix）',
    'risk_stats_source': 'risk_stats_20261005_preopen.json（本档不重算，§3.122c）',
    'holiday_leg_pricing': {
        'a_share_leg': {'priced': False, 'reason': 'A股 10/1-10/7 休市', 'next': '2026-10-08'},
        'hk_leg': {'priced': True, 'reason': '港股 10/5 已收盘（续市第 2 个交易日）',
                   'ref': 'HSTECH 4,183.68 / +0.62%；恒指 24,040.34 / +0.28%',
                   'note': '组合无港交所上市直接持仓 → 进入「待消化」而非「当日盈亏」'},
        'us_qdii_leg': {'priced': False, 'reason': 'US 10/5 尚未收盘（北京 20:00 = 美东 08:00）',
                        'note': '美股上一有效收盘 = 10/2，已于 10/4 档入库，其传导属 QDII 挂账项'},
    },
    'note': ('混合档盘后台账（正式版）：港股腿已按 10/5 收盘价完成累积窗口第 2 日定价'
             f'（{HK_LOW:,.2f} 元 ~ {HK_HIGH:,.2f} 元，几何复合口径）；A股腿待 10/8；美股/QDII 腿在挂账口径内（零变动）。'
             '恒生科技 4,250 破位状态未改变、第 2 次 0.5% 减仓执行待 10/8。本档不产 portfolio_close_*。'),
}
oj = os.path.join(HIST, f'portfolio_pending_{TODAY.replace("-", "")}.json')
json.dump(out, open(oj, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(f'\n已保存（覆盖预登记版）{os.path.basename(oj)}  state={out["state"]} finalized={out["finalized"]}')
