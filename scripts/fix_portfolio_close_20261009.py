#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix_portfolio_close_20261009.py — 补正 2026-10-09 收盘产物（000051 净值到位）

背景（§3.139e / §3.105）：
  10/09 20:02 首抓时 `000051`（华夏沪深300ETF联接A）10/9 净值**尚未发布** →
  该券按「基准已含 → 计 0」处理，组合当日损益被系统性低估。
  本档（10/11）复抓确认 000051 **10/9 净值 = 1.6588（+0.17%）**已出库
  → 按 §3.105「次日盘前档兜底补抓并以 _fix 覆盖本档读数」执行。

硬守卫（§3.115a / §3.33）：
  ① `|Σ tracks.mv − total_mv| < 1.5`
  ② `|Σ tracks.pnl − est_total_pnl| < 1.5`
  ③ `_fix` 总量起点必须取 `base['base_total']`（= 前一收盘 374,466.56），**不得用 `base['total_mv']`**
"""
import copy
import json
import os

ROOT = "/Users/jieyang/Documents/WealthHub"
HIST = os.path.join(ROOT, "data/processed/history")
SRC = os.path.join(HIST, "portfolio_close_20261009.json")
DST = os.path.join(HIST, "portfolio_close_20261009_fix.json")
TODAY = "2026-10-11"
FIX_TARGET = "2026-10-09"

base = json.load(open(SRC, encoding="utf-8"))
d = copy.deepcopy(base)

# ---- 0. 定位 000051 明细行
rows = [x for x in d["detail"] if str(x["code"]).split(".")[0] == "000051"]
assert len(rows) == 1, f"000051 应唯一命中，实际 {len(rows)} 行"
row = rows[0]

NEW_NAV_DATE = "2026-10-09"
OLD_NAV = 1.656     # 10/8 净值（基准）
NEW_NAV = 1.6588    # 10/9 净值（本次补抓）
SHARES = float(row["shares"])
PCT = round((NEW_NAV / OLD_NAV - 1) * 100, 4)
PNL = round(SHARES * (NEW_NAV - OLD_NAV), 2)

print(f"000051 {row['name']}：shares={SHARES}  旧净值 {OLD_NAV}(10/8) → 新净值 {NEW_NAV}(10/9)")
print(f"  修正 est_pct = {PCT}%   est_pnl = {PNL} 元   （原计 0）")

old_est_pnl = d["est_total_pnl"]
old_total_mv = d["total_mv"]
old_track_pnl = d["tracks"]["其他/宽基"]["pnl"]
old_track_mv = d["tracks"]["其他/宽基"]["mv"]

# ---- 1. 逐券行修正
row["price_src"] = (f"净值 10/9 ({NEW_NAV})，基准净值日 2026-10-08"
                    "（§3.105 补正：10/09 档首抓时未出库，本档兜底补抓）")
row["est_pct"] = PCT
row["est_pnl"] = PNL
row["est_pct_best"] = PCT
row["est_pnl_best"] = PNL
row["est_pct_worst"] = PCT
row["est_pnl_worst"] = PNL
row["est_pnl_low"] = PNL
row["mv"] = round(row["mv"] + PNL, 2)
row["fix_applied"] = True

# ---- 2. 赛道行修正（§3.115a：必须同步重算 tracks[].pnl）
d["tracks"]["其他/宽基"]["pnl"] = round(old_track_pnl + PNL, 2)
d["tracks"]["其他/宽基"]["mv"] = round(old_track_mv + PNL, 2)

# ---- 3. 总量修正（起点 = base_total 前一收盘）
d["est_total_pnl"] = round(old_est_pnl + PNL, 2)
d["total_mv"] = round(old_total_mv + PNL, 2)
d["est_total_pct"] = round(d["est_total_pnl"] / d["base_total"] * 100, 4)
d["est_total_pct_raw"] = round(d["est_total_pnl"] / d["base_total"] * 100, 4)
d["est_total_pnl_best"] = round(d.get("est_total_pnl_best", old_est_pnl) + PNL, 2)
d["est_total_pnl_worst"] = round(d.get("est_total_pnl_worst", old_est_pnl) + PNL, 2)
d["est_total_pnl_high"] = d["est_total_pnl_best"]
d["est_total_pnl_low"] = d["est_total_pnl_worst"]

# ---- 4. 硬守卫（§3.115a 双守卫）
sum_track_mv = round(sum(v["mv"] for v in d["tracks"].values()), 2)
sum_track_pnl = round(sum(v["pnl"] for v in d["tracks"].values()), 2)
dev_mv = round(sum_track_mv - d["total_mv"], 2)
dev_pnl = round(sum_track_pnl - d["est_total_pnl"], 2)
print(f"\n[守卫①] Σtracks.mv = {sum_track_mv}  vs total_mv = {d['total_mv']}  → dev = {dev_mv}")
print(f"[守卫②] Σtracks.pnl = {sum_track_pnl}  vs est_total_pnl = {d['est_total_pnl']}  → dev = {dev_pnl}")
assert abs(dev_mv) < 1.5, f"守卫①未通过：{dev_mv}"
assert abs(dev_pnl) < 1.5, f"守卫②未通过：{dev_pnl}"
print("  ✅ 双硬守卫通过")

# 起点守卫：base_total 必须是前一收盘
assert d["base_total"] == 374466.56, f"base_total 异常: {d['base_total']}"
assert abs(d["base_total"] + d["est_total_pnl"] - d["total_mv"]) < 1.5, "总量还原式不成立"
print(f"  ✅ 还原式 base_total({d['base_total']}) + est_total_pnl({d['est_total_pnl']}) = total_mv({d['total_mv']})")

# ---- 5. 补正元数据
d["fix"] = {
    "fix_of": f"portfolio_close_{FIX_TARGET.replace('-', '')}.json",
    "fix_made_at": f"{TODAY} 20:00 盘后档（纯非交易日）",
    "fix_reason": ("000051（华夏沪深300ETF联接A）10/9 净值在 10/09 档 20:02 首抓时尚未出库，"
                   "按「基准已含 → 计 0」处理致组合当日损益低估；本档复抓确认 10/9 净值 1.6588（+0.17%）已出库"
                   "→ 按 §3.105 / §3.139e 执行 _fix 补正"),
    "fix_items": [{
        "code": "000051", "name": row["name"], "account": row["account"], "track": "其他/宽基",
        "shares": SHARES, "base_nav": OLD_NAV, "base_nav_date": "2026-10-08",
        "new_nav": NEW_NAV, "new_nav_date": NEW_NAV_DATE,
        "est_pct": PCT, "est_pnl_元": PNL, "before_est_pnl_元": 0.0,
    }],
    "before": {"est_total_pnl_元": old_est_pnl, "est_total_pct": base["est_total_pct"],
               "total_mv_元": old_total_mv, "其他/宽基_pnl_元": old_track_pnl,
               "其他/宽基_mv_元": old_track_mv},
    "after": {"est_total_pnl_元": d["est_total_pnl"], "est_total_pct": d["est_total_pct"],
              "total_mv_元": d["total_mv"], "其他/宽基_pnl_元": d["tracks"]["其他/宽基"]["pnl"],
              "其他/宽基_mv_元": d["tracks"]["其他/宽基"]["mv"]},
    "delta": {"est_total_pnl_元": round(d["est_total_pnl"] - old_est_pnl, 2),
              "est_total_pct": round(d["est_total_pct"] - base["est_total_pct"], 4),
              "total_mv_元": round(d["total_mv"] - old_total_mv, 2)},
    "guards": {"dev_sum_track_mv_vs_total_mv": dev_mv, "dev_sum_track_pnl_vs_est_total_pnl": dev_pnl,
               "restore_from": "base_total（前一收盘 374,466.56 元），非 total_mv"},
    "restore_rule_used": base.get("restore_rule_used"),
    "detail_restore_rule": base.get("detail_restore_rule"),
    "chain_0pct_row_inserted": False,
    "note": ("本补正件**不覆盖**原产物 portfolio_close_20261009.json，另存 _fix 供链式序列与周报取用"
             "（§3.108：同日期以 _fix 为准）。"),
}

with open(DST, "w", encoding="utf-8") as f:
    json.dump(d, f, ensure_ascii=False, indent=1)

print(f"\n✅ 写盘 {DST}")
print(f"   组合当日损益：{old_est_pnl} 元 → {d['est_total_pnl']} 元（Δ {d['fix']['delta']['est_total_pnl_元']:+}）")
print(f"   组合当日涨幅：{base['est_total_pct']:.4f}% → {d['est_total_pct']:.4f}%（Δ {d['fix']['delta']['est_total_pct']:+.4f}pct）")
print(f"   组合总资产：  {old_total_mv} 元 → {d['total_mv']} 元")
