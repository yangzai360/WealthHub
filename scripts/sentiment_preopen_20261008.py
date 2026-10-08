# -*- coding: utf-8 -*-
"""2026-10-08（周四 · 档型③「正常交易日盘前」· A股 + 港股通 复市首日）盘前档：
情绪标注（窗口 10/7 20:00 - 10/8 07:30，全量标注）
★★★ 本档为「确定性规则标注降级档」（§3.127b / §3.128a）—— **连续第 4 档** ★★★
  - DeepSeek v4-flash 端点本档 08:00 复测仍返回 **HTTP 402 `Insufficient Balance`**
    （`{"error":{"message":"Insufficient Balance (request_id: ...)","code":"invalid_request_error"}}`，**非 429 限流**）
    → 按 §3.127b **停止重试并降级**；
  - 降级路径 = **确定性规则表（RULE）**：由 agent 依据新闻正文逐条指定
    `direction / strength / confidence / volatility / brief`；
  - **三重守卫**：① 标题前缀硬绑定（本档前缀长度 20）；② **前缀唯一性检查**（§3.129d：`len(hits) > 1` 即终止）；
    ③ 任一条未命中即 `raise SystemExit`（**禁止静默套用默认值**，§3.128a）；
  - ⚠️ 属性披露：本档情绪分为 **非模型标注**、跨档比较时须标注「口径差异提示」（§3.127b 条款 ③）。
⚠️ §3.103：必须为每条 item 写 `window` 字段
⚠️ §3.112d：`sentiment-*.json` 条目字段名是 `strength`（不是 `score`）；报告引用分数须取合并后的 `news-*.json`
⚠️ §3.102：情绪标注脚本不写 source_url → 写盘前用 news-*.json 按 title[:40] 回填（本档内置）
"""
import json, os, time, urllib.request, urllib.error

BASE = '/Users/jieyang/Documents/WealthHub'
TODAY = '2026-10-08'
NEWS = os.path.join(BASE, f'data/processed/news/news-{TODAY}.json')
SENT = os.path.join(BASE, f'data/processed/news/sentiment-{TODAY}.json')
WINDOW = '盘前(10/7 20:00-10/8 07:30)'
PREF = 20

# ---------- 确定性规则表（本档降级路径；key = 标题前 20 字，唯一绑定） ----------
# (direction, strength, confidence, volatility, brief)
RULE = {
 '🔴 **美联储 9 月会议纪要（北京 ': ('利空', 68, 93, '中', '美联储9月纪要偏鹰，多数官员预计年底前再加息一次'),
 '🔴 **美东 10/7（周三）收盘：三大指数': ('利空', 58, 96, '中', '美股三大指数齐跌，工业领跌、医疗领涨11板块'),
 '🔴 **美债长端盘中再触 2002 ': ('利空', 70, 93, '高', '10Y盘中触5.365%创2002年以来最高后回落'),
 '🟡 **欧美股市、贵金属、原油、加密货币': ('利空', 60, 90, '高', '欧股金油加密同步回落，美元指数收复102'),
 '🔴 **央行今日（10/8）开展 12,0': ('利多', 68, 95, '低', '央行1.2万亿买断式逆回购加量续作，净投放2000亿'),
 '🟡 **长假国内宏观与储备数据三条': ('中性', 55, 90, '低', '外储3.4万亿降1.11%，黄金连增23个月'),
 '🟡 **地缘与能源两条（方向相反': ('中性', 58, 85, '高', '特朗普称伊朗行动须收尾vs IMF称高油价至2027'),
 '🔴 **恒生指数公司公布恒生科技指数「': ('利多', 74, 94, '中', '恒科指数六项修订：成分股30增至50只，12/7生效'),
 '🔴 **港股 10/7（长假收官日）收跌': ('利空', 60, 95, '中', '港股收官跌0.62%，创新药半导体回吐、成交947亿'),
 '🟡 **南向（港股通）今日 10/8 恢': ('利多', 64, 90, '高', '港股通10/8恢复；机构称短期修复但中期未转向'),
 '🟡 **港股 AI 与新股供给两条（增': ('利多', 60, 85, '中', '月之暗面500亿美元估值拟港股IPO，智谱接入AWS'),
 '🔴 **贝达药业（300558）：全资': ('利多', 62, 90, '中', '贝达BPI-572270获FDA临床试验批准，处剂量爬坡'),
 '🔴 **A股 医药个股 10/7 公告三条': ('利空', 62, 92, '中', '艾力斯伏美替尼III期未达终点；华海净利预增170-190%'),
 '🟡 **FDA 10/7 两条批件（前沿': ('利多', 58, 92, '低', 'FDA批准tucatinib与诺华Rhapsido两项批件'),
 '🔴 **美东 10/7 医疗板块 +1.06%': ('利多', 72, 96, '中', '医疗+1.06%领涨11板块，XLV+1.03%超额+1.28pct'),
 '🟡 **美股 10/7 结构分化两条（与': ('中性', 52, 88, '中', '工业-2.14%由农机调查触发；AI个股融资成本担忧'),
 '🔴 **白酒「酒价内参」10/7（假期': ('中性', 60, 90, '中', '飞天跌破1800元纪录终结，12品总价却追平假期高点'),
 '🔴 **申万宏源《食品饮料行业 2026': ('中性', 62, 92, '中', '白酒双节动销-10%但价格库存底部确认，2027望改善'),
 '🟡 **券商双节旺季渠道跟踪（10/': ('中性', 55, 88, '低', '节后飞天批价1720-1730，茅台渠道库存降至约1周'),
 '🟡 **汽车与出行两条（消费结构迁': ('中性', 54, 88, '中', '比亚迪9月+16.99%；纯燃油车占比首破50%'),
 '🔴 **券商「节后 A股 研判」10/': ('利多', 68, 90, '中', '券商共识节后修复、结构性轮动，红十月可期'),
 '🟡 **机构：科技主线或重新占优': ('利多', 62, 88, '中', '机构称科技或重新占优，节后增量资金约300亿'),
 '🟡 **（与第 9、11 条强制并列）机': ('利空', 60, 88, '高', '美债收益率维持高位是节后行情最直接外部约束'),
 '🟡 **AI 与半导体产业链三条（本档': ('利多', 58, 86, '中', '盛美上海在手订单+88.2%；南亚科再涨DRAM合约价20%'),
 '🟡 **10/8（复市首日）A股 停牌与': ('中性', 48, 90, '低', '节后首日3家停牌筹划并购，三安光电解除留置'),
}


def rule_lookup(t):
    """§3.129d：前缀键必须做唯一性守卫 —— 收集全部命中键，>1 即终止"""
    hits = [k for k in RULE if t.startswith(k)]
    if len(hits) > 1:
        raise SystemExit(f'⚠️ §3.129d 硬守卫：前缀键不唯一 {hits} → 终止（禁止静默取错标签）')
    return RULE[hits[0]] if hits else None


with open('/Users/jieyang/.pi/agent/auth.json') as f:
    KEY = json.load(f)['deepseek']['key']

news = json.load(open(NEWS, encoding='utf-8'))
if os.path.exists(SENT):
    sent = json.load(open(SENT, encoding='utf-8'))
else:
    sent = {'date': TODAY, 'window': WINDOW, 'items': []}
sent['items'] = []          # 本档全新窗口 → 重置（单文件日报：当日仅盘前档，不累加）

done = {x['title'][:60] for x in sent['items']}
todo = [n for n in news if n['title'][:60] not in done]
print(f'待标注 {len(todo)} 条（news {len(news)} / sentiment {len(sent["items"])}）')
if not todo:
    raise SystemExit('⚠️ 盘前窗口无待标注条目，终止')

PROMPT = """你是专业的 A 股/港股/美股基金经理助理，负责给财经新闻打情绪标签。
对下面每条新闻输出 JSON 数组，每条包含字段：
- idx: 新闻序号（整数）
- sentiment: 正面/中性/负面
- strength: 0-100 强度分（对市场情绪冲击力度）
- confidence: 0-100 置信度（信息确定性）
- direction: 利多/利空/中性（对该新闻所属赛道的价格影响方向）
- volatility: 低/中/高（预期波动幅度）
- brief: 一句话中文摘要（不超过 25 字）

要求：
1) 严格基于新闻文本，不臆造数据
2) 赛道归属已给定（track 字段），direction 按该赛道价格方向判断
3) 只输出 JSON 数组，不要任何解释文字、不要 markdown 代码块

新闻列表：
"""

DEGRADED = {'n': 0, 'batches_failed': [], 'reason': None}


def call(batch):
    lines = []
    for i, n in enumerate(batch):
        lines.append(f"{i+1}. [赛道:{n['track']}] {n['title']}")
    data = {"model": "deepseek-v4-flash",
            "messages": [{"role": "user", "content": PROMPT + "\n".join(lines)}],
            "max_tokens": 8000, "temperature": 0.3}
    req = urllib.request.Request("https://api.deepseek.com/chat/completions",
                                 data=json.dumps(data).encode(),
                                 headers={"Authorization": f"Bearer {KEY}",
                                          "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=240) as resp:
        return json.load(resp)['choices'][0]['message']['content']


def rule_batch(batch):
    out = []
    for n in batch:
        v = rule_lookup(n['title'])
        if v is None:
            raise SystemExit(f"⚠️ §3.128a 硬守卫：规则表未命中「{n['title'][:40]}」→ "
                             '禁止静默套用默认值，终止（否则会产生伪中性结果）')
        d, st, cf, vo, br = v
        out.append((n, {'sentiment': ('正面' if d == '利多' else ('负面' if d == '利空' else '中性')),
                        'strength': st, 'confidence': cf, 'direction': d,
                        'volatility': vo, 'brief': br}))
    return out


results = []
B = 5
for si in range(0, len(todo), B):
    batch = todo[si:si + B]
    got = None
    for attempt in range(2):
        try:
            txt = call(batch).strip()
            if txt.startswith('```'):
                txt = txt.split('```')[1].replace('json', '', 1).strip()
            arr = json.loads(txt)
            if len(arr) != len(batch):
                raise ValueError(f'条数不符 {len(arr)} vs {len(batch)}')
            got = [(batch[j], a) for j, a in enumerate(arr)]
            print(f'  批 {si//B+1}: 模型 OK ({len(batch)} 条)')
            break
        except urllib.error.HTTPError as e:
            if e.code == 402:
                print(f'  批 {si//B+1}: HTTP 402 Insufficient Balance → 按 §3.127b 停止重试、'
                      f'本批及后续全部改走确定性规则表')
                DEGRADED['batches_failed'].append(si // B + 1)
                DEGRADED['reason'] = 'HTTP 402 Insufficient Balance（非 429 限流，重试无意义）'
                break
            print(f'  批 {si//B+1} 第{attempt+1}次失败: {e}')
            time.sleep(3)
        except Exception as e:
            print(f'  批 {si//B+1} 第{attempt+1}次失败: {e}')
            time.sleep(3)
    if got is None:
        got = rule_batch(batch)
        DEGRADED['n'] += len(batch)
        if (si // B + 1) not in DEGRADED['batches_failed']:
            DEGRADED['batches_failed'].append(si // B + 1)
        if DEGRADED['reason'] is None:
            DEGRADED['reason'] = '模型端点不可用'
        print(f'  批 {si//B+1}: 规则表降级 OK ({len(batch)} 条)')
    results.extend(got)

start = len(sent['items'])
for k, (n, a) in enumerate(results, start=start + 1):
    sent['items'].append({'idx': k, 'title': n['title'][:60], 'track': n['track'],
                          'window': WINDOW,
                          'sentiment': a['sentiment'], 'strength': a['strength'],
                          'confidence': a['confidence'], 'direction': a['direction'],
                          'volatility': a['volatility'], 'brief': a['brief'],
                          'source_url': n.get('source_url', '')})
    n['sentiment'] = a['sentiment']; n['score'] = a['strength']; n['strength'] = a['strength']
    n['direction'] = a['direction']; n['volatility'] = a['volatility']; n['brief'] = a['brief']
    n['confidence'] = a['confidence']

# §3.102：回填 source_url（情绪标注脚本不写该字段）
url_map = {n['title'][:40]: n.get('source_url', '') for n in news}
for x in sent['items']:
    if not x.get('source_url'):
        x['source_url'] = url_map.get(x['title'][:40], '')

sent['window'] = WINDOW
sent['annotation_mode'] = 'rule_table_fallback' if DEGRADED['n'] else 'deepseek_v4_flash'
sent['degraded_items'] = DEGRADED['n']
sent['degraded_batches'] = DEGRADED['batches_failed']
sent['degradation_reason'] = DEGRADED['reason']
sent['degradation_note'] = (
    ('⚠️ §3.127b / §3.128a：本档 %d/%d 条为**确定性规则表标注（非模型标注）**；成因 = DeepSeek v4-flash 端点'
     '返回 HTTP 402 `Insufficient Balance`（额度耗尽，非限流）→ 依 §3.127b 停止重试并降级。'
     '规则表由 agent 依新闻正文逐条指定 direction/strength/confidence/volatility/brief，'
     '并以「标题前 20 字」硬绑定 + **前缀唯一性守卫 + 未命中即终止** 防止静默套默认值（§3.129d）。'
     '**连续第 4 档为规则表降级档（10/5 盘后 / 10/6 三档 + 10/7 三档 + 本档）→ 跨档比较时须标注口径差异提示：'
     '本档情绪分不可与模型标注档直接混算趋势。**'
     % (DEGRADED['n'], len(sent['items']))) if DEGRADED['n'] else '')
json.dump(sent, open(SENT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
json.dump(news, open(NEWS, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

add = sent['items'][start:]
if not add:
    raise SystemExit('⚠️ 盘前窗口 sentiment 为 0 条，终止')
print(f"\n标注模式 = {sent['annotation_mode']}｜降级 {sent['degraded_items']} 条｜"
      f"降级批次 {sent['degraded_batches']}｜原因：{sent['degradation_reason']}")
if any(x.get('window') != WINDOW for x in add):
    raise SystemExit('⚠️ 盘前窗口存在缺失/错误 window 字段，终止')

np_ = sum(1 for x in add if x['direction'] == '利多')
nn_ = sum(1 for x in add if x['direction'] == '利空')
nu_ = sum(1 for x in add if x['direction'] == '中性')
print(f"\n盘前新增 {len(add)} 条：利多 {np_} / 利空 {nn_} / 中性 {nu_}，"
      f"均值强度 {sum(x['strength'] for x in add)/len(add):.1f}")
print(f"sentiment 总计 {len(sent['items'])} 条；带 source_url "
      f"{sum(1 for x in sent['items'] if x.get('source_url'))}/{len(sent['items'])}")
for x in add:
    print(f"  {x['track']:8s} {x['direction']:2s} {x['strength']:>3d}/{x['confidence']:<3d} {x['volatility']} | {x['brief']}")

from collections import defaultdict
agg = defaultdict(list)
for x in add:
    agg[x['track']].append(x['strength'])
print('\n赛道情绪均值：')
for k, v in sorted(agg.items(), key=lambda kv: -sum(kv[1]) / len(kv[1])):
    print(f'  {k}: {sum(v)/len(v):.1f} (n={len(v)})')

# 名义净分 + 暴露加权（§3.104 强制双表）
net = defaultdict(float)
for x in add:
    sg = 1 if x['direction'] == '利多' else (-1 if x['direction'] == '利空' else 0)
    net[x['track']] += sg * x['strength'] / 100
EXPO = {'大消费': 19.87, 'A股医药': 23.57, '美股标普医药': 15.66, '恒生科技': 8.29, '其他/宽基': 24.94}
print('名义净分（Σ方向×强度，原始分）/ 暴露加权：')
ew = 0.0
for t in EXPO:
    print(f'  {t:8s} 净分={net[t]:+.2f}/{len(agg.get(t, []))} 暴露={EXPO[t]:.2f}%')
    ew += net[t] * EXPO[t] / 100
print(f'  → 暴露加权净情绪分 = {ew:+.4f}')
print(f'  → 名义净分合计 = {sum(net.values()):+.4f}（宏观 {net.get("宏观", 0):+.2f} 权重为 0 → 剔除）')

# 赛道净分（原始分，供报告引用）
raw_net = defaultdict(float)
for x in add:
    sg = 1 if x['direction'] == '利多' else (-1 if x['direction'] == '利空' else 0)
    raw_net[x['track']] += sg * x['strength']
print('赛道净分（原始分）:', {k: round(v, 1) for k, v in sorted(raw_net.items(), key=lambda kv: -kv[1])})
print('强信号（≥70）:', [(x['track'], x['strength'], x['direction']) for x in add if x['strength'] >= 70])
