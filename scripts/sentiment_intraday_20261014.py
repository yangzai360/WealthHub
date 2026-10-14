# -*- coding: utf-8 -*-
"""2026-10-14 盘中档（13:45 · 档型③「正常交易日盘中」：A股 长假后第 5 个正常交易日 + 港股正常交易日）：
情绪标注 + 合并入当日 news/sentiment
  ① 先试 DeepSeek v4-flash（max_tokens 8000+，§3.1）
  ② HTTP 402 → 按 §3.127b / §3.128a **停止重试并降级到确定性规则表**（规则表硬绑定标题前缀、未命中即终止）
     ⚠️ §3.129d 前缀键唯一性守卫：rule_lookup() 先收集全部命中键，len(hits)>1 即 SystemExit
  ③ 合并写入 news-2026-10-14.json / sentiment-2026-10-14.json（带 window 字段，§3.112d / §3.103）
⚠️ §3.96：sentiment-<DATE>.json 为 dict {date,window,count,items}，读取须 doc.get('items',[])；strength 字段名（非 score）
⚠️ §3.113e / §3.121c 四类字面量已核：读写路径 = 20261014 / 2026-10-14 / news-intraday-20261014.json；
   日期常量 = 2026-10-14；docstring 档型语义 = 正常交易日盘中；SESSION_NOTE 档型语义同
⚠️ 本档为规则表降级档 —— **连续第 9 个交易日**（10/6 / 10/7 / 10/8 / 10/9 / 10/12 / 10/13 起持续；
   本档 10/14 13:5x 复测端点仍返回 HTTP 402 Insufficient Balance）
⚠️ 单文件日报口径：盘前档 sentiment 条目（24 条）**必须保留**，本档为 **append**（不重置）
⚠️ 暴露加权基准已推进：由 10/12 收盘件改为 **10/13 收盘修正件 `portfolio_close_20261013_fix.json`**（§3.109）
"""
import json, os, time, urllib.request, urllib.error
from collections import Counter

BASE = "/Users/jieyang/Documents/WealthHub"
NEWS_I = os.path.join(BASE, "data/processed/news/news-intraday-20261014.json")
NEWS_D = os.path.join(BASE, "data/processed/news/news-2026-10-14.json")
SENT = os.path.join(BASE, "data/processed/news/sentiment-2026-10-14.json")
BASE_CLOSE = os.path.join(BASE, "data/processed/history/portfolio_close_20261013_fix.json")
TODAY = "2026-10-14"
WIN = "盘中(10/14 07:30-13:30)"
SESSION_NOTE = ("正常交易日盘中档（A股 长假后第 5 个正常交易日 09:30 开盘 + 港股 10/14 正常交易日；"
                "双市场均开市、均可定价；场外基金净值 15:00 后发布）")

# ---------- 确定性规则表（§3.128a 降级路径；key = 标题前 20 字，唯一绑定，未命中即终止） ----------
RULE = {
 '🔴 **中国 9 月 CPI/PPI 于': ('中性', 62, 94, '高', 'PPI+5.0%超预期/CPI+0.9%低于预期 → 剪刀差'),
 '🔴 **国新办 10:00 前三季度进出': ('利多', 64, 94, '高', '前三季39.94万亿+18.8%；9月首破5万亿+27.5%'),
 '🟡 **Reuters 本档跨市场定调（': ('中性', 58, 92, '中', 'PPI四年最快；HSBC下调年末目标9~15%'),
 '🟡 **A股 本档价格事实（本档核心行情': ('利空', 58, 94, '高', '三段式：冲高→午间收平→13:46跳水'),
 '🟡 **A股 本档板块两端（13:46 ': ('中性', 58, 92, '中', '煤炭/PCB/游戏涨 vs 风电/汽车/零售跌'),
 '🟡 **本档政策/审批两条增量：① 商务': ('中性', 52, 88, '低', '民航两用物项出口凭证便利化；仓储指数回升'),
 '🔴 **AI 硬件链本档继续杀跌（组合「': ('利空', 62, 94, '高', '科创50-2.01%；AI硬件补跌、应用走强'),
 '🟡 **「业绩接棒」本档唯一硬样本 + ': ('利多', 58, 90, '中', '超声电子预增90.78~102%；三季报预告密集'),
 '🔴 **白酒价盘本档读数（本档大消费腿的': ('中性', 58, 92, '中', '九涨但仅1款创新高；批零价差归零'),
 '🟡 **大消费本档价格面（13:46 /': ('利多', 60, 92, '中', '中证消费+0.46%逆势；茅台+0.57%'),
 '🟡 **冰雪经济主题本档续接第 2 日（': ('利多', 54, 88, '低', '迪士尼《冰雪奇缘》主题区；冰山冷热2连板'),
 '🟡 **消费政策面本档无新增总量数据（只': ('中性', 50, 88, '低', '双11发布会10/15；本档无新增总量数据'),
 '🔴 **A股医药本档价格面继续走弱（本档': ('利空', 66, 96, '高', 'CRO-2.44%；代理-0.5775%；恒生医疗-2.28%'),
 '🟢 **A股医药本档正向增量（与价格面方': ('利多', 56, 90, '中', '恒瑞SHR-3201获批临床；创新药ETF连4日净申购'),
 '🟡 **美股标普医药腿本档「无新增定价」': ('利空', 54, 94, '高', 'US休市无新定价；挂账区间-779.75~-519.83元'),
 '🟡 **同赛道「超预期但无溢价」范式本档': ('中性', 52, 92, '中', '本档美股休市、无新样本；衔接不重复计分'),
 '🔴 **港股本档低开高走、科网股强势回暖': ('利多', 68, 96, '高', '恒科+1.76%报4209.48；小米+6.79%阿里+4.20%'),
 '🔴 **中金公司本档发布恒生科技「短周期': ('利多', 60, 90, '中', '14.2倍PE为9·24以来最低；12/7扩容至50只'),
 '🟡 **港股本档资金面与结构补充：① 南': ('中性', 56, 90, '中', '南向10/13净卖出4.57亿；恒科ETF两周+19.21亿'),
}


def rule_lookup(t):
    """§3.129d：前缀键必须做唯一性守卫 —— 收集全部命中键，>1 即终止"""
    hits = [k for k in RULE if t.startswith(k)]
    if len(hits) > 1:
        raise SystemExit(f'⚠️ §3.129d 硬守卫：前缀键不唯一 {hits} → 终止（禁止静默取错标签）')
    return RULE[hits[0]] if hits else None


with open('/Users/jieyang/.pi/agent/auth.json') as f:
    KEY = json.load(f)['deepseek']['key']


def call(batch):
    msgs = [{"role": "system", "content": "你是专业的 A股/港股/美股基金经理助理，只输出 JSON 数组。"}]
    body = "\n".join(f"{i}. {x['title']}\n摘要: {x['summary'][:300]}" for i, x in enumerate(batch))
    msgs.append({"role": "user", "content":
                 "对下面每条新闻输出 JSON 数组，每条含 idx/sentiment(正面|中性|负面)/strength(0-100)/confidence(0-100)/"
                 "direction(利多|中性|利空)/volatility(高|中|低)/brief(≤30字)。\n\n" + body})
    req = urllib.request.Request("https://api.deepseek.com/chat/completions",
                                 data=json.dumps({"model": "deepseek-v4-flash", "messages": msgs,
                                                  "max_tokens": 8000, "temperature": 0.2}).encode(),
                                 headers={"Content-Type": "application/json", "Authorization": "Bearer " + KEY})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.load(r)["choices"][0]["message"]["content"]


items = json.load(open(NEWS_I, encoding='utf-8'))
for i, x in enumerate(items):
    x['idx'] = i
print(f'本档待标注 {len(items)} 条（news-intraday-20261014.json）')
if not items:
    raise SystemExit('⚠️ 盘中窗口无待标注条目，终止')

DEGRADED = {'n': 0, 'batches_failed': [], 'reason': None}

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
assert len(old) == 24, f'盘前档 sentiment 条目数异常（{len(old)} ≠ 24）→ 终止（禁止覆盖盘前档）'
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
     '起持续，本档 10/14 13:5x 复测仍 402）→ 依 §3.127b 停止重试并降级；规则表由 agent 依新闻正文逐条指定 '
     'direction/strength/confidence/volatility/brief，并以「标题前 20 字硬绑定 + 未命中即终止（§3.128a）+ '
     '前缀歧义即终止（§3.129d）」守卫防止静默套用默认值。'
     '本档累计（盘前 24 + 盘中 %d = 当日 %d 条）中盘前档亦为规则表降级 → 当日全量口径一致（rule_table_fallback）。'
     '**跨档比较须标注口径差异提示：本档情绪分不可与模型标注档（≤10/5）直接混算趋势。**'
     % (DEGRADED['n'], len(new_items), len(new_items), len(doc['items']))) if DEGRADED['n'] else '')
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
sp = [x for x in new_items if x["direction"] == "利多" and x["strength"] >= 60]
sn = [x for x in new_items if x["direction"] == "利空" and x["strength"] >= 60]
print(f"强正(≥60) n={len(sp)} 均值 {round(sum(x['strength'] for x in sp)/len(sp),1) if sp else 0}")
print(f"强负(≥60) n={len(sn)} 均值 {round(sum(x['strength'] for x in sn)/len(sn),1) if sn else 0}")

# ---------- 赛道净分 + 暴露加权（EXPO 取 10/13 收盘修正件，主口径） ----------
NET_RULE = {"利多": 1, "中性": 0, "利空": -1}
tracks_new = Counter(x["track"] for x in new_items)
net = {}
for t in sorted({x["track"] for x in new_items}):
    net[t] = sum(NET_RULE[x["direction"]] * x["strength"] for x in new_items if x["track"] == t) / 100
print("赛道净分（本档增量口径，Σ(方向×强度)/100）:")
for t in sorted(net, key=lambda k: -tracks_new[k]):
    print(f"  {t:12s} n={tracks_new[t]}  净分 {net[t]:+.2f}")

bc = json.load(open(BASE_CLOSE, encoding='utf-8'))
EXPO = {t: round(v['mv'] / bc['total_mv'] * 100, 2) for t, v in bc['tracks'].items() if t != '现金'}
print("EXPO（10/13 收盘修正件）:", EXPO)
ew = sum(net.get(t, 0.0) * w / 100 for t, w in EXPO.items())
print(f"暴露加权净分 = {ew:+.4f}")
print(f"source_url 覆盖 {sum(1 for x in new_items if x.get('source_url'))}/{len(new_items)}")

agg = {"date": TODAY, "session": "intraday", "window": WIN,
       "session_type": "normal_trading_day_intraday", "session_type_note": SESSION_NOTE,
       "item_count": len(new_items),
       "direction_dist": dict(Counter(x["direction"] for x in new_items)),
       "mean_strength": round(sum(x["strength"] for x in new_items) / len(new_items), 2),
       "annotation_mode": doc["annotation_mode"],
       "net_by_track": {t: round(v, 4) for t, v in net.items()},
       "count_by_track": dict(tracks_new),
       "expo_weights_pct": EXPO,
       "exposure_weighted_net": round(ew, 4),
       "baseline": "portfolio_close_20261013_fix.json",
       "note": "暴露加权口径 = 赛道净分 × 10/13 收盘修正件权重之和（仅五大赛道，现金与宏观权重 0）"}
json.dump(agg, open(os.path.join(BASE, "data/processed/history/sentiment_agg_20261014_intraday.json"),
                    "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("已保存 sentiment_agg_20261014_intraday.json")
