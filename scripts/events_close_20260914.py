# -*- coding: utf-8 -*-
"""2026-09-14 盘后档事件库处理：
  ① 追加盘后 11 条事件（N20260914-051~061）
  ② 回填 9/13 周末 19 条 + 9/14 当日 61 条 actual_ret_1d
  ③ 全库完整性扫描
  ④ 1日样本 + 方向验证 + 3/5/10日窗口统计 → event_stats_20260914.json（收盘口径，覆盖盘前版）
"""
import json, os, glob, csv, re, shutil
from collections import defaultdict

BASE = '/Users/jieyang/Documents/WealthHub'
EV = os.path.join(BASE, 'data/processed/events')
HIST = os.path.join(BASE, 'data/processed/history')
TODAY = '2026-09-14'
PREV = '2026-09-13'

# ---------- 9/14 各赛道实际收盘走势 ----------
track_ret_0914 = {
    'A股医药': 2.29,     # ETF均值（医疗ETF +2.14% / 医药ETF广发 +2.43%）；申万医药生物 +2.22%
    '大消费': -0.21,     # 中证消费 12,324.03 -0.21%（守 12,300、未收复 12,400）
    '恒生科技': -0.06,   # HSTECH 4,317.94 -0.06%
    '宏观': -0.07,       # 上证指数 3,885.33 -0.07%
    '其他/宽基': 1.61,   # 个股均值（广联达 +1.22% / 通威 +1.99%）；证券ETF -0.57% / 传媒ETF -1.34%
}
# 9/13 周末事件：美股标普医药按 §3.65/§3.67 取最近美股交易日 XLV 9/11 收盘
track_ret_0913 = dict(track_ret_0914)
track_ret_0913['美股标普医药'] = -0.18   # XLV 9/11 -0.18%（IYH -0.11%）

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

# ---------- ① 追加盘后 11 条事件 ----------
news = json.load(open(os.path.join(BASE, 'data/processed/news/news-2026-09-14.json'), encoding='utf-8'))
sent = json.load(open(os.path.join(BASE, 'data/processed/news/sentiment-2026-09-14.json'), encoding='utf-8'))
ev_path = os.path.join(EV, f'events-{TODAY}.json')
ev = json.load(open(ev_path, encoding='utf-8'))
existing = set(e['title'] for e in ev)

close_sent = [x for x in sent['items'] if x.get('window') == '盘后(13:30-20:00)']
print(f'盘后待入库事件 {len(close_sent)} 条')
added = []
for x in close_sent:
    n = next((y for y in news if y['title'][:60] == x['title']), None)
    if n is None or n['title'] in existing:
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
        'reference': {'ret_3d': None, 'ret_5d': None, 'ret_10d': None, 'max_vol': None,
                      'confidence': x.get('confidence'), 'actual_ret_1d': None,
                      'actual_date': None, 'ret_1d_ref': None},
    })
ev.extend(added)
print(f'新增 {len(added)} 条 → 9/14 共 {len(ev)} 条')

# ---------- ② 回填 ----------
# 9/13 周末 19 条
ev13_path = os.path.join(EV, f'events-{PREV}.json')
ev13 = json.load(open(ev13_path, encoding='utf-8'))
f13 = 0
for e in ev13:
    t = e['track']
    v = track_ret_0913.get(t)
    if v is None:
        set_ret1d(e, None, '待 2026-09-15 用 XLV 9/14 收盘回填（美股 9/14 未收盘）')
        continue
    ref = (f"9/14 收盘回填（周末事件取次一交易日；{'美股标普医药取最近美股交易日 XLV 9/11' if t == '美股标普医药' else 'A股/港股当日收盘'}）")
    set_ret1d(e, v, ref); f13 += 1
json.dump(ev13, open(ev13_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(f'9/13 周末回填 {f13}/{len(ev13)} 条')

# 9/14 当日 61 条
f14 = 0
for e in ev:
    t = e['track']
    v = track_ret_0914.get(t)
    if v is None:
        set_ret1d(e, None, '待 2026-09-15 用 XLV 9/14 收盘回填（美股 9/14 未收盘）')
        continue
    set_ret1d(e, v, '9/14 收盘回填（A股/港股当日收盘口径）'); f14 += 1
json.dump(ev, open(ev_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(f'9/14 回填 {f14}/{len(ev)} 条')

# ---------- ③ 全库扫描 ----------
all_ev = []
for p in sorted(glob.glob(os.path.join(EV, 'events-*.json'))):
    all_ev.extend(json.load(open(p, encoding='utf-8')))
blank = [e for e in all_ev if get_ret1d(e) is None]
print(f'\n全库 {len(all_ev)} 条，留空 {len(blank)} 条')
for e in blank:
    print(f"  留空 {e['id']} {e['track']} {e['title'][:50]}")

# ---------- ④ 统计 ----------
samples = defaultdict(lambda: {'n': 0, 'rets': [], 'pos': 0, 'spos': 0, 'spos_rets': [], 'sneg': 0, 'sneg_rets': []})
direction_total = direction_ok = 0
track_dv = defaultdict(lambda: [0, 0])
for e in all_ev:
    t = e.get('track', '?'); v = get_ret1d(e)
    if v is None:
        continue
    s = samples[t]; s['n'] += 1; s['rets'].append(float(v))
    if float(v) > 0:
        s['pos'] += 1
    senti = e.get('sentiment')
    try:
        score = int(e.get('score'))
    except Exception:
        score = None
    if senti == '正面' and score is not None and score >= 65:
        s['spos'] += 1; s['spos_rets'].append(float(v))
    if senti == '负面' and score is not None and score <= 40:
        s['sneg'] += 1; s['sneg_rets'].append(float(v))
    if senti not in ('正面', '负面'):
        continue
    direction_total += 1; track_dv[t][1] += 1
    if (senti == '正面' and float(v) > 0) or (senti == '负面' and float(v) < 0):
        direction_ok += 1; track_dv[t][0] += 1

out_stats = {}
print('\n=== 1日样本统计（截至 9/14 收盘回填） ===')
for t, s in sorted(samples.items()):
    if s['n'] == 0:
        continue
    rec = {'n': s['n'], 'avg': round(sum(s['rets']) / len(s['rets']), 2),
           'worst': round(min(s['rets']), 2), 'best': round(max(s['rets']), 2),
           'pos': round(s['pos'] / s['n'], 2),
           'strong_pos_n': s['spos'],
           'strong_pos_avg': round(sum(s['spos_rets']) / len(s['spos_rets']), 2) if s['spos_rets'] else None,
           'strong_neg_n': s['sneg'],
           'strong_neg_avg': round(sum(s['sneg_rets']) / len(s['sneg_rets']), 2) if s['sneg_rets'] else None}
    out_stats[t] = rec
    print(f"  {t}: n={rec['n']} avg={rec['avg']}% worst={rec['worst']} best={rec['best']} pos={rec['pos']} "
          f"强正{rec['strong_pos_n']}均值{rec['strong_pos_avg']} 强负{rec['strong_neg_n']}均值{rec['strong_neg_avg']}")

print('\n=== 方向验证（sentiment 口径, 中性剔除） ===')
print(f'  全局 {direction_ok}/{direction_total} ({round(direction_ok/direction_total*100,1) if direction_total else 0}%)')
for t, (ok, tot) in sorted(track_dv.items(), key=lambda x: -x[1][1]):
    if tot > 0:
        print(f'  {t}: {ok}/{tot} ({round(ok/tot*100)}%)')

# 当日方向验证（9/14 事件）
d_today = [[0, 0] for _ in range(2)]
today_ok = today_tot = 0
for e in ev:
    senti = e.get('sentiment'); v = get_ret1d(e)
    if senti not in ('正面', '负面') or v is None:
        continue
    today_tot += 1
    if (senti == '正面' and v > 0) or (senti == '负面' and v < 0):
        today_ok += 1
print(f'\n=== 9/14 当日方向验证: {today_ok}/{today_tot} ===')
for senti in ('正面', '负面'):
    sub = [e for e in ev if e.get('sentiment') == senti and get_ret1d(e) is not None]
    ok = sum(1 for e in sub if (senti == '正面' and get_ret1d(e) > 0) or (senti == '负面' and get_ret1d(e) < 0))
    print(f'  {senti}: {ok}/{len(sub)}')

# ---------- 3/5/10 日窗口 ----------
idx_rows = list(csv.reader(open(os.path.join(HIST, 'indices.csv'), encoding='utf-8-sig')))
track_index = {'A股医药': '399006', '大消费': '000932', '恒生科技': 'HSTECH',
               '宏观': '000001', '美股标普医药': 'XLV'}

def build_series(code):
    seen = {}
    for r in idx_rows:
        if not r or len(r) < 6 or r[3] != code or r[1] == '':
            continue
        try:
            c = float(r[4])
        except Exception:
            continue
        d = r[1][:10]
        seen[d] = c
    ds = sorted(seen.items())
    return [d for d, _ in ds], [c for _, c in ds]

def window_stats(ev_date, code, n_days):
    dates, closes = build_series(code)
    if not dates or ev_date not in dates:
        return None
    i0 = dates.index(ev_date); ret = 1.0; cnt = 0
    for i in range(i0 + 1, len(dates)):
        if cnt >= n_days:
            break
        if closes[i] is None or closes[i - 1] in (None, 0):
            continue
        ret *= closes[i] / closes[i - 1]; cnt += 1
    if cnt < n_days:
        return None
    return (ret - 1) * 100

win3 = defaultdict(lambda: {'n': 0, 'rets': []})
win5 = defaultdict(lambda: {'n': 0, 'rets': []})
win10 = defaultdict(lambda: {'n': 0, 'rets': []})
for e in all_ev:
    d, t = e.get('date'), e.get('track')
    if not d or t not in track_index:
        continue
    code = track_index[t]
    for wd, store in [(3, win3), (5, win5), (10, win10)]:
        r = window_stats(d, code, wd)
        if r is not None:
            store[t]['n'] += 1; store[t]['rets'].append(r)

def agg(w):
    return {t: {'n': s['n'], 'avg': round(sum(s['rets']) / len(s['rets']), 2)}
            for t, s in w.items() if s['n']}
w3, w5, w10 = agg(win3), agg(win5), agg(win10)
for nm, w in (('3日', w3), ('5日', w5), ('10日', w10)):
    print(f'\n=== {nm}窗口统计(事件后) ===')
    for t, v in sorted(w.items(), key=lambda x: -x[1]['avg']):
        print(f'  {t}: n={v["n"]} 均值 {v["avg"]}%')

out = {'date': TODAY, 'as_of': '2026-09-14收盘回填',
       'library_total': len(all_ev), 'library_blank': len(blank),
       'sample_stats': out_stats,
       'direction': {'ok': direction_ok, 'total': direction_total,
                     'pct': round(direction_ok / direction_total * 100, 1) if direction_total else 0,
                     'by_track': {t: {'ok': v[0], 'total': v[1]} for t, v in track_dv.items() if v[1] > 0}},
       'today_direction': {'ok': today_ok, 'total': today_tot},
       'win3': w3, 'win5': w5, 'win10': w10}
p_ev = os.path.join(EV, 'event_stats_20260914.json')
json.dump(out, open(p_ev, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
shutil.copy(p_ev, os.path.join(HIST, 'event_stats_20260914.json'))
print(f'\n已保存 {p_ev} 与 history/ 副本')
