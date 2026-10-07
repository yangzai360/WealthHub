# -*- coding: utf-8 -*-
"""2026-10-07 盘中档：组合口径计算（混合档第 4 日 / 长假最后一日：A股休市 + 港股续市 · 复市后第 4 个交易日）
① 基准 = portfolio_close_20260930_fix.json（380,888.29 元，tracks[].mv 求和硬守卫）
② 当日估算盈亏 = 0 元（归因「标的不可定价」，非「市场持平」；§3.107/§3.117a）
③ 待消化（港股腿，三段法 §3.108 条款 23/24 + **累积窗口 = 10/2 + 10/5 + 10/6 已定价段 × 10/7 13:45 盘中段**）：
   **累积第 4 日（最后一日）** → 只给区间上下界、禁止方向判断（§3.129a：前档值列表不可当作端点）
④ 恒生科技 4,250 防线：**日内高 4,222.43 未触及 4,250** → 只做事实确认，
   收盘级判定权归 20:00 盘后档（§3.114c / §3.117d）
⑤ 情绪双口径（名义净分 + 暴露加权）
⑥ 医药敞口 + 门槛（§3.98 方程解法）
⚠️ 混合档**不产 portfolio_close_***、不向链式序列插入 0% 行（§3.108 条款 22）；pending 正式版由 20:00 盘后档覆盖
⚠️ §3.113e / §3.121c 四类字面量核对：读写路径 = *20261007* / 日期常量 = 2026-10-07 /
   docstring 档型语义 = 混合档第 4 日（长假最后一日） / note 字段档型语义 = 同 docstring
"""
import json, os, csv
from collections import defaultdict

BASE = '/Users/jieyang/Documents/WealthHub'
TODAY = '2026-10-07'
HIST = os.path.join(BASE, 'data/processed/history')

# ---------- 1. 基准 ----------
fix = json.load(open(os.path.join(HIST, 'portfolio_close_20260930_fix.json'), encoding='utf-8'))
total_mv = fix.get('total_mv')
tracks_fix = fix.get('tracks') or {}
restored = {tr: v.get('mv') for tr, v in tracks_fix.items() if v.get('mv') is not None}
s = sum(restored.values())
print(f'total_mv(文件) = {total_mv:,.2f}')
print(f'Σ tracks.mv    = {s:,.2f}')
assert abs(s - total_mv) < 1.5, f'硬守卫失败: Σ tracks[].mv {s:.2f} vs total_mv {total_mv}'
print('✅ 硬守卫通过：|Σ tracks[track].mv − total_mv| < 1.5')
BASE_TOTAL = total_mv
for k, v in sorted(restored.items(), key=lambda x: -x[1]):
    print(f'  {k:12s} {v:>12,.2f} 元  {v/BASE_TOTAL*100:>6.2f}%')
print(f'基准总资产 = {BASE_TOTAL:,.2f} 元')

# ---------- 2. 本档港股盘中 ----------
hq = json.load(open(os.path.join(HIST, 'intraday_hq_20261007.json'), encoding='utf-8'))
hk = hq['indices_hk']
stk = hq['hk_stocks']
print('\n=== 港股指数（2026-10-07 13:45）===')
for k, v in hk.items():
    print(f"  {k:10s} {v['cur']:>11.3f} {v['pct']:>+7.2f}%  H{v['high']} L{v['low']}  @{v['date_field']}")
print('=== 港股个股 ===')
for k, v in stk.items():
    print(f"  {k:16s} {v['cur']:>9.2f} {v['pct']:>+7.2f}%")

HSTECH = hk['恒生科技']['pct']
HSI = hk['恒生指数']['pct']
HSCI = hk['恒生综合']['pct']
HSTECH_CUR = hk['恒生科技']['cur']
HSTECH_HIGH = hk['恒生科技']['high']
HSTECH_LOW = hk['恒生科技']['low']

# 中概互联代理（8 名互联网/消费互联网等权 / 6 名大市值平台）
NET8 = ['腾讯控股', '阿里巴巴-W', '小米集团-W', '京东集团-SW', '美团-W', '网易-S', '快手-W', '百度集团-SW']
NET6 = ['腾讯控股', '阿里巴巴-W', '京东集团-SW', '美团-W', '网易-S', '百度集团-SW']
p8 = sum(stk[c]['pct'] for c in NET8) / len(NET8)
p6 = sum(stk[c]['pct'] for c in NET6) / len(NET6)
print(f'\n中概互联代理：8 名等权 = {p8:+.4f}%（含小米/快手，取「最差」代理）；6 名大市值平台 = {p6:+.4f}%（取「最优」代理）')

# ---------- 3. 当日估算盈亏 ----------
print('\n=== 组合当日估算（混合档）===')
print('全部持仓标的不可定价 → 当日可实现盈亏 = 0.00 元（0.000%）（§3.107/§3.117a）')
print(f'估算总资产维持 = {BASE_TOTAL:,.2f} 元')
UNPRICED = [
    'A股 10/1-10/7 休市（第 7 日 / 长假最后一日）→ 20 只 A股类场外基金不发布净值',
    '场外港股联接（000071 / 012348）在 A股休市期不发布净值（§3.112i）',
    '场内 ETF / LOF（513050 / 513180 / 159920 等，沪深交易所）无交易时段 → 无成交价',
    '港股 10/7 开市（09:30-16:00）且本档有 13:45 盘中价，但组合未直接持有港股正股或港交所上市工具 → 港股行情不产生组合层当日定价',
    '美股 10/6 收盘已入库（10/7 盘前档），其组合传导属 QDII 挂账项、不在本档基准内；US 10/7 当日尚未开盘（北京 21:30）',
]
for i, r in enumerate(UNPRICED, 1):
    print(f'  归因{i}: {r}')

# ---------- 4. 待消化（港股腿，三段法 · 累积窗口 §3.108 条款 23/24 + §3.123b + §3.129a） ----------
# 前档已定价段 = 10/2 + 10/5 + 10/6（10/6 盘后档以真实收盘价重算并覆盖 pending，10/7 盘前档汇总）
prev = json.load(open(os.path.join(HIST, 'portfolio_preopen_20261007.json'), encoding='utf-8'))
pcum = prev['hk_leg_pending']['priced_segment_cum']
psegs = pcum['segments']
P_HSTECH_LIST = psegs['pure_hstech']['ret_pct_cum']                  # [-0.7242]
P_NET_LIST = psegs['china_internet']['ret_range_pct_cum']            # 8 值
P_BROAD_LIST = psegs['broad_hk']['ret_range_pct_cum']                # 8 值
print(f'\n[前档已定价段 10/2+10/5+10/6 几何复合] HSTECH {P_HSTECH_LIST}')
print(f'                                      中概 {P_NET_LIST}')
print(f'                                      宽基 {P_BROAD_LIST}')
print(f'[前十档合计区间] low {pcum["low"]:,.2f} 元 / mid {pcum["mid"]:,.2f} 元 / high {pcum["high"]:,.2f} 元')

hk_seg = {'pure_hstech': 17017.68, 'china_internet': 14555.16, 'broad_hk': 18451.42}
HK_TOTAL = sum(hk_seg.values())
assert abs(HK_TOTAL - prev['hk_total']) < 1.5, '港联系总暴露与盘前档不一致'
print(f'\n=== 港股腿「待消化」三段法（本档 = 累积窗口第 4 日 / 最后一日：10/2 + 10/5 + 10/6 收盘段 × 10/7 13:45 盘中段）===')
print(f'  港联系总暴露 {HK_TOTAL:,.2f} 元 = {HK_TOTAL/BASE_TOTAL*100:.2f}%')
print(f"  （赛道层 {hk_seg['pure_hstech']+hk_seg['china_internet']:,.2f} 元 = {(hk_seg['pure_hstech']+hk_seg['china_internet'])/BASE_TOTAL*100:.2f}%；"
      f"宽基恒生系 {hk_seg['broad_hk']:,.2f} 元 = {hk_seg['broad_hk']/BASE_TOTAL*100:.2f}%）")


def cum(*ps):
    """累积复合：输入各段涨跌（百分点），输出累积涨跌（百分点）。"""
    f = 1.0
    for p in ps:
        f *= (1 + p / 100)
    return (f - 1) * 100


# 本档（10/7）代理
T_HSTECH = HSTECH
T_NET_WORST, T_NET_BEST = p8, p6
T_BROAD_A, T_BROAD_B = HSCI, HSI

# 笛卡尔积：对「合计结果值」取 min/max（§3.123b / §3.129a，禁止对各段极值分别取）
combos = []
for ph in P_HSTECH_LIST:
    for pn in P_NET_LIST:
        for pb in P_BROAD_LIST:
            for tn in (T_NET_WORST, T_NET_BEST):
                for tb in (T_BROAD_A, T_BROAD_B):
                    c_h = cum(ph, T_HSTECH)
                    c_n = cum(pn, tn)
                    c_b = cum(pb, tb)
                    v = (hk_seg['pure_hstech'] * c_h / 100
                         + hk_seg['china_internet'] * c_n / 100
                         + hk_seg['broad_hk'] * c_b / 100)
                    combos.append((v, c_h, c_n, c_b))
combos.sort(key=lambda x: x[0])
HK_LOW, HK_HIGH = combos[0][0], combos[-1][0]
HK_MID = (HK_LOW + HK_HIGH) / 2
print(f'  组合数 = {len(combos)}（1 × 8 × 8 × 2 × 2 = 256）')
print(f"  纯恒科系累积 {cum(P_HSTECH_LIST[0], T_HSTECH):+.4f}% × {hk_seg['pure_hstech']:,.2f} 元 "
      f"→ {hk_seg['pure_hstech']*cum(P_HSTECH_LIST[0], T_HSTECH)/100:+,.2f} 元")
print(f"  中概·海外互联系（本档双代理 {T_NET_WORST:+.4f}% / {T_NET_BEST:+.4f}%）× {hk_seg['china_internet']:,.2f} 元")
print(f"  宽基恒生系（本档双代理 {T_BROAD_A:+.4f}% / {T_BROAD_B:+.4f}%）× {hk_seg['broad_hk']:,.2f} 元")
print(f"  → 区间 {HK_LOW:+,.2f} 元 ~ {HK_HIGH:+,.2f} 元（中枢 {HK_MID:+,.2f} 元）  [w= 最差段 {combos[0][1]:.4f}/{combos[0][2]:.4f}/{combos[0][3]:.4f}]")
assert HK_LOW <= HK_MID <= HK_HIGH, '区间端点语义错误（§3.123b）'

# 赛道层（纯恒科 + 中概，与 10/2、10/5、10/6 口径可比）
tc = []
for ph in P_HSTECH_LIST:
    for pn in P_NET_LIST:
        for tn in (T_NET_WORST, T_NET_BEST):
            tc.append(hk_seg['pure_hstech'] * cum(ph, T_HSTECH) / 100 + hk_seg['china_internet'] * cum(pn, tn) / 100)
tc.sort()
track_low, track_high = tc[0], tc[-1]
track_mid = (track_low + track_high) / 2
TRACK_ONLY = hk_seg['pure_hstech'] + hk_seg['china_internet']
print(f"  （仅赛道层 {TRACK_ONLY:,.2f} 元）区间 {track_low:+,.2f} 元 ~ {track_high:+,.2f} 元（中枢 {track_mid:+,.2f} 元）")
print(f"  （前十档 10/2+10/5+10/6 段合计中枢 {pcum['mid']:+,.2f} 元 → 本档中枢 {HK_MID:+,.2f} 元，"
      f"变化 {HK_MID - pcum['mid']:+,.2f} 元）")

# ---------- 5. 情绪（名义 + 暴露加权） ----------
sent = json.load(open(os.path.join(BASE, f'data/processed/news/sentiment-{TODAY}.json'), encoding='utf-8'))
WIN = '盘中(07:30-13:30)'
win = [x for x in sent['items'] if x.get('window') == WIN]
if not win:
    raise SystemExit('⚠️ 盘中窗口 sentiment 为 0 条 → 终止')
print(f'\n=== 情绪（盘中窗口 {len(win)} 条）===')
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
print(f'合并全档 {an} 条：{a_pos} 利多 / {a_neu} 中性 / {a_neg} 利空；净分 {a_nom:+d}；均值强度 {a_mean:.1f}；'
      f'强正 n={len(a_sp)} 均值 {round(sum(x["strength"] for x in a_sp)/len(a_sp),1) if a_sp else 0}；'
      f'强负 n={len(a_sn)} 均值 {round(sum(x["strength"] for x in a_sn)/len(a_sn),1) if a_sn else 0}')

# ---------- 6. 防线 ----------
print('\n=== 防线状态 ===')
idx = defaultdict(dict)
with open(os.path.join(HIST, 'indices.csv'), encoding='utf-8-sig') as fh:
    for row in csv.DictReader(fh):
        try:
            idx[row['code']][row['date']] = float(row['close'])
        except Exception:
            pass
zz = idx.get('000932', {}).get('2026-09-30')
sh = idx.get('000001', {}).get('2026-09-30')
print(f'  恒生科技 HSTECH = {HSTECH_CUR}（10/7 13:45 盘中，前收 {hk["恒生科技"]["prev"]}）')
print(f'     距 4,250 防线 = {(HSTECH_CUR-4250)/4250*100:+.4f}%   → {"🔴 盘中破位" if HSTECH_CUR < 4250 else "🟢 未破"}')
print(f'     ⚠️ 日内高 {HSTECH_HIGH} → {"盘中一度站上 4,250（未站稳）" if HSTECH_HIGH >= 4250 else "日内未触及 4,250"}')
print(f'     距 4,400 = {(HSTECH_CUR-4400)/4400*100:+.3f}%  距 4,300 = {(HSTECH_CUR-4300)/4300*100:+.3f}%')
print(f'     自 9/22 高点 4,510.06 = {(HSTECH_CUR/4510.06-1)*100:+.3f}%')
print(f'     日内区间 {HSTECH_LOW} ~ {HSTECH_HIGH}（现价距日内低 {((HSTECH_CUR-HSTECH_LOW)/HSTECH_LOW*100):+.3f}%、距日内高 {((HSTECH_CUR-HSTECH_HIGH)/HSTECH_HIGH*100):+.3f}%）')
print(f'  中证消费 000932 = {zz}（9/30 收盘，A股休市无更新）  距 12,100 = {(zz-12100)/12100*100:+.4f}%')
print(f'  上证 000001 = {sh}（9/30 收盘）')
print(f'  A股医药反向兑现线：板块代理 +2.958%（9/30 收盘口径）→ 未触发（方向相反）')

# ---------- 7. 医药敞口 + 门槛 ----------
med_mv = restored['A股医药'] + restored['美股标普医药']
med_pct = med_mv / BASE_TOTAL * 100
non_med = sum(v for k, v in restored.items() if k not in ('A股医药', '美股标普医药'))
th_all = (0.40 * non_med / (0.60 * med_mv) - 1) * 100
A_sh = restored['A股医药']
A_us = restored['美股标普医药']
target = 0.40 * non_med / 0.60
th_a = (target - A_us) / A_sh * 100 - 100
print(f'\n=== 医药敞口（§3.98 方程解法）===')
print(f'  总敞口 {med_mv:,.2f} 元 = {med_pct:.2f}%（A股医药 23.57% + 美股标普医药 15.66%），距 40% 上限 {40-med_pct:.2f}pct')
print(f'  非医药（含现金）对手盘 = {non_med:,.2f} 元；触线目标医药市值 = {target:,.2f} 元')
print(f'  触线门槛：医药两赛道单日同涨 +{th_all:.2f}% / 仅 A股医药 +{th_a:.2f}%（美股标普医药按 0）')

# ---------- 8. 敏感性（待消化累积窗口） ----------
print('\n=== 敏感性：港联系累积窗口（10/2、10/5、10/6、10/7 共 4 日，已定价 3 日 + 本档 13:45 盘中）===')
SENS = {}
for nm, key_ in (('乐观（累积 −2.0 元/百元）', 'bull_minus2.0pct'), ('本档中枢对应', 'base_mid_cum'),
                 ('悲观（累积 −6.0 元/百元）', 'bear_minus6.0pct'), ('极端（累积 −9.0 元/百元）', 'tail_minus9.0pct')):
    p = {'bull_minus2.0pct': -2.0, 'bear_minus6.0pct': -6.0, 'tail_minus9.0pct': -9.0}.get(
        key_, HK_MID / HK_TOTAL * 100)
    v = HK_TOTAL * p / 100
    SENS[key_] = round(v, 2)
    print(f'  {nm:24s} {v:>+11,.2f} 元  （占基准 {v/BASE_TOTAL*100:+.3f}%）')

# ---------- 9. 输出 ----------
out = {
    'date': TODAY, 'session': 'intraday', 'as_of': '2026-10-07 13:45',
    'session_type': 'mixed_market_intraday',
    'session_type_note': '档型②「混合档」第 4 日（长假最后一日）= A股休市（10/1-10/7，第 7 日）+ 港股续市（复市后第 4 个交易日，09:30-16:00）；'
                         '本档港股有 13:45 盘中价，但组合全部持仓标的仍不可定价（A股休市 → 20 只 A股类场外基金无净值、场内 ETF/LOF 无成交价，'
                         '且组合未直接持有港股正股或港交所上市工具）→ 当日可实现盈亏恒为 0 元（§3.107/§3.117a）',
    'base_total': BASE_TOTAL, 'base_file': 'portfolio_close_20260930_fix.json',
    'base_guard_dev': round(s - total_mv, 4), 'base_guard_rule': '|Σ tracks.mv − total_mv| < 1.5',
    'tracks_weight': {k: round(v / BASE_TOTAL * 100, 2) for k, v in restored.items()},
    'tracks_mv': restored,
    'weights_after_discipline': {'恒生科技': 7.3, '现金': 8.66},
    'day_result': {
        'est_pnl': 0.0, 'est_pct': 0.0,
        'attribution': '全部持仓标的不可定价（非市场持平）',
        'reasons': UNPRICED,
        'note': '⚠️ 「0 元」是账面冻结，不构成任何方向判断（§3.107/§3.117a/§3.118b）',
    },
    'hk_intraday': {
        'as_of': '2026-10-07 13:45',
        'indices': {k: {'cur': v['cur'], 'pct': v['pct'], 'prev': v['prev'], 'high': v['high'], 'low': v['low'],
                        'date_field': v['date_field']} for k, v in hk.items()},
        'stocks': {k: {'cur': v['cur'], 'pct': v['pct']} for k, v in stk.items()},
        'china_internet_proxy': {'net8_equal_weight': round(p8, 4), 'net6_large_platform': round(p6, 4),
                                 'net8_members': NET8, 'net6_members': NET6,
                                 'note': '513050 跟踪中证海外中国互联网50；组合无港交所上市工具 → 代理仅用于待消化测算'},
    },
    'hk_pending_digest': {
        'window': ['2026-10-02', '2026-10-05', '2026-10-06', '2026-10-07'],
        'total_days': 4, 'priced_days': 4, 'as_of': '2026-10-07 13:45（10/7 盘中，非收盘）',
        'prev_segment_source': 'portfolio_preopen_20261007.json#hk_leg_pending.priced_segment_cum（10/2 + 10/5 + 10/6 真实收盘价，10/6 盘后档已覆盖为正式版）',
        'prev_segment_pct_cum': {'pure_hstech': P_HSTECH_LIST, 'china_internet': P_NET_LIST, 'broad_hk': P_BROAD_LIST},
        'today_segment_pct': {'pure_hstech': round(T_HSTECH, 4), 'china_internet_worst': round(T_NET_WORST, 4),
                              'china_internet_best': round(T_NET_BEST, 4), 'broad_hk_a': round(T_BROAD_A, 4),
                              'broad_hk_b': round(T_BROAD_B, 4)},
        'segments': {
            'pure_hstech': {'mv': hk_seg['pure_hstech'], 'cum_pct': round(cum(P_HSTECH_LIST[0], T_HSTECH), 4),
                            'pnl': round(hk_seg['pure_hstech'] * cum(P_HSTECH_LIST[0], T_HSTECH) / 100, 2)},
            'china_internet': {'mv': hk_seg['china_internet'],
                               'cum_low_pct': round(min(cum(p, t) for p in P_NET_LIST for t in (T_NET_WORST, T_NET_BEST)), 4),
                               'cum_high_pct': round(max(cum(p, t) for p in P_NET_LIST for t in (T_NET_WORST, T_NET_BEST)), 4),
                               'pnl_low': round(hk_seg['china_internet'] * min(cum(p, t) for p in P_NET_LIST for t in (T_NET_WORST, T_NET_BEST)) / 100, 2),
                               'pnl_high': round(hk_seg['china_internet'] * max(cum(p, t) for p in P_NET_LIST for t in (T_NET_WORST, T_NET_BEST)) / 100, 2)},
            'broad_hk': {'mv': hk_seg['broad_hk'],
                         'cum_low_pct': round(min(cum(p, t) for p in P_BROAD_LIST for t in (T_BROAD_A, T_BROAD_B)), 4),
                         'cum_high_pct': round(max(cum(p, t) for p in P_BROAD_LIST for t in (T_BROAD_A, T_BROAD_B)), 4),
                         'pnl_low': round(hk_seg['broad_hk'] * min(cum(p, t) for p in P_BROAD_LIST for t in (T_BROAD_A, T_BROAD_B)) / 100, 2),
                         'pnl_high': round(hk_seg['broad_hk'] * max(cum(p, t) for p in P_BROAD_LIST for t in (T_BROAD_A, T_BROAD_B)) / 100, 2)},
            'segment_field_rule': '§3.123b 字段对齐：各段 cum_low_pct / cum_high_pct 一律取 min / max（与其他区间同规则），不按代理书写顺序',
        },
        'hk_total': HK_TOTAL, 'hk_pct': round(HK_TOTAL / BASE_TOTAL * 100, 2),
        'total_low': round(HK_LOW, 2), 'total_mid': round(HK_MID, 2), 'total_high': round(HK_HIGH, 2),
        'track_only_low': round(track_low, 2), 'track_only_mid': round(track_mid, 2), 'track_only_high': round(track_high, 2),
        'combo_count': len(combos),
        'interval_rule': '§3.123b + §3.129a：对 256 组（1 × 8 × 8 × 2 × 2）「合计结果值」取 min/max；assert low ≤ 中枢 ≤ high 已通过',
        'finalized': False,
        'finalize_at': '2026-10-07 20:00（港股 10/7 收盘后，以收盘价重算并覆盖 portfolio_pending_20261007.json，§3.121b）',
        'rule': '§3.108 条款 23/24 + §3.123b + §3.126c + §3.129a：三段法 + 累积窗口几何复合 + 笛卡尔积取合计值 min/max；'
                '静态测算只给区间上下界、不得作方向判断；本档为累积窗口第 4 日（10/2、10/5、10/6 已定价，10/7 为盘中段）',
        'cumulative_note': '累积口径 = 各段代理涨跌几何复合 (1+r1)(1+r2)(1+r3)(1+r4)−1，非简单相加',
    },
    'qdii_pending': {
        'refreshed': False,
        'reason': '本档无新增美股交易日（US 10/7 尚未开盘，北京 21:30 开盘、收盘成型于北京 10/8 04:00）→ 挂账区间维持 10/7 盘前档值',
        'total_low': -1555.97, 'total_mid': -1298.34, 'total_high': -1126.59,
        'unknown_sessions': ['2026-10-07'],
        'coef_note': '长假前后实测隐含系数 1.25~1.29（§3.118a），远超标定 0.72 / 实测 0.62 → 只给区间、不给中枢点值',
        'source': 'portfolio_preopen_20261007.json#pending',
    },
    'sentiment': {
        'window': WIN, 'n': len(win), 'nominal_net': nominal, 'exposure_weighted_net': round(wsum, 3),
        'weighted_ratio_pct': round(wsum / nominal * 100, 1) if nominal else None,
        'formula_note': '名义净分 = Σ利多强度 − Σ利空强度；暴露加权净分 = Σ(赛道净强度分 × 赛道权重) ÷ 总资产（§3.128e 就地写公式）',
        'annotation_mode': sent.get('annotation_mode'),
        'degraded_items': sent.get('degraded_items'),
        'by_track': {t: {'n': v['n'], 'net': v['net'], 'mean_strength': round(v['sum'] / v['n'], 1),
                         'pos': v['pos'], 'neg': v['neg'], 'neu': v['neu']} for t, v in byt.items()},
        'exposure_detail': wdetail,
        'strong_pos': {'n': len(sp), 'mean': round(sum(x['strength'] for x in sp) / len(sp), 1) if sp else None},
        'strong_neg': {'n': len(sn), 'mean': round(sum(x['strength'] for x in sn) / len(sn), 1) if sn else None},
        'merged_all': {'n': an, 'pos': a_pos, 'neu': a_neu, 'neg': a_neg, 'nominal_net': a_nom,
                       'mean_strength': round(a_mean, 1),
                       'strong_pos_n': len(a_sp), 'strong_pos_mean': round(sum(x['strength'] for x in a_sp) / len(a_sp), 1) if a_sp else None,
                       'strong_neg_n': len(a_sn), 'strong_neg_mean': round(sum(x['strength'] for x in a_sn) / len(a_sn), 1) if a_sn else None},
    },
    'defense_lines': {
        'hstech_4250': {'last': HSTECH_CUR, 'prev_close': hk['恒生科技']['prev'], 'dist_pct': round((HSTECH_CUR - 4250) / 4250 * 100, 4),
                        'state': 'intraday_break_confirmed',
                        'day_low': HSTECH_LOW, 'day_high': HSTECH_HIGH,
                        'intraday_touched_above': bool(HSTECH_HIGH >= 4250),
                        'intraday_above_note': '⚠️ 日内高 4,222.43 **未触及 4,250**（与 10/6 档日内高 4,251.54 不同）→ 本档不存在「盘中一度站上」的表述，只写「全日未站上 4,250」；'
                                               '按 §3.117d，收盘级判定权归 20:00 盘后档',
                        'verify_at': '2026-10-07 16:00（港股收盘）→ 判定权归 20:00 盘后档；10/2 收盘级破位已锁定、本档不重新判定（§3.114c）',
                        'next_trigger': '收盘价 < 4,250 → 第 2 次 0.5% 纪律减仓（标的限纯恒科口径，1,904.44 元，执行待 10/8）；'
                                        '若盘中收复亦**不撤销**（§3.114c）'},
        'zz_consume_12100': {'last': zz, 'dist_pct': round((zz - 12100) / 12100 * 100, 4), 'state': 'restored_close_level',
                             'next_line': 12000, 'next_line_dist_pct': round((zz - 12000) / 12000 * 100, 2),
                             'verify_at': '2026-10-08（A股复市）'},
        'a_med_reverse_1_5pct': {'proxy_pct': 2.958, 'state': 'not_triggered', 'verify_at': '2026-10-08（A股复市）'},
        'sh_comp': {'last': sh},
    },
    'med_exposure': {'mv': round(med_mv, 2), 'pct': round(med_pct, 2), 'non_med_total': round(non_med, 2),
                     'threshold_all_med_pct': round(th_all, 2), 'threshold_a_sh_med_pct': round(th_a, 2),
                     'rule': '§3.98 方程解法 A(1+r)/(B+A(1+r)) = 40%'},
    'hk_exposure': {'total': HK_TOTAL, 'pct': round(HK_TOTAL / BASE_TOTAL * 100, 2), 'segments': hk_seg,
                    'southbound_gap_days': ['2026-10-02', '2026-10-05', '2026-10-06', '2026-10-07'],
                    'gap_day_index_today': 4,
                    'rule_hint': '只报赛道层 8.29% 将低估 4.84pct（宽基层），§3.108 条款 23'},
    'sensitivity': SENS,
    'chain_0pct_row_inserted': False,
    'chain_note': '混合档不产 portfolio_close_*、不向链式序列插入 0% 行（§3.108 条款 22）；链式末行仍 = 2026-09-30（_fix）',
    'risk_stats_source': 'risk_stats_20261007_preopen.json（本档不重算，§3.127e）',
    'pending_file_note': 'portfolio_pending_20261007.json 正式版由 20:00 盘后档以港股 10/7 收盘价重算并覆盖；本档不覆盖（§3.121b）',
    'intraday_pseudo_close_warning': '本档已向 indices.csv 写入 2026-10-07 港股「盘中 13:45」伪收盘行（5 行）→ '
                                     '全库 n 日窗口的恒生科技 n 已被推高（见 event_stats_intraday_20261007.json 的 pseudo_close_n_delta）；'
                                     '盘后档以真实收盘行覆盖当日日期键后即自动修正（§3.126a/§3.127d）',
}
oj = os.path.join(HIST, f'portfolio_intraday_{TODAY.replace("-", "")}.json')
json.dump(out, open(oj, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(f'\n已保存 {os.path.basename(oj)}')
