# -*- coding: utf-8 -*-
"""2026-09-13 周日盘后档: 美股 9/11 收盘增量写入 indices.csv + 事件库全量统计"""
import json, os, csv, glob
from collections import defaultdict

BASE = '/Users/jieyang/Documents/WealthHub'
HIST = os.path.join(BASE, 'data/processed/history')
EV = os.path.join(BASE, 'data/processed/events')
IDX = os.path.join(HIST, 'indices.csv')

# ---------- 1. 写入美股 9/11 收盘 ----------
us = json.load(open(os.path.join(HIST, 'close_20260913.json'), encoding='utf-8'))['us']
rows = list(csv.reader(open(IDX, encoding='utf-8-sig')))
header = rows[0]
existing = set(tuple(r) for r in rows[1:])
added = 0
for r in us:
    if r['close'] is None:
        print(f"  {r['code']} 数据暂缺，跳过")
        continue
    row = [str(r['type']), str(r['date']), str(r['name']), str(r['code']),
           str(r['close']), str(r['pct_change']), str(r['note'])]
    if tuple(row) in existing:
        print(f"  {r['code']} 已存在，跳过")
        continue
    rows.append(row)
    existing.add(tuple(row))
    added += 1
with open(IDX, 'w', encoding='utf-8-sig', newline='') as f:
    w = csv.writer(f)
    w.writerows(rows)
print(f'indices.csv 新增 {added} 行')

# ---------- 2. 事件库统计 ----------
files = sorted(glob.glob(os.path.join(EV, 'events-*.json')))
all_ev = []
for fp in files:
    try:
        all_ev.extend(json.load(open(fp, encoding='utf-8')))
    except Exception as e:
        print('skip', fp, e)
print(f'\n事件库累计 {len(all_ev)} 条 (来自 {len(files)} 个文件)')

blank = [e for e in all_ev if e.get('reference', {}).get('actual_ret_1d') in (None, '')]
print(f'actual_ret_1d 留空 {len(blank)} 条')
for e in blank:
    print('   ', e.get('id'), e.get('date'), e.get('track'), e.get('title', '')[:40])

# 1 日样本按赛道
stat = defaultdict(list)
for e in all_ev:
    v = e.get('reference', {}).get('actual_ret_1d')
    if v not in (None, ''):
        try:
            stat[e['track']].append(float(v))
        except Exception:
            pass
print('\n【1 日样本统计（截至 9/11 收盘）】')
for t, v in sorted(stat.items(), key=lambda x: -len(x[1])):
    n = len(v)
    avg = sum(v) / n
    print(f'  {t:10s} n={n:4d} 均值 {avg:+.2f}%  最差 {min(v):+.2f}%  最好 {max(v):+.2f}%')

# 方向验证（sentiment 口径，剔除中性）
ok = tot = 0
by = defaultdict(lambda: [0, 0])
for e in all_ev:
    d = e.get('direction')
    v = e.get('reference', {}).get('actual_ret_1d')
    if d not in ('利多', '利空') or v in (None, ''):
        continue
    try:
        v = float(v)
    except Exception:
        continue
    hit = (d == '利多' and v > 0) or (d == '利空' and v < 0)
    tot += 1
    ok += hit
    by[e['track']][1] += 1
    by[e['track']][0] += hit
print(f'\n【方向验证】全局 {ok}/{tot} ({ok/tot*100:.1f}%)')
for t, (a, b) in sorted(by.items(), key=lambda x: -x[1][1]):
    print(f'  {t:10s} {a}/{b} ({a/b*100:.0f}%)')

json.dump({'date': '2026-09-13', 'total': len(all_ev), 'blank': len(blank),
           'by_track': {t: {'n': len(v), 'avg': round(sum(v)/len(v), 3)} for t, v in stat.items()},
           'dir_verify': {'hit': ok, 'total': tot}},
          open(os.path.join(HIST, 'event_stats_20260913.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
print('\nSAVED event_stats_20260913.json')
