# -*- coding: utf-8 -*-
"""2026-10-07（周三 · 国庆长假第 7 日 · 混合档：A股休市 + 港股续市第 4 日）盘前档：
情绪标注（窗口 10/6 20:00 - 10/7 07:30，全量标注）
★★★ 本档为「确定性规则标注降级档」（§3.127b 强化 / 新增 §3.128a）★★★
  - DeepSeek v4-flash 端点自 10/6 08:00 起（含本档 10/7 08:00 复测）全部批次返回 **HTTP 402 `Insufficient Balance`**
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
TODAY = '2026-10-07'
NEWS = os.path.join(BASE, f'data/processed/news/news-{TODAY}.json')
SENT = os.path.join(BASE, f'data/processed/news/sentiment-{TODAY}.json')
WINDOW = '盘前(10/6 20:00-10/7 07:30)'

# ---------- 确定性规则表（本档降级路径；key = 标题前 8 字，唯一绑定） ----------
RULE = {
 '🔴 美东 10/': ('利多', 70, 96, '中', '美股三大指数齐涨，标普纳指双创收盘新高'),
 '🔴 **美债长端': ('利多', 66, 92, '中', '美债长端自24年高位回落，10Y −2.32bp'),
 '🔴 油价 10/': ('中性', 62, 92, '高', '油价收平但EIA上调油价预期，方向分歧'),
 '🟡 **贵金属重': ('中性', 55, 88, '中', '黄金重回升势，与美债回落互为印证'),
 '🟡 **美元回落': ('利多', 58, 88, '中', '欧元反弹、人民币破6.70，港股汇率侧缓和'),
 '🔴 **加息路径': ('中性', 58, 90, '高', '市场定价暂停vs官员鹰派，缺口持续'),
 '🔴 **日本央行': ('利空', 60, 85, '中', '日央行12月加息概率升至80%，套息风险'),
 '🔴 **中东地缘': ('利空', 80, 88, '高', '曼德海峡控制权争夺+油债相关性35年最高'),
 '🟡 **美银报告': ('利多', 72, 90, '中', '外资对中国股票配置升至基准中性'),
 '🔴 **港股医药': ('利多', 78, 92, '中', '港股医药生物领涨，恒生生科+3.21%'),
 '🔴 **摩根大通': ('利多', 68, 88, '中', '摩根大通看好港股生物科技与CXO'),
 '🟡 **中国生物': ('利多', 58, 85, '低', '正大天晴与STADA生物类似药合作'),
 '🟡 **开源证券': ('利多', 60, 88, '中', '国产创新药27款临床后期，出海后周期'),
 '🔴 **白酒双节': ('中性', 55, 92, '中', '白酒动销个位数下滑，飞天批价回落'),
 '🟡 **白酒渠道': ('中性', 55, 85, '低', '渠道价表8涨3跌132平，信息量低'),
 '🟡 **贵州茅台': ('中性', 48, 90, '低', 'i茅台10/6全天维护，43家自营停业'),
 '🟢 **2026': ('利多', 62, 90, '中', '国庆档票房破10亿元，量强于价'),
 '🟢 **假期客流': ('中性', 55, 90, '中', '10/6客流预计同比−1.2%，量读数反转'),
 '🟢 **假期消费': ('利多', 58, 90, '中', '离岛免税额增速回落，以旧换新196.3亿'),
 '🔴 港股 10/6': ('利多', 66, 96, '高', '港股三大指数收涨，但量能连续2日低于千亿'),
 '🔴 **港股 1': ('中性', 60, 90, '高', '港股结构切换：硬件降温、医药金融地产领涨'),
 '🔴 **智谱 G': ('利多', 74, 92, '中', '智谱接入AWS Bedrock，单日+7.59%'),
 '🔴 **南向资金': ('利空', 62, 92, '中', '南向空窗第5日，反弹成色待10/8验证'),
 '🟡 **港股一级': ('利多', 66, 88, '中', '前三季港股IPO募资+105%，AI公司拟赴港'),
 '🔴 **XLV ': ('利空', 68, 96, '高', 'XLV/IYH转跌，医疗为11板块唯一下跌'),
 '🔴 **全球医药': ('利多', 68, 90, '中', '医药并购BD单日5笔超34亿美元'),
 '🟡 **研发与审': ('中性', 58, 88, '中', 'Genmab ADC数据亮眼vs诺和诺德两条负向'),
 '🟢 **FDA ': ('中性', 52, 90, '低', 'LYTENAVA商业化推进，本档FDA无新批件'),
 '🟡 **本周美股': ('中性', 50, 90, '中', '10/9罗氏决定日、10/14 CPI、10/28议息'),
 '🔴 **华为昇腾': ('利多', 72, 88, '中', '华为称昇腾中国份额超英伟达，950DT年底供货'),
 '🔴 **高盛大幅': ('利多', 70, 92, '中', '高盛上调台积电2028资本开支至980亿美元'),
 '🟡 **AI 基': ('利多', 62, 88, '中', '600亿美元AI芯片融资银团分销+谷歌核电'),
 '🟡 **并购、评': ('利多', 60, 88, '中', '穆迪上调4家中资券商评级，施耐德收购PTC'),
 '🟡 **A股 制': ('利多', 58, 90, '低', '20只基金10/8开启认购，燃油附加费上调'),
 '🟡 **AI 治': ('利空', 55, 85, '中', 'OpenAI数据越权+71%民众反对数据中心'),
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
