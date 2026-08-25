# -*- coding: utf-8 -*-
"""盘后档 2026-08-25：组合真实收盘收益重算（基于 8/24 收盘市值 386,211.25）+ 赛道归因"""
import os, re, json, csv
import pandas as pd

BASE = "/Users/jieyang/Documents/WealthHub"

# 基准：8/24 收盘市值（portfolio_preopen_20260825.json）
pre = json.load(open(os.path.join(BASE, "data/processed/history/portfolio_preopen_20260825.json"), encoding="utf-8"))
base_total = pre["total_mv"]
detail = pre["detail"]
print(f"8/24 收盘基准总资产: {base_total:,.2f}")

# ---------- 8/25 真实收盘涨跌幅 ----------
# 场内 ETF 收盘（close_20260825.json 实测）
ETF_CLOSE = {
    "159938": 1.71, "512170": 2.36, "159928": 0.61, "513180": -0.17,
    "513050": 0.09, "159920": -0.07, "512880": 0.00, "512980": 1.77,
    "515180": -0.55,
}
# 场外基金 8/25 当日净值（已出 2 只）
FUND_NAV_825 = {
    "519915": 1.80,   # 富国消费主题 8/25 +1.80%（真实净值）
    "100032": -0.61,  # 富国红利增强A 8/25 -0.61%（真实净值）
}
# A股场外基金（T+1 未出 8/25，用对应指数/ETF 代理）
FUND_PROXY = {
    "002708": 2.04,   # 大摩健康 用 医药ETF均值 +2.04%（医疗ETF +2.36%/医药ETF广发 +1.71%）
    "161616": 2.36,   # 融通医疗保健 用 医疗ETF +2.36%
    "012323": 2.36,   # 华宝中证医疗C 用 医疗ETF +2.36%
    "000727": 2.04,   # 融通健康产业 用 医药ETF均值 +2.04%
    "001180": 2.04,   # 广发医药卫生 用 医药ETF均值 +2.04%
    "001551": 2.04,   # 天弘医药100C 用 医药ETF均值 +2.04%
    "000248": 0.59,   # 汇添富主要消费 用 中证消费 +0.59% 近似
    "000968": 1.50,   # 广发养老产业 用 医药消费折中 +1.50%（8/24 -1.83% 介于医药/消费间偏医药）
    "004424": 0.59,   # 汇添富文体娱乐 用 中证消费 +0.59% 近似
    "110020": 0.19,   # 易方达沪深300 用 沪指 +0.19% 近似
    "000051": 0.19,   # 华夏沪深300 用 沪指 +0.19% 近似
    "001469": 0.00,   # 广发金融地产 用 证券ETF 0.00% 近似
    "001552": 0.00,   # 天弘证券保险 用 证券ETF 0.00% 近似
    "004752": 1.77,   # 广发传媒 用 传媒ETF +1.77% 代理
    "002742": 0.10,   # 泓德裕祥债券 用 债券微涨
    "000071": -0.02,  # 华夏恒生ETF联接 用 恒指 -0.02% 代理（QDII T+1 明日兑现）
    "012348": -0.12,  # 天弘恒生科技 用 HSTECH -0.12% 代理（QDII T+1 明日兑现）
    "164906": 0.09,   # 交银海外互联 用 中概互联 +0.09% 代理（QDII T+1 明日兑现）
    "005368": -0.91,  # 富国清洁能源 用 通威 -0.91%（光伏）代理
}
# QDII 广发全球医疗 A/C：8/24 美股基本持平（XLV +0.05%/IYH -0.07%）需 8/26-27 兑现 → 今日按 0
# 个股真实收盘
STOCK_CLOSE = {"002410": -3.26, "600438": -0.91}

rows = []
for d in detail:
    code6 = re.sub(r"\D", "", str(d["code"]))
    mv = d["mv"]
    if code6 in ETF_CLOSE:
        pct = ETF_CLOSE[code6]
    elif code6 in FUND_NAV_825:
        pct = FUND_NAV_825[code6]
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
print(f"\n=== 组合盘后真实收益（8/25） ===")
print(f"  估算盈亏: {total_est:,.2f} ({total_est/base_total*100:.2f}%)")
print(f"  8/25 收盘总资产估算: {base_total + total_est:,.2f}")

print("\n=== 赛道贡献 ===")
contrib = df.groupby("track").apply(lambda d: (d["est_pnl"].sum(), d["est_pnl"].sum()/base_total*100), include_groups=False)
for t, (v, p) in contrib.items():
    print(f"  {t}: {v:,.2f} ({p:.2f}pct)")

# 赛道占比（8/25 收盘口径）
df["mv25"] = df["mv"] + df["est_pnl"]
track_mv = df.groupby("track")["mv25"].sum().sort_values(ascending=False)
print("\n=== 赛道占比（8/25 收盘口径） ===")
for t, v in track_mv.items():
    print(f"  {t}: {v:,.2f} ({v/(base_total+total_est)*100:.2f}%)")
med = track_mv.get("A股医药", 0) + track_mv.get("美股标普医药", 0)
print(f"\n医药总敞口: {med:,.2f} ({med/(base_total+total_est)*100:.2f}%)")

with open(os.path.join(BASE, "data/processed/history/portfolio_close_20260825.json"), "w", encoding="utf-8") as f:
    json.dump({
        "date": "2026-08-25", "as_of": "2026-08-25收盘", "base_total": round(base_total, 2),
        "est_total_pct": round(total_est/base_total*100, 2),
        "est_total_pnl": round(total_est, 2),
        "total_mv": round(base_total + total_est, 2),
        "tracks": {t: {"mv": round(v, 2), "pct": round(v/(base_total+total_est)*100, 2)} for t, v in track_mv.items()},
        "med_exposure": round(med, 2), "med_pct": round(med/(base_total+total_est)*100, 2),
        "detail": rows,
    }, f, ensure_ascii=False, indent=1)
print("\n已保存 portfolio_close_20260825.json")
