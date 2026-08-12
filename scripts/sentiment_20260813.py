# -*- coding: utf-8 -*-
"""2026-08-13 盘前新闻情绪标注 (DeepSeek v4-flash)"""
import json, os, urllib.request, sys

def load_key():
    with open(os.path.expanduser("~/.pi/agent/auth.json")) as f:
        return json.load(f)["deepseek"]["key"]

def call_deepseek(prompt, key, max_tokens=8000):
    data = {
        "model": "deepseek-v4-flash",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": 0.3,
    }
    req = urllib.request.Request(
        "https://api.deepseek.com/chat/completions",
        data=json.dumps(data).encode(),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=180) as resp:
        result = json.load(resp)
    return result["choices"][0]["message"]["content"]

def main():
    base = "/Users/jieyang/Documents/WealthHub"
    news_path = os.path.join(base, "data/processed/news/news-2026-08-13.json")
    out_path = os.path.join(base, "data/processed/news/sentiment-2026-08-13.json")
    with open(news_path, encoding="utf-8") as f:
        news = json.load(f)

    items = []
    for i, n in enumerate(news, 1):
        items.append(f"{i}. [{n['category']}] {n['title']} | 摘要: {n['summary'][:200]}")

    prompt = f"""你是资深A股/港股/美股医药消费投研分析师。以下是中国家庭理财组合(持仓覆盖:大消费/A股医药/美股标普医药/恒生科技四大赛道)今日盘前采集的{len(news)}条新闻(窗口:8/12 18:00-8/13 07:30)。

请对每条新闻输出情绪标注，严格按以下 JSON 数组格式返回(不要输出任何其他文字):

[
  {{"index": 1, "sentiment": "正面/中性/负面", "score": 0-100整数, "direction": "利多/利空/中性", "volatility": "高/中/低", "reason": "一句话理由(≤40字)"}},
  ...
]

评分规则:
- score>=60 为强信号(正面/负面), 40-59 中性偏多/偏空, <40 弱信号
- 结合新闻对【对应赛道或组合整体】的实际影响力度打分, 不是对新闻标题党打分
- direction: 对组合四大赛道(消费/医药/标普医药/恒科)或整体市场的影响方向
- volatility: 该新闻可能引发的市场波动幅度(高>1%日波动预期/中0.5-1%/低<0.5%)"""

    key = load_key()
    content = None
    for attempt in range(3):
        content = call_deepseek(prompt, key)
        content = content.strip()
        if content:
            break
        print(f"attempt {attempt+1} empty, retry...")
    if not content:
        print("ERROR: DeepSeek 返回空")
        sys.exit(1)

    # 提取 JSON 数组
    start = content.find("[")
    end = content.rfind("]")
    if start == -1 or end == -1:
        print("ERROR: 无法解析 JSON:", content[:500])
        sys.exit(1)
    arr = json.loads(content[start:end+1])
    assert len(arr) == len(news), f"标注数 {len(arr)} != 新闻数 {len(news)}"

    # 合并输出
    result = []
    for n, a in zip(news, arr):
        result.append({
            "title": n["title"], "category": n["category"], "time": n["time"],
            "source_url": n["source_url"], "summary": n["summary"],
            "sentiment": a["sentiment"], "score": a["score"], "direction": a["direction"],
            "volatility": a["volatility"], "reason": a.get("reason", ""),
        })
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"OK: {len(result)} 条情绪标注 -> {out_path}")
    for r in result:
        print(f"  [{r['score']:>3} {r['sentiment']}] {r['direction']:<2} {r['volatility']} | {r['title'][:40]}")

if __name__ == "__main__":
    main()
