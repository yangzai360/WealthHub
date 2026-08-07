# -*- coding: utf-8 -*-
"""持仓合并 + 赛道占比 + 盘中组合估算收益 (2026-08-07 13:45 档)"""
import os, re, json, csv
import pandas as pd

BASE = "/Users/jieyang/Documents/WealthHub"
HOLD = os.path.join(BASE, "holdings")

# ---------- 1. 读取 3 账户快照 (手动 csv 解析, note 字段内含逗号) ----------
def load_snapshot(acct, fn):
    rows = []
    with open(os.path.join(HOLD, acct, fn), encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        header = next(reader)
        for r in reader:
            if not r or not r[0].strip():
                continue
            # 若字段数超过表头(股票账户 note 内含逗号), 多余的合并回 note
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

# 金额清洗
def to_float(x):
    try:
        return float(str(x).replace(",", ""))
    except Exception:
        return 0.0
all_df["amount"] = all_df["amount"].apply(to_float)

total = all_df["amount"].sum()
print(f"组合总资产: {total:,.2f}")

# ---------- 2. 赛道映射 (code -> 赛道) ----------
TRACK_MAP = {
    # A股医药
    "002708": "A股医药", "000727": "A股医药", "161616": "A股医药",
    "001180": "A股医药", "012323": "A股医药", "001551": "A股医药",
    "159938": "A股医药", "512170": "A股医药",
    # 大消费 (含养老主题 000968, 与盘前口径一致)
    "519915": "大消费", "000248": "大消费", "159928": "大消费",
    "004424": "大消费", "000968": "大消费",
    # 美股标普医药
    "000369": "美股标普医药", "016280": "美股标普医药",
    # 恒生科技 (含中概互联 513050/164906, 与盘前口径一致)
    "012348": "恒生科技", "513180": "恒生科技",
    "513050": "恒生科技", "164906": "恒生科技",
    # 港股宽基 (归其他)
    "000071": "其他/宽基", "159920": "其他/宽基",
    # 现金
    "余额宝": "现金", "货币资金": "现金",
}
def track_of(row):
    code = str(row["code"]) if pd.notna(row["code"]) else ""
    code6 = re.sub(r"\D", "", code)  # 剥离 .SH/.SZ 后缀
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
print(f"  合计: {track_amount.sum():,.2f}")

# ---------- 3. 盘中代理涨跌幅 (13:45 实时) ----------
# 盘中实时: ETF/指数已抓; 场外基金 T+1 用指数代理
PROXY = {
    "A股医药": 3.36,        # 医药ETF +3.41 / 医疗ETF +3.32 均值
    "大消费": 0.15,          # 消费ETF +0.15
    "美股标普医药": 0.0,     # QDII T+1, 8/6 XLV +0.18% 已反映
    "恒生科技": 0.43,        # HSTECH +0.43
    "其他/宽基": 0.77,       # 上证 +0.77 (宽基近似)
    "现金": 0.0,
}
# 对持仓逐项估算: 个股/ETF 有实时价的用实时价
ETF_REALTIME = {
    "159938": 3.41, "512170": 3.32, "159928": 0.15, "513180": 0.16,
    "513050": -0.26, "159920": 0.33, "512880": -0.27, "512980": 0.35,
    "515180": -0.56,
}
# 个股盘中价暂缺(新浪日线仅到8/6), 用指数近似: 广联达(软件)→创业板, 通威(光伏)→上证保守
STOCK_PROXY = {"002410": 2.69, "600438": 0.77}
def est_pct(row):
    code6 = re.sub(r"\D", "", str(row["code"]) if pd.notna(row["code"]) else "")
    if code6 in ETF_REALTIME:
        return ETF_REALTIME[code6]
    if code6 in STOCK_PROXY:
        return STOCK_PROXY[code6]
    return PROXY.get(row["track"], 0.0)

all_df["est_pct"] = all_df.apply(est_pct, axis=1)
all_df["est_pnl"] = all_df["amount"] * all_df["est_pct"] / 100.0

total_est = all_df["est_pnl"].sum()
print(f"\n=== 组合盘中估算收益 ===")
print(f"  估算盈亏: {total_est:,.2f} ({total_est/total*100:.2f}%)")
print("\n=== 赛道贡献 ===")
contrib = all_df.groupby("track").apply(lambda d: (d["est_pnl"].sum(), d["est_pnl"].sum()/total*100), include_groups=False)
for t, (v, p) in contrib.items():
    print(f"  {t}: {v:,.2f} ({p:.2f}pct)")

# 明细 (供报告)
detail = []
for _, r in all_df.sort_values("amount", ascending=False).iterrows():
    detail.append({
        "account": r["account"], "name": r["name"], "code": str(r["code"]),
        "track": r["track"], "amount": round(r["amount"], 2),
        "est_pct": r["est_pct"], "est_pnl": round(r["est_pnl"], 2),
    })
with open(os.path.join(BASE, "data/processed/history/portfolio_20260807.json"), "w", encoding="utf-8") as f:
    json.dump({
        "total": round(total, 2),
        "tracks": {t: {"amount": round(v, 2), "pct": round(v/total*100, 2)} for t, v in track_amount.items()},
        "est_total_pct": round(total_est/total*100, 2),
        "est_total_pnl": round(total_est, 2),
        "detail": detail,
    }, f, ensure_ascii=False, indent=1)
print("\n已保存 portfolio_20260807.json")
