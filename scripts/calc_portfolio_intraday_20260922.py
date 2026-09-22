# -*- coding: utf-8 -*-
"""2026-09-22 盘中档：组合盘中估算（13:45 口径）
基准：9/21 收盘修正链式总资产 383,064.00（盘前档 §3.98 口径）；权重取 portfolio_preopen_20260922.json 明细（合计 383,064.00）
场外基金盘中估值接口全线不可用（§3.80）→ 按对应场内 ETF / 板块指数代理；主动基按 §3.81/§3.85/§3.87/§3.88/§3.97 弹性档
⚠️ §3.84：代理基准必须逐 code 显式指定（FUND_BASE），禁止统一 fallback
⚠️ §3.87：赛道代理涨跌 = delta/mv0×100，须独立 helper tp()，禁止误用 tracks[k]['pct']（占比）
⚠️ §3.96/§3.98 本档判据：今日为「小票脉冲 + 龙头转跌」日（300医药 -0.32% < 中证医药 -0.11% < 生物制品 +1.40%）
   → 主动基弹性「下修」至全样本中位档（§3.97 口径：002708=1.39 / 161616=1.09 / 000727=0.82）
"""
import json, os, re
from collections import defaultdict

BASE = "/Users/jieyang/Documents/WealthHub"
HIST = os.path.join(BASE, "data/processed/history")
ARCHIVED = 383064.00          # 9/21 收盘修正链式值（盘前档口径，当日涨跌基准）

pre = json.load(open(os.path.join(HIST, "portfolio_preopen_20260922.json")))
detail = pre["detail"]
pre_tracks_med = pre["tracks"]["A股医药"]["mv"] + pre["tracks"]["美股标普医药"]["mv"]
hq = json.load(open(os.path.join(HIST, "intraday_hq_20260922.json")))

ETF = {v["code"]: v["pct"] for v in hq["etfs"].values()}
IDX = {**{k: v["pct"] for k, v in hq["indices_a"].items()},
       **{k: v["pct"] for k, v in hq["boards"].items()},
       **{k: v["pct"] for k, v in hq["indices_hk"].items()}}
STOCK = {"002410": hq["stocks"]["广联达"]["pct"], "600438": hq["stocks"]["通威股份"]["pct"]}

BOARD_MED = round((IDX["中证医药"] + IDX["中证医疗"] + ETF["512170"] + ETF["159938"]) / 4, 4)  # A股医药板块基准
LEADER_MED = IDX["300医药"]            # 龙头/大市值口径（本档结构判别用）
PENSION = round((IDX["中证消费"] + BOARD_MED) / 2, 4)   # 养老产业：医药 + 消费混合属性
HK_TECH = IDX["恒生科技"]

print(f"A股医药板块基准 BOARD_MED = {BOARD_MED:+.4f}%  |  300医药(龙头) {LEADER_MED:+.2f}%  "
      f"|  养老代理 {PENSION:+.4f}%  |  恒生科技 {HK_TECH:+.2f}%")
print(f"结构判别：300医药 {LEADER_MED:+.2f}% < 中证医药 {IDX['中证医药']:+.2f}% < 生物制品 +1.40% "
      f"→ 小票脉冲 + 龙头转跌（§3.96 延续性未通过）")

# 场外代理规则: code -> (基准涨跌幅, 弹性, 说明)
FUND_BASE = {
    # --- A股医药 ---
    "002708": (BOARD_MED, 1.39, "主动创新药/CXO；小票脉冲日弹性下修至全样本中位 1.39（§3.97）"),
    "161616": (BOARD_MED, 1.09, "主动医药；全样本中位弹性 1.09（§3.97）"),
    "000727": (BOARD_MED, 0.82, "融通健康产业灵活配置；全样本中位弹性 0.82（§3.97）"),
    "012323": (IDX["中证医疗"], 1.00, "中证医疗联接 → 中证医疗"),
    "001180": (LEADER_MED, 1.00, "医药卫生ETF联接 → 300医药（大市值口径）"),
    "001551": (BOARD_MED, 1.00, "医药100指数 → A股医药板块基准"),
    # --- 大消费 ---
    "000248": (IDX["中证消费"], 1.00, "主要消费联接 → 中证消费"),
    "519915": (IDX["中证消费"], 1.00, "消费主动基 → 中证消费"),
    "000968": (PENSION, 1.00, "养老产业 → (中证消费+医药)/2"),
    "004424": (ETF["512980"], 1.00, "文体娱乐 → 传媒ETF"),
    # --- 其他/宽基 ---
    "000051": (IDX["沪深300"], 1.00, "沪深300联接 → 沪深300"),
    "110020": (IDX["沪深300"], 1.00, "沪深300联接 → 沪深300"),
    "001552": (ETF["512880"], 1.00, "证券保险 → 证券ETF"),
    "001469": (IDX["中证金融"], 1.00, "金融地产 → 中证金融"),
    "000071": (ETF["159920"], 1.00, "恒生ETF联接 → 恒生ETF华夏"),
    "005368": (IDX["中证环保"], 1.00, "清洁能源 → 中证环保"),
    "100032": (ETF["515180"], 1.00, "红利指增 → 100红利"),
    "004752": (ETF["512980"], 1.00, "传媒联接 → 传媒ETF"),
    "002742": (0.0, 1.00, "债券，按 0"),
    # --- 恒生科技 ---
    "012348": (HK_TECH, 0.90, "恒科联接 → 恒生科技指数 ×0.90"),
    "164906": (ETF["513050"], 1.00, "中概互联LOF → 中概互联ETF"),
    # --- 美股标普医药（QDII T+1~T+2，盘中按 0）---
    "000369": (0.0, 0.0, "QDII 净值未出库（最新仍 9/18），盘中按 0"),
    "016280": (0.0, 0.0, "QDII 净值未出库（最新仍 9/18），盘中按 0"),
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

print("\n=== 分赛道盘中估算（13:45） ===")
agg = defaultdict(lambda: [0.0, 0.0])
for x in rows:
    agg[x["track"]][0] += x["mv"]; agg[x["track"]][1] += x["delta"]


def tp(v):  # §3.87 赛道代理涨跌独立 helper（分母必须为 mv0）
    return v[1] / v[0] * 100 if v[0] else 0.0


for t, v in sorted(agg.items(), key=lambda kv: -kv[1][0]):
    print(f"  {t:10s} 市值 {v[0]:>11,.2f}  贡献 {v[1]:>+9,.2f}  代理涨跌 {tp(v):>+6.3f}%")

print(f"\n权重基数(独立重算) {total_base:,.2f}")
print(f"盘中估算变动 {total_delta:+,.2f} 元 ({pct:+.3f}%)")
print(f"→ 以 9/21 收盘修正链式 {ARCHIVED:,.2f} 元为基准，盘中估算总资产 {ARCHIVED*(1+pct/100):,.2f} 元")
print(f"→ 以独立重算 {total_base:,.2f} 元为基准，盘中估算总资产 {total_base+total_delta:,.2f} 元")

new_total = total_base + total_delta
print("\n=== 盘中估算后赛道占比 ===")
tracks = {}
for t, v in sorted(agg.items(), key=lambda kv: -(kv[1][0] + kv[1][1])):
    val = v[0] + v[1]
    tracks[t] = {"mv0": round(v[0], 2), "mv": round(val, 2), "pct": round(val / new_total * 100, 2),
                 "delta": round(v[1], 2)}
    print(f"  {t:10s} {val:>11,.2f} 元 ({val/new_total*100:>5.2f}%)  贡献 {v[1]:>+9,.2f}  代理涨跌 {tp(v):>+6.3f}%")
med = agg["A股医药"][0] + agg["A股医药"][1] + agg["美股标普医药"][0] + agg["美股标普医药"][1]
print(f"\n医药总敞口 {med:,.2f} 元 ({med/new_total*100:.2f}%)")

# ---------- 医药敞口「被动突破 40%」门槛收益率（§3.98 非线性方程解法）----------
# 口径切换说明：盘前档以 9/21 收盘基数（383,064）计算得 +5.16%；
#   本档改以「盘中估算后」市值（383,940.97）为基数复算，更贴近当前状态。
B_nonmed = new_total - med            # 非医药类（含现金）
need = (0.40 / 0.60) * B_nonmed
r_all = (need / med - 1) * 100
a_only = med - agg["美股标普医药"][0] - agg["美股标普医药"][1]
r_only = ((need - (agg["美股标普医药"][0] + agg["美股标普医药"][1])) / a_only - 1) * 100
print(f"\n【医药敞口门槛（§3.98 方程解法，基数改用盘中估算后）】A(医药)={med:,.2f}  B(非医药含现金)={B_nonmed:,.2f}")
print(f"  令 A(1+r)/[B+A(1+r)]=40% → (1+r)={need/med:.4f}")
print(f"  → 医药两赛道单日同涨 r ≈ {r_all:+.2f}% 才被动触及 40%")
print(f"  → 仅 A股医药单日涨 r ≈ {r_only:+.2f}%（其余持平）")
print(f"  当前距上限 {40 - med/new_total*100:.2f}pct；单边行情下敞口抬升速率 ≈ 敞口×(1−敞口)")

# ---------- 弹性敏感性（§3.98 要求给区间）----------
# 下界 low  ：主动基以 300医药（龙头口径）为基准 → 龙头继续走弱情景
# 基准 base ：主动基以 A股医药板块基准 BOARD_MED 为基准（全样本中位弹性，本档主口径）
# 上界 high ：主动基持平 0%（生物制品结构性上涨完全对冲龙头下跌的最乐观情景）
ACTIVE = ("002708", "161616", "000727")
ELAS = {"002708": 1.39, "161616": 1.09, "000727": 0.82}
sensi = {}
for label in ("low", "high"):
    d2 = 0.0
    for x in rows:
        c = re.sub(r"\D", "", str(x.get("code") or ""))
        if c in ACTIVE:
            b = LEADER_MED if label == "low" else 0.0
            d2 += x["mv"] * round(b * ELAS[c], 4) / 100
        else:
            d2 += x["delta"]
    sensi[label] = (round(d2, 2), round(d2 / total_base * 100, 4))
sensi["base"] = (round(total_delta, 2), round(pct, 4))
print("\n=== 弹性敏感性 ===")
for k in ("low", "base", "high"):
    d, p = sensi[k]
    print(f"  {k:5s} {d:+,.2f} 元 ({p:+.4f}%)  估算总资产 {total_base+d:,.2f} 元")

# 尾盘情景：医药龙头加速回落（300医药 尾盘 -1.00%）
d3 = 0.0
for x in rows:
    c = re.sub(r"\D", "", str(x.get("code") or ""))
    if c in ACTIVE:
        d3 += x["mv"] * round(-1.00 * ELAS[c], 4) / 100
    elif c in ("012323",):
        d3 += x["mv"] * round(-0.90, 4) / 100
    elif c in ("001180",):
        d3 += x["mv"] * round(-1.00, 4) / 100
    elif c in ("001551",):
        d3 += x["mv"] * round(-0.85, 4) / 100
    elif c in ("512170",):
        d3 += x["mv"] * round(-0.60, 4) / 100
    elif c in ("159938",):
        d3 += x["mv"] * round(-0.90, 4) / 100
    else:
        d3 += x["delta"]
sensi["tail_weak"] = (round(d3, 2), round(d3 / total_base * 100, 4))
print(f"  [尾盘情景] 医药龙头加速回落（300医药 -1.00%）：{d3:+,.2f} 元 ({d3/total_base*100:+.4f}%)  "
      f"估算总资产 {total_base+d3:,.2f} 元")

print("\n=== 逐项明细（按市值降序） ===")
for x in sorted(rows, key=lambda r: -r["mv"]):
    print(f"  {str(x['name'])[:22]:24s} {str(x['code']):9s} {x['track']:10s} {x['mv']:>10,.2f} "
          f"{x['proxy_pct']:>+7.3f}% {x['delta']:>+9,.2f}  [{x['note'][:46]}]")

out = {"date": "2026-09-22", "as_of": "盘中13:45",
       "archived_base": ARCHIVED, "weight_base": round(total_base, 2),
       "total_delta": round(total_delta, 2), "est_total_pct": round(pct, 4),
       "est_total_archived_base": round(ARCHIVED * (1 + pct / 100), 2),
       "est_total_weight_base": round(total_base + total_delta, 2),
       "board_med": BOARD_MED, "leader_med": LEADER_MED, "hk_tech": HK_TECH,
       "sensitivity": {k: {"delta": v[0], "pct": v[1]} for k, v in sensi.items()},
       "tracks": tracks,
       "med_exposure": round(med, 2), "med_pct": round(med / new_total * 100, 2),
       "detail": rows}
json.dump(out, open(os.path.join(HIST, "portfolio_intraday_20260922.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("\n已保存 portfolio_intraday_20260922.json")
