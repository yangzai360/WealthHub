#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""2026-08-11 盘前档: 组合赛道占比 + 8/10 收盘估算收益
口径与 calc_portfolio_close_20260810.py 保持一致
"""
import os, re, csv, json
import pandas as pd

BASE = "/Users/jieyang/Documents/WealthHub"
HIST = os.path.join(BASE, "data/processed/history")
HOLD = os.path.join(BASE, "holdings")

def load_snapshot(acct, fn):
    rows = []
    with open(os.path.join(HOLD, acct, fn), encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        header = next(reader)
        for r in reader:
            if not r or not r[0].strip():
                continue
            if len(r) > len(header):
                r = r[: len(header) - 1] + [",".join(r[len(header) - 1:])]
            rec = dict(zip(header, r))
            rec["account"] = acct
            rows.append(rec)
    return rows

all_rows = (load_snapshot("sean-alipay-fund", "snapshot-2026-08-05.csv")
            + load_snapshot("jasy-alipay-fund", "snapshot-2026-08-05.csv")
            + load_snapshot("stock-brokerage", "snapshot-2026-08-06.csv"))
df = pd.DataFrame(all_rows)
df["amount"] = df["amount"].apply(lambda x: float(str(x).replace(",", "")) if str(x).replace(",", "").replace(".", "").isdigit() else 0.0)
total = df["amount"].sum()

TRACK_MAP = {
    "002708": "A股医药", "000727": "A股医药", "161616": "A股医药",
    "001180": "A股医药", "012323": "A股医药", "001551": "A股医药",
    "159938": "A股医药", "512170": "A股医药",
    "519915": "大消费", "000248": "大消费", "159928": "大消费",
    "004424": "大消费", "000968": "大消费",
    "000369": "美股标普医药", "016280": "美股标普医药",
    "012348": "恒生科技", "513180": "恒生科技",
    "513050": "恒生科技", "164906": "恒生科技",
    "000071": "其他/宽基", "159920": "其他/宽基",
}
def track_of(r):
    code6 = re.sub(r"\D", "", str(r["code"])) if pd.notna(r["code"]) else ""
    name = str(r["name"])
    if code6 in TRACK_MAP:
        return TRACK_MAP[code6]
    if "余额宝" in name or "货币" in name or "现金" in name:
        return "现金"
    return "其他/宽基"
df["track"] = df.apply(track_of, axis=1)

ta = df.groupby("track")["amount"].sum().sort_values(ascending=False)
print(f"组合总资产: {total:,.2f}")
for t, v in ta.items():
    print(f"  {t}: {v:,.2f} ({v/total*100:.2f}%)")

# 医药总敞口
med = ta.get("A股医药", 0) + ta.get("美股标普医药", 0)
print(f"医药总敞口: {med/total*100:.2f}%")

# 8/10 收盘行情估算当日收益
# 场外基金 8/10 净值(本次盘前抓取的最新值)
nav_map = {}  # code -> (nav_date, pct)
with open(os.path.join(HIST, "fund_nav.csv"), encoding="utf-8-sig") as f:
    for r in csv.DictReader(f):
        if r["nav_date"] == "2026-08-10":
            nav_map.setdefault(r["code"], []).append(float(r["pct"]))

# 场内 ETF 8/10 收盘
etf_map = {}
with open(os.path.join(HIST, "etf_intraday.csv"), encoding="utf-8-sig") as f:
    for r in csv.DictReader(f):
        if r["date"] == "2026-08-10" and r["note"] == "收盘20:00":
            etf_map[r["code"]] = float(r["pct"])

# 个股 8/10 收盘(广联达+1.60% 通威-2.83% 从盘后报告)
stock_map = {"002410": 1.60, "600438": -2.83}

# 指数代理(盘中无行情的场外基金)
idx_map = {"000071": 1.12, "159920": 1.12, "164906": 1.29, "513050": 1.29, "012348": 1.37, "513180": 1.37,
           "110020": 0.67, "000051": 0.67, "005368": 0.54, "001469": 0.29, "001552": 0.27,
           "100032": 1.06, "002742": 0.12, "004752": 1.38, "515180": 1.06, "512880": 0.27, "512980": 1.38,
           "000968": 1.60, "004424": 2.07}

pnl_total = 0.0
track_pnl = {}
for _, r in df.iterrows():
    code6 = re.sub(r"\D", "", str(r["code"])) if pd.notna(r["code"]) else ""
    name = str(r["name"])
    amt = r["amount"]
    pct = None
    if code6 in nav_map and nav_map[code6]:
        pct = nav_map[code6][-1]
    elif code6 in etf_map:
        pct = etf_map[code6]
    elif code6 in stock_map:
        pct = stock_map[code6]
    elif code6 in idx_map:
        pct = idx_map[code6]
    elif "余额宝" in name or "货币" in name or "现金" in name:
        pct = 0.0
    if pct is None:
        pct = 0.0
    p = amt * pct / 100
    pnl_total += p
    track_pnl[r["track"]] = track_pnl.get(r["track"], 0.0) + p

print(f"\n=== 8/10 收盘组合估算收益: {pnl_total:+,.2f} 元 ({pnl_total/total*100:+.2f}%) ===")
for t, v in sorted(track_pnl.items(), key=lambda x: -abs(x[1])):
    print(f"  {t}: {v:+,.2f} 元 ({v/total*100:+.2f}pct)")

out = {"total": round(total, 2), "track_share": {t: round(v/total*100, 2) for t, v in ta.items()},
       "med_total": round(med/total*100, 2), "est_pnl_0810": round(pnl_total, 2), "est_pnl_pct_0810": round(pnl_total/total*100, 2)}
with open(os.path.join(HIST, "preopen_20260811.json"), "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
print("\nJSON 已保存")
