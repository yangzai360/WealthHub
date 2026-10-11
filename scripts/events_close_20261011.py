# -*- coding: utf-8 -*-
"""2026-10-11 盘后档（周日 · 档型①「纯非交易日」· 常规周末）：事件库更新与统计

输入：news-2026-10-11.json / sentiment-2026-10-11.json（news 与 sentiment 双侧均带 window）
输出：events-2026-10-11.json / event_stats_20261011_close.json

⚠️ §3.114a：枚举型字段 track/category/direction 写入前做全等校验
⚠️ §3.130a：标题匹配须「双侧 60 字前缀比对 + 全称兜底 + 未命中打印告警」
⚠️ §3.130b：`strict_after` 必须在**取数阶段**实现，禁止「先取同日再在调用侧跳过」
⚠️ §3.139b：`session_added` 禁用 `max()`，一律「库内现状」口径
⚠️ 本档新增：**回填条目一律写入 `reference.backfilled_on = TODAY`**，
   使「本档回填量」可跨重跑稳定清点（解决 §3.112c 二次执行归零 + §3.139k 语义混淆）
⚠️ §3.139a：美股类事件参考交易日一律以「美东日历日」标注
"""
import json, os, glob, csv, re, datetime as _dt
from collections import defaultdict

BASE = '/Users/jieyang/Documents/WealthHub'
EV = os.path.join(BASE, 'data/processed/events')
HIST = os.path.join(BASE, 'data/processed/history')
TODAY = '2026-10-11'
WIN = '周末(10/9 20:00-10/11 20:00)'
SESSION_TYPE = 'pure_non_trading_day_close'
SESSION_DESC = ('档型①「纯非交易日」（A股与港股「均」未开市；美股照常开市不改变该判定）。'
                '本档为常规周末（10/10 周六 + 10/11 周日）20:00 盘后复盘档，'
                '不产 portfolio_close_* / portfolio_pending_*；唯一真实新增定价 = 美股 10/9（周五）收盘。')

VALID_TRACK = {'宏观', 'A股医药', '大消费', '恒生科技', '美股标普医药', '其他/宽基'}
VALID_CAT = {'政策类', '业绩类', '行业事件类', '宏观类', '策略类'}
VALID_DIR = {'利多', '利空', '中性'}

REF_INDEX = {'宏观': '000001', 'A股医药': '000933', '大消费': '000932', '恒生科技': 'HSTECH',
             '美股标普医药': 'XLV', '其他/宽基': '000300'}
# 本档「新事件」的下一参考交易日（§3.119c 逐市场分列；周末档一律顺延至下一交易日 2026-10-12）
REF_BY_TRACK_NEW = {k: '2026-10-12' for k in REF_INDEX}

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
    """返回 (参考交易日, 该日相对前一交易日的涨跌幅%)。"""
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

# ---------- ① 回填（可回填者 = 参考指数在「事件日或其后的首个观测日」已有真实收盘价） ----------
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
    strict = str(e.get('window', '')).startswith(('盘后', '周末'))
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
    ref['backfilled_on'] = TODAY          # ★ 本档新增：可跨重跑稳定清点本档回填量
    backfilled += 1
    by_evdate[e['date']] += 1
    by_track_bf[e['track']] += 1
    by_adate[d] += 1
    back_detail.append({'id': e['id'], 'date': e['date'], 'track': e['track'],
                        'actual_date': d, 'actual_ret_1d': r})

# 库内现状口径：本档写入的回填（reference.backfilled_on == TODAY），跨重跑稳定
CLOSE_BF_DETAIL = [{'id': e['id'], 'date': e['date'], 'track': e['track'],
                    'actual_date': (e.get('reference') or {}).get('actual_date'),
                    'actual_ret_1d': (e.get('reference') or {}).get('actual_ret_1d')}
                   for e in all_ev
                   if (e.get('reference') or {}).get('backfilled_on') == TODAY]
print(f'[库内现状] reference.backfilled_on == {TODAY} 的条目 = {len(CLOSE_BF_DETAIL)} 条')

byid_all = {e['id']: e for e in all_ev}
for f in sorted(glob.glob(os.path.join(EV, 'events-*.json'))):
    # §3.123d：按 id 归位写回，禁止对「当日文件」加 skip 守卫
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
        raise SystemExit(f'⚠️ 非法枚举 {bad} in {n["title"][:30]}（§3.114a 静默双重失效）')
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

workingset = [e for e in ev if e.get('window') == WIN]
print(f'本档工作集（库内 window={WIN}）= {len(workingset)} 条（本进程新增 {FIRST_RUN_ADDED} 条）')

all_ev = []
files = sorted(glob.glob(os.path.join(EV, 'events-*.json')))
for f in files:
    all_ev.extend(json.load(open(f, encoding='utf-8')))

# ---------- ③ 完整性扫描（§3.125b：嵌套字段判空） ----------
blank = lambda e: (e.get('reference') or {}).get('actual_ret_1d') is None
n_blank = sum(1 for e in all_ev if blank(e))
bdate, btrack = defaultdict(int), defaultdict(int)
blank_pairs = defaultdict(int)
for e in all_ev:
    if blank(e):
        bdate[e['date']] += 1
        btrack[e['track']] += 1
        blank_pairs[(e['date'], e['track'])] += 1
print(f'\n全库 {len(all_ev)} 条 / {len(files)} 日；留空 {n_blank} 条')
print(f'  留空按日: {dict(sorted(bdate.items()))}')
print(f'  留空按赛道: {dict(btrack)}')
print('  留空（日期×赛道）:')
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
for e in workingset:
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
    print(f"  {t:10s} n={len(arr):>2d}  Top3-3日均值={sum(a3)/len(a3) if a3 else float('nan'):+.2f}%  "
          f"5日={sum(a5)/len(a5) if a5 else float('nan'):+.2f}%  10日={sum(a10)/len(a10) if a10 else float('nan'):+.2f}%  "
          f"平均置信度={sum(cf)/len(cf):.0f}")

# ---------- ⑤ 事件库窗口统计 ----------
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
print('\n[§3.112b 三重守卫 / distinct 交易日] ' + str(guard))

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
pf = json.load(open(os.path.join(HIST, 'portfolio_close_20261009_fix.json'), encoding='utf-8'))
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

legacy_missing = sum(1 for e in all_ev
                     if e.get('reference', {}).get('actual_ret_1d') is not None
                     and not e.get('reference', {}).get('actual_date'))

# ---------- §3.127d/§3.138a 伪收盘覆盖的机器判据（n 变化量） ----------
_prev_path = os.path.join(HIST, 'event_stats_close_20261009.json')
prev = json.load(open(_prev_path, encoding='utf-8')) if os.path.exists(_prev_path) else {}
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
print('\n[上一档对照 prev_path = event_stats_close_20261009.json] 多日窗口 n 变化量:')
for t, dd in n_delta.items():
    print(f"  {t:10s} " + '  '.join(f"{k}日 {v['prev']}→{v['cur']} ({v['delta']:+d})" if v['delta'] is not None
                                    else f"{k}日 {v['cur']}" for k, v in dd.items()))

# ---------- §3.139b 分阶段自证（幂等：以「库内现状」为口径） ----------
PREV_ADDED = prev.get('session_added', 0)          # 10/9 档 = 41（记录，不累加，日期不同）
CLOSE_PHASE_ADDED = len([e for e in ev if e.get('window') == WIN])   # 库内现状：本档窗口条目数
SESSION_ADDED = CLOSE_PHASE_ADDED                   # 新日期 → 本档自成一个 session
SESSION_BF = len(CLOSE_BF_DETAIL)                   # 库内现状：本档写入的回填
print(f'\n[§3.139b 分阶段 / 幂等口径] 本次进程 新增 {FIRST_RUN_ADDED} / 回填 {backfilled}；'
      f'库内现状 本档新增 {CLOSE_PHASE_ADDED} / 本档回填 {SESSION_BF}；'
      f'上一档（10/9）session_added = {PREV_ADDED}（不同事件日，不累加）')

out = {'date': TODAY, 'window': 'close', 'session_type': SESSION_TYPE,
       'session_desc': SESSION_DESC,
       'total_events': len(all_ev), 'today_events': len(ev),
       'added': FIRST_RUN_ADDED, 'workingset': len(workingset), 'match_missed': missed,
       'blank': n_blank,
       'session_added': SESSION_ADDED,
       'session_added_phases': {'preopen_intraday': 0, 'close': CLOSE_PHASE_ADDED},
       'session_added_prior_day': PREV_ADDED,
       'session_backfilled_total': SESSION_BF,
       'session_backfilled_this_run': backfilled,
       'session_backfilled_this_phase': SESSION_BF,
       'session_backfill_phases': {'preopen_intraday': 0, 'close': SESSION_BF},
       'session_prior_filled': 0,
       'session_phase_note': (
           f'单阶段执行（本档为**纯非交易日周末档，无盘前/盘中档**）：追加本档 {CLOSE_PHASE_ADDED} 条事件'
           f'（window = {WIN}，本次进程新增 {FIRST_RUN_ADDED} 条）；'
           f'回填 {SESSION_BF} 条（**全部为 10/9 档留空的「美股标普医药（盘前/盘中窗口）」条目** —— '
           f'其参考指数 XLV 的 2026-10-09 收盘于本档首次可用，XLV 10/9 = +1.58%）。'
           f'⚠️ §3.139b：`session_added` 以「库内现状」为口径（本档 = {SESSION_ADDED}），'
           f'**不与上一档（10/9）的 {PREV_ADDED} 累加**（事件日不同）；'
           f'上一档值仅作连续性记录，见 session_added_prior_day。'
           '⚠️ §3.112c/§3.114b：二次执行后 added/backfilled 归零，而 session_* 读数保持稳定。'),
       'session_backfill_detail': {'by_event_date': dict(by_evdate), 'by_track': dict(by_track_bf),
                                   'by_actual_date': dict(by_adate), 'detail': back_detail,
                                   'basis': '进程内增量（二次执行归零，§3.112c）→ 以 session_backfill_detail_close_phase 为准'},
       'session_backfill_detail_close_phase': {
           'basis': '库内现状（reference.backfilled_on == TODAY），跨重跑稳定（本档新增字段）',
           'n': len(CLOSE_BF_DETAIL), 'detail': CLOSE_BF_DETAIL},
       'blank_by_date_final': dict(sorted(bdate.items())),
       'blank_by_track_final': dict(btrack),
       'blank_by_date_track_final': {f'{k[0]}|{k[1]}': v for k, v in sorted(blank_pairs.items())},
       'reference_trading_day_by_track': REF_BY_TRACK_NEW,
       'reference_day_note': ('§3.119c / §3.127a / §3.139a：参考交易日须「逐市场分列」且「盘后/周末窗口一律严格顺延」。'
                              '本档为**周末档**（窗口 10/9 20:00-10/11 20:00，晚于 A股 10/9 15:00 与港股 10/9 16:00 收盘）'
                              '→ **全部赛道（含美股标普医药）参考交易日 = 2026-10-12**：'
                              'A股医药/大消费/其他·宽基/宏观 → 下一 A股 交易日 = 10/12；'
                              '恒生科技 → 下一港股交易日 = 10/12；'
                              '美股标普医药 → 下一美股交易日 = 10/12（US 10/12 周一开市、债市因哥伦布日/原住民日休市）；'
                              '**美股交易日标注法 = 美东日历日**（§3.139a），与 A股/港股（本地日历日）同栏并存但口径不同。'
                              '⚠️ 美股 10/12 收盘成型于北京 10/13 04:00 → 本档该类条目留空属预期状态。'),
       'backfill_note': ('本档回填范围 = 全部留空条目中、其参考指数在「事件日或其后的首个观测日」已有真实收盘价者。'
                         '本档为周末 → **唯一新增可回填的观测日 = 2026-10-09（XLV，美股）**，'
                         '故回填 5 条 10/9 档留空的「美股标普医药 · 盘前/盘中窗口」条目；'
                         '1 日参考值 XLV 10/9 = +1.5759%。'
                         '判据 = 「该事件的参考指数在当日（或其后首个观测日）是否有真实收盘价」（§3.110），'
                         '**不是「当日是否 A股 交易日」**。'
                         '⚠️ §3.130b：strict_after 在取数阶段实现，禁止「先取同日再在调用侧跳过」。'
                         '⚠️ 本档新增 `reference.backfilled_on` 字段，使「本档回填量」可跨重跑稳定清点。'),
       'window_n_delta_note': (f'§3.127d / §3.133b / §3.133a：本档为**纯非交易日周末档**，无当日伪收盘行写入 → '
                               '多日窗口 n 的**唯一变化来源 = 上一档（10/9 收盘）已写入的新交易日**（本档不新增观测日）。'
                               '**本档与上一档（event_stats_close_20261009.json）对照**：'
                               '① **多日窗口 n 应全部 +0 或极小变动**（本档无新指数交易日、无伪收盘覆盖）；'
                               '② **1 日窗口 n 的增量恒等于本档回填条数（= 5，全部为美股标普医药）**。'
                               '⚠️ 美股 10/9 收盘行本档已写入 `indices.csv`（XLV 170.81 / IYH 72.14），'
                               '属**真实收盘行、非伪收盘**（本档无盘中档执行）。'),
       'window_n_delta': n_delta,
       'window_n_delta_mechanism': {
           'index_gained_new_date': ['XLV（美股标普医药，10/9 收盘行本档写入 → 解锁 1 日窗口回填）'],
           'index_date_set_unchanged': ['000001（宏观）', '000933/399006（A股医药）', '000932（大消费）',
                                        'HSTECH（恒生科技）', '000300（其他/宽基）'],
           'onesample_n_delta_total': SESSION_BF,
           'onesample_n_delta_by_track': dict(by_track_bf),
           'note': ('§3.139f：1 日窗口 n 增量恒等于本档回填条数（§3.110 判据）；'
                    '多日窗口 n 的两种归因（「指数新增交易日」vs「伪收盘覆盖」）本档均不适用 → 应零变动。'),
       },
       'intraday_pseudo_close_warning': {
           'applies': False,
           'note': ('§3.126a/§3.127d：本档为**纯非交易日周末档，无盘中档执行** → 本档未向 `indices.csv` 写入任何'
                    '盘中伪收盘行；本档写入的 8 行为**美股 10/9 真实收盘行**（成型于北京 10/10 04:00）。'),
       },
       'rerun_note': ('可重入脚本：二次执行 added/backfilled 归零；工作集取自库内本窗口条目（§3.113f）；'
                      'session_* 一律「库内现状」口径（§3.139b），不随重跑变化'),
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
       'exposure_weights': {k: round(v, 4) for k, v in w.items()},
       'exposure_weights_source': 'portfolio_close_20261009_fix.json#tracks（10/9 修正收盘口径）',
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
       'note': ('本档为纯非交易日周末档；A股医药 3/5/10 日窗口以 399006（创业板指）为代理（§3.90/§3.111b），'
                '1 日窗口用 000933；宏观类参考交易日 = 000001（§3.100）；美股标普医药 1 日窗口 = XLV；'
                '方向命中率按 actual_date == 事件日 严格过滤（§3.115b）；avg_*d 全 None 时写 null（§3.119d）')}
json.dump(out, open(os.path.join(HIST, 'event_stats_20261011_close.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
print('\n已保存 event_stats_20261011_close.json')
