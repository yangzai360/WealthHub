# -*- coding: utf-8 -*-
"""盘后新闻情绪分析 + 事件库回填 (2026-08-07 20:00 档)
1. 盘后窗口(14:00-20:00)新增新闻 -> DeepSeek 情绪标注 -> 追加 events-2026-08-07.json (编号从 025)
2. 把当日全部事件的 actual_ret_1d 回填(按赛道当日实际收盘涨跌), 逐步积累「事件→赛道后续走势」样本
"""
import json, os, urllib.request

BASE = "/Users/jieyang/Documents/WealthHub"
EV_DIR = os.path.join(BASE, "data/processed/events")
NEWS_DIR = os.path.join(BASE, "data/processed/news")
TODAY = "2026-08-07"

# ---------- 盘后新增新闻 (14:00-20:00 窗口, WebSearch 抓取, 已去重) ----------
NEWS = [
    {
        "time": "15:00", "track": "A股医药",
        "title": "A股收评：指数全线飘红超2800股上涨 创新药PCB掀起涨停潮",
        "summary": "8月7日A股三大指数集体收红，沪指+1.02%、深成指+1.42%、创业板指+1.35%，两市成交2.66万亿元放量1356亿，超2800只个股上涨。创新药、CRO概念全线爆发，生物医药ETF上涨6.4%，百花医药4连板，昭衍新药、药康生物涨停；PCB概念十余股涨停。",
        "source_url": "https://new.qq.com/rain/a/20260807A0AUHE00?refer=cp_1009",
    },
    {
        "time": "15:10", "track": "A股医药",
        "title": "CRO概念收盘掀涨停潮 药明康德涨8.49% 康龙化成涨14.34%",
        "summary": "8月7日收盘CRO概念全线爆发：药明康德+8.49%成交139.6亿、康龙化成+14.34%、昭衍新药+10.01%、凯莱英+10.00%涨停，药石科技+18.39%、博腾股份+20.02%。中邮证券：海外研发外包需求回暖，国内BigPharma研发支出提升、BD持续高涨，研发外包需求提振有望2026年兑现。",
        "source_url": "https://www.toutiao.com/article/7671203665952260623/",
    },
    {
        "time": "16:30", "track": "恒生科技",
        "title": "港股收评：恒指+0.54% 恒生科技+0.78% 药明康德创历史新高",
        "summary": "8月7日港股收盘：恒指+0.54%报25668.03、恒生科技+0.78%报4858.29。药明康德+7%盘中193港元创历史新高，市值约5700亿港元；金斯瑞+16.18%、再鼎医药+18.38%；大模型双雄爆发，智谱+14%、MINIMAX-W+9%(入通两日累涨近三成)。",
        "source_url": "https://www.stcn.com/article/detail/4063741.html",
    },
    {
        "time": "17:00", "track": "恒生科技",
        "title": "南向资金连续三日净卖出 8/7净卖出超7亿港元",
        "summary": "8月7日南向资金净卖出港股超7亿港元，近期连续三个交易日净卖出。本周港股三大指数分化：恒指周跌0.84%、恒生科技周涨0.60%、国企指数周跌0.94%；MINIMAX-W周涨超40%、胜宏科技周涨38.94%。",
        "source_url": "https://www.nbd.com.cn/articles/2026-08-07/4535346.html",
    },
    {
        "time": "17:30", "track": "恒生科技",
        "title": "2026上半年中国医药出海交易总金额达997亿美元 为2024全年1.9倍",
        "summary": "浙商证券统计：2026上半年中国医药出海交易总金额达997亿美元，为2024年全年522亿美元的1.9倍，已接近2025年全年1357亿美元的73%。BD交易高景气为医药板块本轮订单爆发驱动主力，港股医药出海景气持续验证(金斯瑞+16.18%、药明生物+10.83%)。",
        "source_url": "https://www.163.com/dy/article/L3OE45O405198CJN.html",
    },
    {
        "time": "17:50", "track": "大消费",
        "title": "第八代五粮液批价8/7报755元/瓶 单日再涨22元 多地突破760元",
        "summary": "今日酒价显示8月7日第八代五粮液市场批发价755元/瓶，较前日+22元；河南、河北、上海、四川、山东等市场批价已集体突破760元/瓶，单周最高涨幅超30元/瓶。上海零售价站上800-840元/瓶。主因渠道政策调整：酒厂取消年度奖励与模糊奖励，控货挺价，中秋国庆旺季临近。五粮液已累计回购10.02亿元1331.66万股、集团增持1.99亿元。",
        "source_url": "https://so.html5.qq.com/page/real/search_news?docid=70000021_9996a758b8006152",
    },
    {
        "time": "18:10", "track": "美股标普医药",
        "title": "美股医疗保健板块三个月涨11.2%创历史新高 7月资金净流入24.4亿美元",
        "summary": "标普500医疗保健指数过去三个月累计上涨11.2%创历史新高，同期标普500仅+6%；约50只美国医疗基金7月吸引24.4亿美元净流入。美银调查：全球基金经理对医疗保健股净超配比例32%(6月仅14%)。LSEG预计标普医疗公司盈利2026Q4-2027年底实现两位数增长。",
        "source_url": "https://www.163.com/dy/article/L3MSGBH305561FZW.html",
    },
    {
        "time": "18:30", "track": "美股标普医药",
        "title": "美股8/6三大指数收跌但医疗逆势走强 礼来+1.89%辉瑞+1.51%",
        "summary": "当地时间8月6日美股三大指数收跌：道指-0.85%、纳指-0.06%、标普500-0.18%，10年美债收益率升至4.67%。但医疗板块逆势：礼来+1.89%、辉瑞+1.51%、雅培+2.13%、赛默飞+0.38%；医疗保健是当日唯一收涨板块(XLV +0.18%)，防御属性凸显。美联储主席沃什考虑9月加息。",
        "source_url": "https://www.163.com/dy/article/L3NH9VLL0519QIKK.html",
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

content = content.strip()
if content.startswith("```"):
    content = content.split("```")[1]
    if content.startswith("json"):
        content = content[4:]
content = content.strip()
annotations = json.loads(content)
print(f"DeepSeek 返回 {len(annotations)} 条标注")

# ---------- 追加事件 (编号 025 起) ----------
ev_path = os.path.join(EV_DIR, f"events-{TODAY}.json")
with open(ev_path, encoding="utf-8") as f:
    existing = json.load(f)

next_id = len(existing) + 1  # 现有 24 条 -> 025
for n in NEWS:
    ann = next((a for a in annotations if a.get("title", "").strip() == n["title"].strip()), None)
    if ann is None:
        ann = {"sentiment": "中性", "strength": 50, "impact_direction": "中性", "expected_volatility": "中", "reason": "自动标注缺省"}
    existing.append({
        "id": f"N{TODAY.replace('-', '')}-{next_id:03d}",
        "date": TODAY,
        "track": n["track"],
        "category": "行业事件类",
        "title": n["title"],
        "summary": n["summary"],
        "source": "WebSearch(盘后)",
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

# ---------- 回填当日全部事件 actual_ret_1d (赛道当日实际收盘涨跌, 8/7) ----------
ACTUAL = {
    "A股医药": 4.50,        # 医药ETF +4.50 / 医疗ETF +4.53 均值
    "大消费": 0.27,          # 中证消费 +0.27 (消费ETF +0.45)
    "美股标普医药": 0.18,    # XLV 8/6 +0.18 (QDII T+1, 8/7 美股未开盘)
    "恒生科技": 0.78,        # 恒生科技指数 +0.78
    "其他/宽基": 1.02,       # 上证指数 +1.02
}
for ev in existing:
    if ev.get("date") == TODAY:
        tr = ev.get("track", "")
        ev["reference"]["actual_ret_1d"] = ACTUAL.get(tr)
        ev["reference"]["actual_date"] = TODAY

with open(ev_path, "w", encoding="utf-8") as f:
    json.dump(existing, f, ensure_ascii=False, indent=1)
print(f"事件库已追加 {len(NEWS)} 条, 累计 {len(existing)} 条 -> {ev_path}")

# ---------- 打印 ----------
for a in annotations:
    print(f"  [{a.get('strength')}] {a.get('sentiment')} {a.get('impact_direction')} 波动{a.get('expected_volatility')} | {a.get('title', '')[:42]}")
