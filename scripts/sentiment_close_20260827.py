# -*- coding: utf-8 -*-
"""盘后档 2026-08-27：DeepSeek 情绪标注盘后新增 8 条 + 合并全量 + 同步回 news"""
import json, os, urllib.request, time

BASE = '/Users/jieyang/Documents/WealthHub'
NEWS = os.path.join(BASE, 'data/processed/news/news-2026-08-27.json')
SENT = os.path.join(BASE, 'data/processed/news/sentiment-2026-08-27.json')

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

# 手动指定 track（新新闻已带 track 字段，兜底映射）
TRACK_MAP = {
    'A股8/27收盘': '宏观',
    '港股8/27收盘': '恒生科技',
    '百利天恒8/27收盘': 'A股医药',
    '白酒8/27收盘': '大消费',
    '美股医疗8/26收盘': '美股标普医药',
    '英伟达财报后全球AI链': '宏观',
    '8/28杰克逊霍尔前瞻': '宏观',
    '百度集团8/27大涨': '恒生科技',
}
def pick_track(title):
    # 优先用新闻自带 track（盘后新闻已手动归类）
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
            'track': n.get('track') or pick_track(n['title']),
            'sentiment': r.get('sentiment'), 'score': r.get('score'),
            'strength': r.get('strength', r.get('score')),
            'direction': r.get('direction'), 'volatility': r.get('volatility'),
            'reason': r.get('reason')}
    out.append(item)
    print(f'  OK [{r.get("sentiment")} {r.get("score")}/{r.get("strength")}] {n["title"][:44]}')
    time.sleep(1)

sents.extend(out)
with open(SENT, 'w', encoding='utf-8') as f:
    json.dump(sents, f, ensure_ascii=False, indent=1)
print(f'\nsentiment 合并完成，总数 {len(sents)}（新增 {len(out)}）')

# 同步回 news JSON（防御式读取 strength）
with open(SENT, encoding='utf-8') as f:
    sents2 = json.load(f)
by_title = {s['title']: s for s in sents2}
changed = 0
for n in news:
    s = by_title.get(n['title'])
    if s:
        n['track'] = s.get('track', n.get('track', ''))
        n['sentiment'] = s.get('sentiment')
        n['score'] = s.get('score')
        n['strength'] = s.get('strength', s.get('score', 50))
        n['direction'] = s.get('direction')
        n['volatility'] = s.get('volatility')
        n['reason'] = s.get('reason')
        changed += 1
with open(NEWS, 'w', encoding='utf-8') as f:
    json.dump(news, f, ensure_ascii=False, indent=1)
print(f'news 同步情绪字段 {changed} 条')
