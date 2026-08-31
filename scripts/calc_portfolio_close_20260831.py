# -*- coding: utf-8 -*-
"""盘后档 2026-08-31：组合真实收盘收益重算（基于 8/28 收盘市值 387,658.66）+ 赛道归因"""
import os, re, json
import pandas as pd

BASE = "/Users/jieyang/Documents/WealthHub"

# 基准：8/28 收盘市值（portfolio_preopen_20260831.json）
pre = json.load(open(os.path.join(BASE, "data/processed/history/portfolio_preopen_20260831.json"), encoding="utf-8"))
base_total = pre["total_mv"]
detail = pre["detail"]
print(f"8/28 收盘基准总资产: {base_total:,.2f}")

# ---------- 8/31 真实收盘涨跌幅 ----------
# 场内 ETF 收盘（close_20260831.json 实测）
ETF_CLOSE = {
    "159928": -0.75, "512170": -0.88, "159938": -1.38, "513180": 0.17,
    "513050": -0.28, "159920": -0.47, "512880": 0.09, "512980": 3.83,
    "515180": 0.41,
}
# 场外基金 8/31 当日净值（20:00 时点已出 6 只，真实净值）
FUND_NAV_831 = {
    "000968": -0.84,   # 广发养老产业 8/31 -0.84%（真实净值）
    "004752": 3.54,    # 广发传媒 8/31 +3.54%（真实净值）
    "005368": -0.98,   # 富国清洁能源 8/31 -0.98%（真实净值）
    "001551": -1.15,   # 天弘医药100C 8/31 -1.15%（真实净值）
    "001552": 0.18,    # 天弘证券保险 8/31 +0.18%（真实净值）
    "004424": -0.57,   # 汇添富文体娱乐 8/31 -0.57%（真实净值）
}
# A股场外基金（T+1 未出 8/31，用对应指数/ETF 代理）
FUND_PROXY = {
    "000248": -0.72,   # 汇添富主要消费 用 中证消费 -0.72%
    "002708": -1.13,   # 大摩健康 用 医药ETF均值（医疗 -0.88/医药广发 -1.38）
    "161616": -0.88,   # 融通医疗保健 用 医疗ETF -0.88%
    "000727": -1.13,   # 融通健康产业 用 医药ETF均值 -1.13%
    "012323": -0.88,   # 华宝中证医疗C 用 医疗ETF -0.88%
    "001180": -1.13,   # 广发医药卫生 用 医药ETF均值 -1.13%
    "519915": -0.72,   # 富国消费主题 用 中证消费 -0.72%（8/31 净值 T+1 未出）
    "110020": 0.86,    # 易方达沪深300 用 沪指 +0.86% 近似
    "000051": 0.86,    # 华夏沪深300 用 沪指 +0.86% 近似
    "100032": 0.41,    # 富国红利增强 用 100红利 +0.41% 代理
    "001469": 0.09,    # 广发金融地产 用 证券ETF +0.09% 近似
    "000071": -0.47,   # 华夏恒生ETF联接 用 恒生ETF华夏 -0.47%（QDII T+1 9/1 兑现）
    "012348": 0.17,    # 天弘恒生科技A 用 恒指科技 +0.17%（QDII T+1）
    "164906": -0.28,   # 交银海外互联 用 中概互联 -0.28%（QDII T+1）
    "002742": 0.0,     # 泓德裕祥债券 0%（债基微波动）
}
# QDII 广发全球医疗 A/C：8/27 净值已兑现（-1.02%/-1.03%），8/28 美股 XLV -0.24% 将于 9/1-2 兑现，今日按 0 + 缓冲单列
FUND_PROXY["000369"] = 0.0
FUND_PROXY["016280"] = 0.0
# 个股真实收盘（close_20260831.json 实测）
STOCK_CLOSE = {"002410": -0.11, "600438": -3.09}

rows = []
for d in detail:
    code6 = re.sub(r"\D", "", str(d["code"]))
    mv = d["mv"]
    if code6 in ETF_CLOSE:
        pct = ETF_CLOSE[code6]
    elif code6 in FUND_NAV_831:
        pct = FUND_NAV_831[code6]
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
print(f"\n=== 组合盘后真实收益（8/31） ===")
print(f"  估算盈亏: {total_est:,.2f} ({total_est/base_total*100:.2f}%)")
print(f"  8/31 收盘总资产估算: {base_total + total_est:,.2f}")

print("\n=== 赛道贡献 ===")
contrib = df.groupby("track").apply(lambda d: (d["est_pnl"].sum(), d["est_pnl"].sum()/base_total*100), include_groups=False)
for t, (v, p) in contrib.items():
    print(f"  {t}: {v:,.2f} ({p:.2f}pct)")

# 赛道占比（8/31 收盘口径）
df["mv31"] = df["mv"] + df["est_pnl"]
track_mv = df.groupby("track")["mv31"].sum().sort_values(ascending=False)
print("\n=== 赛道占比（8/31 收盘口径） ===")
for t, v in track_mv.items():
    print(f"  {t}: {v:,.2f} ({v/(base_total+total_est)*100:.2f}%)")
med = track_mv.get("A股医药", 0) + track_mv.get("美股标普医药", 0)
print(f"\n医药总敞口: {med:,.2f} ({med/(base_total+total_est)*100:.2f}%)")

with open(os.path.join(BASE, "data/processed/history/portfolio_close_20260831.json"), "w", encoding="utf-8") as f:
    json.dump({
        "date": "2026-08-31", "as_of": "2026-08-31收盘", "base_total": round(base_total, 2),
        "est_total_pct": round(total_est/base_total*100, 2),
        "est_total_pnl": round(total_est, 2),
        "total_mv": round(base_total + total_est, 2),
        "tracks": {t: {"mv": round(v, 2), "pct": round(v/(base_total+total_est)*100, 2)} for t, v in track_mv.items()},
        "med_exposure": round(med, 2), "med_pct": round(med/(base_total+total_est)*100, 2),
        "detail": rows,
    }, f, ensure_ascii=False, indent=1)
print("\n已保存 portfolio_close_20260831.json")
