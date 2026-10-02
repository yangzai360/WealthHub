# -*- coding: utf-8 -*-
"""2026-10-02 盘中档：组合口径计算（混合档：A股休市 + 港股复市首日）
① 基准 = portfolio_close_20260930_fix.json（380,888.29 元，tracks[].mv 求和硬守卫）
② 当日估算盈亏 = 0 元（归因「标的不可定价」，非「市场持平」；§3.107/§3.117a）—— 与 9/25 混合档同口径
③ 待消化（港股腿，三段法 §3.108 条款 23/24）：纯恒科 / 中概互联 / 宽基恒生系，只给区间上下界
④ 恒生科技 4,250 防线：**盘中破位确认**，判定权移交 20:00 盘后档（§3.114c）
⑤ 情绪双口径（名义净分 + 暴露加权）
⑥ 医药敞口 + 门槛（§3.98 方程解法）
⚠️ 混合档不产 portfolio_close_*、不向链式序列插入 0% 行（§3.108 条款 22）；pending 正式版由 20:00 盘后档覆盖
⚠️ §3.113e：本次为全新撰写（非 sed 派生），读写路径 = 20261002 / 2026-10-02
"""
import json, os, csv
from collections import defaultdict

BASE = '/Users/jieyang/Documents/WealthHub'
TODAY = '2026-10-02'
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
hq = json.load(open(os.path.join(HIST, 'intraday_hq_20261002.json'), encoding='utf-8'))
hk = hq['indices_hk']
stk = hq['hk_stocks']
print('\n=== 港股指数（2026-10-02 13:45）===')
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

# 中概互联代理（8 名互联网/消费互联网等权）
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
    'A股 10/1-10/7 休市 → 20 只 A股类场外基金不发布净值',
    '场外港股联接（000071 / 012348）在 A股休市期不发布净值（§3.112i）',
    '场内 ETF / LOF（513050 / 513180 / 159920 等，沪深交易所）无交易时段 → 无成交价',
    '港股 10/2 开市，但组合未直接持有港股正股或港交所上市工具 → 港股行情不产生组合层当日定价',
    '美股 10/1 收盘已入库，其组合传导属 QDII 挂账项、不在本档基准内',
]
for i, r in enumerate(UNPRICED, 1):
    print(f'  归因{i}: {r}')

# ---------- 4. 待消化（港股腿，三段法） ----------
hk_seg = {'pure_hstech': 17017.68, 'china_internet': 14555.16, 'broad_hk': 18451.42}
HK_TOTAL = sum(hk_seg.values())
print(f'\n=== 港股腿「待消化」三段法（本档 = 累积窗口第 1 日：10/2）===')
print(f'  港联系总暴露 {HK_TOTAL:,.2f} 元 = {HK_TOTAL/BASE_TOTAL*100:.2f}%')
print(f"  （赛道层 {hk_seg['pure_hstech']+hk_seg['china_internet']:,.2f} 元 = {(hk_seg['pure_hstech']+hk_seg['china_internet'])/BASE_TOTAL*100:.2f}%；"
      f"宽基恒生系 {hk_seg['broad_hk']:,.2f} 元 = {hk_seg['broad_hk']/BASE_TOTAL*100:.2f}%）")

LEG_PROXY = {
    'pure_hstech': {'nm': '纯恒生科技系（012348 ×2 + 513180）', 'best': HSTECH, 'worst': HSTECH, 'mid': HSTECH},
    'china_internet': {'nm': '中概·海外互联系（513050 + 164906 ×2）', 'best': p6, 'worst': p8, 'mid': (p6 + p8) / 2},
    'broad_hk': {'nm': '宽基恒生系（000071 ×2 + 159920）', 'best': HSI, 'worst': HSCI, 'mid': (HSI + HSCI) / 2},
}
tot = {'best': 0.0, 'worst': 0.0, 'mid': 0.0}
for leg, mv in hk_seg.items():
    lp = LEG_PROXY[leg]
    r = {k: mv * lp[k] / 100 for k in ('best', 'worst', 'mid')}
    for k in tot:
        tot[k] += r[k]
    print(f"  {lp['nm']:38s} {mv:>11,.2f} 元  "
          f"最优 {lp['best']:+.2f}% → {r['best']:>+9,.2f} 元 ｜ 最差 {lp['worst']:+.2f}% → {r['worst']:>+9,.2f} 元 ｜ 中枢 {lp['mid']:+.2f}% → {r['mid']:>+9,.2f} 元")
print(f"  {'港联系合计（三段）':38s} {HK_TOTAL:>11,.2f} 元  "
      f"上界 {tot['best']:>+9,.2f} 元 ｜ 下界 {tot['worst']:>+9,.2f} 元 ｜ 中枢 {tot['mid']:>+9,.2f} 元")
HK_LOW, HK_HIGH, HK_MID = tot['worst'], tot['best'], tot['mid']
print(f"  → 区间 {HK_LOW:+,.2f} 元 ~ {HK_HIGH:+,.2f} 元（中枢 {HK_MID:+,.2f} 元）")

# 赛道层（纯恒科 + 中概，与 9/25 口径可比）
track_low = hk_seg['pure_hstech'] * HSTECH / 100 + hk_seg['china_internet'] * p8 / 100
track_high = hk_seg['pure_hstech'] * HSTECH / 100 + hk_seg['china_internet'] * p6 / 100
track_mid = (track_low + track_high) / 2
print(f"  （仅赛道层，31,572.84 元）区间 {track_low:+,.2f} 元 ~ {track_high:+,.2f} 元（中枢 {track_mid:+,.2f} 元）")

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
# 合并全档
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
print(f'  恒生科技 HSTECH = {HSTECH_CUR}（10/2 13:45 盘中，前收 {hk["恒生科技"]["prev"]}）')
print(f'     距 4,250 防线 = {(HSTECH_CUR-4250)/4250*100:+.4f}%   → {"🔴 盘中破位" if HSTECH_CUR < 4250 else "🟢 未破"}')
print(f'     距 4,400 = {(HSTECH_CUR-4400)/4400*100:+.3f}%  距 4,300 = {(HSTECH_CUR-4300)/4300*100:+.3f}%')
print(f'     自 9/22 高点 4,510.06 = {(HSTECH_CUR/4510.06-1)*100:+.3f}%')
print(f'     日内区间 {HSTECH_LOW} ~ {HSTECH_HIGH}（现价距日内低 {((HSTECH_CUR-HSTECH_LOW)/HSTECH_LOW*100):+.3f}%、距日内高 {((HSTECH_CUR-HSTECH_HIGH)/HSTECH_HIGH*100):+.3f}%）')
print(f'  中证消费 000932 = {zz}（9/30 收盘，A股休市无更新）  距 12,100 = {(zz-12100)/12100*100:+.4f}%')
print(f'  上证 000001 = {sh}（9/30 收盘）')
print(f'  A股医药反向兑现线：板块代理 +2.8697%（9/30 收盘口径）→ 未触发（方向相反）')

# ---------- 7. 医药敞口 + 门槛 ----------
med_mv = restored['A股医药'] + restored['美股标普医药']
med_pct = med_mv / BASE_TOTAL * 100
non_med = sum(v for k, v in restored.items() if k not in ('A股医药', '美股标普医药'))
# §3.98 方程解法：(1+r) = 0.4B/(0.6A)
th_all = (0.40 * non_med / (0.60 * med_mv) - 1) * 100
# 仅 A股医药涨、美股标普医药按 0：(A_sh(1+r) + A_us) = 0.4B / 0.6  →  r = (2B/3 − A_us)/A_sh − 1
A_sh = restored['A股医药']
A_us = restored['美股标普医药']
target = 0.40 * non_med / 0.60
th_a = (target - A_us) / A_sh * 100 - 100
print(f'\n=== 医药敞口（§3.98 方程解法）===')
print(f'  总敞口 {med_mv:,.2f} 元 = {med_pct:.2f}%（A股医药 23.57% + 美股标普医药 15.66%），距 40% 上限 {40-med_pct:.2f}pct')
print(f'  非医药（含现金）对手盘 = {non_med:,.2f} 元；触线目标医药市值 = {target:,.2f} 元')
print(f'  触线门槛：医药两赛道单日同涨 +{th_all:.2f}% / 仅 A股医药 +{th_a:.2f}%（美股标普医药按 0）')

# ---------- 8. 敏感性（待消化累积窗口） ----------
print('\n=== 敏感性：港联系累积窗口（10/2、10/5、10/6、10/7 共 4 日日历、已定价 1 日）===')
for nm, p in (('乐观（累积 −1.0%）', -1.0), ('本档中枢对应（累积 −2.73%）', -2.733), ('悲观（累积 −5.0%）', -5.0), ('极端（累积 −8.0%）', -8.0)):
    print(f'  {nm:24s} {HK_TOTAL*p/100:>+11,.2f} 元  （占基准 {HK_TOTAL*p/100/BASE_TOTAL*100:+.3f}%）')

# ---------- 9. 输出 ----------
out = {
    'date': TODAY, 'session': 'intraday', 'as_of': '2026-10-02 13:45',
    'session_type': 'mixed_day_intraday',
    'session_type_note': '档型②「混合档」= A股休市（10/1-10/7）+ 港股复市首日（10/2 开市，09:30-16:00）；'
                         '本档港股已有个盘中价（13:45），但组合全部持仓标的仍不可定价（A股休市 → 场外无净值、场内无成交价）',
    'base_total': BASE_TOTAL, 'base_file': 'portfolio_close_20260930_fix.json',
    'base_guard_dev': round(s - total_mv, 4), 'base_guard_rule': '|Σ tracks.mv − total_mv| < 1.5',
    'tracks_weight': {k: round(v / BASE_TOTAL * 100, 2) for k, v in restored.items()},
    'tracks_mv': restored,
    'weights_after_discipline': {'恒生科技': 7.8, '现金': 8.16},
    'day_result': {
        'est_pnl': 0.0, 'est_pct': 0.0,
        'attribution': '全部持仓标的不可定价（非市场持平）',
        'reasons': UNPRICED,
        'note': '⚠️ 「0 元」是账面冻结，不构成任何方向判断（§3.107/§3.117a/§3.118b）',
    },
    'hk_intraday': {
        'as_of': '2026-10-02 13:45',
        'indices': {k: {'cur': v['cur'], 'pct': v['pct'], 'prev': v['prev'], 'high': v['high'], 'low': v['low'],
                        'date_field': v['date_field']} for k, v in hk.items()},
        'stocks': {k: {'cur': v['cur'], 'pct': v['pct']} for k, v in stk.items()},
        'china_internet_proxy': {'net8_equal_weight': round(p8, 4), 'net6_large_platform': round(p6, 4),
                                 'net8_members': NET8, 'net6_members': NET6,
                                 'note': '513050 跟踪中证海外中国互联网50；组合无港交所上市工具 → 代理仅用于待消化测算'},
    },
    'hk_pending_digest': {
        'window': ['2026-10-02', '2026-10-05', '2026-10-06', '2026-10-07'],
        'priced_days': 1, 'as_of': '2026-10-02 13:45（10/2 盘中，非收盘）',
        'segments': {
            'pure_hstech': {'mv': hk_seg['pure_hstech'], 'proxy_pct': HSTECH, 'pnl': round(hk_seg['pure_hstech'] * HSTECH / 100, 2)},
            'china_internet': {'mv': hk_seg['china_internet'], 'proxy_low_pct': round(p8, 4), 'proxy_high_pct': round(p6, 4),
                               'pnl_low': round(hk_seg['china_internet'] * p8 / 100, 2),
                               'pnl_high': round(hk_seg['china_internet'] * p6 / 100, 2)},
            'broad_hk': {'mv': hk_seg['broad_hk'], 'proxy_low_pct': HSCI, 'proxy_high_pct': HSI,
                         'pnl_low': round(hk_seg['broad_hk'] * HSCI / 100, 2),
                         'pnl_high': round(hk_seg['broad_hk'] * HSI / 100, 2)},
        },
        'hk_total': HK_TOTAL, 'hk_pct': round(HK_TOTAL / BASE_TOTAL * 100, 2),
        'total_low': round(HK_LOW, 2), 'total_mid': round(HK_MID, 2), 'total_high': round(HK_HIGH, 2),
        'track_only_low': round(track_low, 2), 'track_only_mid': round(track_mid, 2), 'track_only_high': round(track_high, 2),
        'finalized': False,
        'finalize_at': '2026-10-02 20:00（港股 10/2 收盘后，以收盘价重算）',
        'rule': '§3.108 条款 23/24：三段法 + 静态测算只给区间上下界、不得作方向判断；本档为累积窗口第 1 日、未走完',
    },
    'qdii_pending': {
        'refreshed': False,
        'reason': '本档无新增美股交易日入库（US 10/2 收盘于北京 10/3 04:00 成型）→ 挂账区间维持盘前档值',
        'total_low': -1755.32, 'total_mid': -1457.82, 'total_high': -1259.48,
        'coef_note': '长假前后实测隐含系数 1.25~1.29（§3.118a），远超标定 0.72 / 实测 0.62 → 只给区间',
        'source': 'portfolio_preopen_20261002.json',
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
                       'mean_strength': round(a_mean, 1),
                       'strong_pos_n': len(a_sp), 'strong_pos_mean': round(sum(x['strength'] for x in a_sp) / len(a_sp), 1) if a_sp else None,
                       'strong_neg_n': len(a_sn), 'strong_neg_mean': round(sum(x['strength'] for x in a_sn) / len(a_sn), 1) if a_sn else None},
    },
    'defense_lines': {
        'hstech_4250': {'last': HSTECH_CUR, 'prev_close': hk['恒生科技']['prev'], 'dist_pct': round((HSTECH_CUR - 4250) / 4250 * 100, 4),
                        'state': 'intraday_break_confirmed' if HSTECH_CUR < 4250 else 'intraday_safe',
                        'day_low': HSTECH_LOW, 'day_high': HSTECH_HIGH,
                        'verify_at': '2026-10-02 16:00（港股收盘）→ 判定权移交 20:00 盘后档（§3.114c：盘中破位 ≠ 执行交易）',
                        'next_trigger': '收盘价 < 4,250 → 第 2 次 0.5% 纪律减仓（标的限纯恒科口径）'},
        'zz_consume_12100': {'last': zz, 'dist_pct': round((zz - 12100) / 12100 * 100, 4), 'state': 'restored_close_level',
                             'next_line': 12000, 'next_line_dist_pct': round((zz - 12000) / 12000 * 100, 2),
                             'verify_at': '2026-10-08（A股复市）'},
        'a_med_reverse_1_5pct': {'proxy_pct': 2.8697, 'state': 'not_triggered', 'verify_at': '2026-10-08（A股复市）'},
        'sh_comp': {'last': sh},
    },
    'med_exposure': {'mv': round(med_mv, 2), 'pct': round(med_pct, 2), 'non_med_total': round(non_med, 2),
                     'threshold_all_med_pct': round(th_all, 2), 'threshold_a_sh_med_pct': round(th_a, 2),
                     'rule': '§3.98 方程解法 A(1+r)/(B+A(1+r)) = 40%'},
    'hk_exposure': {'total': HK_TOTAL, 'pct': round(HK_TOTAL / BASE_TOTAL * 100, 2), 'segments': hk_seg,
                    'southbound_gap_days': ['2026-10-02', '2026-10-05', '2026-10-06', '2026-10-07'],
                    'rule_hint': '只报赛道层 8.29% 将低估 4.84pct（宽基层），§3.108 条款 23'},
    'sensitivity': {nm: round(HK_TOTAL * p / 100, 2) for nm, p in
                    (('bull_-1.0pct', -1.0), ('base_-2.733pct', -2.733), ('bear_-5.0pct', -5.0), ('tail_-8.0pct', -8.0))},
    'chain_0pct_row_inserted': False,
    'chain_note': '混合档不产 portfolio_close_*、不向链式序列插入 0% 行（§3.108 条款 22）；链式末行仍 = 2026-09-30（_fix）',
    'risk_stats_source': 'risk_stats_20261002_preopen.json（本档不重算）',
    'pending_file_note': 'portfolio_pending_20261002.json 正式版由 20:00 盘后档以港股 10/2 收盘价重算并覆盖；本档不覆盖',
}
oj = os.path.join(HIST, f'portfolio_intraday_{TODAY.replace("-", "")}.json')
json.dump(out, open(oj, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(f'\n已保存 {os.path.basename(oj)}')
