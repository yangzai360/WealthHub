"""2026-10-08（周四 · **档型③：双市场复市首日盘前**）事件库处理：
  A股 长假后复市首日（10/8 09:30 开盘）+ 港股 10/8 正常交易日；08:00 双方均无当日价格
  → 按 §3.109/§3.110 档型③ → **不产 `portfolio_close_*` 与 `portfolio_pending_*`**（本脚本只处理事件库）。

  ① 回填：按「参考指数在事件日（或之后）已有真实收盘 → 回填」通用规则逐条判空
     - **本档为长假后首个「美股/港股均有新增真实收盘」的回填档**：
       可回填的最近真实收盘 = **XLV 的 2026-10-07（168.81 / +1.0294%）**。
       构成（**全部为美股标普医药类，actual_date 全部 = 2026-10-07**）：
         ① 10/7 档新增的**美股标普医药 11 条**（5 条盘前窗口 + 4 条盘中窗口 + 2 条盘后窗口）——
            10/7 08:00 时美东 10/7 尚未开盘 → 留空；本档回填。
       ⚠️ **恒生科技「盘后窗口」事件（10/7 档 4 条）本档仍「不作回填」**（§3.127a）：
          盘后窗口 14:00-20:00 晚于港股 16:00 收盘 → 参考交易日顺延至**事件日之后**首个港股交易日（10/9），
          本档 08:00 尚未发生 → 留空，已写 `reference.backfill_deferred_reason` 自证。
       ⚠️ **A股类（宏观/A股医药/大消费/其他·宽基）全部仍留空**：参考交易日 = 2026-10-08（今日），
          08:00 A股 未开盘 → 属预期状态（§3.119c / §3.119e），本档 20:00 盘后档回填。
  ② 追加本档 25 条盘前事件（window == '盘前(10/7 20:00-10/8 07:30)'，含空集硬守卫）
  ③ 全库完整性扫描（留空按「日期×赛道」二维落库，§3.98）
  ④ 1 日样本 + 3/5/10 日窗口统计 → history/event_stats_20261008_preopen.json
⚠️ 参考日口径：**「下一个交易日」= 该事件参考指数的下一个交易日**（§3.119c），不是「下一个 A股 交易日」。
   宏观 = 000001。A股医药 3/5/10 日窗口代理 = 399006（创业板指，§3.90），1 日窗口 = 000933。
   本档全部赛道参考交易日 = 2026-10-08（A股/港股今日开盘、美东 10/8 收盘成型于北京 10/9 04:00）。
⚠️ 方向验证分母：actual_date == 2026-10-07 的成功回填事件（§3.102/§3.115b 有效样本口径）。
   本档样本覆盖「恒生科技（10/7 已回填）+ 美股标普医药（本档回填）」两类。
⚠️ §3.114a：枚举型字段 track 写入前做全等校验（硬守卫）。
⚠️ §3.113e / §3.121c：本脚本由 events_preopen_20261007.py 直接改写派生，
   已人工核对「读写路径 / 日期常量 / docstring 档型语义 / 产物 note 自然语言字段」四类字面量。
"""
import json, os, glob, csv, datetime
from collections import defaultdict

BASE = '/Users/jieyang/Documents/WealthHub'
EV = os.path.join(BASE, 'data/processed/events')
HIST = os.path.join(BASE, 'data/processed/history')
TODAY = '2026-10-08'
WIN = '盘前(10/7 20:00-10/8 07:30)'
REF_INDEX = {'宏观': '000001', 'A股医药': '000933', '大消费': '000932', '恒生科技': 'HSTECH',
             '美股标普医药': 'XLV', '其他/宽基': '000300'}
DIR_DAY = '2026-10-07'
REF_TD = '2026-10-08'
REF_BY_TRACK = {'宏观': '2026-10-08', 'A股医药': '2026-10-08', '大消费': '2026-10-08',
                '恒生科技': '2026-10-08', '美股标普医药': '2026-10-08', '其他/宽基': '2026-10-08'}

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
    `strictly_after=True` 用于「盘后窗口采集」的事件 → 参考日 = 事件日**之后**的首个交易日。"""
    ser = idx.get(code)
    if not ser:
        return None, None
    ds = sorted(ser)
    for i, d in enumerate(ds):
        ok = (d > event_date) if strictly_after else (d >= event_date)
        if ok and i > 0:
            return d, round((ser[d] / ser[ds[i - 1]] - 1) * 100, 4)
    return None, None


# ---------- §3.127a：盘后窗口（14:00-20:00）采集事件的「严格顺延」判据 ----------
AFTER_CLOSE_WINDOW = '盘后(14:00-20:00)'
# 北京时间收盘时刻：A股 15:00 / 港股 16:00（均早于盘后窗口结束 20:00）→ 必须顺延到下一交易日；
# 美股当日收盘成型于北京时间次日 04:00（晚于窗口结束）→ **不顺延**，当日收盘即可作参考日。
NON_US_TRACKS = {'宏观', 'A股医药', '大消费', '恒生科技', '其他/宽基'}


def needs_defer(e):
    """§3.127a 判据：先定市场、再定是否顺延（与 §3.119c「逐市场分列」正交）。"""
    return (e.get('window') == AFTER_CLOSE_WINDOW) and (e.get('track') in NON_US_TRACKS)


# ---------- ① 回填 ----------
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
                    '§3.127a：本事件采集窗口为盘后(14:00-20:00)，已晚于该市场当日收盘'
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
print(f'  §3.127a 盘后窗口顺延标记（backfill_deferred_reason）累计: {_defer_marks} 条')

# ---------- ② 追加本档事件 ----------
news = json.load(open(os.path.join(BASE, f'data/processed/news/news-{TODAY}.json'), encoding='utf-8'))
sent = json.load(open(os.path.join(BASE, f'data/processed/news/sentiment-{TODAY}.json'), encoding='utf-8'))
ev_path = os.path.join(EV, f'events-{TODAY}.json')
ev = json.load(open(ev_path, encoding='utf-8')) if os.path.exists(ev_path) else []
existing = {e['title'][:60] for e in ev}

win_sent = [x for x in sent['items'] if x.get('window') == WIN]
if not win_sent:
    raise SystemExit('⚠️ 盘前窗口 sentiment 为 0 条 → per-item `window` 字段可能缺失（§3.88/§3.103），终止')
added = []
for x in win_sent:
    n = next((y for y in news if y['title'][:60] == x['title']), None)
    if n is None or n['title'][:60] in existing:
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
                      'ret_1d_ref': (f'盘前档（{TODAY} 08:00，双市场复市首日尚未开盘）；逐市场参考交易日 = '
                                     f'{REF_BY_TRACK.get(n["track"])}，待该日收盘回填')},
    })
# §3.114a 枚举值全等校验（硬守卫）：非法 track 会静默跳过回填与加权
VALID_TRACK = {'宏观', 'A股医药', '大消费', '恒生科技', '美股标普医药', '其他/宽基'}
_bad = {x['track'] for x in added} - VALID_TRACK
if _bad:
    raise SystemExit(f'⚠️ 非法 track 值 {_bad} → 会静默跳过回填与加权，终止（§3.114a）')
_badall = {e['track'] for e in ev} - VALID_TRACK
if _badall:
    raise SystemExit(f'⚠️ 库内非法 track 值 {_badall}，终止（§3.114a）')

ev.extend(added)
json.dump(ev, open(ev_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(f'事件库 {TODAY} +{len(added)} 条 → 当日 {len(ev)} 条')

# ---------- ③ 完整性扫描 ----------
files = sorted(glob.glob(os.path.join(EV, 'events-*.json')))
all_ev, dup = [], {}
for f in files:
    for e in json.load(open(f, encoding='utf-8')):
        all_ev.append(e)
        dup[e['title'][:60]] = dup.get(e['title'][:60], 0) + 1
n_blank = sum(1 for e in all_ev if e.get('reference', {}).get('actual_ret_1d') is None)
blank_by_date, blank_by_track = defaultdict(int), defaultdict(int)
for e in all_ev:
    if e.get('reference', {}).get('actual_ret_1d') is None:
        blank_by_date[e['date']] += 1
        blank_by_track[e['track']] += 1
no_adate = sum(1 for e in all_ev if e.get('reference', {}).get('actual_ret_1d') is not None
               and not e.get('reference', {}).get('actual_date'))
print(f'\n全库 {len(all_ev)} 条 / {len(files)} 日；留空(actual_ret_1d is None) {n_blank} 条')
print(f'  留空按日: {dict(sorted(blank_by_date.items()))}')
print(f'  留空按赛道: {dict(sorted(blank_by_track.items()))}')
print(f'  ⚠️ legacy 字段不全（有 actual_ret_1d 但缺 actual_date）: {no_adate} 条（不计入留空，见 §3.106）')
print(f'  跨日重复标题 {sum(1 for v in dup.values() if v > 1)} 组')
today_all = sum(1 for e in all_ev if e['date'] == TODAY)
blank_pairs = defaultdict(int)
for e in all_ev:
    if e.get('reference', {}).get('actual_ret_1d') is None:
        blank_pairs[(e['date'], e['track'])] += 1
print(f'  【留空构成】当日({TODAY})新增 {today_all} 条；全库留空分布（事件日×赛道）:')
for (d0, t0), c in sorted(blank_pairs.items()):
    print(f'    {d0} {t0}: {c} 条  (参考交易日 = {REF_BY_TRACK.get(t0, REF_TD)}，待回填)')

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
    r = e.get('reference', {})
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

# ---------- ④b §3.112b 稀疏序列三重守卫（distinct 交易日数 + 起点错位 + 日历跨度） ----------
MIN_DAYS = 20
sparse = {}
for t, code in track_index.items():
    ser = idx.get(code) or {}
    ds = sorted(ser)
    n_days = len(ds)
    first_obs = ds[0] if ds else None
    span = None
    if first_obs and ds:
        span = (datetime.date.fromisoformat(ds[-1]) - datetime.date.fromisoformat(first_obs)).days
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
print(f'\n§3.112b 稀疏代理指数守卫（MIN_DAYS={MIN_DAYS}；跨度上限按「观测日数」而非窗口长度）: '
      + (str(sparse) if sparse else '全部通过'))
for t, code in track_index.items():
    ser = idx.get(code) or {}
    ds = sorted(ser)
    span = (datetime.date.fromisoformat(ds[-1]) - datetime.date.fromisoformat(ds[0])).days if ds else None
    lim = 2.2 * len(ds) + 3
    print(f'  {t:8s} proxy={code:8s} distinct_days={len(ds):4d} span={span}d lim={lim:.1f} '
          f'{"✅" if span is not None and span <= lim else "⚠️稀疏"}')

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

# 方向验证（有效样本口径，§3.102/§3.104/§3.115b）
hit, tot, all_tot = 0, 0, 0
by_dir = defaultdict(lambda: [0, 0])
for e in all_ev:
    r0 = e.get('reference', {})
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
EXPO = {'大消费': 19.87, 'A股医药': 23.57, '美股标普医药': 15.66, '恒生科技': 8.29, '其他/宽基': 24.94}
net = defaultdict(float)
for x in sent_all['items']:
    if x.get('window') != WIN:
        continue
    sg = 1 if x['direction'] == '利多' else (-1 if x['direction'] == '利空' else 0)
    net[x['track']] += sg * x['strength'] / 100
print('\n赛道净情绪分（Σ方向×强度/100）与暴露加权（10/8 盘前权重，A股/港股未开盘 → 与 9/30 后一致）:')
expo_weighted = 0.0
for t in EXPO:
    print(f"  {t:8s} 净分={net[t]:+.2f}  暴露={EXPO[t]:.2f}%")
    expo_weighted += net[t] * EXPO[t] / 100
print(f'  → **暴露加权净情绪分 = {expo_weighted:+.4f}**')

out = {
    'date': TODAY, 'window': 'preopen', 'total_events': len(all_ev), 'today_events': len(ev), 'blank': n_blank,
    'blank_by_date': dict(sorted(blank_by_date.items())),
    'blank_by_track': dict(sorted(blank_by_track.items())),
    'reference_trading_day': REF_TD,
    'reference_trading_day_by_track': REF_BY_TRACK,
    'legacy_missing_actual_date': no_adate,
    'backfilled': backfilled, 'backfill_by_event_date': dict(by_evdate),
    'after_close_deferred_rule': ('§3.127a：window == 盘后(14:00-20:00) 且 track ∈ {宏观, A股医药, 大消费, '
                                  '恒生科技, 其他/宽基} 的事件，参考交易日 = 事件日**之后**的首个交易日 '
                                  '（strictly_after=True）；美股标普医药不顺延（其当日收盘成型于北京次日 04:00，'
                                  '晚于采集窗口）。'),
    'after_close_deferred_marked': _defer_marks,
    'backfill_by_track': dict(by_track_bf), 'backfill_by_actual_date': dict(by_adate),
    'backfill_note': (f'本档实际回填 {backfilled} 条（长假后首个「美股恢复收盘」的回填档）；'
                      '可回填的最近真实收盘 = XLV 2026-10-07（168.81 / +1.0294%）'
                      '（美东 10/7 收盘成型于北京 10/8 04:00，已早于本档 08:00）。'
                      f'**全部 {backfilled} 条赛道分布 = {dict(by_track_bf)}、'
                      f'actual_date 分布 = {dict(by_adate)}**，'
                      f'构成 = 事件日 {dict(by_evdate)} 档新增的美股标普医药留空事件（5 盘前 + 4 盘中 + 2 盘后）。'
                      '⚠️ **恒生科技类「盘后窗口」事件（10/7 档 4 条）本档不作回填**'
                      '（§3.127a：盘后窗口晚于港股 16:00 收盘 → 参考日顺延至事件日之后首个港股交易日 10/9）。'
                      f'**A股类（参考日 2026-10-08）本档 08:00 尚未开盘 → 仍全部留空，属预期状态**'
                      '（§3.119c / §3.119e），本档 20:00 盘后档回填。'
                      f'本档新增 {today_all} 条（2026-10-08）参考交易日（逐市场分列，§3.119c）：'
                      'A股类 = 2026-10-08（今日复市首日）；恒生科技 = 2026-10-08（港股今日正常交易日）；'
                      '美股标普医药 = 2026-10-08（美东 10/8 收盘成型于北京 10/9 04:00）。'),
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
                        'note': (f'本档该口径覆盖「恒生科技（10/7 已回填 −0.677%）+ 美股标普医药'
                                 f'（本档回填 +1.0294%）」两类（参考日 {DIR_DAY}）')},
    'exposure_weighted_net_sentiment': round(expo_weighted, 3),
    'track_net_sentiment': {k: round(v, 4) for k, v in net.items()},
    'track_index_map': track_index,
    'ref_index_map': REF_INDEX,
    'note': ('A股医药 3/5/10 日窗口序列实际使用 399006（创业板指）代理（§3.90），1 日窗口用 000933；'
             f'本档新增 {today_all} 条参考交易日**六赛道全部 = 2026-10-08**（A股/港股今日开盘、'
             '美东 10/8 收盘成型于北京 10/9 04:00）→ 本档 08:00 全部留空属预期状态（§3.119c）；'
             '10/8 为**档型③「双市场复市首日盘前」**（§3.109/§3.110）→ '
             '**本档不产 portfolio_close_* 与 portfolio_pending_***，产物为 '
             'portfolio_preopen_20261008.json（state=preopen_estimate / finalized=false）；'
             '全库另有 legacy 事件缺 actual_date 字段但 actual_ret_1d 已有值（不计入留空，§3.106）'),
}

# §3.112c 自证：可重入脚本二次执行会把增量归零 → 与既有产物取 max 保留「首执行真实增量」
SP = os.path.join(HIST, f'event_stats_{TODAY.replace("-", "")}_preopen.json')
if os.path.exists(SP):
    try:
        prev = json.load(open(SP, encoding='utf-8'))
        for k in ('session_added', 'session_backfilled_total'):
            if (prev.get(k) or 0) > (out.get(k) or 0):
                out[k] = prev[k]
        if out.get('session_added'):
            out['rerun_note'] += (f" 本文件为可重入脚本二次执行后回写，session_added={out['session_added']}"
                                  ' 为首次执行的真实增量。')
        if (prev.get('session_backfill_detail') or {}).get('by_event_date') \
                and not out['session_backfill_detail']['by_event_date']:
            out['session_backfill_detail'] = prev['session_backfill_detail']
    except Exception as e:
        print('  WARN 读取既有 event_stats 失败:', e)
json.dump(out, open(os.path.join(HIST, f'event_stats_{TODAY.replace("-", "")}_preopen.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
print(f"\n已保存 event_stats_{TODAY.replace('-', '')}_preopen.json")
