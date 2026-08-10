#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""2026-08-11 盘前档行情增量更新
范围: 隔夜美股 8/10 收盘(XLV/IYH/QQQ/DIA) + 场外基金 8/10 净值(部分已出, QDII T+1~T+2)
写入: indices.csv (type=us_index) / fund_nav.csv, 仅增量
"""
import os, sys, re, json, datetime
import akshare as ak

BASE = "/Users/jieyang/Documents/WealthHub"
HIST = os.path.join(BASE, "data/processed/history")
INDICES = os.path.join(HIST, "indices.csv")
FUND_NAV = os.path.join(HIST, "fund_nav.csv")

def read_csv_lines(path):
    with open(path, encoding="utf-8-sig") as f:
        return f.read().splitlines()

def append_rows(path, header, rows):
    existing = set(read_csv_lines(path))
    with open(path, "a", encoding="utf-8-sig") as f:
        for row in rows:
            if row not in existing:
                f.write(row + "\n")

# ---------- 1. 美股 8/10 收盘 (XLV/IYH/QQQ/DIA) ----------
us_tickers = {
    "XLV": "美股医疗保健XLV",
    "IYH": "美股医疗ETF(IYH)",
    "QQQ": "美股纳指100QQQ",
    "DIA": "美股道指DIA",
}
us_rows = []
existing_us = set(read_csv_lines(INDICES))
for sym, name in us_tickers.items():
    try:
        df = ak.stock_us_daily(symbol=sym)
        df = df.tail(2).reset_index(drop=True)
        if len(df) < 2:
            print(f"[US] {sym}: 数据不足, 跳过")
            continue
        prev = float(df.iloc[-2]["close"]); last = float(df.iloc[-1]["close"])
        date = str(df.iloc[-1]["date"])[:10]
        pct = round((last - prev) / prev * 100, 2)
        row = f"us_index,{date},{name},{sym},{last:.2f},{pct:+g},美股收盘(隔夜)"
        if row not in existing_us:
            us_rows.append(row)
        print(f"[US] {sym} {date} close={last:.2f} pct={pct:+.2f}%")
    except Exception as e:
        print(f"[US] {sym} 失败: {e}")

if us_rows:
    append_rows(INDICES, None, us_rows)
    print(f"[US] 写入 {len(us_rows)} 行 indices.csv")

# ---------- 2. 场外基金 8/10 净值增量 ----------
funds = [
    # (code, name)
    ("000051", "华夏沪深300ETF联接A"), ("000071", "华夏恒生ETF联接A"),
    ("000248", "汇添富主要消费A"), ("000369", "广发全球医疗保健A"),
    ("000727", "融通健康产业A/B"), ("000968", "广发养老产业A"),
    ("001180", "广发医药卫生A"), ("001469", "广发金融地产A"),
    ("001551", "天弘医药100C"), ("001552", "天弘证券保险A"),
    ("002708", "大摩健康产业A"), ("002742", "泓德裕祥债券A"),
    ("004424", "汇添富文体娱乐A"), ("004752", "广发传媒ETF联接A"),
    ("005368", "富国清洁能源A"), ("012323", "华宝中证医疗C"),
    ("012348", "天弘恒生科技A"), ("016280", "广发全球医疗保健C"),
    ("100032", "富国红利增强A"), ("110020", "易方达沪深300A"),
    ("161616", "融通医疗保健A/B"), ("164906", "交银中概互联A"),
    ("519915", "富国消费主题A"),
]
today = "2026-08-11"
nav_rows = []
existing_nav = set(read_csv_lines(FUND_NAV))
for code, name in funds:
    try:
        df = ak.fund_open_fund_info_em(symbol=code, indicator="单位净值走势")
        if df is None or df.empty:
            print(f"[NAV] {code} {name}: 无数据")
            continue
        last = df.iloc[-1]
        nav_date = str(last["净值日期"])[:10]
        nav = last["单位净值"]
        pct = last.get("日增长率", "")
        if pct in (None, "", "-", "--"):
            # 尝试算 pct
            if len(df) >= 2:
                prev = float(df.iloc[-2]["单位净值"])
                pct = round((float(nav) - prev) / prev * 100, 2)
            else:
                pct = 0.0
        # 只看 nav_date >= 2026-08-09 的增量(8/7 已归档, 8/10 净值新出)
        if nav_date >= "2026-08-09":
            row = f"{today},{code},{name},{nav_date},{nav},{pct}"
            if row not in existing_nav:
                nav_rows.append(row)
                print(f"[NAV] {code} {name} {nav_date} nav={nav} pct={pct}% 新增")
            else:
                print(f"[NAV] {code} {name} {nav_date} 已存在, 跳过")
        else:
            print(f"[NAV] {code} {name} 最新净值 {nav_date} 非增量, 跳过")
    except Exception as e:
        print(f"[NAV] {code} {name} 失败: {e}")

if nav_rows:
    append_rows(FUND_NAV, None, nav_rows)
    print(f"[NAV] 写入 {len(nav_rows)} 行 fund_nav.csv")

print("DONE")
