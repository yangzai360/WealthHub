# -*- coding: utf-8 -*-
"""2026-10-20（周二 · **档型③「正常交易日盘前」：A股 + 港股（重阳翌日后复市）+ 美股 三市场均正常交易日**）事件库处理：
  ① 回填：按「参考指数在事件日（或之后）已有真实收盘 → 回填」通用规则逐条判空
     - **本档唯一新增真实收盘 = US 10/19**（XLV 175.65 / −0.60%，已于本档 08:00 归档）
       → 美股标普医药类留空条目**本档可回填**；A股（10/20）与港股（10/20 复市）当日收盘未成型 → 继续留空。
     - **本档新增条目的参考交易日逐市场分列（§3.119c / §3.157a）**：
       A股医药/大消费/其他·宽基/宏观 → 2026-10-20（今日 09:30 开盘）；
       恒生科技 → 2026-10-20（**港股 10/20 复市，本档为其复市首日盘前**）；
       美股标普医药 → 2026-10-19（美东日历日，收盘已于北京 10/20 04:00 成型 → **本档即可回填**）。
  ①b **§3.141a ② 跨档连续性守卫**：以「上一档（10/19 20:00 盘后档）时点各市场可得的最新真实收盘日」为截止日，
       检出「留空条目中参考日 ≤ 该截止日」者 → miss_count > 0 须人工排查。
  ② 追加本档盘前事件（含空集硬守卫、§3.130a 双侧同长前缀 + 全称兜底）
  ③ 全库完整性扫描（留空按「日期×赛道」二维落库，§3.98）
  ④ 1 日样本 + 3/5/10 日窗口统计 → history/event_stats_20261020_preopen.json
⚠️ 参考日口径：**「下一个交易日」= 该事件参考指数的下一个交易日**（§3.119c），不是「下一个 A股 交易日」。
   宏观 = 000001。A股医药 3/5/10 日窗口代理 = 399006（创业板指，§3.90），1 日窗口 = 000933。
⚠️ §3.158：`strict_after` **按市场分列** —— A股/港股/宏观类「盘后/周末」窗口事件顺延；**美股类一律不顺延**。
⚠️ §3.110 条款 27：休市档回填判据 = 「该事件参考指数在当日是否有真实收盘」，**不是「当日是否 A股 交易日」**。
⚠️ §3.114a：枚举型字段 track 写入前做全等校验（硬守卫）。
⚠️ §3.144a：暴露权重取 **10/19 修正件 `tracks[].mv`**（非 `detail[].mv` 陈旧继承值）。
⚠️ §3.113e / §3.121c：本脚本由 events_preopen_20261019.py 改写（非 sed 派生），
   已逐项核对「读写路径 / 日期常量 / docstring 档型语义 / 产物 note 自然语言字段」四类字面量。
"""
import json, os, glob, csv, datetime
from collections import defaultdict

BASE = '/Users/jieyang/Documents/WealthHub'
EV = os.path.join(BASE, 'data/processed/events')
HIST = os.path.join(BASE, 'data/processed/history')
TODAY = '2026-10-20'
WIN = '盘前(10/19 20:00-10/20 07:30)'
REF_INDEX = {'宏观': '000001', 'A股医药': '000933', '大消费': '000932', '恒生科技': 'HSTECH',
             '美股标普医药': 'XLV', '其他/宽基': '000300'}
DIR_DAY = '2026-10-19'
REF_TD = '2026-10-20'
REF_BY_TRACK = {'宏观': '2026-10-20', 'A股医药': '2026-10-20', '大消费': '2026-10-20',
                '恒生科技': '2026-10-20', '美股标普医药': '2026-10-19', '其他/宽基': '2026-10-20'}
PREV_SESSION = '2026-10-19 20:00 盘后档'
PREV_CUTOFF_BY_TRACK = {'宏观': '2026-10-19', 'A股医药': '2026-10-19', '大消费': '2026-10-19',
                        '恒生科技': '2026-10-16', '其他/宽基': '2026-10-19',
                        '美股标普医药': '2026-10-19'}

idx = defaultdict(dict)
with open(os.path.join(HIST, 'indices.csv'), encoding='utf-8-sig') as fh:
    for row in csv.DictReader(fh):
        try:
            idx[row['code']][row['date']] = float(row['close'])
        except Exception:
            pass
for code in sorted(set(REF_INDEX.values())):
    ds = sorted(idx.get(code, {}))
    print(f'  {code}: {len(ds)} 个交易日，尾部 ' + ' | '.join(f'{d}:{idx[code][d]}' for d in ds[-3:]))


def ref_ret(code, event_date, strictly_after=False):
    """§3.127a：ref 交易日 = 事件日（或之后）的首个有真实收盘的交易日；
    `strictly_after=True` 用于「盘后/周末窗口采集」的事件 → 参考日 = 事件日**之后**的首个交易日。"""
    ser = idx.get(code)
    if not ser:
        return None, None
    ds = sorted(ser)
    for i, d in enumerate(ds):
        ok = (d > event_date) if strictly_after else (d >= event_date)
        if ok and i > 0:
            return d, round((ser[d] / ser[ds[i - 1]] - 1) * 100, 4)
    return None, None


# ---------- §3.158：strict_after 按市场分列 ----------
def needs_defer(e):
    """§3.158：A股/港股/宏观类「盘后或周末窗口」事件须顺延；**美股类一律不顺延**。"""
    w = e.get('window') or ''
    return w.startswith(('盘后', '周末')) and e.get('track') != '美股标普医药'


# ---------- ①b 跨档连续性守卫（在回填前取「载入态」） ----------
_loaded = []
for f in sorted(glob.glob(os.path.join(EV, 'events-*.json'))):
    _loaded.extend(json.load(open(f, encoding='utf-8')))
guard_checked, guard_miss = 0, []
for e in _loaded:
    r0 = e.get('reference') or {}
    if r0.get('actual_ret_1d') is not None:
        continue
    code = REF_INDEX.get(e['track'])
    if not code:
        continue
    d_ref, _ = ref_ret(code, e['date'], strictly_after=needs_defer(e))
    if d_ref is None:
        continue
    guard_checked += 1
    cutoff = PREV_CUTOFF_BY_TRACK.get(e['track'])
    if cutoff and d_ref <= cutoff:
        guard_miss.append({'event': e['title'][:46], 'event_date': e['date'], 'track': e['track'],
                           'ref_day': d_ref, 'prev_cutoff': cutoff})
print(f"\n§3.141a ② 跨档连续性守卫：载入态留空 {sum(1 for e in _loaded if (e.get('reference') or {}).get('actual_ret_1d') is None)} 条，"
      f"可判定 {guard_checked} 条，miss_count = {len(guard_miss)}")
for m in guard_miss:
    print('  ⚠️ WARNING 上一档应回填而漏回填:', m)

# ---------- ① 回填（按 id 归位写回，幂等，§3.123d） ----------
backfilled, back_detail = 0, []
for f in sorted(glob.glob(os.path.join(EV, 'events-*.json'))):
    ev = json.load(open(f, encoding='utf-8'))
    touched = False
    for e in ev:
        code = REF_INDEX.get(e['track'])
        if not code:
            continue
        ref = e.setdefault('reference', {})
        if ref.get('actual_ret_1d') is not None:
            continue
        defer = needs_defer(e)
        d, r = ref_ret(code, e['date'], strictly_after=defer)
        if r is None:
            if defer and not ref.get('backfill_deferred_reason'):
                ref['backfill_deferred_reason'] = (
                    '§3.158：本事件采集窗口为盘后/周末，已晚于该市场当日收盘'
                    '（A股 15:00 / 港股 16:00，北京时间）→ 参考交易日顺延至事件日之后的下一交易日；'
                    '本档 08:00 该日收盘尚未成型 → 留空，属预期状态')
                touched = True
            continue
        ref['actual_ret_1d'] = r
        ref['actual_date'] = d
        ref['ret_1d_ref'] = f'{d} 收盘：{code} {idx[code][d]} {r:+.2f}%'
        if defer:
            ref['backfill_deferred_applied'] = True
        backfilled += 1
        touched = True
        back_detail.append({'file': os.path.basename(f), 'date': e['date'], 'track': e['track'],
                            'actual_date': d, 'ret_1d': r, 'deferred_rule': defer})
    if touched:
        json.dump(ev, open(f, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
by_evdate, by_track_bf = defaultdict(int), defaultdict(int)
for x in back_detail:
    by_evdate[x['date']] += 1
    by_track_bf[x['track']] += 1
print(f'\n回填 {backfilled} 条；按事件日 {dict(by_evdate)}；按赛道 {dict(by_track_bf)}')
by_adate = defaultdict(int)
for x in back_detail:
    by_adate[x['actual_date']] += 1
print(f'  回填实际交易日分布: {dict(by_adate)}')
_defer_marks = sum(1 for f2 in sorted(glob.glob(os.path.join(EV, 'events-*.json')))
                   for e2 in json.load(open(f2, encoding='utf-8'))
                   if (e2.get('reference') or {}).get('backfill_deferred_reason'))
print(f'  §3.158 盘后/周末窗口顺延标记（backfill_deferred_reason）累计: {_defer_marks} 条')

# ---------- ② 追加本档事件 ----------
news = json.load(open(os.path.join(BASE, f'data/processed/news/news-{TODAY}.json'), encoding='utf-8'))
sent = json.load(open(os.path.join(BASE, f'data/processed/news/sentiment-{TODAY}.json'), encoding='utf-8'))
ev_path = os.path.join(EV, f'events-{TODAY}.json')
ev = json.load(open(ev_path, encoding='utf-8')) if os.path.exists(ev_path) else []
existing = {e['title'][:60] for e in ev}
existing_full = {e['title'] for e in ev}

win_sent = [x for x in sent['items'] if x.get('window') == WIN]
if not win_sent:
    raise SystemExit('⚠️ 盘前窗口 sentiment 为 0 条 → per-item `window` 字段可能缺失（§3.103），终止')
added, missed = [], 0
for x in win_sent:
    # §3.130a：双侧同长前缀比对 + 全称兜底，未命中即告警（禁止静默 continue）
    n = next((y for y in news if y['title'][:60] == x['title'][:60]), None)
    if n is None:
        n = next((y for y in news if y['title'] == x['title']), None)
    if n is None:
        missed += 1
        print('  ⚠️ WARNING sentiment 条目未在 news 中命中:', x['title'][:40])
        continue
    if n['title'][:60] in existing or n['title'] in existing_full:
        continue
    seq = len(ev) + len(added) + 1
    added.append({
        'id': f"N{TODAY.replace('-', '')}-{seq:03d}", 'date': TODAY, 'track': n['track'],
        'category': n.get('category', '行业事件类'), 'title': n['title'],
        'summary': n.get('summary', ''), 'source': n.get('source', 'WebSearch'),
        'source_url': n.get('source_url', ''), 'sentiment': n.get('sentiment'),
        'score': n.get('score'), 'strength': n.get('strength'),
        'direction': n.get('direction'), 'volatility': n.get('volatility'),
        'reason': n.get('brief', ''),
        'window': WIN,
        'reference': {'ret_3d': None, 'ret_5d': None, 'ret_10d': None,
                      'actual_ret_1d': None, 'actual_date': None,
                      'max_vol': {'低': 1.5, '中': 4.8, '高': 9.0}.get(n.get('volatility'), 4.8),
                      'confidence': n.get('confidence'),
                      'ref_trade_day_planned': REF_BY_TRACK.get(n['track']),
                      'ret_1d_ref': (f'盘前档（{TODAY} 08:00，A股/港股 均未开盘）；逐市场参考交易日 = '
                                     f'{REF_BY_TRACK.get(n["track"])}，待该日收盘回填')},
    })
VALID_TRACK = {'宏观', 'A股医药', '大消费', '恒生科技', '美股标普医药', '其他/宽基'}
_bad = {x['track'] for x in added} - VALID_TRACK
if _bad:
    raise SystemExit(f'⚠️ 非法 track 值 {_bad} → 会静默跳过回填与加权，终止（§3.114a）')
_badall = {e['track'] for e in ev} - VALID_TRACK
if _badall:
    raise SystemExit(f'⚠️ 库内非法 track 值 {_badall}，终止（§3.114a）')

ev.extend(added)

# ---------- ②b 【本档新增】当日「美股标普医药」事件即时回填 ----------
# 依据：盘前窗口（10/19 20:00-10/20 07:30 北京）对应的美股交易日为 **10/19**，
#       而 XLV 10/19 收盘已于本档 08:00 归档（175.65 / −0.60%）→ 该 3 条**本档即可回填**，
#       无需像 A股/港股（参考日 10/20 未成型）那样留空。
# ⚠️ 若不做此步，下一档 `ref_ret(XLV, '2026-10-20')` 会取到 **US 10/20** 收盘 → 参考日错位 1 天。
_bf_us = 0
for e in ev:
    if e['date'] != TODAY or e['track'] != '美股标普医药':
        continue
    ref = e.setdefault('reference', {})
    if ref.get('actual_ret_1d') is not None:
        continue
    d_ref, r = ref_ret('XLV', REF_BY_TRACK['美股标普医药'])
    if r is None:
        continue
    ref['actual_ret_1d'] = r
    ref['actual_date'] = d_ref
    ref['ret_1d_ref'] = f'{d_ref} 收盘：XLV {idx["XLV"][d_ref]} {r:+.2f}%'
    ref['backfill_note'] = '盘前窗口对应的美股交易日 = 10/19，XLV 10/19 收盘已于本档归档 → 即时回填（非顺延）'
    _bf_us += 1
print(f'②b 当日美股标普医药事件即时回填 {_bf_us} 条（参考日 {REF_BY_TRACK["美股标普医药"]}）')
backfilled += _bf_us

json.dump(ev, open(ev_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(f'事件库 {TODAY} +{len(added)} 条 → 当日 {len(ev)} 条（未命中告警 {missed} 条）')

# ---------- ③ 完整性扫描 ----------
files = sorted(glob.glob(os.path.join(EV, 'events-*.json')))
all_ev, dup = [], {}
for f in files:
    for e in json.load(open(f, encoding='utf-8')):
        all_ev.append(e)
        dup[e['title'][:60]] = dup.get(e['title'][:60], 0) + 1
n_blank = sum(1 for e in all_ev if (e.get('reference') or {}).get('actual_ret_1d') is None)
blank_by_date, blank_by_track = defaultdict(int), defaultdict(int)
for e in all_ev:
    if (e.get('reference') or {}).get('actual_ret_1d') is None:
        blank_by_date[e['date']] += 1
        blank_by_track[e['track']] += 1
no_adate = sum(1 for e in all_ev if (e.get('reference') or {}).get('actual_ret_1d') is not None
               and not (e.get('reference') or {}).get('actual_date'))
print(f'\n全库 {len(all_ev)} 条 / {len(files)} 日；留空(actual_ret_1d is None) {n_blank} 条')
print(f'  留空按日: {dict(sorted(blank_by_date.items()))}')
print(f'  留空按赛道: {dict(sorted(blank_by_track.items()))}')
print(f'  ⚠️ legacy 字段不全（有 actual_ret_1d 但缺 actual_date）: {no_adate} 条（不计入留空，见 §3.106）')
print(f'  跨日重复标题 {sum(1 for v in dup.values() if v > 1)} 组')
today_all = sum(1 for e in all_ev if e['date'] == TODAY)
blank_pairs = defaultdict(int)
for e in all_ev:
    if (e.get('reference') or {}).get('actual_ret_1d') is None:
        blank_pairs[(e['date'], e['track'])] += 1
print(f'  【留空构成】当日({TODAY})新增 {today_all} 条；留空分布（事件日×赛道）:')
for (d0, t0), c in sorted(blank_pairs.items()):
    if d0 >= '2026-10-14':
        print(f'    {d0} {t0}: {c} 条  (参考交易日 = {REF_BY_TRACK.get(t0, REF_TD)})')

# ---------- ④ 统计 ----------
track_index = {'A股医药': '399006', '大消费': '000932', '恒生科技': 'HSTECH',
               '美股标普医药': 'XLV', '其他/宽基': '000300'}


def fwd(code, d0, n):
    ser = idx.get(code)
    if not ser:
        return None
    ds = sorted(d for d in ser if d >= d0)
    if len(ds) < n + 1:
        return None
    try:
        return round((ser[ds[n]] / ser[ds[0]] - 1) * 100, 4)
    except Exception:
        return None


win, ones = defaultdict(lambda: defaultdict(list)), defaultdict(list)
for e in all_ev:
    t = e['track']
    r = e.get('reference') or {}
    v = r.get('actual_ret_1d')
    if v is not None and t in track_index:
        ones[t].append((v, e.get('direction'), e.get('strength')))
    code = track_index.get(t)
    if not code:
        continue
    for n in (3, 5, 10):
        x = fwd(code, e['date'], n)
        if x is not None:
            win[t][n].append(x)

# ---------- ④b §3.112b 稀疏序列三重守卫 ----------
MIN_DAYS = 20
sparse = {}
for t, code in track_index.items():
    ser = idx.get(code) or {}
    ds = sorted(ser)
    n_days = len(ds)
    first_obs = ds[0] if ds else None
    span = (datetime.date.fromisoformat(ds[-1]) - datetime.date.fromisoformat(first_obs)).days if ds else None
    offset = None
    for e in all_ev:
        if e['track'] != t:
            continue
        if first_obs:
            offset = (datetime.date.fromisoformat(first_obs) - datetime.date.fromisoformat(e['date'])).days
        break
    flags = []
    if n_days < MIN_DAYS:
        flags.append(f'distinct_days={n_days}<{MIN_DAYS}')
    if offset is not None and offset > 5:
        flags.append(f'start_offset={offset}d>5')
    lim = 2.2 * n_days + 3
    if span is not None and span > lim:
        flags.append(f'calendar_span={span}d>2.2*{n_days}+3={lim:.1f}')
    if flags:
        sparse[code] = flags
print(f'\n§3.112b 稀疏代理指数守卫（MIN_DAYS={MIN_DAYS}）: ' + (str(sparse) if sparse else '全部通过'))
for t, code in track_index.items():
    ser = idx.get(code) or {}
    ds = sorted(ser)
    span = (datetime.date.fromisoformat(ds[-1]) - datetime.date.fromisoformat(ds[0])).days if ds else None
    lim = 2.2 * len(ds) + 3
    print(f'  {t:8s} proxy={code:8s} distinct_days={len(ds):4d} span={span}d lim={lim:.1f} '
          f'{"OK" if span is not None and span <= lim else "SPARSE"}')

print('\n1 日样本（按赛道，全库）:')
for t, arr in sorted(ones.items()):
    vs = [a[0] for a in arr]
    sp = [a[0] for a in arr if a[1] == '利多' and (a[2] or 0) >= 70]
    sn = [a[0] for a in arr if a[1] == '利空' and (a[2] or 0) >= 70]
    line = (f"  {t:8s} n={len(vs):>4d} 均值={sum(vs)/len(vs):+.4f}% "
            f"上涨占比={sum(1 for v in vs if v>0)/len(vs):.4f}")
    if sp:
        line += f" 强正面={sum(sp)/len(sp):+.4f}%(n={len(sp)})"
    if sn:
        line += f" 强负面={sum(sn)/len(sn):+.4f}%(n={len(sn)})"
    print(line)

print('\n3/5/10 日窗口:')
for t, d in sorted(win.items()):
    row = []
    for n in (3, 5, 10):
        a = d[n]
        row.append(f"{n}日={sum(a)/len(a):+.4f}%(n={len(a)})" if a else f"{n}日=n/a（全库无样本）")
    print(f"  {t:8s} " + ' | '.join(row))
win_unavail = {t: [n for n in (3, 5, 10) if not d.get(n)] for t, d in win.items()}
print(f'  窗口不可用数: {win_unavail}')

# 方向验证（参考日 == DIR_DAY 显式过滤，§3.115b / §3.158）
hit, tot, all_tot = 0, 0, 0
by_dir = defaultdict(lambda: [0, 0])
for e in all_ev:
    r0 = e.get('reference') or {}
    if e['date'] != DIR_DAY:
        continue
    all_tot += 1
    if r0.get('actual_date') != DIR_DAY:
        continue
    v, d = r0.get('actual_ret_1d'), e.get('direction')
    if v is None or d not in ('利多', '利空'):
        continue
    tot += 1
    ok = (v > 0) if d == '利多' else (v < 0)
    hit += ok
    by_dir[d][0] += ok
    by_dir[d][1] += 1
print(f"\n方向验证（参考日 {DIR_DAY}，有效样本口径）: {hit}/{tot}"
      + (f"（{hit/tot*100:.1f}%）" if tot else "")
      + (f" — 利多 {by_dir['利多'][0]}/{by_dir['利多'][1]}、利空 {by_dir['利空'][0]}/{by_dir['利空'][1]}" if tot else "")
      + f" ｜ 有效样本 {tot} / 全部当日事件 {all_tot}")

# 暴露加权净情绪分
sent_all = json.load(open(os.path.join(BASE, f'data/processed/news/sentiment-{TODAY}.json'), encoding='utf-8'))
FIXNAME = 'portfolio_close_20261019_fix.json'
_FIXPATH = os.path.join(HIST, FIXNAME)
fx = json.load(open(_FIXPATH, encoding='utf-8'))
_tot = fx['total_mv']
EXPO = {t: round(100 * (v.get('mv') or 0) / _tot, 4) for t, v in fx['tracks'].items() if t != '现金'}
_dev = abs(sum(v.get('mv') or 0 for v in fx['tracks'].values()) - _tot)
if _dev >= 1.5:
    raise SystemExit(f'⚠️ 修正件 unreconciled：Σ tracks.mv − total_mv = {_dev:.2f} ≥ 1.5（§3.104 硬守卫），终止')
if abs(sum(EXPO.values()) + round(100 * (fx['tracks'].get('现金', {}).get('mv') or 0) / _tot, 4) - 100) > 0.05:
    raise SystemExit('⚠️ 暴露权重合计异常（非 100%），终止')
print(f'\n暴露权重来源：{FIXNAME} tracks[].mv（Σ dev = {_dev:.2f} 元，硬守卫通过）')
net = defaultdict(float)
for x in sent_all['items']:
    if x.get('window') != WIN:
        continue
    sg = 1 if x['direction'] == '利多' else (-1 if x['direction'] == '利空' else 0)
    net[x['track']] += sg * x['strength'] / 100
print('\n赛道净情绪分（Σ方向×强度/100）与暴露加权:')
expo_weighted = 0.0
for t in EXPO:
    print(f"  {t:8s} 净分={net[t]:+.2f}  暴露={EXPO[t]:.4f}%  贡献={net[t]*EXPO[t]/100:+.4f}")
    expo_weighted += net[t] * EXPO[t] / 100
print(f'  → 暴露加权净情绪分 = {expo_weighted:+.4f}')

out = {
    'date': TODAY, 'window': 'preopen', 'session_type': 'normal_trading_day_preopen',
    'session_type_note': '档型③「正常交易日盘前」= A股 10/20 正常交易日 + 港股 10/20 复市（10/19 重阳翌日休市）+ 美股 10/20 正常交易日（08:00 A股/港股 均无当日价格）',
    'total_events': len(all_ev), 'today_events': len(ev), 'blank': n_blank,
    'blank_by_date': dict(sorted(blank_by_date.items())),
    'blank_by_track': dict(sorted(blank_by_track.items())),
    'reference_trading_day': REF_TD,
    'reference_trading_day_by_track': REF_BY_TRACK,
    'legacy_missing_actual_date': no_adate,
    'backfilled': backfilled, 'backfill_by_event_date': dict(by_evdate),
    'after_close_deferred_rule': ('§3.158：window startswith(盘后/周末) 且 track != 美股标普医药 的事件，'
                                  '参考交易日 = 事件日**之后**的首个交易日（strictly_after=True）；'
                                  '美股类一律不顺延（其当日收盘成型于北京次日 04:00，晚于采集窗口）。'),
    'after_close_deferred_marked': _defer_marks,
    'backfill_by_track': dict(by_track_bf), 'backfill_by_actual_date': dict(by_adate),
    'cross_session_continuity_guard': {
        'prev_session': PREV_SESSION,
        'prev_cutoff_by_track': PREV_CUTOFF_BY_TRACK,
        'loaded_blank': sum(1 for e in _loaded if (e.get('reference') or {}).get('actual_ret_1d') is None),
        'checked': guard_checked, 'miss_count': len(guard_miss), 'miss': guard_miss,
        'note': ('§3.141a ②：以「上一档时点各市场可得的最新真实收盘日」为截止日，'
                 '检出「留空条目中参考日 ≤ 该截止日」者 = 上一档应回填而漏回填；'
                 'miss_count > 0 须人工排查后方可提交。'),
    },
    'backfill_note': (f'本档实际回填 {backfilled} 条 —— **本档唯一新增真实收盘 = US 10/19**'
                      '（XLV 175.65 / −0.60%、IYH 73.79 / −0.57%，已于本档 08:00 归档）→ '
                      '**美股标普医药类留空条目本档可回填**；A股（今日 09:30 开盘）与港股（10/20 复市）当日收盘均未成型 → 相应赛道留空属预期状态。'
                      f'本档新增 {today_all} 条参考交易日**逐市场分列（§3.119c / §3.157a）**：'
                      'A股医药/大消费/其他·宽基/宏观 → 2026-10-20；**恒生科技 → 2026-10-20（港股 10/20 复市，本档即复市首日盘前）**；'
                      '美股标普医药 → 2026-10-19（美东日历日，收盘已于北京 10/20 04:00 成型 → **本档即可回填**）。'
                      '⚠️ §3.110 条款 27：回填判据是「该事件参考指数在当日是否有真实收盘」，不是「当日是否 A股 交易日」。'),
    'onesample': {t: {'n': len(a), 'mean': round(sum(x[0] for x in a) / len(a), 4),
                      'min': min(x[0] for x in a), 'max': max(x[0] for x in a),
                      'up_ratio': round(sum(1 for x in a if x[0] > 0) / len(a), 4)}
                  for t, a in ones.items()},
    'windows': {t: {str(n): ({'n': len(a), 'mean': round(sum(a) / len(a), 4)} if a else {'n': 0, 'mean': None})
                    for n, a in d.items()}
                for t, d in win.items()},
    'window_unavailable': win_unavail,
    'window_sparse_tracks': {k: v for k, v in sparse.items()},
    'window_min_days': MIN_DAYS,
    'window_note': ('§3.112b 三重守卫：①distinct 交易日数 ≥ 20；②起点错位 ≤ 5 日历日；'
                    '③日历跨度 ≤ 2.2n+3。未通过者计入 window_sparse_tracks，其多日窗口读数'
                    '须随 n 一并披露、不得作方向判断。'),
    'session_added': len(added),
    'session_backfilled_total': backfilled,
    'session_backfill_detail': {'by_event_date': dict(by_evdate), 'by_track': dict(by_track_bf),
                                'by_actual_date': dict(by_adate)},
    'blank_by_date_final': dict(sorted(blank_by_date.items())),
    'blank_by_track_final': dict(sorted(blank_by_track.items())),
    'rerun_note': ('本脚本可重入：二次执行时 events_added/events_backfilled 会归零，'
                   '当档真实增量以 session_added / session_backfilled_total 为准（§3.112c）。'),
    'direction_check': {'day': DIR_DAY, 'hit': hit, 'total': tot, 'all_today': all_tot,
                        'by_dir': {k: {'hit': v[0], 'total': v[1]} for k, v in by_dir.items()},
                        'note': (f'参考日 = {DIR_DAY}（A股/港股/美股 三市场均有真实收盘）；'
                                 '口径 = actual_date 严格等于参考日（§3.115b 显式过滤）')},
    'exposure_weighted_net_sentiment': round(expo_weighted, 3),
    'track_net_sentiment': {k: round(v, 4) for k, v in net.items()},
    'exposure_weights': EXPO,
    'exposure_weights_source': FIXNAME + ' → tracks[].mv（§3.144a）',
    'track_index_map': track_index,
    'ref_index_map': REF_INDEX,
    'note': ('A股医药 3/5/10 日窗口序列实际使用 399006（创业板指）代理（§3.90），1 日窗口用 000933；'
             f'10/20 为**档型③「正常交易日盘前」**（A股 + 港股复市 + 美股 均正常交易日）→ '
             '**`close` 与 `pending` 均不产**，待消化沿用 10/19 收盘修正件；'
             f'暴露权重取 10/19 修正件 tracks[].mv（§3.144a），Σ dev {_dev:.2f} 元；'
             '情绪标注为**规则表模式**（DeepSeek 端点 HTTP 402，连续第 15 个日历日，§3.127b），'
             '跨档比较均值强度时须注意口径差异。'),
}

# §3.112c 自证：可重入脚本二次执行会把增量归零 → 保留「首执行真实增量」
SP = os.path.join(HIST, f'event_stats_{TODAY.replace("-", "")}_preopen.json')
if os.path.exists(SP):
    try:
        prev = json.load(open(SP, encoding='utf-8'))
        for k in ('session_added', 'session_backfilled_total'):
            if (prev.get(k) or 0) > (out.get(k) or 0):
                out[k] = prev[k]
        if prev.get('session_backfill_detail'):
            out['session_backfill_detail'] = prev['session_backfill_detail']
        out['rerun_note'] = ('二次执行：本档增量已归零，session_* 字段取自首执行快照（§3.112c）')
    except Exception as e:
        print('prev merge skip', e)

json.dump(out, open(SP, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('\nwritten', SP)
