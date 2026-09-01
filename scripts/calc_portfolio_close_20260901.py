# -*- coding: utf-8 -*-
"""盘后档 2026-09-01：组合真实收盘收益重算（基于 8/31 收盘市值 386,153.30）+ 赛道归因"""
import os, re, json
import pandas as pd

BASE = "/Users/jieyang/Documents/WealthHub"

# 基准：8/31 收盘市值（portfolio_preopen_20260901.json）
pre = json.load(open(os.path.join(BASE, "data/processed/history/portfolio_preopen_20260901.json"), encoding="utf-8"))
base_total = pre["total_mv"]
detail = pre["detail"]
print(f"8/31 收盘基准总资产: {base_total:,.2f}")

# ---------- 9/1 真实收盘涨跌幅 ----------
# 场内 ETF 收盘（close_20260901.json 实测）
ETF_CLOSE = {
    "159928": 1.20, "512170": 0.59, "159938": 0.47, "513180": -0.86,
    "513050": -1.76, "159920": -0.47, "512880": 0.72, "512980": 1.19,
    "515180": 0.07,
}
# 场外基金 9/1 当日净值（20:00 时点已出 4 只，真实净值）
FUND_NAV_901 = {
    "004752": 1.09,   # 广发传媒 9/1 +1.09%（真实净值）
    "005368": -0.68,  # 富国清洁能源 9/1 -0.68%（真实净值）
    "519915": 0.92,   # 富国消费主题 9/1 +0.92%（真实净值）
    "004424": -0.14,  # 汇添富文体娱乐 9/1 -0.14%（真实净值）
}
# A股场外基金（T+1 未出 9/1，用对应指数/ETF 代理）
FUND_PROXY = {
    "000248": 1.15,   # 汇添富主要消费 用 中证消费 +1.15%
    "002708": 0.53,   # 大摩健康 用 医药ETF均值（医疗 +0.59/医药广发 +0.47 → +0.53）
    "161616": 0.59,   # 融通医疗保健 用 医疗ETF +0.59%
    "000727": 0.53,   # 融通健康产业 用 医药ETF均值 +0.53%
    "012323": 0.59,   # 华宝中证医疗C 用 医疗ETF +0.59%
    "001180": 0.53,   # 广发医药卫生 用 医药ETF均值 +0.53%
    "001551": 0.53,   # 天弘医药100C 用 医药ETF均值 +0.53%
    "000968": 1.15,   # 广发养老产业 用 中证消费 +1.15%（养老含消费权重）
    "110020": -0.30,  # 易方达沪深300 用 沪深300 -0.30%
    "000051": -0.30,  # 华夏沪深300 用 沪深300 -0.30%
    "100032": 0.07,   # 富国红利增强 用 100红利 +0.07% 代理
    "001469": 0.72,   # 广发金融地产 用 证券ETF +0.72% 近似
    "001552": 0.72,   # 天弘证券保险 用 证券ETF +0.72% 近似
    "000071": -0.47,  # 华夏恒生ETF联接 用 恒生ETF华夏 -0.47%（QDII T+1 9/2 兑现）
    "012348": -0.86,  # 天弘恒生科技A 用 恒指科技 -0.86%（QDII T+1）
    "164906": -1.76,  # 交银海外互联 用 中概互联 -1.76%（QDII T+1）
    "002742": 0.0,    # 泓德裕祥债券 0%（债基微波动）
}
# QDII 广发全球医疗 A/C：8/28 净值已兑现（-0.38%/-0.35%），8/31 XLV -0.36% 将于 9/2-3 兑现，今日按 0 + 缓冲单列
FUND_PROXY["000369"] = 0.0
FUND_PROXY["016280"] = 0.0
# 个股真实收盘（close_20260901.json 实测）
STOCK_CLOSE = {"002410": -0.89, "600438": 1.98}

rows = []
for d in detail:
    code6 = re.sub(r"\D", "", str(d["code"]))
    mv = d["mv"]
    if code6 in ETF_CLOSE:
        pct = ETF_CLOSE[code6]
    elif code6 in FUND_NAV_901:
        pct = FUND_NAV_901[code6]
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
print(f"\n=== 组合盘后真实收益（9/1） ===")
print(f"  估算盈亏: {total_est:,.2f} ({total_est/base_total*100:.2f}%)")
print(f"  9/1 收盘总资产估算: {base_total + total_est:,.2f}")

print("\n=== 赛道贡献 ===")
contrib = df.groupby("track").apply(lambda d: (d["est_pnl"].sum(), d["est_pnl"].sum()/base_total*100), include_groups=False)
for t, (v, p) in contrib.items():
    print(f"  {t}: {v:,.2f} ({p:.2f}pct)")

# 赛道占比（9/1 收盘口径）
df["mv91"] = df["mv"] + df["est_pnl"]
track_mv = df.groupby("track")["mv91"].sum().sort_values(ascending=False)
print("\n=== 赛道占比（9/1 收盘口径） ===")
for t, v in track_mv.items():
    print(f"  {t}: {v:,.2f} ({v/(base_total+total_est)*100:.2f}%)")
med = track_mv.get("A股医药", 0) + track_mv.get("美股标普医药", 0)
print(f"\n医药总敞口: {med:,.2f} ({med/(base_total+total_est)*100:.2f}%)")

with open(os.path.join(BASE, "data/processed/history/portfolio_close_20260901.json"), "w", encoding="utf-8") as f:
    json.dump({
        "date": "2026-09-01", "as_of": "2026-09-01收盘", "base_total": round(base_total, 2),
        "est_total_pct": round(total_est/base_total*100, 2),
        "est_total_pnl": round(total_est, 2),
        "total_mv": round(base_total + total_est, 2),
        "tracks": {t: {"mv": round(v, 2), "pct": round(v/(base_total+total_est)*100, 2)} for t, v in track_mv.items()},
        "med_exposure": round(med, 2), "med_pct": round(med/(base_total+total_est)*100, 2),
        "detail": rows,
    }, f, ensure_ascii=False, indent=1)
print("\n已保存 portfolio_close_20260901.json")
