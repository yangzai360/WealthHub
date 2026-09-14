# -*- coding: utf-8 -*-
"""修复 sentiment_close_20260914.py 的标题匹配 bug（news 全称 vs sent 截断 60 字 → 误判全部待标注）
保留: sent['items'][:50]（盘前27+盘中23 原始标注）+ sent['items'][77:88]（盘后11条正确标注）
丢弃: sent['items'][50:77]（对盘前27条的重复标注）
并回写 news-2026-09-14.json 的 per-item 情绪字段（1-27 恢复原值，28-38 用盘后标注）"""
import json, os

BASE = '/Users/jieyang/Documents/WealthHub'
NEWS = os.path.join(BASE, 'data/processed/news')
DATE = '2026-09-14'
NEWS_FILE = os.path.join(NEWS, f'news-{DATE}.json')
SENT_FILE = os.path.join(NEWS, f'sentiment-{DATE}.json')

sent = json.load(open(SENT_FILE, encoding='utf-8'))
news = json.load(open(NEWS_FILE, encoding='utf-8'))
items = sent['items']
print(f'修复前: sent items {len(items)} / news {len(news)}')

keep = items[:50]
close_labels = items[77:88]
print(f'保留盘前/盘中 {len(keep)} 条 + 盘后 {len(close_labels)} 条; 丢弃重复 {len(items)-50-11} 条')
assert len(close_labels) == 11, f'盘后条数异常 {len(close_labels)}'

for i, o in enumerate(close_labels):
    o['idx'] = 51 + i
sent['items'] = keep + close_labels
sent['window'] = '2026-09-13 18:00 - 2026-09-14 07:30 (盘前) | 盘中(07:30-13:30) 追加 23 条 | 盘后(13:30-20:00) 追加 11 条'
json.dump(sent, open(SENT_FILE, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

# 回写 news per-item 字段
for i, n in enumerate(news):
    src = None
    if i < 27:
        src = keep[i] if i < len(keep) else None
    else:
        src = close_labels[i - 27]
    if src:
        n['sentiment'] = src['sentiment']; n['score'] = src['strength']
        n['strength'] = src['strength']; n['direction'] = src['direction']
        n['volatility'] = src['volatility']; n['brief'] = src.get('brief', '')
json.dump(news, open(NEWS_FILE, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

print(f'修复后: sent items {len(sent["items"])} / news {len(news)}')
# 校验：当日全量统计
allit = sent['items']
print('当日累计 %d 条: 利多 %d / 利空 %d / 中性 %d' % (
    len(allit), sum(1 for o in allit if o['direction'] == '利多'),
    sum(1 for o in allit if o['direction'] == '利空'),
    sum(1 for o in allit if o['direction'] == '中性')))
print('均值强度 %.1f' % (sum(o['strength'] for o in allit) / len(allit)))
print('--- 盘后 11 条 ---')
for o in close_labels:
    print(f"  {o['idx']} {o['track']:8s} {o['sentiment']} {o['strength']:3d}/{o['confidence']:3d} {o['direction']} {o['volatility']} | {o['brief']}")
print('--- 校验 news 尾部 3 条 ---')
for n in news[-3:]:
    print('  ', n['title'][:40], n.get('sentiment'), n.get('strength'), n.get('direction'))
