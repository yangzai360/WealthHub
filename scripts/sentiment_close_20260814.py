# -*- coding: utf-8 -*-
"""盘后档 2026-08-14：DeepSeek 情绪标注盘后新增 7 条 + 合并全量 28 条"""
import json, os, urllib.request, time

BASE = '/Users/jieyang/Documents/WealthHub'
NEWS = os.path.join(BASE, 'data/processed/news/news-2026-08-14.json')
SENT = os.path.join(BASE, 'data/processed/news/sentiment-2026-08-14.json')
EVENTS = os.path.join(BASE, 'data/processed/events/events-2026-08-14.json')

with open('/Users/jieyang/.pi/agent/auth.json') as f:
    key = json.load(f)['deepseek']['key']

def ds(prompt):
    data = {"model": "deepseek-v4-flash", "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 8000, "temperature": 0.3}
    req = urllib.request.Request("https://api.deepseek.com/chat/completions",
        data=json.dumps(data).encode(),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                result = json.load(resp)
            content = result['choices'][0]['message']['content']
            if content and content.strip():
                return content
        except Exception as e:
            print(f'  重试 {attempt+1}: {e}')
            time.sleep(3)
    return None

with open(NEWS, encoding='utf-8') as f:
    news = json.load(f)
with open(SENT, encoding='utf-8') as f:
    sents = json.load(f)

# 现有标注按标题索引
sent_by_title = {s['title']: s for s in sents}
existing_keys = set(sent_by_title.keys())

# 待标注：全部新闻中未标注的（盘后新增 7 条）
todo = [n for n in news if n['title'] not in existing_keys]
print(f'待标注 {len(todo)} 条')

prompt_tpl = """你是资深 A股/港股/美股医药消费投研分析师。对下面这条新闻，输出 JSON（不要任何前后缀文字）：
{{
  "sentiment": "正面|中性|负面",
  "score": <0-100整数，情绪强度>,
  "direction": "利多|利空|中性",
  "volatility": "低|中|高",
  "reason": "<一句话归因>"
}}
新闻分类：{category}
标题：{title}
摘要：{summary}"""

out = []
for n in todo:
    prompt = prompt_tpl.format(category=n['category'], title=n['title'], summary=n['summary'])
    content = ds(prompt)
    if content is None:
        print(f'  FAIL {n["title"][:40]}')
        continue
    # 截取 JSON 数组/对象部分
    start, end = content.find('{'), content.rfind('}')
    if start == -1 or end == -1:
        print(f'  PARSE_FAIL {n["title"][:40]} -> {content[:80]}')
        continue
    try:
        r = json.loads(content[start:end+1])
    except Exception as e:
        print(f'  JSON_FAIL {n["title"][:40]}: {e}')
        continue
    item = {**n, 'sentiment': r.get('sentiment'), 'score': r.get('score'),
            'direction': r.get('direction'), 'volatility': r.get('volatility'),
            'reason': r.get('reason')}
    out.append(item)
    print(f'  OK [{r.get("sentiment")} {r.get("score")}] {n["title"][:44]}')
    time.sleep(1)

# 合并：现有 21 条 + 新增标注
merged = [sent_by_title[t] for t in sent_by_title] + out
with open(SENT, 'w', encoding='utf-8') as f:
    json.dump(merged, f, ensure_ascii=False, indent=1)
print(f'sentiment 合并后总数 {len(merged)}')

# 同步回 news：把 sentiment 字段写回 news（全量覆盖）
for n in news:
    s = sent_by_title.get(n['title'])
    if s:
        n['sentiment'] = s.get('sentiment'); n['score'] = s.get('score')
        n['direction'] = s.get('direction'); n['volatility'] = s.get('volatility')
# 新增标注的条目也已写入 news 数组（因为 out 基于 news 的 n）
with open(NEWS, 'w', encoding='utf-8') as f:
    json.dump(news, f, ensure_ascii=False, indent=1)

# 同步回 events
with open(EVENTS, encoding='utf-8') as f:
    events = json.load(f)
for e in events:
    s = sent_by_title.get(e['title']) or next((o for o in out if o['title'] == e['title']), None)
    if s:
        e['sentiment'] = s.get('sentiment'); e['score'] = s.get('score')
        e['direction'] = s.get('direction')
with open(EVENTS, 'w', encoding='utf-8') as f:
    json.dump(events, f, ensure_ascii=False, indent=1)
print('news/events 情绪字段同步完成')
