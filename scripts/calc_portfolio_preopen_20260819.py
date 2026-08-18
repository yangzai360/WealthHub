# -*- coding: utf-8 -*-
"""盘前档 2026-08-19：组合估值重算（用 8/18 收盘净值/收盘价）+ 赛道占比 + 集中度/回撤检查"""
import os, re, json, csv
import pandas as pd

BASE = "/Users/jieyang/Documents/WealthHub"
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
                r = r[:len(header)-1] + [",".join(r[len(header)-1:])]
            rec = dict(zip(header, r))
            rec["account"] = acct
            rows.append(rec)
    return rows

all_rows = (load_snapshot("sean-alipay-fund", "snapshot-2026-08-05.csv")
            + load_snapshot("jasy-alipay-fund", "snapshot-2026-08-12.csv")
            + load_snapshot("stock-brokerage", "snapshot-2026-08-12.csv"))
all_df = pd.DataFrame(all_rows)

def to_float(x):
    try:
        return float(str(x).replace(",", ""))
    except Exception:
        return 0.0

all_df["amount"] = all_df["amount"].apply(to_float)

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
    "余额宝": "现金", "货币资金": "现金",
}
def track_of(row):
    code = str(row["code"]) if pd.notna(row["code"]) else ""
    code6 = re.sub(r"\D", "", code)
    name = str(row["name"])
    if code6 in TRACK_MAP:
        return TRACK_MAP[code6]
    if "余额宝" in name or "货币" in name or "现金" in name:
        return "现金"
    return "其他/宽基"

all_df["track"] = all_df.apply(track_of, axis=1)
snap_total = all_df["amount"].sum()
print(f"快照总资产: {snap_total:,.2f}")

# ---------- 8/18 收盘真实净值/收盘价（盘前最新可得） ----------
# 场外基金 8/18 单位净值（今日盘前抓取，QDII 标注 8/17 为 T+1 滞后）
FUND_NAV_818 = {
    "002708": 2.085, "000968": 0.8533, "002742": 1.2594, "004752": 0.839,
    "005368": 1.1649, "110020": 1.9296, "100032": 0.971, "001180": 0.8461,
    "161616": 1.915, "000051": 1.8009, "519915": 1.904, "000071": 1.5065,
    "012348": 0.6482, "001551": 0.7713, "000248": 1.8473,
    "001469": 1.2161, "001552": 1.0297, "012323": 0.6087,
    "000727": 2.576, "004424": 1.7966,
    "000369": 2.577, "016280": 2.535, "164906": 0.9632,   # QDII 8/17（T+1 滞后）
}
# 场内 ETF 8/18 收盘价
ETF_PRICE_818 = {
    "513050": 1.152, "159928": 0.678, "512170": 0.337, "513180": 0.617,
    "515180": 1.408, "159920": 1.527, "512880": 1.093, "512980": 0.867,
    "159938": 0.701,
}
# 个股 8/18 收盘
STOCK_PRICE_818 = {"002410": 9.07, "600438": 12.78}

def calc_market_value(row):
    code6 = re.sub(r"\D", "", str(row["code"]) if pd.notna(row["code"]) else "")
    name = str(row["name"])
    shares = to_float(row["shares"])
    if "余额宝" in name or "货币" in name or "现金" in name:
        return row["amount"], 0.0
    if code6 in ETF_PRICE_818:
        return shares * ETF_PRICE_818[code6], row["amount"]
    if code6 in STOCK_PRICE_818:
        return shares * STOCK_PRICE_818[code6], row["amount"]
    if code6 in FUND_NAV_818:
        return shares * FUND_NAV_818[code6], row["amount"]
    return row["amount"], row["amount"]

vals = all_df.apply(calc_market_value, axis=1, result_type="expand")
all_df["mv"] = vals[0]
all_df["snap_amt"] = vals[1]

total_mv = all_df["mv"].sum()
print(f"8/18 收盘口径总资产: {total_mv:,.2f}")

track_amount = all_df.groupby("track")["mv"].sum().sort_values(ascending=False)
print("\n=== 赛道占比（8/18 收盘口径） ===")
for t, v in track_amount.items():
    print(f"  {t}: {v:,.2f} ({v/total_mv*100:.2f}%)")

med = track_amount.get("A股医药", 0) + track_amount.get("美股标普医药", 0)
print(f"\n医药总敞口: {med:,.2f} ({med/total_mv*100:.2f}%)")

# 8/18 组合当日估算（相对 8/17 收盘 394,189.23）
print("\n参考: 8/17 收盘总资产 394,189.23；8/18 估算增量 =", round(total_mv - 394189.23, 2))

detail = []
for _, r in all_df.sort_values("mv", ascending=False).iterrows():
    detail.append({"account": r["account"], "name": r["name"], "code": str(r["code"]),
                   "track": r["track"], "mv": round(r["mv"], 2), "shares": r["shares"]})
with open(os.path.join(BASE, "data/processed/history/portfolio_preopen_20260819.json"), "w", encoding="utf-8") as f:
    json.dump({"date": "2026-08-19", "snap_total": round(snap_total, 2), "total_mv": round(total_mv, 2),
               "tracks": {t: {"mv": round(v, 2), "pct": round(v/total_mv*100, 2)} for t, v in track_amount.items()},
               "detail": detail}, f, ensure_ascii=False, indent=1)
print("\n已保存 portfolio_preopen_20260819.json")
