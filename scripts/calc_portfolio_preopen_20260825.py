# -*- coding: utf-8 -*-
"""盘前档 2026-08-25：组合估值重算（8/24 收盘真实净值全量，今日盘前抓取）+ 赛道占比 + 集中度检查"""
import os, re, json, csv, sys
import pandas as pd

sys.path.insert(0, '/Users/jieyang/.workbuddy/binaries/python/envs/default/lib/python3.13/site-packages')
import akshare as ak

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
                extra = r[len(header) - 1:]
                r = r[: len(header) - 1] + [",".join(extra)]
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

# ---------- 8/24 收盘真实净值（今日盘前抓取全量；QDII 用 8/21 最新已兑现） ----------
FUND_NAV_824 = {
    "002708": 1.915, "000968": 0.8224, "002742": 1.263, "004752": 0.797,
    "005368": 1.1423, "110020": 1.8681, "100032": 0.985, "001180": 0.8015,
    "161616": 1.768, "000051": 1.7434, "519915": 1.834, "000071": 1.5084,
    "012348": 0.6288, "001551": 0.7357, "000248": 1.8187,
    "001469": 1.238, "001552": 1.0347, "012323": 0.5844,
    "000727": 2.487, "004424": 1.768,
    "000369": 2.677, "016280": 2.633, "164906": 0.9563,   # QDII 8/21（8/21 美股 +1.29% 已于 8/25 早盘兑现 +0.98%/+1.00%/+0.54%）
}
# 场内 ETF 8/24 收盘（fund_etf_spot_em 抓取 = 8/24 收盘价，周二早盘为周一收盘）
ETF_SPOT = {}
try:
    etf_df = ak.fund_etf_spot_em()
    etf_code_set = etf_df['代码'].astype(str).tolist()
    etf_map = dict(zip(etf_code_set, etf_df['最新价'].tolist()))
    for code in ["513050", "159928", "512170", "513180", "515180", "159920", "512880", "512980", "159938"]:
        if code in etf_map:
            ETF_SPOT[code] = float(etf_map[code])
    print(f"场内 ETF 实时价抓取成功: {len(ETF_SPOT)} 只")
except Exception as e:
    print(f"[FAIL] fund_etf_spot_em: {e}（用 8/24 收盘价兜底）")
    ETF_SPOT = {"513050": 1.071, "159928": 0.661, "512170": 0.348, "513180": 0.578,
                "515180": 1.454, "159920": 1.472, "512880": 1.069, "512980": 0.797,
                "159938": 0.665}
for k, v in ETF_SPOT.items():
    print(f"  ETF {k}: {v}")

# 个股 8/24 收盘（close_20260824 实测口径）
STOCK_PRICE_824 = {"002410": 8.90, "600438": 12.12}   # 广联达 8.90(-1.22%)、通威 12.12(-2.49%)

def calc_market_value(row):
    code6 = re.sub(r"\D", "", str(row["code"]) if pd.notna(row["code"]) else "")
    name = str(row["name"])
    shares = to_float(row["shares"])
    if "余额宝" in name or "货币" in name or "现金" in name:
        return row["amount"], 0.0
    if code6 in ETF_SPOT:
        return shares * ETF_SPOT[code6], row["amount"]
    if code6 in STOCK_PRICE_824:
        return shares * STOCK_PRICE_824[code6], row["amount"]
    if code6 in FUND_NAV_824:
        return shares * FUND_NAV_824[code6], row["amount"]
    return row["amount"], row["amount"]

vals = all_df.apply(calc_market_value, axis=1, result_type="expand")
all_df["mv"] = vals[0]
all_df["snap_amt"] = vals[1]

total_mv = all_df["mv"].sum()
print(f"8/24 收盘口径总资产: {total_mv:,.2f}")

track_amount = all_df.groupby("track")["mv"].sum().sort_values(ascending=False)
print("\n=== 赛道占比（8/24 收盘口径） ===")
for t, v in track_amount.items():
    print(f"  {t}: {v:,.2f} ({v/total_mv*100:.2f}%)")

med = track_amount.get("A股医药", 0) + track_amount.get("美股标普医药", 0)
print(f"\n医药总敞口: {med:,.2f} ({med/total_mv*100:.2f}%)")
print("\n参考: 8/24 盘后重估总资产 387,183.68（快照基准 392,555.65 - 5,371.97）")

detail = []
for _, r in all_df.sort_values("mv", ascending=False).iterrows():
    detail.append({"account": r["account"], "name": r["name"], "code": str(r["code"]),
                   "track": r["track"], "mv": round(r["mv"], 2), "shares": r["shares"]})
out = {"date": "2026-08-25", "as_of": "2026-08-24收盘", "snap_total": round(snap_total, 2),
       "total_mv": round(total_mv, 2),
       "tracks": {t: {"mv": round(v, 2), "pct": round(v/total_mv*100, 2)} for t, v in track_amount.items()},
       "med_exposure": round(med, 2), "med_pct": round(med/total_mv*100, 2),
       "detail": detail}
with open(os.path.join(BASE, "data/processed/history/portfolio_preopen_20260825.json"), "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
print("\n已保存 portfolio_preopen_20260825.json")
