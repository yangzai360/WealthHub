# -*- coding: utf-8 -*-
"""2026-10-14（周三 · 档型③「正常交易日盘前」）盘前档：
情绪标注（窗口 10/13 20:00 - 10/14 07:30，全量标注）
★★★ 本档为「确定性规则标注降级档」（§3.127b / §3.128a）—— **连续第 8 档** ★★★
  （已降级档序：10/6 → 10/7 → 10/8 → 10/9 → 10/11 → 10/12 → 10/13 → 本档；10/5 及之前为 deepseek_v4_flash 模型标注）
  - DeepSeek v4-flash 端点本档 08:0x 复测仍返回 **HTTP 402 `Insufficient Balance`**
    → 按 §3.127b **停止重试并降级**；
  - 降级路径 = **确定性规则表（RULE）**：由 agent 依据新闻正文逐条指定
    `direction / strength / confidence / volatility / brief`；
  - **三重守卫**：① 标题前缀硬绑定（本档前缀长度 20）；② **前缀唯一性检查**（§3.129d：`len(hits) > 1` 即终止）；
    ③ 任一条未命中即 `raise SystemExit`（**禁止静默套用默认值**，§3.128a）；
  - ⚠️ 属性披露：本档情绪分为 **非模型标注**、跨档比较时须标注「口径差异提示」（§3.127b 条款 ③）。
⚠️ §3.103：必须为每条 item 写 `window` 字段
⚠️ §3.112d：`sentiment-*.json` 条目字段名是 `strength`（不是 `score`）；报告引用分数须取合并后的 `news-*.json`
⚠️ §3.102：情绪标注脚本不写 source_url → 写盘前用 news-*.json 按 title[:40] 回填（本档内置）
⚠️ 暴露权重口径更新：EXPO 取 **10/13 收盘修正件**（portfolio_close_20261013_fix.json，§3.140a 补正后）
"""
import json, os, time, urllib.request, urllib.error

BASE = '/Users/jieyang/Documents/WealthHub'
TODAY = '2026-10-14'
NEWS = os.path.join(BASE, f'data/processed/news/news-{TODAY}.json')
SENT = os.path.join(BASE, f'data/processed/news/sentiment-{TODAY}.json')
WINDOW = '盘前(10/13 20:00-10/14 07:30)'
PREF = 20

# ---------- 确定性规则表（本档降级路径；key = 标题前 20 字，唯一绑定） ----------
# (direction, strength, confidence, volatility, brief)
RULE = {
 '🔴 **美股 10/13 收盘（财报季': ('利空', 60, 92, '中', '财报季揭幕首日收跌；能源领涨、保健垫底'),
 '🔴 **长鑫存储 4F² DRAM ': ('利空', 66, 92, '高', '长鑫4F²进展致韩股-5.47%，存储链承压'),
 '🔴 **美债长端三日回落近 10bp': ('利多', 60, 92, '中', '10Y 5.2126%、美元回落；分母端缓和'),
 '🟡 **商品三线分化：原油「油涨布': ('中性', 55, 88, '中', '油涨布跌、金冲高回落、银失守60'),
 '🔴 **中东地缘：霍尔木兹海峡单日': ('利空', 64, 92, '高', '6船遇袭；胡塞首次瞄准阿美设施'),
 '🟡 **今日「中美双 CPI」同日落': ('中性', 56, 90, '中', '中国09:30/美国20:30；只登记不预判'),
 '🟡 **《关于发展新质生产力的意见': ('利多', 58, 90, '低', '19项举措、科技创新列五大任务之首'),
 '🟡 **央行 10/13 开展 650': ('中性', 54, 90, '低', '650亿逆回购；30年国债期货创年内新高'),
 '🔴 **A股 10/14 开盘压力项（隔': ('利空', 62, 92, '中', '隔夜存储/半导体链重挫，高开低走风险'),
 '🔴 **三季报预告披露「最密集一晚」': ('利多', 64, 92, '中', '深市54家近九成预喜，PCB/AI链高增'),
 '🔴 **券商「注销式回购」密集落地': ('利多', 60, 90, '中', '券商密集注销式回购，增厚EPS/BPS'),
 '🟡 **首家外商独资银行卡清算机构获': ('中性', 55, 90, '低', 'Visa威士获准筹备清算机构'),
 '🟡 **机构口径（只登记、不采纳）：巨丰': ('中性', 56, 88, '中', '沪指3750支撑；量能低于2万亿仍磨底'),
 '🔴 **双十一正式启动 + 第四批': ('利多', 60, 92, '中', '625亿第四批国补全额下达，双十一启动'),
 '🟡 **中指研究院：今年以来各地出台超': ('利多', 56, 88, '低', '880条楼市政策；公积金利率下调预期'),
 '🟡 **片仔癀：董事长暨法定代表人离': ('利空', 55, 90, '低', '片仔癀董事长离任；猪价环比走弱'),
 '🟡 **A股医药产业端续接：海特生物': ('中性', 52, 88, '低', '海特生物出海授权；价格未参与修复'),
 '🟡 **机构口径（只登记、不采纳）：10 月': ('利多', 58, 88, '中', '10月ESMO为创新药催化剂窗口'),
 '🔴 **强生（JNJ）Q3 后股价': ('利空', 64, 94, '高', 'JNJ指引中值不及预期-5.73%，XLV-1.35%'),
 '🟡 **同板块「超预期但无溢价」第 2': ('中性', 56, 90, '中', '超预期无溢价；IBB-1.6%弱于XLV'),
 '🔴 **QDII 挂账机制项（组合强制披': ('中性', 50, 96, '低', '新增US10/13段，区间-779.75~-519.83元'),
 '🔴 **港股 10/14 开盘前瞻：恒生': ('利空', 62, 92, '中', '恒科距4250防线-2.67%；韩股情绪压制'),
 '🟡 **机构配置口径（只登记、不采纳': ('中性', 55, 88, '中', '结构做多窗口在vs趋势未打开，成对披露'),
 '🟡 **韩国投资者买入中国股票热情不减': ('利多', 56, 88, '低', '奥士康/中芯国际居韩资净买入榜首'),
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

# ---------- §3.129d 强化：双向全覆盖 + 唯一性命中前置断言（本档新增，防「静默取错标签」） ----------
_all_titles = [n['title'] for n in news]
for _k in RULE:
    _m = [t for t in _all_titles if t.startswith(_k)]
    if len(_m) != 1:
        raise SystemExit(f'⚠️ §3.129d 前置守卫：RULE 键「{_k}」命中 {len(_m)} 条（须恰为 1）→ 终止')
for _t in _all_titles:
    _h = [k for k in RULE if _t.startswith(k)]
    if len(_h) != 1:
        raise SystemExit(f'⚠️ §3.129d 前置守卫：标题「{_t[:30]}」命中 {len(_h)} 个键（须恰为 1）→ 终止')
print(f'✅ §3.129d 前置守卫通过：{len(RULE)} 键 ↔ {len(_all_titles)} 条，双向唯一命中')

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
     '**连续第 8 档为规则表降级档（10/6 / 10/7 / 10/8 / 10/9 / 10/11 / 10/12 / 10/13 + 本档）→ 跨档比较时须标注口径差异提示：'
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
      f"均值强度 {sum(x['strength'] for x in add)/len(add):.2f}")
print(f"sentiment 总计 {len(sent['items'])} 条；带 source_url "
      f"{sum(1 for x in sent['items'] if x.get('source_url'))}/{len(sent['items'])}")
for x in add:
    print(f"  {x['track']:8s} {x['direction']:2s} {x['strength']:>3d}/{x['confidence']:<3d} {x['volatility']} | {x['brief']}")

# 名义净分 + 暴露加权（§3.104 强制双表）；EXPO 取 10/13 收盘**修正件**（§3.140a）
_pc = json.load(open(os.path.join(BASE, 'data/processed/history/portfolio_close_20261013_fix.json')))
_tt = _pc['total_mv']
EXPO = {t: round(_pc['tracks'][t]['mv'] / _tt * 100, 2)
        for t in ['大消费', 'A股医药', '美股标普医药', '恒生科技', '其他/宽基']}
net = {t: 0.0 for t in list(EXPO) + ['宏观']}
raw_net = {t: 0.0 for t in list(EXPO) + ['宏观']}
cnt = {t: 0 for t in list(EXPO) + ['宏观']}
for x in add:
    sg = 1 if x['direction'] == '利多' else (-1 if x['direction'] == '利空' else 0)
    net[x['track']] += sg * x['strength'] / 100
    raw_net[x['track']] += sg * x['strength']
    cnt[x['track']] += 1
print('\n名义净分（原始分）/ 暴露加权：')
ew = 0.0
for t in list(EXPO) + ['宏观']:
    print(f'  {t:8s} 条数={cnt[t]} 原始净分={raw_net[t]:+.1f} 归一={net[t]:+.4f} 暴露={EXPO.get(t,0.0):.2f}%')
    ew += net[t] * EXPO.get(t, 0.0) / 100
print(f'  → 暴露加权净情绪分 = {ew:+.4f}')
print(f'  → 赛道原始净分合计（含宏观）= {sum(raw_net.values()):+.1f}')

agg_out = {t: {'n': cnt[t], 'net_nominal': round(raw_net[t], 1),
               'net_weighted_100': round(net[t], 4),
               'expo_pct': EXPO.get(t, 0.0),
               'weighted_contrib': round(net[t] * EXPO.get(t, 0.0) / 100, 4)}
           for t in list(EXPO) + ['宏观']}
agg_out['_total_nominal'] = round(sum(raw_net.values()), 1)
agg_out['_total_weighted'] = round(ew, 4)
agg_out['_expo_source'] = 'portfolio_close_20261013_fix.json（§3.140a 补正后 total_mv）'
json.dump(agg_out, open(os.path.join(BASE, 'data/processed/history/sentiment_agg_20261014_preopen.json'),
                        'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('\nSAVED sentiment_agg_20261014_preopen.json')
