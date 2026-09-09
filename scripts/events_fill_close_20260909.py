# -*- coding: utf-8 -*-
"""盘后档 2026-09-09：①追加盘后 8 条事件(id 024-031) ②回填 9/9 全部事件 actual_ret_1d
③全库完整性扫描 ④1日样本+方向验证 ⑤3/5日窗口统计"""
import json, os, glob, csv
from collections import defaultdict

BASE = '/Users/jieyang/Documents/WealthHub'
EV = os.path.join(BASE, 'data/processed/events')
TODAY = '2026-09-09'

# ---------- 9/9 各赛道实际收盘走势（用于回填） ----------
track_ret = {
    'A股医药': -1.21,    # ETF均值（医疗ETF -1.17% / 医药ETF广发 -1.24%）；创新药概念 -1.31%
    '大消费': -0.56,     # 中证消费 12,704.26 -0.56%（回调第1日守 12,600）
    '恒生科技': -0.76,   # HSTECH 4,420.79 -0.76%（破 4,500 第 2 日）
    '宏观': 0.28,        # 上证指数 3,951.51 +0.28%（煤炭/航运领涨，缩量 1.86 万亿）
    '其他/宽基': -2.44,  # 个股均值（广联达 -3.61% / 通威 -1.26%）；传媒ETF -2.76%
    # 美股标普医药: 9/9 美股交易日未收盘（北京 9/9 晚开盘），事件待 9/10 用 XLV 回填
}

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

# ---------- 1. 追加盘后 8 条事件（从 sentiment 差集, 补 track） ----------
sent = json.load(open(os.path.join(BASE, 'data/processed/news/sentiment-2026-09-09.json'), encoding='utf-8'))
ev_path = os.path.join(EV, f'events-{TODAY}.json')
ev = json.load(open(ev_path, encoding='utf-8'))
existing_titles = set(e['title'] for e in ev)

# track 归类（标题前缀, 与 build_intraday TRACK_MAP 同源 §3.64 防御式补齐）
TRACK_MAP = {
    "A股收评": "宏观", "港股收评": "恒生科技", "A股医药收盘": "A股医药",
    "港股创新药大跌收盘": "A股医药", "恒生科技收盘": "恒生科技",
    "茅台收盘": "大消费", "中证消费收盘": "大消费", "创新药出海BD延续": "A股医药",
}
def get_track(title):
    for k, v in TRACK_MAP.items():
        if title.startswith(k):
            return v
    return "其他/宽基"

new_events = []
for n in sent:
    if n['title'] in existing_titles:
        continue
    seq = len(ev) + len(new_events) + 1
    new_events.append({
        'id': f"N{TODAY.replace('-', '')}-{seq:03d}",
        'date': TODAY, 'track': get_track(n['title']), 'category': n.get('category', '行业事件类'),
        'title': n['title'], 'summary': n.get('summary', n.get('comment', '')),
        'source': n.get('source', 'WebSearch'), 'source_url': n.get('source_url', ''),
        'sentiment': n.get('sentiment'), 'score': n.get('score'), 'strength': n.get('strength', n.get('score', 50)),
        'direction': n.get('direction'), 'volatility': n.get('volatility'),
        'reason': n.get('reason', n.get('comment', '')),
        'reference': {'actual_ret_1d': None},
    })
ev.extend(new_events)
print(f'盘后新增事件 {len(new_events)} 条 -> 9/9 共 {len(ev)} 条')
for e in new_events:
    print(f'  {e["id"]} [{e["track"]}] {e.get("direction")}{e.get("score")} | {e["title"][:40]}')

# ---------- 1.5 回补 ev 中 sentiment/score/strength 缺失（从 sentiment 文件按标题） ----------
sent_by_title = {s['title']: s for s in sent}
fix_field = 0
for x in ev:
    s = sent_by_title.get(x['title'])
    if not s:
        continue
    for fld in ('sentiment', 'score', 'strength', 'direction', 'volatility', 'reason'):
        if not x.get(fld):
            x[fld] = s.get(fld, x.get(fld))
            if fld in ('sentiment', 'direction', 'volatility') or fld == 'score':
                fix_field += 1
print(f'回补 sentiment 字段 {fix_field} 处')

# ---------- 2. 回填 9/9 全部事件（美股标普医药留空待 9/10 XLV） ----------
fix = 0
for x in ev:
    if get_ret1d(x) is not None:
        continue
    t = x.get('track')
    if t == '美股标普医药':
        continue  # 美股 9/9 交易日未收盘，9/10 盘前用 XLV 回填
    if t in track_ret:
        set_ret1d(x, track_ret[t], '9/9赛道收盘(ETF均值/指数/个股均值)')
        fix += 1
json.dump(ev, open(ev_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(f'9/9 回填 {fix} 条 (美股标普医药留空待明日 XLV)')

# ---------- 3. 全库完整性扫描 ----------
all_ev = []
for p in sorted(glob.glob(os.path.join(EV, 'events-*.json'))):
    all_ev += json.load(open(p, encoding='utf-8'))
all_left = [x for x in all_ev if get_ret1d(x) is None]
print(f'\n全库共 {len(all_ev)} 条, 留空 {len(all_left)} 条')
for x in all_left:
    print(f'  {x["id"]} {x.get("date")} [{x.get("track")}]')

# ---------- 4. 1日样本统计 + 方向验证 ----------
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
    if senti not in ('正面', '负面'):
        continue
    direction_total += 1
    track_dv[t][1] += 1
    ok = (senti == '正面' and float(v) > 0) or (senti == '负面' and float(v) < 0)
    if ok:
        direction_ok += 1
        track_dv[t][0] += 1

out_stats = {}
print('\n=== 1日样本统计（截至 9/9 收盘） ===')
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

print(f"\n=== 方向验证（sentiment 口径） ===")
print(f'  全局 {direction_ok}/{direction_total} ({round(direction_ok/direction_total*100,1) if direction_total else 0}%)')
for t, (ok, tot) in sorted(track_dv.items(), key=lambda x: -x[1][0]):
    if tot > 0:
        print(f'  {t}: {ok}/{tot} ({round(ok/tot*100)}%)')

# ---------- 5. 3/5日窗口统计 ----------
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
print('\n=== 3日窗口统计 ===')
for t, v in sorted(w3.items(), key=lambda x: -x[1]['avg']):
    print(f'  {t}: n={v["n"]} 均值 {v["avg"]}%')
print('=== 5日窗口统计 ===')
for t, v in sorted(w5.items(), key=lambda x: -x[1]['avg']):
    print(f'  {t}: n={v["n"]} 均值 {v["avg"]}%')
print('=== 10日窗口统计 ===')
for t, v in sorted(w10.items(), key=lambda x: -x[1]['avg']):
    print(f'  {t}: n={v["n"]} 均值 {v["avg"]}%')

with open(os.path.join(EV, f'event_stats_{TODAY.replace("-", "")}.json'), 'w', encoding='utf-8') as f:
    json.dump({
        'date': TODAY,
        'total_events': len(all_ev),
        'null_ret': len(all_left),
        'track_1d': out_stats,
        'direction': {'ok': direction_ok, 'total': direction_total,
                      'rate': round(direction_ok/direction_total*100, 1) if direction_total else None,
                      'by_track': {t: {'ok': v[0], 'total': v[1]} for t, v in track_dv.items()}},
        'win3': w3, 'win5': w5, 'win10': w10,
    }, f, ensure_ascii=False, indent=1)
print(f'\n已保存 event_stats_{TODAY.replace("-", "")}.json')
