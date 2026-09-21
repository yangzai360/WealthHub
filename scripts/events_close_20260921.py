# -*- coding: utf-8 -*-
"""2026-09-21 盘后档事件库处理：
  ① 追加盘后 18 条事件（过滤条件 window == '盘后(14:00-20:00)'，含 §3.88 空集硬守卫）
  ② 回填 9/20 周末 24 条 + 9/21 当日 59 条 = 83 条留空事件的 actual_ret_1d（按 9/21 收盘；美股标普医药留空待 9/22 盘前档）
  ③ 全库完整性扫描
  ④ 1日样本 + 方向验证 + 3/5/10日窗口统计 → history/event_stats_20260921_close.json（收盘口径）
⚠️ 已知口径问题：A股医药 3/5/10 日窗口序列实际使用 399006（创业板指）作代理（§3.90），报告须显式披露。
⚠️ 事件统计脚本中 windows 可能为空列表 → 除零守卫（§3.93）。
"""
import json, os, glob, csv
from collections import defaultdict

BASE = '/Users/jieyang/Documents/WealthHub'
EV = os.path.join(BASE, 'data/processed/events')
HIST = os.path.join(BASE, 'data/processed/history')
TODAY = '2026-09-21'
WIN = '盘后(14:00-20:00)'

# 9/21 收盘口径赛道涨跌（用于事件回填）
track_ret = {
    'A股医药': 2.83,     # 2 只 ETF 均值（医药ETF广发 +3.31% / 医疗ETF +2.35%）；中证医药 +3.04% / 中证医疗 +2.63% / 300医药 +3.64%
    '大消费': 0.88,      # 中证消费 12,321.63 +0.88%（另：中证白酒 +1.01%、白酒概念口径 +3.08%）
    '恒生科技': 0.40,    # HSTECH 4,423.29 +0.40%（中证港股通互联网 +1.72%）
    '宏观': 0.97,        # 上证指数 3,949.91 +0.97%
    '其他/宽基': 2.25,   # 个股均值（广联达 +2.38% / 通威股份 +2.11%）
    # 美股标普医药：9/21 美股未收盘 → 留空待 9/22 盘前档按 XLV 9/21 收盘兜底
}
REF = {
    'A股医药': '9/21 收盘：医药ETF广发 0.655 +3.31% / 医疗ETF 0.348 +2.35%（中证医药 7,954.82 +3.04% / 中证医疗 6,869.19 +2.63% / 300医药 8,282.40 +3.64%）',
    '大消费': '9/21 收盘：中证消费 12,321.63 +0.88%（中证白酒 6,254.47 +1.01%）',
    '恒生科技': '9/21 收盘：HSTECH 4,423.29 +0.40%（中证港股通互联网 +1.72%）',
    '宏观': '9/21 收盘：上证指数 3,949.91 +0.97%',
    '其他/宽基': '9/21 收盘：个股均值（广联达 8.60 +2.38% / 通威股份 11.59 +2.11%）',
}

# ---------- ① 追加盘后事件 ----------
news = json.load(open(os.path.join(BASE, 'data/processed/news/news-2026-09-21.json'), encoding='utf-8'))
sent = json.load(open(os.path.join(BASE, 'data/processed/news/sentiment-2026-09-21.json'), encoding='utf-8'))
items = sent['items'] if isinstance(sent, dict) else sent
ev_path = os.path.join(EV, f'events-{TODAY}.json')
ev = json.load(open(ev_path, encoding='utf-8'))
existing = {e['title'] for e in ev}

close_sent = [x for x in items if x.get('window') == WIN]
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
        'window': WIN,
        'reference': {'ret_3d': None, 'ret_5d': None, 'ret_10d': None,
                      'max_vol': {'低': 1.5, '中': 4.8, '高': 9.0}.get(n.get('volatility'), 4.8),
                      'confidence': n.get('confidence')},
    })
ev.extend(added)
print(f'事件库 {TODAY} +{len(added)} 条 → {len(ev)} 条')

# ---------- ② 回填 9/20 周末 + 9/21 当日 留空事件 ----------
filled, blank = 0, 0
blank_detail = defaultdict(int)
for day in ('2026-09-20', '2026-09-21'):
    p = os.path.join(EV, f'events-{day}.json')
    e2 = json.load(open(p, encoding='utf-8'))
    ch = 0
    for e in e2:
        r = e.setdefault('reference', {})
        if r.get('actual_ret_1d') is not None:
            continue
        t = e['track']
        if t in track_ret:
            r['actual_ret_1d'] = track_ret[t]
            r['actual_date'] = TODAY
            r['ret_1d_ref'] = REF[t]
            ch += 1
        else:
            blank += 1
            blank_detail[t] += 1
    json.dump(e2, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    filled += ch
    print(f'  {day} 回填 {ch} 条')
print(f'合计回填 {filled} 条；留空 {blank} 条 {dict(blank_detail)}（美股标普医药，待 9/22 盘前档按 XLV 9/21 收盘兜底）')

# ---------- ③ 全库完整性扫描 ----------
files = sorted(glob.glob(os.path.join(EV, 'events-*.json')))
all_ev = []
for f in files:
    all_ev.extend(json.load(open(f, encoding='utf-8')))
n_blank = sum(1 for e in all_ev if e.get('reference', {}).get('actual_ret_1d') is None)
print(f'\n全库 {len(all_ev)} 条 / {len(files)} 日；留空 {n_blank} 条')

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
ones = defaultdict(list)
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

print('\n1 日样本（按赛道）:')
for t, arr in sorted(ones.items()):
    vs = [a[0] for a in arr]
    if not vs:
        continue
    sp = [a[0] for a in arr if a[1] == '利多' and (a[2] or 0) >= 70]
    sn = [a[0] for a in arr if a[1] == '利空' and (a[2] or 0) >= 70]
    f = lambda a: f"{sum(a)/len(a):+.2f}%(n={len(a)})" if a else 'n/a'
    print(f"  {t:8s} n={len(vs):>4d} 均值={sum(vs)/len(vs):+.2f}% 最差={min(vs):+.2f}% 最好={max(vs):+.2f}% "
          f"上涨占比={sum(1 for v in vs if v>0)/len(vs):.2f} 强正面={f(sp)} 强负面={f(sn)}")

print('\n3/5/10 日窗口:')
for t, d in sorted(win.items()):
    row = []
    for n in (3, 5, 10):
        a = d[n]
        row.append(f"{n}日={sum(a)/len(a):+.2f}%(n={len(a)})" if a else f"{n}日=n/a")
    print(f"  {t:8s} " + ' | '.join(row))

# 方向验证（9/21 当日）
today_ev = [e for e in all_ev if e['date'] == TODAY]
hit, tot = 0, 0
per = defaultdict(lambda: [0, 0])
for e in today_ev:
    r = e.get('reference', {})
    v, d = r.get('actual_ret_1d'), e.get('direction')
    if v is None or d not in ('利多', '利空'):
        continue
    tot += 1
    ok = (v > 0) if d == '利多' else (v < 0)
    hit += ok
    per[d][0] += ok
    per[d][1] += 1
msg = f'\n方向验证（9/21 当日，sentiment 口径）: {hit}/{tot}（{hit/tot*100:.0f}%）' if tot else '\n方向验证: 无有效样本'
if per['利空'][1]:
    msg += (f" — 利多 {per['利多'][0]}/{per['利多'][1]}（{per['利多'][0]/per['利多'][1]*100:.0f}%）"
            f" vs 利空 {per['利空'][0]}/{per['利空'][1]}（{per['利空'][0]/per['利空'][1]*100:.0f}%）")
print(msg)

out = {
    'date': TODAY, 'window': 'close', 'total_events': len(all_ev),
    'days': len(files), 'today_events': len(today_ev), 'blank': n_blank,
    'blank_tracks': dict(blank_detail),
    'track_ret_1d': track_ret, 'ref': REF,
    'onesample': {t: {'n': len(a), 'mean': round(sum(x[0] for x in a) / len(a), 4),
                      'min': min(x[0] for x in a), 'max': max(x[0] for x in a),
                      'up_ratio': round(sum(1 for x in a if x[0] > 0) / len(a), 4)}
                  for t, a in ones.items() if a},
    'windows': {t: {str(n): ({'n': len(a), 'mean': round(sum(a) / len(a), 4)} if a else {'n': 0, 'mean': None})
                     for n, a in d.items()}
                for t, d in win.items()},
    'direction_check': {'hit': hit, 'total': tot,
                        'by_dir': {k: {'hit': v[0], 'total': v[1]} for k, v in per.items()}},
    'track_index_map': track_index,
    'note': 'A股医药 3/5/10 日窗口序列实际使用 399006（创业板指）代理（口径问题，见知识库 §3.90）',
}
json.dump(out, open(os.path.join(HIST, 'event_stats_20260921_close.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
print('\nSAVED event_stats_20260921_close.json')
