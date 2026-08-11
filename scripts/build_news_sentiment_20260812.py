#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""2026-08-12 盘前档: 构建新闻 JSON + DeepSeek 情绪标注
窗口: 8/11 18:00 - 8/12 07:30
产出: news-2026-08-12.json / sentiment-2026-08-12.json
"""
import json, os, urllib.request, sys

BASE = "/Users/jieyang/Documents/WealthHub"
NEWS = os.path.join(BASE, "data/processed/news")

# ---------- 1. 新闻条目 (含 summary/source/source_url) ----------
news = [
 {
  "id": "N20260812-001", "track": "宏观", "category": "宏观类",
  "title": "隔夜美股三大指数连续第二天收跌：道指-0.34%标普-0.32%纳指-0.60% 美伊僵局施压 能源/公用事业领涨 通信服务领跌",
  "summary": "美东8/11收盘：道指53791.85(-0.34%)、标普7728.20(-0.32%)、纳指26445.45(-0.60%)，连续第二天收跌。美联储维持利率3.50%-3.75%不变但偏鹰（3名委员支持加息25bp，期货隐含9月加息概率61.9%）；美伊僵局持续（霍尔木兹海峡不开放、沙特船只曼德海峡遇袭3死），WTI 83.20(+1.3%)、Brent 88.91(+1.36%)。板块：能源XLE+1.2%/公用事业XLU+1.2%领涨，医疗XLV-0.3%基本持平，通信服务XLC-0.5%领跌（谷歌重组AI部门后连跌）。10年期美债收益率上行至4.70%附近。",
  "source": "WebSearch/财联社+新华社",
  "source_url": "https://so.html5.qq.com/page/real/search_news?docid=70000021_0646a7b9eb453652",
 },
 {
  "id": "N20260812-002", "track": "宏观", "category": "宏观类",
  "title": "美国7月CPI今日北京时间21:30公布：预期整体同比3.4%核心2.5% 9月加息概率回升至50%附近 油价反弹为最大上行风险",
  "summary": "美国劳工部8/12（北京时间21:30）公布7月CPI。市场预期整体CPI同比3.4%（前3.5%）、核心2.5%（前2.6%），环比整体+0.1%/核心+0.2%；油价反弹（WTI 83.20美元）使9月加息概率由非农后的~44%回升至50%附近（期货隐含61.9%）。机构分歧：花旗认为连续两月通胀走软基本排除9月加息；美银认为核心服务反弹使加息仍可能。若CPI≤3.4%，加息或推迟至10-12月、今年仅加25bp；若≥3.6%，沃什'数据驱动式加息'兑现、估值承压。",
  "source": "WebSearch/中国证券报+华尔街见闻",
  "source_url": "http://intl.ce.cn/sjjj/qy/202608/t20260812_3142497.shtml",
 },
 {
  "id": "N20260812-003", "track": "宏观", "category": "宏观类",
  "title": "港股8/11收盘：恒指-1.10%报25652.82 恒生科技-1.93%报4824.42 南向净卖出13亿 腾讯-2.2%财报前避险",
  "summary": "港股8/11恒指一度突破26000点后回落，收盘25652.82(-1.10%)、恒生科技4824.42(-1.93%)、国企指数8528.10(-1.09%)，主板成交2109亿港元。大型科网股集体走弱：腾讯-2.2%收470.80、京东-2.99%、小米-3.48%、快手-3.79%、B站-2.97%；南向资金净卖出超13亿港元（腾讯/阿里遭减持）。创新药逆势走强（基石药业+11%、再鼎+5.28%、药明康德盘中创历史新高）；石油股受油价大涨走强（中海油+3.59%）；黄金股大跌（老铺黄金-8%）。",
  "source": "WebSearch/新华社+每经",
  "source_url": "https://www.nbd.com.cn/articles/2026-08-11/4538575.html",
 },
 {
  "id": "N20260812-004", "track": "A股医药", "category": "业绩类",
  "title": "创新药中报密集兑现：百济H1净利+627.1%上调指引 药明康德H1净利110.8亿+29.43%上调全年指引 泽璟首盈 荣昌扭亏",
  "summary": "2026中报季创新药商业化集中兑现：百济神州H1营收222.20亿(+26.8%)、归母净利32.71亿(+627.1%)超2025全年并上调指引，百悦泽单季销售破12亿美元；药明康德H1净利110.8亿(+29.43%)首破百亿并大幅上调全年指引；泽璟制药首次半年度盈利(H1收入12.05亿+221%、净利6.4亿)；荣昌生物H1约58.5亿(+433%)扭亏；信达收入超82亿(+55%)。A股22家药企披露半年报、超百家发布业绩预告。",
  "source": "WebSearch/财闻+新浪",
  "source_url": "https://www.163.com/dy/article/L428ULK50550WHYR.html",
 },
 {
  "id": "N20260812-005", "track": "A股医药", "category": "行业事件类",
  "title": "创新药出海持续超预期：上半年BD交易总额约997-1063亿美元 全球TOP10占8席 甘李GLP-1出海58亿元涨停兑现",
  "summary": "2026H1中国创新药License-out出海总金额约997亿美元（约为2024年全年的2倍，国家药监局口径1100亿美元、占2025全年80%创同期新高），全球TOP10 BD交易中国独占8席；1-7月BD总金额1063亿美元。甘李药业GLP-1博凡格鲁肽欧洲39国独家许可（首付6200万欧元+里程碑6.64亿欧元，约58亿元人民币）8/11以涨停兑现，市值升至445亿；上海七部门发文支持创新药全球注册认证。公募调研医药生物成唯一破百次行业（上周384次调研）。",
  "source": "WebSearch/界面+上证报",
  "source_url": "https://www.163.com/dy/article/L42L8LPN0534A4SC.html",
 },
 {
  "id": "N20260812-006", "track": "A股医药", "category": "行业事件类",
  "title": "A股8/11缩量整固创新药独强：百花医药6连板 万邦医药20cm涨停 医药ETF冲高回落-0.15% 高位分歧加大",
  "summary": "8/11 A股冲高回落：沪指-0.82%收3934.09、创业板+0.34%，两市成交2.32万亿缩量2021亿、超3700股下跌。创新药逆势强势：百花医药6连板、万邦医药20cm涨停、甘李/哈药/亚泰涨停；但医药ETF广发冲高回落收-0.15%（盘中+1.02%）、医疗ETF-0.57%，药明康德冲高165.8回落收160.21（振幅近5%），获利盘兑现迹象明确。机构（华西/中信）认为市场从单一科技抱团转向多条主线，秋季行情布局期，关注创新药/有色等低拥挤板块。",
  "source": "WebSearch/上证报+Wind",
  "source_url": "https://finance.sina.cn/2026-08-12/detail-inimysya5559769.d.html",
 },
 {
  "id": "N20260812-007", "track": "大消费", "category": "行业事件类",
  "title": "茅台自营店飞天1753元（半年涨254元）五粮液批价冲破800元 龙头'抢收'中秋 双轨价格体系重构渠道利润",
  "summary": "茅台半个月内两次调价：自营店飞天零售价1753元（8/8由1719上调，年初1499以来半年涨254元），i茅台维持1639元，经销商合同价1369元不变——'双轨制'价格体系：i茅台作锚、自营店试探高价承接力，且放开专卖店限价、挤出黄牛；五粮液取消返利收紧补贴，进货成本回升至900元、批价被动推高至800元上方（8/11普五808元）。8/11酒价11大单品七涨五跌、总价9986元创5/19以来新高（精品茅台2432元、国窖1573达890元）。但飞天8/11回落至1720元，涨价持续性存疑，中秋国庆行情改善幅度或有限。",
  "source": "WebSearch/中国商报+新浪酒价内参",
  "source_url": "https://www.toutiao.com/article/7672693853904585250",
 },
 {
  "id": "N20260812-008", "track": "大消费", "category": "行业事件类",
  "title": "白酒板块底部获机构密集确认：兴业沈昊'底部基本确认三季度估值修复10-20%' 国泰海通'基金持仓0.97%历史低位' 中金维持茅台跑赢行业",
  "summary": "8/11机构集中看多白酒：兴业证券食品饮料首席沈昊称白酒板块底部已基本确认、安全边际充足，预计三季度起伴随CPI/PPI改善及消费回暖迎第二阶段估值修复（空间约10-20%），中秋旺季为检验基本面关键窗口；国泰海通指出白酒基金持仓降至0.97%历史低位（较Q1减少1.93%，接近2013-2015深度调整期仓位），调整早出清彻底的酒企有望率先估值修复；中金维持茅台'跑赢行业'评级，看好需求周期/经营调整/量价三重改善共振。",
  "source": "WebSearch/澎湃+财中社+财闻",
  "source_url": "https://new.qq.com/rain/a/20260812A037C100?refer=cp_1009",
 },
 {
  "id": "N20260812-009", "track": "恒生科技", "category": "业绩类",
  "title": "腾讯8/12发布Q2财报：预期营收2024-2030亿(+9~10%) Non-IFRS净利660-691亿(+5~7%) AI资本开支上修至1850-2000亿压制短期利润率 云服务+22-25%结构性亮点",
  "summary": "腾讯控股8/12（今日）发布2026Q2财报。市场一致预期：营收2024-2030亿（Bloomberg共识2039亿，同比+9.7~10.5%）、Non-IFRS净利660-691亿（+5~7%，Non-IFRS经营利润率或降0.4-0.9pct至36.6-37.1%）。核心分歧在AI投入：摩根大通将2026 CapEx上修至2000亿、美银1850亿，全年自由现金流短期承压；但摩根士丹利剔除AI影响核心营运利润增速13.5%。看点：游戏国内+10-15%（《三角洲行动》《洛克王国》）、广告+18-20%（视频号/AIM+）、云/企业服务+22-25%（AI推理需求）为结构性亮点。高盛维持跑赢行业目标价666港元（+44%上行空间）。",
  "source": "WebSearch/雪球+中金研报",
  "source_url": "https://xueqiu.com/8315851674/404592059",
 },
 {
  "id": "N20260812-010", "track": "恒生科技", "category": "行业事件类",
  "title": "港股科网财报前集体避险 高盛维持腾讯666港元目标价 华泰/银河聚焦中报盈利确定性 恒指26000点压力再现",
  "summary": "8/11港股高位回落（恒指26000点得而复失）：科网股财报前集体避险（腾讯-2.2%收470.80、小米-3.48%、快手-3.79%、B站-2.97%），南向净卖出13亿。机构展望：东吴聚焦AI中下游+科技主线（国产大模型纳入港股通催化）；华泰指出港股外资维持净流入、南向从红利切向互联网龙头与半导体链，创新药盈利由降转升、宽度转正，中报盈利确定性将成主导变量；银河聚焦AI应用/大模型龙头+高股息底仓。恒生科技指数拟扩至50只成分股（9月底公布、12月生效）为中长期流动性利好。",
  "source": "WebSearch/每经+雪球",
  "source_url": "https://www.nbd.com.cn/articles/2026-08-11/4538575.html",
 },
 {
  "id": "N20260812-011", "track": "美股标普医药", "category": "行业事件类",
  "title": "礼来口服GLP-1 Foundayo获英国MHRA批准（首个欧洲市场） 替尔泊肽H1销售277亿美元+88% 市值破万亿美元 XLV创历史新高",
  "summary": "礼来口服GLP-1药物Foundayo（orforglipron小分子）获英国MHRA批准用于体重管理与2型糖尿病，成为欧洲第二款GLP-1口服药、首个海外获批（FDA今年4月已批），NICE 11/18评估医保纳入；Q2 Foundayo收入9800万美元。替尔泊肽H1全球销售276.93亿美元(+88%)、Q2单季148.71亿，占礼来营收65%，中国区H1收入+73%；礼来两次上调全年指引至850-870亿美元，市值突破1万亿美元。美股大药企指数XLV创历史新高/今年低点反弹近20%（8/11微跌-0.3%）。仿制药挑战：翰宇药业/山德士替尔泊肽ANDA已获FDA受理并发起专利挑战。",
  "source": "WebSearch/财联社+蓝鲸",
  "source_url": "https://health.sina.cn/2026-08-11/detail-inimyhiz0546201.d.html",
 },
 {
  "id": "N20260812-012", "track": "美股标普医药", "category": "业绩类",
  "title": "美国医疗巨头Q2财报季收官：强生+6.6%上调指引全年破千亿美元 默沙东+5%Keytruda 83.7亿 礼来+48% 创新药仍最大看点 器械手术数据走弱",
  "summary": "美国医疗巨头Q2财报季进入后半程：强生销售额253.1亿(+6.6%)、调整后EPS 2.90(+4.7%)，上调全年指引至约1011亿美元（首次破千亿）；默沙东166.1亿(+5%)，Keytruda单季83.7亿(+5%)占近半收入，上调全年预期；礼来229.7亿(+48%)上调至850-870亿；艾伯维/辉瑞/BMS等纷纷上调指引。结构性分化：减重药等创新药延续高增、器械/手术机器人高景气，但美国医院端手术数据走弱为器械后续增长带来不确定性。礼来股价新高迈入万亿美元时代。",
  "source": "WebSearch/金融时报",
  "source_url": "https://www.financialnews.com.cn/2026-08/11/content_454707.html",
 },
]

# ---------- 2. DeepSeek 批量情绪标注 ----------
def ds(prompt):
    with open("/Users/jieyang/.pi/agent/auth.json") as f:
        key = json.load(f)["deepseek"]["key"]
    data = {
        "model": "deepseek-v4-flash",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 8000,
        "temperature": 0.3,
    }
    req = urllib.request.Request(
        "https://api.deepseek.com/chat/completions",
        data=json.dumps(data).encode(),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as resp:
        result = json.load(resp)
    return result["choices"][0]["message"]["content"]

items = []
for n in news:
    items.append({"id": n["id"], "track": n["track"], "category": n["category"], "title": n["title"], "summary": n["summary"][:300]})

prompt = f"""你是投资情绪分析引擎。对以下 12 条财经新闻（每条含 track 赛道），逐条输出情绪标注 JSON 数组，不要输出其他内容。

标注字段:
- sentiment: 正面/中性/负面
- strength: 0-100 强度（对持仓赛道影响程度）
- impact_direction: 利多/利空/中性
- expected_volatility: 低/中/高（预期波动幅度）
- reason: 一句话理由（≤40字）

规则:
1. 以对【持仓组合四大赛道: 大消费/A股医药/美股标普医药/恒生科技】的影响为准，不是对单一公司
2. 利好兑现类（如涨停、涨价落地）强度打8折，因为已部分反映在股价
3. CPI/财报等事件性新闻标注"中性"但高波动（strength≥70）
4. 输出格式: [{{"id":"N20260812-001","sentiment":"...","strength":..,"impact_direction":"...","expected_volatility":"...","reason":"..."}},...]

新闻:
{json.dumps(items, ensure_ascii=False, indent=1)}"""

content = None
for attempt in range(3):
    try:
        content = ds(prompt)
        if content and content.strip():
            break
        print(f"[DS] 第{attempt+1}次空响应, 重试")
    except Exception as e:
        print(f"[DS] 第{attempt+1}次失败: {e}")
if not content or not content.strip():
    print("ERROR: DeepSeek 标注失败")
    sys.exit(1)

# 提取 JSON 数组
start = content.find("[")
end = content.rfind("]") + 1
sentiments = json.loads(content[start:end])
print(f"[DS] 标注 {len(sentiments)} 条")

# ---------- 3. 写入 news + sentiment JSON ----------
with open(os.path.join(NEWS, "news-2026-08-12.json"), "w", encoding="utf-8") as f:
    json.dump(news, f, ensure_ascii=False, indent=1)

smap = {s["id"]: s for s in sentiments}
out = []
for n in news:
    s = smap.get(n["id"], {})
    out.append({
        "id": n["id"], "track": n["track"], "category": n["category"],
        "title": n["title"], "source_url": n["source_url"],
        "sentiment": s.get("sentiment", "中性"), "strength": s.get("strength", 50),
        "impact_direction": s.get("impact_direction", "中性"),
        "expected_volatility": s.get("expected_volatility", "中"),
        "reason": s.get("reason", ""),
    })
with open(os.path.join(NEWS, "sentiment-2026-08-12.json"), "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)

for s in out:
    print(f"{s['id']} {s['track']} {s['sentiment']} {s['strength']} {s['impact_direction']} {s['expected_volatility']} | {s['reason']}")
print("DONE")
