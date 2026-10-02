# -*- coding: utf-8 -*-
"""2026-10-02 盘后档事件库处理（档型②混合档 · A股休市 + 港股复市首日收盘）：
  ① **回填**：按「参考指数在事件日/事件日之后首个交易日已有真实收盘价 → 回填」通用规则逐条判空
     —— 本档**新增可回填类别 = 恒生科技**（HSTECH 10/2 收盘 4,157.94 已成型，1 日实际 = −2.2556%）
     · 覆盖范围 = 「事件日为 10/1（港股休市、参考日 10/2）」+「事件日为 10/2（当日，参考日 10/2）」全部恒生科技类
     · A股类（A股医药/大消费/其他·宽基/宏观）→ 参考日 2026-10-08，本档仍留空
     · 美股标普医药 → 参考日 2026-10-02（美股交易日，收盘于北京 10/3 04:00 成型）→ 本档仍留空
  ② 追加本档 25 条盘后事件（window == '盘后(14:00-20:00)'，含空集硬守卫）
  ③ 全库完整性扫描（留空按「日期×赛道」二维落库，§3.98）
  ④ 1 日样本 + 3/5/10 日窗口统计 + 方向命中率 → history/event_stats_20261002_close.json
  ⑤ 暴露加权净情绪（权重取 portfolio_pending_20261002.json 正式版的 tracks pct）
⚠️ §3.122a：13:45 盘中档写入 indices.csv 的 2026-10-02 伪收盘行已被本档真实收盘行覆盖
   （indices.csv 以 (code,date) 为键、下游 dict 后写入覆盖先写入）→ 本档重算即自动修正窗口统计
   产物须写 intraday_pseudo_close_warning 落库自证
⚠️ §3.115b：方向命中率须写「参考日 == 事件日」显式过滤
⚠️ §3.113f：工作集 = 库内本窗口条目（幂等）；§3.114b：分阶段执行须写 session_prior_filled
⚠️ §3.114a：枚举型字段 track/category/direction 写入前做全等校验
⚠️ §3.113e：本次为全新撰写（非 sed 派生），读写路径 = 20261002 / 2026-10-02
"""
import json, os, glob, csv, re, datetime as _dt
from collections import defaultdict

BASE = '/Users/jieyang/Documents/WealthHub'
EV = os.path.join(BASE, 'data/processed/events')
HIST = os.path.join(BASE, 'data/processed/history')
TODAY = '2026-10-02'
WIN = '盘后(14:00-20:00)'

VALID_TRACK = {'宏观', 'A股医药', '大消费', '恒生科技', '美股标普医药', '其他/宽基'}
VALID_CAT = {'政策类', '业绩类', '行业事件类', '宏观类', '策略类'}
VALID_DIR = {'利多', '利空', '中性'}

REF_INDEX = {'宏观': '000001', 'A股医药': '000933', '大消费': '000932', '恒生科技': 'HSTECH',
             '美股标普医药': 'XLV', '其他/宽基': '000300'}
# §3.119c / §3.115d 逐市场分列
REF_BY_TRACK = {'A股医药': '2026-10-08', '大消费': '2026-10-08', '其他/宽基': '2026-10-08',
                '宏观': '2026-10-08', '恒生科技': '2026-10-02', '美股标普医药': '2026-10-02'}

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


def ref_ret(code, event_date):
    ser = idx.get(code)
    if not ser:
        return None, None
    ds = sorted(ser)
    for i, d in enumerate(ds):
        if d >= event_date and i > 0:
            return d, round((ser[d] / ser[ds[i - 1]] - 1) * 100, 4)
    return None, None


news = json.load(open(os.path.join(BASE, f'data/processed/news/news-{TODAY}.json'), encoding='utf-8'))
sent = json.load(open(os.path.join(BASE, f'data/processed/news/sentiment-{TODAY}.json'), encoding='utf-8'))
win_sent = [x for x in sent['items'] if x.get('window') == WIN]
if not win_sent:
    raise SystemExit('⚠️ 盘后窗口 sentiment 为 0 条 → per-item `window` 缺失，终止以免静默跳过入库')
print(f'盘后窗口情绪条目 {len(win_sent)}')

# ---------- ① 回填（本档新增恒生科技类可回填） ----------
files = sorted(glob.glob(os.path.join(EV, 'events-*.json')))
if os.path.join(EV, f'events-{TODAY}.json') not in files:
    files.append(os.path.join(EV, f'events-{TODAY}.json'))
all_ev = []
for f in sorted(glob.glob(os.path.join(EV, 'events-*.json'))):
    all_ev.extend(json.load(open(f, encoding='utf-8')))

backfilled, back_detail = 0, []
by_evdate, by_track_bf, by_adate = defaultdict(int), defaultdict(int), defaultdict(int)
for e in all_ev:
    ref = e.get('reference', {})
    if ref.get('actual_ret_1d') is not None:
        continue
    code = REF_INDEX.get(e['track'])
    if not code:
        continue
    d, r = ref_ret(code, e['date'])
    if d is None or r is None:
        continue
    # 仅当「该参考交易日的收盘价真实存在」才回填（§3.110）
    if d not in idx.get(code, {}):
        continue
    ref['actual_ret_1d'] = r
    ref['actual_date'] = d
    ref['ref_trade_day'] = REF_BY_TRACK.get(e['track'], d)
    backfilled += 1
    by_evdate[e['date']] += 1
    by_track_bf[e['track']] += 1
    by_adate[d] += 1
    back_detail.append({'id': e['id'], 'date': e['date'], 'track': e['track'],
                        'actual_date': d, 'actual_ret_1d': r})
for f in sorted(glob.glob(os.path.join(EV, 'events-*.json'))):
    # 将回填结果按 id 写回原文件（含当日文件；all_ev 为多文件拼接的扁平列表，须按 id 归位）
    arr = json.load(open(f, encoding='utf-8'))
    byid = {e['id']: e for e in all_ev}
    changed = False
    for e in arr:
        src = byid.get(e['id'])
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
    n = next((y for y in news if y['title'][:60] == x['title']), None)
    if n is None or n['title'][:60] in existing:
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
                      'ref_trade_day': REF_BY_TRACK.get(n['track'])},
    })
ev.extend(added)
json.dump(ev, open(ev_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
FIRST_RUN_ADDED = len(added)
print(f'事件库 {TODAY} +{FIRST_RUN_ADDED} 条 → 当日 {len(ev)} 条')

added = [e for e in ev if e.get('window') == WIN]
print(f'本档工作集（库内 window={WIN}）= {len(added)} 条（本进程新增 {FIRST_RUN_ADDED} 条）')

# 追加后重新扫描全库
all_ev = []
files = sorted(glob.glob(os.path.join(EV, 'events-*.json')))
for f in files:
    all_ev.extend(json.load(open(f, encoding='utf-8')))

# ---------- ③ 完整性扫描 ----------
n_blank = sum(1 for e in all_ev if e.get('reference', {}).get('actual_ret_1d') is None)
bdate, btrack = defaultdict(int), defaultdict(int)
blank_pairs = defaultdict(int)
for e in all_ev:
    if e.get('reference', {}).get('actual_ret_1d') is None:
        bdate[e['date']] += 1
        btrack[e['track']] += 1
        blank_pairs[(e['date'], e['track'])] += 1
print(f'\n全库 {len(all_ev)} 条 / {len(files)} 日；留空 {n_blank} 条')
print(f'  留空按日: {dict(sorted(bdate.items()))}')
print(f'  留空按赛道: {dict(btrack)}')
print('  留空（日期×赛道）:')
for (d0, t0), c in sorted(blank_pairs.items()):
    print(f'    {d0} {t0}: {c} 条（参考交易日 = {REF_BY_TRACK.get(t0)}，待回填）')

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
pf = json.load(open(os.path.join(HIST, 'portfolio_pending_20261002.json'), encoding='utf-8'))
w = {k: v['pct_of_total'] / 100.0 for k, v in pf['tracks'].items() if k != '现金'}
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
print('当日全量赛道净情绪:', tnet_all)
print(f'当日全量 名义合计 {round(sum(tnet_all.values()),2):+.2f} / 暴露加权 {w_all:+.4f}')

legacy_missing = sum(1 for e in all_ev
                     if e.get('reference', {}).get('actual_ret_1d') is not None
                     and not e.get('reference', {}).get('actual_date'))

# ---------- §3.114b 分阶段执行：本档共两阶段（首执行 + 修正持久化重跑），须能还原各阶段做了什么 ----------
_prev_path = os.path.join(HIST, 'event_stats_20261002_close.json')
prev = json.load(open(_prev_path, encoding='utf-8')) if os.path.exists(_prev_path) else {}
SESSION_ADDED = max(FIRST_RUN_ADDED, prev.get('session_added', 0))
SESSION_BF = backfilled + prev.get('session_backfilled_this_run', 0) if backfilled else prev.get('session_backfilled_total', 0)
if FIRST_RUN_ADDED == 0 and prev:
    SESSION_BF = prev.get('session_backfilled_total', 0) + backfilled
SESSION_PRIOR_BF = SESSION_BF - backfilled
print(f'\n[§3.114b 分阶段] 本次进程 新增 {FIRST_RUN_ADDED} / 回填 {backfilled}；'
      f'当档累计 session_added={SESSION_ADDED} session_backfilled_total={SESSION_BF} '
      f'session_prior_filled={SESSION_PRIOR_BF}')

out = {'date': TODAY, 'window': 'close', 'total_events': len(all_ev), 'today_events': len(ev),
       'added': FIRST_RUN_ADDED, 'workingset': len(added),
       'blank': n_blank,
       'session_added': SESSION_ADDED,
       'session_backfilled_total': SESSION_BF,
       'session_backfilled_this_run': backfilled,
       'session_prior_filled': SESSION_PRIOR_BF,
       'session_phase_note': (
           f'两阶段执行：① 首执行 —— 追加本档 25 条事件 + 回填恒生科技类 22 条'
           f'（事件日 10/1 共 12 条、事件日 10/2 共 10 条；HSTECH 10/2 收盘 4,157.94 / −2.2556% 于本档成型）；'
           f'② 修正重跑 —— 首执行的回填写回逻辑对「当日文件」误加了 skip 守卫，'
           f'致事件日 10/2 的 10 条回填仅计入统计而未持久化到 events-2026-10-02.json；'
           f'移除该守卫后重跑，本次再回填 10 条并落盘。'
           f'→ 当档累计：新增 {SESSION_ADDED} 条、回填 {SESSION_BF} 条（其中首执行 {SESSION_PRIOR_BF} 条、本次 {backfilled} 条）。'
           f'A股类（A股医药/大消费/其他·宽基/宏观）参考交易日 = 2026-10-08、'
           f'美股标普医药参考交易日 = 2026-10-02（收盘于北京 10/3 04:00 成型）→ 均仍留空，属预期状态。'),
       'session_backfill_detail': {'by_event_date': dict(by_evdate), 'by_track': dict(by_track_bf),
                                   'by_actual_date': dict(by_adate), 'detail': back_detail},
       'blank_by_date_final': dict(sorted(bdate.items())),
       'blank_by_track_final': dict(btrack),
       'blank_by_date_track_final': {f'{k[0]}|{k[1]}': v for k, v in sorted(blank_pairs.items())},
       'reference_trading_day_by_track': REF_BY_TRACK,
       'reference_day_note': ('§3.119c：长假多日窗口的参考交易日须「逐市场分列」。恒生科技 → 2026-10-02（今日，本档已回填）；'
                              '美股标普医药 → 2026-10-02（美股交易日，收盘于北京 10/3 04:00 成型）；'
                              'A股医药/大消费/其他·宽基/宏观 → 2026-10-08（A股复市日）。'),
       'intraday_pseudo_close_warning': {
           'applied': True,
           'note': ('§3.122a：13:45 盘中档曾向 indices.csv 写入 2026-10-02 港股伪收盘行（恒生科技 4,140.24），'
                    '使恒生科技 3/5/10 日窗口 n 被虚假抬高；本档写入真实收盘行（4,157.94）后重新计算，'
                    'indices.csv 以 (code,date) 为键、下游 dict 后写入覆盖先写入 → 自动修正，无需清理脏行。'),
           'intraday_pseudo': 4140.24, 'real_close': 4157.94,
       },
       'backfill_note': ('本档回填范围 = 恒生科技类事件（事件日为 10/1 或 10/2，参考指数 HSTECH 于 10/2 有真实收盘价）。'
                         '判据 = 「该事件的参考指数在当日是否有真实收盘价」（§3.110），'
                         '不是「当日是否 A股 交易日」—— 本档 A股 休市但港股开市，故恒生科技类应于当日口径回填。'),
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
       'note': ('本档回填恒生科技类；A股医药 3/5/10 日窗口以 399006（创业板指）为代理（§3.90/§3.111b），'
                '1 日窗口用 000933；宏观类参考交易日 = 000001（§3.100）；美股标普医药 1 日窗口 = XLV；'
                '方向命中率按 actual_date == 事件日 严格过滤（§3.115b）；avg_*d 全 None 时写 null（§3.119d）')}
json.dump(out, open(os.path.join(HIST, 'event_stats_20261002_close.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
print('\n已保存 event_stats_20261002_close.json')
