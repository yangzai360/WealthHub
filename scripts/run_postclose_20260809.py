# -*- coding: utf-8 -*-
"""
WealthHub 盘后复盘 2026-08-09（周日，非交易日）
链路步骤: 新闻构建 -> DeepSeek 情绪标注 -> 事件库落盘 -> 报告材料输出
"""
import json, os, re, urllib.request, datetime

BASE = "/Users/jieyang/Documents/WealthHub"
NEWS_DIR = os.path.join(BASE, "data/processed/news")
EVENTS_DIR = os.path.join(BASE, "data/processed/events")
TODAY = "2026-08-09"

# ---------- 1. 新闻构建（8/8 18:00 - 8/9 20:00 窗口，去重过滤后 9 条） ----------
news_items = [
    {
        "id": "N20260809-001", "date": TODAY, "track": "恒生科技",
        "category": "宏观类",
        "title": "环球下周看点：美股创新高后迎关键考验 7月通胀数据或决定美联储9月政策走向",
        "summary": "财联社：本周美股三大指数均涨，标普+3.58%、道指+2.96%、纳指+5.19%，标普与道指创历史新高。7月非农意外减少23万降低加息担忧。7月CPI将于下周三(8/12)公布，FactSet预计同比+3.4%(略低于6月3.5%)；LSEG数据显示美联储9月加息概率约44%，若通胀数据疲弱该概率将进一步下降。下周五零售销售与密歇根消费者信心指数。",
        "source": "WebSearch/财联社",
        "source_url": "https://www.163.com/dy/article/L3S7MPQ605198CJN.html",
    },
    {
        "id": "N20260809-002", "date": TODAY, "track": "恒生科技",
        "category": "行业事件类",
        "title": "中信证券：利空出尽或支撑港股行情延续 维持红利防守+成长弹性杠铃策略",
        "summary": "中信证券研报：近一个月恒生综指业绩预期反转，中报超预期推动全年盈利上修；恒科指数受乘用车盈利分化及头部互联网资本开支扩张压制，预期修复相对滞后。医疗保健(CXO与制药龙头驱动)、金融、公用事业景气上行；消费、地产及资讯科技预期遭下调。配置建议杠铃策略：防守端高股息低β类债资产，进攻端互联网巨头、机器人与生物科技、创新药及工业金属。",
        "source": "WebSearch/界面新闻",
        "source_url": "https://www.163.com/dy/article/L3TLRBL10534A4SC.html",
    },
    {
        "id": "N20260809-003", "date": TODAY, "track": "恒生科技",
        "category": "宏观类",
        "title": "方正证券：超跌反弹进入攻坚期 关注恒生科技与医药核心龙头",
        "summary": "方正证券研报：市场超跌反弹进入攻坚期，科技与景气赛道分化演绎。双创从底部反弹幅度约10%。AI叙事在美股CSP财报后出现变化，建议关注海外算力拥挤度不高的核心标的、国产算力半导体设备材料、相对低位的AI应用及恒生科技；关注HALO资产布局(美联储加息预期弱化)；以及景气度较好、拥挤度不高、负面压制缓解的医药核心龙头。",
        "source": "WebSearch/格隆汇",
        "source_url": "https://caifuhao.eastmoney.com/news/20260809170645020511330",
    },
    {
        "id": "N20260809-004", "date": TODAY, "track": "A股医药",
        "category": "行业事件类",
        "title": "创新药、CDMO赛道获机构扎堆调研 百济神州207家机构居首 上调全年指引",
        "summary": "科创板日报：本周(8/3-8/9)57家A股公司获机构调研，百济神州获207家机构调研居首，上调2026全年营收指引至449-462亿元(原436-452亿)，百悦泽在美国市场领先地位及全球扩张驱动；泽璟制药97家、九洲药业77家。ESMO 2026(10月)将披露CEA ADC非小细胞肺癌早期数据。泽璟制药ZG006为全球首个DLL3/DLL3/CD3三靶点TCE。",
        "source": "WebSearch/科创板日报",
        "source_url": "https://new.qq.com/rain/a/20260809A05SPX00?refer=cp_1009",
    },
    {
        "id": "N20260809-005", "date": TODAY, "track": "A股医药",
        "category": "行业事件类",
        "title": "BD交易破千亿美元 中国创新药上半年License-out达1100亿美元 全球Top10占8席",
        "summary": "华夏时报/沙利文峰会：2026上半年中国创新药License-out潜在交易总额达1100亿美元(2025全年八成)，首付款合计达2025全年七成；全球Top10 BD交易中国独占8席。恒瑞×BMS全球战略合作潜在总额152亿美元、石药×AZ以12亿美元首付款185亿美元潜在总额刷新纪录、信达×辉瑞105亿美元。2025年中国创新药BD总额1356.55亿美元首次超越美国成为全球第一大对外授权市场。",
        "source": "WebSearch/华夏时报",
        "source_url": "https://www.toutiao.com/article/7671892563485262345/",
    },
    {
        "id": "N20260809-006", "date": TODAY, "track": "A股医药",
        "category": "行业事件类",
        "title": "药捷安康首款创新药获批 股价已跌破发行价 港股通资金持续减持",
        "summary": "红星资本局：药捷安康(2617.HK)自主研发新药捷恩泰(替恩戈替尼)获NMPA附条件批准上市，用于FGFR2融合/重排的晚期胆管癌。2025年9月股价曾从90港元暴涨至679.5港元历史高点，此后下行；2026年6月限售股解禁暴跌近60%；截至8/7收盘跌2.52%报11.24港元，已跌破13.15港元发行价。2023-2025年净亏损3.43/2.75/2.96亿元，无商业化收入。",
        "source": "WebSearch/红星新闻",
        "source_url": "https://new.qq.com/rain/a/20260809A05UT200?refer=cp_1009",
    },
    {
        "id": "N20260809-007", "date": TODAY, "track": "美股标普医药",
        "category": "行业事件类",
        "title": "美股生物医药周报：Moderna首个mRNA流感疫苗/Takeda食欲素激动剂/诺华Pluvicto组合获FDA批准",
        "summary": "Nasdaq Weekly Buzz：本周FDA/欧盟多项批准——Moderna mFLUSIVA成为首个mRNA季节性流感疫苗(50岁+成人)；Takeda ORZEYFUL为首个食欲素受体2激动剂(发作性睡病1型)；诺华Pluvicto联合ARPI获FDA批准(mHSPC，风险降低28-33%，患者人群近乎翻倍)；Sanofi MenQuadfi获欧盟批准；Replimune TUDRIQEV获FDA批准。XLV 8/7收165.68(+0.75%)，本周累计约+2.12%(162.24→165.68)。",
        "source": "WebSearch/Nasdaq",
        "source_url": "https://www.nasdaq.com/articles/weekly-buzz-mrna-nvs-sny-gain-approvals-ebs-lsta-cut-jobs-tars-bivi-drive-deals-data",
    },
    {
        "id": "N20260809-008", "date": TODAY, "track": "大消费",
        "category": "行业事件类",
        "title": "酒价内参8/9：11大白酒单品六涨五跌 整体回暖 普五八代+7元至798逼近800关口",
        "summary": "新浪财经酒价内参：8/9 11大白酒单品六涨五跌，多数品牌止跌回暖。精品茅台+8元至2410元创近一个月新高；普五八代+7元至798元创月内次高、逼近800元重要关口；五粮液1618+1元；青花汾20+9元、青花郎+10元；飞天茅台小幅回落2元报1773元。11大单品整包总价9933元较昨日+25元，创5月底以来价格新高，白酒市场整体回暖行情继续推进。",
        "source": "WebSearch/新浪财经",
        "source_url": "https://finance.sina.com.cn/7x24/2026-08-09/doc-inimsnkv3650632.shtml",
    },
    {
        "id": "N20260809-009", "date": TODAY, "track": "大消费",
        "category": "行业事件类",
        "title": "五粮液批价8/8郑州百荣报770元较8/4涨40元 国金证券：白酒产业景气处于筑底窗口",
        "summary": "国际金融报：郑州百荣(全国最大酒水批发市场)8/8第八代五粮液批价770元/瓶，较8/4的730元上涨40元，整箱(6瓶)上涨240元；终端零售价同步上调。国金证券研报：白酒产业景气度处于筑底窗口，淡季至今主流标品价盘平稳，飞天茅台价盘可圈可点，酒企对价盘主动管控利于渠道预期梳理，考虑低基数效应下半年绝大多数酒企报表企稳。茅台自营店一个月内三次调价，26年飞天报价约1850元。",
        "source": "WebSearch/国际金融报",
        "source_url": "https://www.163.com/dy/article/L3RPBBIP0514R9P4.html",
    },
]

# ---------- 2. 落盘新闻库 ----------
os.makedirs(NEWS_DIR, exist_ok=True)
news_path = os.path.join(NEWS_DIR, f"news-{TODAY}.json")
with open(news_path, "w", encoding="utf-8") as f:
    json.dump(news_items, f, ensure_ascii=False, indent=1)
print(f"[OK] 新闻库已写入 {news_path} ({len(news_items)} 条)")

# ---------- 3. DeepSeek 情绪标注 ----------
def deepseek_analyze(items):
    """批量情绪标注: 每条输出 sentiment/strength/impact_direction/expected_volatility/reason"""
    with open("/Users/jieyang/.pi/agent/auth.json") as f:
        key = json.load(f)["deepseek"]["key"]
    prompt = f"""你是投资分析情绪标注引擎。对以下 {len(items)} 条财经新闻逐条标注：
输出 JSON 数组，每元素: {{"id":..., "sentiment": "正面|中性|负面", "strength": 0-100, "impact_direction": "利多|中性|利空", "expected_volatility": "高|中|低", "reason": "一句话理由"}}
强度: 对持仓赛道(大消费/A股医药/美股标普医药/恒生科技)影响越直接越大分越高。只输出 JSON。

新闻列表:
{json.dumps([{"id": i["id"], "track": i["track"], "category": i["category"], "title": i["title"], "summary": i["summary"][:200]} for i in items], ensure_ascii=False, indent=1)}"""
    data = {
        "model": "deepseek-v4-flash",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 8000,
        "temperature": 0.3,
    }
    req = urllib.request.Request(
        "https://api.deepseek.com/chat/completions",
        data=json.dumps(data).encode(),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=180) as resp:
        result = json.load(resp)
    content = result["choices"][0]["message"]["content"]
    # 提取 JSON 数组
    m = re.search(r"\[.*\]", content, re.S)
    if not m:
        raise RuntimeError(f"DeepSeek 未返回 JSON: {content[:300]}")
    return json.loads(m.group(0))

try:
    senti = deepseek_analyze(news_items)
    print(f"[OK] DeepSeek 情绪标注完成 ({len(senti)} 条)")
except Exception as e:
    print(f"[WARN] DeepSeek 标注失败({e})，使用兜底中性标注")
    senti = [{"id": i["id"], "sentiment": "中性", "strength": 50,
              "impact_direction": "中性", "expected_volatility": "中",
              "reason": "DeepSeek 标注失败兜底"} for i in news_items]

senti_map = {s["id"]: s for s in senti}

# ---------- 4. 构建事件库（含历史匹配占位，回填待 8/10） ----------
os.makedirs(EVENTS_DIR, exist_ok=True)
events = []
for item in news_items:
    s = senti_map.get(item["id"], {})
    events.append({
        **item,
        "sentiment": s.get("sentiment", "中性"),
        "strength": s.get("strength", 50),
        "impact_direction": s.get("impact_direction", "中性"),
        "expected_volatility": s.get("expected_volatility", "中"),
        "reason": s.get("reason", ""),
        "reference": {
            "ret_3d": None, "ret_5d": None, "ret_10d": None,
            "max_vol": None, "confidence": None,
            "actual_ret_1d": None, "actual_date": None,
        },
    })
events_path = os.path.join(EVENTS_DIR, f"events-{TODAY}.json")
with open(events_path, "w", encoding="utf-8") as f:
    json.dump(events, f, ensure_ascii=False, indent=1)
print(f"[OK] 事件库已写入 {events_path} ({len(events)} 条)")

# ---------- 5. 输出报告用摘要 ----------
print("\n===== 情绪标注摘要 =====")
for e in events:
    print(f"{e['id']} [{e['track']}] {e['sentiment']}/{e['strength']} {e['impact_direction']} 波动{e['expected_volatility']} | {e['title'][:40]}")
