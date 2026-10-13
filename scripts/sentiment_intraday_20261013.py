# -*- coding: utf-8 -*-
"""2026-10-13 盘中档（13:45 · 档型③「正常交易日盘中」：A股 长假后第 4 个正常交易日 + 港股正常交易日）：
情绪标注 + 合并入当日 news/sentiment
  ① 先试 DeepSeek v4-flash（max_tokens 8000+，§3.1）
  ② HTTP 402 → 按 §3.127b / §3.128a **停止重试并降级到确定性规则表**（规则表硬绑定标题前缀、未命中即终止）
     ⚠️ §3.129d 前缀键唯一性守卫：rule_lookup() 先收集全部命中键，len(hits)>1 即 SystemExit
  ③ 合并写入 news-2026-10-13.json / sentiment-2026-10-13.json（带 window 字段，§3.112d / §3.103）
⚠️ §3.96：sentiment-<DATE>.json 为 dict {date,window,count,items}，读取须 doc.get('items',[])；strength 字段名（非 score）
⚠️ §3.113e / §3.121c 四类字面量已核：读写路径 = 20261013 / 2026-10-13 / news-intraday-20261013.json；
   日期常量 = 2026-10-13；docstring 档型语义 = 正常交易日盘中；SESSION_NOTE 档型语义同
⚠️ 本档为规则表降级档 —— **连续第 8 个交易日**（10/6 / 10/7 / 10/8 / 10/9 / 10/12 起持续，10/13 盘前亦降级）
⚠️ 单文件日报口径：盘前档 sentiment 条目（30 条）**必须保留**，本档为 **append**（不重置）
"""
import json, os, time, urllib.request, urllib.error
from collections import Counter

BASE = "/Users/jieyang/Documents/WealthHub"
NEWS_I = os.path.join(BASE, "data/processed/news/news-intraday-20261013.json")
NEWS_D = os.path.join(BASE, "data/processed/news/news-2026-10-13.json")
SENT = os.path.join(BASE, "data/processed/news/sentiment-2026-10-13.json")
BASE_CLOSE = os.path.join(BASE, "data/processed/history/portfolio_close_20261012.json")
TODAY = "2026-10-13"
WIN = "盘中(10/13 07:30-13:30)"
SESSION_NOTE = ("正常交易日盘中档（A股 长假后第 4 个正常交易日 09:30 开盘 + 港股 10/13 正常交易日；"
                "双市场均开市、均可定价；场外基金净值 15:00 后发布）")

# ---------- 确定性规则表（§3.128a 降级路径；key = 标题前 20 字，唯一绑定，未命中即终止） ----------
RULE = {
 '🔴 **美联储鹰派信号本档再升级：克利夫': ('利空', 66, 94, '高', '哈马克「相对快速」转向限制性；12月加息70.3%/87.7%'),
 '🔴 **霍尔木兹「运输端」本档继续恶化（': ('利空', 64, 94, '高', '10+艘VLCC掉头；保险成本>商品价值1/3'),
 '🟡 **跨资产本档主读数：金跌、银跌、美': ('利空', 58, 92, '中', '金跌银跌+美元18个月高位+油涨，实际利率主导'),
 '🟡 **中国流动性本档读数（与组合 A股': ('利多', 56, 90, '低', 'DR001降至1.2896%；期债放量大涨30年+0.49%'),
 '🟡 **宏观日历（本档硬约束，只登记、不': ('中性', 55, 92, '中', '10/13中国金融数据、10/14中美双CPI'),
 '🔴 **A股 10/13 本档价格事实：': ('中性', 58, 94, '高', 'V型反转：沪指-0.27%→+0.28%；缩量、超3500只下跌'),
 '🟡 **A股 本档板块两端（13:47 ': ('中性', 56, 92, '中', 'PCB/冰雪/白酒涨停 vs 锂电/CRO/半导体下跌'),
 '🟡 **碳酸锂本档独立读数：期货主力 L': ('利空', 60, 92, '中', 'LC2701 -11.79%报104740元/吨，半年腰斩'),
 '🟡 **交易监管本档新规：上期所、郑商所': ('中性', 54, 88, '低', '五交易所拟增六类程序化交易违规情形'),
 '🟡 **机构口径两条（本档新增，均为慢变': ('利多', 56, 88, '低', '中信：银行或向高确定性权益资产重估'),
 '🔴 **大消费本档价格与结构：中证消费 ': ('利空', 60, 94, '中', '中证消费-0.81%、茅台-1.14%；小票涨停与龙头跌背离'),
 '🟡 **冰雪经济概念本档爆发（新主题，非': ('利多', 56, 88, '低', '冰山冷热/大连圣亚等涨停，季节性主题'),
 '🟡 **消费侧宏观背景（本档登记，与 1': ('中性', 54, 88, '低', '本档无新增消费总量数据，方向沿用盘前档'),
 '🟡 **恒瑞医药本档新增解读维度（「模式': ('利多', 60, 90, '中', '首个自研肿瘤药自递EMA，向自主商业化转'),
 '🔴 **A股 医药本档价格面继续走弱（强': ('利空', 64, 96, '高', '医药生物-0.75%、中证医疗-1.02%；CRO调整'),
 '🟢 **医药三季报与审批两条正向增量：①': ('利多', 58, 90, '中', '创业板医药23家18家预增；BMS艾泊度胺获批'),
 '🟡 **美股标普医药腿本档「定价可得性」': ('中性', 55, 92, '低', 'US 10/13未开盘；JNJ/UNH财报落本档之后'),
 '🟡 **QDII 挂账机制项（组合强制披': ('中性', 50, 96, '低', 'US 10/12段区间+201.15~+301.73元；164906不给区间'),
 '🔴 **港股 10/13 本档走弱（高开': ('利空', 62, 94, '高', '恒科午间-1.54%；恒科4,124.79距4,250 -2.947%'),
 '🔴 **港股生物医药 / AI 制药链本': ('利空', 68, 94, '高', '金斯瑞一度-18%，CRO/生物医药全链重挫'),
 '🟡 **港股医药本档重挫的成因拆解（三段': ('中性', 54, 90, '中', '成因拆解条目（不重复计分）：利率/对标/筹码三段'),
 '🟡 **港股本档其他异动（结构补充）：思': ('利空', 58, 88, '中', '思摩尔-12.07%（电子烟退税取消）、先导-9.96%'),
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
print(f'本档待标注 {len(items)} 条（news-intraday-20261013.json）')
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
assert len(old) == 30, f'盘前档 sentiment 条目数异常（{len(old)} ≠ 30）→ 终止（禁止覆盖盘前档）'
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
     '起持续、本档 10/13 13:5x 复测仍 402）→ 依 §3.127b 停止重试并降级；规则表由 agent 依新闻正文逐条指定 '
     'direction/strength/confidence/volatility/brief，并以「标题前 20 字硬绑定 + 未命中即终止（§3.128a）+ '
     '前缀歧义即终止（§3.129d）」守卫防止静默套用默认值。'
     '本档累计（盘前 30 + 盘中 %d = 当日 %d 条）中盘前档亦为规则表降级 → 当日全量口径一致（rule_table_fallback）。'
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

# ---------- 赛道净分 + 暴露加权（EXPO 取 10/12 收盘件，主口径） ----------
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
print("EXPO（10/12 收盘件）:", EXPO)
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
       "baseline": "portfolio_close_20261012.json",
       "note": "暴露加权口径 = 赛道净分 × 10/12 收盘件权重之和（仅五大赛道，现金与宏观权重 0）"}
json.dump(agg, open(os.path.join(BASE, "data/processed/history/sentiment_agg_20261013_intraday.json"),
                    "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("已保存 sentiment_agg_20261013_intraday.json")
