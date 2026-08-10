#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""盘后事件回填 + 盘后新闻追加 (2026-08-10 20:00 档)
1. 回填 events-2026-08-08.json / events-2026-08-09.json 中 actual_ret_1d=null 的事件
   (用 8/10 交易日实际涨跌幅; 美股标普医药因 8/10 美股未开盘暂留空待 8/11 盘前回填)
2. 盘后新闻追加到 news-2026-08-10.json (N018+)
"""
import json, os, re

BASE = "/Users/jieyang/Documents/WealthHub"
EV = os.path.join(BASE, "data/processed/events")
NW = os.path.join(BASE, "data/processed/news")

# 8/10 实际涨跌幅 (来源: close_update_2026-08-10.py 落库收盘值)
TRACK_RET = {
    "A股医药": 1.63,      # 医药ETF广发 159938 收盘 +1.63%
    "大消费": 2.50,       # 中证消费 000932 收盘 +2.50%
    "恒生科技": 1.37,     # HSTECH spot 收盘 +1.37%
    "宏观": 0.67,         # 上证指数 000001 收盘 +0.67%
    "美股标普医药": None,  # 8/10 美股未开盘, 留空待 8/11 盘前回填 (XLV)
}
ACTUAL_DATE = "2026-08-10"

# ---------- 1. 回填 8/8、8/9 事件 ----------
backfilled = 0
skipped = 0
for fname in ["events-2026-08-08.json", "events-2026-08-09.json"]:
    path = os.path.join(EV, fname)
    with open(path, encoding="utf-8") as f:
        events = json.load(f)
    changed = False
    for ev in events:
        ref = ev.get("reference", {})
        if ref.get("actual_ret_1d") is None:
            track = ev.get("track", "宏观")
            ret = TRACK_RET.get(track)
            if ret is not None:
                ref["actual_ret_1d"] = ret
                ref["actual_date"] = ACTUAL_DATE
                backfilled += 1
                changed = True
            else:
                skipped += 1
    if changed:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(events, f, ensure_ascii=False, indent=1)
        print(f"[回填] {fname}: 已更新")
print(f"回填 {backfilled} 条, 留空(美股医药待8/11) {skipped} 条")

# ---------- 2. 盘后新闻追加 (N018+) ----------
new_news = [
 {
  "id": "N20260810-018",
  "date": "2026-08-10",
  "track": "宏观",
  "category": "宏观类",
  "title": "A股收盘：沪指五连阳涨0.67%报3966.59点 超4000只股票上涨 医药有色消费走强 算力硬件调整",
  "summary": "8/10 A股延续反弹，沪指实现日线五连阳收3966.59点(+0.67%)、深成指+0.04%、创业板指-0.73%、北证50+0.31%；沪深京成交约2.54万亿(较前日缩量约1447亿)。超4000只上涨、逾100只涨停。医疗服务全天走强(百花医药5连板)，资源股(钨/贵金属)与白酒板块获资金关注，猪肉/乳业/影视活跃；算力硬件产业链调整(CPO/元件/通信设备领跌，光迅科技盘中跌停)，资金从AI硬件切向医药/资源/消费，市场热点持续轮动。",
  "source": "WebSearch/腾讯新闻·大鱼财经",
  "source_url": "https://new.qq.com/rain/a/20260810A097OZ00?refer=cp_1009",
  "sentiment": "",
  "strength": None,
  "impact_direction": "",
  "expected_volatility": "",
  "reason": ""
 },
 {
  "id": "N20260810-019",
  "date": "2026-08-10",
  "track": "A股医药",
  "category": "行业事件类",
  "title": "涨停复盘：吃酒喝药继续嗨 百花医药5连板 哈三联5天3板 医药生物获49亿主力净流入 创新药BD半年1063亿美元",
  "summary": "8/10涨停复盘：市场回归科技牛以前的吃酒喝药行情，共103股涨停、连板股12只。医药延续强势：百花医药5连板、开开实业3连板、哈三联5天3板、毕得医药/百普赛斯20CM2连板、瑞康医药/哈药股份/誉衡药业2连板；医药生物获49亿主力净流入居申万之首。泛消费异动(一鸣食品10天6板)。上涨逻辑：药明康德/百济神州等药企上调2026全年业绩指引；1-7月中国创新药BD交易总额1063亿美元、全球前十BD中国独占8席。算力硬件调整(中际旭创/新易盛跌超5%、寒武纪跌超6%)，存量资金博弈格局下高位科技与低位消费医药剧烈轮动。",
  "source": "WebSearch/腾讯新闻·涨停复盘",
  "source_url": "https://new.qq.com/rain/a/20260810A0AZ2200?refer=cp_1009",
  "sentiment": "",
  "strength": None,
  "impact_direction": "",
  "expected_volatility": "",
  "reason": ""
 },
 {
  "id": "N20260810-020",
  "date": "2026-08-10",
  "track": "恒生科技",
  "category": "行业事件类",
  "title": "港股收盘：恒指涨1.05%收25937.49点 恒生科技涨1.26% 生物医药与AI医疗概念领涨",
  "summary": "新华社香港8/10电：恒生指数涨269.46点(+1.05%)收25937.49点，全日主板成交2402.8亿港元；国企指数+1.06%收8621.84点；恒生科技+1.26%收4919.46点。腾讯+0.54%收481.4港元、港交所+1.26%、阿里-W收涨2.34%。板块：黄金领涨(老铺黄金+12.39%)，AI医疗概念大涨(百奥赛图-B+11.08%、剂泰科技+7.91%、晶泰控股+7.68%、英矽智能+6.69%)；国泰君安国际复牌大涨36.78%(私有化要约溢价44.2%)；半导体等板块承压。",
  "source": "WebSearch/新华社·腾讯新闻",
  "source_url": "https://new.qq.com/rain/a/20260810A0A2ZU00?refer=cp_1009",
  "sentiment": "",
  "strength": None,
  "impact_direction": "",
  "expected_volatility": "",
  "reason": ""
 },
 {
  "id": "N20260810-021",
  "date": "2026-08-10",
  "track": "美股标普医药",
  "category": "宏观类",
  "title": "静待美国7月CPI 8/12公布 美联储9月加息25bp概率44.4% 美银坚持9月启动加息判断",
  "summary": "财联社/金融界：7月CPI将于北京时间8/12(周三)晚公布，FactSet预期整体CPI同比由3.5%回落至3.4%、核心CPI由2.6%降至2.5%。CME美联储观察：9月维持利率不变概率55.6%、加息25bp概率44.4%。非农虽爆冷(-2.3万)但美银维持美联储9月启动、累计75bp加息预测，称7月CPI比就业报告更重要，政策重心仍在通胀。若CPI偏热(≥3.6%)，9月加息概率回升将压制全球成长资产；若降温兑现，港股/成长延续修复。黄金8/10失守4330美元/盎司(-0.29%)。",
  "source": "WebSearch/财联社·金融界",
  "source_url": "https://finance.jrj.com.cn/2026/08/10152858056285.shtml",
  "sentiment": "",
  "strength": None,
  "impact_direction": "",
  "expected_volatility": "",
  "reason": ""
 },
 {
  "id": "N20260810-022",
  "date": "2026-08-10",
  "track": "A股医药",
  "category": "行业事件类",
  "title": "药明康德股价创历史新高：1260H禁令暂时豁免落地 CXO含量52%的港股通医疗ETF涨超3%",
  "summary": "8/10盘中药明康德A股创历史新高(A股总市值一度达3972.58亿元，早盘涨超5%、市值约4800亿元)，美国哥伦比亚特区联邦地区法院8/7批准初步禁令动议，诉讼期间禁止国防部执行1260H列名效力。CXO含量超52%的港股通医疗ETF华夏(520510)早盘涨超3%居全市场ETF涨幅前列；恒生沪深港创新药精选50指数早盘最高涨超4%。国盛/招商证券认为禁令为阶段性胜利，中报季+WCLC/ESMO催化窗口下医药行情有望持续向上。",
  "source": "WebSearch/网易·新浪财经",
  "source_url": "https://www.163.com/dy/article/L3VEHO5F0534A4SC.html",
  "sentiment": "",
  "strength": None,
  "impact_direction": "",
  "expected_volatility": "",
  "reason": ""
 },
 {
  "id": "N20260810-023",
  "date": "2026-08-10",
  "track": "大消费",
  "category": "行业事件类",
  "title": "A股食品饮料全天强势：迎驾贡酒涨超8% 一鸣食品10天6板 香飘飘/百洋股份涨停 消费ETF+2.68%",
  "summary": "8/10大消费延续强势：农林牧渔领涨两市(百洋股份/益生股份/邦基科技涨停)，食品饮料涨幅居前(皇氏集团/金达威/香飘飘/一鸣食品/莲花控股涨停，迎驾贡酒/品渥食品涨超8%，东鹏饮料/立高食品涨超6%)；白酒Ⅱ板块+2.70%(主力净流入9.6亿元排名靠前)。消费ETF添富159928收0.69元(+2.68%)、中证消费000932收12939.66(+2.50%)。政策面《扩大消费'十五五'规划》提出到2030年社零总额达60万亿元左右目标，为消费板块提供中期政策锚。",
  "source": "WebSearch/腾讯新闻·涨停复盘",
  "source_url": "https://so.html5.qq.com/page/real/search_news?docid=70000021_3926a797d8d77752",
  "sentiment": "",
  "strength": None,
  "impact_direction": "",
  "expected_volatility": "",
  "reason": ""
 }
]

# 合并到 news-2026-08-10.json
news_path = os.path.join(NW, "news-2026-08-10.json")
with open(news_path, encoding="utf-8") as f:
    news = json.load(f)
existing_ids = {n["id"] for n in news}
added = 0
for n in new_news:
    if n["id"] not in existing_ids:
        news.append(n)
        existing_ids.add(n["id"])
        added += 1
with open(news_path, "w", encoding="utf-8") as f:
    json.dump(news, f, ensure_ascii=False, indent=1)
print(f"[news] 追加 {added} 条, 当前共 {len(news)} 条")
