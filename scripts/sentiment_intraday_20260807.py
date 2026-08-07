# -*- coding: utf-8 -*-
"""盘中新闻情绪分析 (2026-08-07 13:45 档)
输入: 本窗口抓取的新增新闻列表
输出: 情绪标注 JSON (正面/中性/负面 + 0-100 强度 + 方向 + 波动), 追加到 events-2026-08-07.json
"""
import json, os, urllib.request

BASE = "/Users/jieyang/Documents/WealthHub"
NEWS_DIR = os.path.join(BASE, "data/processed/news")
EV_DIR = os.path.join(BASE, "data/processed/events")
TODAY = "2026-08-07"

# 本窗口 (07:30-13:30) 新增新闻
NEWS = [
    {
        "time": "10:30", "track": "A股医药",
        "title": "创新药、CRO概念涨势扩大 十余只成分股涨停",
        "summary": "财联社8月7日电，创新药、CRO概念盘中持续扩大涨幅，毕得医药、药康生物、百普赛斯、凯莱英、百花医药等十余股涨停，CRO概念指数涨8.64%。国金证券：TOP15跨国药企今年外部资本开支已达2003亿美元，接近2025全年总额73.5%，全球医药产业并购高景气格局确立。",
        "source_url": "https://www.cls.cn/detail/2448145",
    },
    {
        "time": "11:30", "track": "A股医药",
        "title": "午评：创业板指半日涨1.75% PCB、创新药概念集体爆发",
        "summary": "财联社午评：市场早盘震荡反弹，创业板指领涨，沪指涨0.49%、深成指涨1.31%、创业板指涨1.75%，两市半日成交1.68万亿。创新药概念快速走强，百花医药4连板，哈三联、凯莱英4天2板，哈药股份、海正药业、药康生物涨停。",
        "source_url": "https://www.cls.cn/detail/2448159",
    },
    {
        "time": "12:53", "track": "A股医药",
        "title": "百花医药开盘两分钟涨停！创新药概念股霸屏 业绩预喜股来了",
        "summary": "证券时报：多重利好共驱创新药持续走强。上半年国家药监局批准38款创新药上市（国产31款）；国产创新药对海外药企授权交易81笔、披露总金额约1100亿美元，全球前十占八席；20余家创新药企上半年业绩绝大多数增长，荣昌生物、美迪西扭亏。多家券商以超预期概括药企业绩。",
        "source_url": "https://www.toutiao.com/article/7671148265118630400",
    },
    {
        "time": "12:00", "track": "恒生科技",
        "title": "港股午评：恒指涨0.15% 恒生科技涨0.34% PCB与大模型股领涨",
        "summary": "港股午间收盘，恒生指数涨0.15%报25567.85点，恒生科技涨0.34%报4837.08点。PCB概念走强，鼎泰高科、胜宏科技涨超11%；大模型股大涨，MINIMAX-W、智谱涨超17%；CXO强势，药明生物+6.81%、康龙化成+8.08%、凯莱英+8.07%。",
        "source_url": "https://www.stcn.com/article/detail/4063318.html",
    },
    {
        "time": "11:34", "track": "大消费",
        "title": "五粮液批价回升 白酒已经筑底？多地批价上涨约30元",
        "summary": "云酒头条：8月6日多地市场传出五粮液涨价消息，第八代五粮液批发价集体走高，单瓶涨幅约30元、箱酒涨超100元，主因市场政策收紧（取消部分补贴）。2026年飞天茅台i茅台零售价累计上调至1639元/瓶；高盛研报称白酒最困难阶段已经过去。回暖信号由点及面传导。",
        "source_url": "https://www.163.com/dy/article/L3NOVO3D05199FKS.html",
    },
    {
        "time": "10:49", "track": "大消费",
        "title": "茅台i茅台投放常态化 抢购时代悄然退场",
        "summary": "中国基金报/九派财经：i茅台加大自营投放，生肖酒、精品酒、100ml装均可从容下单；2026Q1 i茅台新增用户近1400万，销售收入215.53亿元同比+267.16%。官方零售价升至1639元后与市场批价利差收窄至百余元，套利空间收窄、投机者离场，真实消费回归。",
        "source_url": "https://www.toutiao.com/article/7671116263980139034/",
    },
    {
        "time": "07:30", "track": "美股标普医药",
        "title": "礼来8/6收涨1.89% 美银上调目标价至1400美元",
        "summary": "礼来8月6日收1191.94美元+1.89%，盘中高至1230.88；Q2收入229.7亿美元+48%、GLP-1产品Mounjaro/Zepbound驱动，净利+25.34%至70.95亿美元；美银上调目标价至1400美元，Cantor维持增持目标价1410美元。XLV 8/6 +0.18%连续走强。",
        "source_url": "https://news.10jqka.com.cn/field/20260807/678737785.shtml",
    },
]

# ---------- DeepSeek 情绪标注 ----------
PROMPT = f"""你是资深医药/消费/科技行业投研分析师。对以下 {len(NEWS)} 条财经新闻逐条做情绪标注，输出 JSON 数组。

每条新闻输出:
- title: 原标题
- sentiment: 正面/中性/负面
- strength: 0-100 整数(情绪强度)
- impact_direction: 利多/利空/中性
- expected_volatility: 低/中/高(对所属赛道的预期波动幅度)
- reason: 一句话理由(30字内)

规则: 只输出 JSON 数组，不要输出任何其他文字。"""

for n in NEWS:
    PROMPT += f"\n- {n['time']} [{n['track']}] {n['title']} | {n['summary']}"

data = {
    "model": "deepseek-v4-flash",
    "messages": [{"role": "user", "content": PROMPT}],
    "max_tokens": 8000,
    "temperature": 0.3,
}
with open("/Users/jieyang/.pi/agent/auth.json") as f:
    key = json.load(f)["deepseek"]["key"]
req = urllib.request.Request(
    "https://api.deepseek.com/chat/completions",
    data=json.dumps(data).encode(),
    headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
)
with urllib.request.urlopen(req, timeout=120) as resp:
    result = json.load(resp)
content = result["choices"][0]["message"]["content"]

# 解析 JSON (可能带 ```json 围栏)
content = content.strip()
if content.startswith("```"):
    content = content.split("```")[1]
    if content.startswith("json"):
        content = content[4:]
content = content.strip()
annotations = json.loads(content)
print(f"DeepSeek 返回 {len(annotations)} 条标注")

# ---------- 生成事件记录 ----------
existing = []
ev_path = os.path.join(EV_DIR, f"events-{TODAY}.json")
if os.path.exists(ev_path):
    with open(ev_path, encoding="utf-8") as f:
        existing = json.load(f)

next_id = 18  # 盘前已生成 N20260807-001..017
for n in NEWS:
    ann = next((a for a in annotations if a.get("title", "").strip() == n["title"].strip()), None)
    if ann is None:
        ann = {"sentiment": "中性", "strength": 50, "impact_direction": "中性", "expected_volatility": "中", "reason": "自动标注缺省"}
    existing.append({
        "id": f"N20260807-{next_id:03d}",
        "date": TODAY,
        "track": n["track"],
        "category": "行业事件类",
        "title": n["title"],
        "summary": n["summary"],
        "source": "财联社/WebSearch",
        "source_url": n["source_url"],
        "sentiment": ann["sentiment"],
        "strength": int(ann["strength"]),
        "impact_direction": ann["impact_direction"],
        "expected_volatility": ann["expected_volatility"],
        "reason": ann.get("reason", ""),
        "reference": {"ret_3d": None, "ret_5d": None, "ret_10d": None, "max_vol": None, "confidence": None,
                      "actual_ret_1d": None, "actual_date": None},
    })
    next_id += 1

with open(ev_path, "w", encoding="utf-8") as f:
    json.dump(existing, f, ensure_ascii=False, indent=1)
print(f"事件库已追加 {len(NEWS)} 条, 累计 {len(existing)} 条 -> {ev_path}")

# ---------- 打印标注结果 ----------
for a in annotations:
    print(f"  [{a.get('strength')}] {a.get('sentiment')} {a.get('impact_direction')} 波动{a.get('expected_volatility')} | {a.get('title', '')[:40]}")
