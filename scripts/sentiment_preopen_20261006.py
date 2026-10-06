# -*- coding: utf-8 -*-
"""2026-10-06（周二 · 国庆长假第 6 日 · 混合档：A股休市 + 港股续市第 3 日）盘前档：
情绪标注（窗口 10/5 20:00 - 10/6 07:30，全量标注）
★★★ 本档为「确定性规则标注降级档」（§3.127b 强化 / 新增 §3.128a）★★★
  - DeepSeek v4-flash 端点 10/6 08:00 起全部批次返回 **HTTP 402 `Insufficient Balance`**
    （`{"error":{"message":"Insufficient Balance"}}`，非 429 限流）→ 按 §3.127b 规则**停止重试并降级**；
  - 降级路径 = **确定性规则表（RULE）**：由 agent 依据新闻正文逐条指定
    `direction / strength / confidence / volatility / brief`，规则表与该 33 条新闻标题一一绑定，
    任何一条标题未命中即 `raise SystemExit`（**禁止静默套用默认值**，否则会重演本档首跑
    「33/33 全部 中性/50/50」的伪中性结果、抹平赛道间差异）；
  - ⚠️ 属性披露：本档情绪分为 **非模型标注**、跨档比较时须标注「口径差异提示」（§3.127b 条款 ③）；
    规则表为**人工口径**（非随机 fallback），故不存在「二次人工复核」问题，但**不可与模型档混算趋势**。
⚠️ §3.88：必须为每条 item 写 `window` 字段；§3.82：差集比对用 title[:60]；§3.72：全局 idx 连续编号
⚠️ §3.102：情绪标注脚本不写 source_url → 写盘前用 news-*.json 按 title[:40] 回填（本档内置）
"""
import json, os, time, urllib.request

BASE = '/Users/jieyang/Documents/WealthHub'
TODAY = '2026-10-06'
NEWS = os.path.join(BASE, f'data/processed/news/news-{TODAY}.json')
SENT = os.path.join(BASE, f'data/processed/news/sentiment-{TODAY}.json')
WINDOW = '盘前(10/5 20:00-10/6 07:30)'

# ---------- 确定性规则表（本档降级路径；key = 标题前 8 字，唯一绑定） ----------
RULE = {
 '🔴 美东 10/5（周': ('利多', 72, 95, '中', '美股三大指数齐涨，纳指创收盘新高'),
 '🔴 美债长端续创 24': ('利空', 78, 92, '高', '10Y/30Y 续创 24 年新高，曲线陡峭化'),
 '🔴 **卖方对「美股': ('中性', 62, 85, '高', 'Wilson 广度背离 vs 花旗看多，须并列'),
 '🔴 国际油价**继续': ('利多', 68, 92, '中', '油价跌破 90，通胀与长端边际缓和'),
 '🔴 **中东地缘本档': ('利空', 80, 88, '高', '胡塞夜间三轮行动，麦加联盟启动集体防御'),
 '🟡 **美元与贵金属': ('中性', 52, 88, '中', '美元反弹至 102.16，黄金微涨、铜强'),
 '🔴 **欧洲本档出现': ('利空', 60, 85, '中', '欧元 17 个月新低，法债利差创危机以来新高'),
 '🟡 **加息路径与实': ('利多', 58, 90, '中', '10 月加息概率降至 24%，服务业仍扩张'),
 '🟡 **亚太与新兴市': ('利多', 62, 88, '中', '日经 +2.4% 破 7 万，台湾加权 +2.55%'),
 '🟡 **本周日历锚点': ('中性', 50, 90, '中', '纪要 10/8、610 亿美元长债拍卖'),
 '🔴 **2026 年诺贝': ('利多', 76, 90, '中', '诺奖光遗传学 A股 映射清单落地'),
 '🔴 **节前最后一个': ('利多', 66, 88, '中', '药明+恒瑞 9/30 主力净流入 12.62 亿'),
 '🟡 **全球医药产业': ('利多', 58, 85, '低', '拜耳 22 亿美元扩产，BD 密度延续'),
 '🔴 **监管对「拥挤': ('中性', 55, 85, '中', 'ADC 单臂数据门槛抬升，载荷换代并行'),
 '🔴 **美股医药本档': ('利多', 70, 96, '中', 'XLV/IYH 同涨 0.72%，超额由负转正'),
 '🔴 **Vaxcyte（P': ('利多', 72, 92, '中', 'VAX-31 Ph3 达终点，收涨 30.7%'),
 '🟡 **FDA 于美东': ('中性', 48, 92, '低', 'Teva 地舒单抗类似药获批'),
 '🟡 **本周美股医药': ('中性', 50, 88, '中', '罗氏 Tecentriq 10/9 决定日等日历'),
 '🔴 **恒生科技指数': ('利多', 74, 85, '高', '恒科夜盘 +1.36% 报 4,245，逼近防线'),
 '🔴 **纳斯达克金龙': ('利多', 78, 92, '高', '金龙中概 +1.71%，阿里 +4.68%'),
 '🟡 **港股「量能承': ('利空', 58, 90, '中', '成交缩量 32.7%，承接力量偏薄'),
 '🟢 **香港市场「制': ('利多', 55, 88, '低', '前三季港股 IPO 募资 3,856 亿港元'),
 '🟡 **香港金融基础': ('中性', 45, 85, '低', '港金结算接驳与 ICE 油轮衍生品'),
 '🔴 **10/5 白酒「': ('利多', 66, 90, '中', '白酒零售与批价同向上行，飞天 1,802'),
 '🟢 **假期客流与返': ('利多', 55, 88, '低', '10/4 跨区域流动 3.05 亿人次、+1.3%'),
 '🟢 **国庆楼市「银': ('利多', 60, 85, '中', '武汉/十堰国庆楼市销售额同比较快增长'),
 '🟡 **假期后半程的': ('中性', 48, 90, '低', '安委办调度假期安全，央视定调消费'),
 '🔴 **华为与高通宣': ('利多', 72, 90, '中', '华为与高通达成多年期专利交叉许可'),
 '🟡 **AI 硬件与代': ('利多', 65, 88, '中', '鸿海 Q3 营收 +47.1%，芯片再提价'),
 '🟡 **美股 Q3 财报': ('利多', 60, 85, '中', '标普 500 Q3 盈利预期同比 +30%'),
 '🟡 **A股 制度与资': ('中性', 50, 88, '低', '券商罚单 260+ 张、公募高管变动 273 起'),
 '🟡 **算力商品化与': ('中性', 52, 85, '中', 'GPU 算力期货上市，RSI 论文警示'),
 '🟡 **大宗商品与债': ('利多', 55, 88, '低', '9 月中国大宗商品价格指数同涨 22.9%'),
}

def rule_lookup(t):
    for k, v in RULE.items():
        if t.startswith(k):
            return v
    return None

with open('/Users/jieyang/.pi/agent/auth.json') as f:
    KEY = json.load(f)['deepseek']['key']

news = json.load(open(NEWS, encoding='utf-8'))
if os.path.exists(SENT):
    sent = json.load(open(SENT, encoding='utf-8'))
else:
    sent = {'date': TODAY, 'window': WINDOW, 'items': []}

done = {x['title'][:60] for x in sent['items']}
todo = [n for n in news if n['title'][:60] not in done]
print(f'待标注 {len(todo)} 条（news {len(news)} / sentiment {len(sent["items"])}）')

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
     '并以「标题前 8 字」硬绑定 + 未命中即终止的守卫防止静默套默认值。'
     '**跨档比较时须标注口径差异提示：本档情绪分不可与模型标注档直接混算趋势。**'
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
print(f"sentiment 总计 {len(sent['items'])} 条；带 source_url {sum(1 for x in sent['items'] if x.get('source_url'))}"
      f"/{len(sent['items'])}")
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
print('名义净分 / 暴露加权：')
ew = 0.0
for t in EXPO:
    print(f'  {t:8s} 净分={net[t]:+.2f}  暴露={EXPO[t]:.2f}%')
    ew += net[t] * EXPO[t] / 100
print(f'  → 暴露加权净情绪分 = {ew:+.4f}')
