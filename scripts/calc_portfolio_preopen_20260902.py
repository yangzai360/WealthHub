# -*- coding: utf-8 -*-
"""盘前档 2026-09-02：组合估值重算（9/1 收盘真实净值全量，QDII 广发全球医疗 8/31 -0.53%/-0.54% 已兑现）+ 赛道占比 + 集中度检查 + 夏普比率估算
基金净值从 fund_nav.csv 读取最新（QDII 8/31、其余 9/1）；场内 ETF/个股用 9/1 收盘价"""
import os, re, json, csv, sys
import pandas as pd

BASE = "/Users/jieyang/Documents/WealthHub"
HOLD = os.path.join(BASE, "holdings")
HIST = os.path.join(BASE, "data/processed/history")

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

# ---------- 从 fund_nav.csv 读取最新净值 ----------
fund_nav = {}
with open(os.path.join(HIST, "fund_nav.csv"), encoding="utf-8-sig") as f:
    for row in csv.DictReader(f):
        code = row["code"]
        nav_date = row["nav_date"]
        try:
            nav = float(row["nav"])
        except Exception:
            continue
        if code not in fund_nav or nav_date > fund_nav[code][0]:
            fund_nav[code] = (nav_date, nav)
print("fund_nav 最新净值（QDII 8/31 已兑现、其余 9/1）：")
for code, (d, nav) in sorted(fund_nav.items()):
    print(f"  {code}: {d} {nav}")

# ---------- 场内 ETF 9/1 收盘 ----------
ETF_SPOT = {"513050": 1.059, "159928": 0.674, "512170": 0.341, "513180": 0.577,
            "515180": 1.469, "159920": 1.489, "512880": 1.113, "512980": 0.851,
            "159938": 0.646}
# ---------- 个股 9/1 收盘 ----------
STOCK_PRICE = {"002410": 8.91, "600438": 11.82}   # 广联达 8.91(-0.89%)、通威 11.82(+1.98%)

def calc_market_value(row):
    code6 = re.sub(r"\D", "", str(row["code"]) if pd.notna(row["code"]) else "")
    name = str(row["name"])
    shares = to_float(row["shares"])
    if "余额宝" in name or "货币" in name or "现金" in name:
        return row["amount"], 0.0
    if code6 in ETF_SPOT:
        return shares * ETF_SPOT[code6], row["amount"]
    if code6 in STOCK_PRICE:
        return shares * STOCK_PRICE[code6], row["amount"]
    if code6 in fund_nav:
        return shares * fund_nav[code6][1], row["amount"]
    return row["amount"], row["amount"]

vals = all_df.apply(calc_market_value, axis=1, result_type="expand")
all_df["mv"] = vals[0]
all_df["snap_amt"] = vals[1]

total_mv = all_df["mv"].sum()
print(f"\n9/1 收盘口径总资产: {total_mv:,.2f}")

track_amount = all_df.groupby("track")["mv"].sum().sort_values(ascending=False)
print("\n=== 赛道占比（9/1 收盘口径） ===")
for t, v in track_amount.items():
    print(f"  {t}: {v:,.2f} ({v/total_mv*100:.2f}%)")

med = track_amount.get("A股医药", 0) + track_amount.get("美股标普医药", 0)
print(f"\n医药总敞口: {med:,.2f} ({med/total_mv*100:.2f}%)")
print("\n参考: 9/1 盘后重估总资产 386,613.68（9/1 收盘口径）")

# ---------- 夏普比率估算 ----------
rf_10y = 1.69
daily_rets = []
import glob, re as _re
for f in sorted(glob.glob(os.path.join(HIST, "portfolio_close_2026*.json"))):
    try:
        with open(f, encoding="utf-8") as fp:
            d = json.load(fp)
        pct = d.get("est_total_pct")
        dt = str(d.get("date", ""))
        m = _re.search(r"(\d{4})-?(\d{2})-?(\d{2})", dt)
        if pct is None:
            continue
        if not m:
            m2 = _re.search(r"(\d{4})(\d{2})(\d{2})", f)
            if not m2:
                continue
            norm = f"{m2.group(1)}-{m2.group(2)}-{m2.group(3)}"
        else:
            norm = f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
        if norm < "2026-08-06":
            continue
        daily_rets.append((norm, float(pct)))
    except Exception:
        continue
seen = {}
for dt, p in daily_rets:
    seen[dt] = p
daily_rets = sorted(seen.items())
sharpe = None
if daily_rets:
    print(f"\n夏普估算: 样本 {len(daily_rets)} 个交易日 ({daily_rets[0][0]} ~ {daily_rets[-1][0]})")
if len(daily_rets) >= 10:
    import statistics
    rets = [p for _, p in daily_rets]
    mean_d = sum(rets) / len(rets)
    std_d = statistics.stdev(rets) if len(rets) > 1 else 0
    rf_d = rf_10y / 100 / 252
    sharpe = (mean_d - rf_d) / std_d * (252 ** 0.5) if std_d > 0 else None
    print(f"  日收益均值 {mean_d:.4f}% 日标准差 {std_d:.4f}% 年化夏普 {sharpe:.2f}" if sharpe else "  年化夏普 None")
    for dt, p in daily_rets:
        print(f"    {dt}: {p}%")

detail = []
for _, r in all_df.sort_values("mv", ascending=False).iterrows():
    detail.append({"account": r["account"], "name": r["name"], "code": str(r["code"]),
                   "track": r["track"], "mv": round(r["mv"], 2), "shares": r["shares"]})
out = {"date": "2026-09-02", "as_of": "2026-09-01收盘", "snap_total": round(snap_total, 2),
       "total_mv": round(total_mv, 2),
       "tracks": {t: {"mv": round(v, 2), "pct": round(v/total_mv*100, 2)} for t, v in track_amount.items()},
       "med_exposure": round(med, 2), "med_pct": round(med/total_mv*100, 2),
       "sharpe_annual": round(sharpe, 2) if sharpe else None,
       "sharpe_samples": len(daily_rets),
       "rf_10y": rf_10y,
       "detail": detail}
with open(os.path.join(HIST, "portfolio_preopen_20260902.json"), "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
print("\n已保存 portfolio_preopen_20260902.json")
