# -*- coding: utf-8 -*-
"""盘后组合收益复盘 (2026-08-10 20:00 档)
输入: 3 账户持仓快照 + 收盘行情 CSV + 场外基金当日净值 + 个股收盘
输出: 组合当日估算收益/赛道归因/明细 JSON
"""
import os, re, json, csv
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
                extra = r[len(header) - 1:]
                r = r[: len(header) - 1] + [",".join(extra)]
            rec = dict(zip(header, r))
            rec["account"] = acct
            rows.append(rec)
    return rows

all_rows = (load_snapshot("sean-alipay-fund", "snapshot-2026-08-05.csv")
            + load_snapshot("jasy-alipay-fund", "snapshot-2026-08-05.csv")
            + load_snapshot("stock-brokerage", "snapshot-2026-08-06.csv"))
all_df = pd.DataFrame(all_rows)

def to_float(x):
    try:
        return float(str(x).replace(",", ""))
    except Exception:
        return 0.0
all_df["amount"] = all_df["amount"].apply(to_float)
total = all_df["amount"].sum()
print(f"组合总资产: {total:,.2f}")

# ---------- 赛道映射 ----------
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

track_amount = all_df.groupby("track")["amount"].sum().sort_values(ascending=False)
print("\n=== 赛道占比 ===")
for t, v in track_amount.items():
    print(f"  {t}: {v:,.2f} ({v/total*100:.2f}%)")

# ---------- 收盘行情: 场内 ETF (收盘20:00) ----------
ETF_CLOSE = {}
with open(os.path.join(HIST, "etf_intraday.csv"), encoding="utf-8-sig") as f:
    for r in csv.DictReader(f):
        if r["date"] == "2026-08-10" and r["note"] == "收盘20:00":
            ETF_CLOSE[r["code"]] = float(r["pct"])

# ---------- 收盘指数 (收盘20:00) ----------
IDX_CLOSE = {}
with open(os.path.join(HIST, "indices.csv"), encoding="utf-8-sig") as f:
    for r in csv.DictReader(f):
        if r["date"] == "2026-08-10" and r["note"] == "收盘20:00":
            IDX_CLOSE[r["code"]] = float(r["pct_change"])

# ---------- 场外基金净值: 取 8/10 当日更新 (从 fund_nav.csv 读, 避免重复调接口) ----------
FUND_REAL = {}
with open(os.path.join(HIST, "fund_nav.csv"), encoding="utf-8-sig") as f:
    for r in csv.DictReader(f):
        if r["date"] == "2026-08-10" and r["nav_date"] == "2026-08-10":
            try:
                FUND_REAL[r["code"]] = float(r["pct"])
            except Exception:
                pass
print(f"\n8/10 净值已更新基金数: {len(FUND_REAL)} 只")
for c, v in FUND_REAL.items():
    print(f"  {c}: {v}%")

# ---------- 个股收盘 (已入库 close_20260810.json) ----------
STOCK_CLOSE = {}
with open(os.path.join(HIST, "close_20260810.json"), encoding="utf-8") as f:
    cj = json.load(f)
STOCK_CLOSE = {c: v["pct"] for c, v in cj.get("stocks", {}).items()}
print(f"\n个股收盘: {STOCK_CLOSE}")

# ---------- 估算当日涨跌幅 ----------
# 优先级: 个股收盘 > 场内ETF收盘 > 场外基金当日净值 > 赛道指数代理
TRACK_PROXY = {
    "A股医药": IDX_CLOSE.get("399006", -0.73) * 0.3 + 1.63,  # 医药ETF 领衔, 创业板略拖累
    "大消费": IDX_CLOSE.get("000932", 2.50),
    "美股标普医药": 0.16,  # 8/10 美股未开盘, QDII 反映 8/6 海外净值 (广发全球医疗 8/6 +0.16%)
    "恒生科技": IDX_CLOSE.get("HSTECH", 1.37),
    "其他/宽基": IDX_CLOSE.get("000001", 0.67),
    "现金": 0.0,
}
def est_pct(row):
    code6 = re.sub(r"\D", "", str(row["code"]) if pd.notna(row["code"]) else "")
    if code6 in STOCK_CLOSE:
        return STOCK_CLOSE[code6]
    if code6 in ETF_CLOSE:
        return ETF_CLOSE[code6]
    if code6 in FUND_REAL:
        return FUND_REAL[code6]
    return TRACK_PROXY.get(row["track"], 0.0)

all_df["est_pct"] = all_df.apply(est_pct, axis=1)
all_df["est_pnl"] = all_df["amount"] * all_df["est_pct"] / 100.0

total_est = all_df["est_pnl"].sum()
print(f"\n=== 组合当日估算收益 ===")
print(f"  估算盈亏: {total_est:,.2f} ({total_est/total*100:.2f}%)")
print("\n=== 赛道归因 ===")
contrib = all_df.groupby("track").apply(lambda d: (d["est_pnl"].sum(), d["est_pnl"].sum()/total*100), include_groups=False)
for t, (v, p) in contrib.items():
    print(f"  {t}: {v:,.2f} ({p:.2f}pct)")

detail = []
for _, r in all_df.sort_values("amount", ascending=False).iterrows():
    detail.append({
        "account": r["account"], "name": r["name"], "code": str(r["code"]),
        "track": r["track"], "amount": round(r["amount"], 2),
        "est_pct": round(r["est_pct"], 2), "est_pnl": round(r["est_pnl"], 2),
    })
with open(os.path.join(HIST, "portfolio_close_20260810.json"), "w", encoding="utf-8") as f:
    json.dump({
        "total": round(total, 2),
        "tracks": {t: {"amount": round(v, 2), "pct": round(v/total*100, 2)} for t, v in track_amount.items()},
        "est_total_pct": round(total_est/total*100, 2),
        "est_total_pnl": round(total_est, 2),
        "contrib": {t: {"pnl": round(v, 2), "pct": round(p, 2)} for t, (v, p) in contrib.items()},
        "fund_real": FUND_REAL,
        "stock_close": STOCK_CLOSE,
        "etf_close": ETF_CLOSE,
        "idx_close": IDX_CLOSE,
        "detail": detail,
    }, f, ensure_ascii=False, indent=1)
print("\n已保存 portfolio_close_20260810.json")
