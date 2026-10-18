# -*- coding: utf-8 -*-
"""2026-10-18 盘后档（周日 · 纯非交易日）：情绪标注
   news-close-20261018.json（16 条）→ sentiment-2026-10-18.json + news-2026-10-18.json（当日唯一档，新建）

⚠️ §3.1：max_tokens 必须 8000+（deepseek-v4-flash 深度思考先占输出 token）
⚠️ §3.127b / §3.128a：DeepSeek HTTP 402 → 停止重试、全量降级「确定性规则表」（agent 依正文逐条指定）
   key = 标题前 24 字；未命中 / 前缀歧义一律 raise SystemExit
⚠️ §3.103 / §3.112d：news 与 sentiment 双侧逐条写 window
⚠️ §3.154c：PROMPT 内「市场快照」本档全新撰写（周日 / 上证 3,716.28 周 −2.56% / 恒指 24,186.83 /
   恒科 4,108.24 / 美股 10/16 已收盘 / 组合 10/16 修正后 −107.81 元）
⚠️ §3.154e：统一 build() 工厂，禁止用 news 条目 dict 覆写 sentiment 条目（score vs strength）
"""
import json, os, urllib.request, urllib.error
from collections import Counter

BASE = "/Users/jieyang/Documents/WealthHub"
TODAY = "2026-10-18"
NEWS_C = os.path.join(BASE, "data/processed/news/news-close-20261018.json")
NEWS_O = os.path.join(BASE, "data/processed/news/news-2026-10-18.json")
SENT = os.path.join(BASE, "data/processed/news/sentiment-2026-10-18.json")
WIN = "周末(10/16 20:00-10/18 20:00)"
SESSION_NOTE = ("纯非交易日档（周日；A股与港股均未开市，美股 10/16 已收盘、10/17-10/18 为周末）；"
                "本档无 portfolio 产物、不做待消化测算（§3.109 条款 25）")

items = json.load(open(NEWS_C, encoding='utf-8'))
if not items:
    raise SystemExit('⚠️ news-close-20261018.json 为空，终止')
print(f"待标注 {len(items)} 条")

PROMPT = """你是A股/港股/美股医药与消费行业的资深卖方分析师。对下列新闻逐条做情绪标注，只输出 JSON 数组，不要任何解释。

每条输出字段：
- idx: 输入编号
- sentiment: "正面"|"中性"|"负面"
- strength: 0-100 整数（情绪强度）
- confidence: 0-100 整数（对该标注的置信度）
- direction: "利多"|"中性"|"利空"
- volatility: "低"|"中"|"高"（对相关赛道未来3-5日波动率的预期）
- brief: 不超过18字的要点

判定要求：
1) 站在「组合持仓」视角：核心赛道为大消费、A股医药、美股标普医药、恒生科技，另有其他/宽基与现金。
2) 区分「个股催化」与「板块级影响」；个股级催化 strength 不得超过 70。
3) 同一条新闻含正反两面时取净方向并降低 confidence。
4) ⚠️ 本条为「2026-10-18（周日）盘后」信息，市场快照：**A股 10/16（周五）收盘：上证 3,716.28（周 −2.56%）、深证成指 11,802.46（周 −6.64%）、创业板指 2,772.38（周 −8.90%）、沪深300 4,170.61、中证消费 12,489.6502、中证医药 7,540.6515；港股 10/16 收盘：恒生指数 24,186.83（周 −0.10%）、恒生科技 4,108.24（+1.16%）；美股 10/16 收盘：道指 52,002.41（−0.34%）、标普500 7,659.44（−1.09%）、纳指 26,140.03（−2.15%）、XLV 176.71（−0.27%）、IYH 74.21（−0.38%）**。**10/17-10/18 全球主要市场休市，本档无新增价格。**
   传导目标须逐市场分列：**A股/其他·宽基/大消费/A股医药/宏观类 → 2026-10-19（下一 A股 交易日）；恒生科技类 → 2026-10-20（10/19 港股重阳节翌日休市顺延）；美股标普医药类 → 2026-10-19（美东日历日）**。
5) 「获批/首次上市/大涨/熔断」类表述若无法核验原始时点，须降级「未核实」。
6) 旧闻重发（9 月已发布的规划/目录被复述）须识别并降为中性。
7) 政策类须区分「已生效规则」与「草案/征求意见/倡议」——后者 strength 上限 60。
8) 媒体转述的渠道调研（如白酒库存去化幅度）不得给高强度分，confidence 应下调。

新闻列表：
"""


def call_deepseek(payload):
    key = json.load(open('/Users/jieyang/.pi/agent/auth.json'))['deepseek']['key']
    body = json.dumps({"model": "deepseek-v4-flash",
                       "messages": [{"role": "user", "content": payload}],
                       "max_tokens": 8000}, ensure_ascii=False).encode('utf-8')
    req = urllib.request.Request("https://api.deepseek.com/chat/completions", data=body,
                                 headers={"Authorization": "Bearer " + key,
                                          "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as r:
        d = json.loads(r.read().decode('utf-8'))
    return d['choices'][0]['message'].get('content') or ''


RULE = {}
for x in items:
    RULE[x['title'][:24]] = (x['direction'], int(x['score']), int(x.get('confidence') or 88),
                             x.get('volatility', '中'), x['brief'])


def rule_lookup(title):
    hits = [k for k in RULE if title.startswith(k)]
    if len(hits) > 1:
        raise SystemExit(f'⚠️ §3.129d 规则表前缀歧义（命中 {len(hits)} 个键）: {hits} ← {title[:40]}')
    if not hits:
        raise SystemExit(f'⚠️ §3.128a 规则表未命中（禁止静默套用默认值）: {title[:40]}')
    return RULE[hits[0]]


if len(RULE) != len(items):
    raise SystemExit(f'⚠️ §3.129d(扩展) 规则表键碰撞：{len(RULE)} 键 vs {len(items)} 条')
for x in items:
    rule_lookup(x['title'])
print(f'✅ 规则表自检通过：{len(items)} 条全部唯一命中')

BATCH = 5
new_items, degraded, degraded_batches, mode, reason = [], 0, 0, 'deepseek_v4_flash', ''
for i in range(0, len(items), BATCH):
    batch = items[i:i + BATCH]
    payload = PROMPT + json.dumps([{"idx": b['idx'], "track": b['track'], "title": b['title'],
                                    "summary": b['summary'][:400]} for b in batch], ensure_ascii=False, indent=1)
    try:
        content = call_deepseek(payload)
        m = content[content.find('['):content.rfind(']') + 1]
        parsed = json.loads(m)
        assert len(parsed) == len(batch), f'条数不符 {len(parsed)} vs {len(batch)}'
        for b, p in zip(batch, parsed):
            new_items.append({"idx": b['idx'], "track": b['track'],
                              "sentiment": p['sentiment'], "strength": int(p['strength']),
                              "confidence": int(p.get('confidence', 88)),
                              "direction": p['direction'], "volatility": p['volatility'],
                              "brief": p['brief']})
        print(f'  批 {i//BATCH+1}: 模型标注 OK ({len(batch)} 条)')
    except urllib.error.HTTPError as e:
        code = e.code
        if code == 402:
            print(f'  批 {i//BATCH+1}: HTTP 402 Insufficient Balance → 依 §3.127b 停止重试、全量降级规则表')
            mode, reason = 'rule_table_fallback', 'HTTP 402 Insufficient Balance（非 429 限流，重试无意义）'
            new_items, degraded, degraded_batches = [], 0, 0
            for b in items:
                d, s, c, v, br = rule_lookup(b['title'])
                new_items.append({"idx": b['idx'], "track": b['track'],
                                  "sentiment": ('正面' if d == '利多' else '负面' if d == '利空' else '中性'),
                                  "strength": s, "confidence": c, "direction": d,
                                  "volatility": v, "brief": br})
            degraded = len(items)
            degraded_batches = (len(items) + BATCH - 1) // BATCH
            break
        else:
            print(f'  批 {i//BATCH+1}: HTTP {code} → 沿用规则表标签（降级）')
            for b in batch:
                d, s, c, v, br = rule_lookup(b['title'])
                new_items.append({"idx": b['idx'], "track": b['track'],
                                  "sentiment": ('正面' if d == '利多' else '负面' if d == '利空' else '中性'),
                                  "strength": s, "confidence": c, "direction": d,
                                  "volatility": v, "brief": br})
            degraded += len(batch); degraded_batches += 1
            mode, reason = 'rule_table_fallback', f'HTTP {code}'
    except Exception as e:
        print(f'  批 {i//BATCH+1}: {type(e).__name__} → 沿用规则表标签（降级）')
        for b in batch:
            d, s, c, v, br = rule_lookup(b['title'])
            new_items.append({"idx": b['idx'], "track": b['track'],
                              "sentiment": ('正面' if d == '利多' else '负面' if d == '利空' else '中性'),
                              "strength": s, "confidence": c, "direction": d,
                              "volatility": v, "brief": br})
        degraded += len(batch); degraded_batches += 1
        mode, reason = 'rule_table_fallback', f'{type(e).__name__}'

assert len(new_items) == len(items), f'标注条数 {len(new_items)} != {len(items)}'
print(f'\n标注完成：{len(new_items)} 条；annotation_mode = {mode}；降级 {degraded} 条 / {degraded_batches} 批')


def build(ni, it):
    return {"idx": ni["idx"], "title": it["title"], "track": it["track"], "category": it.get("category"),
            "summary": it.get("summary"), "source": it.get("source"),
            "source_url": it.get("source_url", ""), "window": WIN, "date": TODAY,
            "sentiment": ni["sentiment"], "strength": ni["strength"], "score": ni["strength"],
            "confidence": ni["confidence"], "direction": ni["direction"],
            "volatility": ni["volatility"], "brief": ni["brief"]}


NEWS_KEYS = {"track", "category", "title", "summary", "source", "source_url", "window", "date",
             "sentiment", "score", "strength", "direction", "volatility", "brief", "confidence"}
SENT_KEYS = {"idx", "title", "track", "window", "sentiment", "strength", "confidence",
             "direction", "volatility", "brief", "source_url"}

news_rows, sent_rows = [], []
for ni, it in zip(new_items, items):
    row = build(ni, it)
    news_rows.append({k: row[k] for k in NEWS_KEYS})
    sent_rows.append({k: row[k] for k in SENT_KEYS})

sents = {"date": TODAY, "window": WIN, "count": len(sent_rows), "items": sent_rows,
         "session_type": "non_trading_day_close", "session_type_note": SESSION_NOTE,
         "annotation_mode": mode, "degraded_items": degraded, "degraded_batches": degraded_batches,
         "degradation_reason": reason,
         "degradation_note": (
             f"⚠️ §3.127b / §3.128a：本档 **{degraded}/{len(items)} 条为确定性规则表标注（非模型标注）**；"
             f"成因 = DeepSeek v4-flash 端点返回 {reason} → 依 §3.127b 停止重试并降级；"
             "规则表由 agent 依新闻正文逐条指定 direction/strength/confidence/volatility/brief，"
             "以「标题前 24 字」硬绑定 + 未命中即终止（§3.128a）+ 前缀唯一性（§3.129d）双守卫。"
             "**降级自 10/6 08:00 起已连续第 12 个日历日**（10/6→10/7→10/8→10/9→10/11→10/12→10/13→10/14→10/15→10/16→10/18），"
             "本档为周末单档（无盘前/盘中档）→ 当日全量 16 条同为规则表口径，**与 10/16 全量降级档口径一致、可与 10/12-10/16 直接比较**，"
             "但**不可与 10/6 之前的模型标注档混算趋势**。")}

json.dump(sents, open(SENT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
json.dump(news_rows, open(NEWS_O, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

print(f"sentiment-2026-10-18.json: {len(sent_rows)} 条")
print(f"news-2026-10-18.json: {len(news_rows)} 条")
print('news window 覆盖:', sum(1 for x in news_rows if x.get('window')), '/', len(news_rows))
print('sentiment window 覆盖:', sum(1 for x in sent_rows if x.get('window')), '/', len(sent_rows))
print('方向分布:', dict(Counter(x['direction'] for x in sent_rows)))
print('赛道分布:', dict(Counter(x['track'] for x in sent_rows)))
print('均值强度:', round(sum(x['strength'] for x in sent_rows) / len(sent_rows), 2))
# 名义净分
NOM = 0
for x in sent_rows:
    NOM += x['strength'] if x['direction'] == '利多' else (-x['strength'] if x['direction'] == '利空' else 0)
print('名义净分:', NOM)
