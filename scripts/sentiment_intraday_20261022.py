# -*- coding: utf-8 -*-
"""2026-10-22 盘中档（13:45 · **正常交易日**：A股 第 11 个正常交易日 + 港股正常交易日）：
情绪标注 + 合并入当日 news/sentiment
  ① 先试 DeepSeek v4-flash（max_tokens 8000+，§3.1）
  ② HTTP 402 → 按 §3.127b / §3.128a **停止重试并降级到确定性规则表**（规则表硬绑定标题前缀、未命中即终止）
     ⚠️ §3.129d 前缀键唯一性守卫：rule_lookup() 先收集全部命中键，len(hits)>1 即 SystemExit
  ③ 合并写入 news-2026-10-22.json / sentiment-2026-10-22.json（带 window 字段，§3.112d / §3.103）
⚠️ §3.96：sentiment-<DATE>.json 为 dict {date,window,count,items}，读取须 doc.get('items',[])；strength 字段名（非 score）
⚠️ §3.121c 四类字面量已核：读写路径 = 20261022 / 2026-10-22 / news-intraday-20261022.json；
   日期常量 = 2026-10-22；docstring 档型语义 = 正常交易日盘中；SESSION_NOTE 档型语义同；
   **BASE_CLOSE 已随 close 序列推进至 10/20 收盘修正件**（§3.109 / §3.149g）
⚠️ 本档为规则表降级档 —— **连续第 18 个日历日**（10/6 起持续）
⚠️ 单文件日报口径：盘前档 sentiment 条目（**30 条**）**必须保留**，本档为 **append**（不重置）
⚠️ 暴露加权基准：10/20 收盘修正件 `portfolio_close_20261021_fix.json`
   ⚠️ 该件 `tracks[].pct_of_total` 与 `mv` 自洽性未逐项复核 → **权重一律 `mv / total_mv` 现算**（§3.146a）
"""
import json, os, time, urllib.request, urllib.error
from collections import Counter

BASE = "/Users/jieyang/Documents/WealthHub"
NEWS_I = os.path.join(BASE, "data/processed/news/news-intraday-20261022.json")
NEWS_D = os.path.join(BASE, "data/processed/news/news-2026-10-22.json")
SENT = os.path.join(BASE, "data/processed/news/sentiment-2026-10-22.json")
BASE_CLOSE = os.path.join(BASE, "data/processed/history/portfolio_close_20261021_fix.json")
TODAY = "2026-10-22"
WIN = "盘中(10/22 07:30-13:30)"
SESSION_NOTE = ("正常交易日盘中（A股 第 11 个正常交易日 09:30 开盘 + 港股正常交易日；"
                "A股/港股/场内 ETF 均可定价，场外基金净值 15:00 后发布）")

# ---------- 确定性规则表（§3.128a 降级路径；key = 标题前 20 字，唯一绑定，未命中即终止） ----------
RULE = {
 '🟢 **09:23 落地读数：央行 7 ': ('利多', 58, 92, '中', '隔夜1730亿；净投放480亿'),
 '🔴 **本档核心外因（组合「分母端」的真': ('利空', 62, 94, '高', '美债避险型下行；亚股同跌'),
 '🔴 **亚太连锁：韩国央行维持基准利率 ': ('利空', 68, 94, '高', 'KOSPI-4%；SK海力士-6.2%'),
 '🟡 **10:02 八部门联合印发《产业': ('利多', 55, 88, '中', '产业基础十五五；工业母机逆势'),
 '🟡 **上海前三季度 GDP 43,30': ('中性', 54, 90, '中', '社零-1.1%；生医+7.9%'),
 '🔴 **创新药概念震荡调整（本档医药腿最': ('利空', 66, 94, '高', '近岸蛋白-12%；莱美-5%'),
 '🔴 **医疗服务与 CRO 概念持续走弱': ('利空', 64, 92, '高', '澳洋跌停；昭衍-10%'),
 '🟡 **中金公司 07:47 研报「AI': ('利多', 52, 86, '低', 'AI4S研报；无当日定价力'),
 '🟡 **泰格医药 08:08 公告：控股': ('中性', 52, 90, '中', '方达控股停牌；方向未定'),
 '🔴 **酒价内参 10/22：12 大单': ('利空', 68, 96, '高', '十跌两平无一涨；飞天1788'),
 '🔴 **白酒板块走弱、皇台酒业跌停：金种': ('利空', 58, 90, '高', '皇台跌停；白酒-1.31%'),
 '🔴 **恒生科技午后跌超 5%、失守 3': ('利空', 72, 96, '高', '恒科3787.88；破3800'),
 '🔴 **科网与硬件股集体崩塌：联想集团 ': ('利空', 68, 94, '高', '联想-11%；阿里破100港元'),
 '🔴 **南向资金净卖出逐级扩大：10:0': ('利空', 60, 90, '高', '南向-50亿；逐级加速'),
 '🟡 **腾讯控股 07:38 公告：根据': ('中性', 52, 88, '中', '18亿美元+260亿票据'),
 '🟢 **恒生科技 ETF 逆势获资金布局': ('利多', 50, 84, '低', '恒科ETF逆势申购'),
 '🔴 **QDII 三腿净值仍停留在 20': ('利空', 54, 92, '中', '净值停10/20；挂账-223~-149'),
 '🟡 **美股腿的时点事实（阻断「本档可定': ('利空', 56, 90, '中', '纳指期货-1.5%；US未开盘'),
 '🔴 **A股 单边重挫：上证 −1.65': ('利空', 66, 94, '高', '创业板-4.04%；3900股跌'),
 '🔴 **AI 硬件链全线下挫、主力资金净': ('利空', 62, 92, '高', '主力流出352.82亿；旭创-17亿'),
 '🔴 **宁德时代 A 股市值跌破 1 万': ('利空', 58, 90, '中', '宁德破万亿；连跌第2日'),
 '🟢 **13:23 易方达基金公告：10': ('利多', 54, 88, '中', '自购2亿；10/23起募集'),
}
# §3.146e 双向唯一命中前置断言：键→条目、条目→键 均须恰为 1
assert len({k[:20] for k in RULE}) == len(RULE), '规则表前缀键长度不足 20 字，存在潜在碰撞'


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
print(f'本档待标注 {len(items)} 条（news-intraday-20261022.json）')
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

# ---------- 合并（append，保留盘前档条目） ----------
doc = json.load(open(SENT, encoding='utf-8'))
n_before = len(doc['items'])
new_items = []
for it in items:
    a = labeled[it['idx']]
    new_items.append({**{k: v for k, v in it.items() if k != 'idx'},
                      'idx': it['idx'], 'strength': a['strength'], 'direction': a['direction'],
                      'confidence': a['confidence'], 'volatility': a['volatility'], 'brief': a['brief'],
                      'sentiment': a['sentiment'], 'degraded': True,
                      'degrade_reason': DEGRADED['reason'] or ''})

all_items = doc['items'] + new_items
for i, x in enumerate(all_items):
    x['idx'] = i
doc['items'] = all_items
doc['count'] = len(all_items)
doc['window'] = "盘前(10/21 20:00-10/22 07:30) + 盘中(10/22 07:30-13:30)"
doc['session_type'] = "normal_trading_day_intraday"
doc['session_type_note'] = SESSION_NOTE
doc['annotation_mode'] = 'rule_table_fallback'
doc['degraded_items'] = doc.get('degraded_items', 0) + DEGRADED['n']
doc['degraded_batches'] = len(DEGRADED['batches_failed'])
doc['degradation_reason'] = 'HTTP 402'
doc['degradation_note'] = (
    f"⚠️ §3.127b / §3.128a：本档 **{DEGRADED['n']}/{len(new_items)} 条（本档增量）为确定性规则表标注（非模型标注）**；"
    "成因 = DeepSeek v4-flash 端点返回 HTTP 402（Insufficient Balance，非 429 限流）→ 依 §3.127b 停止重试并降级，"
    "**连续第 18 个日历日**。规则表由 agent 依新闻正文逐条指定 direction/strength/confidence/volatility，"
    "并以「标题前 20 字」硬绑定 + 前缀唯一性守卫 + 未命中即终止（§3.128a / §3.129d）防止静默套用默认值。"
    "**跨档比较时本档情绪分不可与模型标注档（≤10/5）直接混算趋势。**")
NET_RULE = {"利多": 1, "中性": 0, "利空": -1}
doc['by_track'] = {}
for t in sorted({x['track'] for x in all_items}):
    sub = [x for x in all_items if x['track'] == t]
    doc['by_track'][t] = {"n": len(sub),
                          "net": round(sum(NET_RULE[x['direction']] * x['strength'] for x in sub) / 100, 2),
                          "mean_strength": round(sum(x['strength'] for x in sub) / len(sub), 2),
                          "direction_dist": dict(Counter(x['direction'] for x in sub))}
doc['mean_strength'] = round(sum(x['strength'] for x in all_items) / len(all_items), 2)

# ---------- 合并入当日 news（去重键 = title[:60]，含数字，§3.144c） ----------
news = json.load(open(NEWS_D, encoding='utf-8')) if os.path.exists(NEWS_D) else []
n_before_n = len(news)
seen = {x['title'][:60] for x in news}
added_n = 0
for it in new_items:
    if it['title'][:60] in seen:
        continue
    news.append(it)
    seen.add(it['title'][:60])
    added_n += 1
json.dump(news, open(NEWS_D, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(f"news-{TODAY}.json: {n_before_n} -> {len(news)} 条（本档新增 {added_n}）")
json.dump(doc, open(SENT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(f"sentiment-{TODAY}.json: {n_before} -> {doc['count']} 条")

# ---------- 自检（§3.112d / §3.114a / §3.103） ----------
miss_win = [x for x in news if not x.get("window")]
assert not miss_win, f"news-{TODAY}.json 存在缺 window 条目（§3.103/§3.112d）: {len(miss_win)}"
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
print("合并全档强度均值:", doc['mean_strength'])
sp = [x for x in new_items if x["direction"] == "利多" and x["strength"] >= 60]
sn = [x for x in new_items if x["direction"] == "利空" and x["strength"] >= 60]
print(f"强正(≥60) n={len(sp)} 均值 {round(sum(x['strength'] for x in sp)/len(sp),1) if sp else 0}")
print(f"强负(≥60) n={len(sn)} 均值 {round(sum(x['strength'] for x in sn)/len(sn),1) if sn else 0}")

# ---------- 赛道净分 + 暴露加权 ----------
tracks_new = Counter(x["track"] for x in new_items)
net = {}
for t in sorted({x["track"] for x in new_items}):
    net[t] = sum(NET_RULE[x["direction"]] * x["strength"] for x in new_items if x["track"] == t) / 100
print("赛道净分（本档增量口径，Σ(方向×强度)/100）:")
for t in sorted(net, key=lambda k: -tracks_new[k]):
    print(f"  {t:12s} n={tracks_new[t]}  净分 {net[t]:+.2f}")

bc = json.load(open(BASE_CLOSE, encoding='utf-8'))
EXPO = {t: round(v['mv'] / bc['total_mv'] * 100, 2) for t, v in bc['tracks'].items() if t != '现金'}
print("EXPO（10/21 收盘修正件，mv/total_mv 现算）:", EXPO)
ew = sum(net.get(t, 0.0) * w / 100 for t, w in EXPO.items())
print(f"暴露加权净分 = {ew:+.4f}")
print(f"source_url 覆盖 {sum(1 for x in new_items if x.get('source_url'))}/{len(new_items)}")
