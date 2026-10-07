# -*- coding: utf-8 -*-
"""2026-10-07 盘中档（混合档第 4 日 · A股休市 · 港股续市）：情绪标注 + 合并入当日 news/sentiment
  ① 先试 DeepSeek v4-flash（max_tokens 8000+，§3.1）
  ② HTTP 402 → 按 §3.127b / §3.128a **停止重试并降级到确定性规则表**（规则表硬绑定标题、未命中即终止）
  ③ 合并写入 news-2026-10-07.json / sentiment-2026-10-07.json（带 window 字段，§3.112d）
⚠️ §3.96：sentiment-<DATE>.json 为 dict {date,window,count,items}，读取须 doc.get('items',[])；strength 字段名（非 score）
⚠️ §3.113e / §3.121c：本次为全新撰写（非 sed 派生），读写路径已逐项核对为 20261007 / 2026-10-07；
   docstring 档型语义 = 混合档第 4 日（长假最后一日）；note 字段档型语义同
"""
import json, os, time, urllib.request, urllib.error
from collections import Counter

BASE = "/Users/jieyang/Documents/WealthHub"
NEWS_I = os.path.join(BASE, "data/processed/news/news-intraday-20261007.json")
NEWS_D = os.path.join(BASE, "data/processed/news/news-2026-10-07.json")
SENT = os.path.join(BASE, "data/processed/news/sentiment-2026-10-07.json")
TODAY = "2026-10-07"
WIN = "盘中(07:30-13:30)"
SESSION_NOTE = "档型②「混合档」第 4 日 = A股休市（10/1-10/7，长假最后一日）+ 港股续市（10/7 复市后第 4 个交易日）"

# ---------- 确定性规则表（§3.128a 降级路径；key = 标题前缀，唯一绑定，未命中即终止） ----------
RULE = {
 '**🔴 10/7 亚太股市普跌': ('利空', 66, 94, '中', '港股半日恒指-0.53%/恒科-0.91%，成交518亿'),
 '**🔴 美债长端自 24 年高位': ('中性', 64, 92, '高', '10Y 5.271%(-3.8bp)；3Y发行2.62倍'),
 '**🔴 美联储 9 月货币政策': ('中性', 62, 90, '高', 'FOMC 9月纪要北京10/8 02:00公布'),
 '**🔴 原油「供给充裕': ('中性', 70, 88, '高', '沙特阿美下调售价至2020来最低；4船遭袭'),
 '**🟡 国内政策组合拳': ('利多', 62, 88, '中', '财政/货币/购房贴息/资本市场四线政策'),
 '**🟡 假期外围市场的「累计': ('利多', 64, 90, '中', '纳指累+2.75%、日经+5.89%、10Y+14.1bp'),
 '**🔴 港股半导体赛道集体': ('利空', 68, 94, '高', '澜起-6%、兆易-4.07%；南亚科DRAM涨价'),
 '**🔴 恒生科技权重股多数': ('利空', 64, 92, '中', 'MINIMAX-5%、阿里-2.87%；未触及4250'),
 '**🔴 券商对港股给出': ('中性', 60, 88, '中', '银河：港股短期结构防御为主、三条主线'),
 '**🟡 港股量能连续第 3': ('利空', 58, 90, '中', '半日成交518亿连缩3日；南向空窗第5日'),
 '**🔴 港股医药生物与 CRO': ('利空', 72, 96, '高', '金斯瑞-12.74%、昭衍-12%；恒生生科-2.73%'),
 '**🟡 生物安全类事件登记': ('中性', 52, 85, '低', '俄抗鼠疫研究所员工死亡；官方淡化'),
 '**🟡 10/8 A股 复市的医药': ('中性', 56, 88, '中', '9/30医药主力净流入超百亿；敞口39.23%'),
 '**🔴 10/7 酒价内参': ('中性', 60, 94, '中', '12品打包10806(+6)创新高；飞天1799破位'),
 '**🔴 飞天批价（流通口径': ('中性', 58, 90, '中', '普五批价760、终端806；飞天零售破1800'),
 '**🟢 国庆消费高频数据': ('利多', 62, 92, '中', '商圈营业额+5.3%；免税6.48亿+4.99%'),
 '**🟡 白酒渠道价表口径': ('中性', 52, 88, '低', '百荣价表：7涨9跌127平；糖酒会10/15'),
 '**🔴 花旗将 Moderna': ('利空', 62, 90, '中', '花旗下调Moderna至卖出，目标价80→60'),
 '**🔴 10/6（美东）医药权重': ('利多', 58, 90, '中', 'LLY+1.26%；NVO+0.6%；GMAB+10.7%'),
 '**🟡 诊断与早筛商业化': ('利多', 56, 88, '低', 'Abbott血液早筛上市、敏感性81.1%'),
 '**🟡 本档美股标普医药无': ('利空', 55, 92, '中', 'QDII挂账-1127~-1556元；无新增定价'),
 '**🔴 多家券商 10/7 集中': ('利多', 66, 90, '高', '券商共识：修复性反弹、科技+红利哑铃'),
 '**🔴 10/8 假期后首个交易日': ('利多', 58, 88, '中', '10/8 20只基金开募；穆迪上调4券商'),
 '**🟡 存储产业链两条硬读数': ('中性', 58, 86, '高', '南亚科DRAM+20%；长鑫349亿扩产'),
 '**🟡 中国资产风险偏好本档': ('中性', 54, 86, '中', '假期前强后弱；美元101.97；金-0.43%'),
 '**🟡 本档「科技链情绪」': ('中性', 56, 86, '高', '美股AI硬件强/存储弱；港股半导体大跌'),
}


def rule_lookup(t):
    hits = [k for k in RULE if t.startswith(k)]
    if len(hits) > 1:
        raise SystemExit(f"⚠️ 规则表前缀歧义「{t[:20]}」→ {' / '.join(hits)}")
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
4) 本档背景为「国庆长假第 7 日（最后一日）· A股休市（10/8 复市）· 港股续市第 4 个交易日 · 南向资金连续缺席第 5 日 · 港股 10/7 低开低走，半日恒指 −0.53% / 恒生科技 −0.91%，半导体与生物医药领跌（医药生物回吐 10/6 全部涨幅）、机械与地产逆势抗跌；恒生科技日内高 4,222.43、全日未触及 4,250 防线；美债 10Y 5.271%、30Y 5.644% 高位暂歇；布伦特回升至 101.44 美元；FOMC 9 月纪要将于北京 10/8 02:00 公布」——对恒生科技类新闻须同时考虑「外资主导定价 + 无内地增量资金」与「平台型科网走弱」两个方向。

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
doc['session_type'] = 'mixed_market_intraday'
doc['session_type_note'] = SESSION_NOTE
doc['degraded_items'] = DEGRADED['n']
doc['degraded_batches'] = DEGRADED['batches_failed']
doc['degradation_reason'] = DEGRADED['reason']
doc['degradation_note'] = (
    ('⚠️ §3.127b / §3.128a：本档 %d/%d 条为**确定性规则表标注（非模型标注）**；成因 = DeepSeek v4-flash '
     '端点返回 HTTP 402 `Insufficient Balance`（额度耗尽，非限流；自 10/6 08:00 起持续、本档 10/7 13:45 '
     '复测仍 402）→ 依 §3.127b 停止重试并降级；规则表由 agent 依新闻正文逐条指定 '
     'direction/strength/confidence/volatility/brief，并以「标题前缀唯一绑定 + 未命中即终止」守卫防止静默套默认值。'
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
