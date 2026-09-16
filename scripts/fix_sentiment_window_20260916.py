# -*- coding: utf-8 -*-
"""2026-09-16 修复：盘前/盘中 sentiment 脚本漏写 per-item `window` 字段
→ 盘后档 close_sent 过滤（x.get('window')=='盘后(13:30-20:00)'）返回 0 条，事件库未追加。
按 idx 区间回填（1-34 盘前 / 35-60 盘中 / 61-83 盘后），并修正文件级 window 串。
"""
import json, os

BASE = '/Users/jieyang/Documents/WealthHub'
SENT = os.path.join(BASE, 'data/processed/news/sentiment-2026-09-16.json')

s = json.load(open(SENT, encoding='utf-8'))
items = s['items']
print('items', len(items), '| 已有 window 的条目', sum(1 for x in items if 'window' in x))

BOUND = [(1, 34, '盘前(18:00-07:30)'), (35, 60, '盘中(07:30-13:30)'), (61, 10 ** 9, '盘后(13:30-20:00)')]
for x in items:
    i = x['idx']
    for lo, hi, tag in BOUND:
        if lo <= i <= hi:
            x['window'] = tag
            break

s['window'] = ('2026-09-15 18:00 - 2026-09-16 07:30 (盘前) 34 条 | '
               '盘中(07:30-13:30) 追加 26 条 | 盘后(13:30-20:00) 追加 23 条')
json.dump(s, open(SENT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

from collections import Counter
c = Counter(x['window'] for x in items)
print('回填后 window 分布:', dict(c))
for tag in ('盘前(18:00-07:30)', '盘中(07:30-13:30)', '盘后(13:30-20:00)'):
    sub = [x for x in items if x['window'] == tag]
    if not sub:
        continue
    npos = sum(1 for x in sub if x['direction'] == '利多')
    nneg = sum(1 for x in sub if x['direction'] == '利空')
    nneu = sum(1 for x in sub if x['direction'] == '中性')
    print(f'  {tag}: {len(sub)} 条（利多 {npos} / 利空 {nneg} / 中性 {nneu}，均值强度 {sum(x["strength"] for x in sub)/len(sub):.1f}）')
