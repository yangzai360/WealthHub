# -*- coding: utf-8 -*-
"""2026-10-09 盘中档（13:45 · 档型③「正常交易日盘中」：A股 长假后第 2 个交易日 + 港股正常交易日）：
情绪标注 + 合并入当日 news/sentiment
  ① 先试 DeepSeek v4-flash（max_tokens 8000+，§3.1）
  ② HTTP 402 → 按 §3.127b / §3.128a **停止重试并降级到确定性规则表**（规则表硬绑定标题前缀、未命中即终止）
     ⚠️ §3.129d 前缀键唯一性守卫：rule_lookup() 先收集全部命中键，len(hits)>1 即 SystemExit
  ③ 合并写入 news-2026-10-09.json / sentiment-2026-10-09.json（带 window 字段，§3.112d / §3.103）
⚠️ §3.96：sentiment-<DATE>.json 为 dict {date,window,count,items}，读取须 doc.get('items',[])；strength 字段名（非 score）
⚠️ §3.113e / §3.121c 四类字面量已核：读写路径 = 20261009 / 2026-10-09 / news-intraday-20261009.json；
   日期常量 = 2026-10-09；docstring 档型语义 = 正常交易日盘中；SESSION_NOTE 档型语义同
⚠️ 本档为规则表降级档 —— **连续第 4 档**（10/6 / 10/7 / 10/8 + 本档）→ 跨档比较须标注口径差异
⚠️ 单文件日报口径：盘前档 sentiment 条目（25 条）**必须保留**，本档为 **append**（不重置）
"""
import json, os, time, urllib.request, urllib.error
from collections import Counter

BASE = "/Users/jieyang/Documents/WealthHub"
NEWS_I = os.path.join(BASE, "data/processed/news/news-intraday-20261009.json")
NEWS_D = os.path.join(BASE, "data/processed/news/news-2026-10-09.json")
SENT = os.path.join(BASE, "data/processed/news/sentiment-2026-10-09.json")
TODAY = "2026-10-09"
WIN = "盘中(10/9 07:30-13:30)"
SESSION_NOTE = ("正常交易日盘中档（A股 长假后第 2 个正常交易日 09:30 开盘 + 港股 10/9 正常交易日；"
                "双市场均开市、均可定价；场外基金净值 15:00 后发布）")

# ---------- 确定性规则表（§3.128a 降级路径；key = 标题前 20 字，唯一绑定，未命中即终止） ----------
RULE = {
 '🔴 **【盘前档更正】9 月金融数据（M': ('中性', 52, 94, '低', '9月金融数据公布时点更正为10/12或10/15'),
 '🟡 **央行 10/9 早盘公告：将开展': ('中性', 55, 94, '低', '11000亿买断式逆回购续作，资金面平稳'),
 '🔴 **美东 10/8（周四）收盘：三大': ('利空', 62, 95, '高', '纳指-1.25%费半-3.39%，科技全线杀跌'),
 '🟡 **美债长端 10/8 冲高回落：1': ('中性', 58, 93, '中', '10Y回落5.23%vs30Y拍卖5.618%创新高'),
 '🔴 **国际油价本档继续高位：WTI 1': ('利空', 62, 94, '高', '油价高位，通胀预期上行压制贴现率'),
 '🟡 **美股 10/8 财报与事件三条（': ('中性', 52, 90, '低', '百事营收超预期但下调利润增速；港股审计声明'),
 '🔴 **港股 10/9 高开高走、与 A': ('利多', 72, 96, '高', '恒科+2.35%为本轮破位以来最强单日'),
 '🟢 **小米集团-W 10/9 盘中一度': ('利多', 68, 92, '中', '小米澎程锁单破7万台，小米+8.20%'),
 '🔴 **港股芯片股本档承压、与科网股形成': ('利空', 60, 92, '中', '华虹-1.57%兆易-2.26%，恒科内部反向'),
 '🟡 **南向资金 10/8 追踪（本档补': ('中性', 55, 90, '低', '南向净买入64.77亿港元，占比连续低于四成'),
 '🔴 **国家药监局 10/8 发布《关于': ('利多', 68, 93, '中', '中药品种保护公告，中药板块逆市走强'),
 '🟢 **众生药业创新多肽药物 RAY12': ('利多', 66, 93, '中', 'RAY1225减重III期达主要终点，个股+6%'),
 '🔴 **A股医药 10/9 早盘整体承压': ('利空', 68, 95, '高', '早盘CXO创新药杀跌、午后回补，主力净流出19亿'),
 '🟡 **医药监管与产业增量四条（跨层次、': ('中性', 55, 90, '低', '集采质量监管加码；医药估值处中性分位'),
 '🟢 **A股 大消费 10/9 逆市走强': ('利多', 68, 94, '中', '食品饮料居31行业涨幅第2，主力净流入3.27亿'),
 '🔴 **白酒「酒价内参」10/9 读数（': ('利空', 68, 94, '中', '12品一涨十一跌，总价创13天新低，普五失守800'),
 '🟢 **双节消费结构与乳业周期两条（本档': ('利多', 62, 90, '中', '服务强商品稳；原奶价9月起进入上行周期'),
 '🔴 **A股 10/9「低开低走 → 午': ('利空', 66, 96, '高', '创业板盘中破3000，半日1.17万亿放量4300只跌'),
 '🔴 **申万一级行业 10/9 半日全谱': ('利空', 66, 95, '高', '6涨25跌，煤炭+1.66%vs电子-5.22%极差6.88pct'),
 '🟡 **A股 其他增量三条：① 江淮汽车': ('中性', 52, 90, '低', '两融+43亿未去化；国债期货全线上涨'),
 '🟡 **莫德纳（Moderna, MRN': ('中性', 52, 92, '低', 'MRNA纳入纳指100，市值事件非基本面事件'),
 '🔴 **美东 10/8 医药生物个股多数': ('利空', 62, 96, '中', '礼来-1.58%赛默飞-1.56%，超额仅+0.08pct'),
 '🟡 **本档美股标普医药腿的「分母端」读': ('中性', 55, 92, '中', '10Y-6bp边际友好vs30Y拍卖最高，强制并列'),
}


def rule_lookup(t):
    hits = [k for k in RULE if t.startswith(k)]
    if len(hits) > 1:
        raise SystemExit(f"⚠️ §3.129d 前缀歧义「{t[:20]}」→ {' / '.join(hits)}")
    return RULE[hits[0]] if hits else None


key = json.load(open('/Users/jieyang/.pi/agent/auth.json'))['deepseek']['key']
items = json.load(open(NEWS_I, encoding='utf-8'))
for i, it in enumerate(items, 1):
    it['idx'] = i
print(f"待标注 {len(items)} 条")

PROMPT = """你是A股/港股/美股医药与消费行业的资深卖方分析师。对下列新闻逐条做情绪标注，只输出 JSON 数组，不要任何解释。

每条输出字段：
- idx: 新闻序号（整数）
- sentiment: 正面/中性/负面
- strength: 0-100 强度分（对市场情绪冲击力度）
- confidence: 0-100 置信度（信息确定性）
- direction: 利多/利空/中性（对该新闻所属赛道的价格影响方向）
- volatility: 低/中/高（预期波动幅度）
- brief: 一句话中文摘要（不超过 25 字）

要求：严格基于新闻文本，不臆造；只输出 JSON 数组，不要 markdown 代码块。

新闻列表：
"""

DEGRADED = {'n': 0, 'batches_failed': [], 'reason': None}


def call(batch):
    lines = [f"{i+1}. [赛道:{n['track']}] {n['title']}" for i, n in enumerate(batch)]
    data = {"model": "deepseek-v4-flash",
            "messages": [{"role": "user", "content": PROMPT + "\n".join(lines)}],
            "max_tokens": 8000, "temperature": 0.3}
    req = urllib.request.Request("https://api.deepseek.com/chat/completions",
                                 data=json.dumps(data).encode(),
                                 headers={"Authorization": f"Bearer {key}",
                                          "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=240) as resp:
        return json.load(resp)['choices'][0]['message']['content']


labeled = {}
B = 5
for s in range(0, len(items), B):
    batch = items[s:s + B]
    got = None
    for attempt in range(2):
        try:
            txt = call(batch).strip()
            if txt.startswith('```'):
                txt = txt.split('```')[1].replace('json', '', 1).strip()
            arr = json.loads(txt)
            if len(arr) != len(batch):
                raise ValueError(f'条数不符 {len(arr)} vs {len(batch)}')
            for j, a in enumerate(arr):
                labeled[batch[j]['idx']] = a
            got = True
            print(f'  批 {s//B+1}: 模型 OK ({len(batch)} 条)')
            break
        except urllib.error.HTTPError as e:
            if e.code == 402:
                print(f'  批 {s//B+1}: HTTP 402 Insufficient Balance → 按 §3.127b 停止重试、'
                      f'本批及后续全部改走确定性规则表')
                DEGRADED['batches_failed'].append(s // B + 1)
                DEGRADED['reason'] = 'HTTP 402 Insufficient Balance（非 429 限流，重试无意义）'
                break
            print(f'  批 {s//B+1} 第{attempt+1}次失败: {e}')
            time.sleep(3)
        except Exception as e:
            print(f'  批 {s//B+1} 第{attempt+1}次失败: {e}')
            time.sleep(3)
    if got is None:
        for n in batch:
            v = rule_lookup(n['title'])
            if v is None:
                raise SystemExit(f"⚠️ §3.128a 硬守卫：规则表未命中「{n['title'][:40]}」→ "
                                 '禁止静默套用默认值，终止（否则会产生伪中性结果）')
            d, st, cf, vo, br = v
            labeled[n['idx']] = {'sentiment': ('正面' if d == '利多' else ('负面' if d == '利空' else '中性')),
                                 'strength': st, 'confidence': cf, 'direction': d,
                                 'volatility': vo, 'brief': br}
        DEGRADED['n'] += len(batch)
        if (s // B + 1) not in DEGRADED['batches_failed']:
            DEGRADED['batches_failed'].append(s // B + 1)
        if DEGRADED['reason'] is None:
            DEGRADED['reason'] = '模型端点不可用'
        print(f'  批 {s//B+1}: 规则表降级 OK ({len(batch)} 条)')

print(f"\n标注完成 {len(labeled)}/{len(items)}；降级 {DEGRADED['n']} 条")
assert len(labeled) == len(items), '标注条数不匹配'

# ---------- 合并写入 ----------
doc = json.load(open(SENT, encoding='utf-8'))
old = doc.get('items', [])
old_win = doc.get('window')
assert len(old) == 25, f'盘前档 sentiment 条目数异常（{len(old)} ≠ 25）→ 终止（禁止覆盖盘前档）'
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
    ('⚠️ §3.127b / §3.128a：本档 %d/%d 条（本档增量部分）为**确定性规则表标注（非模型标注）**；'
     '成因 = DeepSeek v4-flash 端点返回 HTTP 402 `Insufficient Balance`（额度耗尽，非限流；自 10/6 08:00 '
     '起持续、本档 10/9 13:45 复测仍 402）→ 依 §3.127b 停止重试并降级；规则表由 agent 依新闻正文逐条指定 '
     'direction/strength/confidence/volatility/brief，并以「标题前 20 字硬绑定 + 未命中即终止（§3.128a）+ '
     '前缀歧义即终止（§3.129d）」守卫防止静默套用默认值。'
     '本档累计（盘前 25 + 盘中 23 = 当日 %d 条）中盘前档亦为规则表降级 → 当日全量口径一致（rule_table_fallback）。'
     '**跨档比较须标注口径差异提示：本档情绪分不可与模型标注档（≤10/5）直接混算趋势。**'
     % (DEGRADED['n'], len(doc['items']), len(doc['items']))) if DEGRADED['n'] else '')
json.dump(doc, open(SENT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(f"\nsentiment-{TODAY}.json: {len(old)} -> {doc['count']} 条")

# ---------- 写回 news 合并文件 ----------
news = json.load(open(NEWS_D, encoding='utf-8'))
n_before = len(news)
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
print(f"news-{TODAY}.json: {n_before} -> {len(news)} 条")

# ---------- 自检（§3.112d / §3.114a / §3.103） ----------
miss_win = [x for x in news if not x.get("window")]
print(f"⚠️ 缺 window 条目: {len(miss_win)}")
assert not miss_win, f"news-{TODAY}.json 存在缺 window 条目（§3.103/§3.112d）"
nonlocal_win = [x for x in new_items if x.get("window") != WIN]
assert not nonlocal_win, f"本档 window 异常条目: {len(nonlocal_win)}"
miss_win_s = [x for x in doc['items'] if not x.get('window')]
assert not miss_win_s, f"sentiment-{TODAY}.json 存在缺 window 条目: {len(miss_win_s)}"
VALID = {"宏观", "A股医药", "大消费", "美股标普医药", "恒生科技", "其他/宽基"}
bad = {x["track"] for x in new_items} - VALID
assert not bad, f"非法 track 枚举（§3.114a）: {bad}"
print("window / track 守卫通过 ✅")
print("本档方向分布:", dict(Counter(x["direction"] for x in new_items)))
print("本档强度均值:", round(sum(x["strength"] for x in new_items) / len(new_items), 2))
print("合并全档方向分布:", dict(Counter(x["direction"] for x in doc['items'])))
print("合并全档强度均值:", round(sum(x["strength"] for x in doc['items']) / len(doc['items']), 2))
sp = [x for x in new_items if x["direction"] == "利多" and x["strength"] >= 70]
sn = [x for x in new_items if x["direction"] == "利空" and x["strength"] >= 70]
print(f"强正 n={len(sp)} 均值 {round(sum(x['strength'] for x in sp)/len(sp),1) if sp else 0}")
print(f"强负 n={len(sn)} 均值 {round(sum(x['strength'] for x in sn)/len(sn),1) if sn else 0}")
tracks_new = Counter(x["track"] for x in new_items)
print("赛道净分（本档增量口径，Σ(方向×强度)/100）:")
net = {}
for t in sorted(set(x["track"] for x in new_items)):
    v = sum((1 if x["direction"] == "利多" else (-1 if x["direction"] == "利空" else 0)) * x["strength"]
            for x in new_items if x["track"] == t) / 100
    net[t] = v
    print(f"  {t:12s} n={tracks_new[t]}  净分 {v:+.2f}")
EXPO = {'大消费': 20.01, 'A股医药': 23.29, '美股标普医药': 15.68, '恒生科技': 8.22, '其他/宽基': 25.00}
ew = sum(net.get(t, 0.0) * w / 100 for t, w in EXPO.items())
print(f"暴露加权净分 = {ew:+.4f}")
print(f"source_url 覆盖 {sum(1 for x in new_items if x.get('source_url'))}/{len(new_items)}")
for x in new_items:
    print(f"  {x['track']:8s} {x['direction']:2s} {x['strength']:>3d}/{x['confidence']:<3d} {x['volatility']} | {x['brief']}")
