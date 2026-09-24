# -*- coding: utf-8 -*-
"""2026-09-24 盘中档：组合盘中估算（13:45 口径）
基准：9/23 收盘真实净值兜底修正总资产 383,039.00 元（9/24 盘前档口径）；权重取 portfolio_close_20260923_fix.json detail（合计 383,038.99）
场外基金盘中估值接口全线不可用（§3.80）→ 按对应场内 ETF / 板块指数代理；主动基按 §3.97 全样本中位弹性档
⚠️ §3.84：代理基准必须逐 code 显式指定（FUND_BASE），禁止统一 fallback
⚠️ §3.87：赛道代理涨跌 = delta/mv0×100，须独立 helper tp()，禁止误用 tracks[k]['pct']（占比）
⚠️ §3.102：主动基弹性系数仅「结构稳定日」可用。本档医药内部三层顺序为
   中证医疗 -1.62% > 300医药 -2.07% > 中证医药 -2.14%（300医药 与 中证医药 相对顺序较 9/22-9/23 互换）
   → 判定「结构切换日」→ 基准估算不可作点估计，必须给区间（下界 = 板块基准 × §3.100 下跌日实测最大倍数）
⚠️ §3.103：000968 广发养老产业不得按中证消费代理（跟踪养老产业指数），本档沿用 (中证消费+医药板块)/2 折中代理并披露
⚠️ ⚠️ 关键口径修正（本档新增）：`portfolio_close_20260923_fix.json` 的 `detail[].mv` 是 **9/22 收盘（mv0）口径**，
   **不是 9/23 收盘口径** —— 已用 `mv + est_pnl`（est_pnl = 该品种 9/23 当日盈亏）还原为 9/23 收盘市值。
   （验证：还原后 detail 合计 = 383,039.00，与 fix 文件 `total_mv` 完全一致；若直接用 mv 会得到 383,598.82，
     即把 9/23 的涨跌重复计入 9/24，属同类「分母口径错配」坑，已回写知识库。）
"""
import json, os, re
from collections import defaultdict

BASE = "/Users/jieyang/Documents/WealthHub"
HIST = os.path.join(BASE, "data/processed/history")
ARCHIVED = 383039.00          # 9/23 收盘真实净值兜底修正链式值（9/24 盘前档口径，当日涨跌基准）
QDII_PRED = -0.48             # XLV 9/23 -0.64% × 传导系数 0.75 → 本档 QDII 预测（不纳入主口径，仅披露）

pre = json.load(open(os.path.join(HIST, "portfolio_preopen_20260924.json")))
b = json.load(open(os.path.join(HIST, "portfolio_close_20260923_fix.json")))
detail = b["detail"]
hq = json.load(open(os.path.join(HIST, "intraday_hq_20260924.json")))

ETF = {v["code"]: v["pct"] for v in hq["etfs"].values()}
IDX = {**{k: v["pct"] for k, v in hq["indices_a"].items()},
       **{k: v["pct"] for k, v in hq["boards"].items()},
       **{k: v["pct"] for k, v in hq["indices_hk"].items()}}
STOCK = {"002410": hq["stocks"]["广联达"]["pct"], "600438": hq["stocks"]["通威股份"]["pct"]}

BOARD_MED = round((IDX["中证医药"] + IDX["中证医疗"] + ETF["512170"] + ETF["159938"]) / 4, 4)
LEADER_MED = IDX["300医药"]
PENSION = round((IDX["中证消费"] + BOARD_MED) / 2, 4)
HK_TECH = IDX["恒生科技"]

print(f"A股医药板块基准 BOARD_MED = {BOARD_MED:+.4f}%  |  300医药(龙头) {LEADER_MED:+.2f}%  "
      f"|  养老折中代理 {PENSION:+.4f}%  |  恒生科技 {HK_TECH:+.2f}%")
print(f"结构判别：中证医疗 {IDX['中证医疗']:+.2f}% > 300医药 {LEADER_MED:+.2f}% > 中证医药 {IDX['中证医药']:+.2f}%"
      f"  → 300医药 与 中证医药 相对顺序较 9/22-9/23 互换 = 「结构切换日」（§3.102）：弹性系数不可作点估计")

FUND_BASE = {
    # --- A股医药 ---
    "002708": (BOARD_MED, 1.39, "主动创新药/CXO；§3.97 全样本中位弹性 1.39"),
    "161616": (BOARD_MED, 1.09, "主动医药；§3.97 全样本中位弹性 1.09"),
    "000727": (BOARD_MED, 0.82, "融通健康产业灵活配置；§3.97 全样本中位弹性 0.82"),
    "012323": (IDX["中证医疗"], 1.00, "中证医疗联接 → 中证医疗"),
    "001180": (LEADER_MED, 1.00, "医药卫生ETF联接 → 300医药（大市值口径）"),
    "001551": (BOARD_MED, 1.00, "医药100指数 → A股医药板块基准"),
    # --- 大消费 ---
    "000248": (IDX["中证消费"], 1.00, "主要消费联接 → 中证消费"),
    "519915": (IDX["中证消费"], 1.00, "消费主动基 → 中证消费"),
    "000968": (PENSION, 1.00, "养老产业 → (中证消费+医药板块)/2 折中代理（§3.103 限定：跟踪养老产业指数）"),
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
    "164906": (ETF["513050"], 1.00, "中概互联LOF（QDII 净值 9/22）→ 中概互联ETF 代理"),
    # --- 美股标普医药（QDII T+1~T+2）---
    "000369": (0.0, 0.0, "QDII 净值未出库（最新仍 9/22），主口径按 0，另披露预测 -0.48%"),
    "016280": (0.0, 0.0, "QDII 净值未出库（最新仍 9/22），主口径按 0，另披露预测 -0.48%"),
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
    mv0 = float(r["mv"])                      # 9/22 收盘口径（mv0）
    mv = round(mv0 + float(r.get("est_pnl") or 0.0), 2)   # 还原为 9/23 收盘市值
    delta = mv * p / 100
    rows.append({**r, "mv0_0922": round(mv0, 2), "mv": mv,
                 "proxy_pct": round(p, 3), "delta": round(delta, 2), "note": note})

total_base = sum(x["mv"] for x in rows)
total_delta = sum(x["delta"] for x in rows)
pct = total_delta / total_base * 100
assert abs(total_base - ARCHIVED) < 1.5, f"权重基数与基准不一致: {total_base:.2f} vs {ARCHIVED:.2f}"

print("\n=== 分赛道盘中估算（13:45） ===")
agg = defaultdict(lambda: [0.0, 0.0])
for x in rows:
    agg[x["track"]][0] += x["mv"]; agg[x["track"]][1] += x["delta"]


def tp(v):
    return v[1] / v[0] * 100 if v[0] else 0.0


for t, v in sorted(agg.items(), key=lambda kv: -kv[1][0]):
    print(f"  {t:10s} 市值 {v[0]:>11,.2f}  贡献 {v[1]:>+9,.2f}  代理涨跌 {tp(v):>+6.3f}%")

print(f"\n权重基数(独立重算) {total_base:,.2f}")
print(f"盘中估算变动 {total_delta:+,.2f} 元 ({pct:+.3f}%)")
print(f"→ 以 9/23 收盘修正链式 {ARCHIVED:,.2f} 元为基准，盘中估算总资产 {ARCHIVED*(1+pct/100):,.2f} 元")

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

# ---------- QDII 预测口径披露 ----------
qdii_mv = agg["美股标普医药"][0]
qdii_delta = qdii_mv * QDII_PRED / 100
print(f"\n【QDII 披露口径】美股标普医药市值 {qdii_mv:,.2f}；XLV 9/23 {QDII_PRED}% → 预测贡献 {qdii_delta:+,.2f} 元")
print(f"  含 QDII 预测的组合变动 {total_delta+qdii_delta:+,.2f} 元 ({(total_delta+qdii_delta)/total_base*100:+.4f}%)")

# ---------- 医药敞口「被动突破 40%」门槛收益率（§3.98 方程解法） ----------
B_nonmed = new_total - med
need = (0.40 / 0.60) * B_nonmed
r_all = (need / med - 1) * 100
a_only = med - agg["美股标普医药"][0] - agg["美股标普医药"][1]
r_only = ((need - (agg["美股标普医药"][0] + agg["美股标普医药"][1])) / a_only - 1) * 100
print(f"\n【医药敞口门槛（§3.98 方程解法）】A(医药)={med:,.2f}  B(非医药含现金)={B_nonmed:,.2f}")
print(f"  令 A(1+r)/[B+A(1+r)]=40% → (1+r)={need/med:.4f}")
print(f"  → 医药两赛道单日同涨 r ≈ {r_all:+.2f}% 才被动触及 40%")
print(f"  → 仅 A股医药单日涨 r ≈ {r_only:+.2f}%（其余持平）")
print(f"  当前距上限 {40 - med/new_total*100:.2f}pct；单边行情下敞口抬升速率 ≈ 敞口×(1−敞口)")

# ---------- 弹性敏感性（§3.98 + §3.100 + §3.102 要求给区间） ----------
ACTIVE = ("002708", "161616", "000727")
ELAS = {"002708": 1.39, "161616": 1.09, "000727": 0.82}
MAXM = {"002708": 1.70, "161616": 3.66, "000727": 1.70}   # §3.100 实测倍数（9/22 下跌日）
sensi = {}
for label in ("low", "high"):
    d2 = 0.0
    for x in rows:
        c = re.sub(r"\D", "", str(x.get("code") or ""))
        if c in ACTIVE:
            if label == "low":
                b2, e = BOARD_MED, MAXM[c]                 # 板块口径 × 下跌日实测最大倍数（跌幅放大）
            else:
                b2, e = BOARD_MED, 0.85 * ELAS[c]          # 板块口径 × 中位弹性 × 0.85（跌幅收敛）
            d2 += x["mv"] * round(b2 * e, 4) / 100
        else:
            d2 += x["delta"]
    sensi[label] = (round(d2, 2), round(d2 / total_base * 100, 4))
sensi["base"] = (round(total_delta, 2), round(pct, 4))
print("\n=== 弹性敏感性 ===")
for k in ("low", "base", "high"):
    d, p = sensi[k]
    print(f"  {k:5s} {d:+,.2f} 元 ({p:+.4f}%)  估算总资产 {total_base+d:,.2f} 元")

# 尾盘情景：医药跌幅进一步扩大（300医药 -3.00%）
d3 = 0.0
for x in rows:
    c = re.sub(r"\D", "", str(x.get("code") or ""))
    if c in ACTIVE:
        d3 += x["mv"] * round(-2.70 * ELAS[c], 4) / 100
    elif c == "012323":
        d3 += x["mv"] * round(-2.10, 4) / 100
    elif c == "001180":
        d3 += x["mv"] * round(-3.00, 4) / 100
    elif c == "001551":
        d3 += x["mv"] * round(-3.10, 4) / 100
    elif c == "512170":
        d3 += x["mv"] * round(-1.80, 4) / 100
    elif c == "159938":
        d3 += x["mv"] * round(-2.60, 4) / 100
    else:
        d3 += x["delta"]
sensi["tail_weak"] = (round(d3, 2), round(d3 / total_base * 100, 4))
print(f"  [尾盘情景] 医药跌幅进一步扩大（300医药 -3.00% / 中证医药 -3.20%）：{d3:+,.2f} 元 "
      f"({d3/total_base*100:+.4f}%)  估算总资产 {total_base+d3:,.2f} 元")

print("\n=== 逐项明细（按市值降序） ===")
for x in sorted(rows, key=lambda r: -r["mv"]):
    print(f"  {str(x['name'])[:22]:24s} {str(x['code']):9s} {x['track']:10s} {x['mv']:>10,.2f} "
          f"{x['proxy_pct']:>+7.3f}% {x['delta']:>+9,.2f}  [{x['note'][:52]}]")

out = {"date": "2026-09-24", "as_of": "盘中13:45",
       "archived_base": ARCHIVED, "weight_base": round(total_base, 2),
       "total_delta": round(total_delta, 2), "est_total_pct": round(pct, 4),
       "est_total_archived_base": round(ARCHIVED * (1 + pct / 100), 2),
       "est_total_weight_base": round(total_base + total_delta, 2),
       "qdii_pred_pct": QDII_PRED, "qdii_pred_delta": round(qdii_delta, 2),
       "est_total_with_qdii_pct": round((total_delta + qdii_delta) / total_base * 100, 4),
       "board_med": BOARD_MED, "leader_med": LEADER_MED, "hk_tech": HK_TECH,
       "structure_switch_day": True,
       "sensitivity": {k: {"delta": v[0], "pct": v[1]} for k, v in sensi.items()},
       "tracks": tracks,
       "med_exposure": round(med, 2), "med_pct": round(med / new_total * 100, 2),
       "detail": rows}
json.dump(out, open(os.path.join(HIST, "portfolio_intraday_20260924.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("\n已保存 portfolio_intraday_20260924.json")
