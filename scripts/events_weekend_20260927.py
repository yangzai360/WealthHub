# -*- coding: utf-8 -*-
"""2026-09-27 周日盘后档事件库处理：
  ① 追加周末 24 条事件到 events-2026-09-27.json（window == 周末(9/25 20:00-9/27 20:00)，含空集硬守卫）
  ② 全库完整性扫描（含「留空 = 当日新增」健康基线判据）
  ③ 1 日样本 + 3/5/10 日窗口统计 → history/event_stats_20260927.json
⚠️ 非交易日：周末事件参考交易日 = 9/28（复市首日）→ 本档 24 条 actual_ret_1d 全部留空（预期状态）。
⚠️ 9/25 遗留 105 条亦不可回填（同一原因），本档逐日核对并显式说明（§3.108 条款 9）。
⚠️ 已知口径问题：A股医药 3/5/10 日窗口序列实际使用 399006（创业板指）作代理（§3.90），报告须披露。
"""
import json, os, glob, csv
from collections import defaultdict

BASE = '/Users/jieyang/Documents/WealthHub'
EV = os.path.join(BASE, 'data/processed/events')
HIST = os.path.join(BASE, 'data/processed/history')
TODAY = '2026-09-27'
WIN = '周末(9/25 20:00-9/27 20:00)'
REF_TD = '2026-09-28'   # 复市首日（参考交易日）

# ---------- ① 追加周末事件 ----------
news = json.load(open(os.path.join(BASE, 'data/processed/news/news-2026-09-27.json'), encoding='utf-8'))
sent = json.load(open(os.path.join(BASE, 'data/processed/news/sentiment-2026-09-27.json'), encoding='utf-8'))
ev_path = os.path.join(EV, f'events-{TODAY}.json')
ev = json.load(open(ev_path, encoding='utf-8')) if os.path.exists(ev_path) else []
existing = {e['title'] for e in ev}

wk_sent = [x for x in sent['items'] if x.get('window') == WIN]
if not wk_sent:
    raise SystemExit('⚠️ 周末窗口 sentiment 为 0 条 → per-item `window` 缺失（§3.88），终止')
added = []
for x in wk_sent:
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
                      'confidence': n.get('confidence'),
                      'actual_ret_1d': None, 'actual_date': None,
                      'ret_1d_ref': f'非交易日（周日），参考交易日 = {REF_TD}（复市首日），待 {REF_TD} 收盘回填'},
    })
ev.extend(added)
json.dump(ev, open(ev_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(f'事件库 {TODAY} +{len(added)} 条 → {len(ev)} 条（当日全部留空，参考交易日 {REF_TD}）')

# ---------- ② 全库扫描 ----------
files = sorted(glob.glob(os.path.join(EV, 'events-*.json')))
all_ev, dup = [], {}
for f in files:
    for e in json.load(open(f, encoding='utf-8')):
        all_ev.append(e)
        dup[e['title'][:60]] = dup.get(e['title'][:60], 0) + 1
n_blank = sum(1 for e in all_ev if e.get('reference', {}).get('actual_ret_1d') is None)
blank_by_date = defaultdict(int)
for e in all_ev:
    if e.get('reference', {}).get('actual_ret_1d') is None:
        blank_by_date[e['date']] += 1
print(f'\n全库 {len(all_ev)} 条 / {len(files)} 日；留空 {n_blank} 条；跨日重复标题 {sum(1 for v in dup.values() if v > 1)} 组')
print(f'留空按日分布: {dict(sorted(blank_by_date.items()))}')
print(f'  → 健康基线判据：留空是否全部来自「非交易日档新增(9/25 混合档 + 9/27 周末)」？')

# ---------- ③ 统计 ----------
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
    sp = [a[0] for a in arr if a[1] == '利多' and (a[2] or 0) >= 70]
    sn = [a[0] for a in arr if a[1] == '利空' and (a[2] or 0) >= 70]
    print(f"  {t:8s} n={len(vs):>4d} 均值={sum(vs) / len(vs):+.2f}% 最差={min(vs):+.2f}% 最好={max(vs):+.2f}% "
          f"上涨占比={sum(1 for v in vs if v > 0) / len(vs):.2f} "
          f"强正面={sum(sp) / len(sp):+.2f}%(n={len(sp)}) 强负面={sum(sn) / len(sn):+.2f}%(n={len(sn)})")

print('\n3/5/10 日窗口:')
for t, d in sorted(win.items()):
    row = []
    for n in (3, 5, 10):
        a = d[n]
        row.append(f"{n}日={sum(a) / len(a):+.2f}%(n={len(a)})" if a else f'{n}日=n/a')
    print(f'  {t:8s} ' + ' | '.join(row))

# 方向验证（全库，按参考交易日回填成功者）
hit = miss = 0
for e in all_ev:
    r = e.get('reference', {})
    v = r.get('actual_ret_1d')
    d = e.get('direction')
    if v is None or d not in ('利多', '利空'):
        continue
    if (d == '利多' and v > 0) or (d == '利空' and v < 0):
        hit += 1
    else:
        miss += 1
print(f'\n方向验证（全库，实际1日）: {hit}/{hit + miss} = {hit / (hit + miss) * 100:.1f}%' if hit + miss else '方向验证: 无样本')

out = {
    'date': TODAY, 'window': 'weekend', 'total_events': len(all_ev),
    'today_events': len(ev), 'blank': n_blank,
    'blank_by_date': dict(sorted(blank_by_date.items())),
    'reference_trading_day': REF_TD,
    'onesample': {t: {'n': len(a), 'mean': round(sum(x[0] for x in a) / len(a), 4),
                      'min': min(x[0] for x in a), 'max': max(x[0] for x in a),
                      'up_ratio': round(sum(1 for x in a if x[0] > 0) / len(a), 4)}
                  for t, a in ones.items()},
    'windows': {t: {str(n): ({'n': len(a), 'mean': round(sum(a) / len(a), 4)} if a else {'n': 0, 'mean': None})
                    for n, a in d.items()}
                for t, d in win.items()},
    'track_index_map': track_index,
    'note': ('A股医药 3/5/10 日窗口序列实际使用 399006（创业板指）代理（§3.90）；'
             f'周末事件留空待 {REF_TD} 回填；9/25 遗留 105 条同为「参考交易日 = {REF_TD}」故本档不可回填（§3.108）'),
}
json.dump(out, open(os.path.join(HIST, 'event_stats_20260927.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
print('\nSAVED event_stats_20260927.json')
