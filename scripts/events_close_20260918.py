# -*- coding: utf-8 -*-
"""2026-09-18 盘后档事件库处理：
  ① 追加盘后 14 条事件（过滤条件 window == '盘后(14:00-20:00)'，含 §3.88 空集硬守卫）
  ② 回填 9/18 当日 57 条 actual_ret_1d（美股标普医药留空，待 9/21 盘前档兜底）
  ③ 全库完整性扫描
  ④ 1日样本 + 方向验证 + 3/5/10日窗口统计 → history/event_stats_20260918_close.json（收盘口径覆盖）
统计口径与 scripts/event_stats_20260918.py（盘前档）保持一致。
⚠️ 已知口径问题：A股医药 3/5/10 日窗口序列实际使用 399006（创业板指）作代理
   （indices.csv 中 000933 中证医药仅 9/15 起 4 行，无足够历史），报告须显式披露。
"""
import json, os, glob, csv, re
from collections import defaultdict

BASE = '/Users/jieyang/Documents/WealthHub'
EV = os.path.join(BASE, 'data/processed/events')
HIST = os.path.join(BASE, 'data/processed/history')
TODAY = '2026-09-18'
WIN = '盘后(14:00-20:00)'

track_ret = {
    'A股医药': 0.76,     # ETF均值（医药ETF广发 +0.63% / 医疗ETF +0.89%）；中证医药 +0.50% / 中证医疗 +0.82%
    '大消费': 0.43,      # 中证消费 12,214.41 +0.43%（收复 12,200 并站稳）
    '恒生科技': 2.20,    # HSTECH 4,405.50 +2.20%
    '宏观': 0.94,        # 上证指数 3,911.87 +0.94%
    '其他/宽基': 0.99,   # 个股均值（广联达 -0.36% / 通威 +2.34%）
    # 美股标普医药：9/18 美股未收盘 → 留空待 9/21 盘前档兜底（§3.70）
}
REF = {
    'A股医药': '9/18 收盘：医药ETF广发 +0.63% / 医疗ETF +0.89%（中证医药 +0.50% / 中证医疗 +0.82%）',
    '大消费': '9/18 收盘：中证消费 12,214.41 +0.43%',
    '恒生科技': '9/18 收盘：HSTECH 4,405.50 +2.20%',
    '宏观': '9/18 收盘：上证指数 3,911.87 +0.94%',
    '其他/宽基': '9/18 收盘：个股均值（广联达 -0.36% / 通威 +2.34%）',
}

# ---------- ① 追加盘后事件 ----------
news = json.load(open(os.path.join(BASE, 'data/processed/news/news-2026-09-18.json'), encoding='utf-8'))
sent = json.load(open(os.path.join(BASE, 'data/processed/news/sentiment-2026-09-18.json'), encoding='utf-8'))
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
print(f'回填 {filled} 条；留空 {blank} 条（美股标普医药，待 9/21 盘前档按 XLV 9/18 收盘兜底）')

# ---------- ③ 全库完整性扫描 ----------
files = sorted(glob.glob(os.path.join(EV, 'events-*.json')))
all_ev, dup = [], {}
for f in files:
    for e in json.load(open(f, encoding='utf-8')):
        all_ev.append(e)
        dup[e['title'][:60]] = dup.get(e['title'][:60], 0) + 1
n_blank = sum(1 for e in all_ev if e.get('reference', {}).get('actual_ret_1d') is None)
print(f'\n全库 {len(all_ev)} 条 / {len(files)} 日；留空 {n_blank} 条；跨日重复标题 {sum(1 for v in dup.values() if v > 1)} 组')

# ---------- ④ 统计（收盘口径） ----------
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
ones = defaultdict(list)
dir_hit = defaultdict(lambda: [0, 0])
for e in all_ev:
    t = e['track']
    r = e.get('reference', {})
    v = r.get('actual_ret_1d')
    if v is not None and t in track_index:
        ones[t].append((v, e.get('direction'), e.get('strength')))
    code = track_index.get(t)
    if not code:
        continue
    for n in (3, 5, 10):
        x = fwd(code, e['date'], n)
        if x is not None:
            win[t][n].append(x)
    if r.get('direction') or e.get('direction'):
        pass

print('\n1 日样本（按赛道）:')
for t, arr in sorted(ones.items()):
    vs = [a[0] for a in arr]
    strong_pos = [a[0] for a in arr if a[1] == '利多' and (a[2] or 0) >= 70]
    strong_neg = [a[0] for a in arr if a[1] == '利空' and (a[2] or 0) >= 70]
    print(f"  {t:8s} n={len(vs):>4d} 均值={sum(vs)/len(vs):+.2f}% 最差={min(vs):+.2f}% 最好={max(vs):+.2f}% "
          f"上涨占比={sum(1 for v in vs if v>0)/len(vs):.2f} "
          f"强正面={sum(strong_pos)/len(strong_pos):+.2f}%(n={len(strong_pos)}) "
          f"强负面={sum(strong_neg)/len(strong_neg):+.2f}%(n={len(strong_neg)})")

print('\n3/5/10 日窗口:')
for t, d in sorted(win.items()):
    row = []
    for n in (3, 5, 10):
        a = d[n]
        row.append(f"{n}日={sum(a)/len(a):+.2f}%(n={len(a)})" if a else f"{n}日=n/a")
    print(f"  {t:8s} " + ' | '.join(row))

# 方向验证（仅当日 9/18）
today_ev = [e for e in all_ev if e['date'] == TODAY]
hit, tot = 0, 0
per = defaultdict(lambda: [0, 0])
for e in today_ev:
    t = e['track']
    r = e.get('reference', {})
    v, d = r.get('actual_ret_1d'), e.get('direction')
    if v is None or d not in ('利多', '利空'):
        continue
    tot += 1
    ok = (v > 0) if d == '利多' else (v < 0)
    hit += ok
    per[d][0] += ok
    per[d][1] += 1
print(f'\n方向验证（9/18 当日，sentiment 口径）: {hit}/{tot}（{hit/tot*100:.0f}%）'
      + (f" — 利多 {per['利多'][0]}/{per['利多'][1]}（{per['利多'][0]/per['利多'][1]*100:.0f}%）"
         f" vs 利空 {per['利空'][0]}/{per['利空'][1]}" if per['利空'][1] else ""))

out = {
    'date': TODAY, 'window': 'close', 'total_events': len(all_ev),
    'today_events': len(today_ev), 'blank': n_blank,
    'track_ret_1d': track_ret, 'ref': REF,
    'onesample': {t: {'n': len(a), 'mean': round(sum(x[0] for x in a) / len(a), 4),
                      'min': min(x[0] for x in a), 'max': max(x[0] for x in a),
                      'up_ratio': round(sum(1 for x in a if x[0] > 0) / len(a), 4)}
                  for t, a in ones.items()},
    'windows': {t: {str(n): ({'n': len(a), 'mean': round(sum(a) / len(a), 4)} if a else {'n': 0, 'mean': None})
                     for n, a in d.items()}
                for t, d in win.items()},
    'direction_check': {'hit': hit, 'total': tot,
                        'by_dir': {k: {'hit': v[0], 'total': v[1]} for k, v in per.items()}},
    'track_index_map': track_index,
    'note': 'A股医药 3/5/10 日窗口序列实际使用 399006（创业板指）代理（口径问题，见知识库 §3.90）',
}
json.dump(out, open(os.path.join(HIST, 'event_stats_20260918_close.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
print('\nSAVED event_stats_20260918_close.json')
