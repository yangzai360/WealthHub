# -*- coding: utf-8 -*-
"""2026-10-20 盘中档（13:45 · **正常交易日**：A股 第 9 个正常交易日 + 港股复市首日）：
情绪标注 + 合并入当日 news/sentiment
  ① 先试 DeepSeek v4-flash（max_tokens 8000+，§3.1）
  ② HTTP 402 → 按 §3.127b / §3.128a **停止重试并降级到确定性规则表**（规则表硬绑定标题前缀、未命中即终止）
     ⚠️ §3.129d 前缀键唯一性守卫：rule_lookup() 先收集全部命中键，len(hits)>1 即 SystemExit
  ③ 合并写入 news-2026-10-20.json / sentiment-2026-10-20.json（带 window 字段，§3.112d / §3.103）
⚠️ §3.96：sentiment-<DATE>.json 为 dict {date,window,count,items}，读取须 doc.get('items',[])；strength 字段名（非 score）
⚠️ §3.121c 四类字面量已核：读写路径 = 20261020 / 2026-10-20 / news-intraday-20261020.json；
   日期常量 = 2026-10-20；docstring 档型语义 = 正常交易日盘中；SESSION_NOTE 档型语义同；
   **BASE_CLOSE 已随 close 序列推进至 10/19 收盘修正件**（§3.109 / §3.149g）
⚠️ 本档为规则表降级档 —— **连续第 16 个日历日**（10/6 起持续）
⚠️ 单文件日报口径：盘前档 sentiment 条目（**32 条**）**必须保留**，本档为 **append**（不重置）
⚠️ 暴露加权基准：10/19 收盘修正件 `portfolio_close_20261019_fix.json`
   ⚠️ 该件 `tracks[].pct_of_total` 与 `mv` 基本自洽，但**权重一律 `mv / total_mv` 现算**（§3.161c）
"""
import json, os, time, urllib.request, urllib.error
from collections import Counter

BASE = "/Users/jieyang/Documents/WealthHub"
NEWS_I = os.path.join(BASE, "data/processed/news/news-intraday-20261020.json")
NEWS_D = os.path.join(BASE, "data/processed/news/news-2026-10-20.json")
SENT = os.path.join(BASE, "data/processed/news/sentiment-2026-10-20.json")
BASE_CLOSE = os.path.join(BASE, "data/processed/history/portfolio_close_20261019_fix.json")
TODAY = "2026-10-20"
WIN = "盘中(10/20 07:30-13:30)"
SESSION_NOTE = ("正常交易日盘中（A股 第 9 个正常交易日 09:30 开盘 + 港股重阳翌日后复市首日；"
                "A股/港股/场内 ETF 均可定价，场外基金净值 15:00 后发布）")

# ---------- 确定性规则表（§3.128a 降级路径；key = 标题前 20 字，唯一绑定，未命中即终止） ----------
RULE = {
 '🟡 **09:00 落地读数①：10 月': ('中性', 55, 96, '低', 'LPR 3.0%/3.5%，连续17月持平'),
 '🟢 **10/19 潘功胜金融街论坛「三': ('利多', 66, 92, '中', 'DR001换锚/基准多元化/退出存基准'),
 '🟢 **10:00 落地读数②（发改委 ': ('利多', 64, 94, '中', '扩大内需方案；服务零售+5%'),
 '🔴 **A股 日内结构（本档组合估值': ('中性', 57, 96, '高', '低开→翻红→再回落；缩量372亿'),
 '🟡 **本档风格切换的完整读数（决定组合': ('中性', 56, 92, '高', '机器人强；金融/白酒弱'),
 '🟢 **发改委明示「扩大养老消费、支持托': ('利多', 64, 92, '中', '扩大养老/托育消费；未定价'),
 '🔴 **白酒板块由 10/19 的「领涨': ('利空', 58, 94, '高', '中证白酒-1.07%；金徽酒领跌'),
 '🟢 **消费的「服务强于商品」结构被发改': ('利多', 60, 90, '中', '服务+5.0% vs 商品+1.1%'),
 '🟡 **消费内部的「防御型抗跌、可选型杀': ('中性', 54, 88, '中', '养老+0.02% > 白酒-1.07%'),
 '🟢 **翰森制药与罗氏达成**超 155': ('利多', 68, 94, '高', '155亿美元ADC平台；首付4亿'),
 '🟢 **ESMO 2026（10/23-': ('利多', 64, 90, '中', '28-30项LBA；10/23开幕'),
 '🟢 **医药三季报预告 66.67% 预': ('利多', 62, 90, '中', '18家66.67%预喜；医博会10/21'),
 '🟢 **A股医药是本档「唯一逆势为正」的': ('利多', 63, 94, '高', '中证医疗+1.52%；唯正赛道'),
 '🔴 **港股复市首日「低开低走」（组合「': ('利空', 62, 94, '高', '恒科-1.65%；阿里-3.86%'),
 '🔴 **恒生科技 4,000 新观察线：': ('利空', 60, 96, '高', '距4000仅+1.01%；未破'),
 '🟡 **港股内部的「结构性对冲」：医药生': ('中性', 55, 88, '中', '恒生医疗+1.57% vs 恒科-1.65%'),
 '🔴 **QDII 三腿净值仍停留在 20': ('利空', 55, 92, '低', '净值停10/16；挂账-313~-209'),
 '🟡 **美股腿的时点事实（阻断「本档可定': ('中性', 54, 92, '低', 'US 21:30开盘；本档无新增定价'),
 '🟢 **人形机器人产业链本档爆发（「其他': ('利多', 62, 86, '中', '全球前五全为中国企业；涨停潮'),
 '🔴 **大金融全线下挫（「其他/宽基」腿': ('利空', 58, 92, '高', '证券ETF-1.74%；与政策叙事反向'),
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
print(f'本档待标注 {len(items)} 条（news-intraday-20261020.json）')
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
doc['window'] = "盘前(10/19 20:00-10/20 07:30) + 盘中(10/20 07:30-13:30)"
doc['session_type'] = "normal_trading_day_intraday"
doc['session_type_note'] = SESSION_NOTE
doc['annotation_mode'] = 'rule_table_fallback'
doc['degraded_items'] = doc.get('degraded_items', 0) + DEGRADED['n']
doc['degraded_batches'] = len(DEGRADED['batches_failed'])
doc['degradation_reason'] = 'HTTP 402'
doc['degradation_note'] = (
    f"⚠️ §3.127b / §3.128a：本档 **{DEGRADED['n']}/{len(new_items)} 条（本档增量）为确定性规则表标注（非模型标注）**；"
    "成因 = DeepSeek v4-flash 端点返回 HTTP 402（Insufficient Balance，非 429 限流）→ 依 §3.127b 停止重试并降级，"
    "**连续第 16 个日历日**。规则表由 agent 依新闻正文逐条指定 direction/strength/confidence/volatility，"
    "并以「标题前 20 字」硬绑定 + 前缀唯一性守卫 + 未命中即终止（§3.128a / §3.129d）防止静默套用默认值。"
    "**跨档比较时本档情绪分不可与模型标注档（≤10/5）直接混算趋势。**")
# 重新聚合
NET_RULE = {"利多": 1, "中性": 0, "利空": -1}
doc['by_track'] = {}
for t in sorted({x['track'] for x in all_items}):
    sub = [x for x in all_items if x['track'] == t]
    doc['by_track'][t] = {"n": len(sub),
                          "nominal_net": round(sum(NET_RULE[x['direction']] * x['strength'] for x in sub) / 100, 2),
                          "mean_strength": round(sum(x['strength'] for x in sub) / len(sub), 2)}
doc['mean_strength'] = round(sum(x['strength'] for x in all_items) / len(all_items), 2)
doc['net_nominal'] = round(sum(NET_RULE[x['direction']] * x['strength'] for x in all_items) / 100, 2)

# ---------- news 合并 ----------
news = json.load(open(NEWS_D, encoding='utf-8'))
n_before_n = len(news)
for it in new_items:
    news.append({**it, 'score': it['strength'], 'date': TODAY})
json.dump(news, open(NEWS_D, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(f"news-{TODAY}.json: {n_before_n} -> {len(news)} 条")
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
print("EXPO（10/19 收盘修正件，mv/total_mv 现算）:", EXPO)
ew = sum(net.get(t, 0.0) * w / 100 for t, w in EXPO.items())
print(f"暴露加权净分 = {ew:+.4f}")
print(f"source_url 覆盖 {sum(1 for x in new_items if x.get('source_url'))}/{len(new_items)}")
