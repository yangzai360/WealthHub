# -*- coding: utf-8 -*-
"""将盘中窗口新闻追加到 news-2026-08-07.json (去重)"""
import json, os

BASE = "/Users/jieyang/Documents/WealthHub"
path = os.path.join(BASE, "data/processed/news/news-2026-08-07.json")

with open(path, encoding="utf-8") as f:
    news = json.load(f)

existing_titles = {n["title"] for n in news}
add = [
    {"time": "10:30", "track": ["A股医药"], "title": "创新药、CRO概念涨势扩大 十余只成分股涨停",
     "summary": "财联社：创新药、CRO概念盘中持续扩大涨幅，毕得医药、药康生物、百普赛斯、凯莱英、百花医药等十余股涨停，CRO概念指数涨8.64%。国金证券：TOP15跨国药企今年外部资本开支已达2003亿美元，接近2025全年总额73.5%。",
     "source_url": "https://www.cls.cn/detail/2448145"},
    {"time": "11:30", "track": ["A股医药"], "title": "午评：创业板指半日涨1.75% PCB、创新药概念集体爆发",
     "summary": "财联社午评：沪指涨0.49%、深成指涨1.31%、创业板指涨1.75%，两市半日成交1.68万亿。创新药概念快速走强，百花医药4连板，哈三联、凯莱英4天2板，哈药股份、海正药业、药康生物涨停。",
     "source_url": "https://www.cls.cn/detail/2448159"},
    {"time": "12:53", "track": ["A股医药"], "title": "百花医药开盘两分钟涨停！创新药概念股霸屏 业绩预喜股来了",
     "summary": "证券时报：上半年国家药监局批准38款创新药上市（国产31款）；国产创新药对海外授权81笔约1100亿美元，全球前十占八席；20余家创新药企上半年业绩绝大多数增长，荣昌生物、美迪西扭亏。多家券商以超预期概括药企业绩。",
     "source_url": "https://www.toutiao.com/article/7671148265118630400"},
    {"time": "12:00", "track": ["恒生科技"], "title": "港股午评：恒指涨0.15% 恒生科技涨0.34% PCB与大模型股领涨",
     "summary": "港股午间收盘，恒指涨0.15%报25567.85，恒生科技涨0.34%报4837.08。PCB概念走强，鼎泰高科、胜宏科技涨超11%；大模型股大涨，MINIMAX-W、智谱涨超17%；CXO强势，药明生物+6.81%、康龙化成+8.08%。",
     "source_url": "https://www.stcn.com/article/detail/4063318.html"},
    {"time": "11:34", "track": ["大消费"], "title": "五粮液批价回升 白酒已经筑底？多地批价上涨约30元",
     "summary": "云酒头条：8月6日多地第八代五粮液批发价集体走高，单瓶涨幅约30元、箱酒涨超100元，主因市场政策收紧（取消部分补贴）。飞天茅台i茅台零售价累计上调至1639元/瓶；高盛称白酒最困难阶段已经过去。",
     "source_url": "https://www.163.com/dy/article/L3NOVO3D05199FKS.html"},
    {"time": "10:49", "track": ["大消费"], "title": "茅台i茅台投放常态化 抢购时代悄然退场",
     "summary": "中国基金报：i茅台加大自营投放，生肖酒、精品酒、100ml装均可从容下单；2026Q1 i茅台新增用户近1400万，销售收入215.53亿元同比+267.16%。官方零售价升至1639元后与批价利差收窄，投机者离场、真实消费回归。",
     "source_url": "https://www.toutiao.com/article/7671116263980139034/"},
    {"time": "07:30", "track": ["美股标普医药"], "title": "礼来8/6收涨1.89% 美银上调目标价至1400美元",
     "summary": "礼来8月6日收1191.94美元+1.89%，盘中高至1230.88；Q2收入229.7亿美元+48%，GLP-1产品Mounjaro/Zepbound驱动；美银上调目标价至1400美元，Cantor维持增持目标价1410美元。XLV 8/6 +0.18%连续走强。",
     "source_url": "https://news.10jqka.com.cn/field/20260807/678737785.shtml"},
]

added = 0
for n in add:
    if n["title"] not in existing_titles:
        news.append(n)
        existing_titles.add(n["title"])
        added += 1

with open(path, "w", encoding="utf-8") as f:
    json.dump(news, f, ensure_ascii=False, indent=1)
print(f"新闻存档新增 {added} 条, 累计 {len(news)} 条")
