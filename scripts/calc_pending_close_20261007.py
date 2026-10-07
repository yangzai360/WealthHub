# -*- coding: utf-8 -*-
"""2026-10-07 盘后档：组合台账（档型②混合档第 4 日 · A股休市最后一日 + 港股续市第 4 日收盘）
① 基准 = portfolio_close_20260930_fix.json（380,888.29 元，tracks[].mv 求和硬守卫）
② 港股 10/7 **收盘**已成型 → 产出 `portfolio_pending_20261007.json` **正式版**
   （state=finalized / finalized=true，覆盖 08:00 预登记版 state=preopen_estimate）（§3.121b / §3.123a）
③ 当日可实现盈亏 = 0 元（归因「标的不可定价」，§3.107；A股 休市 → 场外无净值、场内无成交价）
④ 恒生科技 4,250 防线：**破位状态未改变且幅度重新扩大**（10/7 收 4,194.49 < 4,250，距 −1.3061%）；
   第 2 次 0.5% 纪律减仓 1,904.44 元 判定已于 10/2 锁定、执行待 10/8（§3.114c 不重复判定、不叠加）；
   **日内最高 4,222.43 < 4,250 → 全日未站上防线**（与 10/6 的「盘中一度站上」不同，§3.129b）
⑤ 待消化（港股腿三段法，**累积窗口 4 日全部走完 = 10/2 × 10/5 × 10/6 × 10/7，几何复合**，§3.126c）：
   ⚠️ §3.129a：**前档累积段的分段值是列表**（纯恒科 1 / 中概 8 / 宽基 8）→ 笛卡尔积 1×8×8×2×2 = **256 组**；
   禁止用前档 low/mid/high 三点当输入（会人为收窄区间且 mid 不再是中枢）
   ⚠️ 区间端点一律 `sorted()` 取 min/max（§3.116b / §3.123b），`assert low ≤ 中枢 ≤ high` 自证
⑥ QDII 挂账（本档无新增美股交易日 → 沿用盘前档并声明；§3.122c③）
⑦ 情绪双口径（名义净分 + 暴露加权）
⑧ 医药敞口 + 门槛（§3.98 方程解法）
⚠️ 混合档不产 portfolio_close_*、不向链式序列插入 0% 行（§3.108 条款 22、§3.122c）
⚠️ §3.121c / §3.128d：派生后必检 ①读写路径 ②日期常量 ③docstring 档型语义 ④note 字段档型语义
⚠️ 本次为「全新撰写 + 从 10/6 盘后脚本逐项核对派生」：读写路径 = 20261007 / 2026-10-07
"""
import json, os, csv, itertools
from collections import defaultdict

BASE = '/Users/jieyang/Documents/WealthHub'
TODAY = '2026-10-07'
HIST = os.path.join(BASE, 'data/processed/history')
SESSION_TYPE = 'mixed_day_close'
SESSION_NOTE = ('档型②「混合档」第 4 日（长假最后一日）= A股休市（10/1-10/7 第 7 日）+ 港股续市第 4 个交易日'
                '**已收盘**（10/7 09:30-16:00）；组合全部持仓标的仍不可定价（A股 休市 → 场外无净值、场内无成交价；'
                '场外港股联接不发净值；组合未直接持有港交所上市工具）')

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
hq = json.load(open(os.path.join(HIST, 'close_hq_20261007.json'), encoding='utf-8'))
hk = hq['indices_hk']
stk = hq['hk_stocks']
print('\n=== 港股指数（2026-10-07 收盘）===')
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
      f"HSI {HSI_PCT:+.4f}%（报告 {hk['恒生指数']['pct']:+.2f}%）｜HSCI {HSCI_PCT:+.4f}%（报告 {hk['恒生综合']['pct']:+.2f}%）")

NET8 = ['腾讯控股', '阿里巴巴-W', '小米集团-W', '京东集团-SW', '美团-W', '网易-S', '快手-W', '百度集团-SW']
NET6 = ['腾讯控股', '阿里巴巴-W', '京东集团-SW', '美团-W', '网易-S', '百度集团-SW']
p8 = round(sum(stk[c]['pct'] for c in NET8) / len(NET8), 4)
p6 = round(sum(stk[c]['pct'] for c in NET6) / len(NET6), 4)
print(f'中概互联代理（收盘）：8 名等权 = {p8:+.4f}%（最差代理）；6 名大市值平台 = {p6:+.4f}%（最优代理）')

# 10/2 × 10/5 × 10/6 三段**累积段**（来自 portfolio_pending_20261006.json 的 hk_pending_digest.segments[].cum_pct）
_prev_pf = json.load(open(os.path.join(HIST, 'portfolio_pending_20261006.json'), encoding='utf-8'))
_pseg = _prev_pf['hk_pending_digest']['segments']
PREV = {'pure_hstech': _pseg['pure_hstech']['cum_pct'],
        'china_internet': _pseg['china_internet']['cum_pct'],
        'broad_hk': _pseg['broad_hk']['cum_pct']}
print('上一档（10/6 正式版）累积段值列表长度：', {k: len(v) for k, v in PREV.items()})
assert len(PREV['pure_hstech']) == 1 and len(PREV['china_internet']) == 8 and len(PREV['broad_hk']) == 8, \
    '⚠️ 前档累积段值列表长度异常（§3.129a 期望 1 / 8 / 8）'

# ---------- 3. 当日可实现盈亏 ----------
UNPRICED = [
    'A股 10/1-10/7 休市（第 7 日 / 长假最后一日）→ A股类场外基金不发布净值、A股指数无新收盘（末行仍 = 2026-09-30）',
    '场内 ETF / LOF（513050 / 513180 / 159920 / 159928 等，沪深交易所）无交易时段 → 无成交价（本档实测 date_field 全部 = 2026-09-30）',
    '场外港股联接（000071 / 012348）在 A股休市期不发布净值（§3.112i）',
    '港股 10/7 已开市并收盘（恒生科技 4,194.49 / −0.68%），但组合未直接持有港股正股或港交所上市工具 → 港股行情不产生组合层当日定价',
    '美股 10/7 未开盘（北京 10/7 20:00 = 美东 10/7 08:00 EDT，US 10/7 收盘成型于北京 10/8 04:00），US 10/6 收盘已于本日盘前档入库，其组合传导属 QDII 挂账项、不在本档基准内',
]
print('\n=== 组合当日估算（混合档盘后 · 长假最后一日）===')
print('全部持仓标的不可定价 → 当日可实现盈亏 = 0.00 元（0.000%）；估算总资产维持 '
      f'{BASE_TOTAL:,.2f} 元（归因「标的不可定价」而非「市场持平」，§3.107）')
for i, r in enumerate(UNPRICED, 1):
    print(f'  归因{i}: {r}')

# ---------- 4. 待消化（港股腿三段法 · 累积窗口 4 日全部走完，几何复合） ----------
hk_seg = {'pure_hstech': 17017.68, 'china_internet': 14555.16, 'broad_hk': 18451.42}
HK_TOTAL = round(sum(hk_seg.values()), 2)
assert abs(HK_TOTAL - float(_prev_pf['hk_pending_digest']['hk_total'])) < 1.5, \
    f'⚠️ 港联系暴露与上一档不一致 {HK_TOTAL} vs {_prev_pf["hk_pending_digest"]["hk_total"]}'
print(f'\n=== 港股腿「待消化」三段法（累积窗口 4 日 / 共 4 日：10/2、10/5、10/6、10/7 —— **全部走完**）===')
print(f'  港联系总暴露 {HK_TOTAL:,.2f} 元 = {HK_TOTAL/BASE_TOTAL*100:.2f}%'
      f'（赛道层 {hk_seg["pure_hstech"]+hk_seg["china_internet"]:,.2f} 元 = '
      f'{(hk_seg["pure_hstech"]+hk_seg["china_internet"])/BASE_TOTAL*100:.2f}%；'
      f'宽基恒生系 {hk_seg["broad_hk"]:,.2f} 元 = {hk_seg["broad_hk"]/BASE_TOTAL*100:.2f}%）')
print(f'  ✅ 暴露一致性守卫通过：|Σ暴露 − 前档 hk_total| = {abs(HK_TOTAL - float(_prev_pf["hk_pending_digest"]["hk_total"])):.4f} < 1.5')


def cum(r1, r2):
    """§3.126c：跨档累积一律几何复合、禁止简单相加"""
    return ((1 + r1 / 100) * (1 + r2 / 100) - 1) * 100


LEG = {
    'pure_hstech': {'nm': '纯恒生科技系（012348 ×2 + 513180）',
                    'prev': PREV['pure_hstech'], 'today': [HSTECH_PCT]},
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
    rows[leg] = {'mv': mv, 'prev': lp['prev'], 'today': lp['today'], 'cum': combos, 'outs': outs}
    print(f"  {lp['nm']:38s} {mv:>11,.2f} 元  前档累积 " + ' / '.join(f'{p:+.4f}%' for p in lp['prev']) +
          '  × 本段 ' + ' / '.join(f'{p:+.4f}%' for p in lp['today']) +
          f"\n{' ' * 41}本次累积 {len(combos)} 组：{min(combos):+.4f}% ~ {max(combos):+.4f}%" +
          f"  →  {min(outs):+.2f} 元 ~ {max(outs):+.2f} 元")

# ⚠️ §3.116b / §3.123b / §3.129a：low/high 必须按「合计结果值」的 min/max（笛卡尔积逐组求和后 sorted 取极值）
combos_all = [sum(c) for c in itertools.product(*[rows[l]['outs'] for l in ('pure_hstech', 'china_internet', 'broad_hk')])]
HK_LOW, HK_HIGH = sorted([min(combos_all), max(combos_all)])
print(f"  组合数 combo_count = {len(combos_all)}（1 × 8 × 8 × 2 × 2 = 256，§3.129a）")
mid_exact = (hk_seg['pure_hstech'] * cum(PREV['pure_hstech'][0], HSTECH_PCT) / 100
             + hk_seg['china_internet'] * cum(sum(PREV['china_internet']) / 8, (p8 + p6) / 2) / 100
             + hk_seg['broad_hk'] * cum(sum(PREV['broad_hk']) / 8, (HSCI_PCT + HSI_PCT) / 2) / 100)
print(f"  {'港联系合计（三段）':38s} {HK_TOTAL:>11,.2f} 元  "
      f"low {HK_LOW:>+9,.2f} 元 ｜ high {HK_HIGH:>+9,.2f} 元 ｜ 代理均值口径参考中枢 {mid_exact:>+9,.2f} 元")
assert HK_LOW <= mid_exact <= HK_HIGH, f'⚠️ 中枢 {mid_exact:.2f} 未落在区间 [{HK_LOW:.2f}, {HK_HIGH:.2f}] 内 → 终止'
print(f"  ✅ 双守卫通过：low ≤ 中枢 ≤ high；区间 {HK_LOW:+,.2f} 元 ~ {HK_HIGH:+,.2f} 元"
      f"（占基准 {HK_LOW/BASE_TOTAL*100:+.3f}% ~ {HK_HIGH/BASE_TOTAL*100:+.3f}%）")

track_combos = [hk_seg['pure_hstech'] * cum(PREV['pure_hstech'][0], HSTECH_PCT) / 100
                + hk_seg['china_internet'] * cum(a, b) / 100
                for a in PREV['china_internet'] for b in (p8, p6)]
track_low, track_high = sorted([min(track_combos), max(track_combos)])
broad_combos = [hk_seg['broad_hk'] * cum(a, b) / 100 for a in PREV['broad_hk'] for b in (HSCI_PCT, HSI_PCT)]
broad_low, broad_high = sorted([min(broad_combos), max(broad_combos)])
print(f"  （仅赛道层 {hk_seg['pure_hstech']+hk_seg['china_internet']:,.2f} 元）区间 {track_low:+,.2f} 元 ~ {track_high:+,.2f} 元")
print(f"  （宽基恒生系单列）区间 {broad_low:+,.2f} 元 ~ {broad_high:+,.2f} 元")

# 单日段（10/7 当日，仅作对照，不入累积区间）
d_track = [hk_seg['pure_hstech'] * HSTECH_PCT / 100 + hk_seg['china_internet'] * b / 100 for b in (p8, p6)]
d_broad = [hk_seg['broad_hk'] * b / 100 for b in (HSCI_PCT, HSI_PCT)]
d_low = min(d_track) + min(d_broad)
d_high = max(d_track) + max(d_broad)
print(f"  （对照）10/7 单日段区间 {min(d_low, d_high):+,.2f} 元 ~ {max(d_low, d_high):+,.2f} 元")

# 长假 4 日「逐段并列表」（§3.126c）
# ⚠️ §3.133a：**逐日段值一律从 indices.csv 现算（(code,date) last-wins 去重），禁止手工硬编码常量**
#    —— 本档修复一处实际错误：旧版把 2026-10-05 的 HSTECH 段写成 −0.6689%（事实为 **+0.6191%**，
#    4183.68 / 4157.94 − 1），符号与幅度双错。累积口径不受影响（累积由 prev/today 段列表独立计算），
#    但展示字段会误导报告与「逐段并列」叙述 → 已改为派生 + 自校验。
def _hstech_close_by_date():
    _m = {}
    with open(os.path.join(HIST, 'indices.csv'), encoding='utf-8-sig') as f:
        for r in csv.DictReader(f):
            if r.get('code') == 'HSTECH' and r.get('date'):
                _m[r['date']] = float(r['close'])      # 后写覆盖先写（盘中行 → 收盘行）
    return _m


_H = _hstech_close_by_date()
_DAYS = ['2026-10-02', '2026-10-05', '2026-10-06', '2026-10-07']
_NOTE = {
    '2026-10-02': '港股复市首日、恒科收盘级破位',
    '2026-10-05': '恒科小幅收涨（⚠️ 前档展示字段误记 −0.6689%，本档更正为 +0.6191%）',
    '2026-10-06': '恒科反弹',
    '2026-10-07': '长假最后一日、恒科回落',
}
SEG_BY_DAY = {}
_prev = 4253.89                                        # 9/30 收盘，长假前最后有效行
for _d in _DAYS:
    _cur = _H[_d] if _d != '2026-10-07' else HSTECH_CUR
    _pct = round((_cur / _prev - 1) * 100, 4)
    SEG_BY_DAY[_d] = {'hstech_pct': _pct, 'close': _cur, 'prev_close': _prev, 'note': _NOTE[_d]}
    _prev = _cur
print('逐日段（由 indices.csv 现算）:',
      {k: v['hstech_pct'] for k, v in SEG_BY_DAY.items()})
assert abs(SEG_BY_DAY['2026-10-02']['hstech_pct'] - (-2.2556)) < 0.01, '10/02 段自校验失败'
assert abs(SEG_BY_DAY['2026-10-06']['hstech_pct'] - 0.9418) < 0.01, '10/06 段自校验失败'
assert SEG_BY_DAY['2026-10-05']['hstech_pct'] > 0, '⚠️ 10/05 段应为正（+0.6191%），常量硬编码错误复发'

# ---------- 5. 恒生科技防线（状态确认 + 破位幅度更正） ----------
print('\n=== 恒生科技 4,250 防线（状态确认，判定权已于 10/2 锁定）===')
Dv = HSTECH_CUR - 4250
HIGH = hk['恒生科技']['high']
LOW = hk['恒生科技']['low']
TOUCHED_ABOVE = HIGH >= 4250
print(f"  收盘 {HSTECH_CUR}（前收 {HSTECH_PREV}，{HSTECH_PCT:+.4f}%）距 4,250 = {Dv:+.3f} 点 / {Dv/4250*100:+.4f}%")
print(f"  日内区间 {LOW} ~ {HIGH} → intraday_touched_above = {TOUCHED_ABOVE}"
      f"（{'盘中一度站上 4,250' if TOUCHED_ABOVE else '**全日未触及 4,250**'}）")
TRIGGER_NOW = HSTECH_CUR < 4250
print(f"  本档状态 = {'🔴 收盘价仍 < 4,250（破位状态未改变，且幅度重新扩大）' if TRIGGER_NOW else '🟢 已收回 4,250 上方（纪律不可撤销，§3.114c）'}")
print(f"  距 4,300 = {(HSTECH_CUR-4300)/4300*100:+.4f}%  距 4,400 = {(HSTECH_CUR-4400)/4400*100:+.4f}%"
      f"  自 9/22 高点 4,510.06 = {(HSTECH_CUR/4510.06-1)*100:+.4f}%")
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

# ---------- 8. 敏感性（累积窗口 4 日，已定价 4 日） ----------
print('\n=== 敏感性：港联系累积窗口（4 日，已定价 4 日 —— 全部走完）===')
SENS = {}
for nm, p in (('bull_-2.0pct', -2.0), ('base_mid', mid_exact / HK_TOTAL * 100),
              ('bear_-6.0pct', -6.0), ('tail_-9.0pct', -9.0)):
    v = HK_TOTAL * p / 100
    SENS[nm] = round(v, 2)
    print(f'  {nm:20s} 累积 {p:+.3f}% → {v:>+11,.2f} 元（占基准 {v/BASE_TOTAL*100:+.3f}%）')

# ---------- 9. 输出（正式版 pending，覆盖预登记版） ----------
out = {
    'date': TODAY,
    'as_of': '2026-10-07 20:00（港股收盘后 · 长假最后一日）',
    'state': 'finalized',
    'finalized': True,
    'finalized_at': '2026-10-07 20:00',
    'finalized_note': ('§3.121b / §3.123a：混合档 `portfolio_pending_<DATE>.json` 的正式版归属当日 20:00 盘后档，'
                       '以港股 10/7 收盘价重算并覆盖同文件名；本档已覆盖 08:00 预登记版（state=preopen_estimate）。'
                       '**「防线判定权」与「减仓执行权」同归盘后档**（§3.123a）。'),
    'session': 'close',
    'session_type': SESSION_TYPE,
    'session_type_note': SESSION_NOTE,
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
        'day_high': HIGH, 'day_low': LOW,
        'date_field': hk['恒生科技']['date_field'], 'time_field': hk['恒生科技'].get('time_field'),
        'priced_for_today': True,
        'others': {k: {'close': v['cur'], 'pct': v['pct']} for k, v in hk.items()},
        'turnover_hkd_bn': 947.0,
        'turnover_note': ('10/2 1,458.04 亿 → 10/5 981.02 亿 → 10/6 982.65 亿 → 10/7 947.00 亿：'
                          '**⚠️ 口径更正（§3.129c）** —— 10/6 档所判「量能已触底而非继续恶化」被本档否证，'
                          '长假末段成交量继续下探至四日最低。'),
        'southbound': '港股通（南向）10/1-10/7 全程暂停、**10/8 恢复** → 本档为南向空窗第 4 个港股交易日、亦是长假内最后一个空窗日',
        'note': ('港股 10/7 收盘数据（新浪 hq 直连、返回体日期字段 2026/10/07 16:09:16），'
                 '已写入 indices.csv 真实收盘行并覆盖 13:45 伪收盘行（§3.122a / §3.127d）'),
    },
    'defense_hstech_4250': {
        'close': HSTECH_CUR, 'prev_close': HSTECH_PREV, 'line': 4250,
        'dist_pts': round(Dv, 3), 'dist_pct': round(Dv / 4250 * 100, 4),
        'state': 'close_level_break_unchanged' if TRIGGER_NOW else 'recovered_above_4250_but_discipline_locked',
        'intraday_touched_above': TOUCHED_ABOVE,
        'intraday_above_note': (f'日内最高 {HIGH} < 4,250 → **全日未站上 4,250**（与 10/6 档日内高 4,251.54 不同）；'
                                f'⚠️ 表述纪律（§3.129b / §3.117d）：`state` 只依**收盘价**赋值，盘中读数仅作附注。'),
        'trigger_recheck': False,
        'trigger_recheck_note': ('§3.114c：判定权已于 10/2 收盘级锁定（4,157.94 破位 −2.1661%），'
                                 '本档只做「破位状态未改变」的事实确认，**不重复判定、不叠加新纪律**；'
                                 '同日防线只触发一次，即使 10/8 收盘站上 4,250，已登记的第 2 次减仓亦须于 10/8 执行。'),
        'break_type': ('非边际破位（10/2 −2.1661%）；'
                       '10/5 −1.5605% → 10/6 −0.6342% → **10/7 −1.3061%（幅度重新扩大）**'
                       '→ 前档「连续两档收窄」的趋势**被否证**（§3.129c）。'),
        'dist_trend': {'2026-10-02': -2.1661, '2026-10-05': -1.5605, '2026-10-06': -0.6342, '2026-10-07': -1.3061},
        'action': '第 2 次 0.5% 纪律减仓',
        'cut_pct': 0.5, 'cut_amount': CUT_AMT,
        'cut_basis': f'{BASE_TOTAL:,.2f} 元 × 0.5%（§3.114c / §3.123e 确定性口径，判定锁定于 10/2）',
        'cut_targets': ['012348（天弘恒生科技联接A）', '513180（恒生科技ETF华夏）'],
        'cut_target_rule': '标的限「纯恒科」口径，不落在中概（513050 / 164906）',
        'executed': False, 'execution_pending': True, 'execute_at': '2026-10-08（A股 + 港股通复市首日）',
        'execution_note': ('A股 休市期组合不可交易：场内 ETF 无交易时段、场外联接不发净值、港股通关闭 → '
                           '本档仅完成「状态确认」，实际成交与结算待 10/8 按当日净值执行'),
        'prev_intraday_ref': {'as_of': '2026-10-07 13:45', 'price': 4186.10,
                              'note': ('盘中档报 −0.88%（13:45）；收盘 4,194.49 / −0.677% → 尾盘小幅回升；'
                                       '⚠️ 按 §3.117d，盘中结论由盘后档逐条复核并以收盘价重述。')},
        'cost_note': ('§3.117b / §3.117c：第 2 次减仓尚未成交（执行待 10/8）；已成交的第 1 次（9/30 按净值 1,882.46 元）'
                      '对应 9/29 收 4,249.62 边际破位 → 次日 9/30 即收复 4,253.89，成本须如实记录、不得事后否认。'),
    },
    'hk_pending_digest': {
        'window': ['2026-10-02', '2026-10-05', '2026-10-06', '2026-10-07'],
        'priced_days': 4, 'total_days': 4,
        'as_of': '2026-10-07 收盘（港股真实收盘价，累计 10/2 + 10/5 + 10/6 + 10/7 四段 —— **长假完整走完**）',
        'cumulative_note': '累积口径 = 各段代理涨跌**几何复合** (1+r1)(1+r2)(1+r3)(1+r4)−1（§3.126c），非简单相加',
        'combo_count': len(combos_all),
        'interval_rule': ('§3.129a：跨档累积**禁止用前档区间端点当输入** → 本档以前档 `segments[].cum_pct` 的'
                          '**值列表**（纯恒科 1 值 / 中概 8 值 / 宽基 8 值）与本档 2 × 2 做完整笛卡尔积 = '
                          '1 × 8 × 8 × 2 × 2 = 256 组，逐组求「合计结果值」后 sorted 取 min/max（§3.116b / §3.123b / §3.116b）。'),
        'segments': {
            leg: {'mv': rows[leg]['mv'],
                  'prev_segment_pct': [round(p, 4) for p in rows[leg]['prev']],
                  'today_segment_pct': [round(p, 4) for p in rows[leg]['today']],
                  'cum_pct': [round(c, 4) for c in rows[leg]['cum']],
                  'outs': [round(o, 2) for o in rows[leg]['outs']]} for leg in rows},
        'proxies_used': {'pure_hstech': 'HSTECH 收盘涨跌',
                         'china_internet': '8 名等权（最差）/ 6 名大市值平台（最优）',
                         'broad_hk': '恒生综合 / 恒生指数（笛卡尔积取 min/max 于**合计结果值**上，§3.116b / §3.123b）'},
        'hk_total': HK_TOTAL, 'hk_pct': round(HK_TOTAL / BASE_TOTAL * 100, 2),
        'total_low': round(HK_LOW, 2), 'total_high': round(HK_HIGH, 2),
        'mid_proxy_avg': round(mid_exact, 2),
        'track_only_low': round(track_low, 2), 'track_only_high': round(track_high, 2),
        'broad_hk_low': round(broad_low, 2), 'broad_hk_high': round(broad_high, 2),
        'day_only_1007_low': round(min(d_low, d_high), 2),
        'day_only_1007_high': round(max(d_low, d_high), 2),
        'segment_by_day_hstech': SEG_BY_DAY,
        'segment_by_day_source': ('§3.133a：逐日段由 indices.csv（code=HSTECH，(code,date) 后写覆盖先写去重）**现算**，'
                                  '禁止手工硬编码常量。本档修复：2026-10-05 段由 −0.6689%（旧硬编码常量）'
                                  '更正为 **+0.6191%**（4,183.68 / 4,157.94 − 1）——符号与幅度双错，'
                                  '累积口径不受影响（累积另由 prev/today 段列表计算），仅展示字段被误导。'),
        'prev_total_low': _prev_pf['hk_pending_digest']['total_low'],
        'prev_total_high': _prev_pf['hk_pending_digest']['total_high'],
        'refreshed': True,
        'finalized': True,
        'rule': ('§3.108 条款 23/24 + §3.116b + §3.126c + §3.129a：三段法 + 几何复合 + 笛卡尔积 min/max、'
                 '只给区间上下界、不得作方向判断；本档为累积窗口**第 4 日（4/4，长假全部走完）**，'
                 '**10/8 起该窗口关闭、不再延续**。'),
        'holiday_rule_note': ('10/7 为南向空窗第 4 日、仍是外资 + 本地资金主导定价（港股通 10/1-10/7 暂停、**10/8 恢复**，'
                              '§3.115d / §3.121e）；成交 1,458.04 亿（10/2）→ 981.02（10/5）→ 982.65（10/6）→ **947.00（10/7）**；'
                              '⚠️ §3.122f / §3.121e：**静态测算只可给区间上下界、不得作方向判断**。'),
        'window_closed': True,
    },
    'qdii_pending': {
        'refreshed': False,
        'reason': ('本档无新增美股交易日入库（US 10/7 收盘成型于北京 10/8 04:00；北京 10/7 20:00 = 美东 10/7 08:00 EDT，尚未开盘，§3.120c）'
                   '→ 挂账区间沿用 10/7 盘前档值（该档已纳入 US 10/6 段）'),
        'component_a': {'desc': 'QDII 000369/016280 的 9/29 净值（基准净值日 9/28）', 'amount': -267.82,
                        'trade_date_covered': '2026-09-29'},
        'component_b': {'desc': '自 US 9/30 起未可观测段：IYH 9/30 −1.17% × 10/1 −1.62% × 10/2 +0.00% × 10/5 +0.7244% × 10/6 −0.34% 复合 −2.3997%（IYH 口径）',
                        'trade_dates_covered': ['2026-09-30', '2026-10-01', '2026-10-02', '2026-10-05', '2026-10-06'],
                        'notional': -1431.28,
                        'low': -1288.15, 'mid': -1030.52, 'high': -858.77, 'coef_range': [0.6, 0.9]},
        'total_low': -1555.97, 'total_mid': -1298.34, 'total_high': -1126.59,
        'unknown_sessions': ['2026-10-07'],
        'coef_note': ('§3.118a：长假前后实测隐含系数 1.25~1.29，远超标定 0.72 / 常态实测 0.62（§3.114e）'
                      '→ **只给区间、禁止中枢点值**；按 1.25 折算则两端均可能被击穿；'
                      '**系数未重估前基于该系数的一切仓位决策无效**；10/8 须以 ≥4 券位 × ≥5 交易日样本重估。'),
    },
    'sentiment': {
        'window': WIN, 'n': len(win), 'nominal_net': nominal, 'exposure_weighted_net': round(wsum, 3),
        'weighted_ratio_pct': round(wsum / nominal * 100, 1) if nominal else None,
        'formula_note': '名义净分 = Σ利多强度 − Σ利空强度；暴露加权净分 = Σ(赛道净强度分 × 赛道权重)（§3.128e 就地写公式）',
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
        'annotation_mode': sent.get('annotation_mode'),
        'degraded_items': sent.get('degraded_items'),
        'degraded_batches': sent.get('degraded_batches'),
        'degradation_reason': sent.get('degradation_reason'),
        'note': ('⚠️ §3.127b / §3.128a：本档（含盘前 35 + 盘中 26 + 盘后 23 = 84 条）情绪标签 100% 来自'
                 '**确定性规则表（非模型标注）** —— DeepSeek v4-flash 端点返回 HTTP 402 `Insufficient Balance` '
                 '（额度耗尽，非 429 限流）→ 停止重试并降级。规则表以「标题前 24 字」硬绑定 + 未命中即终止（§3.128a）+ '
                 '前缀唯一性守卫（§3.129d），属 agent 逐条指定的「人工口径」、非随机 fallback。'
                 '⚠️ **跨档比较均值强度/净分时不可与模型标注档直接混算趋势**。'
                 '⚠️ 本档为「零定价」档（除港股外全部标的不可定价）→ 情绪与价格无法做当日方向验证（§3.85 前提不成立），10/8 方可开始验证。'),
    },
    'other_defense_lines': {
        'zz_consume_12100': {'last': zz, 'dist_pct': round((zz - 12100) / 12100 * 100, 4),
                             'state': 'above_lower_line_last_known', 'next_line': 12000,
                             'next_line_dist_pct': round((zz - 12000) / 12000 * 100, 3),
                             'verify_at': '2026-10-08（A股复市）'},
        'a_med_reverse_1_5pct': {'proxy_pct': 2.8697, 'state': 'not_triggered', 'verify_at': '2026-10-08（A股复市）'},
        'sh_comp': {'last': sh},
        'hshci_hk_healthcare': {'close': hk['恒生医疗保健']['cur'], 'pct': hk['恒生医疗保健']['pct'],
                                'note': ('港股医药生物本档领跌（−2.39%，金斯瑞生物科技 −12.74%）；组合零港股医药暴露 → 零直接损益；'
                                         '对 10/8 A股 医药为**弱负向**情绪映射（与 10/6 的 +2.86% 完全对调），须由价格证伪')},
        'hscei': {'close': hk['恒生国企']['cur'], 'pct': hk['恒生国企']['pct']},
        'hsi': {'close': hk['恒生指数']['cur'], 'pct': hk['恒生指数']['pct'],
                'note': '恒指 −0.62% 报 24,130.50，回吐 10/6 的 +1.00%；长假四日累计 −1.96%'},
    },
    'med_exposure': {'mv': round(med_mv, 2), 'pct': round(med_pct, 2), 'non_med_total': round(non_med, 2),
                     'threshold_all_med_pct': round(th_all, 2), 'threshold_a_sh_med_pct': round(th_a, 2),
                     'rule': '§3.98 方程解法 A(1+r)/(B+A(1+r)) = 40%'},
    'hk_exposure': {'total': HK_TOTAL, 'pct': round(HK_TOTAL / BASE_TOTAL * 100, 2), 'segments': hk_seg,
                    'southbound_gap_days': ['2026-10-02', '2026-10-05', '2026-10-06', '2026-10-07'],
                    'gap_day_index_today': 4,
                    'rule_hint': '只报赛道层 8.29% 将低估 4.84pct（宽基层），§3.108 条款 23'},
    'sensitivity': SENS,
    'pending_consume': {
        'hold_decision': 'no_action',
        'reason': ('混合档必做待消化；本档港股腿已按 10/7 **收盘价**完成累积第 4 日计算（区间 '
                   f'{HK_LOW:,.2f} 元 ~ {HK_HIGH:,.2f} 元，256 组笛卡尔积、几何复合）。'
                   '但组合唯一可执行的交易窗口 = 10/8（A股 + 港股通 + 南向同时恢复）→ 本档不做任何赛道级调整；'
                   '恒生科技 0.5% 减仓为 10/2 已锁定的第 2 次触发、执行待 10/8。'),
        'estimated_combo_return_pct': 0.0, 'estimated_combo_pnl': 0.0,
        'attribution': ('A股 10/1-10/7 休市 → 场外基金无净值、场内无成交价；组合未直接持有港交所上市工具 → '
                        '港股行情不产生组合层当日定价 → 当日可实现盈亏恒为 0，归因「标的不可定价」而非「市场持平」（§3.107）。'
                        '三层结构（§3.121d）：① A股腿不可定价（待 10/8）；② 港股腿 10/7 已收盘但组合无港交所直接持仓 → '
                        '入「待消化」；③ 美股/QDII 腿可定价（US 10/6 已收）但落在挂账区间内、按既定规则不入基准。'),
        'new_action_count': 0,
        'new_action_detail': '本档无新增纪律动作（恒科破位判定已于 10/2 锁定、不重复判定、不叠加；全日未站上 4,250 亦不改变状态）',
        'carried_over_action': f'恒生科技 0.5% 纪律减仓 {CUT_AMT:,.2f} 元（10/2 判定，执行待 10/8）',
    },
    'action': {'new_buy': 0, 'active_take_profit': 0, 'discipline_cut_pending': 1,
               'discipline_cut_amount': CUT_AMT, 'settled_discipline_cut': 0, 'new_pending': 0,
               'cumulative_discipline_amount': CUM_CUT,
               'note': '赛道级动作：0 买入 / 0 主动止盈 / 1 项纪律减仓（10/2 判定、执行待 10/8）'},
    'chain_0pct_row_inserted': False,
    'chain_note': '混合档不产 portfolio_close_*、不向链式序列插入 0% 行（§3.108 条款 22 / §3.122c）；链式末行仍 = 2026-09-30（_fix）',
    'risk_stats_source': 'risk_stats_20261007_preopen.json（本档不重算，§3.127e）',
    'holiday_leg_pricing': {
        'a_share_leg': {'priced': False, 'reason': 'A股 10/1-10/7 休市（最后一日）', 'next': '2026-10-08'},
        'hk_leg': {'priced': True, 'reason': '港股 10/7 已收盘（续市第 4 个交易日 · 长假最后一日）',
                   'ref': 'HSTECH 4,194.49 / −0.68%；恒指 24,130.50 / −0.62%；恒生医疗保健 3,890.43 / −2.39%',
                   'note': '组合无港交所上市直接持仓 → 进入「待消化」而非「当日盈亏」；长假四日窗口本档走完'},
        'us_qdii_leg': {'priced': False, 'reason': 'US 10/7 尚未开盘（北京 20:00 = 美东 08:00）',
                        'note': '美股上一有效收盘 = 10/6，已于 10/7 盘前档入库，其传导属 QDII 挂账项'},
    },
    'holiday_window_status': {
        'days_total': 7, 'days_elapsed': 7,
        'a_share_market': '10/1-10/7 全休（10/8 复市）',
        'hk_market': '10/1 休市、10/2 / 10/5 / 10/6 / 10/7 四个交易日（本档为最后一个）',
        'southbound': '港股通 10/1-10/7 全程关闭（10/8 恢复）',
        'us_market': '长假内正常交易（10/1-10/6 共 5 个交易日；10/7 待北京 10/8 04:00 成型）',
        'next_session': '2026-10-08（A股 + 港股通 / 南向同时恢复；恒科减仓执行日）',
    },
    'note': ('混合档第 4 日盘后台账（**正式版**）：港股腿已按 10/7 收盘价完成累积窗口**第 4 日（4/4，长假全部走完）**定价'
             f'（{HK_LOW:,.2f} 元 ~ {HK_HIGH:,.2f} 元，256 组笛卡尔积、几何复合口径，§3.129a）；'
             'A股腿待 10/8；美股/QDII 腿在挂账口径内（零变动、尚余 US 10/7 一个未知交易日）。'
             '恒生科技 4,250 破位状态未改变（距 −1.3061%，**幅度较 10/6 重新扩大**）、全日未站上防线、'
             '第 2 次 0.5% 减仓执行待 10/8。本档不产 portfolio_close_*。'
             '⚠️ 口径更正（§3.129c）：10/6 档所判「长假量能已触底」被 10/7 成交 947.00 亿否证；'
             '「破位幅度连续收窄」的趋势亦被 −1.3061% 否证。'),
}
oj = os.path.join(HIST, f'portfolio_pending_{TODAY.replace("-", "")}.json')
json.dump(out, open(oj, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(f'\n已保存（覆盖预登记版）{os.path.basename(oj)}  state={out["state"]} finalized={out["finalized"]}')
