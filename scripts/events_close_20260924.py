# -*- coding: utf-8 -*-
"""2026-09-24 盘后档事件库处理：
  ① 追加盘后 22 条事件（过滤 window == '盘后(14:00-20:00)'，§3.88 空集硬守卫）
  ② 回填 9/24 全部留空事件（盘前 43 + 盘中 29 + 盘后 22）—— 参考交易日 = 9/24（§3.100 固定映射表）
     美股标普医药留空（XLV 9/24 未收盘 → T+1，§3.97⑤）
  ③ 全库完整性扫描 + 1日样本 + 方向验证（有效样本口径 §3.102/§3.103）+ 3/5/10日窗口 → event_stats_20260924_close.json
⚠️ A股医药 3/5/10 日窗口仍用 399006（创业板指）代理（000933 行数不足，§3.90 待办未清）
⚠️ windows 空列表除零守卫（§3.93）；全 None 不得聚合为 0.0（§3.104）
"""
import json, os, glob, csv
from collections import defaultdict

BASE = '/Users/jieyang/Documents/WealthHub'
EV = os.path.join(BASE, 'data/processed/events')
HIST = os.path.join(BASE, 'data/processed/history')
TODAY = '2026-09-24'
WIN = '盘后(14:00-20:00)'

track_ret = {
    '宏观': -1.22,       # 000001 上证指数 3,888.37 -1.22%
    'A股医药': -2.49,    # 000933 中证医药 7,750.44 -2.49%（中证医疗 -2.28% / 300医药 -2.42%）
    '大消费': -1.46,     # 000932 中证消费 12,109.54 -1.46%（中证白酒 -2.11%）
    '恒生科技': -0.41,   # HSTECH 4,361.13 -0.41%（恒生指数 24,761.13 -0.29%）
    '其他/宽基': -1.73,  # 000300 沪深300 4,439.14 -1.73%
}
REF = {
    '宏观': '9/24 收盘：000001 上证指数 3888.37 -1.22%（深成 -2.34% / 创业板指 -2.68%）',
    'A股医药': '9/24 收盘：000933 中证医药 7750.4444 -2.49%（中证医疗 6731.18 -2.28% / 300医药 8034.61 -2.42%）',
    '大消费': '9/24 收盘：000932 中证消费 12109.54 -1.46%（中证白酒 6105.76 -2.11%）',
    '恒生科技': '9/24 收盘：HSTECH 4361.13 -0.41%（恒生指数 24761.13 -0.29%）',
    '其他/宽基': '9/24 收盘：000300 沪深300 4439.14 -1.73%',
}
MAXVOL = {'低': 1.5, '中': 4.8, '高': 9.0}

# ---------- ① 追加盘后事件 ----------
news = json.load(open(os.path.join(BASE, 'data/processed/news/news-2026-09-24.json'), encoding='utf-8'))
sent = json.load(open(os.path.join(BASE, 'data/processed/news/sentiment-2026-09-24.json'), encoding='utf-8'))
items = sent['items'] if isinstance(sent, dict) else sent
ev_path = os.path.join(EV, f'events-{TODAY}.json')
ev = json.load(open(ev_path, encoding='utf-8'))
existing = {e['title'] for e in ev}

close_sent = [x for x in items if x.get('window') == WIN]
if not close_sent:
    raise SystemExit('⚠️ 盘后窗口 sentiment 为 0 条 → per-item `window` 缺失（§3.88/§3.103），终止以免静默跳过')


def find_news(t):
    return next((y for y in news if y['title'][:60] == t), None)


added = []
for x in close_sent:
    n = find_news(x['title'])
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
        'reason': n.get('brief', ''), 'window': WIN,
        'reference': {'ret_3d': None, 'ret_5d': None, 'ret_10d': None,
                      'max_vol': MAXVOL.get(n.get('volatility'), 4.8),
                      'confidence': n.get('confidence')},
    })
ev.extend(added)
json.dump(ev, open(ev_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(f'事件库 {TODAY} +{len(added)} 条 → {len(ev)} 条（已回写）')

# ---------- ② 回填 9/24 全部留空事件 ----------
filled, blank = 0, 0
blank_by_date, blank_by_track = defaultdict(int), defaultdict(int)
e2 = json.load(open(ev_path, encoding='utf-8'))
for e in e2:
    r = e.setdefault('reference', {})
    if r.get('actual_ret_1d') is not None:
        continue
    t = e['track']
    if t in track_ret:
        r['actual_ret_1d'] = track_ret[t]
        r['actual_date'] = TODAY
        r['ret_1d_ref'] = REF[t]
        filled += 1
    else:
        blank += 1
        blank_by_date[e['date']] += 1
        blank_by_track[t] += 1
json.dump(e2, open(ev_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(f'9/24 回填 {filled} 条；留空 {blank} 条 按日={dict(blank_by_date)} 按赛道={dict(blank_by_track)}')

# ---------- ③ 全库完整性扫描 ----------
files = sorted(glob.glob(os.path.join(EV, 'events-*.json')))
all_ev = []
for f in files:
    all_ev.extend(json.load(open(f, encoding='utf-8')))
n_blank = sum(1 for e in all_ev if e.get('reference', {}).get('actual_ret_1d') is None)
bl = [e for e in all_ev if e.get('reference', {}).get('actual_ret_1d') is None]
print(f'\n全库 {len(all_ev)} 条 / {len(files)} 日；留空 {n_blank} 条')
print(f'  留空按赛道 {dict(defaultdict(int, {t: sum(1 for e in bl if e["track"] == t) for t in {e["track"] for e in bl}}))}')
print(f'  当日(9/24)新增事件 {sum(1 for e in all_ev if e["date"] == TODAY)} 条')

# ---------- ④ 统计 ----------
idx = defaultdict(dict)
with open(os.path.join(HIST, 'indices.csv'), encoding='utf-8-sig') as fh:
    for row in csv.DictReader(fh):
        try:
            idx[row['code']][row['date']] = float(row['close'])
        except Exception:
            pass
track_index = {'A股医药': '399006', '大消费': '000932', '恒生科技': 'HSTECH',
               '美股标普医药': 'XLV', '其他/宽基': '000300'}


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


win = defaultdict(lambda: defaultdict(list))
win_unavail = defaultdict(lambda: defaultdict(int))
for e in all_ev:
    t = e['track']
    code = track_index.get(t)
    if not code:
        continue
    for n in (3, 5, 10):
        x = fwd(code, e['date'], n)
        if x is not None:
            win[t][n].append(x)
        else:
            win_unavail[t][n] += 1

# 方向验证（有效样本口径：actual_date == TODAY）
tot = pos = neg = 0
p_hit = n_hit = 0
p_tot = n_tot = 0
for e in all_ev:
    r = e.get('reference', {})
    if r.get('actual_date') != TODAY or r.get('actual_ret_1d') is None:
        continue
    v, d = r['actual_ret_1d'], e.get('direction')
    tot += 1
    if d == '利多':
        p_tot += 1
        p_hit += 1 if v > 0 else 0
    elif d == '利空':
        n_tot += 1
        n_hit += 1 if v < 0 else 0
print(f'\n方向验证（有效样本 = actual_date=={TODAY}）: {p_hit + n_hit}/{tot} '
      f'({(p_hit + n_hit) / tot * 100:.1f}%)  利多 {p_hit}/{p_tot}  利空 {n_hit}/{n_tot}'
      if tot else '无有效样本')
print(f'  当日全部事件 {sum(1 for e in all_ev if e["date"] == TODAY)} 条（有效样本 {tot} / 全部当日）')

# 暴露加权净情绪分（§3.101/§3.104）
pf = json.load(open(os.path.join(HIST, 'portfolio_close_20260924.json'), encoding='utf-8'))
w = {k: v['pct_of_total'] / 100 for k, v in pf['tracks'].items() if k != '现金'}
net = defaultdict(float)
for e in all_ev:
    if e['date'] != TODAY:
        continue
    s = e.get('strength') or 0
    sg = 1 if e.get('direction') == '利多' else (-1 if e.get('direction') == '利空' else 0)
    net[e['track']] += s * sg
print('\n各赛道净情绪分（9/24 全部事件）:')
weighted = 0.0
for t, v in sorted(net.items(), key=lambda kv: -kv[1]):
    ww = w.get(t)
    print(f"  {t:8s} 净分={v:+7.1f}  暴露权重={'n/a' if ww is None else f'{ww*100:.2f}%'}"
          f"{'' if ww is None else f'  加权={v*ww:+.2f}'}")
    if ww is not None:
        weighted += v * ww
print(f'  → 名义净分合计 {sum(net.values()):+.1f}；按赛道暴露加权后 {weighted:+.2f}')

out = {'date': TODAY, 'as_of': '2026-09-24收盘',
       'events_added': len(added), 'events_backfilled': filled, 'blank': blank,
       'blank_by_date': dict(blank_by_date), 'blank_by_track': dict(blank_by_track),
       'total_events': len(all_ev), 'total_days': len(files),
       'direction_check': {'hit': p_hit + n_hit, 'total': tot,
                           'pct': round((p_hit + n_hit) / tot * 100, 1) if tot else None,
                           'pos_hit': p_hit, 'pos_total': p_tot,
                           'neg_hit': n_hit, 'neg_total': n_tot},
       'net_sentiment_by_track': {k: round(v, 2) for k, v in net.items()},
       'exposure_weighted_net': round(weighted, 2),
       'window_avg': {t: {str(n): (round(sum(v) / len(v), 4) if v else None) for n, v in d.items()}
                      for t, d in win.items()},
       'window_unavailable': {t: {str(n): c for n, c in d.items()} for t, d in win_unavail.items()
                              if sum(d.values())},
       }
json.dump(out, open(os.path.join(HIST, f'event_stats_{TODAY.replace("-", "")}_close.json'), 'w',
                    encoding='utf-8'), ensure_ascii=False, indent=1)

print('\n3/5/10 日窗口历史均值（含窗口不可用计数）:')
for t in sorted(win):
    s = '  '.join(f"{n}日={(sum(win[t][n]) / len(win[t][n])):+.2f}%(n={len(win[t][n])})" if win[t][n] else f'{n}日=n/a'
                  for n in (3, 5, 10))
    u = ' '.join(f'{n}日不可用={win_unavail[t][n]}' for n in (3, 5, 10) if win_unavail[t][n])
    print(f'  {t:8s} {s}   {u}')
print(f'\n已保存 event_stats_{TODAY.replace("-", "")}_close.json')
