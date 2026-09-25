# -*- coding: utf-8 -*-
"""2026-09-25 盘中档新闻构建（窗口 07:30-13:30）
⚠️ A股休市（中秋），但港股正常交易 → 本档新闻以「港股盘中 + 跨窗口确认的中美/政策 + 行业」为主
⚠️ §3.103：每条必须写 window 字段（news 与 sentiment 双写），否则下游 history_ref 静默匹配 0 条
⚠️ 每条必须带 source_url（抓不到留空字符串）
"""
import json, os

BASE = '/Users/jieyang/Documents/WealthHub'
TODAY = '2026-09-25'
WIN = '盘中(07:30-13:30)'
U_FUTU = 'https://news.futunn.com/post/1000202260/hong-kong-stocks-declined-what-happened-analysis-a-confluence-of'
U_JRJ = 'https://m.jrj.com.cn/madapter/hk/2026/09/25092858535047.shtml'
U_ETNET = 'https://www.etnet.com.hk/www/tc/news/news-article.php?category=market&newsid=20260925993&section=categorized'
U_MOFCOM = 'https://news.qq.com/rain/a/20260925A01DEU00'
U_SUMMIT = 'https://finance.sina.com.cn/roll/2026-09-25/doc-inisyuqf4675784.shtml'
U_CD = 'https://www.chinadaily.com.cn/a/202609/25/WS6ab5c868e4b06d4aa0560254.html'
U_XHCJ = 'https://finance.sina.com.cn/jjxw/2026-09-25/doc-inisyywk9751369.shtml'
U_IFNEWS = 'https://www.ifnews.com/news.html?aid=872923'
U_163BOND = 'https://www.163.com/dy/article/L7LDS30605198RSU.html'
U_WSJ = 'https://www.sohu.com/a/1080683943_130887'
U_FX = 'https://news.163.com/dy/article/L7LEU5G605568W0A.html'
U_15W = 'https://dy.163.com/article/L7M2BQAF0532CO9S.html'
U_JIN10 = 'https://xnews.jin10.com/details/230886'
U_QQMED = 'https://news.qq.com/rain/a/20260925A02NWA00'
U_SMPAA = 'https://www.smpaa.cn/gjsdcg/files/file16048.pdf'
U_SH_YBJ = 'https://ybj.sh.gov.cn/cmsres/de/de100c256c514518be7fc9f29f628759/1ef5ecfd469c412092b6ed0517addb00.pdf'
U_LIQUOR1 = 'https://news.qq.com/rain/a/20260925A04BUL00'
U_LIQUOR2 = 'https://gu.qq.com/resources/shy/news/detail-v2/index.html?t=1#/index?_tentrees_trans=0&id=SN20260923115516a6aa51d6'
U_MED_POLICY = 'https://gu.qq.com/resources/shy/news/detail-v2/index.html?t=1#/index?_tentrees_trans=0&id=SN2026092215124798658b10'

N = [
    # ================= 宏观 =================
    dict(track='宏观', category='宏观类',
         title='中美元首白宫会谈：达成新的经贸联合安排，确立「中美建设性战略稳定关系」新定位，并就人工智能开展对话',
         summary='中方强调合作是双行道，既需拉长合作清单也需压缩问题清单；两国元首同意继续开展人工智能对话、共同防范AI被滥用恶用。这是半年内两国元首第二次互访，为本轮风险资产的核心正向变量。',
         source='新华社/环球时报', source_url=U_SUMMIT, sentiment='正面', score=85, direction='利多', volatility='中', brief='中美元首白宫会谈达成新联合安排', confidence=95),

    dict(track='宏观', category='宏观类',
         title='商务部：中美第八轮经贸磋商达成多项共识（对等降税安排、建立贸易理事会与投资理事会、吉隆坡经贸磋商联合安排延期），何立峰与贝森特首次就人工智能对话',
         summary='磋商在纽约举行，双方围绕落实既有共识、对等降税、机制建设展开「坦诚、深入、富有建设性」交流。7月中方曾表示双方在探索覆盖各自300亿美元商品的对等降税框架。',
         source='商务部/央视新闻/中国日报', source_url=U_MOFCOM, sentiment='正面', score=80, direction='利多', volatility='中', brief='中美第八轮经贸磋商达成多项共识', confidence=92),

    dict(track='宏观', category='宏观类',
         title='美国财长贝森特：中美已同意将贸易休战协议延长至2027年1月10日（原吉隆坡安排原定2026年11月10日到期）',
         summary='休战延期覆盖美方对「名单主体持股50%以上实体的出口管制」、针对中国海事/物流/造船业的措施及中方相应反制。延期直接降低了中美9-10月的关税与管制尾部风险。',
         source='华尔街见闻/环球时报', source_url=U_WSJ, sentiment='正面', score=80, direction='利多', volatility='中', brief='贸易休战延长至2027年1月10日', confidence=88),

    dict(track='宏观', category='政策类',
         title='央行三季度货币政策例会：加大逆周期调节力度，新增「综合运用并适时调整货币政策工具」表述，保持流动性充裕',
         summary='会议于9月19日召开、由潘功胜主持，提出发挥增量与存量政策集成效应、增强政策前瞻性灵活性针对性；相较二季度例会删去「跨周期」，政策重心重新聚焦当期稳增长对冲。',
         source='新华社/新华财经', source_url=U_XHCJ, sentiment='正面', score=70, direction='利多', volatility='低', brief='央行例会加大逆周期调节力度', confidence=90),

    dict(track='恒生科技', category='政策类',
         title='多家险企收到《关于明确保险资金投资港股通ETF监管口径的函》：按规定可投资港股通股票的保险机构，可以投资港股通ETF',
         summary='为保险资金南下配置港股打开制度化通道，是港股（尤其恒生科技等权重板块）中长期增量资金来源；但落地到实际买入有时滞，短期不改变节前流动性缺口。',
         source='金融界', source_url=U_JRJ, sentiment='正面', score=65, direction='利多', volatility='中', brief='险资可投港股通ETF口径明确', confidence=80),

    dict(track='宏观', category='宏观类',
         title='美债抛售延续：10Y 收 5.196%（+8.36bp，2007年来首破5.2%）、30Y 收 5.482%（2004年以来最高）、2Y 4.914%；CME 10月加息概率升至约70%',
         summary='440亿美元7年期国债中标收益率5.085%创该期限历史新高、海外投资者获配比例跌至近两年低点；财政部20-30年期回购仅完成上限68%（40.78亿美元），流动性托底力度不及预期。压力已蔓延至美市政债（30Y破5%、2011年以来新高）。',
         source='中国证券报/华尔街见闻/金十数据', source_url=U_163BOND, sentiment='负面', score=88, direction='利空', volatility='高', brief='美债长端收益率续创新高', confidence=95),

    dict(track='宏观', category='宏观类',
         title='美联储官员密集放鹰：威廉姆斯称「年底前再度收紧是合理的」、保尔森称可能需再次加息、哈玛克与巴尔金均强调通胀压力高企',
         summary='威廉姆斯同时把AI热潮定性为传统需求冲击而非单纯供给改善，并称「提供明确且非常直接的前瞻性指引的时代已经结束」——前瞻指引淡出意味着利率路径不确定性系统性抬升。',
         source='新浪财经/华尔街见闻', source_url=U_FX, sentiment='负面', score=82, direction='利空', volatility='高', brief='美联储四官员同日放鹰', confidence=90),

    dict(track='其他/宽基', category='行业事件类',
         title='美国国际贸易委员会对动态随机存取存储器（DRAM）设备及其下游产品启动337调查，美光科技等为列名被告',
         summary='337调查针对专利侵权、可签发排除令与禁止令，对全球存储芯片供应链构成扰动；对A股存储/半导体设备板块为二阶影响（国产替代逻辑与供应链替代风险并存）。',
         source='金融界', source_url=U_JRJ, sentiment='负面', score=55, direction='利空', volatility='中', brief='美ITC对DRAM设备启动337调查', confidence=78),

    dict(track='宏观', category='宏观类',
         title='中国10Y国债收益率1.672%（较上日+0.00%）、5Y 1.400%、30Y 2.116%；中美10Y利差扩大至约352bp',
         summary='国内利率端维持低位平稳，与美债长端创多年新高形成极致反差，是「人民币资产相对估值优势 vs 全球无风险利率抬升」的核心矛盾点。',
         source='国际金融报/新华财经', source_url=U_IFNEWS, sentiment='中性', score=35, direction='中性', volatility='低', brief='中国10Y国债1.672%保持平稳', confidence=90),

    dict(track='其他/宽基', category='政策类',
         title='北京楼市新政9月24日起施行：全面加强预售管理，8月28日后新出让商品住房项目申请预售须完成主体结构封顶并出具验收记录',
         summary='叠加「有序推进现房销售」，指向地产供给端进一步规范化；对地产链及产业链需求预期构成中期扰动。',
         source='新华社/新华财经', source_url=U_XHCJ, sentiment='中性', score=35, direction='中性', volatility='低', brief='北京楼市新政加强预售管理', confidence=82),

    # ================= 恒生科技 =================
    dict(track='恒生科技', category='行业事件类',
         title='港股9月25日低开低走：恒指24,424.96（−1.36%）、恒生科技4,295.13（−1.51%，首次失守4,300）、恒生国企8,142.05（−1.50%）',
         summary='早盘恒指与恒科跌幅一度双双扩大至2%。权重股：阿里−1.91%、小米−3.08%、网易−3.38%、京东−2.37%、美团−1.52%、腾讯−1.09%、快手−2.43%、百度−1.74%、比亚迪股份−2.58%；中芯国际−0.86%相对抗跌。恒生科技自9/22高点4,510.06累计−4.76%。',
         source='新浪hq直取/富途牛牛/金融界', source_url=U_FUTU, sentiment='负面', score=78, direction='利空', volatility='高', brief='恒生科技失守4300报4295.13', confidence=95),

    dict(track='恒生科技', category='宏观类',
         title='港股双压力拆解：①利率端——港元与美元挂钩、金管局跟随美联储，美债收益率上行直接抬升全市场折现率，恒科成分以盈利滞后释放的AI成长股为主；②节前流动性收缩——9/25-9/27港股通暂停、10/1-10/7再次关闭，10/8才恢复',
         summary='南向资金今年以来累计净流入超3,800亿港元，其中资讯科技业净流入1,002亿港元，是港股科技板块最重要的边际定价力量。南向缺位后，同样规模的抛售需要更低价格才能找到对手盘，跌幅被放大。历史数据亦显示港股7-10月存在季节性偏弱特征。',
         source='富途牛牛', source_url=U_FUTU, sentiment='负面', score=72, direction='利空', volatility='高', brief='港股：利率+南向缺位双压力', confidence=88),

    dict(track='恒生科技', category='行业事件类',
         title='南向资金9月24日净流入29.00亿港元（连续第14个交易日净流入，净流入额较前日减少15.9%）；结构为「买宽基+买腾讯、卖医药与半导体」',
         summary='净买入：盈富基金+6.33亿、腾讯+6.30亿、南方恒生科技+5.56亿、恒生中国企业+5.13亿、建滔积层板+2.98亿；净卖出：金斯瑞生物科技−2.79亿、中芯国际−2.25亿、智谱−0.87亿。主板成交1,596亿港元（减少13.4%），港股通成交占比39.5%。',
         source='etnet经济通', source_url=U_ETNET, sentiment='中性', score=45, direction='中性', volatility='中', brief='南向连续14日净流入但额降15.9%', confidence=92),

    dict(track='恒生科技', category='行业事件类',
         title='港股通9月25日至27日暂停南向服务，国庆期间10月1日至7日再次关闭，10月8日恢复——本档起连续多日内地增量资金完全缺位',
         summary='港股市场本身正常交易（与本档确认一致），但南向通道关闭使港股科技权重股失去最重要的边际承接方，长假期间海外不确定性亦无法对冲，机构倾向持币观望。',
         source='富途牛牛/沪深交易所安排', source_url=U_FUTU, sentiment='负面', score=65, direction='利空', volatility='高', brief='港股通暂停，南向连续多日缺位', confidence=90),

    dict(track='恒生科技', category='行业事件类',
         title='港股科技个股相对强弱：商汤逆市涨超4%，中芯国际−0.86%，中概股隔夜承压（纳斯达克中国金龙指数收跌0.67%，拼多多−1.26%、京东−1.51%、百度−1.89%、携程−1.45%、哔哩哔哩−1.33%）',
         summary='互联网平台与AI硬件同步回调，但半导体设备端（中芯）跌幅明显小于平台端，与9/24「压力由互联网向AI硬件/半导体转移」的判断出现反向——本档压力重新集中在平台与消费互联网。',
         source='格隆汇/金融界', source_url=U_JRJ, sentiment='负面', score=60, direction='利空', volatility='中', brief='平台端跌幅大于半导体端', confidence=80),

    dict(track='恒生科技', category='行业事件类',
         title='港股市场结构性亮点：锂电/有色与蓝筹承压的同时，零售股板块持续活跃；市场对港股9-10月的季节性偏弱保持警惕',
         summary='机构普遍将本轮回调归因于「无风险利率+节前流动性」的分母端冲击，而非港股科技盈利端恶化；若假期后南向资金回补，估值修复的弹性同样来自分母端。',
         source='格隆汇/富途牛牛', source_url=U_FUTU, sentiment='中性', score=40, direction='中性', volatility='中', brief='回调归因分母端非盈利端', confidence=75),

    # ================= A股医药 =================
    dict(track='A股医药', category='政策类',
         title='第十一批国家组织药品集中采购文件发布：覆盖55个品种、超400家企业参与、46,359家医药机构完成报量',
         summary='首次在品种遴选时排除「通过谈判新进入医保且仍在协议期内」的品种以保护创新积极性；提出更严格质量要求（2年以上同类制剂生产经验、生产线2年无GMP违规）。自2018年以来国家已开展10批集采、覆盖435种药品。',
         source='人民日报/联合采购办公室', source_url=U_SMPAA, sentiment='负面', score=70, direction='利空', volatility='中', brief='第十一批国采55品种46,359家报量', confidence=90),

    dict(track='A股医药', category='政策类',
         title='上海市医保局发布第十一批集采医保支付协同通知：按通用名（含剂型）确定支付标准，5个限适应症报量品种使用价高药的个人自负比例提高20%/30%；不高于支付标准的用药不核减DRG/DIP支付标准与总额预算',
         summary='「支付标准+自负比例」双工具直接压缩非中选高价药的渠道价值；同时建立医院主动换用低价药的激励，是集采从「中标降价」向「终端支付端传导」的关键一环。',
         source='上海市医疗保障局', source_url=U_SH_YBJ, sentiment='负面', score=60, direction='利空', volatility='中', brief='上海集采支付协同：价高药自负+20%~30%', confidence=88),

    dict(track='A股医药', category='政策类',
         title='第七批国家医用耗材集采：148家企业517个产品拟中选，约九成内镜相关耗材纳入；国家集采累计覆盖165种高值耗材',
         summary='规则设置双标准差价格锚点——畸高价出局、畸低价不带量，报价策略从「压到最低」改为「落在区间内」；采购周期至2029年底，消化介入赛道23种耗材纳入。',
         source='医疗器械经销商联盟/高值医用耗材联采办', source_url='', sentiment='负面', score=62, direction='利空', volatility='中', brief='第七批耗材国采517产品拟中选', confidence=85),

    dict(track='A股医药', category='政策类',
         title='2026年度国家医保药品目录现场谈判竞价完成：124个目录外药品参与竞价，12个药品开展商保创新药目录价格协商；新版目录2027年1月1日起执行',
         summary='谈判覆盖肿瘤、罕见病、慢性病、儿童用药、细胞治疗与双抗ADC；中成药成为上午场主力（枣仁宁心滴丸、桃红四物汤颗粒等经典名方到场）。结果预计11月发布。',
         source='海报新闻', source_url='', sentiment='负面', score=55, direction='利空', volatility='中', brief='国谈124个目录外药品完成竞价', confidence=82),

    dict(track='A股医药', category='政策类',
         title='《医药工业发展「十五五」规划》量化指标解读：规上医药工业营收≥3.5万亿元、FIC占全球比例≥25%、创新药产业规模年均增速≥20%、年营收超百亿药企50家、千亿级医药产业园区20个、五年累计创新医疗器械上市≥200个',
         summary='FIC占全球25%的统计口径覆盖Ⅰ期临床至获批上市全部管线（不含临床前与终止项目），意味着国家不再以「新药上市数量」考核，而是倒逼向源头首创转型。重点方向：新靶点/不可成药靶点、siRNA/ASO、PROTAC、PDC、多抗ADC/RDC/AOC、通用型CAR-T、iPSC、AAV载体、LNP递送。',
         source='工信部等十部门/药时空', source_url=U_15W, sentiment='正面', score=75, direction='利多', volatility='中', brief='医药十五五规划：FIC占全球≥25%', confidence=88),

    dict(track='A股医药', category='行业事件类',
         title='港股医药逆势走强：恒生医疗保健指数+0.38%（同期恒生科技−1.51%），金斯瑞生物科技+8.51%（9月24日曾跌4.8%并被南向净卖出2.79亿港元）',
         summary='港股医药在本档与港股科技出现显著背离，是「利率敏感型成长（平台/AI硬件）与政策免疫型创新药」的分化在价格端的首次清晰体现；对A股医药的映射意义在于：创新药链的独立行情可能不依赖南向资金。',
         source='新浪hq直取', source_url=U_FUTU, sentiment='正面', score=60, direction='利多', volatility='中', brief='恒生医疗保健逆势+0.38%', confidence=85),

    dict(track='A股医药', category='行业事件类',
         title='跨国药企持续扫货中国管线：诺华以9亿美元从中企引进一款临床前放射性配体疗法；罗氏与Atavistik Bio签下潜在总额20亿美元合作（心血管代谢变构小分子）；勃林格殷格翰与Envisagenics签下潜在10亿美元多年期肿瘤多靶点合作',
         summary='GSK表示自两年前从中国授权药物尝到甜头后一直在执行东西方平衡策略，中国资产筛选成为跨国药企常规动作。同时勃林格殷格翰将上海生物药CDMO业务出售给本地抗体开发商——跨国方甩掉重资产、本地方获得产能与标准。',
         source='FierceBiotech/FiercePharma', source_url=U_JIN10, sentiment='正面', score=65, direction='利多', volatility='中', brief='MNC密集扫货中国医药管线', confidence=80),

    # ================= 美股标普医药 =================
    dict(track='美股标普医药', category='行业事件类',
         title='罗氏公布sefaxersen三期数据，与诺华争夺肾病重磅市场；同一适应症的二代产品进场，一代产品的价格与份额同时受压',
         summary='肾病赛道竞争加剧，提示「同一靶点/适应症的代际替代」会快速侵蚀先发产品定价权——这一逻辑同样适用于国内GLP-1与ADC竞品的估值框架。',
         source='FierceBiotech', source_url='', sentiment='中性', score=45, direction='中性', volatility='中', brief='罗氏sefaxersen三期数据公布', confidence=72),

    dict(track='美股标普医药', category='业绩类',
         title='礼来CEO称其GLP-1产品在联邦医疗保险（Medicare）覆盖计划中占据70%份额，参保老年人已达70万',
         summary='支付覆盖是代谢类用药放量的核心瓶颈，Medicare份额高企意味着礼来在美国老龄化人口的支付端已建立壁垒；对国内GLP-1企业的启示是「渠道与支付」而非单纯疗效决定峰值销售。',
         source='FiercePharma', source_url='', sentiment='正面', score=55, direction='利多', volatility='中', brief='礼来GLP-1占Medicare 70%份额', confidence=75),

    dict(track='美股标普医药', category='行业事件类',
         title='美国药企收缩信号：百时美施贵宝计划再裁减265名与新泽西总部相关的员工；Adagio Medical启动战略评估、裁减超一半全职员工并面临纳斯达克退市压力',
         summary='MNC总部成本外移与中小医疗器械企业出清并行，指向「高利率环境下研发/器械长尾企业的融资与成本压力」；对CXO订单结构与器械出海均为中期变量。',
         source='FiercePharma/FierceBiotech', source_url='', sentiment='负面', score=45, direction='利空', volatility='中', brief='美国药企裁员与器械商出清', confidence=72),

    dict(track='美股标普医药', category='政策类',
         title='本赛道双事件窗口提示：美国Section 232进口专利药100%关税（含MFN定价）9月29日零时生效；美国8月PCE数据于9月25日美东公布（北京时间9月25日20:30）',
         summary='关税条款为「扩围+豁免」双向结构（临床/研发/非商业用途零关税，孤儿药、细胞与基因疗法、ADC满足条件时零关税），不得按单边100%外推；PCE则决定10月加息概率能否进一步上行。两者均落在国内中秋休市期间。',
         source='MassBio/华尔街见闻', source_url=U_WSJ, sentiment='中性', score=60, direction='中性', volatility='高', brief='9/29关税生效+9/25 PCE公布', confidence=85),

    # ================= 大消费 =================
    dict(track='大消费', category='业绩类',
         title='贵州茅台披露：9月茅台酒终端动销环比增长约一倍、同比增长超20%；渠道存销比下降至良好水平，市场活力与健康度同步提升',
         summary='茅台集团总经理王莉9月25日在西宁召开青甘新藏四省区市场营销座谈会，标志8月底启动的秋季市场调研收官——一个月内覆盖16个省区、与300余家渠道商面对面交流。这是本赛道连续第2档出现「厂商口径的硬数据转正」。',
         source='贵州茅台微信公众号/酒业家', source_url=U_LIQUOR1, sentiment='正面', score=82, direction='利多', volatility='中', brief='茅台9月终端动销环比翻倍', confidence=88),

    dict(track='大消费', category='行业事件类',
         title='9月25日中秋当天飞天茅台批价升至1,810元/瓶（原箱），连续第六日站上1,800元、创近一个月新高；散瓶1,765-1,790元；普五（八代）回升至825-835元、国窖1573上涨30元/瓶、君品习酒上涨20元/瓶',
         summary='自9月22日起名酒大单品批价持续上涨，25年飞天散瓶从9月21日1,750元低点连续反弹。茅台自营门店执行价1,766元、i茅台挂牌1,639元，两条官方渠道相差127元。50-200元价格带成动销主流，婚宴市场「8天已全部订满」。',
         source='今日酒价/酒业家', source_url=U_LIQUOR1, sentiment='正面', score=75, direction='利多', volatility='中', brief='飞天批价六连涨至1810元原箱', confidence=82),

    dict(track='大消费', category='行业事件类',
         title='批价源口径分歧须并列披露：百荣酒饮9月24日价表显示53%飞天原箱10,530元/箱（折1,755元/瓶）连续第三日持平、公斤飞天回落30元、八代普五微降10元；与「今日酒价」9月25日原箱1,810元/瓶存在明显差异',
         summary='两套批价源分别对应不同渠道样本与箱/瓶折算口径，本方法按纪律同时披露、不做归一；「当日价表整体3涨4跌136持平」，9月25日至27日中秋期间暂停交易前波幅明显收窄。',
         source='百荣酒饮/酒业家', source_url=U_LIQUOR1, sentiment='中性', score=40, direction='中性', volatility='低', brief='飞天批价两源口径分歧须并列', confidence=78),

    dict(track='大消费', category='行业事件类',
         title='肖竹青：今年中秋前夕白酒动销同比下滑但降幅收窄，多地渠道反馈中秋期间销量预计同比下滑约15%-20%；超八成酒商预计双节销售业绩与去年基本持平或同比下滑',
         summary='消费端理性化趋势强化，100-300元仍是中秋礼赠主流价位；肖竹青判断消费基本只剩「礼品需求+企业福利用酒」两大场景且双双走弱，白酒正式进入缩量竞争、头部独享红利的新周期。',
         source='云酒头条/糖酒快讯/酒说', source_url=U_LIQUOR1, sentiment='负面', score=62, direction='利空', volatility='中', brief='渠道反馈中秋动销同比降15%-20%', confidence=85),

    dict(track='大消费', category='业绩类',
         title='山西汾酒公告：股东华创鑫睿（香港）因旗下基金到期清算，拟通过大宗交易减持不超过1,620万股，占总股本1.33%（截至9月22日持有1.28亿股、占10.50%）',
         summary='华润系基金到期清算导致的被动减持，虽为财务性退出而非看空，但在板块情绪脆弱期构成供给端压力，且大宗交易折价可能形成短期价格锚。',
         source='山西汾酒公告/酒业家', source_url=U_LIQUOR1, sentiment='负面', score=55, direction='利空', volatility='中', brief='华润系拟减持汾酒不超1620万股', confidence=88),

    dict(track='大消费', category='行业事件类',
         title='中秋礼盒集体「退潮」：茅台文旅确定不再生产含贵州茅台酒的中秋礼盒，五粮液尚未推出全新中秋礼盒，古井贡由「古16」降档为「古8」，洋河将礼盒转为扫码抽奖返利品',
         summary='节庆礼盒曾是行业惯例，今年明显降温，反映酒企在库存压力下更加务实；渠道端高端滋补礼盒销量同比回落12%-18%、大闸蟹团购订单同比降约15%——礼品溢价系统性退潮，消费从「买面子」转向「买价值」。',
         source='每日经济新闻/腾讯新闻', source_url=U_LIQUOR1, sentiment='负面', score=50, direction='利空', volatility='中', brief='中秋礼盒集体退潮、品牌降档', confidence=80),

    dict(track='大消费', category='行业事件类',
         title='美团闪购联合茅台酱香酒、汾酒、洋河、古井贡、剑南春、西凤、今世缘、郎酒、水井坊等十家名酒推出行业首个白酒全链路保真体系；茅台酱香酒首批超千家门店「闪购开业」，并招募5,000-7,000家主题终端店运营商',
         summary='体系含售前实拍返图、配送「保真送」（一次性「安心扣」上锁）、售后「假一赔十」。即时零售正成为酒企触达新客的增量入口（酒类即时零售2025年破500亿元，机构预测2026年可达1,000亿元，20-35岁用户占65%）。',
         source='美团闪购/酒业家', source_url=U_LIQUOR1, sentiment='正面', score=55, direction='利多', volatility='中', brief='美团闪购推白酒全链路保真体系', confidence=80),

    dict(track='大消费', category='行业事件类',
         title='双节动销逻辑换轨：酒企弃压货、资源转投C端——汾酒对青花30/26/20推出开瓶红包并把打款进货奖励转为消费者端投入，古井贡围绕古5/古8/古16开瓶扫码，洋河对开瓶终端给基础奖励并以异地扫码限制遏制窜货',
         summary='行业不再将打款量与铺货量作为核心考核标准，转向考核开瓶率。「账面旺季」被换成「真实的库存表和价盘表」，中期利好渠道健康度但短期牺牲报表收入节奏。',
         source='澎湃新闻/每日经济新闻', source_url=U_LIQUOR2, sentiment='中性', score=45, direction='中性', volatility='中', brief='酒企考核转开瓶率、弃压货', confidence=82),

    # ================= 其他/宽基 =================
    dict(track='其他/宽基', category='宏观类',
         title='A股中秋休市安排：9月25日至9月27日休市，9月28日（周一）复市；本年度仅剩9月28-30日三个连续交易日，其后10月1日至7日国庆休市，10月8日复市',
         summary='节前最后3个交易日将同时承载「9/29专利药关税生效」「9月PMI」「三季报预告密集披露前」三重信息，且10/8复市后市场定价依据将以盈利为主。',
         source='沪深交易所', source_url=U_XHCJ, sentiment='中性', score=40, direction='中性', volatility='中', brief='A股中秋休市，9/28复市', confidence=92),

    dict(track='其他/宽基', category='行业事件类',
         title='中国10年期国债收益率1.672%、Shibor隔夜1.3640%；央行9月25日开展515亿元7天期逆回购，单日净回笼1,105亿元，银行间资金面依旧平稳',
         summary='国内流动性环境维持宽松取向，与央行例会「保持流动性充裕」表述一致；国债期货全线收涨，30年期主力合约涨0.31%。',
         source='陆家嘴财经早餐/新华财经', source_url=U_XHCJ, sentiment='正面', score=45, direction='利多', volatility='低', brief='央行净回笼1105亿，资金面平稳', confidence=88),

    dict(track='其他/宽基', category='行业事件类',
         title='香港政府计划发行多币种数字绿色债券筹集150亿至200亿港元，为全球同类债券中规模最大；以美元、港元、欧元和离岸人民币计价，最早下周一定价',
         summary='人民币离岸债券市场扩容的又一标志性事件（央行上海总部口径：自贸离岸债已累计发行22单、约86亿元），对离岸人民币流动性构成正向供给。',
         source='陆家嘴财经早餐', source_url=U_XHCJ, sentiment='中性', score=35, direction='中性', volatility='低', brief='香港拟发150-200亿数字绿债', confidence=80),
]

for i, it in enumerate(N, 1):
    it['date'] = TODAY
    it['window'] = WIN
    it.setdefault('strength', it['score'])
    it['source_url'] = it.get('source_url', '')

out = os.path.join(BASE, f'data/processed/news/news-intraday-{TODAY.replace("-","")}.json')
json.dump(N, open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

from collections import Counter
print(f'已写入 {out}：{len(N)} 条')
print('赛道分布:', Counter(x['track'] for x in N))
print('方向分布:', Counter(x['direction'] for x in N))
print('source_url 覆盖:', sum(1 for x in N if x['source_url']), '/', len(N))
