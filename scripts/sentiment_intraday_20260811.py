# -*- coding: utf-8 -*-
"""盘中新闻情绪分析 (2026-08-11 13:45 档)
输入: 本窗口(07:30-13:30)抓取的新增新闻列表 (与盘前14条去重后 10 条)
输出: 情绪标注 JSON + 追加到 events-2026-08-11.json (从 N20260811-015 开始)
"""
import json, os, urllib.request

BASE = "/Users/jieyang/Documents/WealthHub"
EV_DIR = os.path.join(BASE, "data/processed/events")
TODAY = "2026-08-11"

NEWS = [
    {
        "time": "09:35", "track": "A股医药", "category": "行业事件类",
        "title": "创新药概念盘中持续走强：百花医药6连板 万邦医药20cm涨停 甘李药业/哈药股份涨停 上海七部门支持创新药全球注册",
        "summary": "8/11早盘创新药概念持续走强：百花医药6连板、万邦医药20cm涨停、甘李药业/哈药股份涨停、振东制药/博瑞医药等跟涨。消息面：上海七部门印发国家服务贸易创新示范区建设方案，支持创新药/现代中药/高端医疗器械全球注册认证；今年上半年国家药监局批准38款创新药(国产31款占比超80%)，国产创新药海外授权81笔披露金额约1100亿美元已达2025全年80%；百济神州上调全年营收指引至449-462亿元。湘财证券：医药可承接科技流出资金，CXO半年报改善行业复苏确定，本轮行情大概率不会短期终止。",
        "source_url": "https://finance.eastmoney.com/a/202608113837728052.html",
    },
    {
        "time": "10:00", "track": "A股医药", "category": "行业事件类",
        "title": "百济神州与Revolution Medicines达成合作：获daraxonrasib等四款RAS(ON)抑制剂部分亚洲市场独家权益 市值破4820亿",
        "summary": "8/10晚百济神州与Revolution Medicines宣布临床开发及区域商业化合作：探索百济肿瘤候选药与四款RAS(ON)抑制剂联合方案；百济获得四款临床阶段候选药物在中国/印尼/菲律宾/马来西亚/新西兰/泰国/越南等亚洲市场独家开发及商业化权益，覆盖人口约20亿。其中daraxonrasib在ASCO年会上胰腺癌三期将中位生存期从6.7个月延长至13.2个月(近翻倍)，被称为胰腺癌领域数十年来最重大进展，FDA已受理NDA。8/11百济A股/港股涨超4%，A股市值达4820亿元。",
        "source_url": "https://www.163.com/dy/article/L426T52R0519DDQ2.html",
    },
    {
        "time": "11:00", "track": "A股医药", "category": "行业事件类",
        "title": "港股生物医药逆势拉升：药明康德创历史新高 翰森制药+4.75% 百济神州+4.5% 石药+3.19%",
        "summary": "8/11港股生物医药逆势活跃：药明康德创历史新高(+2.12%)，翰森制药+4.75%为半日最佳蓝筹、百济神州+4.5%、石药集团+3.19%、药明生物+1.78%、药明合联+4.32%。港股通医疗ETF华夏盘中涨超2%冲击3连涨，恒生生物科技ETF富国盘中+2.49%。机构：创新药正从估值驱动转向业绩与全球化兑现共同驱动，8-9月将迎来业绩兑现/临床数据发布/海外授权三重催化。",
        "source_url": "https://www.163.com/dy/article/L41VLE450512B07B.html",
    },
    {
        "time": "09:30", "track": "大消费", "category": "行业事件类",
        "title": "8/11酒价内参：11大单品七涨五跌 精品茅台+10元至2432元再创近月新高 普五808元连续两日挺立800大关",
        "summary": "新浪财经酒价内参8/11数据：11大单品七涨五跌赢家占优。精品茅台+10元至2432元再度刷新近一月新高；飞天+4元至1781元逼近7/18提价后高位；普五八代+5元至808元连续两天挺立800元大关上方；国窖1573+7元至890元紧跟头部；古井贡古20+6元至527元。输家：青花汾20-3元至390元(四连涨结束)、习酒君品-5元至631元跌破趋势线。11大单品总价9986元较昨日+21元创5/19以来新高逼近1万元。茅台自营店调价后首个工作日，京沪穗深多地无需预约可直接到店购买飞天。",
        "source_url": "https://finance.sina.com.cn/chanjing/jync/2026-08-11/doc-inimwyqt7678443.shtml",
    },
    {
        "time": "09:41", "track": "大消费", "category": "行业事件类",
        "title": "国泰海通：白酒基金持仓降至0.97%历史低位 申万食饮估值11%分位 行业筑底把握结构性机遇",
        "summary": "国泰海通证券8/11研报：白酒行业处在本轮周期底部，Q2报表延续出清状态；2026Q2主动偏股基金食饮重仓比例降至1.49%(环比-2.41%)，白酒重仓比例降至仅0.97%(环比-1.93%)，接近2013-2015深度调整期仓位。估值：申万食饮位于2000年以来11%分位(仅高于非银金融)，白酒约21%分位。短期高端白酒涨价已传导至股价，茅台放开直营店散客购买、五粮液收紧渠道费用管控批价积极。调整较早、出清彻底的酒企有望率先估值修复。",
        "source_url": "https://dy.163.com/article/L41S2JRG05568V7Z.html",
    },
    {
        "time": "12:10", "track": "恒生科技", "category": "行业事件类",
        "title": "港股午评：恒指-0.63% 恒生科技-1.27% 科网股集体转弱 腾讯/京东/小米/百度跌超2% 药明康德逆势创新高",
        "summary": "8/11港股三大指数早盘冲高后持续走弱，半日恒指-0.63%报25773点、国企指数-0.61%、恒生科技-1.27%报4857点，大市成交1158亿港元。大型科网股普遍转跌：京东-2.76%、小米-2.46%、腾讯-2.20%、百度-2.33%、快手跌逾2%，阿里巴巴+0.32%勉强飘红。黄金股高开低走(紫金-3.51%)，三大航空股齐跌；医药股逆势走强(翰森+4.75%、药明康德创历史新高)，三桶油走高(中海油+3.76%)。大行料小米季绩无惊喜。",
        "source_url": "https://www.tmtpost.com/nictation/8098820.html",
    },
    {
        "time": "10:30", "track": "恒生科技", "category": "政策类",
        "title": "恒生指数公司就恒生科技指数修订征求意见：成份股拟由30只增至50只 扩大科技主题覆盖范围",
        "summary": "8/10晚间恒生指数公司公告，就恒生科技指数修订方案征求市场意见：拟将成份股数量由目前30只增加至50只，同时进一步扩大科技主题覆盖范围。修订方案预计9月底公布，相关成份股变动将于12月指数调整日生效。若落地，恒生科技指数覆盖更广、更均衡，可能吸引更多被动资金跟踪，长期利好指数流动性。",
        "source_url": "https://finance.sina.cn/hkstock/gggd/2026-08-11/detail-inimxewt4394135.d.html",
    },
    {
        "time": "11:30", "track": "美股标普医药", "category": "行业事件类",
        "title": "百济神州合作daraxonrasib将成胰腺癌首个RAS靶向药 中位生存期6.7月→13.2月 FDA已受理NDA 美股映射温和利好",
        "summary": "Revolution Medicines的daraxonrasib(RAS(ON)抑制剂)在晚期胰腺癌三期将中位生存期从6.7个月延长至13.2个月(近翻倍)，获ASCO年会42秒掌声，被称为胰腺癌领域数十年来最重大进展；FDA已受理其NDA(7/22)，若获批将成为胰腺癌首个真正的RAS靶向治疗药物。8/10晚百济神州与Revolution达成合作获部分亚洲市场独家权益。美股Revolution Medicines/RAS赛道映射温和正面。",
        "source_url": "https://www.163.com/dy/article/L426T52R0519DDQ2.html",
    },
    {
        "time": "12:00", "track": "宏观", "category": "宏观类",
        "title": "油价续涨Brent破88美元：美伊谈判僵局 美国SPR降至1980年代以来最低 美债10年期收益率上行至4.70%",
        "summary": "8/11亚洲时段油价续涨：Brent一度触及88美元/桶、WTI 82.45美元，均为7/31以来最高。美伊就霍尔木兹海峡重开谈判陷入僵局(特朗普要求伊朗赔偿，伊朗要求美方满足条件)，分析师形容为'墨西哥对峙'式拉锯；叠加美国战略石油储备降至3亿桶以下(1980年代以来最低)放大供应担忧。10年期美债收益率上行至4.70%附近，美元指数99.81。油价上行抬升8/12美国7月CPI通胀上行风险，若CPI超预期(≥3.6%)将重燃加息预期、压制成长估值。",
        "source_url": "https://live.euronext.com/en/financial-news/oil-prices-rise-asia-stocks-drift-amid-us-iran-stalemate",
    },
    {
        "time": "11:30", "track": "宏观", "category": "宏观类",
        "title": "A股午评：沪指-0.05% 创业板+1.41% MLCC/创新药领涨 半日成交1.52万亿缩量2153亿 超3100股下跌 结构分化",
        "summary": "8/11早盘A股三大指数低开高走：沪指-0.05%报3964.79点、深成指+0.65%、创业板指+1.41%报3587点、科创50+0.16%。MLCC概念领涨(达利凯普/双星新材等涨停)，影视院线反复活跃(北京文化两连板)，石油/减肥药/创新药涨幅居前；航天军工回调(中国卫星/航天环宇跌超6%)，贵金属/稀土/有色领跌。沪深两市半日成交1.52万亿较上日缩量2153亿，全市场超3100股下跌——指数权重与题材分化明显，缩量+普跌结构需警惕。",
        "source_url": "https://www.stcn.com/article/detail/4068754.html",
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
        with urllib.request.urlopen(req, timeout=180) as resp:
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

next_id = len(existing) + 1  # 现有 14 条 -> 从 015 开始
for n in NEWS:
    ann = next((a for a in annotations if a.get("title", "").strip() == n["title"].strip()), None)
    if ann is None:
        ann = {"sentiment": "中性", "strength": 50, "impact_direction": "中性", "expected_volatility": "中", "reason": "自动标注缺省"}
    existing.append({
        "id": f"N20260811-{next_id:03d}",
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

# 同时保存到 news 文件 (增量)
news_path = os.path.join(BASE, "data/processed/news", f"news-{TODAY}.json")
news_existing = []
if os.path.exists(news_path):
    with open(news_path, encoding="utf-8") as f:
        news_existing = json.load(f)
news_ids = {n["id"] for n in news_existing}
added = 0
for n in existing:
    if n["id"] not in news_ids:
        news_existing.append(n)
        news_ids.add(n["id"])
        added += 1
with open(news_path, "w", encoding="utf-8") as f:
    json.dump(news_existing, f, ensure_ascii=False, indent=1)
print(f"news 文件新增 {added} 条, 累计 {len(news_existing)} 条")

# ---------- 打印标注结果 ----------
for a in annotations:
    print(f"  [{a.get('strength')}] {a.get('sentiment')} {a.get('impact_direction')} 波动{a.get('expected_volatility')} | {a.get('title', '')[:44]}")
