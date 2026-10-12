# -*- coding: utf-8 -*-
"""2026-10-12 盘中档（13:45 · 档型③「正常交易日盘中」：A股 长假后第 3 个交易日 / 本周复市首日 + 港股正常交易日）：
情绪标注 + 合并入当日 news/sentiment
  ① 先试 DeepSeek v4-flash（max_tokens 8000+，§3.1）
  ② HTTP 402 → 按 §3.127b / §3.128a **停止重试并降级到确定性规则表**（规则表硬绑定标题前缀、未命中即终止）
     ⚠️ §3.129d 前缀键唯一性守卫：rule_lookup() 先收集全部命中键，len(hits)>1 即 SystemExit
  ③ 合并写入 news-2026-10-12.json / sentiment-2026-10-12.json（带 window 字段，§3.112d / §3.103）
⚠️ §3.96：sentiment-<DATE>.json 为 dict {date,window,count,items}，读取须 doc.get('items',[])；strength 字段名（非 score）
⚠️ §3.113e / §3.121c 四类字面量已核：读写路径 = 20261012 / 2026-10-12 / news-intraday-20261012.json；
   日期常量 = 2026-10-12；docstring 档型语义 = 正常交易日盘中；SESSION_NOTE 档型语义同
⚠️ 本档为规则表降级档 —— **连续第 7 个交易日**（10/6 / 10/7 / 10/8 / 10/9 / 10/12 起持续）→ 跨档比较须标注口径差异
⚠️ 单文件日报口径：盘前档 sentiment 条目（26 条）**必须保留**，本档为 **append**（不重置）
"""
import json, os, time, urllib.request, urllib.error
from collections import Counter

BASE = "/Users/jieyang/Documents/WealthHub"
NEWS_I = os.path.join(BASE, "data/processed/news/news-intraday-20261012.json")
NEWS_D = os.path.join(BASE, "data/processed/news/news-2026-10-12.json")
SENT = os.path.join(BASE, "data/processed/news/sentiment-2026-10-12.json")
TODAY = "2026-10-12"
WIN = "盘中(10/12 07:30-13:30)"
SESSION_NOTE = ("正常交易日盘中档（A股 长假后第 3 个正常交易日 09:30 开盘 + 港股 10/12 正常交易日；"
                "双市场均开市、均可定价；场外基金净值 15:00 后发布）")

# ---------- 确定性规则表（§3.128a 降级路径；key = 标题前 20 字，唯一绑定，未命中即终止） ----------
RULE = {
 '🔴 **胡塞武装 10/12 今晨再次打': ('利空', 62, 94, '高', '胡塞今晨再袭机场；布伦特破105.5后反转，油价转跌'),
 '🟡 **缓和线索（与第 1 条方向相反 ': ('利多', 58, 92, '中', '俄部分解禁柴油50万吨，油价承压回落'),
 '🔴 **美债长端仍处 2002 年以来最': ('利空', 60, 94, '中', '长端仍处2002年以来最高，分母端压制未解'),
 '🔴 **美国 10 月密歇根大学消费者信': ('利空', 58, 94, '中', '密歇根信心46.3大幅低于预期，短期预期历史最低'),
 '🟡 **飓风伊萨亚斯逼近墨西哥湾：美国墨': ('中性', 55, 92, '中', '飓风致墨西哥湾71.5%产量暂停；油跌铜涨'),
 '🟡 **亚太与海外日历（本档硬约束，只登': ('中性', 55, 92, '低', '日本休市；9月金融数据与中美CPI本周窗口'),
 '🟢 **《医药工业发展「十五五」规划》官': ('利多', 70, 94, '中', '十五五规划全文落地，FIC占比≥25%等量化目标'),
 '🔴 **A股 医药本档价格面继续走弱，且': ('利空', 66, 96, '高', '医药生物-1.21%、创新药-1.85%，全谱走弱'),
 '🟢 **港股创新药本档逆势走强（与 A股': ('利多', 64, 92, '中', '港股创新药+0.38%，云顶新耀+7.36%'),
 '🟡 **三季报窗口 + ESMO 数据窗': ('中性', 56, 90, '低', '三季报与ESMO 10/23催化，券商共识口径'),
 '🟡 **A股 医药本档第二条价格结构读数': ('中性', 54, 90, '低', '医药龙头早盘逆势，午间未能维持'),
 '🟢 **白酒「12 大单品终端零售均价」': ('利多', 66, 92, '中', '12大单品七涨三跌两平，总价创4日新高'),
 '🔴 **大消费板块本档价格与资金面：白酒': ('中性', 56, 92, '中', '白酒Ⅱ+0.85%；大消费宽口径-0.26%'),
 '🟡 **国内消费与产业链两条本档新增读数': ('中性', 52, 90, '低', '大闸蟹价格分化；动力煤站上千元'),
 '🔴 **港股 10/12 午间收盘：恒生': ('利空', 64, 96, '高', '恒指+0.17%恒科-0.55%，高开1.03%后转跌'),
 '🔴 **本档恒科内部最大拖累 = 光通信': ('利空', 68, 94, '高', '光通信PCB领跌，工业富联遭ITC 337调查'),
 '🟡 **港股科网股本档显著分化：小米集团': ('中性', 56, 92, '中', '小米-4%vs网易+2%；内银齐创历史新高'),
 '🟡 **港股医药与航空两条本档结构读数：': ('中性', 54, 90, '低', '港股生物医药早盘强；航空走弱JPM看淡'),
 '🟡 **美股 10/12 交易时段（周一': ('中性', 52, 92, '低', '美股周一未开盘，仅期货读数；债市休市'),
 '🟡 **美股医药两条登记项（本档该赛道的': ('利空', 58, 90, '中', '花旗下调诺和诺德目标价；GLP-1支付端受限'),
 '⚠️ **【旧闻重发登记 · 第 3 个': ('中性', 50, 88, '低', '旧闻重发第3样本，获批日为4月，不计分'),
 '🔴 **A股 10/12 午间收盘全景：': ('利空', 66, 96, '高', '沪指-0.12%创业板-1.27%，超4000股下跌'),
 '🟡 **A股 本档板块两端：涨幅居前 =': ('中性', 58, 94, '高', '银行创新高、影视传媒风电强；农业贵金属跌'),
 '🟢 **周末至本档的政策密度读数（与 1': ('利多', 62, 92, '中', '证监会储备增量工具；财政部5500亿；回购120份'),
 '🟡 **外资对中国资产的配置读数（本档该': ('利多', 60, 90, '中', '外资上调中国评级；全球多头结束四年低配'),
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
assert len(old) == 26, f'盘前档 sentiment 条目数异常（{len(old)} ≠ 26）→ 终止（禁止覆盖盘前档）'
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
     '起持续、本档 10/12 13:45 复测仍 402）→ 依 §3.127b 停止重试并降级；规则表由 agent 依新闻正文逐条指定 '
     'direction/strength/confidence/volatility/brief，并以「标题前 20 字硬绑定 + 未命中即终止（§3.128a）+ '
     '前缀歧义即终止（§3.129d）」守卫防止静默套用默认值。'
     '本档累计（盘前 26 + 盘中 25 = 当日 %d 条）中盘前档亦为规则表降级 → 当日全量口径一致（rule_table_fallback）。'
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
