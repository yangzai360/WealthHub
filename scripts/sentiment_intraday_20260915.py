# -*- coding: utf-8 -*-
"""2026-09-15 盘中档新闻情绪标注（DeepSeek v4-flash，max_tokens=8000）"""
import json, urllib.request, ssl, time
ctx = ssl.create_default_context(); ctx.check_hostname=False; ctx.verify_mode=ssl.CERT_NONE

NEWS = [
 # 宏观
 {"idx":1,"track":"宏观","title":"国新办10:00发布8月经济数据：规模以上工业增加值同比+5.2%(比上月加快0.7pct、环比+0.54%)、装备制造业+12.1%、高技术制造业+16.7%、新动能对工业增长贡献超六成；但8月社会消费品零售总额39,824亿元同比仅+0.4%(环比-0.13%)、1-8月累计32.76万亿同比+1.1%，显著低于机构预期区间(+0.3%~+3.0%、均值+0.8%)；1-8月固定资产投资29.31万亿同比-7.2%(扣除房地产-4.2%)；统计局定调『三稳两快』","source_url":"https://www.stats.gov.cn/sj/zxfbhjd/202609/t20260915_1965307.html"},
 {"idx":2,"track":"宏观","title":"工信部、国家发改委联合印发《电子信息制造业发展『十五五』规划》：推动集成电路全链条攻关，发展高性能处理器、高密度存储器、高可靠性模拟和数模混合芯片，做精做细成熟制程、提高先进制程能力，攻关端侧智能计算芯片与高端存储芯片，开发近存计算、存算一体等新型架构","source_url":"https://so.html5.qq.com/page/real/search_news?docid=70000021_4996aa8c1c852052"},
 {"idx":3,"track":"宏观","title":"特朗普就AI表态：AI进程的影响力远超石油、黄金，在其总统任期内AI产业不会被蓄意阻拦；受此影响隔夜美股跌幅收窄，9/15 A股低开后跌幅同步收窄——对前一日『Anthropic/OpenAI/xAI 呼吁放缓AI开发』引发的AI硬件链崩塌形成对冲","source_url":"https://news.qq.com/rain/a/20260915A06KC600"},
 {"idx":4,"track":"宏观","title":"美方寻求与伊朗达成分步协议，国际油价隔夜回落；但国内期市午盘SC原油涨超6%、燃料油涨近2%、低硫燃料油与乙二醇涨超1%，合成橡胶跌近4%、集运欧线跌近3%——输入性通胀压力与地缘溢价并存","source_url":"https://www.jwview.com/?from_belo_click="},
 {"idx":5,"track":"宏观","title":"FOMC(9/15-16)今日揭幕，CME显示9月加息25bp概率92.4%，决议北京时间9/17凌晨落地；隔夜shibor报1.4294%上涨1.74个基点，资金面平稳；市场在议息结果落地前观望情绪浓厚，两市成交额连续缩量","source_url":"https://news.qq.com/rain/a/20260915A06KC600"},
 {"idx":6,"track":"宏观","title":"A股上午缩量震荡：沪指-0.10%报3881.41、深成指+0.04%、创业板指-0.18%、科创50+1.79%报1555.65、北证50+0.99%；两市半日成交10,652亿元较上日缩量487亿元，1,547只上涨/3,916只下跌，主力资金净流入电子/半导体/建材、净流出银行/医药/商贸零售(电子板块净流入超74亿元)","source_url":"https://so.html5.qq.com/page/real/search_news?docid=70000021_4996aa8c1c852052"},
 # A股医药
 {"idx":7,"track":"A股医药","title":"WCLC(9/12-15)今日收官：中国新药入选口头报告19项、小型口头报告45项刷新历史纪录；翰森制药B7-H3 ADC(ARTEMIS-008)与宜联生物B7-H3 ADC针对小细胞肺癌的III期研究均入选规格最高的全体大会主席专场汇报；机构判断WCLC、ESMO接连召开叠加政策端发力，9-10月行业有望迎来新一轮催化","source_url":"https://www.cnstock.com/commonDetail/790190"},
 {"idx":8,"track":"A股医药","title":"创新药盘中反弹乏力、资金持续离场：CS创新药指数午盘-0.64%、缩量74亿元；药明康德-0.74%、成交27亿缩量17亿、主力净流出1.08亿元；5只创新药ETF中4只净赎回(东财净赎回0.11亿居首)、银华净申购由0.1534亿快速收窄至0.0346亿；呈现『反弹缩量、下跌放量』形态","source_url":"https://www.toutiao.com/w/1876370396894283/"},
 {"idx":9,"track":"A股医药","title":"9/14 ETF资金流：净流出TOP20合计约58.44亿元，创新药方向占4席合计净流出10.26亿元(港股创新药ETF广发-4.21亿、创新药ETF银华-2.22亿、创新药ETF广发-2.13亿、港股通创新药ETF汇添富-1.70亿)；当日融资资金亦从创新药ETF集中兑现离场(银华-6,414.66万元、广发-4,212.07万元)","source_url":"https://www.gelonghui.com/live/2668727"},
 {"idx":10,"track":"A股医药","title":"创新药出海维持高景气：2026年上半年中国License-out数量达100起、首付款50亿美元、交易总额997亿美元均创历史同期新高(约为2024年全年2倍)，全球TOP10交易中国药企独占8席；8月医药板块A股医药生物累计+2.81%、恒生医疗保健+9.35%、恒生生物科技+11.74%；机构认为板块正从『估值驱动』转向『业绩+全球化兑现驱动』","source_url":"https://fund.10jqka.com.cn/20260915/c679917416.shtml"},
 {"idx":11,"track":"A股医药","title":"医药个股进展：恒瑞医药SHR-2004注射液上市许可申请获国家药监局受理；博安生物BA1203(遮蔽型PD-1/IL-2)在中国获批开展临床试验；维立志博维利信一线治疗NSCLC的II期临床研究摘要在WCLC网站发布","source_url":"https://www.163.com/dy/article/L6S8RKC10519QIKK.html"},
 {"idx":12,"track":"A股医药","title":"A股医药板块盘中转跌：中证医药7,658.78(-0.64%)、中证医疗6,586.09(-0.19%)、医疗ETF 0.333(-0.30%)、医药ETF广发0.627(-0.79%)；昨日(9/14)板块大涨后进入消化期，医疗ETF与医药ETF广发双双由涨转跌","source_url":"https://so.html5.qq.com/page/real/search_news?docid=70000021_4996aa8c1c852052"},
 # 大消费
 {"idx":13,"track":"大消费","title":"8月社零同比仅+0.4%(机构预期+0.3%~+3.0%)、1-8月累计+1.1%，其中限额以上单位饮料类+4.9%、粮油食品类+4.0%、通讯器材类+27.3%——总量弱、结构分化，服务零售额+4.9%明显好于商品零售+1.0%；消费总量数据显著低于市场预期","source_url":"https://so.html5.qq.com/page/real/search_news?docid=70000021_5226aa8c68958952"},
 {"idx":14,"track":"大消费","title":"白酒终端零售价分化：11大单品六涨五跌，精品茅台+4元至2,459元(连续两日反弹)、青花汾20+6元至399元(三连阳)、古井贡古20+5元至535元(连续三日走强)；但飞天茅台-2元至1,794元、五粮液普五八代-2元至796元(五连跌创近30天新低)、国窖1573-4元至877元、梦之蓝M6+-3元至608元；11大单品打包总价10,037元较昨日+6元创4天新高","source_url":"https://finance.sina.com.cn/7x24/2026-09-15/doc-inirwfqe6975274.shtml"},
 {"idx":15,"track":"大消费","title":"白酒批价：26年飞天散瓶1,730元(+5)、原箱1,750元、25年飞天1,760→1,770元；但高端年份酒明显回调、五粮液普五旺季放货后批价回落至770-780元；次高端价格带倒挂仍突出(约60%白酒企业批价低于出厂价、800-1500元价格带倒挂比例最高)；行业平均存货周转天数达900天","source_url":"http://gu.qq.com/resources/shy/news/detail-v2/index.html"},
 {"idx":16,"track":"大消费","title":"华创食饮中秋动销系列一：中秋备货开启，行业从供给出清向供需再平衡转变，呈现供给克制、需求弱修复；飞天茅台渠道进度约8成、9月配额到货后供不应求、批价1,700元附近有较强支撑；老窖以顺价促进回款、今世缘布局积极；300-800元次高端商务需求持续承压、100-300元大众价位恢复增长；判断底部信号逐步明朗、宜长线播种","source_url":"http://gu.qq.com/resources/shy/news/detail-v2/index.html"},
 {"idx":17,"track":"大消费","title":"白酒板块盘中表现：中证白酒6,230.41(-0.28%)、白酒Ⅱ板块指数35,254.73(-0.22%)、大消费板块982.53(-0.78%)、消费ETF添富0.656(-0.15%)；白酒Ⅱ板块主力净流出3,459.42万元、大消费板块主力净流出7.42亿元；古井贡酒+1.98%为龙头中唯一显著上涨","source_url":"https://finance.sina.com.cn/7x24/2026-09-15/doc-inirwfqe6975274.shtml"},
 # 美股标普医药
 {"idx":18,"track":"美股标普医药","title":"美股9/14(周一)收盘：标普500医疗保健板块+1.35%为11大板块涨幅前二(仅次于通信服务+2.79%)，XLV 167.75(+1.45%)、IYH 70.87(+1.36%)——连续4日跌幅收窄后首次显著转正并重回168附近；FDA单日多项批准(Ameluz成为美国首个治疗皮肤癌光动力疗法、Pixclara、Isembyld、Joenja标签扩展)叠加强生拟200亿美元剥离骨科部门DePuy Synthes","source_url":"https://www.163.com/dy/article/L6S8RKC10519QIKK.html"},
 {"idx":19,"track":"美股标普医药","title":"欧股医药领涨：阿斯利康+3.81%、葛兰素史克+4.74%，富时100指数+0.44%由医药股驱动——美股+欧股医药板块级共振，与A股/港股医药形成跨市场分化(亚洲医药9/15回调、欧美医药9/14领涨)","source_url":"https://www.163.com/dy/article/L6S8RKC10519QIKK.html"},
 # 恒生科技
 {"idx":20,"track":"恒生科技","title":"港股午盘：恒生指数-0.23%报24,859.45、恒生科技指数+0.76%报4,350.96、国企指数-0.15%报8,272.51；大型科网股多数上涨——网易+3.4%、腾讯+2.93%、阿里+2.27%、京东+1.04%、美团+1%、百度约+1%，小米-0.59%；智谱-4.99%、MINIMAX-5.55%延续AI叙事降温；半导体与PCB回暖(建滔系涨逾4%、大族数控近5%)","source_url":"https://www.163.com/dy/article/L6S8RKC10519QIKK.html"},
 {"idx":21,"track":"恒生科技","title":"9/14 ETF资金流：恒生互联网ETF华夏净流出2.52亿元、恒生科技ETF华夏(513180)净流出2.50亿元，港股创新药与港股科技方向的集体流出构成当日跨境ETF大类净流出10.81亿元的主要来源——资金面与指数表现背离","source_url":"https://www.gelonghui.com/live/2668727"},
 {"idx":22,"track":"恒生科技","title":"港股承压项：内银股普跌(建行/招行跌逾2%、工行-1.76%，摩通称中国银行业8月信贷数据逊预期)、中资电讯股受压(联通-3.57%、中电信-2.5%)、宁德时代-3.01%、汇丰控股-2.24%；恒指半日成交962.48亿港元，半日波幅157点——指数被金融与新能源权重拖累","source_url":"https://hk.finance.yahoo.com/news/%E6%B8%AF%E8%82%A1-%E6%81%92%E6%8C%87%E5%81%8F%E8%BB%9F%E5%8D%8A%E6%97%A5%E8%B7%8C58%E9%BB%9E-044035760.html"},
]

with open('/Users/jieyang/.pi/agent/auth.json') as f:
    key = json.load(f)['deepseek']['key']

def label(batch):
    lines = "\n".join([f"{n['idx']}. [{n['track']}] {n['title']}" for n in batch])
    prompt = f"""你是A股/港股/美股基金投研分析师。对下列每条新闻输出情绪标注，严格输出 JSON 数组，不要任何解释文字。
每条格式：{{"idx":序号,"track":"赛道","sentiment":"正面|中性|负面","strength":0-100情绪强度,"confidence":0-100置信度,"direction":"利多|利空|中性","volatility":"高|中|低","brief":"20字内核心影响"}}
赛道取值只能是：宏观 / A股医药 / 大消费 / 美股标普医药 / 恒生科技。
strength 表示情绪强度（重大突发事件 80-95，明确行业事件 60-80，一般消息 40-60）；confidence 表示该事件对市场影响的确定性（数据明确 75-90，观点类 50-70）。
新闻列表：
{lines}"""
    data = {"model":"deepseek-v4-flash","messages":[{"role":"user","content":prompt}],"max_tokens":8000,"temperature":0.3}
    req = urllib.request.Request("https://api.deepseek.com/chat/completions",
        data=json.dumps(data).encode(),
        headers={"Authorization":f"Bearer {key}","Content-Type":"application/json"})
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
    for attempt in range(2):
        try:
            r = label(batch)
            results.extend(r); print(f"batch {i//B+1} OK ({len(r)})"); break
        except Exception as e:
            print(f"batch {i//B+1} attempt{attempt+1} err: {e}")
            time.sleep(2)

by_idx = {r['idx']: r for r in results}
final = []
for n in NEWS:
    r = by_idx.get(n['idx'], {})
    final.append({**n,
        "sentiment": r.get('sentiment','中性'), "strength": r.get('strength',50),
        "confidence": r.get('confidence',50), "direction": r.get('direction','中性'),
        "volatility": r.get('volatility','中'), "brief": r.get('brief','')})
json.dump(final, open('/tmp/news_intraday_20260915.json','w'), ensure_ascii=False, indent=1)
pos=len([x for x in final if x['direction']=='利多']); neg=len([x for x in final if x['direction']=='利空'])
neu=len([x for x in final if x['direction']=='中性'])
print("total",len(final),"利多",pos,"利空",neg,"中性",neu,"均值强度",round(sum(x['strength'] for x in final)/len(final),1))
for x in final: print(x['idx'], x['track'], x['sentiment'], x['strength'], x['direction'], x['brief'])
