# -*- coding: utf-8 -*-
"""2026-09-04 盘后修复: ①news/sentiment 盘中8条补 track ②追加盘后8条 DeepSeek 标注"""
import json, os, re, urllib.request

BASE = '/Users/jieyang/Documents/WealthHub'
NEWS_FILE = os.path.join(BASE, 'data/processed/news/news-2026-09-04.json')
SENT_FILE = os.path.join(BASE, 'data/processed/news/sentiment-2026-09-04.json')

# 盘中 8 条标题前缀 → track (与 append_events_intraday_20260904.py TRACK_MAP 一致)
PREFIX_TRACK = [
    ('A股午评（9/4）', '宏观'),
    ('港股午评（9/4）', '恒生科技'),
    ('恒生科技13:45实时4,578.85', '恒生科技'),
    ('A股医药盘中滞涨（9/4）', 'A股医药'),
    ('中证消费大爆发（9/4盘中）', '大消费'),
    ('世界气象组织确认厄尔尼诺', '宏观'),
    ('美国8月ISM服务业PMI 55.4', '宏观'),
    ('传媒/AI应用大涨（9/4盘中）', '其他/宽基'),
]

def guess_track(title):
    for p, t in PREFIX_TRACK:
        if title.startswith(p):
            return t
    return '其他/宽基'

# ① 修复 news
with open(NEWS_FILE, encoding='utf-8') as f:
    news = json.load(f)
fixed_n = 0
for x in news:
    if 'track' not in x or not x['track']:
        x['track'] = guess_track(x['title'])
        fixed_n += 1
with open(NEWS_FILE, 'w', encoding='utf-8') as f:
    json.dump(news, f, ensure_ascii=False, indent=1)
print(f'news 补 track {fixed_n} 条')

# ② 修复 sentiment 已有条目
with open(SENT_FILE, encoding='utf-8') as f:
    sent = json.load(f)
fixed_s = 0
for x in sent:
    if 'track' not in x or not x['track']:
        x['track'] = guess_track(x['title'])
        fixed_s += 1
with open(SENT_FILE, 'w', encoding='utf-8') as f:
    json.dump(sent, f, ensure_ascii=False, indent=1)
print(f'sentiment 补 track {fixed_s} 条, 当前 {len(sent)} 条')

# ③ 追加盘后 8 条标注 (news 中 sentiment 没有的)
existing_sent_titles = set(x['title'][:50] for x in sent)
added = [n for n in news if n['title'][:50] not in existing_sent_titles]
print(f'待标注盘后新闻: {len(added)} 条')

with open('/Users/jieyang/.pi/agent/auth.json') as f:
    key = json.load(f)['deepseek']['key']

prompt = f"""你是投资新闻情绪分析器。请对以下 {len(added)} 条财经新闻逐条输出情绪标注。

输出要求: 严格输出 JSON 数组, 每元素对应一条新闻(1-based 顺序), 字段:
{{"i": 序号, "sentiment": "正面|中性|负面", "score": 情绪分0-100(正负强度), "strength": 影响强度0-100(对市场影响大小), "direction": "利多|利空|中性", "volatility": "高|中|低", "comment": "一句话理由"}}

新闻列表:
"""
for idx, n in enumerate(added, 1):
    prompt += f"\n[{idx}] [{n['track']}] {n['title'][:200]}"

def call_ds(temperature):
    data = {
        "model": "deepseek-v4-flash",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 8192,
        "temperature": temperature,
    }
    req = urllib.request.Request("https://api.deepseek.com/chat/completions",
        data=json.dumps(data).encode(),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as resp:
        result = json.load(resp)
    return result['choices'][0]['message'].get('content', '')

content = call_ds(0.2)
if not content:
    print('首次为空, 重试...')
    content = call_ds(0.1)
print('DeepSeek content 长度:', len(content))
m = re.search(r'\[[\s\S]*\]', content)
if not m:
    raise RuntimeError('未找到 JSON: ' + content[:300])
annos = json.loads(m.group(0))
print('标注条数:', len(annos))

for a in annos:
    n = added[a['i'] - 1]
    sent.append({
        'date': '2026-09-04',
        'track': n['track'],
        'title': n['title'],
        'sentiment': a['sentiment'],
        'score': a['score'],
        'strength': a['strength'],
        'direction': a['direction'],
        'volatility': a['volatility'],
        'comment': a['comment'],
    })
with open(SENT_FILE, 'w', encoding='utf-8') as f:
    json.dump(sent, f, ensure_ascii=False, indent=1)
print(f'sentiment 最终 {len(sent)} 条')
for s in sent[-len(added):]:
    print(f"  [{s['track']}] {s['sentiment']} {s['score']}/{s['strength']} {s['direction']} | {s['title'][:36]}")
