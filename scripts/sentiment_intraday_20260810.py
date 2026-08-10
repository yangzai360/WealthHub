# -*- coding: utf-8 -*-
"""盘中新闻情绪分析 (2026-08-10 13:45 档)
输入: 本窗口(07:30-13:30)抓取的新增新闻列表
输出: 情绪标注 JSON + 追加到 events-2026-08-10.json (从 N20260810-011 开始)
"""
import json, os, urllib.request

BASE = "/Users/jieyang/Documents/WealthHub"
EV_DIR = os.path.join(BASE, "data/processed/events")
TODAY = "2026-08-10"

NEWS = [
    {
        "time": "09:30", "track": "A股医药", "category": "政策类",
        "title": "药明康德1260H禁令获批：美国法院批准初步禁令动议 半年报营收289亿净利110.8亿大幅超预期并上调全年指引",
        "summary": "8/9晚药明康德公告，美国哥伦比亚特区联邦地区法院就1260H认定诉讼批准初步禁令申请，司法挑战期间免受即时不利影响、业务保持正常。半年报营收288.97亿(+38.93%)、净利110.8亿(+29.43%)，经调整利润115.7亿(+83.2%)，Q2收入164.6亿持续业务+55.2%；上调全年营收指引至585-605亿(增速35%-39%)，推出不超10亿元员工持股计划。华西证券全面上调评级维持买入。",
        "source_url": "https://k.sina.com.cn/article_5953190046_162d6789e06703p0ru.html?loc=38",
    },
    {
        "time": "10:00", "track": "A股医药", "category": "行业事件类",
        "title": "创新药持续霸屏：百花医药5连板 百普赛斯/药康生物20cm涨停 创新药ETF包揽涨幅榜",
        "summary": "8/10早盘创新药强势霸屏：百普赛斯开盘20%涨停(第二个20cm)、药康生物20cm涨停、百花医药5连板、哈药股份一字涨停(封单超70万手)2连板、海正药业/海普瑞涨停。涨幅前30的ETF除养殖外几乎全为医药。湘财证券：科技资金流向医药承接+上游CXO半年报向好行业复苏+中国药企全球化初现雏形三利好驱动。",
        "source_url": "https://stcn.com/article/detail/4066508.html",
    },
    {
        "time": "11:00", "track": "A股医药", "category": "行业事件类",
        "title": "医疗服务板块放量飙升逾6%创2年多新高 医药生物获49亿主力净流入居申万之首",
        "summary": "8/10早盘医疗服务方向领涨，板块指数高开高走盘中放量飙升逾6%创2年多新高；免疫治疗/医药商业/民营医院/基因概念涨幅居前。Wind监测：截至午间收盘医药生物行业获逾49亿元主力资金净流入居申万一级行业之首，医疗服务二级行业获逾20亿元净流入居首。催化：国家卫健委印发卒中中心建设指导原则(2026版)；医疗机构医疗服务免征增值税政策延续。",
        "source_url": "https://xxpl@stcn.com/article/detail/4066517.html",
    },
    {
        "time": "11:16", "track": "大消费", "category": "行业事件类",
        "title": "白酒板块全线爆发：茅台+3.76%一月内第三次调价 普五批价突破800元 板块底部信号明确",
        "summary": "8/10早盘白酒板块全线爆发：白酒Ⅱ板块+3.30%、食品饮料+2.78%，迎驾贡酒+6%、古井贡酒+4%、贵州茅台+3.76%(1358.49元)、五粮液+1.74%(76.42元)。消息面：茅台8/8自营店四款产品调价(飞天1753元)为一个月内第三次调价；第八代五粮液批价突破800元大关。华创证券：Q2加速出清、白酒板块持仓仅1%处15H1历史底部，底部信号明确。",
        "source_url": "https://dy.163.com/article/L3VF4GE10519QIKK.html",
    },
    {
        "time": "10:15", "track": "大消费", "category": "宏观类",
        "title": "兴业证券：茅五批价上行行业修复信号渐明 高端白酒价格体系持续修复",
        "summary": "兴业证券食品饮料点评：近期飞天、普五批价均有上涨，高端白酒价格体系持续修复释放行业触底企稳信号。飞天批价年初低点跌破1499元，7月中旬二次提价后稳定1700元以上，8/8自营店提至1753元；普五批价预计回升至760-780元区间。茅台市场化改革显效(年内两次提价+精准调控供需)叠加需求韧性(飞天动销同比双位数增长)。",
        "source_url": "https://stock.hexun.com/2026-08-10/224795690.html",
    },
    {
        "time": "12:00", "track": "恒生科技", "category": "宏观类",
        "title": "港股午评：恒指+0.72% 恒生科技+0.37% 科网股普涨 药明康德涨近3%",
        "summary": "8/10港股午间收盘恒指涨0.72%报25853.69点、恒生科技涨0.37%报4876.20点、国企指数+0.66%。科网股普涨：阿里+2.10%、京东/哔哩哔哩涨逾1%；生物医药活跃药明康德涨近3%(1260H禁令获批)。证券板块国泰君安国际因私有化要约大涨超36%。光通信/PCB/半导体领跌，天数智芯跌超8%。",
        "source_url": "https://new.qq.com/rain/a/20260810A06C5Z00?refer=cp_1009",
    },
    {
        "time": "10:00", "track": "美股标普医药", "category": "业绩类",
        "title": "安进市值破2222亿美元创纪录 上调全年指引 美股医疗保健防御板块获资金流入",
        "summary": "截至8/7纳斯达克收盘，安进市值达2222亿美元(约1.5万亿人民币)创纪录跻身市值前10药企。Q2单季营收100.54亿美元(+10%)首破百亿，上调全年营收指引至382-394亿美元。8/7美股三大指数齐涨(标普+0.62%创历史新高)，板块轮动下医疗保健等防御型股票获资金流入。礼来市值11160亿美元(+49%营收)居首。",
        "source_url": "https://www.zyzhan.com/news/detail/99985.html",
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

content = ""
for attempt in range(3):
    try:
        req = urllib.request.Request(
            "https://api.deepseek.com/chat/completions",
            data=json.dumps(data).encode(),
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            result = json.load(resp)
        content = result["choices"][0]["message"]["content"]
        if content and content.strip():
            break
        print(f"[warn] DeepSeek 第{attempt+1}次返回空 content, 重试...")
    except Exception as e:
        print(f"[warn] DeepSeek 第{attempt+1}次异常: {e}, 重试...")

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

next_id = len(existing) + 1  # 现有 10 条 -> 从 011 开始
for n in NEWS:
    ann = next((a for a in annotations if a.get("title", "").strip() == n["title"].strip()), None)
    if ann is None:
        ann = {"sentiment": "中性", "strength": 50, "impact_direction": "中性", "expected_volatility": "中", "reason": "自动标注缺省"}
    existing.append({
        "id": f"N20260810-{next_id:03d}",
        "date": TODAY,
        "track": n["track"],
        "category": n["category"],
        "title": n["title"],
        "summary": n["summary"],
        "source": "财联社/证券时报/WebSearch",
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
