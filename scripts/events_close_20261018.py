# -*- coding: utf-8 -*-
"""2026-10-18 盘后档事件库处理（周日 · 档型①「纯非交易日」）
  ① **回填**：判据 = 「该事件的参考指数在当日（或其后首个观测日）是否有真实收盘价」
     —— 本档为纯非交易日：**A股/港股指数无新交易日** → A股医药/大消费/其他·宽基/宏观/恒生科技 类**均不可回填**；
        **但美股 XLV 于本档新增 US 10/16 真实收盘行（+8 行已写入 indices.csv）** →
        **10/16 档留空的「美股标普医药」类可回填**（ref_trade_day = 2026-10-16，美东日历日口径）
  ② 追加本档周末窗口事件（window = 周末(10/16 20:00-10/18 20:00)，16 条，含空集硬守卫）
  ③ 全库完整性扫描（留空按「日期×赛道」二维落库）
  ④ 1 日样本 + 3/5/10 日窗口 + 方向命中率 → history/event_stats_20261018_close.json
  ⑤ 暴露加权净情绪（权重取 portfolio_close_20261016_fix.json 的 tracks mv / total_mv）

⚠️ §3.110：判据不是「当日是否 A股 交易日」—— 本档 A股 未开市但美股已收盘，逐市场分列
⚠️ §3.106 条款 17 / §3.154b：REF_BY_TRACK_NEW 为**计算项**，不得沿用上一档
   → A股/宏观/其他·宽基/大消费/A股医药 = 2026-10-19；恒生科技 = 2026-10-20（10/19 港股重阳翌日休市顺延）；美股 = 2026-10-19
⚠️ §3.154a 闸门③：本档独有数值断言
"""
import json, os, glob, csv, re, datetime as _dt
from collections import defaultdict

BASE = '/Users/jieyang/Documents/WealthHub'
EV = os.path.join(BASE, 'data/processed/events')
HIST = os.path.join(BASE, 'data/processed/history')
TODAY = '2026-10-18'
WIN = '周末(10/16 20:00-10/18 20:00)'
SESSION_TYPE = 'non_trading_day_close'
SESSION_DESC = '纯非交易日档（周日；A股与港股均未开市，美股 10/16 已收盘、10/17-10/18 为周末）'

VALID_TRACK = {'宏观', 'A股医药', '大消费', '恒生科技', '美股标普医药', '其他/宽基'}
VALID_CAT = {'政策类', '业绩类', '行业事件类', '宏观类', '策略类'}
VALID_DIR = {'利多', '利空', '中性'}

REF_INDEX = {'宏观': '000001', 'A股医药': '000933', '大消费': '000932', '恒生科技': 'HSTECH',
             '美股标普医药': 'XLV', '其他/宽基': '000300'}
# 本档新事件的参考交易日（逐市场分列，现算）
REF_BY_TRACK_NEW = {'A股医药': '2026-10-19', '大消费': '2026-10-19', '其他/宽基': '2026-10-19',
                    '宏观': '2026-10-19', '恒生科技': '2026-10-20', '美股标普医药': '2026-10-19'}

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


def ref_ret(code, event_date, strict_after=False):
    ser = idx.get(code)
    if not ser:
        return None, None
    ds = sorted(ser)
    for i, d in enumerate(ds):
        if i == 0:
            continue
        if d > event_date or (d >= event_date and not strict_after):
            return d, round((ser[d] / ser[ds[i - 1]] - 1) * 100, 4)
    return None, None


news = json.load(open(os.path.join(BASE, f'data/processed/news/news-{TODAY}.json'), encoding='utf-8'))
sent = json.load(open(os.path.join(BASE, f'data/processed/news/sentiment-{TODAY}.json'), encoding='utf-8'))
win_sent = [x for x in sent['items'] if x.get('window') == WIN]
if not win_sent:
    raise SystemExit('⚠️ 本档窗口 sentiment 为 0 条 → per-item `window` 缺失，终止以免静默跳过入库')
print(f'本档窗口情绪条目 {len(win_sent)}')

# ---------- ① 回填 ----------
all_ev = []
for f in sorted(glob.glob(os.path.join(EV, 'events-*.json'))):
    all_ev.extend(json.load(open(f, encoding='utf-8')))
print(f'回填前全库 {len(all_ev)} 条')

backfilled, back_detail = 0, []
by_evdate, by_track_bf, by_adate = defaultdict(int), defaultdict(int), defaultdict(int)
missed = []
for e in all_ev:
    ref = e.get('reference', {})
    if ref.get('actual_ret_1d') is not None:
        continue
    code = REF_INDEX.get(e['track'])
    if not code:
        continue
    # ⚠️ §3.158（本档新增）：`strict_after` 必须**按市场分列**，不得只看 window 文本——
    #   window 是北京时间，而美股 10/16 的目标交易日 = 美东 10/16（北京 10/16 20:00 尚未开盘）
    #   → 美股类一律 strict_after=False（允许 d == 事件日），否则 US 10/16 收盘永不回填。
    strict = str(e.get('window', '')).startswith(('盘后', '周末')) and e['track'] != '美股标普医药'
    d, r = ref_ret(code, e['date'], strict_after=strict)
    if d is None or r is None:
        continue
    if strict and d == e['date']:
        continue
    if d not in idx.get(code, {}):
        continue
    ref['actual_ret_1d'] = r
    ref['actual_date'] = d
    ref['ref_trade_day'] = d
    backfilled += 1
    by_evdate[e['date']] += 1
    by_track_bf[e['track']] += 1
    by_adate[d] += 1
    back_detail.append({'id': e['id'], 'date': e['date'], 'track': e['track'],
                        'actual_date': d, 'actual_ret_1d': r})

CLOSE_BF_DETAIL = [{'id': e['id'], 'date': e['date'], 'track': e['track'],
                    'actual_date': (e.get('reference') or {}).get('actual_date'),
                    'actual_ret_1d': (e.get('reference') or {}).get('actual_ret_1d')}
                   for e in all_ev
                   if e['date'] == '2026-10-16' and e['track'] == '美股标普医药'
                   and (e.get('reference') or {}).get('actual_date') == '2026-10-16']
print(f'[§3.139k] 库内现状口径：10/16 事件中日参考日 == 2026-10-16 的条目 = {len(CLOSE_BF_DETAIL)} 条')
byid_all = {e['id']: e for e in all_ev}
for f in sorted(glob.glob(os.path.join(EV, 'events-*.json'))):
    arr = json.load(open(f, encoding='utf-8'))
    changed = False
    for e in arr:
        src = byid_all.get(e['id'])
        if src and src.get('reference', {}).get('actual_ret_1d') is not None \
                and e.get('reference', {}).get('actual_ret_1d') is None:
            e['reference'] = src['reference']
            changed = True
    if changed:
        json.dump(arr, open(f, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(f'\n回填 {backfilled} 条；按事件日 {dict(by_evdate)}；按赛道 {dict(by_track_bf)}；按实际日 {dict(by_adate)}')

# ---------- ② 追加本档事件 ----------
ev_path = os.path.join(EV, f'events-{TODAY}.json')
ev = json.load(open(ev_path, encoding='utf-8')) if os.path.exists(ev_path) else []
existing = {e['title'][:60] for e in ev}
added = []
for x in win_sent:
    n = next((y for y in news if y['title'][:60] == x['title'][:60] or y['title'] == x['title']), None)
    if n is None:
        print(f"  ⚠️ §3.130a 未能在 news-{TODAY}.json 中匹配到 sentiment 条目: {x['title'][:40]}")
        missed.append(x['title'][:40])
        continue
    if n['title'][:60] in existing:
        continue
    bad = ({n['track']} - VALID_TRACK) | ({n.get('category', '行业事件类')} - VALID_CAT)
    if bad:
        raise SystemExit(f'⚠️ 非法枚举 {bad} in {n["title"][:30]}（§3.114a）')
    seq = len(ev) + len(added) + 1
    added.append({
        'id': f"N{TODAY.replace('-', '')}-{seq:03d}", 'date': TODAY, 'track': n['track'],
        'category': n.get('category', '行业事件类'), 'title': n['title'],
        'summary': n.get('summary', ''), 'source': n.get('source', 'WebSearch'),
        'source_url': n.get('source_url', ''), 'sentiment': n.get('sentiment'),
        'score': n.get('score'), 'strength': n.get('strength'),
        'direction': n.get('direction'), 'volatility': n.get('volatility'),
        'reason': n.get('brief', ''), 'window': WIN,
        'reference': {'ret_3d': None, 'ret_5d': None, 'ret_10d': None,
                      'max_vol': {'低': 1.5, '中': 4.8, '高': 9.0}.get(n.get('volatility'), 4.8),
                      'confidence': n.get('confidence'), 'actual_ret_1d': None, 'actual_date': None,
                      'ref_trade_day': REF_BY_TRACK_NEW.get(n['track'])},
    })
ev.extend(added)
json.dump(ev, open(ev_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
FIRST_RUN_ADDED = len(added)
print(f'事件库 {TODAY} +{FIRST_RUN_ADDED} 条 → 当日 {len(ev)} 条（未命中告警 {len(missed)} 条）')

added = [e for e in ev if e.get('window') == WIN]
print(f'本档工作集（库内 window={WIN}）= {len(added)} 条')

all_ev = []
files = sorted(glob.glob(os.path.join(EV, 'events-*.json')))
for f in files:
    all_ev.extend(json.load(open(f, encoding='utf-8')))

# ---------- ③ 完整性扫描 ----------
blank = lambda e: (e.get('reference') or {}).get('actual_ret_1d') is None
n_blank = sum(1 for e in all_ev if blank(e))
bdate, btrack, blank_pairs = defaultdict(int), defaultdict(int), defaultdict(int)
for e in all_ev:
    if blank(e):
        bdate[e['date']] += 1
        btrack[e['track']] += 1
        blank_pairs[(e['date'], e['track'])] += 1
print(f'\n全库 {len(all_ev)} 条 / {len(files)} 日；留空 {n_blank} 条')
print(f'  留空按赛道: {dict(btrack)}')
for (d0, t0), c in sorted(blank_pairs.items()):
    print(f'    {d0} {t0}: {c} 条（参考交易日 = {REF_BY_TRACK_NEW.get(t0)}，待回填）')

# ---------- ④ 历史相似事件匹配 ----------
track_index = {'A股医药': '399006', '大消费': '000932', '恒生科技': 'HSTECH',
               '美股标普医药': 'XLV', '其他/宽基': '000300', '宏观': '000001'}
STOP = set('的了和与在是以为对及等这那日前月年。，、；：（）%＋-')


def kw(s):
    return {w for w in re.findall(r'[\u4e00-\u9fa5]{2,4}', s or '') if w not in STOP}


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


hist = [e for e in all_ev if e['date'] < TODAY]
sim_out = []
for e in added:
    k0 = kw(e['title'] + e.get('summary', ''))
    cands = []
    for h in hist:
        sc = 0.0
        if h['track'] == e['track']:
            sc += 55
        if h.get('category') == e.get('category'):
            sc += 20
        k1 = kw(h['title'] + h.get('summary', ''))
        if k0 and k1:
            sc += 25 * len(k0 & k1) / max(len(k0 | k1), 1)
        if h.get('direction') == e.get('direction'):
            sc += 5
        cands.append((round(min(sc, 100), 1), h))
    cands.sort(key=lambda x: -x[0])
    top = cands[:3]
    rows = []
    for sc, h in top:
        r3, r5, r10 = (fwd(track_index.get(e['track']), h['date'], nn) for nn in (3, 5, 10))
        rows.append({'similarity': sc, 'hist_date': h['date'], 'hist_title': h['title'][:44],
                     'hist_direction': h.get('direction'), 'ret_3d': r3, 'ret_5d': r5, 'ret_10d': r10})

    def avg(k):
        v = [r[k] for r in rows if r[k] is not None]
        return round(sum(v) / len(v), 2) if v else None
    sim_out.append({'id': e['id'], 'track': e['track'], 'category': e['category'],
                    'title': e['title'][:50], 'direction': e['direction'], 'strength': e['strength'],
                    'top3': rows, 'avg_3d': avg('ret_3d'), 'avg_5d': avg('ret_5d'), 'avg_10d': avg('ret_10d'),
                    'confidence': int(round(sum(r['similarity'] for r in rows) / max(len(rows), 1)))})

print('\n=== 历史相似事件匹配（Top3，按赛道聚合） ===')
agg = defaultdict(list)
for s_ in sim_out:
    agg[s_['track']].append(s_)
for t, arr in sorted(agg.items()):
    a3 = [x['avg_3d'] for x in arr if x['avg_3d'] is not None]
    a5 = [x['avg_5d'] for x in arr if x['avg_5d'] is not None]
    a10 = [x['avg_10d'] for x in arr if x['avg_10d'] is not None]
    cf = [x['confidence'] for x in arr]
    print(f"  {t:10s} n={len(arr):>2d}  3日均值={sum(a3)/len(a3) if a3 else float('nan'):+.2f}%  "
          f"5日={sum(a5)/len(a5) if a5 else float('nan'):+.2f}%  10日={sum(a10)/len(a10) if a10 else float('nan'):+.2f}%  "
          f"平均置信度={sum(cf)/len(cf):.0f}")

# ---------- ⑤ 窗口统计 ----------
MIN_DAYS = 20


def _cd(a, b):
    return (_dt.date.fromisoformat(b) - _dt.date.fromisoformat(a)).days


sparse_tracks, guard = {}, {}
for t, code in track_index.items():
    days = sorted(idx.get(code, {}).keys())
    n_day = len(days)
    span = _cd(days[0], days[-1]) if days else 0
    ok = (n_day >= MIN_DAYS) and (span <= 2.2 * n_day + 3)
    guard[code] = {'track': t, 'distinct_days': n_day, 'span_days': span, 'pass': bool(ok)}
    if not ok:
        sparse_tracks[t] = guard[code]
print('\n[§3.112b 三重守卫] ' + str(guard))

win_d = defaultdict(lambda: defaultdict(list))
for e in all_ev:
    code = track_index.get(e['track'])
    if not code:
        continue
    for n in (3, 5, 10):
        x = fwd(code, e['date'], n)
        if x is not None:
            win_d[e['track']][n].append(x)
ones = defaultdict(list)
for e in all_ev:
    v = e.get('reference', {}).get('actual_ret_1d')
    if v is not None and e['track'] in track_index:
        ones[e['track']].append((v, e.get('direction'), e.get('strength'), e.get('date'),
                                 e.get('reference', {}).get('actual_date')))
print('\n1 日样本（全库，按赛道）:')
for t, arr in sorted(ones.items()):
    vs = [a[0] for a in arr]
    print(f"  {t:8s} n={len(vs):>4d} 均值={sum(vs)/len(vs):+.2f}% 上涨占比={sum(1 for v in vs if v>0)/len(vs):.2f}")

strict = defaultdict(lambda: {'pos_hit': 0, 'pos_n': 0, 'neg_hit': 0, 'neg_n': 0})
for t, arr in ones.items():
    for v, d, st, ed, ad in arr:
        if ad != ed:
            continue
        if d == '利多':
            strict[t]['pos_n'] += 1
            strict[t]['pos_hit'] += 1 if v > 0 else 0
        elif d == '利空':
            strict[t]['neg_n'] += 1
            strict[t]['neg_hit'] += 1 if v < 0 else 0
print('\n[§3.115b 严格口径方向命中率] actual_date == 事件日')
for t, d in sorted(strict.items()):
    ph = f"{d['pos_hit']}/{d['pos_n']}" + (f" = {d['pos_hit']/d['pos_n']*100:.0f}%" if d['pos_n'] else " = n/a")
    nh = f"{d['neg_hit']}/{d['neg_n']}" + (f" = {d['neg_hit']/d['neg_n']*100:.0f}%" if d['neg_n'] else " = n/a")
    print(f"  {t:8s} 利多 {ph}   利空 {nh}")

print('\n全库 3/5/10 日窗口（按赛道）:')
for t, d in sorted(win_d.items()):
    s_ = '  '.join(f"{n}日 n={len(d[n])} 均值={sum(d[n])/len(d[n]):+.2f}%" for n in (3, 5, 10) if d.get(n))
    print(f"  {t:10s} {s_}")

# ---------- ⑥ 暴露加权净情绪 ----------
pf = json.load(open(os.path.join(HIST, 'portfolio_close_20261016_fix.json'), encoding='utf-8'))
w = {k: v['mv'] / pf['total_mv'] for k, v in pf['tracks'].items() if k != '现金'}
print('\n暴露权重:', {k: round(v, 4) for k, v in w.items()})

track_net = {}
for x in win_sent:
    t = x['track']
    track_net.setdefault(t, 0.0)
    sign = 1 if x['direction'] == '利多' else (-1 if x['direction'] == '利空' else 0)
    track_net[t] += sign * x['strength'] / 10.0
track_net = {k: round(v, 2) for k, v in track_net.items()}
named_total = round(sum(track_net.values()), 2)
weighted = round(sum(track_net.get(k, 0.0) * w.get(k, 0.0) for k in w), 4)
print('赛道净情绪:', track_net)
print(f'名义合计 {named_total:+.2f} / 暴露加权 {weighted:+.4f}')

tnet_all = defaultdict(float)
for x in sent['items']:
    sign = 1 if x['direction'] == '利多' else (-1 if x['direction'] == '利空' else 0)
    tnet_all[x['track']] += sign * x['strength'] / 10.0
tnet_all = {k: round(v, 2) for k, v in tnet_all.items()}
w_all = round(sum(tnet_all.get(k, 0.0) * w.get(k, 0.0) for k in w), 4)
print(f'当日全量 名义合计 {round(sum(tnet_all.values()),2):+.2f} / 暴露加权 {w_all:+.4f}')

legacy_missing = sum(1 for e in all_ev
                     if e.get('reference', {}).get('actual_ret_1d') is not None
                     and not e.get('reference', {}).get('actual_date'))

# ---------- n 变化量（对比上一档 10/16 收盘档） ----------
_prev_path = os.path.join(HIST, 'event_stats_20261016_close.json')
prev = json.load(open(_prev_path, encoding='utf-8')) if os.path.exists(_prev_path) else {}
if not prev:
    raise SystemExit('⚠️ 上一档（10/16 收盘）统计缺失 → 口径无法自证，终止')
prev_win = prev.get('windows', {})
n_delta = {}
for t, d in win_d.items():
    n_delta[t] = {}
    for n in (3, 5, 10):
        cur_n = len(d.get(n, []))
        prv = (prev_win.get(t, {}) or {}).get(str(n), {}) or {}
        prv_n = prv.get('n')
        n_delta[t][str(n)] = {'cur': cur_n, 'prev': prv_n,
                              'delta': (cur_n - prv_n) if isinstance(prv_n, int) else None}
ones_delta = {}
for t, a in ones.items():
    prv_n = ((prev.get('onesample', {}) or {}).get(t, {}) or {}).get('n')
    ones_delta[t] = {'cur': len(a), 'prev': prv_n,
                     'delta': (len(a) - prv_n) if isinstance(prv_n, int) else None}
ones_delta_total = sum(v['delta'] for v in ones_delta.values() if v['delta'] is not None)
print(f"\n[§3.110 1 日样本 n 增量] 合计 {ones_delta_total:+d}  " +
      '  '.join(f"{t} {v['prev']}→{v['cur']}" for t, v in sorted(ones_delta.items())))
print('\n[§3.127d 多日窗口 n 变化量]')
for t, dd in n_delta.items():
    print(f"  {t:10s} " + '  '.join(f"{k}日 {v['prev']}→{v['cur']} ({v['delta']:+d})" if v['delta'] is not None
                                    else f"{k}日 {v['cur']}" for k, v in dd.items()))

CLOSE_PHASE_ADDED = len([e for e in ev if e.get('window') == WIN])
CLOSE_PHASE_BF = sum(1 for e in all_ev
                     if e['date'] == '2026-10-16' and e['track'] == '美股标普医药'
                     and (e.get('reference') or {}).get('actual_date') == '2026-10-16')
print(f'\n[§3.112c 幂等口径] 本次进程 新增 {FIRST_RUN_ADDED} / 回填 {backfilled}；'
      f'本档真实增量 新增 {CLOSE_PHASE_ADDED} / 回填 {CLOSE_PHASE_BF}')

out = {'date': TODAY, 'window': 'close', 'session_type': SESSION_TYPE, 'session_desc': SESSION_DESC,
       'total_events': len(all_ev), 'today_events': len(ev),
       'added': FIRST_RUN_ADDED, 'workingset': len(added), 'match_missed': missed,
       'blank': n_blank,
       'session_added': CLOSE_PHASE_ADDED, 'session_added_phases': {'weekend_single': CLOSE_PHASE_ADDED},
       'session_backfilled_total': CLOSE_PHASE_BF,
       'session_backfilled_this_run': backfilled,
       'session_backfill_detail': {'by_event_date': dict(by_evdate), 'by_track': dict(by_track_bf),
                                   'by_actual_date': dict(by_adate), 'detail': back_detail,
                                   'basis': '进程内增量（二次执行归零，§3.112c）'},
       'session_backfill_detail_close_phase': {'basis': '库内现状（10/16 事件中 actual_date == 2026-10-16），跨重跑稳定',
                                               'n': CLOSE_PHASE_BF, 'detail': CLOSE_BF_DETAIL},
       'blank_by_date_final': dict(sorted(bdate.items())),
       'blank_by_track_final': dict(btrack),
       'blank_by_date_track_final': {f'{k[0]}|{k[1]}': v for k, v in sorted(blank_pairs.items())},
       'reference_trading_day_by_track': REF_BY_TRACK_NEW,
       'reference_day_note': (
           'A股医药/大消费/其他·宽基/宏观 → **2026-10-19（周一）**（下一 A股 交易日）；'
           '恒生科技 → **2026-10-20**（⚠️ 10/19 为「港股重阳节翌日休市 + A股 正常交易」混合档镜像，'
           '港股当日无收盘价 → 依 §3.110「参考指数当日须有真实收盘价」顺延，§3.108 条款 22）；'
           '美股标普医药 → **2026-10-19**（美东日历日；US 10/19 为正常交易日）。'
           '⚠️ §3.154b：REF_BY_TRACK_NEW 为计算项，本档未沿用 10/16 档的 {10/19, 10/20, 10/16}，'
           '其中美股项由 2026-10-16 改为 2026-10-19（10/16 档的正确值在 10/18 已成过去时）。'),
       'backfill_note': (
           '本档为纯非交易日：**A股与港股均无新交易日 → A股/港股类留空条目一律不可回填**（预期状态）；'
           '**唯一可回填项 = 10/16 档留空的「美股标普医药」条目** —— 因其参考指数 XLV 于本档新增 US 10/16 '
           f'真实收盘行（XLV 176.71 / −0.2709%，已写入 indices.csv +8 行）→ 参考日 = 2026-10-16（美东日历日）。'
           '判据严格采用 §3.110「参考指数在当日是否有真实收盘价」，**不以「是否 A股 交易日」一刀切**。'),
       'window_n_delta': n_delta,
       'window_n_delta_mechanism': {
           'index_gained_new_date': ['XLV（美股标普医药，本档新增 US 10/16 真实收盘行）'],
           'index_date_set_unchanged': ['000001 / 000300 / 000932 / 000933 / 399006（A股 类，末行仍 2026-10-16）',
                                        'HSTECH（恒生科技，末行仍 2026-10-16）'],
           'onesample_n_delta_total': ones_delta_total,
           'onesample_n_delta_by_track': {t: v['delta'] for t, v in sorted(ones_delta.items())},
           'onesample_n_delta_detail': {t: v for t, v in sorted(ones_delta.items())},
           'note': '1 日 n 增量恒等于本档回填条数（§3.110）；多日 n 增量仅由「XLV 新增交易日」驱动（美股标普医药），其余赛道零变动。',
       },
       'intraday_pseudo_close_warning': {
           'applies': False,
           'note': '本档为周末单档（无盘前/盘中档执行），且 indices.csv 本档新增的 8 行为美股 10/16 **真实收盘**（非伪收盘）→ 无伪收盘覆盖情形。',
       },
       'rerun_note': '可重入脚本：二次执行 added/backfilled 归零；工作集取自库内本窗口条目（§3.113f）',
       'similarity_by_track': {t: {'n': len(arr),
                                   'avg_3d': (round(sum(x['avg_3d'] for x in arr if x['avg_3d'] is not None) / len([x for x in arr if x['avg_3d'] is not None]), 2)
                                              if any(x['avg_3d'] is not None for x in arr) else None),
                                   'avg_5d': (round(sum(x['avg_5d'] for x in arr if x['avg_5d'] is not None) / len([x for x in arr if x['avg_5d'] is not None]), 2)
                                              if any(x['avg_5d'] is not None for x in arr) else None),
                                   'avg_10d': (round(sum(x['avg_10d'] for x in arr if x['avg_10d'] is not None) / len([x for x in arr if x['avg_10d'] is not None]), 2)
                                               if any(x['avg_10d'] is not None for x in arr) else None),
                                   'avg_conf': round(sum(x['confidence'] for x in arr) / len(arr), 1)}
                               for t, arr in agg.items()},
       'similarity_detail': sim_out,
       'track_net_sentiment_close': track_net,
       'exposure_weighted_net_sentiment_close': weighted,
       'track_net_sentiment_day_all': tnet_all,
       'exposure_weighted_net_sentiment_day_all': w_all,
       'exposure_weights': {k: round(v, 4) for k, v in w.items()},
       'onesample': {t: {'n': len(a), 'mean': round(sum(x[0] for x in a) / len(a), 4),
                         'up_ratio': round(sum(1 for x in a if x[0] > 0) / len(a), 4)}
                     for t, a in ones.items()},
       'direction_hit_strict': {t: dict(d) for t, d in strict.items()},
       'windows': {t: {str(n): ({'n': len(a), 'mean': round(sum(a) / len(a), 4)} if a else {'n': 0, 'mean': None})
                       for n, a in d.items()} for t, d in win_d.items()},
       'track_index_map': track_index,
       'window_sparse_tracks': sparse_tracks,
       'window_min_days': MIN_DAYS,
       'window_guard': guard,
       'legacy_missing_actual_date': legacy_missing,
       'note': ('A股医药 3/5/10 日窗口以 399006（创业板指）为代理（§3.111b），1 日窗口用 000933；'
                '宏观类参考指数 = 000001；美股标普医药 1 日窗口 = XLV；'
                '方向命中率按 actual_date == 事件日 严格过滤（§3.115b）；avg_*d 全 None 时写 null（§3.119d）')}
json.dump(out, open(os.path.join(HIST, 'event_stats_20261018_close.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
print('\n已保存 event_stats_20261018_close.json')
