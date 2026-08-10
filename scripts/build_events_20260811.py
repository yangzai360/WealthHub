#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""2026-08-11 盘前档: 事件库落盘(新闻 + 历史同类匹配参考)
reference 中 actual_ret_1d 留空, 由盘后档回填
"""
import json, os

BASE = "/Users/jieyang/Documents/WealthHub"
NEWS_DIR = os.path.join(BASE, "data/processed/news")
EVENTS_DIR = os.path.join(BASE, "data/processed/events")
DATE = "2026-08-11"

with open(os.path.join(NEWS_DIR, f"news-{DATE}.json"), encoding="utf-8") as f:
    news = json.load(f)

# 手动语义匹配: id -> reference(历史同类1日参考, 基于事件库累计统计)
MATCH = {
    "N20260811-001": {"ret_1d_ref": None, "confidence": None, "match_titles": ["2026-08-07 美股三大指数齐涨标普创新高(宏观)", "2026-08-06 A股沪指五连阳(宏观)"]},
    "N20260811-002": {"ret_1d_ref": 1.37, "confidence": 70, "match_titles": ["2026-08-10 港股收盘恒科+1.37% AI医疗领涨(恒生科技)", "2026-08-10 中概互联ETF+1.29%(场内)"]},
    "N20260811-003": {"ret_1d_ref": 1.37, "confidence": 70, "match_titles": ["2026-08-10 8/12情绪总开关:腾讯二季报+美国CPI+能源月报(宏观)", "2026-08-10 静待美国7月CPI 9月加息概率44.4%(宏观)"]},
    "N20260811-004": {"ret_1d_ref": 1.63, "confidence": 75, "match_titles": ["2026-08-09 BD破千亿美元 中国创新药License-out占Top10八席(A股医药)", "2026-08-09 创新药/CDMO获机构扎堆调研 百济上调指引(A股医药)", "2026-08-10 医药基金大幅回血 部分反弹超30%(A股医药)"]},
    "N20260811-005": {"ret_1d_ref": 0.5, "confidence": 60, "match_titles": ["2026-08-10 RiboX环形RNA体内CAR-T获FDA许可(美股标普医药)", "2026-08-07 FDA批准密集 全球创新药技术突破(美股标普医药)"]},
    "N20260811-006": {"ret_1d_ref": None, "confidence": None, "match_titles": ["2026-08-10 长春高新GenSci148眼科临床获批(个股级,弱影响)"]},
    "N20260811-007": {"ret_1d_ref": -1.3, "confidence": 70, "match_titles": ["2026-08-06 医药情绪高点后次日回撤样本(A股医药)", "2026-08-10 医药情绪极度过热 集中度逼近上限(A股医药)"]},
    "N20260811-008": {"ret_1d_ref": 2.5, "confidence": 75, "match_titles": ["2026-08-09 五粮液批价8/8报770元 白酒景气筑底窗口(大消费)", "2026-08-09 酒价内参:普五逼近800元(大消费)", "2026-08-10 茅台自营店再调价 飞天1753元(大消费)"]},
    "N20260811-009": {"ret_1d_ref": 2.5, "confidence": 70, "match_titles": ["2026-08-10 兴业证券:茅五批价上行行业修复信号渐明(大消费)", "2026-08-09 方正证券:超跌反弹进入攻坚期(大消费)"]},
    "N20260811-010": {"ret_1d_ref": 2.5, "confidence": 70, "match_titles": ["2026-08-10 白酒板块全线爆发 普五批价突破800元(大消费)", "2026-08-10 A股食品饮料全天强势 消费ETF+2.68%(大消费)"]},
    "N20260811-011": {"ret_1d_ref": 1.37, "confidence": 70, "match_titles": ["2026-08-10 8/12情绪总开关:腾讯二季报+美国CPI(恒生科技)", "2026-08-10 港股收盘恒科+1.26%(恒生科技)"]},
    "N20260811-012": {"ret_1d_ref": 1.37, "confidence": 60, "match_titles": ["2026-08-10 华泰:港股反弹源于AI硬件去杠杆跨市场再平衡(恒生科技)"]},
    "N20260811-013": {"ret_1d_ref": 1.37, "confidence": 60, "match_titles": ["2026-08-10 三大因素推动港股通科技属性增强(恒生科技)", "2026-08-06 恒生科技-2.28%大跌样本(恒生科技)"]},
    "N20260811-014": {"ret_1d_ref": 0.5, "confidence": 60, "match_titles": ["2026-08-10 RiboX环形RNA CAR-T获FDA许可(美股标普医药)", "2026-08-07 安进市值新高 美股医疗防御获流入(美股标普医药)"]},
}

events = []
for n in news:
    ev = dict(n)
    m = MATCH.get(n["id"], {})
    ev["reference"] = {
        "ret_3d": None, "ret_5d": None, "ret_10d": None,
        "max_vol": None, "confidence": m.get("confidence"),
        "actual_ret_1d": None, "actual_date": None,
        "ret_1d_ref": m.get("ret_1d_ref"), "match_titles": m.get("match_titles", []),
    }
    events.append(ev)

out = os.path.join(EVENTS_DIR, f"events-{DATE}.json")
with open(out, "w", encoding="utf-8") as f:
    json.dump(events, f, ensure_ascii=False, indent=1)
print(f"[EVENTS] 已写入 {out} ({len(events)} 条)")
print(f"事件库累计: ", end="")
import glob
total = sum(len(json.load(open(p, encoding='utf-8'))) for p in glob.glob(os.path.join(EVENTS_DIR, 'events-*.json')))
print(total)
