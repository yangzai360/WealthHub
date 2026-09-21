# -*- coding: utf-8 -*-
"""2026-09-21 盘中档：事件库增量落库 + 窗口统计
- 从 sentiment-2026-09-18.json 取 window=intraday 的条目写入 events-2026-09-18.json
- 计算 1日样本 / 方向验证 / 3·5·10日窗口统计
"""
import json, os, glob, csv, re
from collections import defaultdict

BASE = '/Users/jieyang/Documents/WealthHub'
EV = os.path.join(BASE, 'data/processed/events')
TODAY = '2026-09-21'
TODAYC = TODAY.replace('-', '')
WINDOW = 'intraday'

sent = json.load(open(os.path.join(BASE, f'data/processed/news/sentiment-{TODAY}.json'), encoding='utf-8'))
new_items = [x for x in sent['items'] if x.get('window') == WINDOW]
# 硬守卫（§3.88）
if not new_items:
    raise SystemExit('intraday window 过滤结果为空，疑似 window 字段缺失')
print(f'intraday 标注 {len(new_items)} 条')

p_ev = os.path.join(EV, f'events-{TODAY}.json')
ev = json.load(open(p_ev, encoding='utf-8'))
base_n = len(ev)
seq = base_n
ev_exist = set(e['title'] for e in ev)
added = 0
for n in new_items:
    if n['title'] in ev_exist:
        continue
    seq += 1
    ev.append({
        "id": "N%s-%03d" % (TODAYC, seq), "date": TODAY, "track": n['track'],
        "category": n.get('category', '行业事件类'), "title": n['title'],
        "summary": n.get('brief', ''), "source": n.get('source', ''),
        "source_url": n.get('source_url', ''), "sentiment": n['sentiment'],
        "score": n['strength'], "strength": n['strength'], "direction": n['direction'],
        "volatility": n['volatility'], "reason": n.get('brief', ''),
        "window": WINDOW,
        "reference": {"ret_3d": None, "ret_5d": None, "ret_10d": None, "actual_ret_1d": None},
    })
    added += 1
json.dump(ev, open(p_ev, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(f'events-{TODAY}.json: {base_n} -> {len(ev)} (+{added})')

# ---------- 全库统计 ----------
all_ev = []
for p in sorted(glob.glob(os.path.join(EV, 'events-*.json'))):
    all_ev.extend(json.load(open(p, encoding='utf-8')))
print(f'事件库全库 {len(all_ev)} 条')

blank = sum(1 for e in all_ev if (e.get('actual_ret_1d') if e.get('actual_ret_1d') is not None
                                  else e.get('reference', {}).get('actual_ret_1d')) is None)
print(f'留空(actual_ret_1d 为 None) {blank} 条')

# ---------- 1日样本 / 方向验证（截至 9/18 收盘回填） ----------
hist_ev = [e for e in all_ev if TODAY not in str(e.get('date', ''))]

def get_ret1d(e):
    v = e.get('actual_ret_1d')
    if v is None:
        v = e.get('reference', {}).get('actual_ret_1d')
    return v

samples = defaultdict(lambda: {'n': 0, 'rets': [], 'pos': 0, 'spos': 0, 'spos_rets': [], 'sneg': 0, 'sneg_rets': []})
direction_total = direction_ok = 0
track_dv = defaultdict(lambda: [0, 0])
for e in hist_ev:
    t = e.get('track', '?')
    v = get_ret1d(e)
    if v is None:
        continue
    s = samples[t]
    s['n'] += 1
    s['rets'].append(float(v))
    if float(v) > 0:
        s['pos'] += 1
    senti = e.get('sentiment')
    try:
        score = int(e.get('score'))
    except Exception:
        score = None
    # ⚠️ 口径统一（§3.96）：与 events_preopen_/events_close_ 对齐 —— 强正 = direction 利多 且 score>=70；强负 = direction 利空 且 score>=70
    direc = e.get('direction')
    if direc == '利多' and score is not None and score >= 70:
        s['spos'] += 1
        s['spos_rets'].append(float(v))
    if direc == '利空' and score is not None and score >= 70:
        s['sneg'] += 1
        s['sneg_rets'].append(float(v))
    if senti not in ('正面', '负面'):
        continue
    direction_total += 1
    track_dv[t][1] += 1
    ok = (senti == '正面' and float(v) > 0) or (senti == '负面' and float(v) < 0)
    if ok:
        direction_ok += 1
        track_dv[t][0] += 1

out_stats = {}
print('\n=== 1日样本统计（截至 9/18 收盘回填） ===')
for t, s in sorted(samples.items()):
    if s['n'] == 0:
        continue
    rec = {
        'n': s['n'], 'avg': round(sum(s['rets']) / len(s['rets']), 2),
        'worst': round(min(s['rets']), 2), 'best': round(max(s['rets']), 2),
        'pos': round(s['pos'] / s['n'], 2),
        'strong_pos_n': s['spos'],
        'strong_pos_avg': round(sum(s['spos_rets']) / len(s['spos_rets']), 2) if s['spos_rets'] else None,
        'strong_neg_n': s['sneg'],
        'strong_neg_avg': round(sum(s['sneg_rets']) / len(s['sneg_rets']), 2) if s['sneg_rets'] else None,
    }
    out_stats[t] = rec
    print(f"  {t}: n={rec['n']} avg={rec['avg']}% worst={rec['worst']} best={rec['best']} pos={rec['pos']} "
          f"强正{rec['strong_pos_n']}均值{rec['strong_pos_avg']} 强负{rec['strong_neg_n']}均值{rec['strong_neg_avg']}")

print("\n=== 方向验证（sentiment 口径, 中性剔除） ===")
print(f'  全局 {direction_ok}/{direction_total} ({round(direction_ok/direction_total*100,1) if direction_total else 0}%)')
for t, (ok, tot) in sorted(track_dv.items(), key=lambda x: -x[1][0]):
    if tot > 0:
        print(f'  {t}: {ok}/{tot} ({round(ok/tot*100)}%)')

# ---------- 3/5/10 日窗口统计 ----------
idx_rows = list(csv.reader(open(os.path.join(BASE, 'data/processed/history/indices.csv'), encoding='utf-8-sig')))
track_index = {
    'A股医药': ('399006', '创业板指'),
    '大消费': ('000932', '中证消费'),
    '恒生科技': ('HSTECH', '恒生科技'),
    '宏观': ('000001', '上证指数'),
    '美股标普医药': ('XLV', '美股医疗XLV'),
}

def row_quote_date(r):
    m = re.search(r'美股(\d{4}-\d{2}-\d{2})', r[6] if len(r) > 6 else '')
    return m.group(1) if m else r[1][:10]

def build_series(code):
    seen = {}
    for r in idx_rows:
        if not r or len(r) < 6 or r[3] != code or r[1] == '':
            continue
        try:
            c = float(r[4])
        except Exception:
            continue
        d = row_quote_date(r) if r[0] == 'us_index' else r[1][:10]
        seen[d] = c
    ds = sorted(seen.items())
    return [d for d, _ in ds], [c for _, c in ds]

def window_stats(ev_date, code, n_days):
    dates, closes = build_series(code)
    if not dates or ev_date not in dates:
        return None
    i0 = dates.index(ev_date)
    ret = 1.0
    cnt = 0
    for i in range(i0 + 1, len(dates)):
        if cnt >= n_days:
            break
        if closes[i] is None or closes[i - 1] in (None, 0):
            continue
        ret *= closes[i] / closes[i - 1]
        cnt += 1
    if cnt < n_days:
        return None
    return (ret - 1) * 100

win3 = defaultdict(lambda: {'n': 0, 'rets': []})
win5 = defaultdict(lambda: {'n': 0, 'rets': []})
win10 = defaultdict(lambda: {'n': 0, 'rets': []})
for e in hist_ev:
    d, t = e.get('date'), e.get('track')
    if not d or t not in track_index:
        continue
    code = track_index[t][0]
    for wd, store in [(3, win3), (5, win5), (10, win10)]:
        r = window_stats(d, code, wd)
        if r is not None:
            store[t]['n'] += 1
            store[t]['rets'].append(r)

def agg(w):
    return {t: {'n': s['n'], 'avg': round(sum(s['rets']) / len(s['rets']), 2)}
            for t, s in w.items() if s['n']}

w3, w5, w10 = agg(win3), agg(win5), agg(win10)
for nm, w in [('3日', w3), ('5日', w5), ('10日', w10)]:
    print(f'\n=== {nm}窗口统计(事件后) ===')
    for t, v in sorted(w.items(), key=lambda x: -x[1]['avg']):
        print(f'  {t}: n={v["n"]} 均值 {v["avg"]}%')

out = {
    'date': TODAY, 'as_of': '2026-09-18收盘回填', 'window': WINDOW,
    'sample_stats': out_stats,
    'direction': {'ok': direction_ok, 'total': direction_total,
                  'pct': round(direction_ok / direction_total * 100, 1) if direction_total else 0,
                  'by_track': {t: {'ok': v[0], 'total': v[1]} for t, v in track_dv.items() if v[1] > 0}},
    'win3': w3, 'win5': w5, 'win10': w10,
}
dst = os.path.join(BASE, "data/processed/history", "event_stats_intraday_" + TODAYC + ".json")
json.dump(out, open(dst, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(f'\n{dst} 已保存')
