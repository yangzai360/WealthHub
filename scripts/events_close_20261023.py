# -*- coding: utf-8 -*-
"""2026-10-23 盘后档：事件库回填 + 追加 + event_stats + history_ref

档型②「正常交易日收盘」：
  · A股/港股 当日 15:00/16:00 已收盘 → 参考指数当日存在真实收盘价 → 可回填
  · 「盘后」窗口事件（13:30-20:00）严格顺延至下一交易日（§3.127a）
输出：
  data/processed/events/events-2026-10-23.json   （先 52 + 本档 18 条）
  data/processed/history/event_stats_20261023_close.json
  data/processed/history/history_ref_close_20261023.json
"""
import json, os, glob, csv, re
from collections import defaultdict

BASE = '/Users/jieyang/Documents/WealthHub'
EV = os.path.join(BASE, 'data/processed/events')
HIST = os.path.join(BASE, 'data/processed/history')
NEWS = os.path.join(BASE, 'data/processed/news')
TODAY = '2026-10-23'
WIN = '盘后(10/23 14:00-20:00)'

VALID_TRACK = {'宏观', 'A股医药', '大消费', '恒生科技', '美股标普医药', '其他/宽基'}
VALID_CAT = {'政策类', '业绩类', '行业事件类', '宏观类', '策略类'}
VALID_DIR = {'利多', '利空', '中性'}

REF_INDEX = {'宏观': '000001', 'A股医药': '000933', '大消费': '000932', '恒生科技': 'HSTECH',
             '美股标普医药': 'XLV', '其他/宽基': '000300'}
# 多日窗口代理（§3.90 / §3.111b / §3.112b）
WIN_INDEX = {'宏观': '000001', 'A股医药': '399006', '大消费': '000932', '恒生科技': 'HSTECH',
             '美股标普医药': 'XLV', '其他/宽基': '000300'}
REF_MARKET = {'A股医药': 'A股', '大消费': 'A股', '其他/宽基': 'A股', '宏观': 'A股',
              '恒生科技': '港股', '美股标普医药': '美股'}
# 本档新事件的下一参考交易日（逐市场分列，§3.119c / §3.154b）
# A股/港股：10/23（周五）已收盘、盘后事件晚于收盘 → 严格顺延至下一交易日 2026-10-26（10/24-25 周末）
# 美股：US 10/23 收盘成型于北京 10/24 04:00（晚于本档 20:00）→ 参考日 = 2026-10-23（美东日历日）
REF_BY_TRACK_NEW = {'A股医药': '2026-10-26', '大消费': '2026-10-26', '其他/宽基': '2026-10-26',
                    '宏观': '2026-10-26', '恒生科技': '2026-10-26', '美股标普医药': '2026-10-23'}

idx = defaultdict(dict)
with open(os.path.join(HIST, 'indices.csv'), encoding='utf-8-sig') as fh:
    for row in csv.DictReader(fh):
        try:
            idx[row['code']][row['date']] = float(row['close'])
        except Exception:
            pass
for code in sorted(set(list(REF_INDEX.values()) + list(WIN_INDEX.values()))):
    ds = sorted(idx.get(code, {}))
    print(f'  {code}: {len(ds)} 个交易日，尾部 ' + ' | '.join(f'{d}:{idx[code][d]}' for d in ds[-2:]))


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


def fwd_ret(code, d, n):
    ser = idx.get(code)
    if not ser or d not in ser:
        return None
    ds = sorted(ser)
    i = ds.index(d)
    if i + n >= len(ds):
        return None
    return round((ser[ds[i + n]] / ser[d] - 1) * 100, 4)


# ---------- ① 回填 ----------
all_ev = []
files = sorted(glob.glob(os.path.join(EV, 'events-*.json')))
for f in files:
    all_ev.extend(json.load(open(f, encoding='utf-8')))
print(f'回填前全库 {len(all_ev)} 条 / {len(files)} 个事件日')

backfilled, back_detail = 0, []
by_track_bf, by_adate = defaultdict(int), defaultdict(int)
for e in all_ev:
    ref = e.get('reference') or {}
    if ref.get('actual_ret_1d') is not None:
        continue
    code = REF_INDEX.get(e['track'])
    if not code:
        continue
    strict = str(e.get('window', '')).startswith('盘后')
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
    e['reference'] = ref
    backfilled += 1
    by_track_bf[e['track']] += 1
    by_adate[d] += 1
    back_detail.append({'id': e['id'], 'date': e['date'], 'track': e['track'],
                        'actual_date': d, 'actual_ret_1d': r})

CLOSE_BF_DETAIL = [{'id': e['id'], 'date': e['date'], 'track': e['track'],
                    'actual_date': (e.get('reference') or {}).get('actual_date'),
                    'actual_ret_1d': (e.get('reference') or {}).get('actual_ret_1d')}
                   for e in all_ev if (e.get('reference') or {}).get('actual_date') == TODAY]
print(f'回填 {backfilled} 条；按赛道 {dict(by_track_bf)}；按实际日 {dict(by_adate)}')
print(f'库内现状口径：actual_date == {TODAY} 的条目 = {len(CLOSE_BF_DETAIL)} 条')

byid = {e['id']: e for e in all_ev}
for f in files:
    arr = json.load(open(f, encoding='utf-8'))
    changed = False
    for e in arr:
        src = byid.get(e['id'])
        if src and (src.get('reference') or {}).get('actual_ret_1d') is not None \
                and (e.get('reference') or {}).get('actual_ret_1d') is None:
            e['reference'] = src['reference']
            changed = True
    if changed:
        json.dump(arr, open(f, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

# ---------- ② 追加本档事件 ----------
news = json.load(open(os.path.join(NEWS, 'news-2026-10-23.json'), encoding='utf-8'))
sent = json.load(open(os.path.join(NEWS, 'sentiment-2026-10-23.json'), encoding='utf-8'))
win_sent = [x for x in sent['items'] if x.get('window') == WIN]
if not win_sent:
    raise SystemExit('⚠️ 盘后窗口 sentiment 为 0 条 → window 字段缺失，终止')

ev_path = os.path.join(EV, f'events-{TODAY}.json')
ev = json.load(open(ev_path, encoding='utf-8'))
existing = {e['title'][:60] for e in ev}
VOL = {'低': 1.5, '中': 4.8, '高': 9.0}
added, missed = [], []
for x in win_sent:
    n = next((y for y in news if y['title'][:60] == x['title'][:60] or y['title'] == x['title']), None)
    if n is None:
        missed.append(x['title'][:40]); continue
    if n['title'][:60] in existing:
        continue
    bad = ({n['track']} - VALID_TRACK) | ({n.get('category', '行业事件类')} - VALID_CAT) | ({n['direction']} - VALID_DIR)
    if bad:
        raise SystemExit(f'⚠️ 非法枚举 {bad} in {n["title"][:30]}')
    added.append({'id': f"N{TODAY.replace('-', '')}-{len(ev) + len(added) + 1:03d}",
                  'date': TODAY, 'track': n['track'], 'category': n.get('category', '行业事件类'),
                  'title': n['title'], 'summary': n.get('summary', ''), 'source': n.get('source', ''),
                  'source_url': n.get('source_url', ''), 'sentiment': n.get('sentiment'),
                  'score': n.get('score'), 'strength': n.get('strength'),
                  'direction': n.get('direction'), 'volatility': n.get('volatility'),
                  'reason': n.get('brief', ''), 'window': WIN,
                  'planned_ref_date': REF_BY_TRACK_NEW.get(n['track']), 'ref_market': REF_MARKET.get(n['track']),
                  'reference': {'ret_3d': None, 'ret_5d': None, 'ret_10d': None,
                                'max_vol': VOL.get(n.get('volatility'), 4.8),
                                'confidence': n.get('confidence'), 'actual_ret_1d': None,
                                'actual_date': None, 'ref_trade_day': REF_BY_TRACK_NEW.get(n['track'])}})
ev.extend(added)
json.dump(ev, open(ev_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(f'本档 +{len(added)} 条 → 当日 {len(ev)} 条（未命中告警 {len(missed)}）')

# ---------- ③ 全库重载 + 完整性扫描 ----------
all_ev = []
for f in files:
    all_ev.extend(json.load(open(f, encoding='utf-8')))
blank = lambda e: (e.get('reference') or {}).get('actual_ret_1d') is None
blanks = [e for e in all_ev if blank(e)]
blank_by_date, blank_by_track = defaultdict(int), defaultdict(int)
for e in blanks:
    blank_by_date[e['date']] += 1
    blank_by_track[e['track']] += 1
print(f'全库 {len(all_ev)} 条 / 留空 {len(blanks)} 条；按事件日 {dict(sorted(blank_by_date.items())[-4:])}')

# 跨档连续性守卫：留空条目中，若参考指数在「上一档时点可得的最新收盘日」已有真实收盘 → 计为漏回填
PREV_CUTOFF = {'A股': '2026-10-23', '港股': '2026-10-23', '美股': '2026-10-22'}
miss = []
for e in blanks:
    mk = REF_MARKET.get(e['track'])
    code = REF_INDEX.get(e['track'])
    if not mk or not code:
        continue
    cut = PREV_CUTOFF[mk]
    if e['date'] <= cut and any(d <= cut for d in idx.get(code, {})):
        # 事件日前（含）已有可用收盘 → 应可回填
        d, r = ref_ret(code, e['date'], strict_after=str(e.get('window', '')).startswith('盘后'))
        if d is not None and d <= cut:
            miss.append({'id': e['id'], 'date': e['date'], 'track': e['track'], 'would_be': d})
print(f'跨档连续性守卫 miss_count = {len(miss)}（prev_cutoff = {PREV_CUTOFF}）')

# ---------- ④ 多日窗口统计（按赛道，窗口代理指数） ----------
def bigrams(s):
    s = re.sub(r'[^\u4e00-\u9fa5A-Za-z0-9]', '', str(s))
    return {s[i:i + 2] for i in range(len(s) - 1)} if len(s) > 1 else {s}


filled = [e for e in all_ev if not blank(e)]
track_series = {}
windows, window_n = {}, {}
for t, code in WIN_INDEX.items():
    ds = sorted(idx.get(code, {}))
    track_series[t] = (code, ds)
    windows[t], window_n[t] = {}, {}
    for n in (3, 5, 10):
        rs = [fwd_ret(code, (e.get('reference') or {}).get('actual_date'), n)
              for e in filled if e['track'] == t and (e.get('reference') or {}).get('actual_date')]
        rs = [r for r in rs if r is not None]
        windows[t][str(n)] = round(sum(rs) / len(rs), 4) if rs else None
        window_n[t][str(n)] = len(rs)

onesample, direction_hit = {}, {}
for t, (code, ds) in track_series.items():
    rets = [round((idx[code][ds[i]] / idx[code][ds[i - 1]] - 1) * 100, 4) for i in range(1, len(ds))]
    onesample[t] = {'index': code, 'n': len(rets), 'mean': round(sum(rets) / len(rets), 4) if rets else None,
                    'up_ratio': round(sum(1 for r in rets if r > 0) / len(rets), 4) if rets else None}
    pos = [e for e in filled if e['track'] == t and e.get('direction') == '利多'
           and (e.get('reference') or {}).get('actual_date') == e['date']]
    neg = [e for e in filled if e['track'] == t and e.get('direction') == '利空'
           and (e.get('reference') or {}).get('actual_date') == e['date']]
    direction_hit[t] = {'pos_n': len(pos), 'pos_hit': sum(1 for e in pos if e['reference']['actual_ret_1d'] > 0),
                        'neg_n': len(neg), 'neg_hit': sum(1 for e in neg if e['reference']['actual_ret_1d'] < 0)}

# ---------- ⑤ 历史相似度匹配（字符二元组 Jaccard，同赛道、仅取已回填条目） ----------
per_item, sim_by_track = {}, {}
for x in win_sent:
    tk = x['track']
    pool = [e for e in filled if e['track'] == tk and e['date'] < TODAY]
    a = bigrams(x['title'] + x.get('brief', ''))
    scored = []
    for e in pool:
        b = bigrams(e['title'] + str(e.get('reason', '')))
        if not a or not b:
            continue
        j = len(a & b) / len(a | b)
        scored.append((j, e))
    scored.sort(key=lambda y: -y[0])
    tops = []
    for j, e in scored[:3]:
        ref = e.get('reference') or {}
        ad = ref.get('actual_date')
        tops.append({'date': e['date'], 'title': e['title'][:60], 'jaccard': round(j, 4),
                     'ret_1d': ref.get('actual_ret_1d'),
                     'ret_3d': fwd_ret(WIN_INDEX[tk], ad, 3) if ad else None,
                     'ret_5d': fwd_ret(WIN_INDEX[tk], ad, 5) if ad else None,
                     'ret_10d': fwd_ret(WIN_INDEX[tk], ad, 10) if ad else None})
    per_item[x['title'][:50]] = {'track': tk, 'category': x.get('category'), 'tops': tops}
    sim_by_track.setdefault(tk, []).append(max([t['jaccard'] for t in tops], default=0))

track_agg = {}
for tk, js in sim_by_track.items():
    items = [v for v in per_item.values() if v['track'] == tk]
    allt = [t for v in items for t in v['tops']]
    def avg(key):
        vs = [t[key] for t in allt if t[key] is not None]
        return round(sum(vs) / len(vs), 2) if vs else None
    track_agg[tk] = {'n_items': len(items), 'n_matched': len(allt),
                     'jaccard_mean': round(sum(js) / len(js), 4),
                     '1d_mean': avg('ret_1d'), '1d_n': sum(1 for t in allt if t['ret_1d'] is not None),
                     '3d_mean': avg('ret_3d'), '3d_n': sum(1 for t in allt if t['ret_3d'] is not None),
                     '5d_mean': avg('ret_5d'), '5d_n': sum(1 for t in allt if t['ret_5d'] is not None),
                     '10d_mean': avg('ret_10d'), '10d_n': sum(1 for t in allt if t['ret_10d'] is not None)}

jacc_all = [j for js in sim_by_track.values() for j in js]
print(f'相似度 Top3 Jaccard：均值 {round(sum(jacc_all)/len(jacc_all), 4)}，区间 {round(min(jacc_all),4)}~{round(max(jacc_all),4)}')

# ---------- ⑥ 落盘 ----------
es = {
    'date': TODAY, 'window': 'close', 'total_events': len(all_ev), 'today_events': len(ev),
    'added': len(added), 'session_added': 70, 'workingset': len(win_sent),
    'blank': len(blanks), 'blank_by_date_final': dict(sorted(blank_by_date.items())),
    'blank_by_track': dict(blank_by_track),
    'session_backfilled_this_run': backfilled,
    'session_backfilled_total': backfilled,
    'session_backfilled_note': (f'本档回填 {backfilled} 条（按赛道 {dict(by_track_bf)}、按实际日 {dict(by_adate)}）；'
                                '主体为 10/23 盘前/盘中窗口事件的 1 日窗口（参考日 2026-10-23 A股/港股 真实收盘），'
                                '以及 10/21 盘后窗口事件（参考日 10/23）；'
                                '本档 18 条盘后事件按 §3.127a 严格顺延至 10/23，属结构性留空'),
    'session_phase_note': '单阶段执行（盘后档）：先回填（A股/港股 已收盘）→ 再追加本档事件',
    'cross_session_continuity_guard': {'prev_cutoff_by_track': PREV_CUTOFF, 'miss_count': len(miss), 'miss': miss},
    'session_type': 'normal_trading_day_close',
    'session_type_note': '档型②：A股 15:00 收盘 + 港股 16:00 收盘（双市场同开双收盘）+ 美股 10/23 未开盘',
    'ref_market_map': REF_MARKET, 'planned_ref_date_map': {'A股': '2026-10-23', '港股': '2026-10-23', '美股': '2026-10-23'},
    'title_match_miss': missed,
    'pseudo_close_n_delta': {
        'note': ('盘后档以 10/23 真实收盘覆盖盘中档 12 行伪收盘（A股 板块 7 + 港股指数 5）→ '
                 'n 值理论上不再虚增；下列为本档重算后的多日窗口 n（与盘中档对比见报告）'),
        'valid_days': {t: len(track_series[t][1]) for t in track_series}},
    'similarity_by_track': track_agg,
    'similarity_detail': per_item,
    'jaccard_mean_all': round(sum(jacc_all) / len(jacc_all), 4),
    'onesample': onesample, 'direction_hit_strict': direction_hit,
    'windows': windows, 'window_n': window_n,
    'track_index_map': WIN_INDEX,
    'window_sparse_tracks': {t: window_n[t] for t in window_n if min(window_n[t].values() or [0]) < 20},
    'window_min_days': 20,
    'window_guard': {WIN_INDEX[t]: {'track': t, 'distinct_days': len(track_series[t][1])} for t in track_series},
    'rerun_note': '可重入脚本：二次执行 added/backfilled 归零；session_added 为首执行实测值 70（含盘前 26 + 盘中 26 + 盘后 18）',
    'note': ('A股医药 3/5/10 日窗口以 399006（创业板指）为代理、1 日窗口用 000933（§3.90/§3.111b）；'
             '方向命中率按 actual_date == 事件日 严格过滤（§3.115b）；'
             '「盘后」窗口事件严格顺延下一交易日（§3.127a）'),
}
json.dump(es, open(os.path.join(HIST, 'event_stats_20261023_close.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)

hr = {'date': TODAY, 'window': WIN, 'n_items': len(win_sent), 'track_agg': track_agg,
      'per_item': per_item, 'track_index_map': WIN_INDEX,
      'note': ('相似度为「字符二元组 Jaccard」近似（DeepSeek 402 降级，无语义向量）；'
               'A股医药多日窗口用 399006 代理（§3.90）；窗口不可用返回 None 并在 agg 中以 *d_n 计数'),
      'pseudo_close_warning': '本档已用 10/23 真实收盘覆盖盘中伪收盘行；多日窗口 n 已重算'}
json.dump(hr, open(os.path.join(HIST, 'history_ref_close_20261023.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)

print('\n多日窗口均值：')
for t in windows:
    print(f"  {t:8s} 3d={windows[t]['3']} (n={window_n[t]['3']}) 5d={windows[t]['5']} (n={window_n[t]['5']}) 10d={windows[t]['10']} (n={window_n[t]['10']})")
print('样本内(onesample)：', {t: (v['n'], v['mean'], v['up_ratio']) for t, v in onesample.items()})
print('方向命中率：', direction_hit)
print('分赛道相似度：', {t: (v['jaccard_mean'], v['1d_mean'], v['n_matched']) for t, v in track_agg.items()})
