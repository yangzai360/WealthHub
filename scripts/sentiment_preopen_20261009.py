# -*- coding: utf-8 -*-
"""2026-10-09（周五 · 档型③「正常交易日盘前」· A股复市第 2 个交易日 + 港股正常交易日）盘前档：
情绪标注（窗口 10/8 18:00 - 10/9 07:30，全量标注）
★★★ 本档为「确定性规则标注降级档」（§3.127b / §3.128a）—— **连续第 4 档** ★★★
  （已降级档序：10/6 → 10/7 → 10/8 → 本档；10/5 及之前为 deepseek_v4_flash 模型标注）
  - DeepSeek v4-flash 端点本档 08:0x 复测仍返回 **HTTP 402 `Insufficient Balance`**
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
TODAY = '2026-10-09'
NEWS = os.path.join(BASE, f'data/processed/news/news-{TODAY}.json')
SENT = os.path.join(BASE, f'data/processed/news/sentiment-{TODAY}.json')
WINDOW = '盘前(10/8 20:00-10/9 07:30)'
PREF = 20

# ---------- 确定性规则表（本档降级路径；key = 标题前 20 字，唯一绑定） ----------
# (direction, strength, confidence, volatility, brief)
RULE = {
 '🔴 **美东 10/8（周四）收盘：三大': ('利空', 58, 96, '中', '美股分化：道指+0.10%、标普-0.47%、纳指-1.25%'),
 '🔴 **美债长端「拍卖定价值得关注但未失': ('利空', 62, 93, '高', '30Y拍卖收益率5.618%认购2.54，欧债压力第二源'),
 '🔴 **国际油价显著上涨（本档方向性最强': ('利空', 64, 95, '高', 'WTI+3.64%布伦特+4.07%，供给中断驱动'),
 '🔴 **中国人民银行阐明人民币汇率政策立': ('中性', 58, 92, '低', '央行重申有管理浮动，防汇率超调负反馈'),
 '🔴 **财政部 1,500 亿元中央金融': ('中性', 55, 94, '低', '1500亿注资特别国债发行；央行净回笼6085亿'),
 '🟡 **地缘与能源两条（方向相反，须并列': ('中性', 58, 85, '高', '特朗普称不攻击伊朗vs油价与航运附加费上调'),
 '🟡 **海外产业与宏观三条（背景读数，方': ('中性', 52, 90, '中', '三星Q3低于预估；WTO上调；厄尔尼诺至2027年2月'),
 '🟡 **CME 加息预期与官员表态（本档': ('利空', 58, 92, '中', '12月加息25bp概率升至67.6%，路径未转向'),
 '🔴 **港股 10/8 放量下跌：恒生科': ('利空', 78, 96, '高', '恒科-2.89%创2024年9月来新低，成交放大119%'),
 '🔴 **香港银行股 10/8 重挫并成为': ('利空', 62, 94, '中', '汇丰-4.87%渣打-5.5%，合计拖累恒指逾100点'),
 '🟡 **外资对中国股票配置的「结构性拐点': ('利多', 58, 88, '中', '美银：主动基金对华配置由低配回升至中性'),
 '🟡 **港股大模型价格战与 AI 硬件链': ('利空', 66, 90, '高', 'Anthropic降价90%；光芯片紧缺与跌停背离'),
 '🔴 **国家卫健委、国家发改委印发《医疗': ('利多', 72, 94, '中', '医疗康复护理扩容提升工程实施方案印发'),
 '🔴 **A股 医药创新管线与业绩密集落地': ('利多', 68, 93, '中', '众生药业等创新管线与三季报预增密集落地'),
 '🟡 **医药合规风险读数（本档 A股医药': ('利空', 58, 90, '中', '福建第十二批医药价格招采合规风险'),
 '🟡 **FDA 10/8 相关批件与前沿': ('中性', 50, 92, '低', 'FDA肿瘤批件页面更新，组合无直接暴露'),
 '🔴 **美东 10/8 医疗板块 −0.': ('利空', 62, 96, '中', 'XLV-0.3871%为11板块下跌之三，超额仅+0.08pct'),
 '🟡 **美股医药个股的三条结构性事件（正': ('中性', 55, 90, '中', 'ARGX III期失败-11.83% vs Pacira被收购+44.40%'),
 '🔴 **华泰证券《白酒：双节表现平淡，延': ('利空', 68, 93, '中', '华泰：双节平淡延续分化，动销承压'),
 '🔴 **白酒终端价与批价两口径本档「同向': ('利空', 66, 92, '中', '12大单品终端总价跌至10759元，批价走弱'),
 '🔴 **消费刺激政策增量：国家发展改革委': ('利多', 66, 94, '中', '第四批625亿元超长期特别国债支持以旧换新'),
 '🔴 **A股 10/8 收盘结构：极致分': ('利空', 70, 96, '高', '上证-0.79%创业板-3.15%科创50-4.82%，成交1.69万亿'),
 '🔴 **A股 三季报预增密集披露（10/': ('利多', 64, 92, '中', '多家A股公司三季报大幅预增（东岳硅材等）'),
 '🟡 **产业与制度性增量四条**：① *': ('中性', 50, 90, '低', '中证1000/500样本调整10/9收市后生效'),
 '🟡 **海外科技与 AI 产业链五条（本': ('中性', 55, 88, '中', '英伟达10亿美元投入vs OpenAI收入下调'),
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
     '**连续第 4 档为规则表降级档（10/6 / 10/7 / 10/8 + 本档）→ 跨档比较时须标注口径差异提示：'
     '本档情绪分不可与模型标注档（≤10/5）直接混算趋势。**'
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
# 暴露取值 = 10/8 收盘修正口径（portfolio_close_20261008.json，total_mv 374,466.56）
EXPO = {'大消费': 20.01, 'A股医药': 23.29, '美股标普医药': 15.68, '恒生科技': 8.22, '其他/宽基': 25.00}
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
