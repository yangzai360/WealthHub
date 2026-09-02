# -*- coding: utf-8 -*-
"""盘后档 2026-09-02：组合真实收盘收益重算（基准 9/1 收盘市值 385,731.39）+ 赛道归因"""
import os, re, json
import pandas as pd

BASE = "/Users/jieyang/Documents/WealthHub"

# 基准：9/1 收盘市值（portfolio_preopen_20260902.json）
pre = json.load(open(os.path.join(BASE, "data/processed/history/portfolio_preopen_20260902.json"), encoding="utf-8"))
base_total = pre["total_mv"]
detail = pre["detail"]
print(f"9/1 收盘基准总资产: {base_total:,.2f}")

# ---------- 9/2 真实收盘涨跌幅 ----------
# 场内 ETF 收盘（close_20260902.json 实测）
ETF_CLOSE = {
    "159928": -0.89, "512170": -0.88, "159938": -0.77, "513180": -1.39,
    "513050": -0.85, "159920": -0.40, "512880": -2.07, "512980": -2.47,
    "515180": -1.43,
}
# 场外基金 9/2 当日净值（20:00 时点已出 4 只，真实净值）
FUND_NAV_902 = {
    "004752": -2.31,   # 广发传媒 9/2 -2.31%（真实净值）
    "005368": -1.29,   # 富国清洁能源 9/2 -1.29%（真实净值）
    "100032": -1.51,   # 富国红利增强 9/2 -1.51%（真实净值）
    "004424": -0.88,   # 汇添富文体娱乐 9/2 -0.88%（真实净值）
}
# A股场外基金（T+1 未出 9/2，用对应指数/ETF 代理）
FUND_PROXY = {
    "000248": -0.85,   # 汇添富主要消费 用 中证消费 -0.85%（12,516.21 守 12,500）
    "002708": -0.83,   # 大摩健康 用 医药ETF均值（医疗 -0.88/医药广发 -0.77 → -0.83）
    "161616": -0.88,   # 融通医疗保健 用 医疗ETF -0.88%
    "000727": -0.83,   # 融通健康产业 用 医药ETF均值 -0.83%
    "012323": -0.88,   # 华宝中证医疗C 用 医疗ETF -0.88%
    "001180": -0.83,   # 广发医药卫生 用 医药ETF均值 -0.83%
    "001551": -0.83,   # 天弘医药100C 用 医药ETF均值 -0.83%
    "000968": -0.85,   # 广发养老产业 用 中证消费 -0.85%（养老含消费权重）
    "110020": -1.35,   # 易方达沪深300 用 沪深300 近似 -1.35%（沪指 -0.97/深成指 -1.88 之间）
    "000051": -1.35,   # 华夏沪深300 用 沪深300 近似 -1.35%
    "001469": -2.07,   # 广发金融地产 用 证券ETF -2.07% 近似
    "001552": -2.07,   # 天弘证券保险 用 证券ETF -2.07% 近似
    "000071": -0.40,   # 华夏恒生ETF联接 用 恒生ETF华夏 -0.40%（QDII 净值停 9/1，当日港股变化用 ETF 代理）
    "012348": -1.39,   # 天弘恒生科技A 用 恒指科技 -1.39%（同上）
    "164906": -0.85,   # 交银海外互联 用 中概互联 -0.85%（同上）
    "002742": 0.0,     # 泓德裕祥债券 0%（债基微波动）
}
# QDII 广发全球医疗 A/C：净值停 8/31（-0.53%/-0.54% 已含于基准）；9/1 XLV +0.66% 将于 9/3-4 兑现，今日按 0 + 缓冲单列
FUND_PROXY["000369"] = 0.0
FUND_PROXY["016280"] = 0.0
# 个股真实收盘（close_20260902.json 实测）
STOCK_CLOSE = {"002410": -2.58, "600438": -3.89}

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
    elif code6 in FUND_NAV_902:
        pct = FUND_NAV_902[code6]
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
print(f"\n=== 组合盘后真实收益（9/2） ===")
print(f"  估算盈亏: {total_est:,.2f} ({total_est/base_total*100:.2f}%)")
print(f"  9/2 收盘总资产估算: {base_total + total_est:,.2f}")

print("\n=== 赛道贡献 ===")
contrib = df.groupby("track").apply(lambda d: (d["est_pnl"].sum(), d["est_pnl"].sum()/base_total*100), include_groups=False)
for t, (v, p) in contrib.items():
    print(f"  {t}: {v:,.2f} ({p:.2f}pct)")

# 赛道占比（9/2 收盘口径）
df["mv92"] = df["mv"] + df["est_pnl"]
track_mv = df.groupby("track")["mv92"].sum().sort_values(ascending=False)
print("\n=== 赛道占比（9/2 收盘口径） ===")
for t, v in track_mv.items():
    print(f"  {t}: {v:,.2f} ({v/(base_total+total_est)*100:.2f}%)")
med = track_mv.get("A股医药", 0) + track_mv.get("美股标普医药", 0)
print(f"\n医药总敞口: {med:,.2f} ({med/(base_total+total_est)*100:.2f}%)")

with open(os.path.join(BASE, "data/processed/history/portfolio_close_20260902.json"), "w", encoding="utf-8") as f:
    json.dump({
        "date": "2026-09-02", "as_of": "2026-09-02收盘", "base_total": round(base_total, 2),
        "est_total_pct": round(total_est/base_total*100, 2),
        "est_total_pnl": round(total_est, 2),
        "total_mv": round(base_total + total_est, 2),
        "tracks": {t: {"mv": round(v, 2), "pct": round(v/(base_total+total_est)*100, 2)} for t, v in track_mv.items()},
        "med_exposure": round(med, 2), "med_pct": round(med/(base_total+total_est)*100, 2),
        "detail": rows,
    }, f, ensure_ascii=False, indent=1)
print("\n已保存 portfolio_close_20260902.json")
