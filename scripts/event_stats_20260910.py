# -*- coding: utf-8 -*-
"""盘前档 2026-09-10: 事件库统计——①1日样本(截至9/9回填) ②方向验证 ③3/5/10日事件后窗口统计"""
import json, os, glob, csv
from collections import defaultdict

BASE = '/Users/jieyang/Documents/WealthHub'
EV = os.path.join(BASE, 'data/processed/events')
TODAY = '2026-09-10'

all_ev = []
for p in sorted(glob.glob(os.path.join(EV, 'events-*.json'))):
    if TODAY in p:
        continue
    with open(p, encoding='utf-8') as f:
        all_ev.extend(json.load(f))

def get_ret1d(e):
    v = e.get('actual_ret_1d')
    if v is None:
        v = e.get('reference', {}).get('actual_ret_1d')
    return v

samples = defaultdict(lambda: {'n': 0, 'rets': [], 'pos': 0, 'spos': 0, 'spos_rets': [], 'sneg': 0, 'sneg_rets': []})
direction_total = 0
direction_ok = 0
track_dv = defaultdict(lambda: [0, 0])

for e in all_ev:
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
    score = e.get('score')
    try:
        score = int(score)
    except:
        score = None
    if senti == '正面' and score is not None and score >= 65:
        s['spos'] += 1
        s['spos_rets'].append(float(v))
    if senti == '负面' and score is not None and score <= 40:
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
print('\n=== 1日样本统计（截至 9/9 收盘回填） ===')
for t, s in sorted(samples.items()):
    if s['n'] == 0:
        continue
    rec = {
        'n': s['n'], 'avg': round(sum(s['rets'])/len(s['rets']), 2),
        'worst': round(min(s['rets']), 2), 'best': round(max(s['rets']), 2),
        'pos': round(s['pos']/s['n'], 2),
        'strong_pos_n': s['spos'], 'strong_pos_avg': round(sum(s['spos_rets'])/len(s['spos_rets']), 2) if s['spos_rets'] else None,
        'strong_neg_n': s['sneg'], 'strong_neg_avg': round(sum(s['sneg_rets'])/len(s['sneg_rets']), 2) if s['sneg_rets'] else None,
    }
    out_stats[t] = rec
    print(f"  {t}: n={rec['n']} avg={rec['avg']}% worst={rec['worst']} best={rec['best']} pos={rec['pos']} 强正{rec['strong_pos_n']}均值{rec['strong_pos_avg']} 强负{rec['strong_neg_n']}均值{rec['strong_neg_avg']}")

print(f"\n=== 方向验证（sentiment 口径, 中性剔除） ===")
print(f'  全局 {direction_ok}/{direction_total} ({round(direction_ok/direction_total*100,1) if direction_total else 0}%)')
for t, (ok, tot) in sorted(track_dv.items(), key=lambda x: -x[1][0]):
    if tot > 0:
        print(f'  {t}: {ok}/{tot} ({round(ok/tot*100)}%)')

# ---------- 3/5/10日事件后窗口统计 ----------
idx_rows = list(csv.reader(open(os.path.join(BASE, 'data/processed/history/indices.csv'), encoding='utf-8-sig')))
track_index = {
    'A股医药': ('399006', '创业板指'),
    '大消费': ('000932', '中证消费'),
    '恒生科技': ('HSTECH', '恒生科技'),
    '宏观': ('000001', '上证指数'),
    '美股标普医药': ('XLV', '美股医疗XLV'),
}
def build_series(code):
    seen = {}
    for r in idx_rows:
        if r and len(r) >= 6 and r[3] == code and r[1] != '':
            try:
                d = r[1][:10]
                c = float(r[4])
                seen[d] = c
            except:
                continue
    ds = sorted(seen.items())
    return [d for d, _ in ds], [c for _, c in ds]

def window_stats(ev_date, code, n_days):
    dates, closes = build_series(code)
    if not dates:
        return None
    try:
        i0 = dates.index(ev_date)
    except ValueError:
        return None
    ret = 1.0
    cnt = 0
    for i in range(i0 + 1, len(dates)):
        if cnt >= n_days:
            break
        if closes[i] is None or closes[i-1] in (None, 0):
            continue
        ret *= closes[i] / closes[i-1]
        cnt += 1
    if cnt < n_days:
        return None
    return (ret - 1) * 100

win3 = defaultdict(lambda: {'n': 0, 'rets': []})
win5 = defaultdict(lambda: {'n': 0, 'rets': []})
win10 = defaultdict(lambda: {'n': 0, 'rets': []})
for e in all_ev:
    d = e.get('date')
    t = e.get('track')
    if not d or t not in track_index:
        continue
    code = track_index[t][0]
    for wd, store in [(3, win3), (5, win5), (10, win10)]:
        r = window_stats(d, code, wd)
        if r is not None:
            store[t]['n'] += 1
            store[t]['rets'].append(r)

def agg(w):
    out = {}
    for t, s in w.items():
        if s['n']:
            out[t] = {'n': s['n'], 'avg': round(sum(s['rets'])/len(s['rets']), 2)}
    return out
w3, w5, w10 = agg(win3), agg(win5), agg(win10)
print('\n=== 3日窗口统计(事件后) ===')
for t, v in sorted(w3.items(), key=lambda x: -x[1]['avg']):
    print(f'  {t}: n={v["n"]} 均值 {v["avg"]}%')
print('=== 5日窗口统计(事件后) ===')
for t, v in sorted(w5.items(), key=lambda x: -x[1]['avg']):
    print(f'  {t}: n={v["n"]} 均值 {v["avg"]}%')
print('=== 10日窗口统计(事件后) ===')
for t, v in sorted(w10.items(), key=lambda x: -x[1]['avg']):
    print(f'  {t}: n={v["n"]} 均值 {v["avg"]}%')

out = {
    'date': TODAY, 'as_of': '2026-09-09收盘回填(XLV 9/9 -0.33% 回填 N20260909-002, 全库0留空)',
    'sample_stats': out_stats,
    'direction': {'ok': direction_ok, 'total': direction_total,
                  'pct': round(direction_ok/direction_total*100, 1) if direction_total else 0,
                  'by_track': {t: {'ok': v[0], 'total': v[1]} for t, v in track_dv.items() if v[1] > 0}},
    'win3': w3, 'win5': w5, 'win10': w10,
}
with open(os.path.join(EV, f'event_stats_{TODAY.replace("-", "")}.json'), 'w', encoding='utf-8') as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
print(f'\nevent_stats_20260910.json 已保存')
