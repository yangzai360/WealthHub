# -*- coding: utf-8 -*-
"""盘后档 2026-08-27：组合真实收盘收益重算（基于 8/26 收盘市值 388,639.07）+ 赛道归因"""
import os, re, json
import pandas as pd

BASE = "/Users/jieyang/Documents/WealthHub"

# 基准：8/26 收盘市值（portfolio_preopen_20260827.json）
pre = json.load(open(os.path.join(BASE, "data/processed/history/portfolio_preopen_20260827.json"), encoding="utf-8"))
base_total = pre["total_mv"]
detail = pre["detail"]
print(f"8/26 收盘基准总资产: {base_total:,.2f}")

# ---------- 8/27 真实收盘涨跌幅 ----------
# 场内 ETF 收盘（close_20260827.json 实测）
ETF_CLOSE = {
    "159938": 0.61, "512170": 0.29, "159928": 0.00, "513180": -0.51,
    "513050": -0.46, "159920": -0.46, "512880": 0.91, "512980": 0.62,
    "515180": 0.27,
}
# 场外基金 8/27 当日净值（20:00 时点已出 8 只，真实净值）
FUND_NAV_827 = {
    "000968": 0.04,   # 广发养老产业 8/27 +0.04%（真实净值）
    "100032": 0.41,   # 富国红利增强A 8/27 +0.41%（真实净值）
    "001180": 0.65,   # 广发医药卫生 8/27 +0.65%（真实净值）
    "519915": 0.11,   # 富国消费主题 8/27 +0.11%（真实净值）
    "001551": 0.63,   # 天弘医药100C 8/27 +0.63%（真实净值）
    "001469": -0.20,  # 广发金融地产 8/27 -0.20%（真实净值）
    "001552": 0.62,   # 天弘证券保险 8/27 +0.62%（真实净值）
    "002742": -0.15,  # 泓德裕祥债券 8/27 -0.15%（真实净值）
}
# A股场外基金（T+1 未出 8/27，用对应指数/ETF 代理）
FUND_PROXY = {
    "002708": 0.45,   # 大摩健康 用 医药ETF均值 +0.45%（医疗ETF +0.29%/医药ETF广发 +0.61%）
    "161616": 0.29,   # 融通医疗保健 用 医疗ETF +0.29%
    "000727": 0.45,   # 融通健康产业 用 医药ETF均值 +0.45%
    "000248": 0.04,   # 汇添富主要消费 用 中证消费 +0.04% 近似
    "004424": 0.62,   # 汇添富文体娱乐 用 传媒ETF +0.62% 近似
    "110020": 1.13,   # 易方达沪深300 用 沪指 +1.13% 近似
    "004752": 0.62,   # 广发传媒 用 传媒ETF +0.62% 代理
    "000071": -0.46,  # 华夏恒生ETF联接 用 恒生ETF华夏 -0.46% 代理（QDII T+1 明日兑现）
    "164906": -0.46,  # 交银海外互联 用 中概互联 -0.46% 代理（QDII 8/26 净值 +0.73% 已出，8/27 净值待 T+1）
    "005368": -0.92,  # 富国清洁能源 用 通威 -0.92%（光伏）代理
    "012348": -0.51,  # 天弘恒生科技A 用 恒指科技ETF -0.51% 代理（QDII T+1）
}
# QDII 广发全球医疗 A/C：基准(8/26收盘)用 8/25 净值，8/27 盘后已出 8/26 净值 -0.93%/-0.95% → 当日兑现计入
FUND_PROXY["000369"] = -0.93  # 广发全球医疗A 8/26 净值 -0.93%（对应美股 8/26 XLV -1.00%）
FUND_PROXY["016280"] = -0.95  # 广发全球医疗C 8/26 净值 -0.95%
# 个股真实收盘
STOCK_CLOSE = {"002410": 0.00, "600438": -0.92}

rows = []
for d in detail:
    code6 = re.sub(r"\D", "", str(d["code"]))
    mv = d["mv"]
    if code6 in ETF_CLOSE:
        pct = ETF_CLOSE[code6]
    elif code6 in FUND_NAV_827:
        pct = FUND_NAV_827[code6]
    elif code6 in FUND_PROXY:
        pct = FUND_PROXY[code6]
    elif code6 in STOCK_CLOSE:
        pct = STOCK_CLOSE[code6]
    else:
        pct = 0.0
    pnl = mv * pct / 100.0
    rows.append({**d, "est_pct": pct, "est_pnl": round(pnl, 2)})

df = pd.DataFrame(rows)
total_est = df["est_pnl"].sum()
print(f"\n=== 组合盘后真实收益（8/27） ===")
print(f"  估算盈亏: {total_est:,.2f} ({total_est/base_total*100:.2f}%)")
print(f"  8/27 收盘总资产估算: {base_total + total_est:,.2f}")

print("\n=== 赛道贡献 ===")
contrib = df.groupby("track").apply(lambda d: (d["est_pnl"].sum(), d["est_pnl"].sum()/base_total*100), include_groups=False)
for t, (v, p) in contrib.items():
    print(f"  {t}: {v:,.2f} ({p:.2f}pct)")

# 赛道占比（8/27 收盘口径）
df["mv27"] = df["mv"] + df["est_pnl"]
track_mv = df.groupby("track")["mv27"].sum().sort_values(ascending=False)
print("\n=== 赛道占比（8/27 收盘口径） ===")
for t, v in track_mv.items():
    print(f"  {t}: {v:,.2f} ({v/(base_total+total_est)*100:.2f}%)")
med = track_mv.get("A股医药", 0) + track_mv.get("美股标普医药", 0)
print(f"\n医药总敞口: {med:,.2f} ({med/(base_total+total_est)*100:.2f}%)")

with open(os.path.join(BASE, "data/processed/history/portfolio_close_20260827.json"), "w", encoding="utf-8") as f:
    json.dump({
        "date": "2026-08-27", "as_of": "2026-08-27收盘", "base_total": round(base_total, 2),
        "est_total_pct": round(total_est/base_total*100, 2),
        "est_total_pnl": round(total_est, 2),
        "total_mv": round(base_total + total_est, 2),
        "tracks": {t: {"mv": round(v, 2), "pct": round(v/(base_total+total_est)*100, 2)} for t, v in track_mv.items()},
        "med_exposure": round(med, 2), "med_pct": round(med/(base_total+total_est)*100, 2),
        "detail": rows,
    }, f, ensure_ascii=False, indent=1)
print("\n已保存 portfolio_close_20260827.json")
