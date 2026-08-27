# -*- coding: utf-8 -*-
"""盘后档 2026-08-27：追加盘后新闻（14:00-20:00 窗口，8 条）到 news-2026-08-27.json"""
import json, os

BASE = '/Users/jieyang/Documents/WealthHub'
NEWS_PATH = os.path.join(BASE, 'data/processed/news/news-2026-08-27.json')

with open(NEWS_PATH, encoding='utf-8') as f:
    news = json.load(f)
existing_titles = set(n['title'] for n in news)

new_items = [
    {
        "time": "2026-08-27 15:05",
        "track": "宏观",
        "category": "宏观类",
        "title": "A股8/27收盘：沪指+1.13%报3,956.57、深成指+1.50%、创业板+1.71%、科创50+3.77%——三大指数均涨超1%，成交2.13万亿放量3,172亿、超3300股上涨；存储芯片涨停潮（大普微/德明利/联瑞新材20cm）、CPO/光刻机/先进封装/PCB算力硬件爆发、粮食概念续强（万向德农3连板）；银行/白酒/传媒领跌",
        "summary": "英伟达2028指引+70%直接催化算力硬件全面爆发，A股普涨放量；白酒逆势走弱（伊力特-3.79%/洋河-2.58%）",
        "source": "证券时报/中新经纬/网易",
        "source_url": "https://stcn.com/article/detail/4138666.html",
    },
    {
        "time": "2026-08-27 16:20",
        "track": "恒生科技",
        "category": "行业事件类",
        "title": "港股8/27收盘：恒指-0.34%报25,565.74、恒科-0.13%报4,620.29、国企指数-0.51%报8,490.31，成交2,335亿港元缩量；南向净买入31.8亿港元（8/26 +4.53亿后连续回正）——翰森制药+16.01%（H1净利+35.82%创新药占比85.4%）、百度+5.3%（9/1双重主要上市+纳入港股通倒计时）、智谱+12.62%大涨（AI大模型概念）；消费股财报拖累（蜜雪-8%/达势-14%/海天味业-11.21%）；小鹏-3.34%/商汤-3.06%/蔚来-2.91%",
        "summary": "英伟达财报点燃硬件行情但港股高开低走，恒科守住4,600；南向净买入31.8亿为企稳信号；消费股财报普跌拖累大市",
        "source": "每经/中国基金报/腾讯新闻",
        "source_url": "https://new.qq.com/rain/a/20260827A0AAQ400?refer=cp_1009",
    },
    {
        "time": "2026-08-27 15:30",
        "track": "A股医药",
        "category": "业绩类",
        "title": "百利天恒8/27收盘：+1.04%报271.99（低开268.00下探257.31 -4.4%后翻红收涨），振幅5.75%、成交5.18亿——III期利多定价未决转正，创新药指数+1.06%、生物医药+0.95%、医药生物板块+0.80%",
        "summary": "百利天恒日内V型反转收涨1.04%，创新药板块回正——医药兑现后企稳信号增强",
        "source": "东方财富",
        "source_url": "https://quote.eastmoney.com/sh688506.html",
    },
    {
        "time": "2026-08-27 15:40",
        "track": "大消费",
        "category": "行业事件类",
        "title": "白酒8/27收盘：白酒概念-0.15%（主力净流出10.67亿：五粮液-5.42亿/茅台-3.20亿/泸州老窖-6,646万居前）；洋河-2.58%报38.88（低开-2.0%后窄幅震荡，软着陆确认）、茅台1,292.30、五粮液71.12；中证消费12,489.39（+0.04%）守住12,400——白酒财报周后半程（8/28老窖除息/8/29五粮液+古井财报）",
        "summary": "白酒板块资金流出但洋河软着陆第2次确认（未恐慌杀跌），中证消费守住12,400防线",
        "source": "证券时报/网易",
        "source_url": "https://www.toutiao.com/article/7678629787706933811",
    },
    {
        "time": "2026-08-27 16:00",
        "track": "美股标普医药",
        "category": "行业事件类",
        "title": "美股医疗8/26收盘：XLV 173.54（-1.00%）、IYH 73.40（-0.98%）——PCE偏鹰+财报日科技焦点下医疗板块连续回落（8/25 +0.34%→8/26 -1.00%）；QDII广发全球医疗A/C 8/26净值-0.93%/-0.95%已兑现8/26美股跌幅，将于8/27-28组合显现",
        "summary": "美股医疗连续2日回落（-1.00%），QDII净值-0.93%/-0.95%已锁定兑现；8/28杰克逊霍尔前医疗防御逻辑承压",
        "source": "Yahoo Finance/腾讯自选股",
        "source_url": "https://finance.yahoo.com/quote/XLV/risk",
    },
    {
        "time": "2026-08-27 17:00",
        "track": "宏观",
        "category": "宏观类",
        "title": "英伟达财报后全球AI链盘后大涨（8/27凌晨）：盘后+4.57%报219.25、一度涨超5%；2028财年指引+70%（市场预期45%）供应受限下仍超预期——存储（SK海力士ADR+4.4%/美光+4%/闪迪+4.2%）、光通信（Coherent+3%/Lumentum+3%）、AI云（CoreWeave+5%/Nebius+6%）集体走强；纳指100期货+0.94%；Salesforce盘后+13%（Q3指引超预期+Anthropic合作）",
        "summary": "英伟达财报全面超预期（Q3指引1,080亿/2028指引+70%）为全球AI算力链最强催化，今日A股算力硬件已充分定价",
        "source": "证券时报/券商中国",
        "source_url": "https://www.stcn.com/article/detail/4138046.html",
    },
    {
        "time": "2026-08-27 18:30",
        "track": "宏观",
        "category": "宏观类",
        "title": "8/28杰克逊霍尔前瞻（明日）：美联储主席沃什周五演讲成关键节点——市场预计不提供明确9月指引；PCE后12月加息已完全定价（money market）；10Y美债4.647%（-1.5bp）回落；美元99.12持稳；黄金4,624.14（+0.7%）收复部分失地；WTI回落、布伦特87.20（-0.7%）四连跌（卡塔尔首相访伊推进停火）；小麦三年新高（俄乌升级+全球粮食价格7月连涨3月）",
        "summary": "8/28沃什杰克逊霍尔为全球市场下一总开关；美债收益率回落+黄金企稳缓解部分压力，但PCE后12月加息完全定价压制成长",
        "source": "Saxo/Straits Times/华尔街见闻",
        "source_url": "https://www.home.saxo/content/articles/macro/market-quick-take---nvidia-rises-on-strong-earnings-and-growth-outlook-27082026",
    },
    {
        "time": "2026-08-27 19:30",
        "track": "恒生科技",
        "category": "业绩类",
        "title": "百度集团8/27大涨5.3%（9/1完成香港双重主要上市、纳入港股通倒计时）：翰森制药+16.01%（H1净利+35.82%）领涨恒指成分；智谱+12.62%大涨（认领AI大模型'牛来'、使用量超DeepSeek两倍）、MiniMax+3.83%（8月ARR破8亿美元）——港股AI应用/大模型概念爆发",
        "summary": "百度双重主要上市+港股通纳入倒计时为资金面利多，AI应用股（智谱/MiniMax）爆发提振恒科情绪",
        "source": "中国基金报",
        "source_url": "https://new.qq.com/rain/a/20260827A0AJCY00?refer=cp_1009",
    },
]

added = []
for n in new_items:
    if n['title'] in existing_titles:
        print('跳过(已存在):', n['title'][:40])
        continue
    news.append(n)
    existing_titles.add(n['title'])
    added.append(n['title'][:40])
    print('新增:', n['title'][:40])

with open(NEWS_PATH, 'w', encoding='utf-8') as f:
    json.dump(news, f, ensure_ascii=False, indent=1)
print(f'\nnews-2026-08-27.json 共 {len(news)} 条（新增 {len(added)}）')
