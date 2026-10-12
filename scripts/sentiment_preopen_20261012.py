# -*- coding: utf-8 -*-
"""2026-10-12（周一 · 档型③「正常交易日盘前」· A股 + 港股双市场复市首日）盘前档：
情绪标注（窗口 10/11 20:00 - 10/12 07:30，全量标注）
★★★ 本档为「确定性规则标注降级档」（§3.127b / §3.128a）—— **连续第 6 档** ★★★
  （已降级档序：10/6 → 10/7 → 10/8 → 10/9 → 10/11 → 本档；10/5 及之前为 deepseek_v4_flash 模型标注）
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
⚠️ 暴露权重口径更新：EXPO 取 **10/9 收盘修正件**（portfolio_close_20261009_fix.json）
"""
import json, os, time, urllib.request, urllib.error

BASE = '/Users/jieyang/Documents/WealthHub'
TODAY = '2026-10-12'
NEWS = os.path.join(BASE, f'data/processed/news/news-{TODAY}.json')
SENT = os.path.join(BASE, f'data/processed/news/sentiment-{TODAY}.json')
WINDOW = '盘前(10/11 20:00-10/12 07:30)'
PREF = 20

# ---------- 确定性规则表（本档降级路径；key = 标题前 20 字，唯一绑定） ----------
# (direction, strength, confidence, volatility, brief)
RULE = {
 '🔴 **胡塞武装 10/11 对沙特发动': ('利空', 70, 94, '高', '胡塞四轮打击沙特腹地，阿美设施起火、地缘升级'),
 '🔴 **亚盘油价与贵金属高开、金油同涨（': ('利空', 62, 94, '高', '布油105.59、COMEX金4220.30双高开'),
 '🔴 **俄乌达成「能源停火」与俄方承诺增': ('利多', 58, 88, '高', '俄乌能源停火+俄方增供柴油，油价向下开关'),
 '🔴 **美债长端仍在 5.2% 上方、美': ('利空', 60, 92, '中', '10Y 5.238%高位；12月加息25bp概率69.5%'),
 '🔴 **本周双 CPI 与中国 9 月经': ('中性', 55, 90, '中', '10/14 中美CPI同日；PPI预期升至4.5%'),
 '🟡 **美国「企业盈利与家庭现金流」的 ': ('利空', 55, 88, '中', '标普盈利+25% vs 消费信心12年最低'),
 '🟡 **国内流动性与交易监管本档两条（与': ('利空', 55, 90, '低', '央行7天逆回购零投放；深交所141起监管'),
 '🔴 **港股 10/9 反弹的「外资回补': ('利多', 66, 94, '高', '恒科+3.06%但南向仅2.91亿，外资回补驱动'),
 '🔴 **中概股与中资资产集体走强（本档跨': ('利多', 68, 92, '中', '金龙+2.69%全周+4.25%，人民币偏强'),
 '🟡 **中信证券港股策略：流动性承压但基': ('利多', 56, 88, '中', '中信：港股基本面触底，短期红利仍占优'),
 '🟡 **港股当日盘面结构与本档跨市场映射': ('利多', 54, 90, '中', '港股高开高走；A股高切低、中位+0.59%'),
 '🔴 **《医药工业发展「十五五」规划》目': ('利多', 72, 94, '中', '医药十五五：FIC占全球≥25%、器械≥200个'),
 '🔴 **路透：美国财政部正起草规范美国生': ('利多', 62, 84, '中', '美拟允许多数中国药物许可协议；内外资加仓'),
 '🟡 **医药支付端「双目录」进展与地方落': ('利多', 62, 90, '中', '商保创新药目录与医保目录同步调整'),
 '🟡 **A股 医药「价格面 vs 政策面': ('利空', 58, 92, '中', 'A股医药两日-2.13%，政策强/价格弱背离'),
 '🔴 **美股 10/9（周五）医药生物板': ('利多', 66, 94, '中', 'XLV+1.58%/IYH+1.72%，Moderna+14.21%'),
 '🟡 **礼来（LLY）三源读数：TOGE': ('中性', 56, 84, '中', 'TOGETHER数据积极但支付端受阻；市值近1.1万亿'),
 '🔴 **QDII 挂账机制项（组合强制披': ('中性', 50, 96, '低', '本档无新增美股交易日，挂账沿用+612~+918元'),
 '🔴 **中泰证券《26Q3 食饮前瞻》：': ('利多', 56, 90, '中', '中泰：白酒加速筑底，茅台动销超预期'),
 '🔴 **建投食饮周度跟踪（10/11）：': ('利空', 64, 92, '中', '双节动销下滑10-15%略低于预期；普五750-760'),
 '🔴 **申万食品饮料周报：行业价格底部确': ('利多', 56, 90, '中', '价格底部确认、库存去化；2027有望重回上行'),
 '🟡 **消费高频与股东回报本档增量（与白': ('利多', 58, 90, '低', '二手房网签+10.7%；五粮液分红不低于200亿'),
 '🔴 **10/12 为本周解禁高峰：14': ('利空', 60, 94, '中', '10/12解禁317-320亿，陕西能源238.56亿'),
 '🔴 **三季报预增密集落地、PCB/算力': ('利多', 64, 92, '中', 'PCB/算力/玻纤/液冷链三季报大幅预增'),
 '🟡 **美国 337 调查涉立讯精密、工': ('利空', 56, 88, '中', '337调查涉立讯/工业富联；稀土Q4提价48%'),
 '🟡 **本档机构策略汇总（六家口径，全部': ('利多', 58, 88, '中', '六家机构：修复窗口已开、非全面牛市'),
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
     '**连续第 6 档为规则表降级档（10/6 / 10/7 / 10/8 / 10/9 / 10/11 + 本档）→ 跨档比较时须标注口径差异提示：'
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
# 暴露取值 = 10/9 收盘修正口径（portfolio_close_20261009_fix.json，total_mv 377,040.85）
EXPO = {'大消费': 20.07, 'A股医药': 23.06, '美股标普医药': 15.47, '恒生科技': 8.25, '其他/宽基': 25.39}
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

# 落盘加权汇总（供报告与产物引用）
agg_out = {t: {'n': len(agg.get(t, [])),
               'net_nominal': round(raw_net.get(t, 0.0), 1),
               'net_weighted_100': round(net.get(t, 0.0), 4),
               'expo_pct': EXPO.get(t, 0.0),
               'weighted_contrib': round(net.get(t, 0.0) * EXPO.get(t, 0.0) / 100, 4)}
           for t in list(EXPO) + ['宏观']}
agg_out['_total_nominal'] = round(sum(raw_net.values()), 1)
agg_out['_total_weighted'] = round(ew, 4)
json.dump(agg_out, open(os.path.join(BASE, 'data/processed/history/sentiment_agg_20261012_preopen.json'),
                        'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('\nSAVED sentiment_agg_20261012_preopen.json')
