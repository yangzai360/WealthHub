# -*- coding: utf-8 -*-
"""2026-09-16 盘中档：组合盘中估算（13:48 口径）
基准：9/15 盘后归档链式总资产 375,505.37；权重取 portfolio_preopen_20260916.json 明细（独立重算 375,107.97）
场外基金盘中估值接口全线不可用（§3.80）→ 按对应场内 ETF / 板块指数代理；主动基按 §3.81/§3.85 弹性系数
⚠️ §3.84 教训：代理基准必须逐 code 显式指定（FUND_BASE），禁止统一 fallback
"""
import json, os, re
from collections import defaultdict

BASE = "/Users/jieyang/Documents/WealthHub"
HIST = os.path.join(BASE, "data/processed/history")
ARCHIVED = 375505.37          # 9/15 盘后归档链式值（当日涨跌基准）
PREV_ARCHIVED = 375841.62     # 9/14 盘后归档链式值（参考）

pre = json.load(open(os.path.join(HIST, "portfolio_preopen_20260916.json")))
detail = pre["detail"]

# ---- 13:48 实时代理涨跌幅 ----
ETF = {"512170": 0.90, "159938": 0.32, "159928": -0.61, "513050": -0.88, "513180": 0.55,
       "515180": -0.42, "512880": 0.96, "512980": 0.25, "159920": -0.07, "512800": -0.47}
IDX = {"中证医药": 0.13, "中证医疗": 0.60, "中证消费": -0.71, "中证白酒": -0.38,
       "沪深300": 0.69, "中证环保": 0.23, "恒生科技": 0.83, "中证金融": -0.22}
STOCK = {"002410": 0.36, "600438": 0.90}
BOARD_MED = round((IDX["中证医药"] + IDX["中证医疗"] + ETF["512170"] + ETF["159938"]) / 4, 4)  # A股医药板块基准

# 场外代理规则: code -> (基准涨跌幅, 弹性, 说明)
FUND_BASE = {
    # --- A股医药 ---
    "002708": (BOARD_MED, 1.90, "主动创新药/CXO，上涨日弹性 1.9（§3.85）"),
    "161616": (BOARD_MED, 1.55, "主动医药 弹性 1.55（§3.81）"),
    "000727": (BOARD_MED, 0.65, "主动医药 弹性 0.65（§3.81）"),
    "012323": (ETF["512170"], 0.90, "医疗ETF联接 → 医疗ETF +0.90%"),
    "001180": (BOARD_MED, 0.87, "ETF联接 0.87（§3.81）"),
    "001551": (BOARD_MED, 1.00, "医药100指数 1.00"),
    # --- 大消费 ---
    "000248": (IDX["中证消费"], 1.00, "主要消费联接 → 中证消费"),
    "519915": (IDX["中证消费"], 1.00, "消费主动基 → 中证消费"),
    "000968": (-0.25, 1.00, "养老产业 → 中证消费/大盘加权"),
    "004424": (ETF["512980"], 1.00, "文体娱乐 → 传媒ETF"),
    # --- 其他/宽基 ---
    "000051": (IDX["沪深300"], 1.00, "沪深300联接 → 沪深300"),
    "110020": (IDX["沪深300"], 1.00, "沪深300联接 → 沪深300"),
    "001552": (ETF["512880"], 1.00, "证券保险 → 证券ETF"),
    "001469": (IDX["中证金融"], 1.00, "金融地产 → 中证金融 -0.22%"),
    "000071": (ETF["159920"], 1.00, "恒生ETF联接 → 恒生ETF华夏"),
    "005368": (IDX["中证环保"], 1.00, "清洁能源 → 中证环保"),
    "100032": (ETF["515180"], 1.00, "红利指增 → 100红利"),
    "004752": (ETF["512980"], 1.00, "传媒联接 → 传媒ETF"),
    "002742": (0.0, 1.00, "债券，按 0"),
    # --- 恒生科技 ---
    "012348": (IDX["恒生科技"], 0.90, "恒科联接 → 恒生科技指数 ×0.90"),
    "164906": (ETF["513050"], 1.00, "中概互联LOF → 中概互联ETF -0.88%（港美中概加权）"),
    # --- 美股标普医药（QDII T+1，盘中按 0）---
    "000369": (0.0, 0.0, "QDII T+1，盘中按 0（XLV 9/15 -0.05% 待 9/16 盘后计入）"),
    "016280": (0.0, 0.0, "QDII T+1，盘中按 0"),
}


def proxy_pct(r):
    code = re.sub(r"\D", "", str(r["code"]) or "")
    name = str(r["name"])
    if "现金" in name or "余额宝" in name or "帮你投" in name:
        return 0.0, "现金/投顾按 0"
    if code in ETF:
        return ETF[code], "场内ETF实时"
    if code in STOCK:
        return STOCK[code], "个股实时"
    if code in FUND_BASE:
        base, e, note = FUND_BASE[code]
        return base * e, note
    return 0.0, "无代理，按 0"


rows = []
for r in detail:
    p, note = proxy_pct(r)
    mv = float(r["mv"])
    delta = mv * p / 100
    rows.append({**r, "proxy_pct": round(p, 3), "delta": round(delta, 2), "note": note})

total_base = sum(x["mv"] for x in rows)
total_delta = sum(x["delta"] for x in rows)
pct = total_delta / total_base * 100

print(f"A股医药板块基准 BOARD_MED = {BOARD_MED:+.4f}%")
print("\n=== 分赛道盘中估算（13:48） ===")
agg = defaultdict(lambda: [0.0, 0.0])
for x in rows:
    agg[x["track"]][0] += x["mv"]; agg[x["track"]][1] += x["delta"]
for t, (mv, dl) in sorted(agg.items(), key=lambda kv: -kv[1][0]):
    print(f"  {t:10s} 市值 {mv:>11,.2f}  贡献 {dl:>+9,.2f}  代理 {dl/mv*100 if mv else 0:>+6.3f}%")

print(f"\n权重基数(独立重算) {total_base:,.2f}")
print(f"盘中估算变动 {total_delta:+,.2f} 元 ({pct:+.3f}%)")
print(f"→ 以 9/15 盘后归档 {ARCHIVED:,.2f} 为基准，盘中估算总资产 {ARCHIVED*(1+pct/100):,.2f}")
print(f"→ 以独立重算 {total_base:,.2f} 为基准，盘中估算总资产 {total_base+total_delta:,.2f}")

print("\n=== 盘中估算后赛道占比 ===")
new_total = total_base + total_delta
for t, (mv, dl) in sorted(agg.items(), key=lambda kv: -(kv[1][0]+kv[1][1])):
    v = mv + dl
    print(f"  {t:10s} {v:>11,.2f} ({v/new_total*100:>5.2f}%)")
med = agg["A股医药"][0] + agg["A股医药"][1] + agg["美股标普医药"][0] + agg["美股标普医药"][1]
print(f"\n医药总敞口 {med:,.2f} ({med/new_total*100:.2f}%)")

print("\n=== 逐项明细（按市值降序） ===")
for x in sorted(rows, key=lambda r: -r["mv"]):
    print(f"  {str(x['name'])[:24]:26s} {str(x['code']):9s} {x['track']:10s} {x['mv']:>10,.2f} {x['proxy_pct']:>+7.3f}% {x['delta']:>+9,.2f}  [{x['note'][:44]}]")

out = {"date": "2026-09-16", "as_of": "盘中13:48",
       "archived_base": ARCHIVED, "weight_base": round(total_base, 2),
       "total_delta": round(total_delta, 2), "est_total_pct": round(pct, 4),
       "est_total_archived_base": round(ARCHIVED * (1 + pct / 100), 2),
       "est_total_weight_base": round(total_base + total_delta, 2),
       "board_med": BOARD_MED,
       "tracks": {t: {"mv": round(v[0], 2), "delta": round(v[1], 2),
                      "pct": round((v[0] + v[1]) / new_total * 100, 2)} for t, v in agg.items()},
       "med_exposure": round(med, 2), "med_pct": round(med / new_total * 100, 2),
       "detail": rows}
json.dump(out, open(os.path.join(HIST, "portfolio_intraday_20260916.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("\n已保存 portfolio_intraday_20260916.json")
