#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""盘后全量行情更新脚本 (2026-08-10 20:00 档)
抓取: A股指数收盘(新浪日线) + 港股指数收盘(新浪spot) + 场内ETF收盘(东财) + 场外基金净值(天天基金) + 个股收盘(新浪日线)
增量写入: data/processed/history/{indices,etf_intraday,fund_nav}.csv
知识库 §3.9: 盘后收盘数据不依赖 spot, A股指数用 stock_zh_index_daily 日线最后一行收盘价 + 与前一交易日算涨跌幅
"""
import os, sys, re, time, json
import akshare as ak
import pandas as pd

BASE = "/Users/jieyang/Documents/WealthHub"
HIST = os.path.join(BASE, "data/processed/history")
TODAY = "2026-08-10"
NOTE = "收盘20:00"
os.makedirs(HIST, exist_ok=True)

def retry(fn, *args, retries=2, **kwargs):
    last = None
    for i in range(retries + 1):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            last = e
            time.sleep(1.5)
    raise last

def load_existing(path):
    if os.path.exists(path):
        with open(path, encoding="utf-8-sig") as f:
            return [l.rstrip("\n") for l in f if l.strip()]
    return []

def append_unique(path, rows, key_len, header):
    """增量追加: 用前 key_len 列(拼接)判重, 同 key 保留旧行 (key 用整行, 见知识库 §3.9补充3)"""
    existing = load_existing(path)
    keys = set()
    for r in existing[1:]:
        parts = r.split(",")
        if len(parts) >= key_len:
            keys.add(",".join(parts[:key_len]))
    new_rows = []
    for row in rows:
        k = ",".join(str(x) for x in row[:key_len])
        if k not in keys:
            new_rows.append([str(x) for x in row])
            keys.add(k)
    if new_rows:
        exists = os.path.exists(path) and os.path.getsize(path) > 0
        with open(path, "a", encoding="utf-8-sig") as f:
            if not exists:
                f.write(header + "\n")
            for r in new_rows:
                f.write(",".join(r) + "\n")
    return len(new_rows)

results = {"indices": [], "etf": [], "fund_nav": [], "stocks": {}}
errors = []

# ---------- 1. A股指数收盘 (新浪日线, 稳定可靠) ----------
a_daily = {
    "sh000001": ("000001", "上证指数"),
    "sz399006": ("399006", "创业板指"),
    "sh000932": ("000932", "中证消费"),
}
for symbol, (code, name) in a_daily.items():
    try:
        df = retry(ak.stock_zh_index_daily, symbol=symbol)
        if df is not None and len(df) >= 2:
            last = df.iloc[-1]
            prev = df.iloc[-2]
            close = float(last["close"])
            pct = (close / float(prev["close"]) - 1) * 100
            results["indices"].append({
                "type": "index", "date": TODAY, "name": name, "code": code,
                "close": round(close, 2), "pct_change": round(pct, 2), "note": NOTE
            })
    except Exception as e:
        errors.append(f"index {symbol}: {e}")

# ---------- 2. 港股指数收盘 (新浪spot; 收盘后为收盘值) ----------
try:
    hk = retry(ak.stock_hk_index_spot_sina)
    hk_want = {"HSTECH": "恒生科技", "HSI": "恒生指数"}
    for _, row in hk.iterrows():
        code = str(row.get("代码", ""))
        if code in hk_want:
            results["indices"].append({
                "type": "index", "date": TODAY, "name": hk_want[code], "code": code,
                "close": round(float(row["最新价"]), 2),
                "pct_change": round(float(row["涨跌幅"]), 2), "note": NOTE
            })
except Exception as e:
    errors.append(f"stock_hk_index_spot_sina: {e}")

# ---------- 3. 场内 ETF 收盘 (东财 fund_etf_spot_em, 实测可用) ----------
ETF_MAP = {
    "513050": "中概互联", "159928": "消费ETF添富", "159938": "医药ETF广发",
    "512170": "医疗ETF", "513180": "恒指科技", "159920": "恒生ETF华夏",
    "512880": "证券ETF", "512980": "传媒ETF", "515180": "100红利",
}
try:
    etf = retry(ak.fund_etf_spot_em)
    for _, row in etf.iterrows():
        code = str(row["代码"]).zfill(6)
        if code in ETF_MAP:
            results["etf"].append({
                "date": TODAY, "code": code, "name": ETF_MAP[code],
                "price": round(float(row["最新价"]), 3),
                "pct": round(float(row["涨跌幅"]), 2),
                "amount_wan": round(float(row.get("成交额", 0)) / 1e4, 1),
                "note": NOTE
            })
except Exception as e:
    errors.append(f"fund_etf_spot_em: {e}")

# ---------- 4. 场外基金净值 (天天基金源, 收盘后当日净值陆续更新; QDII T+1~T+2) ----------
FUND_MAP = {
    "000369": "广发全球医疗保健A", "016280": "广发全球医疗保健C",
    "002708": "大摩健康产业", "000727": "融通健康产业",
    "012348": "天弘恒生科技A", "000071": "华夏恒生ETF联接A",
    "000248": "汇添富主要消费A", "519915": "富国消费主题",
    "012323": "华宝中证医疗C", "161616": "融通医疗保健",
    "001180": "广发医药卫生", "001551": "天弘医药100C",
    "000968": "广发养老产业", "005368": "富国清洁能源",
    "110020": "易方达沪深300", "000051": "华夏沪深300",
    "001469": "广发金融地产", "001552": "天弘证券保险",
    "004424": "汇添富文体娱乐", "164906": "交银海外互联",
    "100032": "富国红利",
}
fund_detail = {}
for code, name in FUND_MAP.items():
    try:
        nav = retry(ak.fund_open_fund_info_em, symbol=code, indicator="单位净值走势")
        if nav is not None and len(nav) > 0:
            last = nav.iloc[-1]
            nav_date = str(last["净值日期"])[:10]
            chg = float(last["日增长率"]) if pd.notna(last["日增长率"]) else None
            results["fund_nav"].append({
                "date": TODAY, "code": code, "name": name,
                "nav_date": nav_date,
                "nav": round(float(last["单位净值"]), 4),
                "pct": round(chg, 2) if chg is not None else ""
            })
            fund_detail[code] = {"name": name, "nav_date": nav_date,
                                 "nav": float(last["单位净值"]), "chg": chg}
        time.sleep(0.25)
    except Exception as e:
        errors.append(f"fund {code}: {e}")

# ---------- 5. 个股收盘 (新浪日线, 盘后可取当日收盘, 修正盘中指数近似) ----------
STOCK_MAP = {"002410": ("sz002410", "广联达"), "600438": ("sh600438", "通威股份")}
for code6, (symbol, name) in STOCK_MAP.items():
    try:
        df = retry(ak.stock_zh_a_daily, symbol=symbol, adjust="qfq")
        if df is not None and len(df) >= 2:
            last = df.iloc[-1]
            prev = df.iloc[-2]
            close = float(last["close"])
            pct = (close / float(prev["close"]) - 1) * 100
            results["stocks"][code6] = {"name": name, "close": round(close, 2), "pct": round(pct, 2)}
    except Exception as e:
        errors.append(f"stock {symbol}: {e}")

# ---------- 写入 (增量) ----------
idx_path = os.path.join(HIST, "indices.csv")
n_idx = append_unique(idx_path, [
    [r["type"], r["date"], r["name"], r["code"], r["close"], r["pct_change"], r["note"]]
    for r in results["indices"]
], 7, "type,date,name,code,close,pct_change,note")
print(f"[indices] 新增 {n_idx} 条")

etf_path = os.path.join(HIST, "etf_intraday.csv")
n_etf = append_unique(etf_path, [
    [r["date"], r["code"], r["name"], r["price"], r["pct"], r["amount_wan"], r["note"]]
    for r in results["etf"]
], 7, "date,code,name,price,pct,amount_wan,note")
print(f"[etf_intraday] 新增 {n_etf} 条")

nav_path = os.path.join(HIST, "fund_nav.csv")
n_nav = append_unique(nav_path, [
    [r["date"], r["code"], r["name"], r["nav_date"], r["nav"], r["pct"]]
    for r in results["fund_nav"]
], 6, "date,code,name,nav_date,nav,pct")
print(f"[fund_nav] 新增 {n_nav} 条")

# 汇总 JSON
with open(os.path.join(HIST, "close_20260810.json"), "w", encoding="utf-8") as f:
    json.dump({"indices": results["indices"], "etf": results["etf"],
               "fund_nav": results["fund_nav"], "stocks": results["stocks"],
               "errors": errors},
              f, ensure_ascii=False, indent=2)

print("\n=== 指数 ===")
for r in results["indices"]:
    print(f"  {r['name']} {r['code']} {r['close']} {r['pct_change']}%")
print("=== ETF ===")
for r in results["etf"]:
    print(f"  {r['name']} {r['code']} {r['price']} {r['pct']}%")
print("=== 基金净值 ===")
for r in results["fund_nav"]:
    print(f"  {r['name']} {r['code']} {r['nav_date']} {r['nav']} {r['pct']}%")
print("=== 个股 ===")
for c, v in results["stocks"].items():
    print(f"  {v['name']} {c} {v['close']} {v['pct']}%")
if errors:
    print("\n[errors]")
    for e in errors:
        print(f"  {e}")
