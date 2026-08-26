# -*- coding: utf-8 -*-
"""盘后档 2026-08-26：组合真实收盘收益重算（基于 8/25 收盘市值 387,234.70）+ 赛道归因"""
import os, re, json
import pandas as pd

BASE = "/Users/jieyang/Documents/WealthHub"

# 基准：8/25 收盘市值（portfolio_preopen_20260826.json）
pre = json.load(open(os.path.join(BASE, "data/processed/history/portfolio_preopen_20260826.json"), encoding="utf-8"))
base_total = pre["total_mv"]
detail = pre["detail"]
print(f"8/25 收盘基准总资产: {base_total:,.2f}")

# ---------- 8/26 真实收盘涨跌幅 ----------
# 场内 ETF 收盘（close_20260826.json 实测）
ETF_CLOSE = {
    "159938": 0.15, "512170": -0.58, "159928": 0.15, "513180": 1.21,
    "513050": 1.21, "159920": 0.80, "512880": 2.72, "512980": -0.37,
    "515180": 0.69,
}
# 场外基金 8/26 当日净值（20:00 时点已出 4 只）
FUND_NAV_826 = {
    "000051": 0.82,   # 华夏沪深300 8/26 +0.82%（真实净值）
    "519915": -0.48,  # 富国消费主题 8/26 -0.48%（真实净值）
    "012348": 0.72,   # 天弘恒生科技A 8/26 +0.72%（真实净值）
    "012323": -0.82,  # 华宝中证医疗C 8/26 -0.82%（真实净值）
}
# A股场外基金（T+1 未出 8/26，用对应指数/ETF 代理）
FUND_PROXY = {
    "002708": -0.22,  # 大摩健康 用 医药ETF均值 -0.22%（医疗ETF -0.58%/医药ETF广发 +0.15%）
    "161616": -0.58,  # 融通医疗保健 用 医疗ETF -0.58%
    "000727": -0.22,  # 融通健康产业 用 医药ETF均值 -0.22%
    "001180": -0.22,  # 广发医药卫生 用 医药ETF均值 -0.22%
    "001551": -0.22,  # 天弘医药100C 用 医药ETF均值 -0.22%
    "000248": -0.06,  # 汇添富主要消费 用 中证消费 -0.06% 近似
    "000968": -0.14,  # 广发养老产业 用 医药消费折中 -0.14%
    "004424": -0.06,  # 汇添富文体娱乐 用 中证消费 -0.06% 近似
    "110020": 0.59,   # 易方达沪深300 用 沪指 +0.59% 近似
    "001469": 2.72,   # 广发金融地产 用 证券ETF +2.72% 近似
    "001552": 2.72,   # 天弘证券保险 用 证券ETF +2.72% 近似
    "004752": -0.37,  # 广发传媒 用 传媒ETF -0.37% 代理
    "002742": 0.10,   # 泓德裕祥债券 用 债券微涨
    "000071": 0.56,   # 华夏恒生ETF联接 用 恒指 +0.56% 代理（QDII T+1 明日兑现）
    "164906": 1.21,   # 交银海外互联 用 中概互联 +1.21% 代理（QDII T+1 明日兑现）
    "005368": 0.00,   # 富国清洁能源 用 通威 0.00%（光伏）代理
    "100032": 0.69,   # 富国红利增强A 8/26 未出 用 100红利 +0.69% 代理
}
# QDII 广发全球医疗 A/C：8/25 XLV +0.34% 需 8/27-28 兑现 → 今日按 0
# 个股真实收盘
STOCK_CLOSE = {"002410": 2.09, "600438": 0.00}

rows = []
for d in detail:
    code6 = re.sub(r"\D", "", str(d["code"]))
    mv = d["mv"]
    if code6 in ETF_CLOSE:
        pct = ETF_CLOSE[code6]
    elif code6 in FUND_NAV_826:
        pct = FUND_NAV_826[code6]
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
print(f"\n=== 组合盘后真实收益（8/26） ===")
print(f"  估算盈亏: {total_est:,.2f} ({total_est/base_total*100:.2f}%)")
print(f"  8/26 收盘总资产估算: {base_total + total_est:,.2f}")

print("\n=== 赛道贡献 ===")
contrib = df.groupby("track").apply(lambda d: (d["est_pnl"].sum(), d["est_pnl"].sum()/base_total*100), include_groups=False)
for t, (v, p) in contrib.items():
    print(f"  {t}: {v:,.2f} ({p:.2f}pct)")

# 赛道占比（8/26 收盘口径）
df["mv26"] = df["mv"] + df["est_pnl"]
track_mv = df.groupby("track")["mv26"].sum().sort_values(ascending=False)
print("\n=== 赛道占比（8/26 收盘口径） ===")
for t, v in track_mv.items():
    print(f"  {t}: {v:,.2f} ({v/(base_total+total_est)*100:.2f}%)")
med = track_mv.get("A股医药", 0) + track_mv.get("美股标普医药", 0)
print(f"\n医药总敞口: {med:,.2f} ({med/(base_total+total_est)*100:.2f}%)")

with open(os.path.join(BASE, "data/processed/history/portfolio_close_20260826.json"), "w", encoding="utf-8") as f:
    json.dump({
        "date": "2026-08-26", "as_of": "2026-08-26收盘", "base_total": round(base_total, 2),
        "est_total_pct": round(total_est/base_total*100, 2),
        "est_total_pnl": round(total_est, 2),
        "total_mv": round(base_total + total_est, 2),
        "tracks": {t: {"mv": round(v, 2), "pct": round(v/(base_total+total_est)*100, 2)} for t, v in track_mv.items()},
        "med_exposure": round(med, 2), "med_pct": round(med/(base_total+total_est)*100, 2),
        "detail": rows,
    }, f, ensure_ascii=False, indent=1)
print("\n已保存 portfolio_close_20260826.json")
