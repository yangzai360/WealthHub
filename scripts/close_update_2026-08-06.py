#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""盘后全量行情更新脚本 (2026-08-06 20:00 档)
抓取: A股/港股指数收盘(新浪源) + 场内ETF收盘(东财) + 场外基金净值(天天基金)
增量写入: data/processed/history/{indices,etf_intraday,fund_nav}.csv
"""
import sys, os, re, time, json
import akshare as ak
import pandas as pd

HIST = os.path.join(os.path.dirname(__file__), "..", "data", "processed", "history")
HIST = os.path.abspath(HIST)
TODAY = "2026-08-06"
NOTE = "收盘20:00"

os.makedirs(HIST, exist_ok=True)

def retry(fn, *args, retries=2, **kwargs):
    for i in range(retries + 1):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            if i == retries:
                raise
            time.sleep(2)

def load_existing(path):
    if os.path.exists(path):
        with open(path, encoding="utf-8-sig") as f:
            return [l.rstrip("\n") for l in f if l.strip()]
    return []

def append_unique(path, rows, key_idx):
    existing = load_existing(path)
    keys = set()
    for r in existing[1:]:
        parts = r.split(",")
        if len(parts) > key_idx:
            keys.add(",".join(parts[: key_idx + 1]))
    header = existing[0] if existing else None
    new_rows = []
    for row in rows:
        k = ",".join(str(x) for x in row[: key_idx + 1])
        if k not in keys:
            new_rows.append([str(x) for x in row])
            keys.add(k)
    if not existing and new_rows:
        raise RuntimeError(f"{path} 缺少表头")
    with open(path, "a", encoding="utf-8-sig") as f:
        for r in new_rows:
            f.write(",".join(r) + "\n")
    return len(new_rows)

summary = {}

# ---------- 1. A股指数收盘(新浪) ----------
a_rows = []
try:
    df = retry(ak.stock_zh_index_spot_sina)
    df["code6"] = df["代码"].astype(str).apply(lambda x: re.sub(r"\D", "", x))
    target = {"000001": "上证指数", "399006": "创业板指", "399932": "中证消费"}
    for code, name in target.items():
        row = df[df["code6"] == code]
        if not row.empty:
            r = row.iloc[0]
            a_rows.append(["index", TODAY, name, code, round(float(r["最新价"]), 2),
                           round(float(r["涨跌幅"]), 2), NOTE])
    print("A股指数:", a_rows)
except Exception as e:
    print("A股指数失败:", e)
summary["a_index"] = a_rows

# ---------- 2. 港股指数收盘(新浪) ----------
hk_rows = []
try:
    hk = retry(ak.stock_hk_index_spot_sina)
    for code in ["HSTECH", "HSI"]:
        row = hk[hk["代码"] == code]
        if not row.empty:
            r = row.iloc[0]
            hk_rows.append(["index", TODAY, r["名称"], code, round(float(r["最新价"]), 2),
                            round(float(r["涨跌幅"]), 2), NOTE])
    print("港股指数:", hk_rows)
except Exception as e:
    print("港股指数失败:", e)
summary["hk_index"] = hk_rows

# 合并指数
idx_rows = a_rows + hk_rows
n_idx = append_unique(os.path.join(HIST, "indices.csv"), idx_rows, 3)
print(f"indices.csv 新增 {n_idx} 条")

# ---------- 3. 场内 ETF 收盘(东财) ----------
etf_rows = []
try:
    spot = retry(ak.fund_etf_spot_em)
    etf_codes = ["513050", "159928", "159938", "512170", "513180", "159920",
                 "512880", "512980", "515180"]
    sub = spot[spot["代码"].isin(etf_codes)]
    for _, r in sub.iterrows():
        etf_rows.append([TODAY, r["代码"], r["名称"], round(float(r["最新价"]), 3),
                         round(float(r["涨跌幅"]), 2),
                         round(float(r.get("成交额", 0)) / 10000, 1), NOTE])
    etf_rows.sort(key=lambda x: etf_codes.index(x[1]))
    print("ETF:", etf_rows)
except Exception as e:
    print("ETF失败:", e)
summary["etf"] = etf_rows
n_etf = append_unique(os.path.join(HIST, "etf_intraday.csv"), etf_rows, 1)
print(f"etf_intraday.csv 新增 {n_etf} 条")

# ---------- 4. 场外基金净值(天天基金) ----------
fund_codes = ["002708", "000968", "005368", "110020", "000369", "001180",
              "161616", "000051", "519915", "000071", "012348", "001551",
              "164906", "000248", "016280", "001469", "001552", "012323",
              "000727", "004424"]
fund_rows = []
fund_detail = {}
for code in fund_codes:
    try:
        dfn = retry(ak.fund_open_fund_info_em, symbol=code, indicator="单位净值走势")
        if dfn is None or dfn.empty:
            continue
        last = dfn.iloc[-1]
        nav_date = str(last["净值日期"])[:10]
        nav = float(last["单位净值"])
        chg = float(last["日增长率"]) if "日增长率" in last and pd.notna(last["日增长率"]) else None
        name = dfn.attrs.get("name", "") if hasattr(dfn, "attrs") else ""
        # fund_open_fund_info_em 无名称列, 用映射
        fund_rows.append([TODAY, code, "", nav_date, round(nav, 4),
                          round(chg, 2) if chg is not None else ""])
        fund_detail[code] = {"nav_date": nav_date, "nav": nav, "chg": chg}
        time.sleep(0.3)
    except Exception as e:
        print(f"基金 {code} 失败: {e}")
        fund_detail[code] = {"error": str(e)}
print("基金净值抓取完成, 明细见 fund_nav.csv")
n_fund = append_unique(os.path.join(HIST, "fund_nav.csv"), fund_rows, 3)
print(f"fund_nav.csv 新增 {n_fund} 条")

# ---------- 5. 汇总输出 ----------
print(json.dumps({
    "indices_added": n_idx,
    "etf_added": n_etf,
    "fund_added": n_fund,
    "fund_detail": fund_detail,
    "hk_index": hk_rows,
}, ensure_ascii=False, indent=1))
