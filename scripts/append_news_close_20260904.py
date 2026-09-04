# -*- coding: utf-8 -*-
"""2026-09-04 盘后档: 追加 8 条盘后新闻(窗口 14:00-20:00) + DeepSeek 情绪标注"""
import json, os, urllib.request

BASE = '/Users/jieyang/Documents/WealthHub'
NEWS_FILE = os.path.join(BASE, 'data/processed/news/news-2026-09-04.json')
SENT_FILE = os.path.join(BASE, 'data/processed/news/sentiment-2026-09-04.json')

# 8 条盘后新闻 (title, track, category, source_url, summary)
POST_NEWS = [
    {
        "title": "A股9/4收评(冲高回落): 沪指-0.30%报3,930.12、深成指-0.79%报13,516.97、创业板-0.78%报3,286.55——隔夜美股大涨/沃勒转鸽缓冲下高开冲高(最高3,980.20)后午后集体跳水翻绿; 成交2.03万亿放量2,718亿; 农业猪肉涨停潮(敦煌种业6天3板/亚盛2连板/新希望/牧原+9%)、AI应用(龙版传媒5连板)、白酒食品涨幅居前 vs 半导体重灾(HBM/PCB/CPO/覆铜板跌3-4%、华虹宏力/国科微下挫)、煤炭(郑州煤电跌停)",
        "track": "宏观", "category": "宏观类",
        "source_url": "https://www.stcn.com/article/detail/4172468.html",
        "summary": "A股冲高回落三大指数收跌, 农业猪肉/AI应用/白酒强, 半导体重灾",
    },
    {
        "title": "港股9/4收评: 恒指+1.74%报25,650.87、恒生科技+2.27%报4,569.80(收复4,500站稳)——科网普涨(同程/联想+6%/美团+5%/百度+4.81%报95.90/小米网易京东+3%/阿里腾讯+2%)、大金融全线走强(国有五大行本周创新高/内险+3%左右/中资券商+2%); 猪肉股牧原+9%; AI应用MINIMAX一度+11%; 全日成交2,768.57亿港元——但南向资金逢高撤离净卖出超100亿港元",
        "track": "恒生科技", "category": "行业事件类",
        "source_url": "https://news.qq.com/rain/a/20260904A0B7YQ00",
        "summary": "港股强势反攻恒科收复4,500站稳, 但南向逢高净卖出超100亿",
    },
    {
        "title": "恒生指数系列季度调整9/4收市正式生效(9/7起新成分股运作): 恒指新纳华虹宏力/潍柴动力, 恒生科技新纳天数智芯剔除同程旅行, 恒生综合指数由534只增至580只半导体/AI大幅扩容; 高盛测算将产生超72亿美元双向被动资金流, 科技硬件及半导体预计流入约8.7亿美元; 西部证券看国产AI产业链或存系统性重估",
        "track": "恒生科技", "category": "行业事件类",
        "source_url": "https://new.qq.com/rain/a/20260904A0CVH200?refer=cp_1009",
        "summary": "恒指季调收市生效, 高盛72亿美元被动资金流9/7落地",
    },
    {
        "title": "央行9/4晚间公告: 将于9/7开展5000亿元3个月期买断式逆回购(固定数量/利率招标/多重价位中标)——9月有5000亿元到期故为等量续作(零投放零回笼), A股午后跳水后晚间出手稳定流动性预期; 东方金诚: 政策向稳增长方向进一步发力, 不排除后期实施降准; 8月公开市场国债买卖净投放500亿",
        "track": "宏观", "category": "宏观类",
        "source_url": "https://www.toutiao.com/article/7681640743928300073/",
        "summary": "央行5000亿买断式逆回购等量续作, 流动性维稳信号",
    },
    {
        "title": "中证主要消费9/4收盘+2.65%报12,809.57站上12,800(冲高回落但仍收强): 白酒Ⅱ+2.64%主力净流入9.87亿(茅台+2.40%报1,330.00/汾酒+4.79%/泸州老窖+5.16%/古井+4.56%/洋河+2.17%/五粮液+1.84%)黄酒涨停潮+猪产业(新希望涨停/温氏+6.15%)——『超跌反弹+估值修复+中秋动销』左侧布局第2日; 申万宏源: 白酒报表加速出清股价底部特征已验证、茅台价格Q1已筑底迎周期拐点、优质白酒公司已处于战略配置期",
        "track": "大消费", "category": "行业事件类",
        "source_url": "https://news.qq.com/rain/a/20260904A05JBP00",
        "summary": "中证消费收12,809.57站上12,800, 白酒/猪肉双驱动, 机构看拐点",
    },
    {
        "title": "A股医药9/4收跌: 医药生物板块-0.30%/医疗服务-1.51%——药明康德除息日(XD)-1.47%收153.83(可转债转股新增682.71万股H股、主力净流出6,883.55万、近5日主力净流入4.91亿)、博济医药-1.43%; A股医药冲高回落收跌 vs 港股生物科技持续走强(恒生生物科技+1.86%三日) A/H背离第5日以A股走弱收盘确认",
        "track": "A股医药", "category": "行业事件类",
        "source_url": "https://www.163.com/dy/article/L60LFHE50519QIKK.html",
        "summary": "A股医药收跌药明除息领跌, 港股医药强A/H背离第5日",
    },
    {
        "title": "国家医保局『十五五』发布会(9/4国新办): 2018年以来累计新增纳入949种药其中199种创新药; 将继续每年调整基本医保药品目录, 将更多肿瘤/慢性病/罕见病/儿童疾病等创新药纳入报销; 优化商保创新药目录——对超出基本医保范围/创新程度高/临床价值大/患者获益显著的创新药推荐商业医保先行支付; 持续扩大集采覆盖面但坚持『新药不集采, 集采非新药』; 2026医保国谈9/5明日启动为期4-5天",
        "track": "A股医药", "category": "政策类",
        "source_url": "https://news.qq.com/rain/a/20260904A05UCT00",
        "summary": "医保局每年调目录纳入创新药+商保目录并行, 国谈明日启动",
    },
    {
        "title": "CRO/创新药中报景气拐点确认(东吴/中邮/安永): 365家A/H医药上市公司2026H1营收+5.31%/归母净利+22.89%; A股58家创新药样本H1收入/净利+21.3%/+88.8%(盈利拐点+BD增厚); 中邮: 临床CRO需求供给双改善景气拐点渐明(美迪西扭亏新签订单12.33亿+104.74%); 渤海: CXO订单修复有望走出底部、龙头企业上调全年指引——机构共识创新药及产业链仍是医药板块产业趋势最明确方向",
        "track": "A股医药", "category": "业绩类",
        "source_url": "https://www.toutiao.com/article/7681517596956459583/",
        "summary": "CRO/创新药H1业绩兑现景气拐点, 机构集中看好",
    },
]

with open(NEWS_FILE, encoding='utf-8') as f:
    news = json.load(f)
with open(SENT_FILE, encoding='utf-8') as f:
    sent = json.load(f)

existing_titles = set(x['title'][:50] for x in news)
# 追加到 news 文件
added = []
for n in POST_NEWS:
    if n['title'][:50] not in existing_titles:
        news.append({**n, 'time': '2026-09-04 19:00'})
        added.append(n)
with open(NEWS_FILE, 'w', encoding='utf-8') as f:
    json.dump(news, f, ensure_ascii=False, indent=1)
print(f'news-2026-09-04.json 追加 {len(added)} 条, 共 {len(news)} 条')

# ---------- DeepSeek 情绪标注 ----------
with open('/Users/jieyang/.pi/agent/auth.json') as f:
    key = json.load(f)['deepseek']['key']

prompt = f"""你是投资新闻情绪分析器。请对以下 {len(added)} 条财经新闻逐条输出情绪标注。

输出要求: 严格输出 JSON 数组, 每元素对应一条新闻(1-based 顺序), 字段:
{{"i": 序号, "sentiment": "正面|中性|负面", "score": 情绪分0-100(正负强度), "strength": 影响强度0-100(对市场影响大小), "direction": "利多|利空|中性", "volatility": "高|中|低", "comment": "一句话理由"}}

新闻列表:
"""
for idx, n in enumerate(added, 1):
    prompt += f"\n[{idx}] [{n['track']}] {n['title'][:200]}"

data = {
    "model": "deepseek-v4-flash",
    "messages": [{"role": "user", "content": prompt}],
    "max_tokens": 8192,
    "temperature": 0.2,
}
req = urllib.request.Request("https://api.deepseek.com/chat/completions",
    data=json.dumps(data).encode(),
    headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
with urllib.request.urlopen(req, timeout=180) as resp:
    result = json.load(resp)
content = result['choices'][0]['message']['content']
print('DeepSeek 返回长度:', len(content))

# 提取 JSON
import re
m = re.search(r'\[[\s\S]*\]', content)
if not m:
    raise RuntimeError('未找到 JSON 数组: ' + content[:500])
annos = json.loads(m.group(0))
print('标注条数:', len(annos))

# 追加标注到 sentiment(1-based 对齐)
for a in annos:
    n = added[a['i'] - 1]
    sent.append({
        'date': '2026-09-04',
        'track': n['track'],
        'title': n['title'],
        'sentiment': a['sentiment'],
        'score': a['score'],
        'strength': a['strength'],
        'direction': a['direction'],
        'volatility': a['volatility'],
        'comment': a['comment'],
    })
with open(SENT_FILE, 'w', encoding='utf-8') as f:
    json.dump(sent, f, ensure_ascii=False, indent=1)
print(f'sentiment-2026-09-04.json 共 {len(sent)} 条')
for s in sent[-len(added):]:
    print(f"  [{s['track']}] {s['sentiment']} {s['score']}/{s['strength']} {s['direction']} | {s['title'][:36]}")
