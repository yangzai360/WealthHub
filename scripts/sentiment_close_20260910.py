# -*- coding: utf-8 -*-
"""2026-09-10 盘后: DeepSeek 情绪标注盘后新增 8 条 (幂等, 2x4 分批 §3.67/§3.72 索引对齐)
只标注 sentiment 为空的条目; 结果写回 sentiment-2026-09-10.json"""
import json, os, time, urllib.request

BASE = '/Users/jieyang/Documents/WealthHub'
SENT_FILE = os.path.join(BASE, 'data/processed/news/sentiment-2026-09-10.json')

with open(os.path.join(BASE, 'data/processed/news/news-2026-09-10.json'), encoding='utf-8') as f:
    news = json.load(f)
with open(SENT_FILE, encoding='utf-8') as f:
    sent = json.load(f)

sent_titles = set(n.get('title', '') for n in sent)
pending = []
for n in news:
    t = n.get('title', '')
    if t in sent_titles:
        continue
    pending.append(n)
# 防御: sent 中 sentiment 为空的也补标
for s in sent:
    if not s.get('sentiment') and s.get('title') not in [p['title'] for p in pending]:
        pending.append(s)

print(f'待标注 {len(pending)} 条')

if not pending:
    print('无待标注条目')
else:
    with open('/Users/jieyang/.pi/agent/auth.json') as f:
        key = json.load(f)['deepseek']['key']

    def call_ds(items):
        lines = []
        for i, it in enumerate(items, 1):
            title = it['title'][:200]  # §3.64: 标题截断 200 字符
            lines.append(f'{i}. {title}')
        prompt = (
            "你是A股/港股/美股医疗投研情绪标注器。对以下每条新闻判断其对相应赛道的影响。\n"
            "输出 JSON 数组，每项格式: {\"i\": 序号, \"sentiment\": \"正面|中性|负面\", \"score\": 情绪分0-100, "
            "\"strength\": 影响强度0-100, \"direction\": \"利多|中性|利空\", \"volatility\": \"低|中|高\", \"reason\": 一句话理由}\n"
            "只输出 JSON，不要多余文字。\n新闻列表:\n" + "\n".join(lines)
        )
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
        if not content or not content.strip():
            raise ValueError('empty content')
        s, e = content.find('['), content.rfind(']')
        if s < 0 or e < 0:
            raise ValueError('no json array')
        return json.loads(content[s:e + 1])

    results = {}
    # 2x4 分批 + 批偏移 bi 对齐全局索引（§3.62/§3.72 索引坑）
    for bi in range(0, len(pending), 4):
        batch = pending[bi:bi + 4]
        ok = False
        for attempt in range(4):
            try:
                labels = call_ds(batch)
                for lab in labels:
                    results[bi + int(lab['i'])] = lab
                ok = True
                break
            except Exception as ex:
                print(f'  批次{bi//4+1} 第{attempt+1}次失败: {ex}')
                time.sleep(5)
        print(f'  批次{bi//4+1} ({len(batch)}条) {"标注成功" if ok else "重试耗尽"}')

    updated = 0
    for idx, n in enumerate(pending):
        lab = results.get(idx + 1)
        if not lab:
            continue
        entry = None
        for s in sent:
            if s.get('title', '') == n.get('title', ''):
                entry = s
                break
        if entry is None:
            entry = dict(n)
            sent.append(entry)
        entry['sentiment'] = lab.get('sentiment', entry.get('sentiment', '中性'))
        entry['score'] = lab.get('score', entry.get('score', 50))
        entry['strength'] = lab.get('strength', entry.get('strength', entry.get('score', 50)))
        entry['direction'] = lab.get('direction', entry.get('direction', '中性'))
        entry['volatility'] = lab.get('volatility', entry.get('volatility', '中'))
        entry['reason'] = lab.get('reason', entry.get('reason', ''))
        if not entry.get('track'):
            entry['track'] = n.get('track')
        updated += 1

    with open(SENT_FILE, 'w', encoding='utf-8') as f:
        json.dump(sent, f, ensure_ascii=False, indent=1)
    print(f'已更新 {updated} 条 -> sentiment 文件共 {len(sent)} 条')

for s in sent:
    print(f"  {s.get('sentiment','?'):2s} {str(s.get('score','?')):>3s}/{str(s.get('strength','')):>3s} | {(s.get('title') or '')[:50]}")
