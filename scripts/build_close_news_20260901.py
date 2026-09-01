# -*- coding: utf-8 -*-
"""盘后档 2026-09-01：构建盘后 7 条新闻（14:00-20:00 窗口）+ DeepSeek 情绪标注 + 合并 sentiment/news"""
import json, os, urllib.request, time

BASE = '/Users/jieyang/Documents/WealthHub'
NEWS_DIR = os.path.join(BASE, 'data/processed/news')
TODAY = '2026-09-01'

# ---------- 盘后 7 条新闻（手动整理，带 source_url） ----------
close_news = [
    {
        "track": "宏观", "category": "行业事件类",
        "title": "A股9月开门「指数弱、结构强」：沪指-0.16%报3,979.89距4,000仅20点（盘中最高3,995.18三度冲击未破）、创业板-1.32%、深成指-1.02%、沪深300-0.30%；成交20,334亿缩量976亿；农业（万向德农6连板/隆平高科涨停/神农种业）、商贸零售+3.08%（茂业商业/东百集团/国芳集团涨停）、银行批量历史新高（中行/建行/成都/江苏）领涨；电子-2.99%主力净流出221.68亿居首（半导体/PCB/CPO回调）——消费/农业/银行 vs AI硬件结构性轮动，主力全天净流出237.77亿",
        "summary": "A股9月开门指数弱结构强：消费农业银行领涨、AI硬件回调，沪指距4000仅20点未破",
        "source": "证券时报", "source_url": "https://www.stcn.com/article/detail/4167284.html",
    },
    {
        "track": "恒生科技", "category": "行业事件类",
        "title": "港股9月开门黑：恒指-0.93%报25,329.73连跌两日（累跌255点）、恒科-1.49%报4,550.88收日内最低点（守4,500）、国指-0.59%、成交2,387亿港元回落至3,000亿下；大型科网普跌（阿里-3.3%/京东-3.2%/腾讯-2.6%/美团-2.9%/百度-2.6%/网易-1.87%/B站-2.87%/小米-0.2%）、内房续跌（越秀-7%/建发国际4连跌/龙湖-3.8%）、PCB概念-5%、濠赌股走低；内银强势（农行+2.6%、中行/工行历史新高）+猪肉（德康农牧+6%猪价站上11元）/乳业消费活跃；快手+3.2%逆市（北京可灵获国家队注资14亿元）",
        "summary": "港股9月开门黑：科网内房PCB普跌、恒科收日内最低守4500，内银消费强势、快手逆市+3.2%",
        "source": "格隆汇/网易财经", "source_url": "https://www.163.com/dy/article/L5OMK2D605198ETO.html",
    },
    {
        "track": "A股医药", "category": "政策类",
        "title": "2026版基药目录9/1施行首日A股医药温和定价收盘确认：创新药午后逆市走强（透景生命20CM涨停/千金药业5天4板/瑞康医药/沃华医药/小方制药涨停）、医药生物+0.48%、生物医药+1.17%、医药商业+1.40%、医疗ETF+0.59%/医药ETF广发+0.47%收盘——「政策底半定价」从盘中温和转向收盘确认（8/31未定价→9/1温和定价）；国家卫健委等四部门同步印发《2026年基本公共卫生服务工作的通知》；中邮证券：创新药产业链高景气+CXO半年报超预期，看好下半年核心资产价值回归",
        "summary": "基药目录施行首日医药温和定价确认：创新药午后走强多股涨停、CXO景气上行",
        "source": "腾讯新闻/证券时报", "source_url": "https://news.qq.com/rain/a/20260901A0AEZZ00",
    },
    {
        "track": "A股医药", "category": "业绩类",
        "title": "港股医药外包/创新药收涨：金斯瑞生物科技+7%、药明康德/药明生物/凯莱英收涨——招商证券：CXO板块2026上半年营收+24.5%/归母净利+52.7%利润增速接近上轮周期高点、在手订单与新签订单全面回暖、龙头上调全年指引；融资环境持续向好为创新药研发提供资金保障；叠加基药目录+百济PD-1海外定价双催化",
        "summary": "港股CXO医药外包收涨：金斯瑞+7%，CXO上半年净利+52.7%接近周期高点",
        "source": "格隆汇/网易财经", "source_url": "https://www.163.com/dy/article/L5OMK2D605198ETO.html",
    },
    {
        "track": "大消费", "category": "政策类",
        "title": "大消费9/1领涨定价收盘确认：中证消费12,623.92（+1.15%）收稳12,600、白酒概念+2.35%（古井贡酒涨停/茅五泸延续昨强）、商贸零售+3.08%（零售涨停潮壹网壹创/茂业商业/东百集团）、农林牧渔+2.48%（猪价站上11元德康农牧+6%）——商务部等7部门60万亿消费扩容方案首日全面定价 + 白酒「利空出尽」软着陆第5次验证收盘确认（19家酒企中报利空数据出尽、中信证券：白酒基本面底部企稳）",
        "summary": "大消费领涨：中证消费+1.15%收稳12600、60万亿政策首日全面定价、白酒软着陆第5次验证",
        "source": "澎湃新闻", "source_url": "https://www.thepaper.cn/newsDetail_forward_33982977",
    },
    {
        "track": "宏观", "category": "宏观类",
        "title": "美伊冲突延续+油价续涨（9/1）：特朗普称将「狠狠打击伊朗」、霍尔木兹海峡一艘油轮报告被三枚射弹袭击（UKMTO）、布伦特91.15（+0.7%）WTI 87（+1%）逼近100美元风险（摩根大通：海峡每多中断一个月布伦特+7-8美元）；CME 9月加息概率升至65%、10Y美债4.76%创2025年1月以来新高、9/16美联储政策会议为关键时点——输入性通胀+加息预期双重压制全球成长资产",
        "summary": "美伊冲突延续油价续涨逼近100美元风险，9月加息概率升至65%压制成长股",
        "source": "Economic Times/CNA", "source_url": "https://m.economictimes.com/markets/commodities/news/oil-price-today-september-1-crude-oil-above-90-as-us-iran-attacks-jolt-hormuz-hopes-100-in-sight/amp_articleshow/133666056.cms",
    },
    {
        "track": "恒生科技", "category": "行业事件类",
        "title": "百度双重主要上市生效首日-2.6%（收93.7）「催化落空」第3次验证（8/27先例+9/1）；但CFO何海建称「很快迎来新增资金流入、可能下周就能看到效果」，参考券商观点预计10%-15%增量资金（最快9/7纳入港股通、MSCI调整后被动资金）——落空与增量预期并存，新增资金验证窗口为9/7前后",
        "summary": "百度双重上市首日催化落空-2.6%，但CFO称下周或迎10-15%增量资金",
        "source": "星岛头条", "source_url": "https://www.stheadline.com/stock-market/3610319/",
    },
]

# ---------- DeepSeek 情绪标注 ----------
with open('/Users/jieyang/.pi/agent/auth.json') as f:
    key = json.load(f)['deepseek']['key']

def deepseek_sentiment(title):
    prompt = f"""你是 A股/港股/美股基金组合投研助手。请对以下新闻做情绪标注，输出 JSON：
{{
  "sentiment": "正面|中性|负面",
  "score": 0-100 情绪分（>60 强情绪,40-60 中性,<40 弱情绪）,
  "strength": 0-100 事件强度（对持仓赛道的实际影响力度）,
  "direction": "利多|利空|中性",
  "volatility": "高|中|低",
  "comment": "一句话点评（20字内）"
}}
只输出 JSON，不要其他文字。

新闻：{title}"""
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
    # 提取 JSON
    start = content.find('{')
    end = content.rfind('}') + 1
    return json.loads(content[start:end])

# ---------- 标注 ----------
annotated = []
for n in close_news:
    try:
        s = deepseek_sentiment(n['title'])
        n.update(s)
        annotated.append(n)
        print(f"  [{n['track']}] {s['sentiment']} {s['score']}/{s['strength']} | {n['title'][:40]}")
    except Exception as e:
        print(f"  FAIL {n['title'][:30]}: {e}")
        n.update({'sentiment': '中性', 'score': 50, 'strength': 50, 'direction': '中性', 'volatility': '中', 'comment': '标注失败兜底'})
        annotated.append(n)
    time.sleep(1)

with open(os.path.join('/tmp', 'close_news_20260901.json'), 'w', encoding='utf-8') as f:
    json.dump(annotated, f, ensure_ascii=False, indent=1)
print(f'\n盘后标注完成 {len(annotated)} 条 -> /tmp/close_news_20260901.json')
