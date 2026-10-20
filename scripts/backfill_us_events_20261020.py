# -*- coding: utf-8 -*-
"""2026-10-20 盘中档：**美股类事件即时回填**（§3.161a 固定工序）
   —— 事件库 events-2026-10-20.json 中 `ref_market == 美股` 的新增条目，
      其参考指数 XLV 的 US 10/19 收盘已于北京 10/20 04:00 成型并落入 indices.csv
      → 必须在**同一采集档内**回填 `reference.actual_date = 2026-10-19`，否则下一档
        `ref_ret(XLV, '2026-10-20')` 会取到 US 10/20 收盘 → 参考日错位 1 天。
⚠️ 同时修正 event_stats_intraday_20261020.json 的 `session_backfilled_total` / `session_backfill_detail`，
   并重算 `blank_by_*`（§3.112c：报告引用须取 session 快照字段，非进程内增量）
"""
import json, os, csv, glob
from collections import Counter

BASE = '/Users/jieyang/Documents/WealthHub'
EV = os.path.join(BASE, 'data/processed/events')
HIST = os.path.join(BASE, 'data/processed/history')
TODAY = '2026-10-20'
WIN = '盘中(10/20 07:30-13:30)'
REF_MARKET = {'A股医药': 'A股', '大消费': 'A股', '其他/宽基': 'A股', '宏观': 'A股',
              '恒生科技': '港股', '美股标普医药': '美股'}
TRACK_INDEX = {'A股医药': '399006', '大消费': '000932', '其他/宽基': '000300',
               '宏观': '000001', '恒生科技': 'HSTECH', '美股标普医药': 'XLV'}

idx = {}
with open(os.path.join(HIST, 'indices.csv'), encoding='utf-8-sig') as fh:
    for r in csv.DictReader(fh):
        try:
            idx[(r['code'], r['date'])] = float(r['close'])
        except Exception:
            pass

ev_path = os.path.join(EV, f'events-{TODAY}.json')
ev = json.load(open(ev_path, encoding='utf-8'))
print(f'events-{TODAY}.json 共 {len(ev)} 条')

filled = []
for e in ev:
    if e.get('window') != WIN:
        continue
    mk = REF_MARKET.get(e['track'])
    if mk != '美股':
        continue
    ref = e.setdefault('reference', {})
    if ref.get('actual_ret_1d') is not None:
        continue
    code = TRACK_INDEX['美股标普医药']
    actual = '2026-10-19'
    cur, prev = idx.get((code, actual)), idx.get((code, '2026-10-16'))
    assert cur is not None and prev is not None, f'{code} 缺 {actual} 或 2026-10-16 收盘'
    ret = round((cur / prev - 1) * 100, 4)
    ref.update({'index': code, 'actual_date': actual, 'actual_close': cur,
                'actual_ret_1d': ret,
                'backfill_note': f'§3.161a 即时回填：美股类事件的参考日为美东日历日 {actual}，'
                                 f'该日收盘已于北京 10/20 04:00 成型 → 本采集档内回填（防下一档参考日错位 1 天）'})
    e['planned_ref_date'] = actual
    filled.append({'title': e['title'][:60], 'track': e['track'], 'index': code,
                   'actual_date': actual, 'actual_ret_1d': ret})

json.dump(ev, open(ev_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(f'\n即时回填 {len(filled)} 条（美股类）:')
for x in filled:
    print('  ', x)

# ---------- 修正 event_stats ----------
sp = os.path.join(HIST, 'event_stats_intraday_20261020.json')
st = json.load(open(sp, encoding='utf-8'))

all_ev, days = [], set()
files = sorted(glob.glob(os.path.join(EV, 'events-2026-*.json')))
for f in files:
    d = json.load(open(f, encoding='utf-8'))
    all_ev.extend(d)
    days |= {e['date'] for e in d}
blank = [e for e in all_ev if (e.get('reference') or {}).get('actual_ret_1d') is None]
print(f'\n全库 {len(all_ev)} 条 / {len(days)} 个事件日 / {len(files)} 个采集档；留空 {len(blank)} 条')

st['session_backfilled_total'] = len(filled)
st['session_backfilled_this_run'] = len(filled)
st['session_backfill_detail'] = filled
st['session_backfilled_note'] = (
    f'{len(filled)} 条 —— **美股类即时回填**（§3.161a）：参考指数 XLV 的 US 10/19 收盘已于北京 10/20 04:00 成型 '
    f'→ 本采集档内回填 actual_date = 2026-10-19，防止下一档 ref_ret 取到 US 10/20 收盘而错位 1 天。'
    '**A股/港股 类 0 条** —— 13:45 双市场均未收盘，参考日 2026-10-20 尚无可用收盘（结构性，非缺陷）。')
st['events_total'] = len(all_ev)
st['event_days_total'] = len(days)
st['collect_days_total'] = len(files)
st['blank_total'] = len(blank)
st['blank_by_date_final'] = dict(sorted(Counter(e['date'] for e in blank).items()))
st['blank_by_track'] = dict(Counter(e['track'] for e in blank))
json.dump(st, open(sp, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(f'✅ event_stats_intraday_20261020.json 已修正：session_backfilled_total = {len(filled)} / blank {len(blank)}')
print('   blank_by_track:', st['blank_by_track'])
