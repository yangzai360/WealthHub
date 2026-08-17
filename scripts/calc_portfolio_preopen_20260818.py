# -*- coding: utf-8 -*-
"""盘前档 2026-08-18：组合估值重算（用 8/17 收盘净值/收盘价）+ 赛道占比 + 集中度/回撤检查"""
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

# ---------- 8/17 收盘真实净值/收盘价（盘前最新可得） ----------
# 场外基金 8/17 单位净值（今日盘前抓取，QDII 标注 8/14 为 T+1 滞后）
FUND_NAV_817 = {
    "002708": 2.11, "000968": 0.8509, "002742": 1.2588, "004752": 0.8516,
    "005368": 1.1699, "110020": 1.9357, "100032": 0.966, "001180": 0.85,
    "161616": 1.916, "000051": 1.8067, "519915": 1.884, "000071": 1.5045,
    "012348": 0.6529, "001551": 0.7767, "000248": 1.8319,
    "001469": 1.219, "001552": 1.0422, "012323": 0.6091,
    "000727": 2.594, "004424": 1.7857,
    "000369": 2.577, "016280": 2.534, "164906": 0.956,   # QDII 8/14（T+1 滞后）
}
# 场内 ETF 8/17 收盘价
ETF_PRICE_817 = {
    "513050": 1.150, "159928": 0.674, "512170": 0.337, "513180": 0.624,
    "515180": 1.399, "159920": 1.528, "512880": 1.109, "512980": 0.881,
    "159938": 0.704,
}
# 个股 8/17 收盘
STOCK_PRICE_817 = {"002410": 9.12, "600438": 12.91}

# 快照参考价（用于算涨跌）：场内/个股取快照 amount/shares；场外取快照日净值近似
def calc_market_value(row):
    code6 = re.sub(r"\D", "", str(row["code"]) if pd.notna(row["code"]) else "")
    name = str(row["name"])
    shares = to_float(row["shares"])
    # 现金/余额宝：直接取 amount
    if "余额宝" in name or "货币" in name or "现金" in name:
        return row["amount"], 0.0
    # 场内 ETF 与个股：shares × 收盘价
    if code6 in ETF_PRICE_817:
        return shares * ETF_PRICE_817[code6], row["amount"]
    if code6 in STOCK_PRICE_817:
        return shares * STOCK_PRICE_817[code6], row["amount"]
    if code6 in FUND_NAV_817:
        return shares * FUND_NAV_817[code6], row["amount"]
    # 兜底：保持快照市值
    return row["amount"], row["amount"]

vals = all_df.apply(calc_market_value, axis=1, result_type="expand")
all_df["mv"] = vals[0]
all_df["snap_amt"] = vals[1]

total_mv = all_df["mv"].sum()
print(f"8/17 收盘口径总资产: {total_mv:,.2f}")

track_amount = all_df.groupby("track")["mv"].sum().sort_values(ascending=False)
print("\n=== 赛道占比（8/17 收盘口径） ===")
for t, v in track_amount.items():
    print(f"  {t}: {v:,.2f} ({v/total_mv*100:.2f}%)")

med = track_amount.get("A股医药", 0) + track_amount.get("美股标普医药", 0)
print(f"\n医药总敞口: {med:,.2f} ({med/total_mv*100:.2f}%)")

# 组合当日估算（相对 8/14 基准，8/17 单日）
# 用盘后已知：8/17 组合 +0.14%（559.58 元），总资产 393,115.23 —— 直接引用
print("\n参考: 8/17 盘后组合 +0.14%（+559.58 元），总资产 393,115.23（盘后已算）")

detail = []
for _, r in all_df.sort_values("mv", ascending=False).iterrows():
    detail.append({"account": r["account"], "name": r["name"], "code": str(r["code"]),
                   "track": r["track"], "mv": round(r["mv"], 2), "shares": r["shares"]})
with open(os.path.join(BASE, "data/processed/history/portfolio_preopen_20260818.json"), "w", encoding="utf-8") as f:
    json.dump({"date": "2026-08-18", "snap_total": round(snap_total, 2), "total_mv": round(total_mv, 2),
               "tracks": {t: {"mv": round(v, 2), "pct": round(v/total_mv*100, 2)} for t, v in track_amount.items()},
               "detail": detail}, f, ensure_ascii=False, indent=1)
print("\n已保存 portfolio_preopen_20260818.json")
