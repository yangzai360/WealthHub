# -*- coding: utf-8 -*-
"""盘后档 2026-08-28：组合真实收盘收益重算（基于 8/27 收盘市值 388,442.90）+ 赛道归因"""
import os, re, json
import pandas as pd

BASE = "/Users/jieyang/Documents/WealthHub"

# 基准：8/27 收盘市值（portfolio_preopen_20260828.json）
pre = json.load(open(os.path.join(BASE, "data/processed/history/portfolio_preopen_20260828.json"), encoding="utf-8"))
base_total = pre["total_mv"]
detail = pre["detail"]
print(f"8/27 收盘基准总资产: {base_total:,.2f}")

# ---------- 8/28 真实收盘涨跌幅 ----------
# 场内 ETF 收盘（close_20260828.json 实测）
ETF_CLOSE = {
    "159928": 0.90, "512170": -1.16, "159938": -0.91, "513180": -0.34,
    "513050": 0.09, "159920": 0.00, "512880": -0.18, "512980": 0.12,
    "515180": 0.21,
}
# 场外基金 8/28 当日净值（20:00 时点已出，真实净值）
FUND_NAV_828 = {
    "005368": -0.97,   # 富国清洁能源 8/28 -0.97%（真实净值）
    "519915": -0.22,   # 富国消费主题 8/28 -0.22%（真实净值）
}
# A股场外基金（T+1 未出 8/28，用对应指数/ETF 代理）
FUND_PROXY = {
    "000248": 0.66,   # 汇添富主要消费 用 中证消费 +0.66%
    "002708": -1.04,  # 大摩健康 用 医药ETF均值（医疗 -1.16%/医药广发 -0.91%）
    "161616": -1.16,  # 融通医疗保健 用 医疗ETF -1.16%
    "000727": -1.04,  # 融通健康产业 用 医药ETF均值 -1.04%
    "012323": -1.16,  # 华宝中证医疗C 用 医疗ETF -1.16%
    "001551": -1.04,  # 天弘医药100C 用 医药ETF均值 -1.04%
    "001180": -1.04,  # 广发医药卫生 用 医药ETF均值 -1.04%
    "000968": 0.66,   # 广发养老产业 用 中证消费 +0.66% 近似
    "004424": 0.12,   # 汇添富文体娱乐 用 传媒ETF +0.12% 近似
    "110020": -0.11,  # 易方达沪深300 用 沪指 -0.11% 近似
    "000051": -0.11,  # 华夏沪深300 用 沪指 -0.11% 近似
    "100032": 0.21,   # 富国红利增强 用 100红利 +0.21% 代理
    "001469": -0.18,  # 广发金融地产 用 证券ETF -0.18% 近似
    "001552": -0.18,  # 天弘证券保险 用 证券ETF -0.18% 代理
    "000071": 0.00,   # 华夏恒生ETF联接 用 恒生ETF华夏 0.00%（QDII T+1 8/29 兑现）
    "012348": -0.34,  # 天弘恒生科技A 用 恒指科技 -0.34%（QDII T+1）
    "164906": 0.09,   # 交银海外互联 用 中概互联 +0.09%（QDII T+1；8/27 净值 -0.52% 已补更）
    "004752": 0.12,   # 广发传媒 用 传媒ETF +0.12% 代理
    "002742": 0.0,    # 泓德裕祥债券 0%（债基微波动）
}
# QDII 广发全球医疗 A/C：8/27 净值尚未更新（8/27 美股 XLV -1.13% 将于 8/29-31 兑现），今日按 0 + 缓冲单列
FUND_PROXY["000369"] = 0.0
FUND_PROXY["016280"] = 0.0
# 个股真实收盘
STOCK_CLOSE = {"002410": 2.39, "600438": 0.50}

rows = []
for d in detail:
    code6 = re.sub(r"\D", "", str(d["code"]))
    mv = d["mv"]
    if code6 in ETF_CLOSE:
        pct = ETF_CLOSE[code6]
    elif code6 in FUND_NAV_828:
        pct = FUND_NAV_828[code6]
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
print(f"\n=== 组合盘后真实收益（8/28） ===")
print(f"  估算盈亏: {total_est:,.2f} ({total_est/base_total*100:.2f}%)")
print(f"  8/28 收盘总资产估算: {base_total + total_est:,.2f}")

print("\n=== 赛道贡献 ===")
contrib = df.groupby("track").apply(lambda d: (d["est_pnl"].sum(), d["est_pnl"].sum()/base_total*100), include_groups=False)
for t, (v, p) in contrib.items():
    print(f"  {t}: {v:,.2f} ({p:.2f}pct)")

# 赛道占比（8/28 收盘口径）
df["mv28"] = df["mv"] + df["est_pnl"]
track_mv = df.groupby("track")["mv28"].sum().sort_values(ascending=False)
print("\n=== 赛道占比（8/28 收盘口径） ===")
for t, v in track_mv.items():
    print(f"  {t}: {v:,.2f} ({v/(base_total+total_est)*100:.2f}%)")
med = track_mv.get("A股医药", 0) + track_mv.get("美股标普医药", 0)
print(f"\n医药总敞口: {med:,.2f} ({med/(base_total+total_est)*100:.2f}%)")

with open(os.path.join(BASE, "data/processed/history/portfolio_close_20260828.json"), "w", encoding="utf-8") as f:
    json.dump({
        "date": "2026-08-28", "as_of": "2026-08-28收盘", "base_total": round(base_total, 2),
        "est_total_pct": round(total_est/base_total*100, 2),
        "est_total_pnl": round(total_est, 2),
        "total_mv": round(base_total + total_est, 2),
        "tracks": {t: {"mv": round(v, 2), "pct": round(v/(base_total+total_est)*100, 2)} for t, v in track_mv.items()},
        "med_exposure": round(med, 2), "med_pct": round(med/(base_total+total_est)*100, 2),
        "detail": rows,
    }, f, ensure_ascii=False, indent=1)
print("\n已保存 portfolio_close_20260828.json")
