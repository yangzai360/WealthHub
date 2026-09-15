# -*- coding: utf-8 -*-
"""2026-09-15 盘中档：新闻/情绪/事件库增量落库（§3.82 口径：标题统一 title[:60] 判重）"""
import json, os

ROOT = "/Users/jieyang/Documents/WealthHub"
TODAY = "2026-09-15"
TODAYC = TODAY.replace("-", "")

news = json.load(open('/tmp/news_intraday_20260915.json'))

# ---- 赛道 -> category 映射（事件库四级分类） ----
def cat_of(n):
    t = n['title']
    if any(k in t for k in ['国新办', '统计局', '经济数据', '社零', 'FOMC', '工信部', '发改委', '特朗普', '油价', 'shibor', '美方寻求', '期市']):
        return '宏观类'
    if any(k in t for k in ['规划', '印发', '政策', '规划》', '获批', '受理']):
        return '政策类'
    if any(k in t for k in ['半年', '业绩', '净利润', '营收']):
        return '业绩类'
    return '行业事件类'

# ---- 1) news 文件增量 ----
p_news = os.path.join(ROOT, "data/processed/news/news-%s.json" % TODAY)
cur = json.load(open(p_news))
exist = set(x['title'] for x in cur)
added = []
for n in news:
    if n['title'] in exist: continue
    added.append({
        "title": n['title'], "category": cat_of(n), "track": n['track'],
        "summary": n['brief'], "source": "财联社/东方财富/证券时报/新华财经/华西/新浪财经",
        "source_url": n.get('source_url', ''), "sentiment": n['sentiment'], "score": n['strength'],
        "strength": n['strength'], "direction": n['direction'], "volatility": n['volatility'],
        "brief": n['brief'],
    })
cur.extend(added)
json.dump(cur, open(p_news, 'w'), ensure_ascii=False, indent=1)
print("news: %d -> %d (+%d)" % (len(cur)-len(added), len(cur), len(added)))

# ---- 2) sentiment 文件增量（title 截断 60 字符，与既有条目口径一致） ----
p_sent = os.path.join(ROOT, "data/processed/news/sentiment-%s.json" % TODAY)
sd = json.load(open(p_sent))
sent_titles = set(x['title'] for x in sd['items'])
base_idx = len(sd['items'])
new_items = []
i = 0
for n in news:
    t60 = n['title'][:60]
    if t60 in sent_titles: continue
    i += 1
    new_items.append({"idx": base_idx + i, "title": t60, "track": n['track'],
                      "sentiment": n['sentiment'], "strength": n['strength'],
                      "confidence": n['confidence'], "direction": n['direction'],
                      "volatility": n['volatility'], "brief": n['brief']})
sd['items'].extend(new_items)
json.dump(sd, open(p_sent, 'w'), ensure_ascii=False, indent=1)
print("sentiment: %d -> %d (+%d)" % (base_idx, len(sd['items']), len(new_items)))

# ---- 3) events 事件库增量 ----
p_ev = os.path.join(ROOT, "data/processed/events/events-%s.json" % TODAY)
ev = json.load(open(p_ev))
seq = len(ev)
ev_exist = set(e['title'] for e in ev)
new_ev = []
for n in news:
    if n['title'] in ev_exist: continue
    seq += 1
    new_ev.append({
        "id": "N%s-%03d" % (TODAYC, seq), "date": TODAY, "track": n['track'],
        "category": cat_of(n), "title": n['title'], "summary": n['brief'],
        "source": "财联社/东方财富/证券时报/新华财经/新浪财经",
        "source_url": n.get('source_url', ''), "sentiment": n['sentiment'],
        "score": n['strength'], "strength": n['strength'], "direction": n['direction'],
        "volatility": n['volatility'], "reason": n['brief'],
        "reference": {"ret_3d": None, "ret_5d": None, "ret_10d": None, "actual_ret_1d": None},
    })
ev.extend(new_ev)
json.dump(ev, open(p_ev, 'w'), ensure_ascii=False, indent=1)
print("events: %d -> %d (+%d)" % (len(ev)-len(new_ev), len(ev), len(new_ev)))

# ---- 全库统计 ----
import glob
tot = 0
for f in sorted(glob.glob(os.path.join(ROOT, "data/processed/events/events-*.json"))):
    tot += len(json.load(open(f)))
print("事件库全库 %d 条" % tot)
