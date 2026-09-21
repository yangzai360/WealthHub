# -*- coding: utf-8 -*-
"""2026-09-21 盘中档：组合盘中估算（13:47 口径）
基准：9/18 盘后归档链式总资产 378,405.26（修正后口径，§3.94/§3.95）；权重取 portfolio_preopen_20260921.json 明细
场外基金盘中估值接口全线不可用（§3.80）→ 按对应场内 ETF / 板块指数代理；主动基按 §3.81/§3.85/§3.87/§3.88 弹性档
⚠️ §3.84：代理基准必须逐 code 显式指定（FUND_BASE），禁止统一 fallback
⚠️ §3.87：赛道代理涨跌 = delta/mv×100，须独立 helper tp()，禁止误用 tracks[k]['pct']（占比）
⚠️ §3.92 本档新增判据：医药「龙头驱动回归」→ 主动基弹性上修（龙头+小票同步普涨）
"""
import json, os, re
from collections import defaultdict

BASE = "/Users/jieyang/Documents/WealthHub"
HIST = os.path.join(BASE, "data/processed/history")
ARCHIVED = 378405.26          # 9/18 盘后归档链式值（修正后口径，当日涨跌基准）

pre = json.load(open(os.path.join(HIST, "portfolio_preopen_20260921.json")))
detail = pre["detail"]
hq = json.load(open(os.path.join(HIST, "intraday_hq_20260921.json")))

ETF = {v["code"]: v["pct"] for v in hq["etfs"].values()}
IDX = {**{k: v["pct"] for k, v in hq["indices_a"].items()},
       **{k: v["pct"] for k, v in hq["boards"].items()},
       **{k: v["pct"] for k, v in hq["indices_hk"].items()}}
STOCK = {"002410": hq["stocks"]["广联达"]["pct"], "600438": hq["stocks"]["通威股份"]["pct"]}

BOARD_MED = round((IDX["中证医药"] + IDX["中证医疗"] + ETF["512170"] + ETF["159938"]) / 4, 4)  # A股医药板块基准
PENSION = round((IDX["中证消费"] + BOARD_MED) / 2, 4)   # 养老产业：医药 + 消费混合属性
HK_TECH = IDX["恒生科技"]

print(f"A股医药板块基准 BOARD_MED = {BOARD_MED:+.4f}%  |  养老代理 {PENSION:+.4f}%  |  恒生科技 {HK_TECH:+.2f}%")

# 场外代理规则: code -> (基准涨跌幅, 弹性, 说明)
# 日型判定（§3.88 四档 + §3.92 龙头驱动修正）: A股医药板块 +2.44%（>2% 强普涨）+ 龙头/CXO/小票同步普涨
#   → 主动基弹性取「放量普涨日」上档；因本档为「龙头驱动回归」（持仓偏龙头），较 9/18 政策脉冲日进一步上修
FUND_BASE = {
    # --- A股医药 ---
    "002708": (BOARD_MED, 1.70, "主动创新药/CXO，龙头驱动回归日弹性 1.70（§3.92 上修）"),
    "161616": (BOARD_MED, 1.60, "主动医药 弹性 1.60（§3.81 基准 1.55 上修）"),
    "000727": (BOARD_MED, 0.80, "融通健康产业灵活配置 弹性 0.80（§3.81 基准 0.65 上修）"),
    "012323": (IDX["中证医疗"], 1.00, "中证医疗联接 → 中证医疗 +2.30%"),
    "001180": (BOARD_MED, 1.00, "医药卫生ETF联接 → A股医药板块基准"),
    "001551": (BOARD_MED, 1.00, "医药100指数 1.00"),
    # --- 大消费 ---
    "000248": (IDX["中证消费"], 1.00, "主要消费联接 → 中证消费 +0.76%"),
    "519915": (IDX["中证消费"], 1.00, "消费主动基 → 中证消费"),
    "000968": (PENSION, 1.00, "养老产业 → (中证消费+医药)/2"),
    "004424": (ETF["512980"], 1.00, "文体娱乐 → 传媒ETF +0.49%"),
    # --- 其他/宽基 ---
    "000051": (IDX["沪深300"], 1.00, "沪深300联接 → 沪深300 +0.36%"),
    "110020": (IDX["沪深300"], 1.00, "沪深300联接 → 沪深300"),
    "001552": (ETF["512880"], 1.00, "证券保险 → 证券ETF +0.38%"),
    "001469": (IDX["中证金融"], 1.00, "金融地产 → 中证金融 +0.37%"),
    "000071": (ETF["159920"], 1.00, "恒生ETF联接 → 恒生ETF华夏 +0.55%"),
    "005368": (IDX["中证环保"], 1.00, "清洁能源 → 中证环保 -0.48%"),
    "100032": (ETF["515180"], 1.00, "红利指增 → 100红利 +0.78%"),
    "004752": (ETF["512980"], 1.00, "传媒联接 → 传媒ETF +0.49%"),
    "002742": (0.0, 1.00, "债券，按 0"),
    # --- 恒生科技 ---
    "012348": (HK_TECH, 0.90, "恒科联接 → 恒生科技指数 ×0.90"),
    "164906": (ETF["513050"], 1.00, "中概互联LOF → 中概互联ETF +0.99%"),
    # --- 美股标普医药（QDII T+1，盘中按 0）---
    "000369": (0.0, 0.0, "QDII T+1，盘中按 0（9/18 美股收盘净值待 9/21 盘后/9/22 计入）"),
    "016280": (0.0, 0.0, "QDII T+1，盘中按 0"),
}


def proxy_pct(r):
    code = re.sub(r"\D", "", str(r.get("code") or ""))
    name = str(r["name"])
    if "现金" in name or "余额宝" in name or "帮你投" in name or "现金" in str(r.get("track", "")):
        return 0.0, "现金/投顾按 0"
    if code in ETF:
        return ETF[code], "场内ETF实时"
    if code in STOCK:
        return STOCK[code], "个股实时"
    if code in FUND_BASE:
        base, e, note = FUND_BASE[code]
        return round(base * e, 4), note
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

print("\n=== 分赛道盘中估算（13:47） ===")
agg = defaultdict(lambda: [0.0, 0.0])
for x in rows:
    agg[x["track"]][0] += x["mv"]; agg[x["track"]][1] += x["delta"]


def tp(v):  # §3.87 赛道代理涨跌独立 helper
    return v[1] / v[0] * 100 if v[0] else 0.0


for t, v in sorted(agg.items(), key=lambda kv: -kv[1][0]):
    print(f"  {t:10s} 市值 {v[0]:>11,.2f}  贡献 {v[1]:>+9,.2f}  代理涨跌 {tp(v):>+6.3f}%")

print(f"\n权重基数(独立重算) {total_base:,.2f}")
print(f"盘中估算变动 {total_delta:+,.2f} 元 ({pct:+.3f}%)")
print(f"→ 以 9/18 盘后归档 {ARCHIVED:,.2f} 元为基准，盘中估算总资产 {ARCHIVED*(1+pct/100):,.2f} 元")
print(f"→ 以独立重算 {total_base:,.2f} 元为基准，盘中估算总资产 {total_base+total_delta:,.2f} 元")

new_total = total_base + total_delta
print("\n=== 盘中估算后赛道占比 ===")
tracks = {}
for t, v in sorted(agg.items(), key=lambda kv: -(kv[1][0] + kv[1][1])):
    val = v[0] + v[1]
    # ⚠️ mv0 = 估算前市值（盘前权重基数口径），§3.87「赛道代理涨跌 = delta/mv0×100」必须用它，
    #    不可用估算后 mv（否则同一日两个脚本会算出不同代理涨跌，本档踩坑 1 次）
    tracks[t] = {"mv0": round(v[0], 2), "mv": round(val, 2), "pct": round(val / new_total * 100, 2), "delta": round(v[1], 2)}
    print(f"  {t:10s} {val:>11,.2f} 元 ({val/new_total*100:>5.2f}%)  贡献 {v[1]:>+9,.2f}  代理涨跌 {tp(v):>+6.3f}%")
med = agg["A股医药"][0] + agg["A股医药"][1] + agg["美股标普医药"][0] + agg["美股标普医药"][1]
print(f"\n医药总敞口 {med:,.2f} 元 ({med/new_total*100:.2f}%)")

print("\n=== 逐项明细（按市值降序） ===")
for x in sorted(rows, key=lambda r: -r["mv"]):
    print(f"  {str(x['name'])[:22]:24s} {str(x['code']):9s} {x['track']:10s} {x['mv']:>10,.2f} {x['proxy_pct']:>+7.3f}% {x['delta']:>+9,.2f}  [{x['note'][:46]}]")

out = {"date": "2026-09-21", "as_of": "盘中13:47",
       "archived_base": ARCHIVED, "weight_base": round(total_base, 2),
       "total_delta": round(total_delta, 2), "est_total_pct": round(pct, 4),
       "est_total_archived_base": round(ARCHIVED * (1 + pct / 100), 2),
       "est_total_weight_base": round(total_base + total_delta, 2),
       "board_med": BOARD_MED, "hk_tech": HK_TECH,
       "tracks": tracks,
       "med_exposure": round(med, 2), "med_pct": round(med / new_total * 100, 2),
       "detail": rows}
json.dump(out, open(os.path.join(HIST, "portfolio_intraday_20260921.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("\n已保存 portfolio_intraday_20260921.json")
