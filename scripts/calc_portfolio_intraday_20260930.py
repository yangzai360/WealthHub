# -*- coding: utf-8 -*-
"""2026-09-30 盘中档：组合盘中估算（13:45 口径）
基准：9/29 收盘净值修正件 `portfolio_close_20260929_fix.json` = 376,491.53 元（tracks[].mv 求和）
⚠️ §3.112a：9/29_fix 的正确逐券还原式 = `detail.mv0_new + detail.est_pnl`（机器判据 dev=0.00）
   → 本档同时用「三候选还原式 + 逐赛道最大偏差」自动判别，不按字段名硬取。
⚠️ §3.84：代理基准必须逐 code 显式指定（FUND_BASE），禁止统一 fallback
⚠️ §3.87：赛道代理涨跌 = delta/mv0×100，须独立 helper tp()
⚠️ §3.102：结构切换日 → 弹性不可作点估计，必须给区间
⚠️ §3.103：000968 广发养老产业不得按中证消费代理，沿用 (中证消费+医药板块)/2 折中代理并披露
⚠️ §3.112i：场外港股联接（000071/012348）与场内 ETF（159920）口径不可混用；本档沿用「场内 / 指数」代理
⚠️ §3.113i：本档恒生科技减仓为盘前档已决定之纪律执行，按 9/30 净值成交 → 价值中性、仅改变权重
⚠️ §3.115a：基准取 base['base_total'] 语义（前一收盘）已由 _fix 件完成，本档仅读 tracks[].mv
"""
import json, os, re
from collections import defaultdict

BASE = "/Users/jieyang/Documents/WealthHub"
HIST = os.path.join(BASE, "data/processed/history")
ARCHIVED = 376491.53          # 9/29 修正收盘链式值（当日涨跌基准）
QDII_PRED = 0.0               # 本档 QDII 净值未出库（最新仍 9/28），主口径按 0；挂账值见盘前档

b = json.load(open(os.path.join(HIST, "portfolio_close_20260929_fix.json")))
detail = b["detail"]
tracks_ref = b["tracks"]
hq = json.load(open(os.path.join(HIST, "intraday_hq_20260930.json")))

# ---------- 0. 还原式自动判别 ----------
def restore(kind):
    agg = defaultdict(float)
    for r in detail:
        if kind == "mv0_pnl":
            v = float(r["mv0"]) + float(r.get("est_pnl") or 0.0)
        elif kind == "mv0new_pnl":
            v = float(r["mv0_new"]) + float(r.get("est_pnl") or 0.0)
        else:
            v = float(r["mv"]) + float(r.get("est_pnl") or 0.0)
        agg[r["track"]] += v
    return agg


cand = {}
for kind in ("mv0_pnl", "mv0new_pnl", "mv_pnl"):
    agg = restore(kind)
    dev = max(abs(agg[t] - tracks_ref[t]["mv"]) for t in tracks_ref)
    cand[kind] = (dev, agg)
best = min(cand, key=lambda k: cand[k][0])
print("=== 还原式判别（逐赛道 Σ 与 tracks[].mv 最大偏差） ===")
for kind, (dev, _) in cand.items():
    print(f"  {kind:12s} 最大偏差 {dev:>10,.2f} 元  {'← 采用（Δ<1.5 通过）' if kind == best and dev < 1.5 else ''}")
assert cand[best][0] < 1.5, f"三种还原式均无法复现 tracks[].mv：{cand}"
RESTORE = best
FIELD = {"mv0_pnl": "mv0", "mv0new_pnl": "mv0_new", "mv_pnl": "mv"}[best]
print(f"→ 采用还原式 = detail.{FIELD} + est_pnl\n")

ETF = {v["code"]: v["pct"] for v in hq["etfs"].values()}
IDX = {**{k: v["pct"] for k, v in hq["indices_a"].items()},
       **{k: v["pct"] for k, v in hq["boards"].items()},
       **{k: v["pct"] for k, v in hq["indices_hk"].items()}}
STOCK = {"002410": hq["stocks"]["广联达"]["pct"], "600438": hq["stocks"]["通威股份"]["pct"]}

BOARD_MED = round((IDX["中证医药"] + IDX["中证医疗"] + ETF["512170"] + ETF["159938"]) / 4, 4)
LEADER_MED = IDX["300医药"]
LAG_MED = IDX["中证医疗"]
PENSION = round((IDX["中证消费"] + BOARD_MED) / 2, 4)
HK_TECH = IDX["恒生科技"]

print(f"A股医药板块基准 BOARD_MED = {BOARD_MED:+.4f}%  |  300医药(龙头) {LEADER_MED:+.2f}%  "
      f"|  中证医疗 {LAG_MED:+.2f}%  |  养老折中代理 {PENSION:+.4f}%  |  恒生科技 {HK_TECH:+.2f}%")
print(f"结构判别（§3.99）：300医药 {LEADER_MED:+.2f}% > 中证医疗 {LAG_MED:+.2f}% > 中证医药 {IDX['中证医药']:+.2f}%\n")

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
    "000968": (PENSION, 1.00, "养老产业 → (中证消费+医药板块)/2 折中代理（§3.103 限定）"),
    "004424": (ETF["512980"], 1.00, "文体娱乐 → 传媒ETF"),
    # --- 其他/宽基 ---
    "000051": (IDX["沪深300"], 1.00, "沪深300联接 → 沪深300"),
    "110020": (IDX["沪深300"], 1.00, "沪深300联接 → 沪深300"),
    "001552": (ETF["512880"], 1.00, "证券保险 → 证券ETF"),
    "001469": (IDX["中证金融"], 1.00, "金融地产 → 中证金融"),
    "000071": (ETF["159920"], 1.00, "恒生ETF联接 → 恒生ETF华夏（⚠️§3.112i 场内口径代理）"),
    "005368": (IDX["中证环保"], 1.00, "清洁能源 → 中证环保"),
    "100032": (ETF["515180"], 1.00, "红利指增 → 100红利"),
    "004752": (ETF["512980"], 1.00, "传媒联接 → 传媒ETF"),
    "002742": (0.0, 1.00, "债券，按 0"),
    # --- 恒生科技 ---
    "012348": (HK_TECH, 0.90, "恒科联接 → 恒生科技指数 ×0.90（⚠️§3.112i 口径）"),
    "164906": (ETF["513050"], 1.00, "中概互联LOF（QDII 净值 9/28）→ 中概互联ETF 代理"),
    # --- 美股标普医药（QDII T+1~T+2 未出库）---
    "000369": (0.0, 0.0, "QDII 净值未出库（最新仍 9/28），按 0"),
    "016280": (0.0, 0.0, "QDII 净值未出库（最新仍 9/28），按 0"),
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
    base = float(r[FIELD])
    mv = round(base + float(r.get("est_pnl") or 0.0), 2)
    delta = mv * p / 100
    rows.append({**r, "mv_pre": round(base, 2), "mv": mv,
                 "proxy_pct": round(p, 3), "delta": round(delta, 2), "note": note})

total_base = sum(x["mv"] for x in rows)
total_delta = sum(x["delta"] for x in rows)
pct = total_delta / total_base * 100
assert abs(total_base - ARCHIVED) < 1.5, f"权重基数与基准不一致: {total_base:.2f} vs {ARCHIVED:.2f}"

print("=== 分赛道盘中估算（13:45） ===")
agg = defaultdict(lambda: [0.0, 0.0])
for x in rows:
    agg[x["track"]][0] += x["mv"]; agg[x["track"]][1] += x["delta"]


def tp(v):
    return v[1] / v[0] * 100 if v[0] else 0.0


for t, v in sorted(agg.items(), key=lambda kv: -kv[1][0]):
    print(f"  {t:10s} 市值 {v[0]:>11,.2f}  贡献 {v[1]:>+9,.2f}  代理涨跌 {tp(v):>+6.3f}%")

print(f"\n权重基数(独立重算) {total_base:,.2f}")
print(f"盘中估算变动 {total_delta:+,.2f} 元 ({pct:+.3f}%)")
print(f"→ 以 9/29 修正收盘链式 {ARCHIVED:,.2f} 元为基准，盘中估算总资产 {ARCHIVED*(1+pct/100):,.2f} 元")

new_total = total_base + total_delta
print("\n=== 盘中估算后赛道占比 ===")
tracks = {}
for t, v in sorted(agg.items(), key=lambda kv: -(kv[1][0] + kv[1][1])):
    val = v[0] + v[1]
    tracks[t] = {"mv0": round(v[0], 2), "mv": round(val, 2), "pct": round(val / new_total * 100, 2),
                 "delta": round(v[1], 2), "proxy_pct": round(tp(v), 4)}
    print(f"  {t:10s} {val:>11,.2f} 元 ({val/new_total*100:>5.2f}%)  贡献 {v[1]:>+9,.2f}  代理涨跌 {tp(v):>+6.3f}%")
med = agg["A股医药"][0] + agg["A股医药"][1] + agg["美股标普医药"][0] + agg["美股标普医药"][1]
print(f"\n医药总敞口 {med:,.2f} 元 ({med/new_total*100:.2f}%)")

print("\n=== 逐项明细（按市值降序） ===")
for x in sorted(rows, key=lambda r: -r["mv"]):
    print(f"  {str(x['name'])[:24]:26s} {str(x['code']):9s} {x['track']:10s} {x['mv']:>10,.2f} "
          f"{x['proxy_pct']:>+7.3f}% {x['delta']:>+9,.2f}  [{x['note'][:46]}]")

# ---------- 港股暴露三层拆解（§3.108 条款 4 / AGENTS 23） ----------
hk_track = ["012348", "513050", "164906", "513180"]
pure_hk, cn_internet, hk_broad = 0.0, 0.0, 0.0
for x in rows:
    c = re.sub(r"\D", "", str(x.get("code") or ""))
    v = x["mv"] + x["delta"]
    if c in ("012348", "513180"):
        pure_hk += v
    elif c in ("513050", "164906"):
        cn_internet += v
    elif c in ("000071", "159920"):
        hk_broad += v
hk_total = pure_hk + cn_internet + hk_broad
print(f"\n=== 港股暴露三层拆解 ===")
print(f"  纯恒科（012348+513180）{pure_hk:>11,.2f} 元 ({pure_hk/new_total*100:.2f}%)")
print(f"  中概互联（513050+164906）{cn_internet:>9,.2f} 元 ({cn_internet/new_total*100:.2f}%)")
print(f"  宽基恒生系（000071×2+159920）{hk_broad:>7,.2f} 元 ({hk_broad/new_total*100:.2f}%)")
print(f"  → 港联系总暴露 {hk_total:,.2f} 元 = {hk_total/new_total*100:.2f}%")
print(f"  （赛道层「恒生科技」{tracks['恒生科技']['mv']:,.2f} 元 = {tracks['恒生科技']['pct']:.2f}%，"
      f"宽基层恒生系 {hk_broad:,.2f} 元 = {hk_broad/new_total*100:.2f}%）")

# ---------- 医药敞口门槛收益率（§3.98 方程解法） ----------
B_nonmed = new_total - med
need = (0.40 / 0.60) * B_nonmed
r_all = (need / med - 1) * 100
a_only = med - agg["美股标普医药"][0] - agg["美股标普医药"][1]
r_only = ((need - (agg["美股标普医药"][0] + agg["美股标普医药"][1])) / a_only - 1) * 100
print(f"\n【医药敞口门槛（§3.98 方程解法）】A(医药)={med:,.2f}  B(非医药含现金)={B_nonmed:,.2f}")
print(f"  → 医药两赛道单日同涨 r ≈ {r_all:+.2f}% 才被动触及 40%")
print(f"  → 仅 A股医药单日涨 r ≈ {r_only:+.2f}%（其余持平）")
print(f"  当前距上限 {40 - med/new_total*100:.2f}pct")

# ---------- 弹性敏感性（结构切换日：必须给区间） ----------
# ⚠️ §3.111e 修正：上下界必须按「结果值 min/max」定义，不得把弹性常量固定绑到 low/high——
#    在上涨日（base>0）最大弹性给出最优结果、在下跌日给出最差结果，固定绑定会方向反转。
ACTIVE = ("002708", "161616", "000727")
ELAS = {"002708": 1.39, "161616": 1.09, "000727": 0.82}
MAXM = {"002708": 1.70, "161616": 3.66, "000727": 1.70}
sensi = {}
scen = {}
for label, mult in (("elas_max", None), ("elas_min", 0.85)):
    d2 = 0.0
    for x in rows:
        c = re.sub(r"\D", "", str(x.get("code") or ""))
        if c in ACTIVE:
            e = MAXM[c] if mult is None else mult * ELAS[c]
            d2 += x["mv"] * round(BOARD_MED * e, 4) / 100
        else:
            d2 += x["delta"]
    scen[label] = round(d2, 2)
_lo, _hi = sorted([scen["elas_max"], scen["elas_min"]])
sensi["low"] = (round(_lo, 2), round(_lo / total_base * 100, 4))
sensi["high"] = (round(_hi, 2), round(_hi / total_base * 100, 4))
sensi["base"] = (round(total_delta, 2), round(pct, 4))
print("\n=== 弹性敏感性（结构切换日 → 区间优先） ===")
print(f"  弹性常量档：MAXM 实测档 → {scen['elas_max']:+,.2f} 元 ｜ 0.85×中位档 → {scen['elas_min']:+,.2f} 元")
print("  方向约定（§3.111e 修正版）：low = 结果下界（最差）、high = 结果上界（最优）—— 按结果值排序取 min/max")
for k in ("low", "base", "high"):
    d, p = sensi[k]
    print(f"  {k:5s} {d:+,.2f} 元 ({p:+.4f}%)  估算总资产 {total_base+d:,.2f} 元")

# 尾盘情景 A（A股医药冲高回落 + 港股继续下探）
d3 = 0.0
for x in rows:
    c = re.sub(r"\D", "", str(x.get("code") or ""))
    if c in ACTIVE:
        d3 += x["mv"] * round(0.50 * ELAS[c], 4) / 100
    elif c in ("012323", "001551"):
        d3 += x["mv"] * round(0.50, 4) / 100
    elif c == "001180":
        d3 += x["mv"] * round(0.50, 4) / 100
    elif c == "512170":
        d3 += x["mv"] * round(0.40, 4) / 100
    elif c == "159938":
        d3 += x["mv"] * round(0.50, 4) / 100
    elif c == "012348":
        d3 += x["mv"] * round(-0.82 * 0.90, 4) / 100
    elif c in ("513050", "164906"):
        d3 += x["mv"] * round(-0.90, 4) / 100
    elif c == "513180":
        d3 += x["mv"] * round(-0.85, 4) / 100
    else:
        d3 += x["delta"]
sensi["tail_weak"] = (round(d3, 2), round(d3 / total_base * 100, 4))
print(f"  [尾盘弱情景] A股医药回落至 +0.50% / 恒生科技 -0.82%：{d3:+,.2f} 元 "
      f"({d3/total_base*100:+.4f}%)  估算总资产 {total_base+d3:,.2f} 元")

# 尾盘情景 B（A股医药维持强势 + 港股回升）
d4 = 0.0
for x in rows:
    c = re.sub(r"\D", "", str(x.get("code") or ""))
    if c in ACTIVE:
        d4 += x["mv"] * round(BOARD_MED * 1.15 * ELAS[c], 4) / 100
    elif c in ("012323", "001180", "001551"):
        d4 += x["mv"] * round(BOARD_MED * 1.15, 4) / 100
    elif c == "512170":
        d4 += x["mv"] * round(BOARD_MED * 1.15, 4) / 100
    elif c == "159938":
        d4 += x["mv"] * round(BOARD_MED * 1.15, 4) / 100
    elif c == "012348":
        d4 += x["mv"] * round(0.20 * 0.90, 4) / 100
    elif c in ("513050", "164906"):
        d4 += x["mv"] * round(0.20, 4) / 100
    elif c == "513180":
        d4 += x["mv"] * round(0.25, 4) / 100
    else:
        d4 += x["delta"]
sensi["tail_strong"] = (round(d4, 2), round(d4 / total_base * 100, 4))
print(f"  [尾盘强情景] A股医药扩至 +3.53% / 恒生科技 +0.20%：{d4:+,.2f} 元 "
      f"({d4/total_base*100:+.4f}%)  估算总资产 {total_base+d4:,.2f} 元")

# ---------- 三条防线 ----------
print("\n=== 三条防线（9/30 13:45） ===")
_cs = hq["indices_a"]["中证消费"]
_hs = hq["indices_hk"]["恒生科技"]
cons = _cs["cur"]
hst = _hs["cur"]
print(f"  中证消费 {cons:,.4f} 距 12,100 下沿 {(cons/12100-1)*100:+.3f}%  距 12,000 下一线 {(cons/12000-1)*100:+.3f}%  "
      f"(日内低 {_cs['low']:,.2f} / 高 {_cs['high']:,.2f})  [代理涨跌 {_cs['pct']:+.2f}%]")
print(f"  恒生科技 {hst:,.2f} 距 4,250 防线 {(hst/4250-1)*100:+.3f}%  "
      f"(日内低 {_hs['low']:,.2f} / 高 {_hs['high']:,.2f})  [代理涨跌 {_hs['pct']:+.2f}%]")
print(f"  A股医药板块代理 {BOARD_MED:+.4f}%（反向兑现线阈值 -1.5%）→ "
      f"{'⚠️ 触发区' if BOARD_MED <= -1.5 else '未触发'}")

# ---------- 恒生科技 0.5% 纪律减仓台账 ----------
REDEEM_HK = 1882.46
hk_now = tracks["恒生科技"]["mv"]
cash_now = tracks["现金"]["mv"]
print(f"\n=== 本档恒生科技 0.5% 纪律减仓（盘前档决定、9/30 净值成交） ===")
print(f"  减仓前：恒生科技 {hk_now:,.2f} 元 ({hk_now/new_total*100:.2f}%)  现金 {cash_now:,.2f} 元 ({cash_now/new_total*100:.2f}%)")
print(f"  减仓后：恒生科技 {hk_now-REDEEM_HK:,.2f} 元 ({(hk_now-REDEEM_HK)/new_total*100:.2f}%)  "
      f"现金 {cash_now+REDEEM_HK:,.2f} 元 ({(cash_now+REDEEM_HK)/new_total*100:.2f}%)")
print(f"  （按 9/30 净值成交 → 价值中性、不影响当日估算总额；仅改变赛道权重）")

out = {"date": "2026-09-30", "as_of": "盘中13:45",
       "archived_base": ARCHIVED, "weight_base": round(total_base, 2),
       "restore_rule_used": RESTORE,
       "restore_dev": {k: round(v[0], 2) for k, v in cand.items()},
       "total_delta": round(total_delta, 2), "est_total_pct": round(pct, 4),
       "est_total_archived_base": round(ARCHIVED * (1 + pct / 100), 2),
       "est_total_weight_base": round(total_base + total_delta, 2),
       "qdii_pred_pct": QDII_PRED,
       "board_med": BOARD_MED, "leader_med": LEADER_MED, "lag_med": LAG_MED, "hk_tech": HK_TECH,
       "structure": {"order": "300医药 > 中证医疗 > 中证医药", "regime": "大市值龙头微弱占优 + 主题领涨并存"},
       "defense": {"cs_index": cons, "cs_vs_12100": round((cons / 12100 - 1) * 100, 3),
                   "cs_vs_12000": round((cons / 12000 - 1) * 100, 3),
                   "hstech": hst, "hstech_vs_4250": round((hst / 4250 - 1) * 100, 3),
                   "hstech_break": hst < 4250,
                   "med_reverse_line": BOARD_MED <= -1.5},
       "sensitivity": {k: {"delta": v[0], "pct": v[1]} for k, v in sensi.items()},
       "tracks": tracks,
       "med_exposure": round(med, 2), "med_pct": round(med / new_total * 100, 2),
       "threshold_all_med": round(r_all, 2), "threshold_a_sh_med": round(r_only, 2),
       "hk_split": {"pure_hk": round(pure_hk, 2), "cn_internet": round(cn_internet, 2),
                    "hk_broad": round(hk_broad, 2), "total": round(hk_total, 2),
                    "total_pct": round(hk_total / new_total * 100, 2),
                    "track_layer_pct": tracks["恒生科技"]["pct"]},
       "redeem_hstech": REDEEM_HK,
       "redeem_hstech_ledger": {"before_hk": round(hk_now, 2), "before_cash": round(cash_now, 2),
                                "after_hk": round(hk_now - REDEEM_HK, 2), "after_cash": round(cash_now + REDEEM_HK, 2),
                                "before_hk_pct": round(hk_now / new_total * 100, 2),
                                "after_hk_pct": round((hk_now - REDEEM_HK) / new_total * 100, 2),
                                "before_cash_pct": round(cash_now / new_total * 100, 2),
                                "after_cash_pct": round((cash_now + REDEEM_HK) / new_total * 100, 2),
                                "target": "纯恒科口径（012348 优先 / 513180 备选）",
                                "settle": "9/30 净值成交（本周最后一个 A股交易日）"},
       "detail": rows}
json.dump(out, open(os.path.join(HIST, "portfolio_intraday_20260930.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("\n已保存 portfolio_intraday_20260930.json")
