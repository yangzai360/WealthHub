# -*- coding: utf-8 -*-
"""2026-08-13 盘中: 构建盘中新增新闻 (07:30-13:30 窗口)"""
import json, os

base = "/Users/jieyang/Documents/WealthHub"
news_path = os.path.join(base, "data/processed/news/news-2026-08-13.json")
sent_path = os.path.join(base, "data/processed/news/sentiment-2026-08-13.json")

# 已归档盘前新闻标题（用于去重）
existing = []
if os.path.exists(news_path):
    with open(news_path, encoding="utf-8") as f:
        existing = json.load(f)
elif os.path.exists(sent_path):
    with open(sent_path, encoding="utf-8") as f:
        existing = json.load(f)
existing_titles = set(n.get("title", "")[:40] for n in existing)
print(f"已归档 {len(existing)} 条")

# 盘中新增新闻（窗口 07:30-13:30）
intraday = [
    {
        "title": "腾讯低开超3%：Q2 GAAP净利560.2亿(+0.7%)不及预期、Non-IFRS 684亿(+8.5%)超预期，资本开支527.8亿(+176%)远超市场预估321亿",
        "category": "业绩类",
        "time": "2026-08-13T09:30",
        "source_url": "https://hk.finance.yahoo.com/news/%E9%A8%B0%E8%A8%8A-00700-hk-%E4%BD%8E%E9%96%8B%E9%80%BE3-%E6%AC%A1%E5%AD%A3%E8%B3%87%E6%9C%AC%E9%96%8B%E6%94%AF527-013525338.html",
        "summary": "腾讯8/13低开3.29%报446.4港元，Q2收入2,047.85亿(+11%)略超预期，GAAP净利560.2亿(+0.7%)按季-4%不及预期，Non-IFRS净利684亿(+8.5%)超预期；资本开支527.84亿(+176%、环比+65%)远超市场预估321亿，自由现金流转负138亿。刘炽平：资本配置为动态模式，若AI持续回报才继续加大投入。",
    },
    {
        "title": "恒生科技指数午后直线拉升超1%：联想+18%（Q1溢利+176%、AI收入+60%）、华虹宏力/MINIMAX涨超5%、智谱/中芯/百度领涨，腾讯跌超3%",
        "category": "行业事件类",
        "time": "2026-08-13T13:05",
        "source_url": "https://new.qq.com/rain/a/20260813A07LZB00?refer=cp_1009",
        "summary": "8/13恒生科技指数午后直线拉升，涨幅扩大至1%以上。联想集团第一财季经调整溢利同比+176%、AI相关业务收入+60%，午后猛拉逼近+18%；华虹宏力、MINIMAX涨超5%，智谱、中芯国际、百度等涨幅居前。腾讯控股跌超3%（市值约4.04万亿港元），受FCF转负担忧拖累。",
    },
    {
        "title": "港股通信息技术ETF汇添富(526030)大涨超2%：恒生科技扩容至50只解读，AI硬件+大模型含量更高受益",
        "category": "行业事件类",
        "time": "2026-08-13T10:21",
        "source_url": "https://www.163.com/dy/article/L4736BIO0534A4SC.html",
        "summary": "恒生科技指数探底回升翻红，港股通信息技术ETF汇添富(526030)大涨超2%。腾讯Q2收入2,047.85亿(+11%)、调整后净利684.15亿(+9%)，资本开支528亿(+176%)主要用于AI算力采购；高管称AI投入已看到明显回报上行空间，现金流承压源于AI前置采购非经营恶化。AI应用类小程序半年增长近40%。",
    },
    {
        "title": "创新药板块强势领涨：科创创新药ETF国泰(589720)盘中大涨超5%，科创板生物医药指数+4.22%（热景生物+9.07%、君实生物+8.28%、成都先导+8.10%）",
        "category": "行业事件类",
        "time": "2026-08-13T13:03",
        "source_url": "https://new.qq.com/rain/a/20260813A07KFT00?refer=cp_1009",
        "summary": "8/13盘中医疗服务、化学制药、CRO、创新药等板块涨幅居前，科创板生物医药指数+4.22%，科创创新药ETF国泰(589720)一度+5.19%、成交超10亿。医药魔方：2026H1国内药企对外授权交易总额997亿美元超2025全年七成，全球前十授权交易中国占8席。兴业证券：创新药迎'技术范式革新+业绩高景气共振'双重利好，AIDD将新药研发周期13年缩短至8年、成本降至7亿美元。",
    },
    {
        "title": "午评：医药股集体爆发——南模生物/博济医药20cm涨停，CRO/减肥药/免疫治疗大涨，上海'20条'新政打通科创企业募投管退全链条",
        "category": "政策类",
        "time": "2026-08-13T11:32",
        "source_url": "https://dy.163.com/article/L47771S705568W0A.html",
        "summary": "8/13午盘沪指+0.42%、创业板指+1.61%、科创50+1.90%。医药股集体爆发：南模生物、博济医药20cm涨停，CRO概念（万邦医药、近岸蛋白、皓元医药）走强；财通证券：三靶点/口服GLP-1/环肽/小核酸新分子需求旺盛+中国成本交付优势，外需驱动CDMO业绩持续兑现。上海'20条'新政打通科创企业'募投管退'全链条堵点，允许未盈利及破发企业再融资，利好创新药。",
    },
    {
        "title": "白酒板块震荡拉升：会稽山涨停、古井贡酒/山西汾酒涨超4%、茅台+1.12%报1358，中秋备货+中报催化（茅台中报8/14盘后发布）",
        "category": "行业事件类",
        "time": "2026-08-13T13:00",
        "source_url": "https://new.qq.com/rain/a/20260813A064IE00?refer=cp_1009",
        "summary": "8/13盘中白酒股直线拉升，会稽山涨停，古井贡酒、山西汾酒涨超4%，茅台+1.12%报1,358元。临近中秋旺季，飞天茅台自营店零售价上调至1,753元/瓶，第八代普五批价同步上涨。茅台中报8/14盘后发布。多数白酒股（五粮液/汾酒/老窖/洋河/今世缘）股价已低于'924'低点，估值显著偏低，市场酝酿修复性行情。",
    },
    {
        "title": "食品饮料延续活跃：皇氏集团4连板、一鸣食品13天9板；瑞幸'秋天的第一杯奶茶'单日2500万杯创新高，奶价触底反转信号明确",
        "category": "行业事件类",
        "time": "2026-08-13T11:32",
        "source_url": "https://dy.163.com/article/L47771S705568W0A.html",
        "summary": "食品饮料板块延续活跃：皇氏集团4连板、一鸣食品13天9板。瑞幸咖啡立秋'秋天的第一杯奶茶'销量2,500万杯创历史新高，蜜雪冰城刷新年度纪录。国海证券：奶牛首次产奶需约24月龄叠加牧场决策时滞，完整周期7-8年，4月以来部分地区散奶价格大涨、主产区生鲜乳均价底部抬头，奶价触底反转信号较为明确；华西证券预计2026供需基本平衡、2027缺口扩大。",
    },
]

# 过滤掉已存在的（标题前 40 字匹配）
new_items = [n for n in intraday if n["title"][:40] not in existing_titles]
print(f"盘中新增 {len(new_items)} 条")

# 合并写入 news-2026-08-13.json
combined = existing + new_items
with open(news_path, "w", encoding="utf-8") as f:
    json.dump(combined, f, ensure_ascii=False, indent=2)
print(f"news-2026-08-13.json 共 {len(combined)} 条")

# 同时写一份给 DeepSeek 标注用的临时文件
with open("/tmp/intraday_news_20260813.json", "w", encoding="utf-8") as f:
    json.dump(new_items, f, ensure_ascii=False, indent=2)
print("已写 /tmp/intraday_news_20260813.json")
for n in new_items:
    print(f"  [{n['category']}] {n['title'][:45]}")
