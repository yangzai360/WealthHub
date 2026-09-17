# -*- coding: utf-8 -*-
"""2026-09-17 盘后档事件库处理：
  ① 追加盘后 20 条事件（过滤条件 window == '盘后(14:00-20:00)'，含 §3.88 空集硬守卫）
  ② 回填 9/17 当日 54 条 actual_ret_1d（美股标普医药留空，待 9/18 盘前档兜底）
  ③ 全库完整性扫描
  ④ 1日样本 + 方向验证 + 3/5/10日窗口统计 → history/event_stats_20260917.json（收盘口径覆盖）
统计口径与 scripts/event_stats_20260917.py（盘前档）保持一致。
⚠️ 已知口径问题：A股医药 3/5/10 日窗口序列实际使用 399006（创业板指）作代理
   （indices.csv 中 000933 中证医药仅有 9/15 起 3 行，无足够历史），报告须显式披露。
"""
import json, os, glob, csv, re
from collections import defaultdict

BASE = '/Users/jieyang/Documents/WealthHub'
EV = os.path.join(BASE, 'data/processed/events')
HIST = os.path.join(BASE, 'data/processed/history')
TODAY = '2026-09-17'
WIN = '盘后(14:00-20:00)'

track_ret = {
    'A股医药': 0.38,     # ETF均值（医药ETF广发 +0.16% / 医疗ETF +0.60%）；申万医药生物 +0.61%
    '大消费': 0.09,      # 中证消费 12,162.26 +0.09%（仍处 12,200 下方）
    '恒生科技': -0.34,   # HSTECH 4,310.74 -0.34%
    '宏观': -0.41,       # 上证指数 3,875.60 -0.41%
    '其他/宽基': -0.36,  # 个股均值（广联达 +0.36% / 通威 -1.07%）
    # 美股标普医药：9/17 美股未收盘 → 留空待 9/18 盘前档兜底（§3.70）
}
REF = {
    'A股医药': '9/17 收盘：医药ETF广发 +0.16% / 医疗ETF +0.60%（申万医药生物 +0.61%）',
    '大消费': '9/17 收盘：中证消费 12,162.26 +0.09%',
    '恒生科技': '9/17 收盘：HSTECH 4,310.74 -0.34%',
    '宏观': '9/17 收盘：上证指数 3,875.60 -0.41%',
    '其他/宽基': '9/17 收盘：个股均值（广联达 +0.36% / 通威 -1.07%）',
}

# ---------- ① 追加盘后事件 ----------
news = json.load(open(os.path.join(BASE, 'data/processed/news/news-2026-09-17.json'), encoding='utf-8'))
sent = json.load(open(os.path.join(BASE, 'data/processed/news/sentiment-2026-09-17.json'), encoding='utf-8'))
ev_path = os.path.join(EV, f'events-{TODAY}.json')
ev = json.load(open(ev_path, encoding='utf-8'))
existing = {e['title'] for e in ev}

close_sent = [x for x in sent['items'] if x.get('window') == WIN]
if not close_sent:
    raise SystemExit('⚠️ 盘后窗口 sentiment 为 0 条 → per-item `window` 字段可能缺失（§3.88），终止以免静默跳过事件入库')
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
        'reference': {'ret_3d': None, 'ret_5d': None, 'ret_10d': None,
                      'max_vol': {'低': 1.5, '中': 4.8, '高': 9.0}.get(n.get('volatility'), 4.8),
                      'confidence': n.get('confidence')},
    })
ev.extend(added)
print(f'事件库 {TODAY} +{len(added)} 条 → {len(ev)} 条')

# ---------- ② 回填 ----------
filled, blank = 0, 0
for e in ev:
    t = e['track']
    r = e.setdefault('reference', {})
    if t in track_ret:
        r['actual_ret_1d'] = track_ret[t]
        r['actual_date'] = TODAY
        r['ret_1d_ref'] = REF[t]
        filled += 1
    else:
        blank += 1
json.dump(ev, open(ev_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(f'回填 {filled} 条；留空 {blank} 条（美股标普医药，待 9/18 盘前档按 XLV 9/17 收盘兜底）')

# ---------- ③ 全库完整性 ----------
left, tot = [], 0
for p in sorted(glob.glob(os.path.join(EV, 'events-*.json'))):
    for e in json.load(open(p, encoding='utf-8')):
        tot += 1
        if e.get('reference', {}).get('actual_ret_1d') is None:
            left.append(e['id'])
print(f'全库 {tot} 条，留空 {len(left)} 条 {left[:12]}')

# ---------- ④ 统计 ----------
def get_ret1d(e):
    v = e.get('actual_ret_1d')
    if v is None:
        v = e.get('reference', {}).get('actual_ret_1d')
    return v


all_ev = []
for p in sorted(glob.glob(os.path.join(EV, 'events-*.json'))):
    all_ev.extend(json.load(open(p, encoding='utf-8')))
hist_ev = [e for e in all_ev if e.get('date') != TODAY]
print(f'历史样本（排除当日）{len(hist_ev)} 条')

samples = defaultdict(lambda: {'n': 0, 'rets': [], 'pos': 0, 'spos_rets': [], 'sneg_rets': []})
direction_total = direction_ok = 0
track_dv = defaultdict(lambda: [0, 0])
for e in hist_ev:
    t = e.get('track', '?')
    v = get_ret1d(e)
    if v is None:
        continue
    s = samples[t]
    s['n'] += 1; s['rets'].append(float(v))
    if float(v) > 0:
        s['pos'] += 1
    senti = e.get('sentiment')
    try:
        score = int(e.get('score'))
    except Exception:
        score = None
    if senti == '正面' and score is not None and score >= 65:
        s['spos_rets'].append(float(v))
    if senti == '负面' and score is not None and score <= 40:
        s['sneg_rets'].append(float(v))
    if senti not in ('正面', '负面'):
        continue
    direction_total += 1
    track_dv[t][1] += 1
    if (senti == '正面' and float(v) > 0) or (senti == '负面' and float(v) < 0):
        direction_ok += 1
        track_dv[t][0] += 1

S = {}
for t, s in sorted(samples.items()):
    if s['n'] == 0:
        continue
    S[t] = {'n': s['n'], 'avg': round(sum(s['rets']) / len(s['rets']), 2),
            'worst': round(min(s['rets']), 2), 'best': round(max(s['rets']), 2),
            'pos': round(s['pos'] / s['n'], 2),
            'strong_pos_n': len(s['spos_rets']),
            'strong_pos_avg': round(sum(s['spos_rets']) / len(s['spos_rets']), 2) if s['spos_rets'] else None,
            'strong_neg_n': len(s['sneg_rets']),
            'strong_neg_avg': round(sum(s['sneg_rets']) / len(s['sneg_rets']), 2) if s['sneg_rets'] else None}

tday = [0, 0]
tday_dir = defaultdict(lambda: [0, 0])
for e in ev:
    v = get_ret1d(e)
    d = e.get('direction')
    if v is None or d not in ('利多', '利空'):
        continue
    tday[1] += 1
    tday_dir[d][1] += 1
    if (d == '利多' and float(v) > 0) or (d == '利空' and float(v) < 0):
        tday[0] += 1
        tday_dir[d][0] += 1

# ---------- 3/5/10 日窗口 ----------
idx_rows = list(csv.reader(open(os.path.join(HIST, 'indices.csv'), encoding='utf-8-sig')))
track_index = {'A股医药': '399006', '大消费': '000932', '恒生科技': 'HSTECH',
               '宏观': '000001', '美股标普医药': 'XLV'}


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


SER = {t: build_series(c) for t, c in track_index.items()}


def window_stats(ev_date, code, n_days):
    dates, closes = SER[[k for k, v in track_index.items() if v == code][0]]
    if not dates or ev_date not in dates:
        return None
    i0 = dates.index(ev_date)
    ret, cnt = 1.0, 0
    for i in range(i0 + 1, len(dates)):
        if cnt >= n_days:
            break
        if closes[i] is None or closes[i - 1] in (None, 0):
            continue
        ret *= closes[i] / closes[i - 1]
        cnt += 1
    return (ret - 1) * 100 if cnt >= n_days else None


W = {}
for wd in (3, 5, 10):
    store = defaultdict(lambda: {'n': 0, 'rets': []})
    for e in all_ev:
        d, t = e.get('date'), e.get('track')
        if not d or t not in track_index:
            continue
        r = window_stats(d, track_index[t], wd)
        if r is not None:
            store[t]['n'] += 1; store[t]['rets'].append(r)
    W[wd] = {t: {'n': s['n'], 'avg': round(sum(s['rets']) / len(s['rets']), 2)}
             for t, s in store.items() if s['n']}

out = {'date': TODAY, 'as_of': '2026-09-17收盘回填', 'library_total': len(all_ev),
       'library_blank': len(left), 'sample_stats': S,
       'direction': {'ok': direction_ok, 'total': direction_total,
                     'pct': round(direction_ok / direction_total * 100, 1) if direction_total else 0,
                     'by_track': {t: {'ok': v[0], 'total': v[1]} for t, v in track_dv.items() if v[1] > 0}},
       'today_direction': {'ok': tday[0], 'total': tday[1],
                           'by_dir': {d: {'ok': v[0], 'tot': v[1]} for d, v in tday_dir.items()}},
       'win3': W[3], 'win5': W[5], 'win10': W[10]}
json.dump(out, open(os.path.join(HIST, f'event_stats_{TODAY.replace("-", "")}.json'), 'w',
                    encoding='utf-8'), ensure_ascii=False, indent=1)

print('\n1 日样本:')
for k, v in S.items():
    print(f"  {k:8s} n={v['n']:>4d} avg={v['avg']:+.2f}% worst={v['worst']}% best={v['best']}% pos={v['pos']} | 强正面 {v['strong_pos_avg']}%(n={v['strong_pos_n']}) 强负面 {v['strong_neg_avg']}%(n={v['strong_neg_n']})")
print(f"\n方向验证 全局 {direction_ok}/{direction_total} ({round(direction_ok/direction_total*100,1)}%)")
for k, v in sorted(track_dv.items(), key=lambda kv: -(kv[1][0] / max(kv[1][1], 1))):
    print(f"  {k:8s} {v[0]}/{v[1]} ({round(v[0]/max(v[1],1)*100)}%)")
print(f"当日 {tday[0]}/{tday[1]} ({round(tday[0]/max(tday[1],1)*100)}%)  " +
      ' / '.join(f"{d} {v[0]}/{v[1]}" for d, v in tday_dir.items()))
print('\n3/5/10 日窗口:')
for wd in (3, 5, 10):
    print(f"  {wd}日:", {k: (v['avg'], v['n']) for k, v in W[wd].items()})
