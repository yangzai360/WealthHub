# -*- coding: utf-8 -*-
"""盘后档 2026-08-12：追加盘后新增新闻到 news JSON + DeepSeek 情绪标注"""
import json, os, time, urllib.request

BASE = '/Users/jieyang/Documents/WealthHub'
NEWS = os.path.join(BASE, 'data/processed/news')

# ---------- 盘后新增新闻（14:00-20:00 窗口） ----------
new_items = [
    {
        "id": "N20260812-019",
        "track": "恒生科技",
        "category": "业绩类",
        "title": "腾讯Q2财报落地：营收2047.85亿首破2000亿(+11%) Non-IFRS经营利润756.4亿(+9%) 剔除新AI产品+19% 资本开支527.8亿(+176%)上半年超2025全年",
        "summary": "8/12港股盘后腾讯发布2026Q2财报：营收2047.85亿元(+11%，首破2000亿、环比+4%)；毛利1184亿(+13%)；Non-IFRS经营利润756.4亿(+9%)，剔除新AI产品影响+19%至861亿；IFRS归母净利684.15亿(+9%)。资本开支527.84亿(+176%、环比+65%)，上半年847.2亿超2025全年792亿；自由现金流转负138亿（含AI预付款，剔除后376亿）。本土游戏+17%(473亿，《三角洲行动》《洛克王国:世界》创新高)、营销服务+22%(435.65亿，AIM+驱动)、金融科技及企业服务+9%(602.86亿，云服务受惠AI)。微信月活14.39亿(+2%)、视频号时长+20%。Hy3正式版上线（OpenRouter全球前三）、WorkBuddy 6月PC访问量破2000万、微信AI小微灰测。",
        "source": "WebSearch/腾讯财报+上证报+21世纪",
        "source_url": "https://news.qq.com/rain/a/20260812A09X8P00?adChannelId=tech"
    },
    {
        "id": "N20260812-020",
        "track": "宏观",
        "category": "宏观类",
        "title": "A股收评：三大指数缩量反弹沪指+0.32%创业板+1.49% CPO/地产/白酒集体爆发 超4100只个股上涨",
        "summary": "8/12 A股低开高走集体收红：沪指+0.32%(3946.68)、深成指+1.09%(14414.43)、创业板+1.49%(3602.08)、科创50+1.61%、北证50+0.23%；沪深两市成交2.15万亿(缩量~1686亿)；4128只上涨/1280下跌，涨停96家跌停0，赚钱效应76%。盘面：CPO/光模块爆发（炬光科技20cm涨停，集邦咨询上调2026全球九大CSP AI服务器出货量年增率至近31%、资本开支+90%破8867亿美元）；房地产午后拉升（北京限购松绑：非京籍五环内社保/个税2年调减至1年，全国超百城调整政策）；白酒活跃（今世缘涨停9.99%）；创新药延续强势（百花7连板、浙江医药/誉衡/康恩贝涨停）；油气/煤炭等周期调整（跷跷板效应）。晚间美国7月CPI将公布。",
        "source": "WebSearch/智通财经+金融界+证券之星",
        "source_url": "https://stock.stockstar.com/IG2026081200027787.shtml"
    },
    {
        "id": "N20260812-021",
        "track": "恒生科技",
        "category": "行业事件类",
        "title": "港股收盘：恒指-0.83%恒科-0.99%报4776.44 腾讯财报前-1.95%收461.6 阿里-3% 内房股与半导体强势领涨",
        "summary": "8/12港股三大指数续跌：恒指-0.83%(25440.17)、国企指数-0.96%(8446.27)、恒生科技-0.99%(4776.44)，主板成交2167.79亿港元。大型科网股集体低迷：腾讯-1.95%(461.6，财报前)、阿里巴巴-3%、京东-2.77%、百度-2.49%、美团/小米跌超1%；腾讯音乐绩后大跌12%+拖累影视娱乐、金蝶国际-8.68%(CFO称投资大模型公司或致利润波动)。逆势：内房股午后涨幅扩大（中国金茂+14%，'十五五'城市更新+北京限购松绑）、存储半导体/光通信活跃（中际旭创+8.8%、澜起/华虹+7%+，Lumentum财报超预期）。港股创新药走弱（港股创新药ETF广发-0.78%、主力流出1.06亿）。",
        "source": "WebSearch/新华社+财闻+腾讯财经",
        "source_url": "https://so.html5.qq.com/page/real/search_news?docid=70000021_6186a7c429c53652"
    },
    {
        "id": "N20260812-022",
        "track": "其他/宽基",
        "category": "行业事件类",
        "title": "通威股份+5.06%收13.49：多晶硅涨价预期升温 8大龙头'反内卷'倡议+期货主连+4.26% 主力净流入3.48亿",
        "summary": "8/12通威股份涨5.06%收13.49元，成交17.26亿，主力净流入3.48亿（占总成交20.16%）；协鑫科技/新特能源同步大涨5%左右，多晶硅期货主连+4.26%（8/6以来累计+6.44%）。催化：8月8大多晶硅龙头签署'反内卷'自律倡议、组件厂商明确涨价、贸易商积极参与；摩根大通预计硅料潜在上涨空间5-5.5万元/吨（边际生产商全成本+13%增值税）；上游惜售封盘+下游硅片/电池片价格小幅上行。但现货连续两周0成交、开工率不足40%、需求端全球装机增速回落——'弱现实强预期'，兑现时间存疑。光伏产业指数自7月底累计涨11%。",
        "source": "WebSearch/光伏头条+中粮期货+新浪证券",
        "source_url": "https://www.163.com/dy/article/L45AL8PV05568W0A.html"
    },
    {
        "id": "N20260812-023",
        "track": "A股医药",
        "category": "行业事件类",
        "title": "医药资金面分歧：医药生物主力净流出32.4亿 但Q2公募基金集体重仓医药 百花7连板换手35%PE202倍 哈药月涨180%",
        "summary": "8/12医药板块走势分化：医药生物-0.09%、创新药+0.37%、生物医药+0.54%，但资金面出现分歧——医药生物主力净流出32.4亿、创新药净流出36.9亿、生物医药净流出37.2亿（获利盘兑现），而医药电商/医药商业小幅净流入。情绪面：百花医药7连板（14.03元、PE 202.8倍 vs 同行34.96倍、换手近35%、龙虎榜游资现身，公司5次风险提示：CRO企业不涉及创新药研发）；哈药股份月涨超180%、万邦医药历史新高79.99元。基本面：'被冷落三年后基金经理开始重仓医药'——2026Q2众多基金公司将医药重新纳入投资重点，机构认为医药进入业绩兑现期（百济/药明/昭衍中报超预期）。",
        "source": "WebSearch/中新经纬+新京报+腾讯财经",
        "source_url": "https://m.chinanews.com/wap/detail/cht/zw/jw683236.shtml"
    },
    {
        "id": "N20260812-024",
        "track": "大消费",
        "category": "行业事件类",
        "title": "白酒板块活跃：今世缘涨停9.99% 申万宏源'300元以上价格带扩容' 北京限购松绑+金九银十预期催化地产消费共振",
        "summary": "8/12白酒板块活跃：今世缘涨停(9.99%)、古井贡酒/迎驾贡酒/皇台酒业/舍得酒业上涨，与地产（滨江/新城/荣盛涨停）、医药共同构成'喝酒吃药买房'修复主线。申万宏源研报：2026年白酒行业总容量持续萎缩但300元以上价格带仍扩容，竞争从'大鱼吃小鱼'进入'大鱼吃大鱼'；主力饮酒人群(30-60岁)2026年达峰值约3.3亿后下行，高端酒批价与人均可支配收入比值处历史低位，茅台/五粮液/国窖1573批价有望2026年企稳。消息面：北京优化限购（非京籍五环内社保2年→1年）+'金九银十'旺季预期+全国超百城调整楼市政策，地产链与消费情绪共振。",
        "source": "WebSearch/雪球+证券之星",
        "source_url": "https://xueqiu.com/3075122481/404733154"
    },
    {
        "id": "N20260812-025",
        "track": "宏观",
        "category": "宏观类",
        "title": "美国7月CPI今夜公布（北京20:30/21:30口径）：预期环比+0.1%同比3.4% 油价连续5日上涨Brent近90美元 金价突破4450美元 9月加息概率50%附近",
        "summary": "美国劳工部8/12（北京晚间20:30/21:30）公布7月CPI：路透调查预期整体CPI环比+0.1%(6月-0.4%)、同比3.4%(6月3.5%)；核心环比+0.2%、同比2.5%（2月以来最小）。7月非农意外负值使劳动力市场降温，但霍尔木兹海峡僵局推油价连续第五日上涨（Brent近90美元、WTI约84美元，伊朗称海峡关闭至诉求满足），9月加息概率回升至50%附近（期货隐含61.9%）。美银：核心服务反弹（预期环比+0.3%）使加息仍可能；德银：汽油降约2%拉低整体CPI至3.45%。SPX期权隐含当日0.58%波动、VIX1D+34%。金价COMEX突破4450美元（黄金ETF 6连涨，中金建议超配黄金）。CPI≥3.6%则加息预期回归、成长/QDII承压；≤3.4%则缓和。",
        "source": "WebSearch/金十数据+中证报+盛宝银行",
        "source_url": "https://xnews.jin10.com/details/227119"
    },
    {
        "id": "N20260812-026",
        "track": "A股医药",
        "category": "行业事件类",
        "title": "医疗器械午后反弹：8款创新器械进入特别审查 宝莱特20cm涨停 澳华内镜涨超10%",
        "summary": "8/12午后医疗器械板块震荡反弹：宝莱特20cm涨停、澳华内镜涨超10%、鹿得医疗/康众医疗/南卫股份/戴维医疗跟涨。消息面：国家药监局医疗器械技术审评中心8/10发布《创新医疗器械特别审查申请审查结果公示(2026年第13号)》，8款产品进入创新医疗器械特别审查程序。叠加创新药中报兑现（百济+627%/药明+29.43%上调指引）与出海BD（上半年997-1063亿美元），医药器械创新链条政策与业绩双支撑。",
        "source": "WebSearch/金融界",
        "source_url": "https://www.163.com/dy/article/L451MB3S0519QIKK.html"
    },
]

# ---------- 追加到 news JSON ----------
news_path = os.path.join(NEWS, 'news-2026-08-12.json')
with open(news_path, encoding='utf-8') as f:
    news = json.load(f)
existing_ids = {n['id'] for n in news}
added = [n for n in new_items if n['id'] not in existing_ids]
news.extend(added)
with open(news_path, 'w', encoding='utf-8') as f:
    json.dump(news, f, ensure_ascii=False, indent=1)
print(f'news-2026-08-12.json: 新增 {len(added)} 条，当前共 {len(news)} 条')

# ---------- DeepSeek 情绪标注（新增 8 条） ----------
with open('/Users/jieyang/.pi/agent/auth.json') as f:
    key = json.load(f)['deepseek']['key']

def ds_annotate(item):
    prompt = f"""你是投资组合情绪分析器。对以下财经新闻做情绪标注，仅输出 JSON（不要多余文字）：
{{
  "sentiment": "正面|中性|负面",
  "strength": 0-100,
  "impact_direction": "利多|中性|利空",
  "expected_volatility": "低|中|高",
  "reason": "一句话理由"
}}
新闻赛道: {item['track']}
标题: {item['title']}
摘要: {item['summary']}"""
    data = {
        "model": "deepseek-v4-flash",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 8000,
        "temperature": 0.3,
    }
    req = urllib.request.Request("https://api.deepseek.com/chat/completions",
        data=json.dumps(data).encode(),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        result = json.load(resp)
    content = result['choices'][0]['message']['content']
    if not content or not content.strip():
        raise ValueError('empty content')
    # 提取 JSON
    start = content.find('{'); end = content.rfind('}')
    return json.loads(content[start:end+1])

annotations = []
for item in added:
    for attempt in range(2):
        try:
            ann = ds_annotate(item)
            annotations.append({
                'id': item['id'], 'track': item['track'], 'category': item['category'],
                'title': item['title'], 'source_url': item['source_url'],
                'sentiment': ann['sentiment'], 'strength': ann['strength'],
                'impact_direction': ann['impact_direction'],
                'expected_volatility': ann['expected_volatility'], 'reason': ann['reason'],
            })
            print(f"  {item['id']}: {ann['sentiment']} {ann['strength']} {ann['impact_direction']}")
            break
        except Exception as e:
            print(f"  {item['id']} 重试 {attempt+1}: {e}")
            time.sleep(3)
    time.sleep(1)

# 追加到 sentiment JSON
sent_path = os.path.join(NEWS, 'sentiment-2026-08-12.json')
with open(sent_path, encoding='utf-8') as f:
    sent = json.load(f)
existing_ids = {s['id'] for s in sent}
for a in annotations:
    if a['id'] not in existing_ids:
        sent.append(a)
with open(sent_path, 'w', encoding='utf-8') as f:
    json.dump(sent, f, ensure_ascii=False, indent=1)
print(f'sentiment-2026-08-12.json: 当前共 {len(sent)} 条')
print('DONE')
