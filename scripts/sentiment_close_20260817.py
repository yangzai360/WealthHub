# -*- coding: utf-8 -*-
"""盘后档 2026-08-17：DeepSeek 情绪标注盘后新增 8 条 + 合并全量 29 条，track 手动指定"""
import json, os, urllib.request, time

BASE = '/Users/jieyang/Documents/WealthHub'
NEWS = os.path.join(BASE, 'data/processed/news/news-2026-08-17.json')
SENT = os.path.join(BASE, 'data/processed/news/sentiment-2026-08-17.json')

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

sent_by_title = {s['title']: s for s in sents}
existing_keys = set(sent_by_title.keys())
todo = [n for n in news if n['title'] not in existing_keys]
print(f'待标注 {len(todo)} 条（盘后新增）')

# 手动指定 track（新新闻无 track 字段）
TRACK_MAP = {
    '7月经济数据落地': '宏观',
    'A股收评': '宏观',
    '茅台失守1,300元关口': '大消费',
    '药明康德A+H齐创历史新高': 'A股医药',
    '港股收评': '恒生科技',
    '礼来retatrutide': '美股标普医药',
    "SK海力士董事长警告明年将现最严重'存储荒'": '恒生科技',
    '7月70城房价数据': '宏观',
}
def pick_track(title):
    for k, v in TRACK_MAP.items():
        if title.startswith(k):
            return v
    return '宏观'

prompt_tpl = """你是资深 A股/港股/美股医药消费投研分析师。对下面这条新闻，输出 JSON（不要任何前后缀文字）：
{{
  "sentiment": "正面|中性|负面",
  "score": <0-100整数，情绪强度>,
  "strength": <0-100整数，影响强度>,
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
    start, end = content.find('{'), content.rfind('}')
    if start == -1 or end == -1:
        print(f'  PARSE_FAIL {n["title"][:40]} -> {content[:80]}')
        continue
    try:
        r = json.loads(content[start:end+1])
    except Exception as e:
        print(f'  JSON_FAIL {n["title"][:40]}: {e}')
        continue
    item = {**n,
            'track': pick_track(n['title']),
            'sentiment': r.get('sentiment'), 'score': r.get('score'),
            'strength': r.get('strength', r.get('score')),
            'direction': r.get('direction'), 'volatility': r.get('volatility'),
            'reason': r.get('reason')}
    out.append(item)
    print(f'  OK [{r.get("sentiment")} {r.get("score")}/{r.get("strength")}] {n["title"][:44]}')
    time.sleep(1)

# 合并：现有 21 条 + 新增标注（按 date/track 排序保持可读）
sents.extend(out)
with open(SENT, 'w', encoding='utf-8') as f:
    json.dump(sents, f, ensure_ascii=False, indent=1)
print(f'\nsentiment 合并完成，总数 {len(sents)}（新增 {len(out)}）')
