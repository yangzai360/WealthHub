# -*- coding: utf-8 -*-
"""2026-09-07 盘后: DeepSeek 情绪标注(幂等) —— 标注 news 中 sentiment 缺失的盘后条目
批 ≤4 条 + 每批重试 4 次(间隔5s) 规避空 content(§3.1/§3.60/§3.64); 标题截断 200; 1-based 对齐(§3.62)"""
import json, os, re, time, urllib.request

BASE = '/Users/jieyang/Documents/WealthHub'
NEWS_FILE = os.path.join(BASE, 'data/processed/news/news-2026-09-07.json')
SENT_FILE = os.path.join(BASE, 'data/processed/news/sentiment-2026-09-07.json')

news = json.load(open(NEWS_FILE, encoding='utf-8'))
sent = json.load(open(SENT_FILE, encoding='utf-8'))

sent_titles = set(s['title'] for s in sent)
# 待标注: sentiment 中缺失的 news 条目（盘后 8 条, 时间字段格式混杂用 title 差集判定）
pending = [n for n in news if n['title'] not in sent_titles]
print(f'待标注 {len(pending)} 条 (news 共 {len(news)} / sentiment 已标 {len(sent)})')
if not pending:
    print('无待标注, 退出')
    raise SystemExit(0)
# 缺失 track 的条目防御式归类（标题关键词）
def guess_track(t):
    if any(k in t for k in ['收评', '国谈', '医药', '创新药', '医保']):
        return 'A股医药' if ('医药' in t or '创新药' in t or '国谈' in t or '医保' in t) and '恒生' not in t and '港股' not in t else ('恒生科技' if '港股' in t or '恒生' in t else '宏观')
    if any(k in t for k in ['消费', '白酒', '茅台', '猪肉']):
        return '大消费'
    if any(k in t for k in ['恒科', '恒生科技', '港股', '小米', '港股通', '百度']):
        return '恒生科技'
    if any(k in t for k in ['美股', '非农', 'CPI', 'FOMC', '休市']):
        return '宏观'
    return '宏观'
for n in pending:
    if not n.get('track'):
        n['track'] = guess_track(n['title'])

with open('/Users/jieyang/.pi/agent/auth.json') as f:
    key = json.load(f)['deepseek']['key']

def call_deepseek(batch):
    prompt = f"""你是投资新闻情绪分析器。请对以下 {len(batch)} 条财经新闻逐条输出情绪标注。
输出要求: 严格输出 JSON 数组, 每元素对应一条新闻(1-based 顺序), 字段:
{{"i": 序号, "sentiment": "正面|中性|负面", "score": 情绪分0-100(正负强度), "strength": 影响强度0-100(对市场影响大小), "direction": "利多|利空|中性", "volatility": "高|中|低", "comment": "一句话理由"}}
新闻列表:
"""
    for idx, n in enumerate(batch, 1):
        prompt += f"\n[{idx}] [{n['track']}] {n['title'][:200]}"
    data = {
        "model": "deepseek-v4-flash",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 8192,
        "temperature": 0.2,
    }
    req = urllib.request.Request("https://api.deepseek.com/chat/completions",
        data=json.dumps(data).encode(),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as resp:
        result = json.load(resp)
    content = result['choices'][0]['message']['content']
    if not content or len(content) < 20:
        raise RuntimeError('空 content')
    m = re.search(r'\[[\s\S]*\]', content)
    if not m:
        raise RuntimeError('未找到 JSON: ' + content[:300])
    return json.loads(m.group(0))

# 分 ≤4 条/批
added = []
for i in range(0, len(pending), 4):
    batch = pending[i:i + 4]
    ok = False
    for attempt in range(4):
        try:
            annos = call_deepseek(batch)
            if len(annos) != len(batch):
                raise RuntimeError(f'标注数 {len(annos)} != {len(batch)}')
            ok = True
            break
        except Exception as e:
            print(f'  批次{i//4+1} 第{attempt+1}次失败: {e}')
            time.sleep(5)
    if not ok:
        raise RuntimeError(f'批次 {i//4+1} 重试 4 次仍失败')
    for a in annos:
        n = batch[a['i'] - 1]
        sent.append({
            'date': '2026-09-07',
            'track': n['track'],
            'title': n['title'],
            'sentiment': a['sentiment'],
            'score': a['score'],
            'strength': a['strength'],
            'direction': a['direction'],
            'volatility': a['volatility'],
            'comment': a['comment'],
        })
        added.append(a)
    print(f'批次{i//4+1} 标注 {len(batch)} 条成功')

with open(SENT_FILE, 'w', encoding='utf-8') as f:
    json.dump(sent, f, ensure_ascii=False, indent=1)
print(f'sentiment-2026-09-07.json 共 {len(sent)} 条 (本次新增 {len(added)})')
for s in sent[-len(pending):]:
    print(f"  [{s['track']}] {s['sentiment']} {s['score']}/{s['strength']} {s['direction']} | {s['title'][:40]}")
