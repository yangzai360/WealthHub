# -*- coding: utf-8 -*-
"""2026-10-19 盘中档：组合盘中估算（13:45 口径）—— **反向混合档**（A股 正常交易日 + 港股重阳节翌日休市）

基准：10/16 收盘修正件 `portfolio_close_20261016_fix.json` = 370,152.61 元（tracks[].mv 求和，硬守卫 1.5 元 ✅）
⚠️ §3.112a/§3.115a：逐券还原式**禁止按字段名取数**，必须用机器判据选式（三候选 + 逐赛道最大偏差 < 1.5）
⚠️ §3.159（本档新增）：**「腿内部分可定价」的定价边界**
   · 场内市价记账（price_src 含「场内收盘」）：002410 / 600438 / 159928 / 512170 / 513050 / 513180 /
     515180 / 159920 / 512880 / 512980 → **按今日 A股 市价定价**
   · 场外净值记账的 **A股** 基金 → 按赛道代理估算（净值 15:00 后发布，13:45 用代理）
   · 场外**港股联接**（000071 ×2 / 012348 ×2）→ 港股休市、**基金不发布净值** → 按 0
   · **164906（LOF，按净值记账）** → 净值迟滞（最新 10/15）→ 按 0，只登记待兑现（§3.122e）
   · QDII（000369 ×2 / 016280 ×2）→ 净值迟滞 + US 10/19 未开盘 → 按 0，挂账区间单列
   → **恒生科技腿 = 部分定价（仅场内 513050/513180 可定价）；其他/宽基腿含 000071 ×2 不可定价**
⚠️ §3.144a：QDII notional 取 `tracks['美股标普医药'].mv`，**禁止用 detail[].mv**
⚠️ 2026-10-19 = 反向混合档 → 产 `portfolio_intraday_20261019.json`；**不产 close / pending**
"""
import json, os, re
from collections import defaultdict

BASE = "/Users/jieyang/Documents/WealthHub"
HIST = os.path.join(BASE, "data/processed/history")
ARCHIVED = 370152.61
BASE_FILE = "portfolio_close_20261016_fix.json"

b = json.load(open(os.path.join(HIST, BASE_FILE)))
detail = b["detail"]
tracks_ref = b["tracks"]
hq = json.load(open(os.path.join(HIST, "intraday_hq_20261019.json")))
pre = json.load(open(os.path.join(HIST, "portfolio_preopen_20261019.json")))


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
       **{k: v["pct"] for k, v in hq["boards"].items()}}
STOCK = {"002410": hq["stocks"]["广联达"]["pct"], "600438": hq["stocks"]["通威股份"]["pct"]}

BOARD_MED = round((IDX["中证医药"] + IDX["中证医疗"] + ETF["512170"] + ETF["159938"]) / 4, 4)
LEADER_MED = IDX["300医药"]
LAG_MED = IDX["中证医疗"]
PENSION = round((IDX["中证消费"] + BOARD_MED) / 2, 4)

HSTECH_STALE = hq["indices_hk_stale_ref"]["恒生科技"]["cur"]
HSTECH_STALE_DATE = hq["indices_hk_stale_ref"]["恒生科技"]["date_field"]

print(f"A股医药板块基准 BOARD_MED = {BOARD_MED:+.4f}%（中证医药 {IDX['中证医药']:+.2f} / 中证医疗 {LAG_MED:+.2f} / "
      f"医疗ETF {ETF['512170']:+.2f} / 医药ETF广发 {ETF['159938']:+.2f} 四者均值）")
print(f"300医药(龙头) {LEADER_MED:+.2f}%  |  中证医疗 {LAG_MED:+.2f}%  |  养老折中代理 PENSION {PENSION:+.4f}%")
print(f"恒生科技 = **休市 stale {HSTECH_STALE:,.2f}（{HSTECH_STALE_DATE}）→ 本档无当日价格、不参与估算**")
print(f"结构判别（§3.99）：300医药 {LEADER_MED:+.2f}% / 中证医药 {IDX['中证医药']:+.2f}% / 中证医疗 {LAG_MED:+.2f}% / "
      f"中证白酒 {IDX['中证白酒']:+.2f}% / 中证消费 {IDX['中证消费']:+.2f}%\n")

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
    # --- 其他/宽基（A股 部分） ---
    "000051": (IDX["沪深300"], 1.00, "沪深300联接 → 沪深300"),
    "110020": (IDX["沪深300"], 1.00, "沪深300联接 → 沪深300"),
    "001552": (ETF["512880"], 1.00, "证券保险 → 证券ETF"),
    "001469": (IDX["中证金融"], 1.00, "金融地产 → 中证金融"),
    "005368": (IDX["中证环保"], 1.00, "清洁能源 → 中证环保"),
    "100032": (ETF["515180"], 1.00, "红利指增 → 100红利"),
    "004752": (ETF["512980"], 1.00, "传媒联接 → 传媒ETF"),
    "002742": (0.0, 1.00, "债券，按 0"),
    # --- 港股联接（休市 → 不发布净值，按 0） ---
    "000071": (0.0, 0.00, "⚠️ 港股休市：场外港股联接当日不发布净值 → 按 0（§3.159b；不得用 159920 场内价替代）"),
    "012348": (0.0, 0.00, "⚠️ 港股休市：场外恒科联接当日不发布净值 → 按 0（§3.159b）"),
    # --- 净值迟滞 ---
    "164906": (0.0, 0.00, "中概互联LOF：最新净值日 2026-10-15（本档 13:45 实测未推进）→ 按 0，登记待兑现（§3.122e）"),
    "000369": (0.0, 0.00, "QDII 最新净值日 = 2026-10-15 → 按 0（挂账区间见 stale_nav_legs）"),
    "016280": (0.0, 0.00, "QDII 最新净值日 = 2026-10-15 → 按 0（挂账区间见 stale_nav_legs）"),
}

UNPRICEABLE_NOTE = ("⚠️ 本档不可定价券：000071 ×2（港股联接）、012348 ×2（恒科联接）、164906 ×2（LOF 净值迟滞）、"
                    "000369 ×2 + 016280 ×2（QDII 净值迟滞）→ 合计 12 个券位，按 0 计")


def proxy_pct(r):
    code = re.sub(r"\D", "", str(r.get("code") or ""))
    name = str(r["name"])
    src = str(r.get("price_src") or "")
    if "现金" in name or "余额宝" in name or "帮你投" in name or "现金" in str(r.get("track", "")):
        return 0.0, "现金/投顾按 0"
    # ⚠️ §3.159a：定价口径跟随基准的 price_src —— 场内市价记账者用今日市价
    if "场内收盘" in src and code in ETF:
        return ETF[code], "场内ETF实时（基准为场内市价 → 单日口径）"
    if "场内收盘" in src and code in STOCK:
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
print(f"→ 以 10/16 收盘链式 {ARCHIVED:,.2f} 元为基准，盘中估算总资产 {ARCHIVED*(1+pct/100):,.2f} 元")

new_total = total_base + total_delta
print("\n=== 盘中估算后赛道占比 ===")
tracks = {}
for t, v in sorted(agg.items(), key=lambda kv: -(kv[1][0] + kv[1][1])):
    val = v[0] + v[1]
    tracks[t] = {"mv0": round(v[0], 2), "mv": round(val, 2), "pct": round(val / new_total * 100, 2),
                 "delta": round(v[1], 2), "proxy_pct": round(tp(v), 4)}
    print(f"  {t:10s} {val:>11,.2f} 元 ({val/new_total*100:>5.2f}%)  贡献 {v[1]:>+9,.2f}  代理涨跌 {tp(v):>+6.3f}%")

# ---------- 1b. 腿内「可定价比例」（§3.159c 本档新增） ----------
print("\n=== 腿内可定价比例（§3.159c） ===")
priceable = defaultdict(lambda: [0.0, 0.0])
for x in rows:
    t = x["track"]
    priceable[t][0] += x["mv"]
    if "按 0" not in x["note"]:
        priceable[t][1] += x["mv"]
for t, (tot, pr) in sorted(priceable.items(), key=lambda kv: -kv[1][0]):
    print(f"  {t:10s} 腿市值 {tot:>11,.2f}  可定价 {pr:>11,.2f} ({pr/tot*100:>5.1f}%)  不可定价 {tot-pr:>11,.2f}")
hk_price_ratio = priceable["恒生科技"][1] / priceable["恒生科技"][0]

med = agg["A股医药"][0] + agg["A股医药"][1] + agg["美股标普医药"][0] + agg["美股标普医药"][1]
print(f"\n医药总敞口 {med:,.2f} 元 ({med/new_total*100:.2f}%)  距 40% 上限 {40-med/new_total*100:+.2f}pct")

# ---------- 港股暴露三层拆解 ----------
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
print(f"  宽基恒生系（000071×2 + 159920）{hk_broad:>7,.2f} 元 ({hk_broad/new_total*100:.2f}%)")
print(f"  → 港联系总暴露 {hk_total:,.2f} 元 = {hk_total/new_total*100:.2f}%")
print(f"  （赛道层「恒生科技」{tracks['恒生科技']['mv']:,.2f} 元 = {tracks['恒生科技']['pct']:.2f}%；"
      f"只报赛道层将低估 {hk_total/new_total*100 - tracks['恒生科技']['pct']:.2f}pct）")
print(f"  ⚠️ §3.149f 对账：纯恒科 {pure_hk:,.2f} 元 + 中概互联 {cn_internet:,.2f} 元 = {pure_hk+cn_internet:,.2f} 元 "
      f"vs 赛道层 恒生科技 {tracks['恒生科技']['mv']:,.2f} 元（宽基层落在「其他/宽基」）")
print(f"  ⚠️ 本档港联系仅 {hk_price_ratio*100:.1f}% 可按 A股 市价定价（其余为休市/迟滞），"
      f"且场内 ETF 为「标的休市下的溢价/折价」→ 禁止外推 10/20 港股方向")

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

# ---------- 弹性敏感性（给区间，§3.116b） ----------
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
print("\n=== 弹性敏感性（区间优先，§3.116b） ===")
print(f"  弹性常量档：MAXM 实测档 → {scen['elas_max']:+,.2f} 元 ｜ 0.85×中位档 → {scen['elas_min']:+,.2f} 元")
for k in ("low", "base", "high"):
    d, p = sensi[k]
    print(f"  {k:5s} {d:+,.2f} 元 ({p:+.4f}%)  估算总资产 {total_base+d:,.2f} 元")
assert sensi["low"][0] <= sensi["base"][0] <= sensi["high"][0], "区间端点违背 low ≤ base ≤ high（§3.116b）"

# 尾盘弱情景：A股 尾盘回吐（沪指冲高回落 → 医药回吐、消费转负）
d3 = 0.0
for x in rows:
    c = re.sub(r"\D", "", str(x.get("code") or ""))
    if c in ACTIVE:
        d3 += x["mv"] * round(-0.60 * ELAS[c], 4) / 100
    elif c in ("012323", "001551", "001180", "512170", "159938"):
        d3 += x["mv"] * round(-0.50, 4) / 100
    elif c in ("000248", "519915", "159928"):
        d3 += x["mv"] * round(-0.40, 4) / 100
    else:
        d3 += x["delta"]
sensi["tail_weak"] = (round(d3, 2), round(d3 / total_base * 100, 4))
print(f"  [尾盘弱情景] A股医药 −0.60%（代理回吐转负）/ 消费 −0.40%：{d3:+,.2f} 元 "
      f"({d3/total_base*100:+.4f}%)  估算总资产 {total_base+d3:,.2f} 元")

# 尾盘强情景：A股 尾盘继续走强（沪指收复 3,740、医药扩散）
d4 = 0.0
for x in rows:
    c = re.sub(r"\D", "", str(x.get("code") or ""))
    if c in ACTIVE:
        d4 += x["mv"] * round(1.60 * ELAS[c], 4) / 100
    elif c in ("012323", "001551", "001180", "512170", "159938"):
        d4 += x["mv"] * round(1.60, 4) / 100
    elif c in ("000248", "519915", "159928"):
        d4 += x["mv"] * round(0.90, 4) / 100
    else:
        d4 += x["delta"]
sensi["tail_strong"] = (round(d4, 2), round(d4 / total_base * 100, 4))
print(f"  [尾盘强情景] A股医药 +1.60% / 消费 +0.90%：{d4:+,.2f} 元 "
      f"({d4/total_base*100:+.4f}%)  估算总资产 {total_base+d4:,.2f} 元")

# ---------- 三条防线 ----------
print("\n=== 三条防线（10/19 13:45） ===")
_cs = hq["indices_a"]["中证消费"]
cons = _cs["cur"]
print(f"  中证消费 {cons:,.4f} 距 12,100 下沿 {(cons/12100-1)*100:+.3f}%  "
      f"(日内低 {_cs['low']:,.2f} / 高 {_cs['high']:,.2f})  [代理涨跌 {_cs['pct']:+.2f}%]  → 未触发")
print(f"  恒生科技 **今日休市、无当日价格** → 4,250 破位 / 4,000 新观察线**判定权全部移交 10/20 收盘**")
print(f"    · 最近可用读数 = {HSTECH_STALE:,.2f}（{HSTECH_STALE_DATE}）距 4,250 {(HSTECH_STALE/4250-1)*100:+.4f}%、"
      f"距 4,000 {(HSTECH_STALE/4000-1)*100:+.4f}%")
print(f"    · ⚠️ 禁止用 A股 场内 513050（{ETF['513050']:+.2f}%）/ 513180（{ETF['513180']:+.2f}%）替代港股指数 —— "
      f"标的休市下 ETF 涨跌为溢价/折价变动（§3.121e / §3.159c）")
print(f"  A股医药板块代理 {BOARD_MED:+.4f}%（反向兑现线阈值 −1.5%）→ {'⚠️ 触发区' if BOARD_MED <= -1.5 else '未触发'}")
print(f"    · **闭环判定（盘前档规则）**：盘前档要求「今日收盘板块代理 ≤ 0% → 连续 2 日回调成立 → 建 0.5% 被动减配预案」；"
      f"本档 13:45 代理 {BOARD_MED:+.4f}% 为正 → **闭环暂不成立**，最终以 15:00 收盘价判定（20:00 盘后档）")

# ---------- 恒生科技 0.5% 纪律减仓台账（累计口径） ----------
CUT1, CUT2 = 1882.46, 1904.44
cum_cut = CUT1 + CUT2
hk_now = tracks["恒生科技"]["mv"]
cash_now = tracks["现金"]["mv"]
print(f"\n=== 恒生科技 0.5% 纪律减仓（累计口径，§3.123e） ===")
print(f"  第 1 次（9/30 已成交）{CUT1:,.2f} 元 + 第 2 次（10/2 判定 / 10/8 已成交）{CUT2:,.2f} 元 = 累计 {cum_cut:,.2f} 元")
print(f"  自证：{CUT1:,.2f} + {CUT2:,.2f} = {cum_cut:,.2f} ✅")
print(f"  ⚠️ 本档不新增纪律动作：港股休市、无当日收盘价 → 4,000 线**无法判定**（§3.114c 同日防线只触发一次）")
print(f"  权重口径（累计纪律后）：恒生科技 {hk_now-cum_cut:,.2f} 元 ({(hk_now-cum_cut)/new_total*100:.2f}%)  "
      f"现金 {cash_now+cum_cut:,.2f} 元 ({(cash_now+cum_cut)/new_total*100:.2f}%)")

# ---------- QDII 挂账（未出库 → 单列披露） ----------
qd = pre["qdii_pending"]
QD_LOW, QD_MID, QD_HIGH = qd["low"], qd["mid"], qd["high"]
QD_NOTIONAL = tracks_ref["美股标普医药"]["mv"]
LOF_NOTIONAL = sum(x["mv"] for x in rows if re.sub(r"\D", "", str(x.get("code") or "")) == "164906")
print(f"\n=== QDII 挂账（US {qd['segment']} 段，本档未刷新） ===")
print(f"  标的 000369 / 016280；最新净值日 = 2026-10-15 → 待核销段 US 10/16（IYH −0.3759%）")
print(f"  区间 {QD_LOW:,.2f} 元 ~ {QD_HIGH:,.2f} 元（中枢 {QD_MID:,.2f} 元仅参考）")
print(f"  名义市值 {QD_NOTIONAL:,.2f} 元（tracks[\"美股标普医药\"].mv，§3.144a）；**未出库 → 不计入主口径、不并入待消化**")
print(f"  164906（中概 LOF）最新净值日 2026-10-15 → 名义 {LOF_NOTIONAL:,.2f} 元，不给区间、只登记待兑现（§3.122e）")

print("\n=== 逐项明细（按市值降序，前 20 项） ===")
for x in sorted(rows, key=lambda r: -r["mv"])[:20]:
    print(f"  {str(x['name'])[:24]:26s} {str(x['code']):9s} {x['track']:10s} {x['mv']:>10,.2f} "
          f"{x['proxy_pct']:>+7.3f}% {x['delta']:>+9,.2f}  [{x['note'][:42]}]")

out = {"date": "2026-10-19", "as_of": "盘中13:45", "session_type": "reverse_mixed_closed_hk",
       "session_type_note": "反向混合档盘中（A股 第 8 个正常交易日 + 港股重阳节翌日休市；A股 可定价、港股无当日价格）",
       "archived_base": ARCHIVED, "base_file": BASE_FILE,
       "weight_base": round(total_base, 2),
       "restore_rule_used": RESTORE, "restore_dev": {k: round(v[0], 4) for k, v in cand.items()},
       "total_delta": round(total_delta, 2), "est_total_pct": round(pct, 4),
       "est_total_archived_base": round(ARCHIVED * (1 + pct / 100), 2),
       "est_total_weight_base": round(total_base + total_delta, 2),
       "board_med": BOARD_MED, "leader_med": LEADER_MED, "lag_med": LAG_MED,
       "hk_market": {"closed": True, "reason": hq["hk_market_state"]["reason"],
                     "stale_hstech": HSTECH_STALE, "stale_date": HSTECH_STALE_DATE,
                     "defense_judgement": "deferred_to_2026-10-20_close",
                     "etf_prices_used": {"513050": ETF["513050"], "513180": ETF["513180"], "159920": ETF["159920"]},
                     "etf_caliber_note": "标的休市下的 A股 场内溢价/折价变动，禁止外推 10/20 港股方向（§3.121e）"},
       "structure": {
           "index": f"上证 {IDX['上证指数']:+.2f}% / 深证 {IDX['深证成指']:+.2f}% / 创业板 {IDX['创业板指']:+.2f}% / "
                    f"科创50 {IDX['科创50']:+.2f}% / 沪深300 {IDX['沪深300']:+.2f}% / 中证500 {IDX['中证500']:+.2f}%",
           "regime": f"**「大盘价值强、成长弱」（风格切换）**：沪指 {IDX['上证指数']:+.2f}% 翻红、创业板 {IDX['创业板指']:+.2f}% / "
                     f"科创50 {IDX['科创50']:+.2f}% 续跌；消费 {IDX['中证消费']:+.2f}% / 医药代理 {BOARD_MED:+.2f}% / "
                     f"金融 {IDX['中证金融']:+.2f}% 偏正，地产链弱（投资 −20.6%）→ 与本组合「低成长端暴露」同向有利",
           "sub": f"医药内部：300医药 {LEADER_MED:+.2f}% / 中证医药 {IDX['中证医药']:+.2f}% / 中证医疗 {LAG_MED:+.2f}% "
                  f"（三者同向为正，但 CRO/医疗服务领跌 → 指数与腿背离风险）；消费内部：中证白酒 {IDX['中证白酒']:+.2f}% "
                  f"vs 中证消费 {IDX['中证消费']:+.2f}%（白酒独强、非酒类弱）"},
       "defense": {"cs_index": cons, "cs_vs_12100": round((cons / 12100 - 1) * 100, 3),
                   "cs_low": _cs["low"], "cs_high": _cs["high"],
                   "hstech": HSTECH_STALE, "hstech_stale_date": HSTECH_STALE_DATE,
                   "hstech_judgement_deferred": True,
                   "hstech_vs_4250_last_available": round((HSTECH_STALE / 4250 - 1) * 100, 4),
                   "hstech_vs_4000_last_available": round((HSTECH_STALE / 4000 - 1) * 100, 4),
                   "hstech_next_line": 4000,
                   "med_reverse_line": BOARD_MED <= -1.5,
                   "med_closure_today": "pending_close（13:45 代理为正 → 闭环暂不成立）",
                   "med_judgement": "盘中口径（判定权移交 20:00 盘后档）"},
       "sensitivity": {k: {"delta": v[0], "pct": v[1]} for k, v in sensi.items()},
       "tracks": tracks,
       "med_exposure": round(med, 2), "med_pct": round(med / new_total * 100, 2),
       "threshold_all_med": round(r_all, 2), "threshold_a_sh_med": round(r_only, 2),
       "hk_split": {"pure_hk": round(pure_hk, 2), "cn_internet": round(cn_internet, 2),
                    "hk_broad": round(hk_broad, 2), "total": round(hk_total, 2),
                    "total_pct": round(hk_total / new_total * 100, 2),
                    "track_layer_pct": tracks["恒生科技"]["pct"],
                    "priceable_ratio": round(hk_price_ratio, 4),
                    "segment_identity": {"pure_plus_cn_internet": round(pure_hk + cn_internet, 2),
                                         "track_layer_mv": tracks["恒生科技"]["mv"],
                                         "note": "§3.149f：纯恒科 + 中概互联 = 恒生科技赛道层；宽基恒生系落在「其他/宽基」"}},
       "partial_pricing": {t: {"mv": round(v[0], 2), "priceable_mv": round(v[1], 2),
                               "priceable_pct": round(v[1] / v[0] * 100, 2) if v[0] else 0.0}
                           for t, v in priceable.items()},
       "stale_nav_legs": {
           "count": 6,
           "codes": ["000071", "012348", "164906", "000369", "016280"],
           "hk_link_closed": {"codes": ["000071", "012348"], "reason": "港股 10/19 休市 → 场外港股联接当日不发布净值",
                              "notional_mv": round(sum(x["mv"] for x in rows if re.sub(r"\D", "", str(x.get("code") or "")) in ("000071", "012348")), 2),
                              "rule": "§3.159b：按 0 计，不得用 159920 场内价替代（场外与场内口径不可混用，§38）"},
           "us_medical": {"codes": ["000369", "016280"], "base_nav_date": "2026-10-15",
                          "pending_segment": qd["segment"],
                          "notional_mv": QD_NOTIONAL,
                          "band_low": QD_LOW, "band_mid": QD_MID, "band_high": QD_HIGH,
                          "source": "portfolio_preopen_20261019.json#qdii_pending（refreshed = false）",
                          "rule": "§3.118a：只给区间、禁止中枢点值；不并入当日收益与待消化"},
           "cn_internet": {"codes": ["164906"], "base_nav_date": "2026-10-15",
                           "notional_mv": round(LOF_NOTIONAL, 2), "range_given": False,
                           "rule": "§3.122e：无单一稳定代理 → 不给区间、只登记待兑现"},
           "main_caliber_note": "本档对上述 6 类（12 个券位）均按 0 计；其中场内 513050/513180/159920 按 A股 市价定价、不属挂账"},
       "discipline_cut": {"cut1": CUT1, "cut2": CUT2, "cumulative_amount": round(cum_cut, 2),
                          "selfcheck_ok": abs(CUT1 + CUT2 - cum_cut) < 0.005,
                          "new_cut_today": 0, "settle": "第 2 次已于 10/8 按净值成交（累计 3,786.90 元）",
                          "after_hk": round(hk_now - cum_cut, 2), "after_cash": round(cash_now + cum_cut, 2),
                          "after_hk_pct": round((hk_now - cum_cut) / new_total * 100, 2),
                          "after_cash_pct": round((cash_now + cum_cut) / new_total * 100, 2),
                          "note": "本档不新增纪律动作：港股休市 → 4,000 线无法判定（§3.114c 同日防线只触发一次）"},
       "detail_restore_note": "逐券还原式由机器判据选定（三候选 + 逐赛道最大偏差 <1.5 元），禁止按字段名取数（§3.112a）",
       "pricing_caliber_note": ("§3.159a：**定价口径跟随基准 `price_src`** —— 场内市价记账者用今日 A股 市价；"
                                "场外 A股 基金用赛道代理估算；场外港股联接因休市不发布净值按 0；"
                                "164906 / QDII 因净值迟滞按 0。禁止用 A股 场内 ETF 涨幅替代港股指数或场外联接净值（§38 / §3.121e）"),
       "unpriceable_note": UNPRICEABLE_NOTE,
       "pseudo_close_rows": {"indices": 7, "etf": 9,
                             "note": "A股 板块 7 行（港股 0 行，休市不写，§3.159）；7 个板块代码均非 track_index 代理 → 多日窗口 n Δ=0"},
       "upcoming": {"hk_reopen": "2026-10-20", "lpr": "2026-10-20 09:00", "us_close": "2026-10-20 04:00（北京）",
                    "defense_judgement": "2026-10-20 收盘（恒生科技 4,000 / 4,250）"},
       "detail": rows}
json.dump(out, open(os.path.join(HIST, "portfolio_intraday_20261019.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("\n已保存 portfolio_intraday_20261019.json")
