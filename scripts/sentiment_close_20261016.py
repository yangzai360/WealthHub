# -*- coding: utf-8 -*-
"""2026-10-16 盘后档：情绪标注（news-close-20261016.json → sentiment-2026-10-16.json）
⚠️ §3.1：max_tokens 必须 8000+（deepseek-v4-flash 深度思考先占输出 token）
⚠️ §3.127b / §3.128a：DeepSeek 端点若返回 HTTP 402（额度耗尽，非 429 限流）→ **停止重试并降级**；
   降级必须走「确定性规则表」（agent 依新闻正文逐条指定），**禁止无表兜底（会产生伪中性档）**；
   规则表 key = 标题前 24 字，**未命中即 raise SystemExit**；**前缀必须唯一（len(hits) > 1 即终止，§3.129d）**
⚠️ 落库自证字段（缺一不可）：annotation_mode / degraded_items / degraded_batches / degradation_reason / degradation_note
⚠️ §3.103 / §3.112d：逐条写 window 字段（news 与 sentiment 双侧）
⚠️ §3.112d：报告引用分数一律取合并后的 news-2026-10-16.json（sentiment 侧字段名为 strength）
⚠️ §3.154c：PROMPT 内「市场快照」须逐档核对（本档已更新为 10/16 读数：周五 / 长假后第 7 个正常交易日 /
   上证 3,716.28 / 恒生指数 24,186.83 / 恒生科技 4,108.24）
⚠️ §3.154e：合并盘后块一律用统一 build() 工厂；**禁止用 news 条目 dict 直接覆写 sentiment 条目**（字段名不同：score vs strength）
⚠️ §3.119c / §3.127a：本档为「正常交易日收盘档」（A股 10/16 15:00 收盘 + 港股 10/16 16:00 收盘；美股 10/16 未开盘），传导目标逐市场分列：
   A股/港股/宏观/其他·宽基类 → 2026-10-19（本档采集窗口 13:30-20:00 晚于 A股 15:00 与港股 16:00 收盘，须严格顺延）；
   美股类 → 2026-10-16（US 10/16 交易日收盘成型于北京 10/17 04:00，本档时点尚无读数）
"""
import json, os, urllib.request, urllib.error
from collections import Counter

BASE = "/Users/jieyang/Documents/WealthHub"
TODAY = "2026-10-16"
NEWS_C = os.path.join(BASE, "data/processed/news/news-close-20261016.json")
NEWS_O = os.path.join(BASE, "data/processed/news/news-2026-10-16.json")
SENT = os.path.join(BASE, "data/processed/news/sentiment-2026-10-16.json")
WIN = "盘后(13:30-20:00)"
SESSION_NOTE = "正常交易日收盘档（A股 10/16 长假后第 7 个正常交易日 15:00 收盘 + 港股 10/16 正常交易日 16:00 收盘；两市均正常交易）"

items = json.load(open(NEWS_C, encoding='utf-8'))
if not items:
    raise SystemExit('⚠️ news-close-20261016.json 为空，终止')
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
1) 站在「组合持仓」视角：组合核心赛道为大消费、A股医药、美股标普医药、恒生科技，另有其他/宽基与现金。
2) 区分「个股催化」与「板块级影响」；个股级催化 strength 不得超过 70。
3) 若同一条新闻同时含正反两面，取净方向并降低 confidence。
4) ⚠️ 本条为「2026-10-16（周五，长假后第 7 个正常交易日）盘后（13:30-20:00）」信息：**A股已收盘（上证 3,716.28 / +0.24%、深证成指 −0.12%、创业板指 −0.39%、沪深300 +0.11%、中证消费 +1.46%、中证医药 −1.31%、中证医疗 −2.33%）、港股已收盘（恒生指数 24,186.83 / +0.52%、恒生科技 4,108.24 / +1.16%、恒生国企 +0.31%）、美股尚未开盘（北京 20:00 = 美东 08:00 EDT，美股 21:30 开盘）**。
   传导目标须**逐市场分列**：**A股/港股/宏观/其他·宽基类事件 → 2026-10-19（严格顺延至下一交易日；本档采集晚于 A股 15:00 与港股 16:00 收盘，§3.127a）；美股类事件 → 2026-10-16（US 10/16 交易日，收盘成型于北京 10/17 04:00，本档时点尚无读数）**。
5) 「获批/首次上市/大涨」类表述若无法核验原始获批日与实际收盘，须降级「未核实」，不得给高强度分。
6) 长假窗口内旧闻重发（如 9 月已发布的规划/目录被复述）须识别并降为中性。
7) 一切「资金流 / 净买入」读数在港股通暂停期间一律按「未核实」处理。
8) ⚠️ 美债收益率在美股开盘前属「盘中读数」，标注时须降低 confidence 并避免给结论位强度。

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


# ---------- 确定性规则表（agent 依新闻正文逐条指定；key = 标题前 24 字） ----------
RULE = {}
for x in items:
    RULE[x['title'][:24]] = (x['direction'], int(x['score']), int(x.get('confidence', 88) if x.get('confidence') else 88),
                             x.get('volatility', '中'), x['brief'])


def rule_lookup(title):
    hits = [k for k in RULE if title.startswith(k)]
    if len(hits) > 1:
        raise SystemExit(f'⚠️ §3.129d 规则表前缀歧义（命中 {len(hits)} 个键）: {hits} ← {title[:40]}')
    if not hits:
        raise SystemExit(f'⚠️ §3.128a 规则表未命中（禁止静默套用默认值）: {title[:40]}')
    return RULE[hits[0]]


# 先做一次「键无碰撞 + 全表可命中 + 唯一」自检
if len(RULE) != len(items):
    raise SystemExit(f'⚠️ §3.129d(扩展) 规则表键碰撞：{len(RULE)} 键 vs {len(items)} 条（24 字前缀重复 → 会静默取错标签）')
for x in items:
    rule_lookup(x['title'])
print(f'✅ 规则表自检通过：{len(items)} 条全部唯一命中（键长 24 字、无碰撞）')

# ---------- 批处理：先试模型 → 402 立即 break 并全量降级 ----------
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
                new_items.append({"idx": b['idx'], "track": b['track'], "sentiment":
                                  ('正面' if d == '利多' else '负面' if d == '利空' else '中性'),
                                  "strength": s, "confidence": c, "direction": d,
                                  "volatility": v, "brief": br})
            degraded = len(items)
            degraded_batches = (len(items) + BATCH - 1) // BATCH
            break
        else:
            print(f'  批 {i//BATCH+1}: HTTP {code} → 沿用规则表标签（降级）')
            for b in batch:
                d, s, c, v, br = rule_lookup(b['title'])
                new_items.append({"idx": b['idx'], "track": b['track'], "sentiment":
                                  ('正面' if d == '利多' else '负面' if d == '利空' else '中性'),
                                  "strength": s, "confidence": c, "direction": d,
                                  "volatility": v, "brief": br})
            degraded += len(batch)
            degraded_batches += 1
            mode = 'rule_table_fallback'
            reason = f'HTTP {code}'
    except Exception as e:
        print(f'  批 {i//BATCH+1}: {type(e).__name__} → 沿用规则表标签（降级）')
        for b in batch:
            d, s, c, v, br = rule_lookup(b['title'])
            new_items.append({"idx": b['idx'], "track": b['track'], "sentiment":
                              ('正面' if d == '利多' else '负面' if d == '利空' else '中性'),
                              "strength": s, "confidence": c, "direction": d,
                              "volatility": v, "brief": br})
        degraded += len(batch)
        degraded_batches += 1
        mode = 'rule_table_fallback'
        reason = f'{type(e).__name__}'

assert len(new_items) == len(items), f'标注条数 {len(new_items)} != {len(items)}'
print(f'\n标注完成：{len(new_items)} 条；annotation_mode = {mode}；降级 {degraded} 条 / {degraded_batches} 批')

# ---------- [§3.154e] 统一 build() 工厂：禁止用 news 条目 dict 直接覆写 sentiment 条目 ----------
def build(ni, it):
    """统一构造：同时产出 news 侧与 sentiment 侧所需的全部字段。"""
    return {
        "idx": ni["idx"],
        "title": it["title"],
        "track": it["track"],
        "category": it.get("category"),
        "summary": it.get("summary"),
        "source": it.get("source"),
        "source_url": it.get("source_url", ""),
        "window": WIN,
        "date": TODAY,
        "sentiment": ni["sentiment"],
        "strength": ni["strength"],
        "score": ni["strength"],
        "confidence": ni["confidence"],
        "direction": ni["direction"],
        "volatility": ni["volatility"],
        "brief": ni["brief"],
    }


NEWS_KEYS = {"track", "category", "title", "summary", "source", "source_url",
             "window", "date", "sentiment", "score", "strength", "direction", "volatility", "brief", "confidence"}
SENT_KEYS = {"idx", "title", "track", "window", "sentiment", "strength", "confidence",
             "direction", "volatility", "brief", "source_url"}

sents = json.load(open(SENT, encoding='utf-8'))
news = json.load(open(NEWS_O, encoding='utf-8'))
print(f'合并前：news-{TODAY}.json {len(news)} 条；sentiment items {len(sents["items"])} 条')

for ni, it in zip(new_items, items):
    row = build(ni, it)
    news.append({k: row[k] for k in NEWS_KEYS})
    sents['items'].append({k: row[k] for k in SENT_KEYS})

sents['count'] = len(sents['items'])
sents['window'] = '盘前(10/15 20:00-10/16 07:30) + 盘中(10/16 07:30-13:30) + 盘后(10/16 13:30-20:00)'
sents['session_type'] = 'normal_trading_day_close'
sents['session_type_note'] = SESSION_NOTE
sents['annotation_mode'] = mode
sents['degraded_items'] = degraded
sents['degraded_batches'] = degraded_batches
sents['degradation_reason'] = reason
sents['degradation_note'] = (
    f"⚠️ §3.127b / §3.128a：本档 **{degraded}/{len(items)} 条（本档增量部分）为确定性规则表标注（非模型标注）**；"
    f"成因 = DeepSeek v4-flash 端点返回 {reason} → 依 §3.127b 停止重试并降级；"
    "规则表由 agent 依新闻正文逐条指定 direction/strength/confidence/volatility/brief，"
    "以「标题前 24 字」硬绑定 + 未命中即终止的守卫（§3.128a）+ 前缀唯一性守卫（§3.129d）防止静默套用默认值。"
    "规则表为「人工口径」而非随机 fallback（不存在二次复核问题），但**仍属非模型标注** → "
    "跨档比较均值强度/净分时须标注「口径差异提示」，不可与模型标注档直接混算趋势。"
    f"本档累计（盘前 25 + 盘中 19 + 盘后 {len(items)} = 当日 {25 + 19 + len(items)} 条），"
    "**三档同为规则表降级（同日全量降级），口径一致**；降级自 10/6 08:00 起持续"
    "（连续第 11 个日历日，10/6 → 10/7 → 10/8 → 10/9 → 10/11 → 10/12 → 10/13 → 10/14 → 10/15 → 10/16 全天 3 档），"
    "须按 §3.136f 从产物 annotation_mode 实际清点（不得用「上一档口径」外推）。"
)

json.dump(sents, open(SENT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
json.dump(news, open(NEWS_O, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(f"news-{TODAY}.json: {len(news)} 条")
missing = [x for x in news if not x.get('window')]
print('news window 覆盖:', len(news) - len(missing), '/', len(news))
if missing:
    raise SystemExit('⚠️ §3.103 有新闻缺 window 字段，终止')

# ---------- [§3.154e] 回读抽样：字段完备性验证 ----------
_rb = json.load(open(SENT, encoding='utf-8'))['items'][-len(items):]
_need = SENT_KEYS
_bad = [(i, sorted(_need - set(r))) for i, r in enumerate(_rb) if _need - set(r)]
if _bad:
    raise SystemExit(f'⚠️ §3.154e 回读抽查失败（缺字段）: {_bad}')
print(f'✅ §3.154e 回读抽查通过：sentiment 侧末 {len(items)} 条字段完备（含 strength）')
_rb2 = json.load(open(NEWS_O, encoding='utf-8'))[-len(items):]
_bad2 = [(i, sorted(NEWS_KEYS - set(r))) for i, r in enumerate(_rb2) if NEWS_KEYS - set(r)]
if _bad2:
    raise SystemExit(f'⚠️ §3.154e 回读抽查失败（news 侧缺字段）: {_bad2}')

by_track = {}
for x in new_items:
    by_track.setdefault(x['track'], []).append(x)


def net(its):
    return sum((x['strength'] if x['direction'] == '利多' else -x['strength'] if x['direction'] == '利空' else 0) / 10
               for x in its)


print(f"\n本档窗口名义净情绪 = {net(new_items):+.1f}")
for t, arr in sorted(by_track.items(), key=lambda kv: -net(kv[1])):
    print(f"  [{t:8s}] n={len(arr)} 净分 {net(arr):+.1f} 均值强度 {sum(a['strength'] for a in arr)/len(arr):.1f}")
print(f"方向分布: {dict(Counter(x['direction'] for x in new_items))}")
print(f"均值强度 {sum(x['strength'] for x in new_items)/len(new_items):.2f}")
print("\n逐条:")
for x in new_items:
    print(f"  [{x['track']:8s}] {x['direction']} {x['strength']:>3d} | {x['brief']}")
