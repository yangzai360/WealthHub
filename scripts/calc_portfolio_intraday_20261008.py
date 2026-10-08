# -*- coding: utf-8 -*-
"""2026-10-08 盘中档：组合盘中估算（13:45 口径）—— **正常交易日**（A股 长假后复市首日 + 港股正常交易日）

基准：9/30 收盘修正件 `portfolio_close_20260930_fix.json` = 380,888.29 元（tracks[].mv 求和）
⚠️ §3.112a/§3.115a：逐券还原式**禁止按字段名取数**，必须用机器判据选式（三候选 + 逐赛道最大偏差 < 1.5）
⚠️ §3.84：代理基准必须逐 code 显式指定（FUND_BASE），禁止统一 fallback
⚠️ §3.87：赛道代理涨跌 = delta/mv0×100，须独立 helper tp()
⚠️ §3.116b：情境区间 low/high 必须按「结果值 min/max」取，禁止把弹性常量硬绑定到上下界
⚠️ §3.112i：场外港股联接（000071/012348）的**今日净值将一次性体现「9/30 → 10/8」跨长假累积**
   （港股 10/2、10/5、10/6、10/7、10/8 共 5 个交易日）→ 本档对 000071/012348 采用**累积口径代理**，
   而非单日口径；场内 ETF（513180/159920/513050）因 A股 长假未交易、其「昨收」即 9/30 收盘，
   **其涨跌幅本身已是累积口径**（本档已核验：513180 −3.00% vs HSTECH 累积 −3.53%）→ 两口径本档天然一致。
⚠️ 2026-10-08 = 正常交易日 → 本档产 `portfolio_intraday_20261008.json`；**不产 close / pending**（§3.109 条款 28）
"""
import json, os, re
from collections import defaultdict

BASE = "/Users/jieyang/Documents/WealthHub"
HIST = os.path.join(BASE, "data/processed/history")
ARCHIVED = 380888.29
QDII_PRED = 0.0     # QDII（000369/016280）10/8 净值未发布 → 主口径按 0；挂账区间见盘前档

b = json.load(open(os.path.join(HIST, "portfolio_close_20260930_fix.json")))
detail = b["detail"]
tracks_ref = b["tracks"]
hq = json.load(open(os.path.join(HIST, "intraday_hq_20261008.json")))


# ---------- 0. 还原式自动判别（§3.112a / §3.115a） ----------
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
print(f"→ 采用还原式 = detail.{FIELD} + est_pnl（dev = {cand[best][0]:.4f} 元）\n")

# ---------- 1. 行情字典 ----------
ETF = {v["code"]: v["pct"] for v in hq["etfs"].values()}
IDX = {**{k: v["pct"] for k, v in hq["indices_a"].items()},
       **{k: v["pct"] for k, v in hq["boards"].items()},
       **{k: v["pct"] for k, v in hq["indices_hk"].items()}}
STOCK = {"002410": hq["stocks"]["广联达"]["pct"], "600438": hq["stocks"]["通威股份"]["pct"]}

BOARD_MED = round((IDX["中证医药"] + IDX["中证医疗"] + ETF["512170"] + ETF["159938"]) / 4, 4)
LEADER_MED = IDX["300医药"]
LAG_MED = IDX["中证医疗"]
PENSION = round((IDX["中证消费"] + BOARD_MED) / 2, 4)
HK_TECH_IDX = IDX["恒生科技"]          # 单日口径（4,103.760 vs 10/7 收 4,194.49）
HSTECH_CUM = -3.5292                   # 累积口径（9/30 收 4,253.89 → 10/8 13:45 报 4,103.760）

print(f"A股医药板块基准 BOARD_MED = {BOARD_MED:+.4f}%  |  300医药(龙头) {LEADER_MED:+.2f}%  "
      f"|  中证医疗 {LAG_MED:+.2f}%  |  养老折中代理 {PENSION:+.4f}%")
print(f"恒生科技：单日口径 {HK_TECH_IDX:+.2f}%  |  跨长假累积口径 {HSTECH_CUM:+.4f}%（场外联接采用后者，§3.112i）")
print(f"结构判别（§3.99）：300医药 {LEADER_MED:+.2f}% > 中证医药 {IDX['中证医药']:+.2f}% > 中证医疗 {LAG_MED:+.2f}%"
      f"  → {'大市值相对抗跌' if LEADER_MED > LAG_MED else '大市值相对更弱'}\n")

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
    "000071": (ETF["159920"], 1.00, "恒生ETF联接 → 恒生ETF华夏（⚠️§3.112i：场内 ETF 昨收 = 9/30，已含长假累积）"),
    "005368": (IDX["中证环保"], 1.00, "清洁能源 → 中证环保"),
    "100032": (ETF["515180"], 1.00, "红利指增 → 100红利"),
    "004752": (ETF["512980"], 1.00, "传媒联接 → 传媒ETF"),
    "002742": (0.0, 1.00, "债券，按 0"),
    # --- 恒生科技 ---
    "012348": (HSTECH_CUM, 1.00, "恒科联接 → 恒生科技**累积口径**（§3.112i：今日净值含 9/30→10/8 五个港股交易日）"),
    "164906": (ETF["513050"], 1.00, "中概互联LOF → 中概互联ETF（场内，昨收 = 9/30，含累积）"),
    # --- 美股标普医药（QDII T+1~T+2 未出库）---
    "000369": (0.0, 0.0, "QDII 净值未出库，按 0（挂账区间见盘前档）"),
    "016280": (0.0, 0.0, "QDII 净值未出库，按 0（挂账区间见盘前档）"),
}


def proxy_pct(r):
    code = re.sub(r"\D", "", str(r.get("code") or ""))
    name = str(r["name"])
    if "现金" in name or "余额宝" in name or "帮你投" in name or "现金" in str(r.get("track", "")):
        return 0.0, "现金/投顾按 0"
    if code in ETF:
        return ETF[code], "场内ETF实时（昨收 = 9/30，含长假累积）"
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
    agg[x["track"]][0] += x["mv"]
    agg[x["track"]][1] += x["delta"]


def tp(v):
    return v[1] / v[0] * 100 if v[0] else 0.0


for t, v in sorted(agg.items(), key=lambda kv: -kv[1][0]):
    print(f"  {t:10s} 市值 {v[0]:>11,.2f}  贡献 {v[1]:>+9,.2f}  代理涨跌 {tp(v):>+6.3f}%")

print(f"\n权重基数(独立重算) {total_base:,.2f}")
print(f"盘中估算变动 {total_delta:+,.2f} 元 ({pct:+.3f}%)")
print(f"→ 以 9/30 修正收盘链式 {ARCHIVED:,.2f} 元为基准，盘中估算总资产 {ARCHIVED*(1+pct/100):,.2f} 元")

new_total = total_base + total_delta
print("\n=== 盘中估算后赛道占比 ===")
tracks = {}
for t, v in sorted(agg.items(), key=lambda kv: -(kv[1][0] + kv[1][1])):
    val = v[0] + v[1]
    tracks[t] = {"mv0": round(v[0], 2), "mv": round(val, 2), "pct": round(val / new_total * 100, 2),
                 "delta": round(v[1], 2), "proxy_pct": round(tp(v), 4)}
    print(f"  {t:10s} {val:>11,.2f} 元 ({val/new_total*100:>5.2f}%)  贡献 {v[1]:>+9,.2f}  代理涨跌 {tp(v):>+6.3f}%")
med = agg["A股医药"][0] + agg["A股医药"][1] + agg["美股标普医药"][0] + agg["美股标普医药"][1]
print(f"\n医药总敞口 {med:,.2f} 元 ({med/new_total*100:.2f}%)  距 40% 上限 {40-med/new_total*100:+.2f}pct")

print("\n=== 逐项明细（按市值降序） ===")
for x in sorted(rows, key=lambda r: -r["mv"]):
    print(f"  {str(x['name'])[:24]:26s} {str(x['code']):9s} {x['track']:10s} {x['mv']:>10,.2f} "
          f"{x['proxy_pct']:>+7.3f}% {x['delta']:>+9,.2f}  [{x['note'][:44]}]")

# ---------- 港股暴露三层拆解（§3.108 / AGENTS 23） ----------
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
print(f"  （赛道层「恒生科技」{tracks['恒生科技']['mv']:,.2f} 元 = {tracks['恒生科技']['pct']:.2f}%）")

# ---------- 医药敞口门槛收益率（§3.98 方程解法） ----------
B_nonmed = new_total - med
need = (0.40 / 0.60) * B_nonmed
r_all = (need / med - 1) * 100
a_only = med - agg["美股标普医药"][0] - agg["美股标普医药"][1]
r_only = ((need - (agg["美股标普医药"][0] + agg["美股标普医药"][1])) / a_only - 1) * 100
print(f"\n【医药敞口门槛（§3.98 方程解法）】A(医药)={med:,.2f}  B(非医药含现金)={B_nonmed:,.2f}")
print(f"  → 医药两赛道同涨 r ≈ {r_all:+.2f}% 才被动触及 40%")
print(f"  → 仅 A股医药涨 r ≈ {r_only:+.2f}%（其余持平）")
print(f"  当前距上限 {40 - med/new_total*100:.2f}pct")

# ---------- 弹性敏感性（结构切换日：给区间，§3.116b） ----------
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
print("\n=== 弹性敏感性（结构切换日 → 区间优先，§3.116b） ===")
print(f"  弹性常量档：MAXM 实测档 → {scen['elas_max']:+,.2f} 元 ｜ 0.85×中位档 → {scen['elas_min']:+,.2f} 元")
print("  方向约定（§3.116b）：low = 结果下界（最差）、high = 结果上界（最优）—— 按**结果值**排序取 min/max")
for k in ("low", "base", "high"):
    d, p = sensi[k]
    print(f"  {k:5s} {d:+,.2f} 元 ({p:+.4f}%)  估算总资产 {total_base+d:,.2f} 元")
assert sensi["low"][0] <= sensi["base"][0] <= sensi["high"][0], "区间端点违背 low ≤ base ≤ high（§3.116b）"

# 尾盘情景 A（A股医药跌幅收窄 + 港股续弱）
d3 = 0.0
for x in rows:
    c = re.sub(r"\D", "", str(x.get("code") or ""))
    if c in ACTIVE:
        d3 += x["mv"] * round(-1.20 * ELAS[c], 4) / 100
    elif c in ("012323", "001551", "001180"):
        d3 += x["mv"] * round(-1.80, 4) / 100
    elif c == "512170":
        d3 += x["mv"] * round(-1.80, 4) / 100
    elif c == "159938":
        d3 += x["mv"] * round(-1.80, 4) / 100
    elif c == "012348":
        d3 += x["mv"] * round(-4.20, 4) / 100
    elif c in ("513050", "164906"):
        d3 += x["mv"] * round(-3.00, 4) / 100
    elif c == "513180":
        d3 += x["mv"] * round(-3.60, 4) / 100
    else:
        d3 += x["delta"]
sensi["tail_weak"] = (round(d3, 2), round(d3 / total_base * 100, 4))
print(f"  [尾盘弱情景] A股医药 −1.20% / 恒生科技累积 −4.20%：{d3:+,.2f} 元 "
      f"({d3/total_base*100:+.4f}%)  估算总资产 {total_base+d3:,.2f} 元")

# 尾盘情景 B（尾盘修复）
d4 = 0.0
for x in rows:
    c = re.sub(r"\D", "", str(x.get("code") or ""))
    if c in ACTIVE:
        d4 += x["mv"] * round(-0.50 * ELAS[c], 4) / 100
    elif c in ("012323", "001551", "001180", "512170", "159938"):
        d4 += x["mv"] * round(-0.70, 4) / 100
    elif c == "012348":
        d4 += x["mv"] * round(-1.50, 4) / 100
    elif c in ("513050", "164906"):
        d4 += x["mv"] * round(-1.00, 4) / 100
    elif c == "513180":
        d4 += x["mv"] * round(-1.20, 4) / 100
    else:
        d4 += x["delta"]
sensi["tail_strong"] = (round(d4, 2), round(d4 / total_base * 100, 4))
print(f"  [尾盘强情景] A股医药 −0.50% / 恒生科技累积 −1.50%：{d4:+,.2f} 元 "
      f"({d4/total_base*100:+.4f}%)  估算总资产 {total_base+d4:,.2f} 元")

# ---------- 三条防线 ----------
print("\n=== 三条防线（10/8 13:45） ===")
_cs = hq["indices_a"]["中证消费"]
_hs = hq["indices_hk"]["恒生科技"]
cons = _cs["cur"]
hst = _hs["cur"]
print(f"  中证消费 {cons:,.4f} 距 12,100 下沿 {(cons/12100-1)*100:+.3f}%  "
      f"(日内低 {_cs['low']:,.2f} / 高 {_cs['high']:,.2f})  [代理涨跌 {_cs['pct']:+.2f}%]")
print(f"  恒生科技 {hst:,.2f} 距 4,250 防线 {(hst/4250-1)*100:+.3f}%  "
      f"(日内低 {_hs['low']:,.2f} / 高 {_hs['high']:,.2f})  [代理涨跌 {_hs['pct']:+.2f}%]")
print(f"  A股医药板块代理 {BOARD_MED:+.4f}%（反向兑现线阈值 -1.5%）→ "
      f"{'⚠️ 触发区' if BOARD_MED <= -1.5 else '未触发'}")

# ---------- 恒生科技 0.5% 纪律减仓台账（累计口径，§3.123e） ----------
CUT1, CUT2 = 1882.46, 1904.44
cum_cut = CUT1 + CUT2
hk_now = tracks["恒生科技"]["mv"]
cash_now = tracks["现金"]["mv"]
print(f"\n=== 恒生科技 0.5% 纪律减仓（累计口径，§3.123e） ===")
print(f"  第 1 次（9/30 已成交）{CUT1:,.2f} 元 + 第 2 次（10/2 判定 / 今日 10/8 执行）{CUT2:,.2f} 元 = 累计 {cum_cut:,.2f} 元")
print(f"  自证：{CUT1:,.2f} + {CUT2:,.2f} = {cum_cut:,.2f} ✅")
print(f"  纪律前：恒生科技 {hk_now:,.2f} 元 ({hk_now/new_total*100:.2f}%)  现金 {cash_now:,.2f} 元 ({cash_now/new_total*100:.2f}%)")
print(f"  纪律后：恒生科技 {hk_now-cum_cut:,.2f} 元 ({(hk_now-cum_cut)/new_total*100:.2f}%)  "
      f"现金 {cash_now+cum_cut:,.2f} 元 ({(cash_now+cum_cut)/new_total*100:.2f}%)")

# ---------- 场外港股联接累积口径披露（§3.112i） ----------
print("\n=== 场外港股联接累积口径披露（§3.112i） ===")
print(f"  012348 天弘恒生科技联接：累积 {HSTECH_CUM:+.4f}%（9/30 收 4,253.89 → 10/8 报 4,103.760）；"
      f"若误用单日口径 {HK_TECH_IDX:+.2f}% → 低估 {HK_TECH_IDX - HSTECH_CUM:+.4f}pct")
print(f"  000071 华夏恒生ETF联接：代理 159920 场内 {ETF['159920']:+.2f}%（A股 昨收 = 9/30 → 已含累积）")
diff_012348 = sum(x["mv"] for x in rows if re.sub(r"\D", "", str(x.get("code") or "")) == "012348")
print(f"  012348 合计市值 {diff_012348:,.2f} 元 → 两口径差异约 {diff_012348*(HK_TECH_IDX-HSTECH_CUM)/100:+,.2f} 元")

out = {"date": "2026-10-08", "as_of": "盘中13:45", "session_type": "normal_trading_day_intraday",
       "session_type_note": "正常交易日盘中（A股 长假后复市首日 + 港股正常交易日，港股通恢复首日）",
       "archived_base": ARCHIVED, "weight_base": round(total_base, 2),
       "restore_rule_used": RESTORE, "restore_dev": {k: round(v[0], 4) for k, v in cand.items()},
       "total_delta": round(total_delta, 2), "est_total_pct": round(pct, 4),
       "est_total_archived_base": round(ARCHIVED * (1 + pct / 100), 2),
       "est_total_weight_base": round(total_base + total_delta, 2),
       "qdii_pred_pct": QDII_PRED,
       "board_med": BOARD_MED, "leader_med": LEADER_MED, "lag_med": LAG_MED,
       "hk_tech_intraday": HK_TECH_IDX, "hstech_cum": HSTECH_CUM,
       "structure": {"order": "300医药 > 中证医药 > 中证医疗",
                     "regime": "大市值相对抗跌 + 中小市值/主题跌幅更深"},
       "defense": {"cs_index": cons, "cs_vs_12100": round((cons / 12100 - 1) * 100, 3),
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
       "discipline_cut": {"cut1": CUT1, "cut2": CUT2, "cumulative_amount": round(cum_cut, 2),
                          "selfcheck_ok": abs(CUT1 + CUT2 - cum_cut) < 0.005,
                          "before_hk": round(hk_now, 2), "before_cash": round(cash_now, 2),
                          "after_hk": round(hk_now - cum_cut, 2), "after_cash": round(cash_now + cum_cut, 2),
                          "after_hk_pct": round((hk_now - cum_cut) / new_total * 100, 2),
                          "after_cash_pct": round((cash_now + cum_cut) / new_total * 100, 2),
                          "target": "纯恒科口径（012348 优先 / 513180 备选）",
                          "settle": "第 2 次于 10/8 净值成交（A股 复市首日）"},
       "detail_restore_note": "逐券还原式由机器判据选定（三候选 + 逐赛道最大偏差 <1.5 元），禁止按字段名取数（§3.112a）",
       "hk_linked_fund_cumulative_note": (
           f"场外港股联接（012348/000071）今日净值一次性体现 9/30→10/8 跨长假累积（5 个港股交易日）；"
           f"本档 012348 采用累积口径 {HSTECH_CUM:+.4f}%（非单日 {HK_TECH_IDX:+.2f}%），"
           f"差异约 {diff_012348*(HK_TECH_IDX-HSTECH_CUM)/100:+.2f} 元（§3.112i）"),
       "detail": rows}
json.dump(out, open(os.path.join(HIST, "portfolio_intraday_20261008.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("\n已保存 portfolio_intraday_20261008.json")
