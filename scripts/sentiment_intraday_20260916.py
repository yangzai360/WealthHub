# -*- coding: utf-8 -*-
"""2026-09-16 盘中档新闻情绪标注（DeepSeek v4-flash，max_tokens=8000，批次 ≤7）"""
import json, urllib.request, ssl, time
ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE

NEWS = [
 # ---------------- 宏观 ----------------
 {"idx":1,"track":"宏观","title":"9/16 A股半日放量反弹：沪指+0.57%报3886.48、深成指+1.42%报13476.85、创业板指+2.35%报3324.36、科创50暴涨+4.50%；沪深两市半日成交1.17万亿元、较上日放量1082亿元；全市场超4200只个股上涨（占比76.17%）、涨停66只跌停4只；算力硬件/存储芯片/CPO/光通信/半导体材料集体爆发，银行、保险、煤炭、白酒、工程机械下跌","source_url":"https://www.cnr.cn/jingji/gundong/20260916/t20260916_527815264.shtml"},
 {"idx":2,"track":"宏观","title":"央行9/16开展1100亿元7天期逆回购（操作利率1.40%、全额满足一级交易商需求）+6000亿元隔夜逆回购，当日5970亿元隔夜逆回购到期、公开市场实现净投放1130亿元；建行金融市场部预计资金利率中枢较上周小幅上行（本周有9月税期走款+政府债净融资5780亿元）","source_url":"https://www.cnstock.com/commonDetail/790841"},
 {"idx":3,"track":"宏观","title":"FOMC(9/15-16)决议与点阵图北京时间9/17凌晨2:00公布、沃什新闻发布会2:30；CME显示加息25bp概率92%，目标区间预计由3.50-3.75%升至3.75-4.00%；9/16为决议前最后一个交易日，市场风险偏好回升但成交结构集中在科技成长","source_url":"https://m.21jingji.com/article/20260916/herald/89c91825789db8375012a9ff2019b0a2.html"},
 {"idx":4,"track":"宏观","title":"宁德时代9/16开盘跳水、跌幅扩大至5%以上、股价跌破300元报299.7元/股，港股同步跌超5%，A+H市值缩水至1.41万亿元；因宁德时代占创业板指权重约16%，创业板指盘中一度翻绿；为9/8（-3.65%）、9/15（A股-6%）后连续第三次大跌，自5月高点最大回撤超30%、市值蒸发7000亿元","source_url":"https://m.21jingji.com/article/20260916/herald/89c91825789db8375012a9ff2019b0a2.html"},
 {"idx":5,"track":"宏观","title":"国际油价回落：布伦特原油期货9/16早间跌幅扩大至1%报107.665美元/桶（前一日曾大涨2.9%至108.75美元）；油气/煤炭/石油股同步普跌，A股工程机械板块三一重工盘中逼近跌停——输入性通胀压力边际缓和","source_url":"https://m.21jingji.com/article/20260916/herald/89c91825789db8375012a9ff2019b0a2.html"},
 # ---------------- A股医药 ----------------
 {"idx":6,"track":"A股医药","title":"国家药监局披露：今年以来我国创新药出海步伐再提速，对外授权交易总额突破1200亿美元、同比增长36%，首付款规模超百亿美元，单笔平均交易金额、首付款金额与占比双双提升；今年以来已有59个创新药、51个创新医疗器械获批上市，其中13个为新机制新靶点的首创新药；我国首款依托人工智能辅助研发的原创创新药艾普司韦正式获批上市","source_url":"https://news.qq.com/rain/a/20260916A05OE200"},
 {"idx":7,"track":"A股医药","title":"创新药盈利拐点确认：2026年上半年国内创新药对外授权交易共81笔、总额约1100亿美元（已达2025年全年总额八成、创历史新高）；上半年A股和H股创新药上市公司整体营收同比增长21.3%、归母净利润同比大幅增长88.8%；兴业证券指出2027年预计有5款以上国产创新药在海外商业化，估值体系将从rNPV向EV/EBITDA、P/E迁移","source_url":"https://news.qq.com/rain/a/20260916A05OE200"},
 {"idx":8,"track":"A股医药","title":"9/16 A股创新药/CXO产业链集体反弹：CS创新药指数+0.83%（09:48），凯莱英涨超4%、康龙化成涨超3%、药明康德与泰格医药涨超2%、恒瑞医药与百济神州上涨；成都先导+12.30%、艾迪药业+9.70%、近岸蛋白+9.04%、佰仁医疗+8.03%、药康生物+4.76%、美迪西+4.54%、华大智造+5.44%、纳微科技+4.32%、博腾股份+4.05%——CXO/科研试剂/生命科学上游全面走强","source_url":"https://finance.sina.com.cn/jjxw/2026-09-16/doc-iniryzma2969324.shtml"},
 {"idx":9,"track":"A股医药","title":"科创板9/15召开2026年半年度生物制品及CXO行业集体业绩说明会，多家上市公司披露最新出海进展——从产品出海到服务能力出海，创新药产业链企业同步『走出去』，全球化路径持续深化；近日常州市市场监管局首创创新药械经营许可AI辅助审批模式，企业申报材料补正效率提高75%","source_url":"https://news.qq.com/rain/a/20260916A05OE200"},
 {"idx":10,"track":"A股医药","title":"一品红9/15在2026年半年报业绩说明会表示：公司在研痛风创新药AR882在痛风伴高尿酸血症参与者中表现出积极疗效及良好安全性，国内III期试验结果理想、达到预期目的，将积极与药监部门沟通争取早日完成上市申报","source_url":"https://news.qq.com/rain/a/20260916A05OE200"},
 {"idx":11,"track":"A股医药","title":"医药板块估值修复逻辑梳理：政策端医保国谈推出医保+商保双目录、高价创新药不必强制大幅降价、预申报机制缩短新药上市保障周期，控费转向鼓励创新；资金端板块估值处历史低位、半年报CXO与创新药与医疗器械业绩环比改善、医药ETF持续净流入；行情特征为震荡上行但内部分化极大，11月医保谈判最终结果是重要观察节点","source_url":"https://www.toutiao.com/article/7685891139110486567"},
 # ---------------- 大消费 ----------------
 {"idx":12,"track":"大消费","title":"9/16 A股大消费继续走弱：中证消费午间12170.01（-0.68%）、盘中最低12079.87（已破12000上方的12200防线）、最高12242.74；中证白酒指数当日下跌0.97%，白酒板块整体弱于大盘；银行、保险、煤炭、白酒为午盘下跌板块之一","source_url":"https://m.chinanews.com/wap/detail/cht/zw/jw688672.shtml"},
 {"idx":13,"track":"大消费","title":"9/16白酒板块内部剧烈分化：舍得酒业涨停，古井贡酒、金徽酒涨超5%，迎驾贡酒、老白干酒、口子窖涨幅居前；茅台批价26年飞天单瓶1730元持平、26年飞天原箱1750→1745元（-5元），23/22/21年飞天单瓶分别-20/-30/-30元；五粮液、国窖1573等次高端价格继续下探；中秋旺季终端备货意愿不足、百荣市场出现甩货、成都等核心城市经销商普遍拒绝压货","source_url":"https://www.163.com/dy/article/L6UMHSO80534A4SC.html"},
 {"idx":14,"track":"大消费","title":"国家统计局：1-8月全国烟酒类零售总额同比增长12.4%，行业整体消费保持较高增速；1-8月全国社会消费品零售总额累计327569亿元、同比增长1.1%，剔除汽车后零售额同比增速达2.7%；分结构看乡村消费增速持续跑赢城镇，餐饮收入复苏明显快于实物商品消费，服务消费展现更强韧性","source_url":"https://www.163.com/dy/article/L6UMHSO80534A4SC.html"},
 {"idx":15,"track":"大消费","title":"黄酒概念9/16异动拉升：金枫酒业直线涨停、会稽山实现2连板、古越龙山跟涨；华泰证券指出黄酒行业量价逻辑有望迎来重构——量上由江浙沪渗透提升走向全国拓展，价上龙头合力推进高端化；黄酒行业长期受制于区域局限与消费场景狭窄、估值处消费品板块底部区域","source_url":"https://www.163.com/dy/article/L6UMHSO80534A4SC.html"},
 {"idx":16,"track":"大消费","title":"华创证券研报：本周正式进入中秋国庆备货期，高端酒回款与发货节奏正常，飞天茅台渠道进度达8成、批价稳在1700元附近；五粮液批价微调至770-780元但回款顺畅、部分区域已达成全年目标；超高端茅台中秋飞天放量价格坚挺、系列酒动销超预期；100-300元大众价格带同比恢复增长，古井贡酒/今世缘/迎驾等区域龙头7-8月普遍增长、库存边际去化；判断行业有望从供给出清向供需再平衡转变","source_url":"https://www.163.com/dy/article/L6UMHSO80534A4SC.html"},
 # ---------------- 美股标普医药 ----------------
 {"idx":17,"track":"美股标普医药","title":"美股9/15生物科技股密集创52周新高：MediciNova +8%、Revvity +9.11%（Q2营收7.3亿美元、pro forma增长4%，全年营收指引上调至28.3-28.6亿美元）、10x Genomics +6%、Telix +9%（9/14 FDA批准Pixclara用于胶质瘤FET-PET显像）、Schrodinger +12%——创新与诊断工具链集体走强","source_url":"https://www.rttnews.com/3691329/biotech-stocks-at-52-week-highs-mnov-8-rvty-8-txg-6-tlx-9-sdgr-12.aspx"},
 {"idx":18,"track":"美股标普医药","title":"FDA 9/15动态：①缩短安进Imdelltra（tarlatamab-dlle）处方信息中初始监测时间——广泛期小细胞肺癌成人前两剂输注后观察期由22-24小时降至6-8小时，有望使更多患者在离家更近处接受治疗；②批准Aurobindo的倍氯米松HFA吸入气雾剂（Teva Qvar RediHaler仿制药，对应市场约3.01亿美元），为其首个定量吸入剂产品；③就迷幻药治疗用途召开公开听证会（已向3家企业发放优先券）","source_url":"https://www.indiapharmaoutlook.com/news/fda-today-drug-access-approvals-and-new-pathways-nwid-5822.html"},
 {"idx":19,"track":"美股标普医药","title":"FDA 9/15批准Microstructure Imaging的MICSI-PET（MR引导PET增强平台，具备自动化淀粉样蛋白Centiloid与tau定量能力），用于神经系统PET影像分析——阿尔茨海默病诊断工具链持续扩容","source_url":"https://neurologylive.com/fda-news"},
 {"idx":20,"track":"美股标普医药","title":"赛特瑞恩（Celltrion）9/15向FDA提交Zymfentra（Remsima SC）240mg高剂量方案IV期临床试验IND申请：拟在美国55个中心入组447例克罗恩病与溃疡性结肠炎患者，比较高剂量静脉英夫利西单抗与Zymfentra 240mg；同时推进类风湿关节炎适应症拓展","source_url":"https://www.thelec.net/news/articleView.html?idxno=13949"},
 # ---------------- 恒生科技 ----------------
 {"idx":21,"track":"恒生科技","title":"港股9/16午盘：恒生指数+0.12%报24697.35、恒生科技指数+0.87%报4328.85（收复4300关口、日内最低4259.27未破4250）、国企指数-0.05%报8201.16、红筹指数-0.38%；半导体/光通信/PCB概念股集体走高——剑桥科技涨逾13%、中际旭创涨超8%、华虹宏力涨逾7%、长飞光纤光缆涨6.7%；黄金股普涨（灵宝黄金/赤峰黄金涨逾6%）；工程机械龙头下挫（三一重工大跌近8%）、石油股/猪肉概念股/煤炭股普跌","source_url":"https://www.163.com/dy/article/L6URK9TU0519QIKK.html"},
 {"idx":22,"track":"恒生科技","title":"港股大型科技股9/16午盘普遍走弱：阿里巴巴-0.37%、腾讯控股-0.91%、京东集团-1.22%、小米集团-0.98%、网易-0.43%、美团-0.87%、哔哩哔哩-2.31%、快手+0.2%；恒生科技指数成分股涨幅居前为智谱、天数智芯、华虹宏力，跌幅居前为腾讯音乐-SW、哔哩哔哩-W、京东健康——AI算力硬件与互联网平台形成明显跷跷板","source_url":"https://finance.eastmoney.com/a/202609163875894423.html"},
 {"idx":23,"track":"恒生科技","title":"港股个股公告与产业动态：石药集团(01093.HK)公告SYS6010获国家药监局纳入突破性治疗品种名单（驱动基因阴性非鳞状非小细胞肺癌）；华润置地前8月累计合同销售金额约1491.0亿元、同比增长9.0%（8月185.0亿元、同比+40.2%）；中国神华前8月煤炭销售量4.09亿吨、同比增长0.8%；蓝思科技拟出资2亿元参设基金；天工国际拟投资河南佐能精工切入PCB钻针等精密加工工具市场","source_url":"https://www.163.com/dy/article/L6URK9TU0519QIKK.html"},
 # ---------------- 其他/宽基 ----------------
 {"idx":24,"track":"其他/宽基","title":"9/16 A股算力硬件产业链全面爆发：存储芯片、CPO、光通信概念股多股涨停——澳弘电子4连板、东田微涨超14%创历史新高、光迅科技涨停、华脉科技与永鼎股份涨停；半导体材料板块走强，有研硅与晶升股份20cm涨停、中晶科技2连板、晶丰明源涨超19%；通信设备股长芯博创涨超14%、仕佳光子涨超10%","source_url":"https://m.chinanews.com/wap/detail/cht/zw/jw688672.shtml"},
 {"idx":25,"track":"其他/宽基","title":"9/16 A股工程机械板块大幅调整：三一重工盘中逼近跌停，山推股份、柳工、恒立液压随之下跌；港股三一重工大跌近8%领衔下跌；摩托车、发电设备、海运、油气、航空、保险板块同步下跌——资金从周期与价值向科技成长切换","source_url":"https://m.chinanews.com/wap/detail/cht/zw/10697382.shtml"},
 {"idx":26,"track":"其他/宽基","title":"9/16 A股贵金属集体拉升：盛达资源涨超8%、四川黄金涨超7%、赤峰黄金涨超5%，晓程科技、招金黄金等多股大涨；港股黄金股同步普涨（灵宝黄金、赤峰黄金涨逾6%，山东黄金涨超4%）；浙商证券称政策托底叠加基本面无忧保证『系统性慢牛』框架不变，但海外利率高位、成交降温与拥挤度消化限制估值快速扩张空间，四季度或为区间震荡与行业轮动","source_url":"https://m.chinanews.com/wap/detail/cht/zw/jw688672.shtml"},
]

with open('/Users/jieyang/.pi/agent/auth.json') as f:
    key = json.load(f)['deepseek']['key']

def label(batch):
    lines = "\n".join([f"{n['idx']}. [{n['track']}] {n['title']}" for n in batch])
    prompt = f"""你是A股/港股/美股基金投研分析师。对下列每条新闻输出情绪标注，严格输出 JSON 数组，不要任何解释文字。
每条格式：{{"idx":序号,"track":"赛道","sentiment":"正面|中性|负面","strength":0-100情绪强度,"confidence":0-100置信度,"direction":"利多|利空|中性","volatility":"高|中|低","brief":"20字内核心影响"}}
赛道取值只能是：宏观 / A股医药 / 大消费 / 美股标普医药 / 恒生科技 / 其他宽基。
strength 表示情绪强度（重大突发事件 80-95，明确行业事件 60-80，一般消息 40-60）；confidence 表示该事件对市场影响的确定性（数据明确 75-90，观点类 50-70）。
新闻列表：
{lines}"""
    data = {"model": "deepseek-v4-flash", "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 8000, "temperature": 0.3}
    req = urllib.request.Request("https://api.deepseek.com/chat/completions",
                                 data=json.dumps(data).encode(),
                                 headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=180, context=ctx) as resp:
        r = json.load(resp)
    c = r['choices'][0]['message']['content']
    if not c:
        raise RuntimeError("empty content")
    c = c.strip()
    if c.startswith("```"):
        c = c.split("```")[1]
        if c.startswith("json"): c = c[4:]
    return json.loads(c.strip())

results = []
B = 7
for i in range(0, len(NEWS), B):
    batch = NEWS[i:i+B]
    for attempt in range(3):
        try:
            r = label(batch)
            results.extend(r); print(f"batch {i//B+1} OK ({len(r)})"); break
        except Exception as e:
            print(f"batch {i//B+1} attempt{attempt+1} err: {e}")
            time.sleep(3)

by_idx = {r['idx']: r for r in results}
# 赛道名归一（其他宽基 -> 其他/宽基）
final = []
for n in NEWS:
    r = by_idx.get(n['idx'], {})
    tr = n['track']
    final.append({**n, "track": tr,
                  "sentiment": r.get('sentiment', '中性'), "strength": r.get('strength', 50),
                  "confidence": r.get('confidence', 50), "direction": r.get('direction', '中性'),
                  "volatility": r.get('volatility', '中'), "brief": r.get('brief', '')})
json.dump(final, open('/tmp/news_intraday_20260916.json', 'w'), ensure_ascii=False, indent=1)
pos = len([x for x in final if x['direction'] == '利多']); neg = len([x for x in final if x['direction'] == '利空'])
neu = len([x for x in final if x['direction'] == '中性'])
print("total", len(final), "利多", pos, "利空", neg, "中性", neu,
      "均值强度", round(sum(x['strength'] for x in final) / len(final), 1))
for x in final:
    print(x['idx'], x['track'], x['sentiment'], x['strength'], x['direction'], x['brief'])
