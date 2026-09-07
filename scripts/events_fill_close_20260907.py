# -*- coding: utf-8 -*-
"""盘后档 2026-09-07：①追加盘后 8 条事件(id 027-034) ②回填 9/7 当日全部事件
③回填 9/6 周末 16 条 ④全库完整性扫描 ⑤1日样本+方向验证 ⑥3/5日窗口统计"""
import json, os, glob
from collections import defaultdict

BASE = '/Users/jieyang/Documents/WealthHub'
EV = os.path.join(BASE, 'data/processed/events')
TODAY = '2026-09-07'

# ---------- 9/7 各赛道实际收盘走势（用于回填） ----------
track_ret = {
    'A股医药': -0.45,    # ETF均值（医疗ETF -0.59% / 医药ETF广发 -0.31%）；医药生物 -0.02% 平盘
    '大消费': -0.27,     # 中证消费 12,775.54 -0.27%（回调第1日尾盘收复）
    '恒生科技': -0.92,   # HSTECH 4,527.71 -0.92% 守住 4,500（盘中最低 4,509.38）
    '宏观': 0.07,        # 上证指数 3,932.70 +0.07%（深成指 +1.91%、创业板 +3.41%、成交1.95万亿缩量846亿）
    '其他/宽基': 0.95,   # 广联达 -0.56% / 通威 +2.46% 平均（§9/3 口径）
    # 美股标普医药: 美股 9/7 休市, 事件描述的非农压制即 XLV 9/4 反应 → 回填 -1.04 (XLV 9/4 最近收盘)
}
XLV_LATEST = -1.04  # XLV 9/4 收盘(美股 9/5-9/7 无交易)

def get_ret1d(e):
    v = e.get('actual_ret_1d')
    if v is None:
        v = e.get('reference', {}).get('actual_ret_1d')
    return v
def set_ret1d(e, v, ref_text):
    r = e.setdefault('reference', {})
    r['actual_ret_1d'] = v
    r['actual_date'] = TODAY
    r['ret_1d_ref'] = ref_text

# ---------- 1. 追加盘后 8 条事件（从 sentiment 差集） ----------
sent = json.load(open(os.path.join(BASE, 'data/processed/news/sentiment-2026-09-07.json'), encoding='utf-8'))
ev_path = os.path.join(EV, f'events-{TODAY}.json')
ev = json.load(open(ev_path, encoding='utf-8'))
existing_titles = set(e['title'] for e in ev)
new_events = []
for n in sent:
    if n['title'] in existing_titles:
        continue
    seq = len(ev) + len(new_events) + 1
    new_events.append({
        'id': f"N{TODAY.replace('-', '')}-{seq:03d}",
        'date': TODAY, 'track': n.get('track', '宏观'), 'category': '行业事件类',
        'title': n['title'], 'summary': n.get('comment', ''),
        'source': 'WebSearch', 'source_url': '',
        'sentiment': n.get('sentiment'), 'score': n.get('score'), 'strength': n.get('strength', n.get('score', 50)),
        'direction': n.get('direction'), 'volatility': n.get('volatility'),
        'reason': n.get('comment', ''),
        'reference': {'actual_ret_1d': None},
    })
ev.extend(new_events)
print(f'盘后新增事件 {len(new_events)} 条 -> 9/7 共 {len(ev)} 条')
for e in new_events:
    print(f'  {e["id"]} [{e["track"]}] {e["direction"]}{e["score"]} | {e["title"][:40]}')

# ---------- 2. 回填 9/7 全部事件 ----------
fix = 0
for x in ev:
    if get_ret1d(x) is not None:
        continue
    t = x.get('track')
    if t == '美股标普医药':
        set_ret1d(x, XLV_LATEST, 'XLV 9/4 -1.04%(美股9/7休市, 事件描述的非农压制即9/4反应)')
        fix += 1
    elif t in track_ret:
        set_ret1d(x, track_ret[t], '赛道指数/ETF收盘')
        fix += 1
json.dump(ev, open(ev_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(f'9/7 回填 {fix} 条')

# ---------- 3. 回填 9/6 周末 16 条（首个交易日 9/7 收盘） ----------
ev6_path = os.path.join(EV, 'events-2026-09-06.json')
ev6 = json.load(open(ev6_path, encoding='utf-8'))
fix6 = 0
for x in ev6:
    if get_ret1d(x) is not None:
        continue
    t = x.get('track')
    if t == '美股标普医药':
        set_ret1d(x, XLV_LATEST, 'XLV 9/4 -1.04%(周末美股医药事件, 用最近美股交易日收盘)')
        fix6 += 1
    elif t in track_ret:
        set_ret1d(x, track_ret[t], '首个交易日(9/7)赛道收盘')
        fix6 += 1
json.dump(ev6, open(ev6_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(f'9/6 回填 {fix6} 条')

# ---------- 4. 全库完整性扫描 ----------
all_ev = []
for p in sorted(glob.glob(os.path.join(EV, 'events-*.json'))):
    all_ev += json.load(open(p, encoding='utf-8'))
all_left = [x for x in all_ev if get_ret1d(x) is None]
print(f'\n全库共 {len(all_ev)} 条, 留空 {len(all_left)} 条')
for x in all_left:
    print(f'  {x["id"]} {x.get("date")} [{x.get("track")}]')

# ---------- 5. 1日样本统计 + 方向验证 ----------
samples = defaultdict(lambda: {'n': 0, 'rets': [], 'pos': 0, 'spos': 0, 'sneg': 0, 'spos_rets': [], 'sneg_rets': []})
direction_ok = 0
direction_total = 0
track_dv = defaultdict(lambda: [0, 0])
for e in all_ev:
    v = get_ret1d(e)
    if v is None:
        continue
    t = e.get('track', '?')
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
    # 方向验证: 仅 正面/负面 事件
    if senti not in ('正面', '负面'):
        continue
    direction_total += 1
    track_dv[t][1] += 1
    ok = (senti == '正面' and float(v) > 0) or (senti == '负面' and float(v) < 0)
    if ok:
        direction_ok += 1
        track_dv[t][0] += 1

out_stats = {}
print('\n=== 1日样本统计（截至 9/7 收盘） ===')
for t, s in sorted(samples.items()):
    if s['n'] == 0:
        continue
    rec = {
        'n': s['n'],
        'avg': round(sum(s['rets'])/len(s['rets']), 2),
        'worst': round(min(s['rets']), 2),
        'best': round(max(s['rets']), 2),
        'pos': round(s['pos']/s['n'], 2),
        'strong_pos_n': s['spos'],
        'strong_pos_avg': round(sum(s['spos_rets'])/len(s['spos_rets']), 2) if s['spos_rets'] else None,
        'strong_neg_n': s['sneg'],
        'strong_neg_avg': round(sum(s['sneg_rets'])/len(s['sneg_rets']), 2) if s['sneg_rets'] else None,
    }
    out_stats[t] = rec
    print(f"  {t}: n={rec['n']} avg={rec['avg']}% worst={rec['worst']} best={rec['best']} pos={rec['pos']} 强正{rec['strong_pos_n']}均值{rec['strong_pos_avg']} 强负{rec['strong_neg_n']}均值{rec['strong_neg_avg']}")

print(f"\n=== 方向验证（sentiment 口径） ===")
print(f'  全局 {direction_ok}/{direction_total} ({round(direction_ok/direction_total*100,1) if direction_total else 0}%)')
for t, (ok, tot) in sorted(track_dv.items(), key=lambda x: -x[1][0]):
    if tot > 0:
        print(f'  {t}: {ok}/{tot} ({round(ok/tot*100)}%)')

# ---------- 6. 3/5日窗口统计 ----------
import csv
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
for e in all_ev:
    d = e.get('date')
    t = e.get('track')
    if not d or t not in track_index:
        continue
    code = track_index[t][0]
    r3 = window_stats(d, code, 3)
    r5 = window_stats(d, code, 5)
    if r3 is not None:
        win3[t]['n'] += 1
        win3[t]['rets'].append(r3)
    if r5 is not None:
        win5[t]['n'] += 1
        win5[t]['rets'].append(r5)

def agg(w):
    out = {}
    for t, s in w.items():
        if s['n']:
            out[t] = {'n': s['n'], 'avg': round(sum(s['rets'])/len(s['rets']), 2)}
    return out
w3, w5 = agg(win3), agg(win5)
print('\n=== 3日窗口统计 ===')
for t, v in sorted(w3.items(), key=lambda x: -x[1]['avg']):
    print(f'  {t}: n={v["n"]} 均值 {v["avg"]}%')
print('=== 5日窗口统计 ===')
for t, v in sorted(w5.items(), key=lambda x: -x[1]['avg']):
    print(f'  {t}: n={v["n"]} 均值 {v["avg"]}%')

with open(os.path.join(BASE, 'data/processed/events/event_stats_20260907.json'), 'w', encoding='utf-8') as f:
    json.dump({
        'date': TODAY,
        'total_events': len(all_ev),
        'null_ret': len(all_left),
        'track_1d': out_stats,
        'direction': {'ok': direction_ok, 'total': direction_total,
                      'rate': round(direction_ok/direction_total*100, 1) if direction_total else None,
                      'by_track': {t: {'ok': v[0], 'total': v[1]} for t, v in track_dv.items()}},
        'win3': w3, 'win5': w5,
    }, f, ensure_ascii=False, indent=1)
print('\n已保存 event_stats_20260907.json')
