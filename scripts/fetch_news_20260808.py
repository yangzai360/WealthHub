# -*- coding: utf-8 -*-
"""2026-08-08 周六(非交易日)盘前档: 归档隔夜美股收盘 + 周末新闻窗口(8/7 18:00 - 8/8 07:30)
产物:
  1) indices.csv 追加美股 8/7 收盘行 (type=us_index, 增量)
  2) news-2026-08-08.json 归档周末新闻 (含 source_url)
  3) 调 DeepSeek 情绪标注 -> events-2026-08-08.json
"""
import json, os, urllib.request

BASE = "/Users/jieyang/Documents/WealthHub"
HIST = os.path.join(BASE, "data/processed/history")
NEWS_DIR = os.path.join(BASE, "data/processed/news")
EV_DIR = os.path.join(BASE, "data/processed/events")
TODAY = "2026-08-08"

# ---------- 1. indices.csv 增量: 美股 8/7 收盘 (非交易日仅补隔夜美股, A股/港股无新行情) ----------
us_rows = [
    ("us_index", "2026-08-07", "美股医疗保健XLV", "XLV", "165.68", "+0.75", "美股收盘(非交易日参考)"),
    ("us_index", "2026-08-07", "美股纳指100QQQ", "QQQ", "723.03", "+1.17", "美股收盘(非交易日参考)"),
    ("us_index", "2026-08-07", "美股道指DIA", "DIA", "539.62", "+0.27", "美股收盘(非交易日参考)"),
]
csv_path = os.path.join(HIST, "indices.csv")
with open(csv_path, encoding="utf-8-sig") as f:
    lines = f.read().splitlines()
header = lines[0]
existing = set(tuple(l.split(",")) for l in lines[1:] if l.strip())
added = 0
new_lines = list(lines)
for row in us_rows:
    key = tuple(row)
    if key not in existing:
        new_lines.append(",".join(row))
        existing.add(key)
        added += 1
with open(csv_path, "w", encoding="utf-8-sig") as f:
    f.write("\n".join(new_lines) + "\n")
print(f"indices.csv 新增 {added} 行(美股收盘), 累计 {len(new_lines)-1} 行")

# ---------- 2. 周末新闻窗口归档 ----------
NEWS = [
    {
        "time": "06:50", "track": ["恒生科技"],
        "title": "7月非农爆冷-2.3万 美联储9月加息概率降至约40% 美股三大指数收涨标普创新高",
        "summary": "美国7月非农就业环比减少2.3万(预期+8万)，5-6月合计下修10.3万，失业率降至4.1%；CME利率期货9月加息概率由超50%降至约40%。美股三大指数集体收涨(道指+0.28%/纳指+1.3%/标普+0.62%创新高)，10年期美债收益率走低，COMEX黄金+2.37%报4401美元。美联储内部加息阵营扩大(卡什卡利/洛根/哈马克/施密德)，沃什保持沉默，8/12公布的7月CPI为9月会议前关键验证点。",
        "source_url": "https://news.10jqka.com.cn/20260808/c678775253.shtml",
    },
    {
        "time": "07:30", "track": ["美股标普医药"],
        "title": "美股8/7收盘：XLV +0.75%续涨 医疗ETF连续走强",
        "summary": "新浪源ETF日线：XLV 8/7收165.68美元+0.75%（连续多日走强），QQQ +1.17%、DIA +0.27%，三大指数收涨标普创新高；非农降温缓解加息压力，医疗防御属性（beta 0.26）凸显，全球医疗主线延续。",
        "source_url": "https://cj.sina.com.cn/articles/view/1651428902/626ece2601901ioia",
    },
    {
        "time": "07:10", "track": ["美股标普医药"],
        "title": "ANI Pharmaceuticals Q2净收入2.66亿美元+25.9% 重申全年指引",
        "summary": "ANI(ANIP)8/7盘前发布Q2：净收入2.66亿美元同比+25.9%，核心Cortrophin Gel收入1.17亿美元+43.5%，调整后EPS 2.21美元；重申全年收入10.8-11.4亿美元指引，痛风适应症扩面放量。美股罕见病/专科药中盘业绩延续景气。",
        "source_url": "https://www.taiwannews.com.tw/en/news/6417385",
    },
    {
        "time": "07:00", "track": ["A股医药"],
        "title": "北京普惠健康保特药清单升级至176种 新增22种创新药 首次纳入CAR-T",
        "summary": "8/7起北京普惠健康保2026年度特药清单中期调整执行：新增22种创新药，清单扩至176种（国内特药71/海外65/特药2共40），首次将CAR-T创新疗法、罕见病用药、高值慢病用药纳入特药2保障；报销比例提高5个百分点。创新药支付端政策利好延续。",
        "source_url": "https://so.html5.qq.com/page/real/search_news?docid=70000021_6556a760e4347852",
    },
    {
        "time": "07:00", "track": ["A股医药"],
        "title": "上半年医药License Out总金额1090亿美元 行情从超跌反弹切向确定性兑现",
        "summary": "截至7月底本年医药License Out总金额达1090亿美元(2025全年79%)，石药×AZ/恒瑞×BMS/信达×辉瑞等平台型大单落地；NMPA临床试验审评缩短至30个工作日，2026基药目录首次纳入16种创新药(4种国产I类)。东财证券周报：医药行情从超跌反弹切换到确定性+兑现力驱动。",
        "source_url": "https://www.163.com/dy/article/L3NKSB330534A4SC.html",
    },
    {
        "time": "18:32", "track": ["恒生科技", "A股医药"],
        "title": "港股8/7：生物科技指数+5.73% 药明生物+10.83% 第十二批国家集采开标",
        "summary": "8/7港股恒指+0.54%报25668、恒生科技+0.78%报4858；恒生生物科技指数+5.73%，再鼎医药+18.38%、金斯瑞+16.18%、药明合联+11.82%、百济神州+5.26%上调全年指引；药明生物+10.83%拟收购创胜医药杭州基地。第十二批国家集采65种药品采购成功。但南向资金净卖出7.78亿港元(连续3日)。",
        "source_url": "http://gu.qq.com/resources/shy/news/detail-v2/index.html#/?id=nesSN20260807183255973210c0&s=b",
    },
    {
        "time": "07:20", "track": ["大消费"],
        "title": "第八代五粮液批价续涨：整箱两天涨近百元 多地突破760元/瓶 挺价目标800元",
        "summary": "8/6-8/7第八代五粮液批价加速上行：郑州百荣整箱调货价单日+90元(两天涨幅近150元)，河南/河北/上海/四川/山东多地批价突破760元/瓶，上海授权专卖店零售价站上800元；厂家取消渠道奖励、控货挺价(目标800元/瓶)，新任董事长邓敏渠道改革为中秋旺季备货；集团累计增持241.13万股约1.99亿元(计划30-50亿)，累计回购10.02亿元。",
        "source_url": "https://so.html5.qq.com/page/real/search_news?docid=70000021_7976a752ef670052",
    },
    {
        "time": "07:10", "track": ["大消费"],
        "title": "华创证券：下半年白酒行业有望边际企稳 二阶导转正",
        "summary": "华创证券研报：下半年白酒行业有望边际企稳、二阶导转正，迎来小幅催化。依据：6月烟酒类社零数据表现较好、零售口径向规模以上集中、白酒前端基数效应显现、端午局部区域渠道出货转正。五粮液批价上行配合增持回购形成组合拳。",
        "source_url": "https://www.163.com/dy/article/L3NJES0N0519D45U.html",
    },
    {
        "time": "06:30", "track": ["恒生科技"],
        "title": "彭博经济学家：7月CPI预计同比+2.4% 核心CPI或创五年新低",
        "summary": "彭博经济学家预计下周(8/12)公布的美国7月CPI同比+2.4%，之后两个月放缓至2.2%-2.3%，对应核心CPI同比放缓至约2%创五年新低；但核心PCE仍高于3%，两者分化促使美联储保持谨慎。若CPI兑现降温，9月加息概率将进一步下降，利好港股/成长股估值修复。",
        "source_url": "https://m.weibo.cn/status/5329542827738757",
    },
]

news_path = os.path.join(NEWS_DIR, f"news-{TODAY}.json")
if os.path.exists(news_path):
    with open(news_path, encoding="utf-8") as f:
        news = json.load(f)
else:
    news = []
existing_titles = {n["title"] for n in news}
added_n = 0
for n in NEWS:
    if n["title"] not in existing_titles:
        news.append(n)
        existing_titles.add(n["title"])
        added_n += 1
with open(news_path, "w", encoding="utf-8") as f:
    json.dump(news, f, ensure_ascii=False, indent=1)
print(f"news-{TODAY}.json 新增 {added_n} 条, 累计 {len(news)} 条")

# ---------- 3. DeepSeek 情绪标注 ----------
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
    PROMPT += f"\n- {n['time']} [{'/'.join(n['track'])}] {n['title']} | {n['summary']}"

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

# ---------- 4. 事件库追加 ----------
ev_path = os.path.join(EV_DIR, f"events-{TODAY}.json")
existing_ev = []
if os.path.exists(ev_path):
    with open(ev_path, encoding="utf-8") as f:
        existing_ev = json.load(f)

next_id = len(existing_ev) + 1
for n in NEWS:
    ann = next((a for a in annotations if a.get("title", "").strip() == n["title"].strip()), None)
    if ann is None:
        ann = {"sentiment": "中性", "strength": 50, "impact_direction": "中性", "expected_volatility": "中", "reason": "自动标注缺省"}
    existing_ev.append({
        "id": f"N{TODAY.replace('-', '')}-{next_id:03d}",
        "date": TODAY,
        "track": n["track"][0],
        "category": "行业事件类",
        "title": n["title"],
        "summary": n["summary"],
        "source": "WebSearch/财经媒体",
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
    json.dump(existing_ev, f, ensure_ascii=False, indent=1)
print(f"事件库 events-{TODAY}.json 累计 {len(existing_ev)} 条")

for a in annotations:
    print(f"  [{a.get('strength')}] {a.get('sentiment')} {a.get('impact_direction')} 波动{a.get('expected_volatility')} | {a.get('title', '')[:42]}")
