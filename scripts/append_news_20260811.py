# -*- coding: utf-8 -*-
"""盘后档：追加 14:00-20:00 新增新闻到 news-2026-08-11.json"""
import json, os

BASE = '/Users/jieyang/Documents/WealthHub'
NEWS = os.path.join(BASE, 'data/processed/news/news-2026-08-11.json')
SENT = os.path.join(BASE, 'data/processed/news/sentiment-2026-08-11.json')

d = json.load(open(NEWS))
existing_ids = {x['id'] for x in d}

new_news = [
    {
        "id": "N20260811-025",
        "date": "2026-08-11",
        "track": "宏观",
        "category": "宏观类",
        "title": "A股收评：冲高回落超3700只个股下跌 沪指-0.82%成交2.32万亿缩量2021亿 机器人/MLCC/算力租赁逆势",
        "summary": "8/11收盘：沪指-0.82%报3934.77点、深成指-0.40%、创业板指+0.34%、科创50-1.63%；两市成交2.32万亿较前日缩量2021亿，全市场超3700只个股下跌，涨跌比约1:2.3。热点杂乱：机器人概念午后走强（巨轮智能/北特科技涨停）、MLCC概念拉升（双星新材/洁美科技/国风新材涨停，部分客户以原价2-3倍抢料、交期拉长至12-16个月）、算力租赁异动（杭钢/鸿博涨停）；创新药反复活跃（百花医药6连板、甘李/万邦涨停）；医药商业补涨（开开实业4连板、老百姓涨停）。下跌方面有色金属回落（洛阳钼业/西部矿业/赤峰黄金下挫，黄金稀土调整）。全市场ETF成交4299.8亿缩量579.2亿，仅390余只收涨。",
        "source": "WebSearch/财联社收评",
        "source_url": "https://finance.eastmoney.com/a/202608113837914087.html",
        "sentiment": "中性",
        "strength": 50,
        "impact_direction": "中性",
        "expected_volatility": "高",
        "reason": "指数缩量震荡、普跌但结构性热点轮动"
    },
    {
        "id": "N20260811-026",
        "date": "2026-08-11",
        "track": "A股医药",
        "category": "行业事件类",
        "title": "医药生物主力资金持续涌入：早盘净流入114亿 近5日391亿 近20日790亿 近60日1665亿 医药商业补涨",
        "summary": "Wind监测：8/11早盘医药生物行业主力资金净流入逾114亿元，近5交易日合计391亿元、近20交易日790亿元、近60交易日1665亿元。医药商业一马当先（开开实业4连板、老百姓/一心堂/第一医药涨停），生物制品/减肥药/创新药/仿制药涨幅居前；哈药股份获逾10亿主力净流入、恒瑞/药明康德逾8亿。万联证券：线下药店行业出清加速，强者恒强。资金从创新药向整条医药产业链扩散，医药商业等滞涨赛道补涨，或夯实本轮医药行情基础。",
        "source": "WebSearch/证券时报",
        "source_url": "https://www.163.com/dy/article/L428N7P6053469RG.html",
        "sentiment": "正面",
        "strength": 65,
        "impact_direction": "利多",
        "expected_volatility": "中",
        "reason": "医药资金持续净流入、行情向产业链扩散，但已连续流入需防高位分歧"
    },
    {
        "id": "N20260811-027",
        "date": "2026-08-11",
        "track": "A股医药",
        "category": "行业事件类",
        "title": "吃药行情冲高回落：甘李药业涨停兑现7.26亿欧元出海 百济神州6连阳创新高 但药明康德冲高165.8元回落收160.21",
        "summary": "8/11医药冲高回落：甘李药业涨停（上日盘后公告博凡格鲁肽出海欧洲潜在总金额最高7.26亿欧元，今日兑现）；百济神州+2.63%斩获6连阳股价创年内新高；港股药明康德盘中涨超3%续创新高（A股早盘冲高165.8元回落收160.21、振幅近5%），药明生物摸高3.6%后收跌。港股通医疗ETF华宝(159137)一度涨2.5%续刷5个月高点收涨0.42%三连阳；港股通创新药ETF(520880)盘中涨超2%收涨0.22%。西南证券：8-9月创新药业绩兑现+临床数据（WCLC 9月/ESMO 10月）+出海三重共振。",
        "source": "WebSearch/腾讯新闻",
        "source_url": "https://new.qq.com/rain/a/20260811A0AEGR00",
        "sentiment": "中性",
        "strength": 55,
        "impact_direction": "中性",
        "expected_volatility": "高",
        "reason": "主线仍强但盘中冲高回落、获利盘兑现迹象明显，高位波动加大"
    },
    {
        "id": "N20260811-028",
        "date": "2026-08-11",
        "track": "恒生科技",
        "category": "行业事件类",
        "title": "港股集体收跌：恒指-1.10%收25652.82 恒生科技-1.93%收4824.42 腾讯-2.20% 小米-3.48% 快手-3.79% 财报前避险",
        "summary": "港股8/11三大指数齐跌：恒指-1.10%报25652.82（主板成交2109.42亿港元）、恒生科技-1.93%报4824.42、国企指数-1.09%报8528.1。大型科网股午后跌幅扩大：腾讯-2.20%收470.8、小米-3.48%、京东-2.99%、快手-3.79%、哔哩哔哩-2.97%、百度跌超2%、阿里-0.24%。黄金股大跌（老铺黄金-8%、灵宝黄金-8%、紫金黄金国际-7%）；PCB概念下挫（芯碁微装-9%）；石油股逆势上涨（中海油+3.59%、中石油+1.78%）；机器人概念走高（微创机器人+7%、埃斯顿+6%）。",
        "source": "WebSearch/新华社/腾讯新闻",
        "source_url": "https://new.qq.com/rain/a/20260811A0ACLA00?refer=cp_1009",
        "sentiment": "负面",
        "strength": 60,
        "impact_direction": "利空",
        "expected_volatility": "高",
        "reason": "腾讯财报前科网股集体避险回调，明日财报落地前压制恒科"
    },
    {
        "id": "N20260811-029",
        "date": "2026-08-11",
        "track": "A股医药",
        "category": "行业事件类",
        "title": "港股创新药逆势走强：基石药业+11% 再鼎+5.28% 百济神州+2.63%六连阳 药明康德盘中创历史新高",
        "summary": "8/11港股创新药概念股持续走强：基石药业涨超11%、乐普生物+3%、药明合联+2%、百济神州+2.63%斩获6连阳股价创年内新高、药明康德盘中创历史新高（收涨0.56%）。国金证券：创新药企业扭亏节点到来，全年临床数据催化密集，叠加BD出海管线海外临床进展顺利，看好板块投资机会。国元国际：上半年中国创新药出海交易总额997亿美元、全球TOP10独占8席。港股涨幅前10大细分板块中有9个与医药相关。",
        "source": "WebSearch/腾讯新闻",
        "source_url": "https://new.qq.com/rain/a/20260811A0ACLA00?refer=cp_1009",
        "sentiment": "正面",
        "strength": 68,
        "impact_direction": "利多",
        "expected_volatility": "中",
        "reason": "创新药产业兑现+出海叙事强化，港股医药逆势领涨"
    },
    {
        "id": "N20260811-030",
        "date": "2026-08-11",
        "track": "大消费",
        "category": "行业事件类",
        "title": "白酒板块回调：板块-0.60% 茅台-0.17%收1346.50 主力净流出5.32亿 大消费板块-1.01% 冲高回落",
        "summary": "8/11白酒Ⅱ板块-0.60%收37714.30（振幅1.46%、量比0.77），主力净流入市场排名100/124、主力净流出5.32亿；贵州茅台-0.17%收1346.50（主力净流入4.89亿居食品饮料首位的昨日强势后今日微跌）；泸州老窖-0.63%、迎驾贡酒+0.17%。大消费板块-1.01%收1026.19（主力净流出22.13亿）。8/10白酒大涨+2.50%后今日回踩，符合冲高回落预期；猪肉概念逆势普涨（牧原股份+2.2%，7家上市猪企7月合计生猪销量1182万头同比+4.3%）。",
        "source": "WebSearch/同花顺行情数据",
        "source_url": "https://stock.10jqka.com.cn/20260811/c678849556.shtml",
        "sentiment": "负面",
        "strength": 55,
        "impact_direction": "利空",
        "expected_volatility": "中",
        "reason": "白酒大涨后正常回踩、主力转净流出，但批价续涨未破位"
    },
    {
        "id": "N20260811-031",
        "date": "2026-08-11",
        "track": "宏观",
        "category": "宏观类",
        "title": "美国7月CPI明日21:30公布：预期同比3.4%核心2.5%月率+0.1% 摩根大通预警最大2%波动 CME9月加息概率上修至略超50%",
        "summary": "8/12北京时间21:30美国劳工部公布7月CPI：预期未季调CPI同比3.4%（前值3.5%）、核心CPI同比2.5%（前值2.6%）、CPI月率+0.1%（前值-0.4%）、核心CPI月率+0.2%（前值0.0%）。摩根大通预警CPI或引发标普500最大2%波动；CME数据显示9月加息概率略超50%（较盘前44%上修）。若7月CPI与核心CPI同比均小幅低于前值，美联储大概率将加息时间从9月推迟至10月或12月，今年大概率仅加息25bp。油价反弹与核心服务业通胀为最大上行风险。",
        "source": "WebSearch/同花顺/每日经济新闻",
        "source_url": "https://stock.10jqka.com.cn/20260811/c678849556.shtml",
        "sentiment": "中性",
        "strength": 75,
        "impact_direction": "中性",
        "expected_volatility": "高",
        "reason": "CPI为美联储9月决议核心参考，9月加息概率上修至五五开，波动风险升级"
    },
    {
        "id": "N20260811-032",
        "date": "2026-08-11",
        "track": "宏观",
        "category": "宏观类",
        "title": "美伊'墨西哥式对峙'油价或在75-95美元区间波动 燃料成本上涨令明日CPI更加关键",
        "summary": "美伊双方言辞交锋升级、重开关键航道努力复杂化，分析师形容双方陷入'墨西哥式对峙'：等待谁先让步期间油价或75-95美元区间波动。近期燃料成本再次上涨，令8/12美国7月CPI更加关键——若通胀数据意外高于预期，可能重新点燃市场对美联储9月加息的押注；目前市场对9月加息判断接近五五开。",
        "source": "WebSearch/腾讯新闻",
        "source_url": "https://so.html5.qq.com/page/real/search_news?docid=70000021_4726a7adb5140152",
        "sentiment": "负面",
        "strength": 65,
        "impact_direction": "利空",
        "expected_volatility": "高",
        "reason": "油价高位波动推升通胀预期，CPI前夜全球风险偏好承压"
    },
    {
        "id": "N20260811-033",
        "date": "2026-08-11",
        "track": "A股医药",
        "category": "业绩类",
        "title": "创新药商业化兑现：信达生物Q2收入43亿+60% 百济Q2全球收入17.05亿美元+30%上调利润指引 再鼎+11%",
        "summary": "创新药海内外商业化持续兑现：信达生物Q2产品收入超43亿元（同比+60%、环比+10%）；百济神州Q2全球总收入17.05亿美元（同比+30%）、上调全年利润指引，泽布替尼多地需求超预期；再鼎医药Q2产品销售环比+11%。公募排排网：上周医药生物行业公募调研104次，热度反超电子居申万一级行业首位。Q2公募医药仓位降至5年冰点，低配状态下易引发扩散性行情。",
        "source": "WebSearch/腾讯新闻",
        "source_url": "https://new.qq.com/rain/a/20260811A0AEGR00",
        "sentiment": "正面",
        "strength": 70,
        "impact_direction": "利多",
        "expected_volatility": "中",
        "reason": "业绩兑现+公募低配双支撑，医药行情扩散有基本面背书"
    },
]

added = 0
for n in new_news:
    if n['id'] not in existing_ids:
        d.append(n)
        existing_ids.add(n['id'])
        added += 1
json.dump(d, open(NEWS, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(f'news-2026-08-11.json: +{added} 条（盘后新增），total {len(d)}')

# 盘后新增新闻直接写入 sentiment 文件（统一由 DeepSeek 重标，先写占位）
s = json.load(open(SENT))
sent_ids = {x['id'] for x in s}
for n in new_news:
    if n['id'] not in sent_ids:
        s.append({'id': n['id'], 'track': n['track'], 'category': n['category'], 'title': n['title'],
                  'source_url': n['source_url'], 'sentiment': n['sentiment'], 'strength': n['strength'],
                  'impact_direction': n['impact_direction'], 'expected_volatility': n['expected_volatility'], 'reason': n['reason']})
json.dump(s, open(SENT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(f'sentiment-2026-08-11.json: total {len(s)}')
