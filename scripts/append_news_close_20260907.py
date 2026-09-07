# -*- coding: utf-8 -*-
"""2026-09-07 盘后档: 追加 8 条盘后新闻(窗口 14:00-20:00) + DeepSeek 情绪标注
标题截断 <=200 规避空 content(§3.64); DeepSeek 1-based i 与 enumerate(news,1) 对齐(§3.62)"""
import json, os, re, urllib.request

BASE = '/Users/jieyang/Documents/WealthHub'
NEWS_FILE = os.path.join(BASE, 'data/processed/news/news-2026-09-07.json')
SENT_FILE = os.path.join(BASE, 'data/processed/news/sentiment-2026-09-07.json')

POST_NEWS = [
    {
        "title": "A股9/7收评: 沪指+0.07%报3,932.70、深成指+1.91%报13,774.92、创业板+3.41%报3,398.68(午后自3,409小幅回落)——算力硬件(CPO/PCB/存储)涨停潮(泰金新能/迅捷兴20CM/中际旭创成交241亿) vs 银行(注资利好出尽续跌)/保险/煤炭/贵金属领跌; 农业/零售活跃; 超3,100股上涨、成交1.95万亿缩量846亿; 科创综指+1.90%",
        "track": "宏观", "category": "宏观类",
        "source_url": "https://www.stcn.com/article/detail/4174799.html",
        "summary": "A股科技独强创业板+3.41%, 银行保险煤炭领跌, 结构分化延续",
    },
    {
        "title": "港股9/7收评: 恒指-0.93%报25,413.12、恒生科技-0.92%报4,527.71守住4,500(盘中最低4,509.38未破)——季检+港股通双催化生效日高开低走第2日: 百度入通首日-4.69%收91.40(盘中-5.74%后收窄)/美团-2%/腾讯-0.72%/小米-3.31% vs 群核科技+30%/中际旭创+19.58%/华虹宏力+4.92%; 大金融全线走弱(农行建行招行-2%+); 南向净买入12.76亿港元转正(周五净卖超100亿后)",
        "track": "恒生科技", "category": "行业事件类",
        "source_url": "https://news.qq.com/rain/a/20260907A0B7FT00",
        "summary": "恒科守住4,500减仓预案取消, 双催化利好兑现但南向转正托底",
    },
    {
        "title": "2026国谈第三日(9/7): 替尼类抗肿瘤新药集群登场(诺诚健华佐来曲替尼/首药控股康特替尼/江苏威凯尔安瑞曲替尼近20家企业)+下午科伦博泰/百济等ADC赛道'目录内扩容+目录外新增'双线博弈; 双目录梯度支付体系常态化运行; 59个1类创新药完成预沟通(价格锚点前置, 定价逻辑从现场博弈转向预期管理); 新版目录11月公布",
        "track": "A股医药", "category": "政策类",
        "source_url": "https://www.cls.cn/detail/2475899",
        "summary": "国谈第三日肿瘤药主场, 双目录常态化, 创新药定价预期锚定",
    },
    {
        "title": "A股医药9/7收盘: 医药生物-0.02%报7,743.59基本平盘、创新药板块+0.35%微红 vs 持仓医疗ETF-0.59%/医药ETF广发-0.31%; 医药生物主力净流出4.11亿/创新药主力-3.3亿; 药明康德-0.38%收153.25/恒瑞+0.52%/百济-2.2%/百利天恒-2%——国谈第3日定价仍未启动('利多未定价'第8日), 科技虹吸+加息贴现率压制延续",
        "track": "A股医药", "category": "行业事件类",
        "source_url": "https://gu.qq.com/resources/shy/news/detail-v2/index.html?t=1#/index?_tentrees_trans=0&id=SN20260907075547984d3172",
        "summary": "A股医药平盘国谈未定价, ETF弱于大盘, 主力净流出",
    },
    {
        "title": "大消费9/7收盘: 中证消费-0.27%报12,775.54(盘中-0.50%尾盘收复, 9/4 +2.65%历史样本后回调第1日)——白酒概念+0.18%(金徽酒+1.69%/均瑶健康+5%)内部分化 vs 茅台-0.11%报1,304/五粮液-1.18%: 高端弱区域性酒强; 农业(亚盛集团3连板/敦煌种业涨停 厄尔尼诺)与零售(中百/中央商场 60万亿政策)独立走强; 猪价旺季不旺延续; 富国消费主题主动基-0.53%弱于指数(白酒权重)",
        "track": "大消费", "category": "行业事件类",
        "source_url": "https://www.163.com/dy/article/L67V22R90534A4SC.html",
        "summary": "中证消费回调第1日守12,700上方, 农业零售强白酒弱内部分化",
    },
    {
        "title": "小米18 Fold发布(9/7晚7点): '中折叠'手机10,999元起(9/10开售)+首发玄戒O3自研AI旗舰SoC(安兔兔561万/率先量产长鑫LPDDR6 113.8GB/s)+小米汽车澎程正式上市——小米港股当日-3.31%(发布会前了结)但南向逆势净买入13.84亿港元居首; 华为Mate XT 2同日发布(19,999元起)",
        "track": "恒生科技", "category": "行业事件类",
        "source_url": "https://finance.sina.cn/2026-09-07/detail-iniqzhfv0187447.d.html",
        "summary": "小米折叠屏+玄戒O3自研芯片落地, 定价10999起, 南向加仓",
    },
    {
        "title": "美股9/7劳动节休市+本周关键事件前瞻: 9/10美国8月PPI(20:30)+苹果折叠屏iPhone发布会(北京9/10凌晨1点)+甲骨文/Adobe财报+台积电8月营收; 9/11美国8月CPI(贝莱德: 加息真正门槛); 9/15-16 FOMC——美股9/8(周二)重开将先消化非农超预期(2Y 4.416% 15个月高/10Y 4.801%/加息概率58.4%)",
        "track": "宏观", "category": "宏观类",
        "source_url": "https://www.sfccn.com/2026/9-7/2MMDE0MDVfMjIzMzA2Mg.html",
        "summary": "本周PPI/CPI/FOMC为外部总开关, 美股周二重开消化非农",
    },
    {
        "title": "54股新纳入港股通9/7生效(深交所/上交所季检): 当日仅12涨42跌分化——AI算力/机器人/创新药(18A生物科技十余只)密集入通(群核科技+30%居首); 高盛上调全球光模块2026-28出货量预测+21%/+31%/+31%(1.6T及以上+29%/+61%/+50%)+华为韬定律论文(麒麟2026晶体管密度+55%)驱动A股港股算力硬件共振; 机构提示入通拥挤风险",
        "track": "恒生科技", "category": "行业事件类",
        "source_url": "https://news.qq.com/rain/a/20260907A0BGPR00",
        "summary": "港股通大扩容生效日分化, 光模块景气上调, 拥挤风险提示",
    },
]

with open(NEWS_FILE, encoding='utf-8') as f:
    news = json.load(f)
with open(SENT_FILE, encoding='utf-8') as f:
    sent = json.load(f)

existing_titles = set(x['title'][:50] for x in news)
added = []
for n in POST_NEWS:
    if n['title'][:50] not in existing_titles:
        news.append({**n, 'time': '2026-09-07 19:30'})
        added.append(n)
with open(NEWS_FILE, 'w', encoding='utf-8') as f:
    json.dump(news, f, ensure_ascii=False, indent=1)
print(f'news-2026-09-07.json 追加 {len(added)} 条, 共 {len(news)} 条')

# ---------- DeepSeek 情绪标注 (标题截断 200) ----------
if added:
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
    m = re.search(r'\[[\s\S]*\]', content)
    if not m:
        raise RuntimeError('未找到 JSON 数组: ' + content[:500])
    annos = json.loads(m.group(0))
    print('标注条数:', len(annos))
    for a in annos:
        n = added[a['i'] - 1]
        sent.append({
            'date': '2026-09-07',
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
    print(f'sentiment-2026-09-07.json 共 {len(sent)} 条')
    for s in sent[-len(added):]:
        print(f"  [{s['track']}] {s['sentiment']} {s['score']}/{s['strength']} {s['direction']} | {s['title'][:40]}")
