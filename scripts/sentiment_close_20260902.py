# -*- coding: utf-8 -*-
"""盘后档 2026-09-02：DeepSeek 情绪标注盘后新增 8 条新闻；回填盘中 8 条缺 track/strength；合并更新 sentiment JSON"""
import json, os, re, urllib.request

BASE = '/Users/jieyang/Documents/WealthHub'
TODAY = '2026-09-02'
NEWS_PATH = os.path.join(BASE, f'data/processed/news/news-{TODAY}.json')
SENT_PATH = os.path.join(BASE, f'data/processed/news/sentiment-{TODAY}.json')

with open('/Users/jieyang/.pi/agent/auth.json') as f:
    key = json.load(f)['deepseek']['key']

news = json.load(open(NEWS_PATH, encoding='utf-8'))
sent = json.load(open(SENT_PATH, encoding='utf-8'))
sent_titles = set(s['title'] for s in sent)

# 待标注 = news 中存在但 sentiment 中没有的
todo = [n for n in news if n['title'] not in sent_titles]
print(f'待标注: {len(todo)} 条')
for i, n in enumerate(todo, 1):
    print(f'  {i}. [{n["track"]}] {n["title"][:50]}')

if todo:
    items = []
    for i, n in enumerate(todo, 1):
        items.append({"no": i, "title": n['title'], "track": n['track'], "category": n['category']})
    prompt = f"""你是 A股/港股/美股投资新闻情绪分析师。对以下 {len(todo)} 条财经新闻逐条输出情绪标签。

规则：
- sentiment ∈ {{正面, 负面, 中性}}
- score: 情绪方向强度 0-100（>55 偏正面、<45 偏负面）
- strength: 事件重要性/影响力强度 0-100
- direction ∈ {{利多, 利空, 中性}}（对该赛道/组合的预期方向）
- volatility ∈ {{低, 中, 高}}（预期波动）
- comment: 一句话理由（含对持仓赛道影响）

严格输出 JSON 数组，格式：
[{{"no":1,"sentiment":"正面","score":70,"strength":60,"direction":"利多","volatility":"中","comment":"..."}}, ...]

新闻列表：
{json.dumps(items, ensure_ascii=False, indent=1)}"""
    data = {
        "model": "deepseek-v4-flash",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 8000,
        "temperature": 0.3,
    }
    req = urllib.request.Request("https://api.deepseek.com/chat/completions",
        data=json.dumps(data).encode(),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as resp:
        result = json.load(resp)
    content = result['choices'][0]['message']['content']
    # 提取 JSON（可能包在 ```json ... ``` 里）
    m = re.search(r'\[[\s\S]*\]', content)
    if not m:
        print('ERROR: 无法从响应解析 JSON')
        print(content[:2000])
        raise SystemExit(1)
    anno = json.loads(m.group(0))
    print(f'\nDeepSeek 标注 {len(anno)} 条成功:')
    for a in anno:
        no = a['no']
        n = todo[no - 1]
        print(f"  {no}. [{n['track']}] {a['sentiment']}{a['score']}/{a['strength']} {a.get('comment','')[:50]}")
    # 合并到 sentiment
    for a in anno:
        n = todo[a['no'] - 1]
        sent.append({
            'title': n['title'],
            'track': n['track'],
            'category': n['category'],
            'source_url': n.get('source_url', ''),
            'summary': n.get('summary', ''),
            'time': n.get('time', ''),
            'sentiment': a['sentiment'],
            'score': a['score'],
            'strength': a['strength'],
            'direction': a['direction'],
            'volatility': a['volatility'],
            'comment': a.get('comment', ''),
        })

# 修复盘中 8 条缺 track（用 news 的 track 覆盖）+ strength 缺失回填
news_by_title = {n['title']: n for n in news}
fixed = 0
for s in sent:
    nt = news_by_title.get(s['title'])
    if not nt:
        continue
    if not s.get('track') or s.get('track') == '?' or s.get('track') == '':
        s['track'] = nt.get('track', '宏观')
        fixed += 1
    # 盘中标注 strength 缺失或等于 score 时：补 strength 默认=score
    if s.get('strength') is None:
        s['strength'] = s.get('score', 50)
        fixed += 1

json.dump(sent, open(SENT_PATH, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(f'\nsentiment-2026-09-02.json 共 {len(sent)} 条（修复 {fixed} 处缺失）')
