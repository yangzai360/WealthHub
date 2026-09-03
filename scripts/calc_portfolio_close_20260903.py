# -*- coding: utf-8 -*-
"""盘后档 2026-09-03：组合真实收盘收益重算（基准 9/2 收盘全量净值口径 382,989.21）+ 赛道归因"""
import os, re, json
import pandas as pd

BASE = "/Users/jieyang/Documents/WealthHub"

# 基准：9/2 收盘全量净值口径（portfolio_preopen_20260903.json）
pre = json.load(open(os.path.join(BASE, "data/processed/history/portfolio_preopen_20260903.json"), encoding="utf-8"))
base_total = pre["total_mv"]
detail = pre["detail"]
print(f"9/2 收盘基准总资产: {base_total:,.2f}")

# ---------- 9/3 真实收盘涨跌幅 ----------
# 场内 ETF 收盘（close_20260903.json 实测）
ETF_CLOSE = {
    "159928": -0.45, "512170": 0.30, "159938": 0.47, "513180": -0.70,
    "513050": -1.43, "159920": -0.13, "512880": 0.73, "512980": -0.48,
    "515180": 0.14,
}
# 场外基金 9/3 当日净值（20:00 时点已出 3 只，真实净值）
FUND_NAV_903 = {
    "005368": 0.17,   # 富国清洁能源 9/3 +0.17%（真实净值）
    "519915": 0.65,   # 富国消费主题 9/3 +0.65%（真实净值，主动基逆势翻红）
    "004424": 0.23,   # 汇添富文体娱乐 9/3 +0.23%（真实净值）
}
# A股场外基金（T+1 未出 9/3，用对应指数/ETF 代理）
MED_AVG = round((ETF_CLOSE["512170"] + ETF_CLOSE["159938"]) / 2, 2)  # +0.39
FUND_PROXY = {
    "000248": -0.30,   # 汇添富主要消费 用 中证消费 -0.30%（12,478.59 失守 12,500）
    "002708": MED_AVG, # 大摩健康 用 医药ETF均值 +0.39%
    "161616": MED_AVG, # 融通医疗保健 用 医药ETF均值 +0.39%
    "000727": MED_AVG, # 融通健康产业 用 医药ETF均值 +0.39%
    "012323": MED_AVG, # 华宝中证医疗C 用 医药ETF均值 +0.39%
    "001180": MED_AVG, # 广发医药卫生 用 医药ETF均值 +0.39%
    "001551": MED_AVG, # 天弘医药100C 用 医药ETF均值 +0.39%
    "000968": -0.30,   # 广发养老产业 用 中证消费 -0.30%
    "110020": 0.05,    # 易方达沪深300 用 沪深300 近似 +0.05%（沪指 +0.02/深成指 +0.10）
    "000051": 0.05,    # 华夏沪深300 用 沪深300 近似 +0.05%
    "001469": 0.73,    # 广发金融地产 用 证券ETF +0.73%
    "001552": 0.73,    # 天弘证券保险 用 证券ETF +0.73%
    "000071": -0.13,   # 华夏恒生ETF联接 用 恒生ETF华夏 -0.13%（QDII 净值停 9/1）
    "012348": -0.70,   # 天弘恒生科技A 用 恒指科技 -0.70%（同上）
    "164906": -1.43,   # 交银海外互联 用 中概互联 -1.43%（同上）
    "002742": 0.0,     # 泓德裕祥债券 0%
    "100032": 0.14,    # 富国红利增强 用 100红利 +0.14%
    "004752": -0.48,   # 广发传媒 用 传媒ETF -0.48%
}
# QDII 广发全球医疗 A/C：净值停 9/1（已含于基准）；9/2 XLV +0.75% 将于 9/4-5 兑现，今日按 0 + 缓冲单列
FUND_PROXY["000369"] = 0.0
FUND_PROXY["016280"] = 0.0
# 个股真实收盘（close_20260903.json 实测）
STOCK_CLOSE = {"002410": -0.92, "600438": -0.70}

rows = []
for d in detail:
    code_raw = str(d.get("code", ""))
    code6 = re.sub(r"\D", "", code_raw)
    mv = d["mv"]
    track = d.get("track", "?")
    if not code6 or code_raw.strip() == "" or track == "现金":
        pct = 0.0
    elif code6 in ETF_CLOSE:
        pct = ETF_CLOSE[code6]
    elif code6 in FUND_NAV_903:
        pct = FUND_NAV_903[code6]
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
print(f"\n=== 组合盘后真实收益（9/3） ===")
print(f"  估算盈亏: {total_est:,.2f} ({total_est/base_total*100:.2f}%)")
print(f"  9/3 收盘总资产估算: {base_total + total_est:,.2f}")

print("\n=== 赛道贡献 ===")
contrib = df.groupby("track").apply(lambda d: (d["est_pnl"].sum(), d["est_pnl"].sum()/base_total*100), include_groups=False)
for t, (v, p) in contrib.items():
    print(f"  {t}: {v:,.2f} ({p:.2f}pct)")

# 赛道占比（9/3 收盘口径）
df["mv93"] = df["mv"] + df["est_pnl"]
track_mv = df.groupby("track")["mv93"].sum().sort_values(ascending=False)
print("\n=== 赛道占比（9/3 收盘口径） ===")
for t, v in track_mv.items():
    print(f"  {t}: {v:,.2f} ({v/(base_total+total_est)*100:.2f}%)")
med = track_mv.get("A股医药", 0) + track_mv.get("美股标普医药", 0)
print(f"\n医药总敞口: {med:,.2f} ({med/(base_total+total_est)*100:.2f}%)")

with open(os.path.join(BASE, "data/processed/history/portfolio_close_20260903.json"), "w", encoding="utf-8") as f:
    json.dump({
        "date": "2026-09-03", "as_of": "2026-09-03收盘", "base_total": round(base_total, 2),
        "est_total_pct": round(total_est/base_total*100, 2),
        "est_total_pnl": round(total_est, 2),
        "total_mv": round(base_total + total_est, 2),
        "tracks": {t: {"mv": round(v, 2), "pct": round(v/(base_total+total_est)*100, 2)} for t, v in track_mv.items()},
        "med_exposure": round(med, 2), "med_pct": round(med/(base_total+total_est)*100, 2),
        "detail": rows,
    }, f, ensure_ascii=False, indent=1)
print("\n已保存 portfolio_close_20260903.json")
