# -*- coding: utf-8 -*-
"""2026-09-14 盘中档新闻情绪标注（DeepSeek v4-flash，max_tokens=8000）"""
import json, urllib.request, ssl, time
ctx = ssl.create_default_context(); ctx.check_hostname=False; ctx.verify_mode=ssl.CERT_NONE

NEWS = [
 # 宏观
 {"idx":1,"track":"宏观","title":"布伦特原油突破107美元/桶(日内涨2.6%-3.37%)、WTI突破103美元(涨2.99%)：也门胡塞武装袭击沙特吉赞省民宅与清真寺、霍尔木兹海峡一船只被投射物击中起火船员撤离、伊朗一商船被击1死4伤；沙特东西输油管道9/11遭袭关闭威胁全球4%石油供应，阿曼霍尔木兹航运会议9/14推迟","source_url":"https://www.thevibes.com/articles/business/127257/oil-prices-surge-above-us107-as-middle-east-supply-risks-deepen"},
 {"idx":2,"track":"宏观","title":"CME FedWatch显示美联储9/16加息25bp概率升至86%(CPI公布前67%)；摩根大通预计2026年9月与12月各加息25bp；高盛由预计按兵不动改为9月加息25bp、降息时点推迟至2027年；2年期美债收益率4.61%创2024年7月以来最高、10年期4.967%接近2023年10月最高","source_url":"https://live.euronext.com/en/financial-news/shares-slip-asia-oil-climbs-rate-hikes-loom"},
 {"idx":3,"track":"宏观","title":"亚太股市普跌：日经225跌1.7%(软银集团-11%、铠侠-9.3%、爱德万测试-4.9%)、韩国KOSPI跌3.3%、MSCI亚太除日本-0.8%；美股期货标普500跌0.5%、纳指期货跌1.1%；欧股EUROSTOXX50期货-0.5%、DAX期货-0.4%","source_url":"https://live.euronext.com/en/financial-news/shares-slip-asia-oil-climbs-rate-hikes-loom"},
 {"idx":4,"track":"宏观","title":"全球央行超级周：日本央行9/18加息25bp至1.25%概率约76%；欧洲央行上周已加息并警告进一步收紧；英国央行9/17预计维持3.75%但票数可能分裂——油价高企推动全球通胀压力再起","source_url":"https://www.thevibes.com/articles/business/127257/oil-prices-surge-above-us107-as-middle-east-supply-risks-deepen"},
 {"idx":5,"track":"宏观","title":"IEA大幅下调2026年石油需求预测(日均减少250万桶，疫情以来最大年度降幅)、OPEC连续第5次下调2026年需求增长预测——高油价与供应收紧压制消费，对油价上行形成中期对冲","source_url":"https://pip.bar/daily-analysis-14-sep-2026-dollar-under-pressure-as-oil-volatility-and-fed-rate-hike-bets-drive-markets"},
 {"idx":6,"track":"宏观","title":"9/14 17:00中国金融数据密集公布(M2、人民币贷款余额、新增人民币贷款、社会融资规模)，为盘后核心变量；发改委披露8月线下消费支付金额同比+2.6%连续2个月上升","source_url":"https://news.10jqka.com.cn/20260914/c679856039.shtml"},
 # A股医药
 {"idx":7,"track":"A股医药","title":"WCLC世界肺癌大会重磅数据：康方生物全球首创PD-1/VEGF双抗依沃西HARMONi-2研究OS 30.8个月vs帕博利珠单抗22.6个月、死亡风险降低27%，为全球首个对比『药王』帕博利珠单抗取得OS与PFS双阳性结果的III期临床","source_url":"https://news.qq.com/rain/a/20260914A05UTI00"},
 {"idx":8,"track":"A股医药","title":"百济神州泽布替尼新适应症上市申请获CDE受理(联合利妥昔单抗一线治疗相关淋巴瘤，疾病进展或死亡风险降低43%)；2026上半年泽布替尼全球销售额161.27亿元、占全球主要BTK抑制剂销售额41%稳居第一","source_url":"https://news.qq.com/rain/a/20260914A05UTI00"},
 {"idx":9,"track":"A股医药","title":"翰森制药B7-H3 ADC瑞康立伏妥塔单抗III期ARTEMIS-008研究期中分析：经治小细胞肺癌二线治疗死亡风险降低54%、刷新该领域最长总生存期纪录；GSK曾以17.1亿美元获得该药海外权益","source_url":"https://finance.sina.com.cn/jjxw/2026-09-14/doc-inirupew9493336.shtml"},
 {"idx":10,"track":"A股医药","title":"医药板块盘中大幅走强：创新药板块指数+1.94%报1,068.52、医药生物板块+1.81%、化学制药+1.75%；万邦医药与近岸蛋白20cm涨停，百普赛斯涨近12%、东富龙涨近8%、泰格医药/迈威生物/康龙化成涨超5%；港股恒生生物科技指数大涨近3%、康方生物+5.15%","source_url":"https://xueqiu.com/9396125131/409168224"},
 {"idx":11,"track":"A股医药","title":"药明康德2026上半年营业收入288.97亿元同比+38.93%、归母净利润110.8亿元同比+29.43%，并全面上调2026年全年指引(整体收入由513-530亿元上调至585-605亿元，持续经营收入增速由18%-22%上调至35%-39%)","source_url":"https://finance.sina.com.cn/jjxw/2026-09-14/doc-inirupew9493336.shtml"},
 {"idx":12,"track":"A股医药","title":"中泰证券：WCLC集中披露多项肺癌领域临床进展，进一步验证中国创新药的临床价值和全球竞争力，可积极把握创新药回调后的配置机会；当前医药板块估值27倍PE低于历史均值，三季度部分企业新增订单进入收入确认期","source_url":"https://news.qq.com/rain/a/20260914A05UTI00"},
 # 大消费
 {"idx":13,"track":"大消费","title":"白酒板块资金面持续走弱：当日主力资金净流出3.27亿元、连续3个交易日净流出(其中高端白酒标的净流出占比62%)；全国白酒批发价格指数报99.72较前一日跌0.08、连续3个交易日小幅回落，800-1500元次高端价格带倒挂仍突出","source_url":"https://cfi.cn/p20260914000110.html"},
 {"idx":14,"track":"大消费","title":"白酒批价分化：茅台系全线走强(26年飞天单瓶1725元+5/原箱1750元+15、精品茅台2370元+10)，国窖1573升至881元+6、古井贡古20反弹9元至530元、习酒君品641元+4、青花郎689元+6；五粮液普五八代798元-2延续四连阴跌破800元整数关口；11大单品终端零售总价回升36元至10,031元重上万元","source_url":"https://k.sina.com.cn/article_5953189932_162d6782c06704y36k.html"},
 {"idx":15,"track":"大消费","title":"仁怀产区政策落地：落实《深化世界酱香白酒核心产区建设政策措施》28条细则(原料奖励、污水处理补贴、电费补贴)，推进『卖酒向卖生活方式』升级打造酒旅融合场景；茅台镇生产主体已从巅峰期1925家锐减至868家、淘汰率超55%，产区集中度进一步提升","source_url":"https://cfi.cn/p20260914000110.html"},
 {"idx":16,"track":"大消费","title":"华创食饮中秋动销系列：中秋备货开启、行业从供给出清向供需再平衡转变；飞天茅台渠道进度约8成、9月配额到货后仍供不应求、批价稳在1700元附近；五粮液回款顺畅部分区域已达成全年目标；Q2为报表底部、下半年低基数下动销与利润有望转正","source_url":"https://cfi.cn/p20260914000110.html"},
 # 美股标普医药
 {"idx":17,"track":"美股标普医药","title":"Summit Therapeutics(SMMT) ivonescimab在WCLC公布HARMONi-2总生存数据(30.8 vs 22.6个月，HR 0.73，p=0.009)，9/14周一为首个定价日，暗盘一度涨超4%；同期BNTX公布pumitamig+elfetabart组合(PD-L1×VEGF双抗+B7-H3 ADC)小细胞肺癌ORR 70.4%","source_url":"https://xueqiu.com/1947009696/409119752"},
 {"idx":18,"track":"美股标普医药","title":"FDA周末密集审批：9/13周日批准Telix(TLX)的Pixclara(脑胶质瘤PET显影剂)，9/14开盘定价；Scholar Rock(SRRK)的IsembYLD(apitegromab)获FDA批准成为全球首个肌靶向SMA疗法、提前19天获批","source_url":"https://xueqiu.com/1947009696/409119752"},
 {"idx":19,"track":"美股标普医药","title":"上周(9/8-9/11)美股医药个股剧烈分化：诺华NVS周跌0.39%(del-desiran DM1 III期HARBOR失败、周二单日-13.93%)、安进AMGN周跌4.02%(pelacarsen Lp(a)失败read-across、周一-10.08%创2016年来最大跌幅)、TYRA周跌17.58%、EVMN周跌19.42%；阿斯利康AZN周涨0.08%一正一负互抵","source_url":"https://xueqiu.com/1947009696/409119752"},
 {"idx":20,"track":"美股标普医药","title":"标普500医疗保健板块9/11跌0.14%，为11大板块唯二下跌(仅强于公用事业-0.34%)；XLV 165.36(-0.18%)、IYH 69.92(-0.11%)跌幅连续第4个交易日收窄(-2.52%→-0.33%→-0.55%→-0.18%)，板块性利空呈一次性定价后修复形态","source_url":"https://www.marketindex.com.au/news/morning-wrap-asx-200-to-rise-s-and-p-500-snaps-a-four-day-slide-cpi-locks"},
 # 恒生科技
 {"idx":21,"track":"恒生科技","title":"港股午盘主要指数集体上涨：恒生指数+0.32%、恒生中国企业指数+0.36%、恒生科技指数+0.17%、恒生生物科技指数大涨近3%；药明康德/药明生物/药明合联均涨超4%、康方生物涨超5%，医药与生物科技为港股最强主线","source_url":"https://xueqiu.com/9396125131/409168224"},
 {"idx":22,"track":"恒生科技","title":"日经225跌1.7%、软银集团跌11%、铠侠跌9.3%、爱德万测试跌4.9%——全球AI硬件与半导体链在加息预期与油价高企下同步回调，对港股科技板块情绪形成外部压制","source_url":"https://finance.sina.com.cn/headline/2026-09-14/doc-iniruhxa7321623.shtml?froms=pccs"},
 {"idx":23,"track":"恒生科技","title":"恒生科技指数13:42报4,320.38点基本持平(-0.02%)，盘中最低4,290.58一度失守4,300后收复；恒生指数24,901.62(+0.39%)——南向资金持续流入与医药生物主线对冲了全球科技回调压力","source_url":"https://finance.sina.com.cn/jjxw/2026-09-14/doc-inirupew9493336.shtml"},
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
B = 8
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
json.dump(final, open('/tmp/news_intraday_20260914.json','w'), ensure_ascii=False, indent=1)
pos=len([x for x in final if x['direction']=='利多']); neg=len([x for x in final if x['direction']=='利空'])
neu=len([x for x in final if x['direction']=='中性'])
print("total",len(final),"利多",pos,"利空",neg,"中性",neu,"均值强度",round(sum(x['strength'] for x in final)/len(final),1))
for x in final: print(x['idx'], x['track'], x['sentiment'], x['strength'], x['direction'], x['brief'])
