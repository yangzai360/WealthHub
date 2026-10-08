# -*- coding: utf-8 -*-
"""2026-10-08 盘中档（正常交易日 · A股 复市首日 + 港股正常交易日）：情绪标注 + 合并入当日 news/sentiment
  ① 先试 DeepSeek v4-flash（max_tokens 8000+，§3.1）
  ② HTTP 402 → 按 §3.127b / §3.128a **停止重试并降级到确定性规则表**（规则表硬绑定标题前缀、未命中即终止）
     ⚠️ §3.129d 前缀键唯一性守卫：同级两条标题可能共享前 17 字（本档 4/18 与 18/18 均以
        「🟡 **美股 10/8 盘后（北京时段）」开头）→ rule_lookup() 先收集全部命中键，len(hits)>1 即 SystemExit
  ③ 合并写入 news-2026-10-08.json / sentiment-2026-10-08.json（带 window 字段，§3.112d）
⚠️ §3.96：sentiment-<DATE>.json 为 dict {date,window,count,items}，读取须 doc.get('items',[])；strength 字段名（非 score）
⚠️ §3.113e / §3.121c 四类字面量已核：读写路径 = 20261008 / 2026-10-08 / news-intraday-20261008.json；
   日期常量 = 2026-10-08；docstring 档型语义 = 正常交易日盘中（复市首日）；note 字段档型语义同
"""
import json, os, time, urllib.request, urllib.error
from collections import Counter

BASE = "/Users/jieyang/Documents/WealthHub"
NEWS_I = os.path.join(BASE, "data/processed/news/news-intraday-20261008.json")
NEWS_D = os.path.join(BASE, "data/processed/news/news-2026-10-08.json")
SENT = os.path.join(BASE, "data/processed/news/sentiment-2026-10-08.json")
TODAY = "2026-10-08"
WIN = "盘中(10/8 07:30-13:30)"
SESSION_NOTE = ("正常交易日盘中档（A股 10/1-10/7 长假后**复市首日** 09:30 开盘 + 港股 10/8 正常交易日；"
                "港股通/南向恢复首日）")

# ---------- 确定性规则表（§3.128a 降级路径；key = 标题前缀，唯一绑定，未命中即终止） ----------
RULE = {
 '🔴 **央行 10/8 公开市场实际操作落地': ('中性', 62, 92, '中', '净回笼4085亿；DR007 1.3665%偏松'),
 '🔴 **美债长端 10/7 收盘小幅回落但仍处 2002': ('利空', 68, 93, '高', '10Y收5.277%；亚洲时段回5.30%'),
 '🟡 **财政部 10/8 发行 2026 年中央金融机构注资特别国债': ('利多', 58, 90, '中', '1500亿注资特别国债；20只基金齐发'),
 '🟡 **美股 10/8 盘后（北京时段）：三大': ('利多', 56, 88, '中', '美股期指全线上涨；存储股普涨'),
 '🟡 **亚太与地缘两条': ('利空', 60, 88, '高', '日经-0.55%；霍尔木兹口径冲突'),
 '🔴 **A股医药复市首日「过山车」': ('利空', 74, 95, '高', '伏美替尼III期未达终点；医药-2.4%'),
 '🔴 **A股医药盘中出现「先涨停潮': ('中性', 55, 86, '中', '鼠疫传闻脉冲失败；流感阳性19.8%'),
 '🔴 **经国务院批复同意，国家卫生健康委': ('利多', 62, 92, '中', '康复护理扩容工程方案落地'),
 '🟡 **A股医药个股业绩与管线三条': ('利多', 64, 90, '中', '华海药业前三季预增170%~190%'),
 '🔴 **港股 10/8 低开低走、半导体领跌': ('利空', 70, 95, '高', '恒科-2.16%；中芯-5.75%'),
 '🔴 **南向资金（港股通）长假后恢复首日盘中加速流入': ('利多', 62, 86, '中', '南向净流入超48亿港元'),
 '🟡 **机构对港股的最新策略口径': ('中性', 58, 88, '中', '银河：南向修复vs利率压制；反转未确认'),
 '🔴 **白酒「酒价内参」10/8 读数': ('利空', 66, 94, '中', '12品两涨八跌；总价-47至10759'),
 '🟡 **「段永平再度增持贵州茅台」': ('中性', 56, 86, '中', '茅台-0.63%抗跌；主力净流出7.89亿'),
 '🔴 **A股 复市首日「冲高回落、结构性剧烈分化」': ('利空', 68, 95, '高', '科创50-4.76%；3300只个股下跌'),
 '🟡 **A股 复市首日制度与个股层面四条': ('中性', 55, 88, '中', '3家停牌重组；10/10周六休市'),
 '🟡 **（与第 16 条强制并列）A股 复市首日的「分母端约束」': ('利空', 66, 92, '高', '美债压制已由前瞻转已实现定价'),
 '🟡 **美股 10/8 盘后（北京时段）医药': ('中性', 54, 86, '低', '盘后医药股涨跌不一；非收盘口径'),
}


def rule_lookup(t):
    hits = [k for k in RULE if t.startswith(k)]
    if len(hits) > 1:
        raise SystemExit(f"⚠️ 规则表前缀歧义「{t[:24]}」→ {' / '.join(hits)}")
    return RULE[hits[0]] if hits else None


key = json.load(open('/Users/jieyang/.pi/agent/auth.json'))['deepseek']['key']
items = json.load(open(NEWS_I, encoding='utf-8'))
print(f"待标注 {len(items)} 条")

PROMPT = """你是A股/港股/美股医药与消费行业的资深卖方分析师。对下列新闻逐条做情绪标注，只输出 JSON 数组，不要任何解释。

每条输出字段：
- idx: 输入编号
- sentiment: "正面"|"中性"|"负面"
- strength: 0-100 整数（情绪强度）
- confidence: 0-100 整数（对该标注的置信度）
- direction: "利多"|"中性"|"利空"
- volatility: "低"|"中"|"高"（对相关赛道未来 3-5 日波动率的预期）
- brief: 不超过 18 字的要点

判定要求：
1) 站在「组合持仓」视角：组合核心赛道为大消费、A股医药、美股标普医药、恒生科技。
2) 区分「个股催化」与「板块级影响」；个股级催化 strength 不得超过 70。
3) 若同一条新闻同时含正反两面，取净方向并降低 confidence。
4) 本档背景为「2026-10-08 正常交易日盘中（A股 国庆长假后**复市首日** + 港股正常交易日，港股通/南向恢复首日）」：
   上午 A股 冲高回落、结构性剧烈分化（沪指 −0.94% / 创业板指 −3.22% / 科创50 −4.76%、半导体与光刻/CPO 跌停潮、
   海运银行领涨、电池逆市走强）；港股低开低走（恒生科技 13:46 报 4,103.76 / −2.16%，距 4,250 防线 −3.44%，
   半导体与医药双杀）；A股医药因「伏美替尼 FURVENT III 期未达 PFS 主要终点」复市补跌（中证医药 −2.43%）；
   白酒「酒价内参」12 大单品两涨八跌、总价 −47 元至 10,759 元；美债 10Y 收 5.277%、亚洲时段回到 5.30%；
   央行 12,000 亿元买断式逆回购 + 6,060 亿元隔夜逆回购、当日实现净回笼 4,085 亿元（DR007 1.3665% 偏松）。
   → 对恒生科技类新闻须同时考虑「南向回归承接（利多）」与「美债高位 + 半导体杀跌（利空）」两个方向。

新闻列表：
"""


def call(batch):
    body = PROMPT + json.dumps(
        [{"idx": b["idx"], "track": b["track"], "category": b["category"],
          "title": b["title"], "summary": b["summary"]} for b in batch],
        ensure_ascii=False, indent=1)
    data = {"model": "deepseek-v4-flash",
            "messages": [{"role": "user", "content": body}],
            "max_tokens": 8000, "temperature": 0.3}
    req = urllib.request.Request("https://api.deepseek.com/chat/completions",
                                data=json.dumps(data).encode(),
                                headers={"Authorization": f"Bearer {key}",
                                         "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as resp:
        r = json.load(resp)
    return r['choices'][0]['message'].get('content') or ''


DEGRADED = {'n': 0, 'batches_failed': [], 'reason': None}

for i, it in enumerate(items):
    it["idx"] = i + 1

labeled = {}
B = 5
for s in range(0, len(items), B):
    batch = items[s:s + B]
    txt = ""
    got = None
    for attempt in range(2):
        try:
            txt = call(batch)
            if txt.strip().startswith('```'):
                txt = txt.split('```')[1].replace('json', '', 1).strip()
            arr = json.loads(txt)
            if len(arr) != len(batch):
                raise ValueError(f'条数不符 {len(arr)} vs {len(batch)}')
            got = {b['idx']: a for b, a in zip(batch, arr)}
            print(f'  批 {s//B+1}: 模型 OK ({len(batch)} 条)')
            break
        except urllib.error.HTTPError as e:
            if e.code == 402:
                print(f'  批 {s//B+1}: HTTP 402 Insufficient Balance → 按 §3.127b/§3.128a '
                      f'停止重试、本批及后续全部改走确定性规则表')
                DEGRADED['batches_failed'].append(s // B + 1)
                DEGRADED['reason'] = 'HTTP 402 Insufficient Balance（非 429 限流，重试无意义）'
                break
            print(f'  批 {s//B+1} 第{attempt+1}次失败: {e}')
            time.sleep(3)
        except Exception as e:
            print(f'  批 {s//B+1} 第{attempt+1}次失败: {type(e).__name__}: {e}')
            time.sleep(3)
    if got is None:
        for b in batch:
            v = rule_lookup(b['title'])
            if v is None:
                raise SystemExit(f"⚠️ §3.128a 硬守卫：规则表未命中「{b['title'][:40]}」→ "
                                 '禁止静默套用默认值，终止（否则会产生伪中性结果）')
            d, st, cf, vo, br = v
            labeled[b['idx']] = {
                'sentiment': ('正面' if d == '利多' else ('负面' if d == '利空' else '中性')),
                'strength': st, 'confidence': cf, 'direction': d, 'volatility': vo, 'brief': br}
        DEGRADED['n'] += len(batch)
        if (s // B + 1) not in DEGRADED['batches_failed']:
            DEGRADED['batches_failed'].append(s // B + 1)
        if DEGRADED['reason'] is None:
            DEGRADED['reason'] = '模型端点不可用'
        print(f'  批 {s//B+1}: 规则表降级 OK ({len(batch)} 条)')

print(f"\n标注完成 {len(labeled)}/{len(items)}；降级 {DEGRADED['n']} 条")

# ---------- 合并写入 ----------
doc = json.load(open(SENT, encoding='utf-8'))
old = doc.get('items', [])
old_win = doc.get('window')
new_items = []
for it in items:
    a = labeled[it['idx']]
    new_items.append({'idx': len(old) + len(new_items) + 1, 'title': it['title'][:60],
                      'track': it['track'], 'window': WIN,
                      'sentiment': a['sentiment'], 'strength': a['strength'],
                      'confidence': a['confidence'], 'direction': a['direction'],
                      'volatility': a['volatility'], 'brief': a['brief'],
                      'source_url': it.get('source_url', '')})
doc = {'date': TODAY, 'window': (old_win + " + " + WIN) if old_win else WIN,
       'count': len(old) + len(new_items), 'items': old + new_items}
doc['annotation_mode'] = 'rule_table_fallback' if DEGRADED['n'] else 'deepseek_v4_flash'
doc['session_type'] = 'normal_trading_day_intraday'
doc['session_type_note'] = SESSION_NOTE
doc['degraded_items'] = DEGRADED['n']
doc['degraded_batches'] = DEGRADED['batches_failed']
doc['degradation_reason'] = DEGRADED['reason']
doc['degradation_note'] = (
    ('⚠️ §3.127b / §3.128a：本档 %d/%d 条为**确定性规则表标注（非模型标注）**；成因 = DeepSeek v4-flash '
     '端点返回 HTTP 402 `Insufficient Balance`（额度耗尽，非限流；自 10/6 08:00 起持续、本档 10/8 13:45 '
     '复测仍 402）→ 依 §3.127b 停止重试并降级；规则表由 agent 依新闻正文逐条指定 '
     'direction/strength/confidence/volatility/brief，并以「标题前缀唯一绑定 + 未命中即终止 + 前缀歧义即终止」'
     '（§3.128a / §3.129d）守卫防止静默套默认值。'
     '**跨档比较须标注口径差异提示：本档情绪分不可与模型标注档直接混算趋势。**'
     % (DEGRADED['n'], len(doc['items']))) if DEGRADED['n'] else '')
json.dump(doc, open(SENT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(f"\nsentiment-{TODAY}.json: {len(old)} -> {doc['count']} 条")

# ---------- 写回 news 合并文件 ----------
news = json.load(open(NEWS_D, encoding='utf-8'))
for it, ni in zip(items, new_items):
    it2 = dict(it)
    it2.pop("idx", None)
    it2["window"] = WIN
    it2["sentiment"] = ni["sentiment"]
    it2["score"] = ni["strength"]
    it2["strength"] = ni["strength"]
    it2["confidence"] = ni["confidence"]
    it2["direction"] = ni["direction"]
    it2["volatility"] = ni["volatility"]
    it2["brief"] = ni["brief"]
    news.append(it2)
json.dump(news, open(NEWS_D, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"news-{TODAY}.json: {len(news)} 条")

# ---------- 自检（§3.112d / §3.114a） ----------
miss_win = [x for x in news if not x.get("window")]
print(f"⚠️ 缺 window 条目: {len(miss_win)}")
assert not miss_win, f"news-{TODAY}.json 存在缺 window 条目（§3.103/§3.112d）"
nonlocal_win = [x for x in new_items if x.get("window") != WIN]
assert not nonlocal_win, f"本档 window 异常条目: {len(nonlocal_win)}"
VALID = {"宏观", "A股医药", "大消费", "美股标普医药", "恒生科技", "其他/宽基"}
bad = {x["track"] for x in new_items} - VALID
assert not bad, f"非法 track 枚举（§3.114a）: {bad}"
print("window / track 守卫通过 ✅")
print("本档方向分布:", dict(Counter(x["direction"] for x in new_items)))
print("本档强度均值:", round(sum(x["strength"] for x in new_items) / len(new_items), 1))
sp = [x for x in new_items if x["direction"] == "利多" and x["strength"] >= 70]
sn = [x for x in new_items if x["direction"] == "利空" and x["strength"] >= 70]
print(f"强正 n={len(sp)} 均值 {round(sum(x['strength'] for x in sp)/len(sp),1) if sp else 0}")
print(f"强负 n={len(sn)} 均值 {round(sum(x['strength'] for x in sn)/len(sn),1) if sn else 0}")
print("合并全档方向分布:", dict(Counter(x["direction"] for x in doc['items'])))
tracks_new = Counter(x["track"] for x in new_items)
print("赛道净分（本档增量口径，Σ(方向×强度)/100）:")
for t in sorted(set(x["track"] for x in new_items)):
    net = sum((1 if x["direction"] == "利多" else (-1 if x["direction"] == "利空" else 0)) * x["strength"]
              for x in new_items if x["track"] == t) / 100
    print(f"  {t:12s} n={tracks_new[t]}  净分 {net:+.2f}")
