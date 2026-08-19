# -*- coding: utf-8 -*-
"""盘后档 2026-08-19：组合真实收盘收益重算 + 赛道归因"""
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

total = all_df["amount"].sum()
print(f"组合总资产(快照): {total:,.2f}")

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

# ---------- 8/19 真实收盘涨跌幅 ----------
# 场内 ETF 收盘（close_20260819.json 实测）
ETF_CLOSE = {
    "159938": -1.62, "512170": -2.55, "159928": -1.04, "513180": -1.50,
    "513050": -0.18, "159920": -0.13, "512880": -1.39, "512980": -4.18,
    "515180": 0.49,
}
# 场外基金 8/19 当日净值（已出）
FUND_NAV_819 = {
    "519915": -1.84,   # 富国消费主题 8/19 -1.84%（真实净值）
    "012323": -2.56,   # 华宝中证医疗C 8/19 -2.56%（真实净值）
}
# QDII 今日净值未动（8/18 美股 +1.59% 于 8/20-21 兑现）——广发全球医疗 A/C 按 0 计
# A股场外基金（T+1 未出 8/19，用对应指数/ETF 代理）
FUND_PROXY = {
    "002708": -2.09,   # 大摩健康 用 医药ETF均值 -2.09%
    "000727": -2.09,   # 融通健康 同上
    "001180": -2.09,   # 广发医药卫生 同上
    "001551": -2.09,   # 天弘医药100 同上
    "161616": -2.55,   # 融通医疗保健 用 医疗ETF -2.55%
    "000248": -1.08,   # 汇添富主要消费 用 中证消费 -1.08% 代理
    "000968": -1.20,   # 广发养老 用 消费医药均衡近似
    "005368": -3.76,   # 富国清洁能源 用 通威 -3.76% 代理（光伏）
    "110020": -2.90,   # 易方达沪深300 用 沪深300 -2.90% 代理
    "000051": -2.90,   # 华夏沪深300 同上
    "001469": -0.80,   # 广发金融地产 用 银行稳/证券弱近似（内银活跃）
    "001552": -1.39,   # 天弘证券保险 用 证券ETF -1.39% 代理
    "100032": 0.49,    # 富国红利增强 用 100红利 +0.49% 代理
    "004752": -4.18,   # 广发传媒 用 传媒ETF -4.18% 代理
    "002742": 0.0,     # 泓德裕祥债券 0
    "000071": 0.09,    # 华夏恒生ETF联接 用 恒指 +0.09% 代理（QDII T+1 明日兑现）
    "012348": -1.21,   # 天弘恒生科技 用 HSTECH -1.21% 代理（QDII T+1 明日兑现）
    "164906": -0.18,   # 交银海外互联 用 中概互联ETF -0.18% 代理（8/18 净值 -0.23% 已归档）
    "004424": -1.50,   # 汇添富文体 用 文体消费科技均衡近似
    "000369": 0.0,     # 广发全球医疗A QDII 净值未动（8/18 美股 +1.59% 8/20-21 兑现）
    "016280": 0.0,     # 广发全球医疗C 同上
}
# 个股真实收盘
STOCK_CLOSE = {"002410": -2.21, "600438": -3.76}
def est_pct(row):
    code6 = re.sub(r"\D", "", str(row["code"]) if pd.notna(row["code"]) else "")
    if code6 in ETF_CLOSE:
        return ETF_CLOSE[code6]
    if code6 in FUND_NAV_819:
        return FUND_NAV_819[code6]
    if code6 in FUND_PROXY:
        return FUND_PROXY[code6]
    if code6 in STOCK_CLOSE:
        return STOCK_CLOSE[code6]
    return 0.0

all_df["est_pct"] = all_df.apply(est_pct, axis=1)
all_df["est_pnl"] = all_df["amount"] * all_df["est_pct"] / 100.0

total_est = all_df["est_pnl"].sum()
print(f"\n=== 组合盘后真实收益 ===")
print(f"  估算盈亏: {total_est:,.2f} ({total_est/total*100:.2f}%)")
print("\n=== 赛道贡献 ===")
contrib = all_df.groupby("track").apply(lambda d: (d["est_pnl"].sum(), d["est_pnl"].sum()/total*100), include_groups=False)
for t, (v, p) in contrib.items():
    print(f"  {t}: {v:,.2f} ({p:.2f}pct)")

detail = []
for _, r in all_df.sort_values("amount", ascending=False).iterrows():
    detail.append({
        "account": r["account"], "name": r["name"], "code": str(r["code"]),
        "track": r["track"], "amount": round(r["amount"], 2),
        "est_pct": r["est_pct"], "est_pnl": round(r["est_pnl"], 2),
    })
with open(os.path.join(BASE, "data/processed/history/portfolio_close_20260819.json"), "w", encoding="utf-8") as f:
    json.dump({
        "total": round(total, 2),
        "tracks": {t: {"amount": round(v, 2), "pct": round(v/total*100, 2)} for t, v in track_amount.items()},
        "est_total_pct": round(total_est/total*100, 2),
        "est_total_pnl": round(total_est, 2),
        "detail": detail,
    }, f, ensure_ascii=False, indent=1)
print("\n已保存 portfolio_close_20260819.json")
