# -*- coding: utf-8 -*-
"""盘前档 2026-08-19 新闻构建 + DeepSeek 情绪标注（窗口 8/18 18:00 - 8/19 07:30）"""
import json, os, sys, urllib.request

BASE = '/Users/jieyang/Documents/WealthHub'
NEWS_DIR = os.path.join(BASE, 'data/processed/news')
DATE = '2026-08-19'

# 手动整理的有效增量新闻（track 用赛道名，规避关键词分类器误归 §3.17）
news = [
    {
        "track": "宏观", "category": "宏观类",
        "title": "隔夜美股三大指数收跌（标普7,691.76 -0.69%、纳指26,289.71 -1.33%、道指53,343.40 -0.22%）；费城半导体指数暴跌5%（存储/光通信/AI云全线大跌：闪迪-9.01%、美光-7.02%、Coherent-12%+、Lumentum-9%）；但医疗板块+1.59%领涨",
        "summary": "8/18美股收盘：标普500 -0.69%报7691.76（连续第三日回调）、纳指-1.33%、道指-0.22%。费城半导体指数暴跌5%：存储（闪迪-9.01%/SK海力士-9%+/希捷-9%+/美光-7.02%/西数-7.43%）、光通信（Coherent-12%+/Lumentum-9%+/康宁-7.68%）、AI云服务（CoreWeave-12%+）全线大跌；科技七巨头多数下跌（Meta-4.45%/英伟达-2.34%），苹果+1.49%逆势。标普11大板块七跌四涨，能源+1.79%与医疗+1.59%领涨。纳斯达克金龙指数-1.01%（百度-12.73%）。",
        "source": "WebSearch",
        "source_url": "https://www.stcn.com/article/detail/4085455.html"
    },
    {
        "track": "宏观", "category": "宏观类",
        "title": "全球债券收益率飙升：美国30年期国债收益率盘中创2007年以来新高（近5.30%）、10年期创2025年1月来高位；日本10年期创30年新高——跨资产重新定价压制科技股估值",
        "summary": "8/18全球债券市场收益率普遍走高：美30年期国债收益率盘中升至2007年以来最高水平（近5.30%）、10年期升至2025年1月以来高位；日本、德国、法国长期国债收益率也处多年高位。美债收益率上升提高股票估值压力，尤其对科技和成长型股票形成较大压制。洛根资本警告推动债券收益率走高的因素短期难以消退，随着利率压力累积，股票市场未来或面临抛售风险。",
        "source": "WebSearch",
        "source_url": "https://www.cnfin.com/gs-lb/detail/20260819/4456976_1.html"
    },
    {
        "track": "宏观", "category": "宏观类",
        "title": "国际油价续涨：WTI 84.94(+0.52%)/布伦特91.02(+0.17%)；阿联酋宣布暂停与伊朗一切贸易金融往来，霍尔木兹海峡僵局持续、美伊谈判窗口期满无实质进展",
        "summary": "受美国与伊朗谈判进展不确定以及市场对能源供应和航运风险的担忧影响，国际油价8/18继续上涨：WTI 84.94（+0.52%）、布伦特91.02（+0.17%）。地缘层面：阿联酋宣布暂停与伊朗一切贸易金融往来（每经早参），伊朗政策转'全面进攻性'后霍尔木兹海峡航运量仅战前5%，特朗普此前称不寻求延长谅解备忘录——地缘风险溢价持续。",
        "source": "WebSearch",
        "source_url": "https://so.html5.qq.com/page/real/search_news?docid=70000021_5606a84d84706152"
    },
    {
        "track": "宏观", "category": "宏观类",
        "title": "美联储9月加息概率骤降至~33%（CME：9月维持不变概率65%、加息35%）；FOMC 7月会议纪要8/20凌晨02:00公布；美元三连跌至三个月低点（DXY 99.5）、新兴市场货币指数创历史新高",
        "summary": "7月CPI（3.4%）/PPI（4.7%）/零售销售（-0.6%创逾一年最大降幅）数据组合使市场对美联储9月加息预期全面瓦解：CME'美联储观察'显示9月维持利率不变概率65%、加息25BP概率35%（较7月末75%骤降）。北京时间8/20凌晨美联储将公布7月FOMC会议纪要（7/29连续第五次按兵不动3.5%-3.75%，3票反对要求加息）。美元指数三连跌至99.50附近三个月低点，新兴市场货币指数创历史新高、外资重新流入亚洲。",
        "source": "WebSearch",
        "source_url": "https://gu.qq.com/resources/shy/news/detail-v2/index.html?t=1#/index?_tentrees_trans=0&id=SN20260818094428a709356a"
    },
    {
        "track": "宏观", "category": "宏观类",
        "title": "美国7月新屋开工年化123.9万套（-12.4%，大幅低于预期135万）；独栋住宅开工80.8万套创2022年11月以来最低——地产链走弱再证经济降温",
        "summary": "美国商务部8/18盘前公布：7月新屋开工总量按年率计算123.9万套，环比下降12.4%，大幅低于市场预期的135万套；其中独栋住宅开工量下降9.9%至80.8万套，为2022年11月以来最低水平。地产数据走弱进一步印证美国经济降温，支持美联储9月按兵不动的市场预期。",
        "source": "WebSearch",
        "source_url": "https://www.cnfin.com/gs-lb/detail/20260819/4456976_1.html"
    },
    {
        "track": "恒生科技", "category": "业绩类",
        "title": "百度Q2财报暴雷：营收313亿(-4%，低于预期315.9亿)、归母净利23亿(-68%大幅低于预期)、EPS 7.22元低于预期9.84元——隔夜美股-12.73%；但AI收入占比过半、GPU云+283%、8/26审议港股双重主要上市",
        "summary": "百度8/18发布Q2财报：总营收313亿元同比-4%（低于市场预估315.9亿），归母净利润23亿元同比-68%（大幅低于预期），核心广告收入-19%、传统业务-23%——AI新业务尚未填平传统业务缺口。AI收入占比50%（连续两季过半）、AI云基础设施73亿(+50%)、GPU云+283%（连续四季度三位数增长）。隔夜美股-12.73%至90.39美元，创年内新低、2026年累计-35%。另确认8/26召开股东特别大会审议香港双重主要上市事项。恒科权重股业绩暴雷为今日港股最大个股利空。",
        "source": "WebSearch",
        "source_url": "https://usstock.jrj.com.cn/2026/08/19074058166182.shtml"
    },
    {
        "track": "恒生科技", "category": "行业事件类",
        "title": "恒生指数公司就恒生科技指数重大修订征询意见：成分股拟由30只扩容至50只，首次引入'市值+收入增长'双轨选股机制以扩大AI及先进硬件覆盖",
        "summary": "恒生指数公司发文就恒生科技指数修订方案征询市场意见：成分股拟从30只大幅扩容至50只，并首次引入'市值+收入增长'双轨选股机制，纳入更多高成长硬科技公司、扩大对AI及先进硬件覆盖。中信建投、中金认为修订将提升指数代表性与对全球配置资金的吸引力。港股反弹节奏放缓背景下（8/18恒指+0.07%/恒科-0.90%），该修订为结构性制度利好。",
        "source": "WebSearch",
        "source_url": "https://new.qq.com/rain/a/20260819A02PYT00?refer=cp_1009"
    },
    {
        "track": "恒生科技", "category": "行业事件类",
        "title": "南向资金8/18净买入超140亿港元创7月9日以来最大单日纪录；腾讯-0.90%收442.40、阿里+3.68%（财报前抢跑）、快手-1.75%；今日快手财报、8/20阿里财报密集落地",
        "summary": "8/18南向资金净买入港股超140亿港元，创7月9日以来最大单日净买入纪录；8月以来净流入规模已超270亿元。个股：腾讯控股8/18收442.40（-0.90%）、阿里巴巴-W收126.70（+3.68%领涨，财报前抢跑）、快手-W收39.38（-1.75%）。恒指收25471.15（+0.07%）主要靠阿里及医药股（药明生物+5%+/百济神州+3%）支撑；大模型概念重挫（智谱-13%/MINIMAX-4%）。本周中概财报：8/19快手、8/20阿里+网易。",
        "source": "WebSearch",
        "source_url": "https://www.stcn.com/article/detail/4085520.html"
    },
    {
        "track": "大消费", "category": "行业事件类",
        "title": "8/18飞天茅台散瓶批价约1700元（较前日再跌10元）；i茅台零售价1639（提价后）；五粮液普五批价980企稳——批价高位窄幅震荡、渠道利润薄",
        "summary": "8/18酒价跟踪：26年飞天散瓶批价约1700元（较前日-10），依然站在i茅台1639元零售价之上；i茅台平台零售价1639元（7/18提价100元后）、销售合同价1369元；自营店1753元。五粮液普五第八代980元持平、国窖1573 960元。渠道反馈：经销商卖一瓶普通飞天利润仅一两百元，转手价差约40元，渠道加价空间小——批价高位企稳但上行动能减弱，中秋动销为关键检验窗口。",
        "source": "WebSearch",
        "source_url": "https://post.m.smzdm.com/p/a82l04el"
    },
    {
        "track": "大消费", "category": "行业事件类",
        "title": "A股农业板块8/18掀涨停潮（24股涨停：金健米业/农发种业2连板、大北农20CM首板）；摩根大通警告下一轮全球粮食危机或于明年爆发；农林牧渔+3.63%领涨两市",
        "summary": "8/18农业股掀起涨停潮：种业/猪产业领涨（金健米业、农发种业2连板，万向德农、亚盛集团、登海种业涨停，罗牛山2连板，天邦食品涨停），板块32只成分股中15只涨停、将近一半；农林牧渔板块+3.63%领涨两市。催化=摩根大通警告下一轮全球粮食危机可能正在酝酿、或于明年爆发。资金从高位科技股流向农业等低估值防御板块，科技与传统板块形成跷跷板效应（成交2.42万亿、全市场3292跌/2121涨）。",
        "source": "WebSearch",
        "source_url": "https://caifuhao.eastmoney.com/news/20260819070906720016540?from=guba&gubaurl=aHR0cHM6Ly9ndWJhLmVhc3Rtb25leS5jb20vbGlzdCw2MDUxNzkuaHRtbA%3D%3D&name=5LiA6bij6aOf5ZOB5ZCn"
    },
    {
        "track": "大消费", "category": "行业事件类",
        "title": "今日8/19世界机器人大会在北京亦庄开幕（8/19-23，300余家参展）+ 宇树科技科创板上市（发行价150.80元、市值约610亿）——机器人产业本周最密集事件窗口",
        "summary": "2026世界机器人大会8/19-23在北京亦庄举办：300余家参展企业、2000余件展品、150余款首发新品（宇树G1/R1、优必选Walker S3、银河通用Galbot、天工2.0同台展出）。同日宇树科技科创板上市（发行价150.80元/股、市值约610亿），第二届世界人形机器人运动会8/22开幕。机器人概念8/18已提前反应（正裕工业3连板、南方精工/日丰股份涨停）——今日事件兑现日，需防利好兑现冲高回落。",
        "source": "WebSearch",
        "source_url": "https://caifuhao.eastmoney.com/news/20260819063445090068390?from=guba&gubaurl=aHR0cHM6Ly9ndWJhLmVhc3Rtb25leS5jb20vbGlzdCw2MDA0ODcuaHRtbA%3D%3D&name=5Lqo6YCa5YWJ55S15ZCn"
    },
    {
        "track": "A股医药", "category": "行业事件类",
        "title": "医疗服务板块行情升温：申万医疗服务指数8月累计+23.45%、年内+41.55%；药明康德年内+87.38%、H1净利110.8亿居首；8月来6股获融资净买入超亿元——板块盈利拐点确认",
        "summary": "证券时报：8月以来医疗服务板块加速，申万医疗服务指数月内+23.45%、年内+41.55%（百奥赛图/药康生物/万邦医药/益诺思年内翻倍、药明康德+87.38%）。政策端：2026政府工作报告首将生物医药列为新兴支柱产业、7月《国民健康'十五五'规划》全链条支持创新药。基本面：2026Q1医疗服务板块收入+3%、归母净利+17%盈利改善。融资：昭衍新药/药康生物年内融资净买入超2亿。综合半年报：8家企业H1净利破亿，药明康德110.8亿居首、康龙化成7.5亿。开源证券/中银国际均看好板块结构性复苏。",
        "source": "WebSearch",
        "source_url": "https://www.toutiao.com/article/7675462282231333410/"
    },
    {
        "track": "A股医药", "category": "政策类",
        "title": "山东省发布《医药工业'十五五'发展行动方案(征求意见稿)》：2030年营收破4000亿、创新药械上市20个以上，济南被委以重任（生物医药概念验证中心/医药大模型/AI+医药）",
        "summary": "8/18山东省工信厅发布《山东省医药工业'十五五'发展行动方案(征求意见稿)》：到2030年全省医药工业营收突破4000亿元（2025年2855亿）、创新药械上市20个以上，推动从'医药大省'向'创新型医药强省'跨越。济南被赋予多项任务（依托济南国际医学中心布局省级生物医药概念验证中心/中试基地、打造医药大模型创新平台），六大重点领域覆盖生物药/化学药/中药/医疗器械全链条。区域政策级利好，对行业景气预期有正向加持。",
        "source": "WebSearch",
        "source_url": "https://news.e23.cn/shandong/2026-08-19/2026081900005.html"
    },
    {
        "track": "美股标普医药", "category": "行业事件类",
        "title": "隔夜美股医疗板块+1.59%领涨（标普11大板块第二）：礼来+3.60%收1,225.73、艾伯维+3.43%、强生+3.33%、吉利德+3.25%、辉瑞+1.41%、安进+1.41%；IYH+1.52%收71.67",
        "summary": "8/18美股医疗保健板块+1.59%领涨（标普11大板块中仅次于能源+1.79%），在科技暴跌环境中逆势走强：礼来+3.60%收1225.73（突破1200关口）、艾伯维+3.43%、强生+3.33%、吉利德+3.25%、辉瑞+1.41%、安进+1.41%、雅培+2.09%、福泰制药+2.45%；XLV新浪源滞后至8/17（167.05 -0.19%），IYH已更新至8/18（71.67 +1.52%）——美股医药全线走强，对应QDII广发全球医疗净值预计8/20-21兑现+1.5%量级。",
        "source": "WebSearch",
        "source_url": "https://finance.jrj.com.cn/2026/08/19063058166065.shtml"
    },
    {
        "track": "美股标普医药", "category": "行业事件类",
        "title": "减肥药概念股逆势上扬：礼来+2.6%/诺和诺德+1.8%/辉瑞+1.7%；诺和诺德CEO称2030年全球减肥药市场规模将超1000亿美元、'赢家通吃'不会上演",
        "summary": "8/18美股减肥药概念逆势上涨：礼来+2.6%（收1225.73）、诺和诺德+1.8%、辉瑞+1.7%、罗氏+1.4%、安进+1.2%。诺和诺德CEO Mike Doustdar表示投资者低估了减肥药市场对差异化产品的需求，预计到2030年全球减肥药市场规模将超过1000亿美元；随着口服药等新疗法不断推出，肥胖治疗领域不会演变成诺和诺德与礼来之间'赢家通吃'的竞争。GLP-1赛道景气延续，礼来8/14减重数据后+7%创新高后高位续涨。",
        "source": "WebSearch",
        "source_url": "https://gu.qq.com/resources/shy/news/detail-v2/index.html?t=1#/index?_tentrees_trans=0&id=SN2026081822132494dd7c3e"
    },
    {
        "track": "宏观", "category": "宏观类",
        "title": "A股8/18收盘：沪指3,990.30(+0.19%)距4,000仅10点连续第二日冲关失败、创业板-0.92%、中证消费+0.89%站稳12,600；成交2.42万亿温和放量，资金从高位科技流向农业/信创等低位防御",
        "summary": "8/18 A股收盘：上证3,990.30（+0.19%，盘中最高3,992.09距4,000仅10点，连续第二日冲关失败）、深成指14,622.50（-0.56%）、创业板3,705.56（-0.92%）、科创50+0.11%、北证50+2.67%；沪深京成交2.42万亿（较前日+172.56亿）。全市场3292跌/2121涨，权重护盘掩盖多数个股疲弱。板块：农林牧渔+3.63%领涨（粮食安全24股涨停）、石油石化+1.84%、信创午后异动（诚迈20CM涨停）；综合金融-1.69%/传媒-1.54%领跌。量价背离：资金从高位科技（兆易-1.64%/长鑫-4.22%）流向农业等低估值方向。",
        "source": "WebSearch",
        "source_url": "https://caifuhao.eastmoney.com/news/20260819063445090068390?from=guba&gubaurl=aHR0cHM6Ly9ndWJhLmVhc3Rtb25leS5jb20vbGlzdCw2MDA0ODcuaHRtbA%3D%3D&name=5Lqo6YCa5YWJ55S15ZCn"
    },
]

# 写入 news JSON
news_path = os.path.join(NEWS_DIR, f'news-{DATE}.json')
if os.path.exists(news_path):
    with open(news_path, encoding='utf-8') as f:
        old = json.load(f)
    old_titles = {n['title'] for n in old}
    merged = old + [n for n in news if n['title'] not in old_titles]
    print(f'news-{DATE}.json 已存在，合并后 {len(merged)} 条')
else:
    merged = news
    print(f'新建 news-{DATE}.json，{len(merged)} 条')
with open(news_path, 'w', encoding='utf-8') as f:
    json.dump(merged, f, ensure_ascii=False, indent=1)

# ---------- DeepSeek 情绪标注 ----------
with open('/Users/jieyang/.pi/agent/auth.json') as f:
    key = json.load(f)['deepseek']['key']

prompt = f"""你是资深A股/港股投研分析师。对以下 {len(news)} 条财经新闻（日期 {DATE}）逐条输出情绪标注。

要求：
1. 每条输出 JSON 对象：sentiment(正面/中性/负面)、score(0-100 情绪分, 50中性)、strength(0-100 影响强度)、direction(利多/利空/中性)、volatility(低/中/高)、reason(一句话理由, ≤40字)
2. 严格按输入顺序输出一个 JSON 数组，不要额外文字
3. 站在个人持仓组合角度评估：组合重仓 A股医药(创新药/CXO/医疗ETF)、大消费(白酒/消费ETF)、美股标普医药(QDII)、恒生科技(腾讯/中概/恒科ETF)、宽基
4. strength 按对持仓赛道的实际影响定：政策级与基本面兑现可给 65-75；个股事件 50-60；宏观利率/油价/地缘 50-70；批价微调等边际 40-50

新闻列表：
{json.dumps([{'title': n['title'], 'summary': n['summary'][:200]} for n in news], ensure_ascii=False, indent=1)}"""

data = {
    "model": "deepseek-v4-flash",
    "messages": [{"role": "user", "content": prompt}],
    "max_tokens": 8000,
    "temperature": 0.3,
}
req = urllib.request.Request("https://api.deepseek.com/chat/completions",
    data=json.dumps(data).encode(),
    headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
with urllib.request.urlopen(req, timeout=180) as resp:
    result = json.load(resp)
content = result['choices'][0]['message']['content']
if not content:
    raise RuntimeError('DeepSeek content 为空，需重试')

# 解析（兼容模型输出前后缀文字）
s = content.find('['); e = content.rfind(']')
if s == -1 or e == -1:
    raise RuntimeError(f'解析失败，content: {content[:200]}')
senti = json.loads(content[s:e+1])
if len(senti) != len(news):
    raise RuntimeError(f'标注条数不匹配: {len(senti)} vs {len(news)}')

for n, s in zip(news, senti):
    n.update({'sentiment': s['sentiment'], 'score': s['score'], 'strength': s['strength'],
              'direction': s['direction'], 'volatility': s['volatility'], 'reason': s['reason']})
    print(f"  {n['track']:6s} {n['sentiment']}({n['score']}/{n['strength']}) {n['direction']} | {n['title'][:40]}")

with open(news_path, 'w', encoding='utf-8') as f:
    json.dump(news, f, ensure_ascii=False, indent=1)
print(f'\n情绪标注完成 -> news-{DATE}.json（{len(news)} 条）')
