# -*- coding: utf-8 -*-
"""2026-10-22 盘后档：新闻窗口（14:00-20:00）+ 情绪标注（规则表，DeepSeek 402 降级第 17 日）

输出：
  data/processed/news/news-close-20261022.json      （本档 18 条）
  data/processed/news/news-2026-10-22.json          （合并：盘前 30 + 盘中 22 + 盘后 18）
  data/processed/news/sentiment-2026-10-22.json     （同结构，含 window 字段）
  data/processed/history/sentiment_agg_20261022_close.json
"""
import json, os
from collections import defaultdict

BASE = '/Users/jieyang/Documents/WealthHub'
NEWS = os.path.join(BASE, 'data/processed/news')
HIST = os.path.join(BASE, 'data/processed/history')
TODAY = '2026-10-22'
WIN = '盘后(10/22 13:30-20:00)'
DEG = '规则表降级（DeepSeek HTTP 402，连续第 17 个日历日）'

ITEMS = [
    dict(track='其他/宽基', category='行业事件类', sentiment='中性', strength=56, direction='中性',
         volatility='高', confidence=92,
         brief='沪指-1.48%·创业板-4.37%·近5000股下跌·放量998亿',
         title='🟡 **10/22 收盘速览：上证 −1.48% 报 3,658.03（跌破 3,700、日内最低 3,649.86）、深证成指 −2.96% 报 11,357.32、创业板指 −4.37% 报 2,576.90（失守 2,600 并创一年多新低）、科创50 −2.78%；两市成交 1.5419 万亿元、放量 998 亿元；全市场近 5,000 只个股下跌**',
         summary=('**本档定价基准条目。** ① **「放量下跌」定性确定** —— 成交 15,419 亿元、较 10/21 放量 998 亿元，'
                  '与 10/21「缩量阴跌（−268 亿）」**形态完全反转**，说明**主动减仓而非无人接盘**；'
                  '② **跌幅结构 = 成长 >> 价值**：创业板 −4.37% / 科创50 −2.78% / 深证 −2.96% 均远大于上证 −1.48%、'
                  '沪深300 −1.84%；**银行逆势创历史新高**（工商银行 +0.83% 报 8.58 元、市值 3.06 万亿元）→ '
                  '**资金是「从成长切向红利」，不是全面撤离**；'
                  '③ **组合映射**：其他/宽基腿 −1,835.09 元（−1.982%）为**本档最大拖累**，其中广联达 −2.34%（−895.97 元）'
                  '为单券最大负贡献；该腿偏大盘、不持有银行，**因此既没享受「银行护盘」也没享受「小盘抗跌」**；'
                  '④ **本档赛道动作 0 元**（详见策略章节）。'),
         source='同花顺 A股收评（2026-10-22 15:00）/ 本地新浪 hq 直取（指数点位与成交额）',
         source_url='https://stock.10jqka.com.cn/20261022/c680971639.shtml'),

    dict(track='其他/宽基', category='宏观类', sentiment='利空', strength=70, direction='利空',
         volatility='高', confidence=90,
         brief='亚太集体大跌·AI叙事与美债双压',
         title='🔴 **亚太股市集体大跌：韩国综合指数跌逾 3%（三星电子、SK海力士领跌）、日经225 跌超 2%、恒生科技盘中跌超 5%；韩国央行 10/22 明确表态「股市波动主要源于市场对 AI 投资增速放缓的忧虑」**；10 年期美债收益率维持 5% 上方（最高触及 5.36%）、30 年期 5.73%，均创 2002 年以来最高',
         summary=('**这是本档的「共同因子」条目 —— A股 与港股 同跌并非两个独立事件。** ① **传导链**：'
                  '高利率 → 长久期资产折现率抬升 → 远期盈利赛道（AI/算力/创新药）杀估值 → '
                  '成长股权重高的指数跌幅放大（创业板 −4.37% / 恒科 −5.03%）；'
                  '② **A股 的特殊性**：10/21 隔夜美股是涨的（纳指 +1.05%），但 **A股 与港股 未跟随** → '
                  '**「外盘好 → A股好」的简单映射本档失效**，说明内因为主；'
                  '③ **油价二次冲击**：沙特 Shaybah 油田遭无人机袭击、布伦特升至 110 美元附近 → '
                  '**通胀黏性 → 利率更久** 的正反馈，是本档新增的边际变量（10/21 尚未定价）；'
                  '④ **判读纪律**：以上均属**宏观外生变量**，不构成对任何单一赛道的加减仓依据。'),
         source='凤凰网财经（亚太股市集体大跌）/ 每日经济新闻（全球利率与油价）',
         source_url='https://finance.ifeng.com/c/8xQkC1HD7J9'),

    dict(track='恒生科技', category='行业事件类', sentiment='利空', strength=85, direction='利空',
         volatility='高', confidence=93,
         brief='恒科3793.93跌5.03%·创2024年9月来新低',
         title='🔴 **恒生科技收盘 3,793.93（−5.03%），创 2024 年 9 月 25 日以来新低，较 2025 年 10 月高点回撤 43%**；恒指 −3.03% 报 22,934.68（跌 717.19 点）、恒生国企 −3.20% 报 7,689.19；主板成交 2,560.51 亿港元；**联想集团 −10%、华虹宏力 −9%、智谱 −7%、MiniMax −6%（跌破发行价）、网易/中芯国际/阿里巴巴均 −6% 以上**',
         summary=('**本档最重条目 —— 恒科「三线同破」在收盘口径上全部成立，且跌幅为十月以来最大。** ① **破位读数**：'
                  '距 4,250 为 **−10.7311%**（10/21 −6.0054%，单日走阔 4.73pct）、距 4,000 为 **−5.1517%**、'
                  '**距 3,950 为 −3.9511%、距 3,800 为 −0.1597%** → **4,000 与 3,950 两条线同日收盘失守**；'
                  '② **形态 = 低开低走、收在日内次低**（开 3,949.02 即已 −1.15%，高 = 开盘价，低 3,781.15，收盘 3,793.93）→ '
                  '**全日无一次有效反抽**，与 10/21「高开低走」不同（本档连「高开」都没有）；'
                  '③ **归因可拆到个股**：阿里 −6.17%、网易 −6.32%、中芯 −6.49%、比亚迪股份 −5.34%、'
                  '美团 −4.55% → **「中国资产折价 + 全球成长股杀估值」双杀**，非单一公司事件；'
                  '④ **纪律**：按 §3.114c「同日不重复触发」，本档**只按 3,950 线建 −0.5% 预案、动作 0 元**，'
                  '3,800 破位仅登记，下一参考位下移至 **3,700（距 +2.5386%）**。'),
         source='中新经纬（恒生科技指数跌5%）/ 每日经济新闻（港股黑色星期四）/ 本地新浪 hq 直取',
         source_url='https://www.jwview.com/jingwei/kb/pc/10-22/239636.shtml'),

    dict(track='恒生科技', category='行业事件类', sentiment='利空', strength=74, direction='利空',
         volatility='中', confidence=90,
         brief='南向净卖出92亿·连续第7日·沽股交税传闻',
         title='🔴 **南向资金 10/22 净卖出港股超 92 亿港元 → 连续第 7 个交易日净卖出**（10/21 为 44 亿，本档规模翻倍）；市场同时流传「沽股交税」未证实传闻，多个巨头单日被净卖出超 10 亿港元',
         summary=('**「南向承接」假设彻底破产 —— 连续 7 日净卖出是本季最长记录。** ① **规模递进**：'
                  '10/20 −17 亿 → 10/21 −44 亿 → 10/22 −92 亿，**流出在加速而非收敛**；'
                  '② **制度性变量（本档新增）**：市场讨论「跨境券商存量账户单向卖出（只可卖不可买）」政策预期，'
                  '叠加 **10/22 是离岸信托补税 90 天窗口截止日** → **技术性抛压与政策性抛压同日落点**，'
                  '**不排除 10/23 起抛压自然衰减**，但**属推测、不作判据**；'
                  '③ **对组合的含义**：港联系三层当日合计 **−1,695.96 元**（纯恒科 −770.28 / 中概 −419.13 / '
                  '宽基恒生系 −506.55），**三层同向为负且纯恒科最重**；'
                  '④ **纪律**：南向流向只作风险偏好读数，**不构成加仓依据**（接飞刀式抄底明确禁止）。'),
         source='每日经济新闻（南向净卖出超92亿）/ 同花顺（港股暴跌的真相）/ 凤凰网财经（补税窗口）',
         source_url='https://www.nbd.com.cn/articles/2026-10-22/4612619.html'),

    dict(track='A股医药', category='行业事件类', sentiment='利空', strength=72, direction='利空',
         volatility='高', confidence=91,
         brief='CRO-4.96%·凯莱英逼近跌停·近岸蛋白-16%',
         title='🔴 **CRO/创新药午后持续下挫：CRO 板块收 −4.96%、创新药 −3.20%、医药生物 −2.69%（中证全指医药卫生 −2.19%）；凯莱英 −8.26%（盘中逼近跌停）、近岸蛋白 −16.20%、药明康德 A −4.10% / H −6.02%、恒瑞 −2.91%、百济神州 −3.61%**',
         summary=('**本档医药腿暴跌的直接读数，也是「反向兑现线」第 4 次触发。** ① **板块代理（四口径均值）= −1.895%** '
                  '（中证医药 −1.96% / 中证医疗 −1.74% / 医疗ETF −1.81% / 医药ETF −2.07%）→ **≤ −1.5% 阈值成立**；'
                  '② **但「无新增行业利空」是卖方与媒体的共同结论** —— 药财社明确「10/22 未见医药行业层面新的重大利空，'
                  '下跌更多跟随市场风险偏好回落、延续前期强势股调整」→ **归因为 β 而非 α**；'
                  '③ **结构分化仍在**：医美逆势（锦波生物 +6.31%）、百利天恒 +0.36%、艾力斯 −0.05% 抗跌 → '
                  '**不是全板块资金撤离**；'
                  '④ **组合实测**：A股医药腿 −1,305.52 元（−1.576%），主动基放大效应显著（161616 −3.49%、'
                  '000727 −2.13%、001180 −2.08% vs 板块 −1.895%）→ **与 10/22 盘中的 β>1 判断一致**。'),
         source='财联社（创新药CRO持续下挫，2026-10-22）/ 新浪财经转载 / 药财社收评（板块归因）',
         source_url='https://finance.sina.com.cn/roll/2026-10-22/doc-iniwarrm5136637.shtml'),

    dict(track='A股医药', category='行业事件类', sentiment='中性', strength=58, direction='中性',
         volatility='中', confidence=86,
         brief='医药无新增利空·纯β下跌·主力净流出48亿',
         title='🟡 **医药板块归因：10/22 无行业新增重大利空，医药生物板块主力资金净流出 48.16 亿元（CRO −14.03 亿元 / 创新药 −40.49 亿元）；中证全指医药卫生此前反弹 1.09% 未能延续，10/21 已小幅收跌**',
         summary=('**「反向兑现线」第 4 次触发的定性判据 —— 是 β 不是 α。** ① **资金面**：医药生物主力净流出 48.16 亿元、'
                  '流出占比 15%（流入 13%）→ **净流出但非恐慌式**（对比 10/21 生物医药主力净流出 3.42 亿元，本档放大 14 倍，'
                  '但成交额同步放大）；② **时间序列**：10/12-10/16 医疗服务子板块累计 −9%、CXO 领跌，'
                  '**本轮下跌已是第 2 周，非本日突发**；③ **对纪律的含义**：该线**本季 4 次触发、前 3 次次日全部转正**，'
                  '**判别力接近零** → 本档只按剧本建案、**明确标注低置信度**，须 10/23 盘前复核；'
                  '④ **不构成加仓依据**：医药敞口 39.09%、距 40% 仅 0.91pct，门槛收益率 +3.90%（两腿同涨）/ '
                  '+6.85%（仅 A股医药）→ **加仓空间几乎封死**。'),
         source='药财社（A股医药随大盘下跌）/ 东方财富板块资金流（CRO/创新药/医药生物）',
         source_url='http://mp.weixin.qq.com/s?__biz=Mzk0MzY4MjA0MA==&mid=2247502952&idx=2&sn=c7bb11b49e6c8eff2ce3c849b9a519d9'),

    dict(track='A股医药', category='行业事件类', sentiment='利多', strength=62, direction='利多',
         volatility='高', confidence=88,
         brief='ESMO 10/23开幕·29项中国研究入选LBA创新高',
         title='🟢 **ESMO（欧洲肿瘤内科学会年会）10/23-27 召开：29 项中国创新药研究入选最新突破性摘要（LBA），数量创历届新高，其中 5 项进入最高规格主席研讨会环节**',
         summary=('**未来 5 个交易日医药腿的唯一确定性催化 —— 但本档不得提前定价。** ① **量级**：29 项 LBA 为历届最高、'
                  '5 项主席研讨会 = **学术认可度高**，但**会前阵容 ≠ 临床数据**，读数 10/23 起才陆续释放；'
                  '② **映射路径**：创新药/生物科技为主，**对组合的传导偏「情绪 + 估值」而非「当期利润」** —— '
                  '持仓中医美股（002708 / 161616 / 000727 / 001180 / 001551）合计 26,004 元以上，'
                  '**是唯一可能受益的方向**；③ **反向风险**：10/22 港股创新药已先跌（恒生创新药 −6.35%、'
                  '康方 −9.59%、信达 −8.42%、药明生物 −8.38%）→ **会前预期已被大幅压低**，'
                  '**「数据好也只是修复、不是突破」**；④ **纪律**：**不因会前预期加仓**（敞口 39.09% 已近上限）。'),
         source='药财社（ESMO 29项中国研究入选）/ 财联社（会期确认）',
         source_url='http://mp.weixin.qq.com/s?__biz=Mzk0MzY4MjA0MA==&mid=2247502952&idx=2&sn=c7bb11b49e6c8eff2ce3c849b9a519d9'),

    dict(track='A股医药', category='行业事件类', sentiment='利空', strength=66, direction='利空',
         volatility='高', confidence=90,
         brief='恒生医疗-5.65%·港股创新药-6.35%·连续3日逆势后全线跌',
         title='🔴 **港股医药跌幅显著深于 A股：恒生医疗保健 −5.65%（3,457.82）、恒生创新药 −6.35%；此前连续 3 个交易日逆市上涨的港股通创新药指数本档全线收跌 —— 药明生物 −8.38%、康方生物 −9.59%、信达生物 −8.42%、乐普生物 −10.29%、再鼎医药 −9.81%、映恩生物 −10.19%**',
         summary=('**港股医药是「弹性放大器」而非独立行情。** ① **三日反弹一日回吐**：乐普生物两日前因 ESMO 消息涨超 10%，'
                  '**两日内基本回吐** → **事件驱动型涨幅在风险偏好收缩时不具持续性**；'
                  '② **A/H 分化不可一概而论**：药明康德 H −6.02% > A −4.10%，但百济神州 A −3.61% > H −2.94% → '
                  '**「港股更弱」是板块层面结论，不能外推到每家公司**（§3.114d 同型纪律）；'
                  '③ **对组合的映射路径**：组合**不直接持有港股医药**，但经 `000071`（恒生ETF联接，宽基层）'
                  '与 `012348`（恒科）间接受影响 —— 港股医药不在恒科成分主导中，**该条对本档损益的贡献近似为 0**，'
                  '**只作风险偏好读数**。'),
         source='药财社（港股医药全线收跌）/ 每经（医药股走低）',
         source_url='https://www.nbd.com.cn/articles/2026-10-22/4612619.html'),

    dict(track='大消费', category='行业事件类', sentiment='利空', strength=58, direction='利空',
         volatility='中', confidence=88,
         brief='白酒持续走低·汾酒-1.81%·皇台跌停·中证消费-0.42%',
         title='🔴 **白酒板块持续走低：山西汾酒 −1.81% 报 108.64 元（5 日 −6.43%、年初至今 −34.21%）、皇台酒业 −10.00% 跌停、金种子酒 −8.70%；中证消费 −0.42% 报 12,248.57（相对抗跌）、食品饮料 −0.43%、大消费 −1.49%**',
         summary=('**大消费是本档唯一「跑赢大盘」的权益腿（−0.774% vs 上证 −1.48%）—— 防御属性首次显现。** ① **反差读数**：'
                  '中证消费 −0.42% 而创业板 −4.37%，**差异 3.95pct** → 与 10/21「消费是最大拖累（−1.01%）」**完全反转**；'
                  '② **腿内结构**：白酒（汾酒 −1.81%）拖累 but 消费ETF −0.46%、519915 净值 −0.84%、'
                  '000248 −0.40%、000968 −1.89%、004424 −2.27% → **整体跌幅小于成长腿**；'
                  '③ **防线读数**：中证消费距 12,100 下沿 **+1.2279%**（10/21 为 +1.6536%，本档收窄 0.4257pct）→ '
                  '**连续 2 日收窄、安全垫只剩 1.23pct**，**须在 10/23 起逐日复核**；'
                  '④ **不加仓**：白酒动销下滑 + 三季报强分化出清仍在，**茅台三季报 10/31 是唯一硬验证**。'),
         source='中金在线（10/22 白酒板块持续走低）/ 东方财富板块行情 / 本地新浪 hq 直取',
         source_url='http://mp.cnfol.com/32038/article/1792584409-142769744.html'),

    dict(track='大消费', category='宏观类', sentiment='利空', strength=55, direction='利空',
         volatility='中', confidence=84,
         brief='9月社零+1.1%·地产投资-20.6%·需求端仍承压',
         title='🟡 **1-9 月社会消费品零售总额同比增长 1.1%、房地产开发投资同比下降 20.6%** → 经济运行呈「生产相对较强、部分需求与投资领域承压」格局；中信建投解读金融街论坛时指出「政策更重视金融基础制度而非短期总量刺激」',
         summary=('**消费腿的宏观底色 —— 弱而不崩，因此不构成加仓也不构成清仓理由。** ① **社零 +1.1% 是「低位正增长」**，'
                  '解释了白酒/家电等可选消费为何持续弱势（**分母端无扩张**）；'
                  '② **政策范式已变**：从「强刺激」转向「结构性托底 + 制度建设」→ **不应期待消费板块出现政策驱动的 β 行情**；'
                  '③ **对组合的映射**：大消费 20.27% 权重、−579.47 元（−0.774%）**已是本档表现第二好的权益腿**，'
                  '**「弱宏观 + 防御属性」在本档同时成立**，无需调整；'
                  '④ **纪律**：月度总量数据（社零）与价格带结构（白酒批价）**不可互相验证**（§3.110 条款同型）。'),
         source='中信建投（联合解读2026金融街论坛，含 9 月经济数据）/ 同花顺财经转载',
         source_url='https://m.10jqka.com.cn/20261022/c680972456.shtml'),

    dict(track='其他/宽基', category='政策类', sentiment='利多', strength=66, direction='利多',
         volatility='中', confidence=88,
         brief='金融街论坛闭幕·政策利率换锚·非银流动性工具',
         title='🟢 **2026 金融街论坛年会（10/19-10/22）闭幕：央行宣布研究将公开市场主要操作期限由 7 天切换至隔夜（隔夜回购利率将成为主要政策利率）、设立应对非银机构大额赎回的流动性支持工具、扩大 SLF 适用机构范围、推动银行间与交易所债市互联互通；证监会 10/19 同意首批 18 只主动 ETF 注册**',
         summary=('**本档唯一的政策级利多，但收盘已被市场「无视」。** ① **政策量级**：'
                  '「政策利率换锚」被华泰/中金解读为**利率中枢实质性下移、具降息效果**，但**中金同时提示「并非直接释放总量宽松信号」** → '
                  '**不能按「降息」定价**；② **稳市工具箱**：非银大额赎回流动性支持工具 = **针对「赎回—抛售负向循环」的定向工具**，'
                  '与 10/22「近 5,000 股下跌 + 放量」的场景**高度对应**，**属中期利好、非当日催化**；'
                  '③ **市场反应的事实**：论坛 10/19-10/22 期间沪指累计 −1.37%（本周），**政策未阻止下跌** → '
                  '**「政策底 ≠ 市场底」再次验证**；④ **纪律**：**不据政策预期加仓**（盘前档已定「只看量化表述」）。'),
         source='中国新闻网（一行两局一会集体发声）/ 中国产业经济信息网（央行四项举措）/ 中信建投解读',
         source_url='https://m.chinanews.com/wap/detail/chs/zw/10718617.shtml'),

    dict(track='其他/宽基', category='政策类', sentiment='中性', strength=52, direction='中性',
         volatility='低', confidence=82,
         brief='国新办"十五五"商务发布会·无量化新增',
         title='🟡 **国新办 10/22 就「推进十五五时期商务高质量发展」举行新闻发布会**（盘前档已列为 P1 观察项）；同期披露 2026 年前三季度期货市场新增客户 91 万个、同比增长 41%',
         summary=('**盘前档 P1 事项的收盘核销 —— 未见可量化增量。** ① **观察口径**：盘前档明确「只看扩内需/服务消费的**量化表述**，'
                  '无量化则本档结论不变、不据表述调仓」→ **本档核销结论 = 无量化增量、结论不变**；'
                  '② **市场反应**：发布会当日消费板块（中证消费 −0.42%）**未出现脉冲**，与「无实质增量」一致；'
                  '③ **期货新增客户 +41%** 属**市场结构指标**（增量参与者），与短期指数方向无稳定关系，**只作登记**；'
                  '④ **纪律**：政策类新闻一律**先判「是否含量化工具/金额/时点」，再判方向**，不得仅凭标题定利多。'),
         source='国新办发布会（10/22）/ 中国期货市场监控中心（前三季度新增客户）',
         source_url='http://mp.weixin.qq.com/s?__biz=MzkyMzc0NjExMA==&mid=2247484416&idx=1&sn=c8e9d25d5c76475651835f46870b4006'),

    dict(track='其他/宽基', category='宏观类', sentiment='利空', strength=64, direction='利空',
         volatility='高', confidence=86,
         brief='沙特油田遇袭·布油110美元·通胀黏性',
         title='🔴 **沙特阿美 Shaybah 油田遭无人机袭击（2 人死亡、生产未受影响），布伦特 12 月合约升至 109.98 美元/桶、WTI 98.02 美元；美国务院已令驻沙特非紧急人员撤离；美以被指计划中期选举后再次打击伊朗**',
         summary=('**本档新增的「通胀—利率」正反馈变量，10/21 尚未定价。** ① **传导链**：油价 → 通胀黏性 → '
                  '「高利率维持更久」→ 长久期资产折现率抬升 → **港股/A股成长股承压**，与本档跌幅结构一致；'
                  '② **量级判断**：Shaybah 生产未受影响 → **供给冲击有限，属「风险溢价」而非「供给缺口」**，'
                  '**不可按「油荒」定价**；③ **对组合的直接影响**：组合**无能源敞口**（中证环保 −1.48% 非能源），'
                  '**只有间接的折现率影响**；④ **尾部风险**：若中期选举后冲突升级，油价二次跳升将同时压制消费（成本）与成长（估值），'
                  '**这是「消费 + 成长」双杀的唯一宏观路径** → 须纳入风险提示。'),
         source='财经早报（2026-10-22，沙特 Shaybah 油田遇袭）/ 凤凰网财经（布油与美债）',
         source_url='http://mp.weixin.qq.com/s?__biz=MzkyMzc0NjExMA==&mid=2247484416&idx=1&sn=c8e9d25d5c76475651835f46870b4006'),

    dict(track='其他/宽基', category='行业事件类', sentiment='中性', strength=50, direction='中性',
         volatility='低', confidence=85,
         brief='银行逆势创新高·工行市值3.06万亿',
         title='🟡 **银行股逆势走强：工商银行盘中涨 0.83% 报 8.58 元、总市值 3.06 万亿元创历史新高；建设银行同步创盘中新高**；同期证券公司 −0.58%、中证金融 −0.45% 相对抗跌',
         summary=('**「资金从成长切向红利」的盘面证据。** ① **相对强度**：银行创新高 vs 创业板 −4.37% → '
                  '**极端的风格分化（单日 5pct 以上）**；② **对组合的含义（重要）**：组合宽基腿持有沪深300 联接（000051 / 110020）'
                  '**含银行权重但不足**，且**不持有个股银行** → **「护盘红利」只吃到一部分**，'
                  '**这是宽基腿 −1.982% 弱于上证 −1.48% 的结构原因之一**（另一原因是广联达 −2.34%）；'
                  '③ **不可外推**：银行创新高是「避险 + 高股息」的资金行为，**与「经济复苏」叙事相反** → '
                  '**不能据此判断市场见底**；④ **纪律**：不追高股息（组合已有 515180 红利 ETF，−1.69%，'
                  '本档**红利反而下跌** → 「红利避险」在 A股 内部也不成立）。'),
         source='凤凰网财经（工商银行创历史新高）/ 同花顺 A股收评',
         source_url='https://finance.ifeng.com/c/8xQkC1HD7J9'),

    dict(track='美股标普医药', category='行业事件类', sentiment='中性', strength=55, direction='中性',
         volatility='中', confidence=88,
         brief='QDII 10/21净值出库-0.19%·核销挂账-116.32元',
         title='🟡 **QDII 腿净值出库：`000369` / `016280` 10/21 净值均为 −0.19%（2.6780 / 2.6320）→ 13:45 档登记的「US 10/21 挂账区间 −222.85 元 ~ −148.56 元」本档按真实净值核销 −116.32 元**；传导系数 0.4657 / 0.4740，**低于 0.60 下界**',
         summary=('**本档唯一的「正向意外」—— 亏损小于预告区间下界。** ① **对账**：预告区间按 IYH −0.40% × 弹性 0.60~0.90 '
                  '得 −222.85 ~ −148.56 元，**实测 −116.32 元 优于最优端 −148.56 元**（差 32.24 元）；'
                  '② **越界方向**：**首次出现「下跌段实际跌幅小于预告下界」** → 说明 QDII 对 IYH 的传导在**下跌段更钝**'
                  '（此前上涨段系数 0.84~0.86、下跌段 0.47）→ **系数存在「方向不对称」，单点系数不可用**；'
                  '③ **纪律**：该腿 **T+2 确认、T+3 到账**，且**净值日 ↔ 美股交易日映射仍未确定** → '
                  '**一切基于当日读数的加减仓动作不可执行**（`new_buy = 0` / `reduce = 0`）；'
                  '④ **US 10/22 尚未开盘**（北京 20:00 = 美东 08:00）→ 本档只登记新窗口、不给数值。'),
         source='天天基金 F10（000369 / 016280 净值）/ 本地 fund_nav.csv 归档 / 盘中档挂账登记',
         source_url='https://fundf10.eastmoney.com/jjjz_000369.html'),

    dict(track='美股标普医药', category='宏观类', sentiment='利空', strength=58, direction='利空',
         volatility='高', confidence=82,
         brief='纳指期货盘中跌超1%·美债5%上方·成长承压',
         title='🔴 **美股 10/22 盘前：纳指期货盘中跌超 1%；10 年期美债收益率维持 5% 上方（9 月以来最高触及 5.36%）、30 年期 5.73%** → 全球成长资产继续承压；美股 10/22 正式交易时段（北京 21:30 开盘）**本档尚未开始**',
         summary=('**QDII 腿「下一段挂账」的方向预告（只给方向、不给数值）。** ① **口径**：US 10/22 收盘成型于北京 10/23 04:00，'
                  '**晚于本档** → 按 §3.120c **只登记窗口、不给区间**，避免「用未发生的行情算损益」；'
                  '② **方向**：纳指期货 −1% + 美债 5% 上方 → **美股成长股偏弱**，XLV 作为防御性板块**可能相对抗跌**'
                  '（10/21 XLV −0.49% vs 纳指 +1.05% 已示相对弱势中的「不同步」）；'
                  '③ **对组合的含义**：美股标普医药占 16.85%、当日已核销 −116.32 元，'
                  '**该腿是本季唯一正贡献来源（10/19-10/21 累计 +2,722.75 元以上），不宜在数据盲区操作**；'
                  '④ **纪律**：**不预测 QDII 净值，只登记行情**；系数 pending 期间**区间绝对值不可作仓位依据**。'),
         source='凤凰网财经（美债收益率与纳指期货）/ 本地 indices.csv（US 10/21 归档）',
         source_url='https://finance.ifeng.com/c/8xQkC1HD7J9'),

    dict(track='恒生科技', category='行业事件类', sentiment='利空', strength=62, direction='利空',
         volatility='中', confidence=84,
         brief='跨境券商存量账户单向卖出预期·补税窗口10/22截止',
         title='🟡 **港股资金面的两项制度性变量同日落地：① 市场对「跨境券商存量账户只可卖出、不可新增买入」政策预期升温 → 内资只能走港股通/QDII 合规通道，新增买盘补充变慢；② 10/22 为离岸信托补税 90 天窗口截止日 → 技术性抛压集中释放**',
         summary=('**这是本档「明天可能不再更差」的唯一论据 —— 但只作观察、不作交易依据。** ① **机制**：'
                  '两项变量都是**「一次性时点型」**而非「持续性」→ 时间窗口过去后抛压**理论上自然衰减**；'
                  '② **反面证据**：南向已连续 7 日净卖出且规模递增（17 → 44 → 92 亿），**说明抛压并未因「窗口临近结束」而减弱**，'
                  '本档**不支持「利空出尽」判断**；③ **不可证伪性警告**：「沽股交税」为**未证实传闻**，'
                  '按 §3.167a「日历/事实错误 + 条件命中」教训，**传闻类信息一律不得作为触发条件**；'
                  '④ **纪律**：恒科减配按**价格线（3,950）**而非「消息面」执行，本档动作口径不变。'),
         source='同花顺（港股暴跌的真相：跨境政策与补税窗口）/ 凤凰网财经（补税窗口 10/22 截止）',
         source_url='https://stock.10jqka.com.cn/hks/20261022/c680989324.shtml'),

    dict(track='A股医药', category='业绩类', sentiment='中性', strength=54, direction='中性',
         volatility='中', confidence=80,
         brief='三季报密集期·迪安诊断Q3净利+438%',
         title='🟡 **三季报密集披露期：迪安诊断第三季度净利润 2.50 亿元、同比增长 438.03%（医药流通/ICL 方向）；同期 A股 已披露公司业绩分化显著（北纬科技前三季净利 +2,246.41%、建新股份 +1,555.93%）**',
         summary=('**医药腿「分子端」的首个正面样本，但不足以对冲估值杀。** ① **个例 vs 板块**：迪安诊断 +438% 属**低基数 + '
                  'ICL 业务修复**，**不代表板块整体盈利拐点**；② **本档医药腿仍 −1.31% 量级亏损** → '
                  '**「业绩好 + 股价跌」是典型的杀估值环境**，与 10/21「宁德时代增收不增利」同构（业绩与股价可短期脱钩）；'
                  '③ **对 10/31 茅台三季报的含义**：三季报密集期意味着**个股风险集中于未来 7 个交易日**，'
                  '组合持仓的主动基（002708 / 161616 / 000727）**存在单日 ±2% 以上的净值跳空风险**；'
                  '④ **纪律**：**不因单季业绩预告调整赛道权重**（业绩类事件的历史 3/5/10 日窗口统计置信度本轮偏低）。'),
         source='财经早报（2026-10-22 三季报速览）/ 公司公告',
         source_url='http://mp.weixin.qq.com/s?__biz=MzkyMzc0NjExMA==&mid=2247484416&idx=1&sn=c8e9d25d5c76475651835f46870b4006'),
]


def to_news(it):
    return {'track': it['track'], 'category': it['category'], 'sentiment': it['sentiment'],
            'direction': it['direction'], 'strength': it['strength'], 'confidence': it['confidence'],
            'volatility': it['volatility'], 'brief': it['brief'], 'title': it['title'],
            'summary': it['summary'], 'window': WIN, 'score': it['strength'],
            'source': it['source'], 'source_url': it['source_url']}


def to_sent(it, i):
    return {'idx': i, 'title': it['title'], 'track': it['track'], 'window': WIN,
            'sentiment': it['sentiment'], 'strength': it['strength'], 'confidence': it['confidence'],
            'direction': it['direction'], 'volatility': it['volatility'], 'brief': it['brief'],
            'source_url': it['source_url'], 'category': it['category'],
            'degraded': True, 'degrade_reason': DEG}


close_news = [to_news(x) for x in ITEMS]
assert all(n['source_url'].startswith('http') for n in close_news), '存在无 source_url 的条目'
assert all(n['window'] == WIN for n in close_news), 'window 缺失（§3.103 复发守卫）'

json.dump(close_news, open(os.path.join(NEWS, 'news-close-20261022.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)

# ---- 合并当日新闻 ----
p_news = os.path.join(NEWS, 'news-2026-10-22.json')
alln = json.load(open(p_news, encoding='utf-8'))
before = len(alln)
exist_titles = {n['title'][:60] for n in alln}
added_n = [n for n in close_news if n['title'][:60] not in exist_titles]
alln.extend(added_n)
json.dump(alln, open(p_news, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

# ---- 合并当日情绪 ----
p_sent = os.path.join(NEWS, 'sentiment-2026-10-22.json')
s = json.load(open(p_sent, encoding='utf-8'))
ex_s = {x['title'][:60] for x in s['items']}
add_s = [to_sent(x, len(s['items']) + k) for k, x in enumerate(ITEMS) if x['title'][:60] not in ex_s]
s['items'].extend(add_s)
s['count'] = len(s['items'])
s['degraded_items'] = len(s['items'])
s['degraded_batches'] = s.get('degraded_batches', 0) + 1
s['degradation_reason'] = 'HTTP 402'
s['mean_strength'] = round(sum(x['strength'] for x in s['items']) / len(s['items']), 2)
s['net_nominal'] = round(sum((x['strength'] if x['direction'] == '利多' else -x['strength'] if x['direction'] == '利空' else 0)
                             for x in s['items']), 2)
bt = defaultdict(lambda: {'n': 0, 'net': 0.0, 'strength_sum': 0})
for x in s['items']:
    v = bt[x['track']]
    v['n'] += 1; v['strength_sum'] += x['strength']
    v['net'] += (x['strength'] if x['direction'] == '利多' else -x['strength'] if x['direction'] == '利空' else 0)
s['by_track'] = {k: {'n': v['n'], 'net': round(v['net'], 2),
                     'mean_strength': round(v['strength_sum'] / v['n'], 2)} for k, v in bt.items()}
json.dump(s, open(p_sent, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

# ---- 本档窗口聚合 ----
win_items = [x for x in s['items'] if x['window'] == WIN]
assert len(win_items) == len(ITEMS), f'本档窗口条目 {len(win_items)} != {len(ITEMS)}'
wt = defaultdict(lambda: {'n': 0, 'net': 0.0, 'sum': 0})
for x in win_items:
    v = wt[x['track']]
    v['n'] += 1; v['sum'] += x['strength']
    v['net'] += (x['strength'] if x['direction'] == '利多' else -x['strength'] if x['direction'] == '利空' else 0)
by_track = {k: {'n': v['n'], 'net_score': round(v['net'] / v['n'], 2),
                'mean_strength': round(v['sum'] / v['n'], 2)} for k, v in wt.items()}

pc = json.load(open(os.path.join(HIST, 'portfolio_close_20261022.json'), encoding='utf-8'))
total = pc['total_mv']
w = {k: v['mv'] / total for k, v in pc['tracks'].items()}
expo_net = round(sum(by_track[t]['net_score'] * w[t] for t in by_track if t in w) / sum(w[t] for t in by_track if t in w), 4)
agg = {'date': TODAY, 'window': WIN, 'count': len(win_items),
       'annotation_mode': 'rule_table_degraded', 'degraded_items': len(win_items),
       'degradation_reason': DEG,
       'by_track': by_track,
       'mean_strength': round(sum(x['strength'] for x in win_items) / len(win_items), 2),
       'net_nominal': round(sum((x['strength'] if x['direction'] == '利多' else -x['strength'] if x['direction'] == '利空' else 0)
                                for x in win_items), 2),
       'direction_count': {'利多': sum(1 for x in win_items if x['direction'] == '利多'),
                           '利空': sum(1 for x in win_items if x['direction'] == '利空'),
                           '中性': sum(1 for x in win_items if x['direction'] == '中性')},
       'exposure_weighted_net': expo_net,
       'exposure_weight_note': '按 10/22 收盘赛道权重加权；未归类赛道（无）不参与',
       'source_url_coverage': f"{sum(1 for x in win_items if x['source_url'])}/{len(win_items)}",
       'window_coverage': f"{sum(1 for x in win_items if x.get('window'))}/{len(win_items)}"}
json.dump(agg, open(os.path.join(HIST, 'sentiment_agg_20261022_close.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)

print(f'news 当日：{before} → {len(alln)}（本档 +{len(added_n)}）')
print(f'sentiment 当日：{s["count"]} 条；本档窗口 {len(win_items)} 条；均值强度 {agg["mean_strength"]}')
print(f'名义净 {agg["net_nominal"]} / 暴露加权 {expo_net}')
print('方向分布', agg['direction_count'])
print('分赛道净分：', {k: v['net_score'] for k, v in by_track.items()})
print('source_url 覆盖', agg['source_url_coverage'])
