# -*- coding: utf-8 -*-
"""盘前档 2026-08-27：①事件库追加 16 条（actual_ret_1d 待 8/27 收盘回填）
②回填 8/26 遗留 3 条美股标普医药（XLV 8/26 -1.00%）③全库完整性扫描 ④1日样本+方向验证 ⑤3/5日窗口统计"""
import json, os, glob, csv
from collections import defaultdict

BASE = '/Users/jieyang/Documents/WealthHub'
EV = os.path.join(BASE, 'data/processed/events')
TODAY = '2026-08-27'

NEWS_PATH = os.path.join(BASE, 'data/processed/news/news-2026-08-27.json')
SENT_PATH = os.path.join(BASE, 'data/processed/news/sentiment-2026-08-27.json')
EVT_PATH = os.path.join(EV, f'events-{TODAY}.json')

with open(NEWS_PATH, encoding='utf-8') as f:
    news = json.load(f)
with open(SENT_PATH, encoding='utf-8') as f:
    sentiments = json.load(f)

# ---------- 1. 追加 16 条盘前事件 ----------
evs = []
for i, s in enumerate(sentiments, 1):
    n = next((x for x in news if x['title'] == s['title']), {})
    evs.append({
        "id": f"N20260827-{i:03d}",
        "date": TODAY,
        "track": s['track'],
        "category": n.get('category', ''),
        "title": s['title'],
        "summary": n.get('summary', ''),
        "source": "WebSearch",
        "source_url": n.get('source_url', ''),
        "sentiment": s['sentiment'],
        "score": s['score'],
        "strength": s['strength'],
        "direction": s['direction'],
        "volatility": s['volatility'],
        "reason": s['comment'],
        "reference": {
            "ret_3d": None,
            "ret_5d": None,
            "ret_10d": None,
            "max_vol": None,
            "confidence": None,
            "actual_ret_1d": None,
            "note": "盘前事件,actual_ret_1d 待 8/27(周四)收盘回填",
            "ret_1d_ref": "赛道指数/ETF收盘",
            "actual_date": TODAY
        }
    })

with open(EVT_PATH, 'w', encoding='utf-8') as f:
    json.dump(evs, f, ensure_ascii=False, indent=1)
print(f'事件库追加 {len(evs)} 条 -> events-{TODAY}.json')

# ---------- 2. 回填 8/26 遗留美股标普医药 3 条（XLV 8/26 收盘 -1.00%） ----------
BACKFILL = {
    'N20260826-010': -1.00,
    'N20260826-011': -1.00,
    'N20260826-012': -1.00,
}
bf_path = os.path.join(EV, 'events-2026-08-26.json')
with open(bf_path, encoding='utf-8') as f:
    ev26 = json.load(f)
cnt = 0
for e in ev26:
    if e['id'] in BACKFILL:
        e['reference']['actual_ret_1d'] = BACKFILL[e['id']]
        e['reference']['note'] = '8/27盘前回填(XLV 8/26 -1.00%)'
        e['reference']['ret_1d_ref'] = 'XLV 8/26收盘'
        cnt += 1
with open(bf_path, 'w', encoding='utf-8') as f:
    json.dump(ev26, f, ensure_ascii=False, indent=1)
print(f'8/26 遗留美股标普医药回填 {cnt} 条（XLV 8/26 -1.00%）')

# ---------- 3. 全库完整性扫描 ----------
def get_ret1d(e):
    v = e.get('actual_ret_1d')
    if v is None:
        v = e.get('reference', {}).get('actual_ret_1d')
    return v

all_ev = []
for f in sorted(glob.glob(os.path.join(EV, 'events-*.json'))):
    all_ev += json.load(open(f, encoding='utf-8'))
nulls = [x for x in all_ev if get_ret1d(x) is None]
print(f'\n事件库全量累计: {len(all_ev)} 条；actual_ret_1d 留空: {len(nulls)} 条')
for x in nulls:
    print(f'  留空: {x.get("id")} [{x.get("track")}] {x.get("title","")[:50]}')

# ---------- 4. 1 日样本统计 + 方向验证 ----------
final = defaultdict(lambda: {'n': 0, 'rets': [], 'sp': {'n': 0, 'rets': []}, 'sn': {'n': 0, 'rets': []}, 'dir_ok': 0, 'dir_n': 0})
for x in all_ev:
    v = get_ret1d(x)
    if v is None:
        continue
    t = x.get('track', '?'); s = final[t]
    s['n'] += 1; s['rets'].append(float(v))
    strength = x.get('strength') or x.get('score') or 0
    if strength >= 60 and x.get('sentiment') == '正面':
        s['sp']['n'] += 1; s['sp']['rets'].append(float(v))
    if strength >= 60 and x.get('sentiment') == '负面':
        s['sn']['n'] += 1; s['sn']['rets'].append(float(v))
    senti = x.get('sentiment')
    if senti in ('正面', '负面'):
        s['dir_n'] += 1
        if (senti == '正面' and float(v) > 0) or (senti == '负面' and float(v) < 0):
            s['dir_ok'] += 1
print('\n赛道 1 日样本统计（截至 8/27 盘前）：')
tot_n = tot_ok = tot_sample = 0
for t, s in sorted(final.items()):
    def avg(lst): return round(sum(lst)/len(lst), 2) if lst else None
    print(f"  {t}: n={s['n']} 均值={avg(s['rets'])} | 强正面 n={s['sp']['n']} 均值={avg(s['sp']['rets'])} | 强负面 n={s['sn']['n']} 均值={avg(s['sn']['rets'])} | 方向 {s['dir_ok']}/{s['dir_n']}")
    tot_n += s['dir_n']; tot_ok += s['dir_ok']; tot_sample += s['n']
print(f'\n方向验证全局: {tot_ok}/{tot_n}（{round(tot_ok/tot_n*100) if tot_n else 0}%）；1 日样本总量 {tot_sample}')

# ---------- 5. 3/5 日窗口统计 ----------
print('\n--- 3/5 日窗口统计 ---')
idx_series = defaultdict(dict)
with open(os.path.join(BASE, 'data/processed/history', 'indices.csv'), encoding='utf-8-sig') as f:
    for row in csv.reader(f):
        if len(row) >= 7 and row[0] in ('index', 'us_index'):
            d, code, pct = row[1], row[3], row[5]
            try:
                idx_series[code][d] = float(pct)
            except Exception:
                pass
track_idx = {
    '宏观': '000001',
    'A股医药': '399006',
    '大消费': '000932',
    '恒生科技': 'HSTECH',
    '美股标普医药': 'XLV',
    '其他/宽基': '000001',
}
ev_dated = []
for x in all_ev:
    v = get_ret1d(x)
    if v is None:
        continue
    d = x.get('date')
    if not d:
        continue
    ev_dated.append((d, x))
ret3_stats = defaultdict(lambda: {'n': 0, 'rets': []})
ret5_stats = defaultdict(lambda: {'n': 0, 'rets': []})
for d, x in ev_dated:
    t = x.get('track', '?')
    code = track_idx.get(t)
    if not code:
        continue
    dates = sorted(idx_series.get(code, {}).keys())
    if d not in dates:
        continue
    idx_pos = dates.index(d)
    if idx_pos + 4 <= len(dates):
        cum = 1.0
        for i in range(idx_pos + 1, idx_pos + 4):
            if i >= len(dates):
                cum = None
                break
            cum *= (1 + idx_series[code][dates[i]] / 100.0)
        if cum is not None:
            ret3_stats[t]['n'] += 1
            ret3_stats[t]['rets'].append((cum - 1) * 100)
    if idx_pos + 6 <= len(dates):
        cum = 1.0
        for i in range(idx_pos + 1, idx_pos + 6):
            if i >= len(dates):
                cum = None
                break
            cum *= (1 + idx_series[code][dates[i]] / 100.0)
        if cum is not None:
            ret5_stats[t]['n'] += 1
            ret5_stats[t]['rets'].append((cum - 1) * 100)
for t in ['美股标普医药', '恒生科技', 'A股医药', '大消费', '宏观']:
    s3, s5 = ret3_stats.get(t), ret5_stats.get(t)
    if s3 and s3['n']:
        avg5 = 'n/a'
        if s5 and s5['rets']:
            avg5 = f"{sum(s5['rets'])/len(s5['rets']):.2f}"
        print(f"  {t}: 3日 n={s3['n']} 均值={sum(s3['rets'])/len(s3['rets']):.2f}% 最差={min(s3['rets']):.2f}% 最好={max(s3['rets']):.2f}% | 5日 n={s5['n'] if s5 else 0} 均值={avg5}%")

print('\nDONE 8/27 盘前事件追加+回填+统计完成')
