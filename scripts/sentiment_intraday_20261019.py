# -*- coding: utf-8 -*-
"""2026-10-19 盘中档（13:45 · **反向混合档**：A股 正常交易日 + 港股重阳节翌日休市）：
情绪标注 + 合并入当日 news/sentiment
  ① 先试 DeepSeek v4-flash（max_tokens 8000+，§3.1）
  ② HTTP 402 → 按 §3.127b / §3.128a **停止重试并降级到确定性规则表**（规则表硬绑定标题前缀、未命中即终止）
     ⚠️ §3.129d 前缀键唯一性守卫：rule_lookup() 先收集全部命中键，len(hits)>1 即 SystemExit
  ③ 合并写入 news-2026-10-19.json / sentiment-2026-10-19.json（带 window 字段，§3.112d / §3.103）
⚠️ §3.96：sentiment-<DATE>.json 为 dict {date,window,count,items}，读取须 doc.get('items',[])；strength 字段名（非 score）
⚠️ §3.121c 四类字面量已核：读写路径 = 20261019 / 2026-10-19 / news-intraday-20261019.json；
   日期常量 = 2026-10-19；docstring 档型语义 = 反向混合档盘中；SESSION_NOTE 档型语义同；
   **BASE_CLOSE 已随 close 序列推进至 10/16 收盘修正件**（§3.109 / §3.149g）
⚠️ 本档为规则表降级档 —— **连续第 14 个日历日**（10/6 起持续）
⚠️ 单文件日报口径：盘前档 sentiment 条目（**16 条**）**必须保留**，本档为 **append**（不重置）
⚠️ 暴露加权基准：10/16 收盘修正件 `portfolio_close_20261016_fix.json`
   ⚠️ 该件 `tracks[].pct_of_total` 可能与其自身 `mv` 不自洽（§3.146a）→ **权重一律 `mv / total_mv` 现算**
"""
import json, os, time, urllib.request, urllib.error
from collections import Counter

BASE = "/Users/jieyang/Documents/WealthHub"
NEWS_I = os.path.join(BASE, "data/processed/news/news-intraday-20261019.json")
NEWS_D = os.path.join(BASE, "data/processed/news/news-2026-10-19.json")
SENT = os.path.join(BASE, "data/processed/news/sentiment-2026-10-19.json")
BASE_CLOSE = os.path.join(BASE, "data/processed/history/portfolio_close_20261016_fix.json")
TODAY = "2026-10-19"
WIN = "盘中(10/19 07:30-13:30)"
SESSION_NOTE = ("反向混合档盘中（A股 正常交易日 09:30 开盘 + 港股 10/19 重阳节翌日休市；"
                "A股 指数/板块/个股/场内 ETF 可定价，港股无当日价格，场外基金净值 15:00 后发布）")

# ---------- 确定性规则表（§3.128a 降级路径；key = 标题前 20 字，唯一绑定，未命中即终止） ----------
RULE = {
 '🔴 **10:00 落地读数①：三季度 ':( '利多', 66, 96, '中', 'Q3 GDP+4.5%超预期；环比+1.2%'),
 '🔴 **10:00 落地读数②（本档最大': ('利多', 68, 96, '高', '9月社零+1.1%远超预期0.5~0.7%'),
 '🟡 **10:00 落地读数③：9 月规': ('中性', 56, 92, '中', '工增+5.5%加速但低于预期6%'),
 '🔴 **10:00 落地读数④（本档最大': ('利空', 58, 94, '中', '固投-7.2%；地产投资-20.6%'),
 '🔴 **A股 日内结构（本档组合估值': ('中性', 58, 96, '高', '沪指+0.34%；超3800股跌；风格切换'),
 '🟢 **政策面「尚未落地」的时点事实': ('中性', 54, 90, '中', '论坛下午开幕；13:45无工具清单'),
 '🔴 **白酒板块「涨幅居前」为今日消费内': ('利多', 64, 94, '高', '中证白酒+1.26%；茅台+0.59%'),
 '🟢 **9 月社零的结构拆解（本档「大消': ('利多', 62, 92, '中', '除汽车+3.9%；吃类+15.8%'),
 '🔴 **消费内部「非酒类」明显走弱（与本': ('利空', 56, 90, '中', '乳业/饮料/餐饮旅游领跌'),
 '🔴 **中药板块逆势走强（组合「A股医药': ('利多', 64, 94, '高', '中证中药+2%；达仁堂涨停'),
 '🟢 **生物制品板块盘中直线拉升（医药内': ('利多', 60, 90, '中', '信诺维+10%；血制品跟涨'),
 '🔴 **医药内部负向细分（本档「A股医药': ('利空', 58, 92, '高', 'CRO/医疗服务/生物科技领跌'),
 '🟢 **ESMO 2026（10/23-': ('利多', 58, 88, '低', '中国12项LBA/5项主席专场'),
 '🟢 **美股标普医药腿的「相对抗跌」结构': ('利多', 56, 90, '低', 'XLV-0.27% vs 纳指-2.15%'),
 '🔴 **【§3.148d 强制条目】美股': ('中性', 54, 94, '低', '挂账-206.5~-137.65元；净值日10/15'),
 '🔴 **港股休市确认 + A股 港股类 ': ('利空', 56, 94, '中', '港股休市；513050-0.69%独市定价'),
 '🟡 **10/20（周二）港股复市首日的': ('中性', 52, 88, '中', 'LPR/GTC/宁德三季报三重日程'),
 '🟡 **中概/港股复市的「先行指标方向冲': ('利空', 54, 88, '中', '金龙-1.30% vs 恒科期货+0.98%'),
 '🟢 **低估值权重方向今日领涨（「其他/': ('利多', 58, 92, '中', '工行新高；中证金融+0.92%'),
 '🔴 **房地产链条为今日最弱方向（「其他': ('利空', 58, 92, '中', '地产低开低走；投资-20.6%'),
 '🟡 **卖方观点与三季报节奏（本档「预期': ('中性', 56, 86, '低', '申万"调整尾声"；预喜率83%'),
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
print(f'本档待标注 {len(items)} 条（news-intraday-20261019.json）')
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
assert len(old) == 16, f'盘前档 sentiment 条目数异常（{len(old)} ≠ 16）→ 终止（禁止覆盖盘前档）'
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
doc['session_type'] = 'reverse_mixed_closed_hk'
doc['session_type_note'] = SESSION_NOTE
doc['degraded_items'] = DEGRADED['n']
doc['degraded_batches'] = DEGRADED['batches_failed']
doc['degradation_reason'] = DEGRADED['reason']
doc['degradation_note'] = (
    ('⚠️ §3.127b / §3.128a：本档 %d/%d 条（本档增量部分）为**确定性规则表标注（非模型标注）**；'
     '成因 = DeepSeek v4-flash 端点返回 HTTP 402 `Insufficient Balance`（额度耗尽，非限流；自 10/6 08:00 '
     '起持续，本档 10/19 13:4x 复测仍 402）→ 依 §3.127b 停止重试并降级；规则表由 agent 依新闻正文逐条指定 '
     'direction/strength/confidence/volatility/brief，并以「标题前 20 字硬绑定 + 未命中即终止（§3.128a）+ '
     '前缀歧义即终止（§3.129d）」守卫防止静默套用默认值。'
     '**跨档比较时本档情绪分不可与模型标注档（≤10/5）直接混算趋势**。') % (DEGRADED['n'], len(new_items)))
json.dump(doc, open(SENT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

news = json.load(open(NEWS_D, encoding='utf-8'))
n_before = len(news)
for it in items:
    a = labeled[it['idx']]
    if 'window' not in it:
        raise SystemExit('❌ window 缺失（§3.103/§3.112d）')
    news.append({**{k: v for k, v in it.items() if k != 'idx'},
                 'strength': a['strength'], 'direction': a['direction'],
                 'confidence': a['confidence'], 'volatility': a['volatility'], 'brief': a['brief']})
json.dump(news, open(NEWS_D, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
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

# ---------- 赛道净分 + 暴露加权 ----------
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
print("EXPO（10/16 收盘修正件，mv/total_mv 现算）:", EXPO)
ew = sum(net.get(t, 0.0) * w / 100 for t, w in EXPO.items())
print(f"暴露加权净分 = {ew:+.4f}")
print(f"source_url 覆盖 {sum(1 for x in new_items if x.get('source_url'))}/{len(new_items)}")
