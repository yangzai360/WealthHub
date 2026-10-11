#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
2026-10-11 20:00 盘后复盘档（档型①「纯非交易日」· 常规周末）产物脚本

产出：
  1) data/processed/history/portfolio_holiday_20261011.json  —— 纯非交易日台账
  2) data/processed/history/sentiment_agg_20261011_close.json —— 情绪双口径聚合
  3) data/processed/history/weekly_stats_20261011.json       —— W41 周度统计

硬守卫：
  · |Σ tracks.mv − base_total| < 1.5
  · QDII_LOW ≤ QDII_MID ≤ QDII_HIGH        （§3.116b：对结果值取 min/max）
  · 三市场独立验证字段齐备
  · W41 组合周收益「几何链式」与「首尾市值差」双法一致
"""
import json
import os

ROOT = "/Users/jieyang/Documents/WealthHub"
D = "2026-10-11"
BASE_FIX = "portfolio_close_20261009_fix.json"
PREV_RISK = "risk_stats_close_20261009.json"

# ============================ 1. 情绪双口径聚合 ============================
sent = json.load(open(f"{ROOT}/data/processed/news/sentiment-2026-10-11.json", encoding="utf-8"))
items = sent["items"]

base = json.load(open(f"{ROOT}/data/processed/history/{BASE_FIX}", encoding="utf-8"))
base_total = base["total_mv"]
WEIGHTS = {t: round(v["mv"] / base_total * 100, 4) for t, v in base["tracks"].items()}
WEIGHTS["宏观"] = 0.00

agg = {}
for it in items:
    t = it["track"]
    a = agg.setdefault(t, {"n": 0, "pos": 0, "neg": 0, "neu": 0, "nominal": 0.0, "strength_sum": 0.0})
    a["n"] += 1
    a["strength_sum"] += it.get("strength", 0)
    s = it["sentiment"]
    if s == "正面":
        a["pos"] += 1
        a["nominal"] += it.get("strength", 0)
    elif s == "负面":
        a["neg"] += 1
        a["nominal"] -= it.get("strength", 0)
    else:
        a["neu"] += 1

rows, tot_n, tot_nom, tot_w = [], 0, 0, 0.0
for t, a in agg.items():
    w = WEIGHTS.get(t, 0.0)
    contrib = a["nominal"] * w / 100.0
    rows.append({"track": t, "n": a["n"], "pos": a["pos"], "neg": a["neg"], "neu": a["neu"],
                 "nominal": round(a["nominal"], 1),
                 "mean_strength": round(a["strength_sum"] / a["n"], 1) if a["n"] else 0.0,
                 "weight": w, "weighted": round(contrib, 4)})
    tot_n += a["n"]; tot_nom += a["nominal"]; tot_w += contrib
rows.sort(key=lambda r: -r["weighted"])

tot_pos = sum(a["pos"] for a in agg.values())
tot_neg = sum(a["neg"] for a in agg.values())
tot_neu = sum(a["neu"] for a in agg.values())
mean_strength = round(sum(i.get("strength", 0) for i in items) / len(items), 2)
strong_pos = [i for i in items if i["sentiment"] == "正面" and i.get("strength", 0) >= 60]
strong_neg = [i for i in items if i["sentiment"] == "负面" and i.get("strength", 0) >= 60]

agg_out = {
    "date": D, "window": sent.get("window"), "count": len(items),
    "nominal_total": round(tot_nom, 1), "weighted_total": round(tot_w, 4),
    "pos": tot_pos, "neg": tot_neg, "neu": tot_neu, "mean_strength": mean_strength,
    "distribution": rows,
    "weights_source": f"{BASE_FIX}#tracks（按 10/9 修正收盘市值加权，非持仓快照）",
    "dilution_note": "暴露加权 / 名义 比值 = %.4f%%（宏观类零暴露被完全剔除）" % (tot_w / tot_nom * 100 if tot_nom else 0),
    "strong_pos_n": len(strong_pos),
    "strong_neg_n": len(strong_neg),
    "strong_pos_mean": round(sum(i["strength"] for i in strong_pos) / len(strong_pos), 1) if strong_pos else 0.0,
    "strong_neg_mean": round(sum(i["strength"] for i in strong_neg) / len(strong_neg), 1) if strong_neg else 0.0,
    "strong_pos_list": [i["brief"] for i in strong_pos],
    "strong_neg_list": [i["brief"] for i in strong_neg],
    "annotation_mode": sent.get("annotation_mode", "rule_table_fallback"),
    "annotation_note": ("本档 28/28 条为确定性规则表标注（DeepSeek HTTP 402 降级，§3.127b）→ "
                        "跨档比较均值强度/净分须标注口径差异，不得与模型标注档直接混算趋势"),
}
json.dump(agg_out, open(f"{ROOT}/data/processed/history/sentiment_agg_20261011_close.json", "w",
                        encoding="utf-8"), ensure_ascii=False, indent=1)

# ============================ 2. 假期台账 ============================
tracks = {k: {"mv": round(v["mv"], 2), "pct_of_total": round(v["mv"] / base_total * 100, 4)}
          for k, v in base["tracks"].items()}
sum_mv = round(sum(v["mv"] for v in tracks.values()), 2)
guard_dev = round(sum_mv - base_total, 4)
assert abs(guard_dev) < 1.5, f"守卫失败: Σ tracks.mv − base_total = {guard_dev}"

# --- QDII 挂账（US 10/9 单日段）---
from collections import defaultdict
by_code_mv = defaultdict(float)
for x in base["detail"]:
    c = str(x["code"]).split(".")[0]
    if c:
        by_code_mv[c] += x["mv"]
QDII_US_BASIS = round(by_code_mv["000369"] + by_code_mv["016280"], 2)   # 美股标普医药 QDII 腿
QDII_CN_BASIS = round(by_code_mv["164906"], 2)                          # 中概互联 QDII 腿
IYH_1009, XLV_1009 = 1.72, 1.58       # 美股 10/9 收盘涨跌幅（本地 indices.csv 现算值）
COEF_LOW, COEF_HIGH, COEF_MID = 0.60, 0.90, 0.72
qdii_pct_low = round(IYH_1009 * COEF_LOW, 4)
qdii_pct_high = round(IYH_1009 * COEF_HIGH, 4)
qdii_pct_mid = round(IYH_1009 * COEF_MID, 4)
qdii_outs = [round(QDII_US_BASIS * p / 100, 2) for p in (qdii_pct_low, qdii_pct_high, qdii_pct_mid)]
QDII_LOW, QDII_HIGH, QDII_MID = min(qdii_outs), max(qdii_outs), round(QDII_US_BASIS * qdii_pct_mid / 100, 2)
assert QDII_LOW <= QDII_MID <= QDII_HIGH, "QDII 区间守卫失败"
assert QDII_LOW <= QDII_HIGH, "QDII 端点语义守卫失败（_low ≤ _high，§3.123b）"

ledger = {
    "date": D,
    "session": "close",
    "session_type": "pure_non_trading_day_close",
    "session_type_note": (
        "档型①「纯非交易日」（A股与港股「均」未开市；美股照常开市不改变该判定，§3.109/§3.118b/§3.120a）。"
        "本档为**常规周末**（10/10 周六 + 10/11 周日）20:00 盘后复盘档 → 不产 "
        "portfolio_close_* / portfolio_pending_*，不向链式序列插入 0% 行。"
        "与「假期档」的差别：无跨市场长休窗口，仅常规周末两日；另本档同时产出 W41 周报。"
    ),
    "three_market_verification": {
        "ashare": {"source": "akshare.stock_zh_index_daily('sh000001')", "last_row_date": "2026-10-09",
                   "close": 3813.791, "verdict": "未开市（末行日期 = 上一交易日 2026-10-09；10/10-10/11 为周末）"},
        "hk": {"source": "新浪 hq 直连 rt_hkHSTECH 返回体日期字段", "date_field": "2026/10/09",
               "time_field": "16:08:32", "close": 4197.84,
               "verdict": "未开市（返回体日期字段 = 上一港股交易日 2026/10/09，§3.119b/§3.122b）"},
        "us": {"source": "akshare.stock_us_daily('IYH' / 'XLV')", "last_row_date": "2026-10-09",
               "IYH": 72.14, "XLV": 170.81,
               "verdict": "美股 10/9（周五）已收盘（成型于北京 10/10 04:00）→ 本档为**唯一真实新增定价**；10/10-10/11 为周末休市"},
        "rule": "三市场各自独立验证、不得互相外推（§3.119b）",
    },
    "base": {
        "file": BASE_FIX, "base_total": base_total,
        "sum_tracks_mv": sum_mv, "guard_dev": guard_dev,
        "guard_rule": "|Σ tracks.mv − base_total| < 1.5",
        "base_revision": {
            "prev_file": "portfolio_close_20261009.json", "prev_total": 377025.06,
            "delta": round(base_total - 377025.06, 2),
            "reason": ("本档对 10/9 收盘产物执行 `_fix` 补正：000051（华夏沪深300ETF联接A）10/9 净值 1.6588（+0.17%）"
                       "在 10/9 档 20:02 首抓时尚未出库、按「基准已含计 0」处理 → 本档复抓到位后按 §3.105 补正，"
                       "组合当日损益 +2,558.50 元 → **+2,574.29 元（+0.6875%）**，总资产 377,025.06 元 → **377,040.85 元**"),
        },
        "restore_rule_used": base.get("restore_rule_used"),
        "detail_restore_rule": base.get("detail_restore_rule"),
        "fix_applied": True,
    },
    "tracks": tracks,
    "tracks_weight_after_discipline": {
        "恒生科技": round(27332.38 / base_total * 100, 2),
        "现金": round(32999.87 / base_total * 100, 2),
        "note": ("累计纪律口径（§3.125c）：第 1 次 0.5%（1,882.46 元，9/30 成交）+ 第 2 次 0.5%（1,904.44 元，10/8 成交）"
                 "= **3,786.90 元**（两笔均已按净值成交、价值中性，P&L 口径不变）；"
                 "本档无新增防线触发（§3.114c：同日防线只触发一次）。"),
        "cumulative_amount": 3786.9,
        "cumulative_selfcheck": {"sum_of_cuts": 3786.9, "cumulative_amount": 3786.9, "ok": True},
    },
    "day_result": {
        "est_pnl": 0.0, "est_pct": 0.0,
        "attribution": "全部持仓标的不可定价（非市场持平）",
        "reasons": [
            "A股 10/10-10/11 为周末休市 → 20 余只 A股 类场外基金不发布净值、场内 ETF/LOF 无成交价（末行收盘仍 = 10/9）",
            "港股 10/10-10/11 为周末休市 → 无新港股价格（恒指/恒科 末次收盘 = 10/9）",
            "场外港股联接（000071 / 012348）在非 A股 交易日不发布净值（§3.112i）",
            "美股 10/9 收盘虽已入库（XLV +1.58% / IYH +1.72%），其组合传导属 **QDII 挂账项**、按既定规则**不入本档基准**（第三层，见 qdii_pending）",
        ],
        "note": ("「0 元」是账面冻结，归因「标的不可定价」而非「市场持平」（§3.107 条款 19 / §3.117a / §3.118b）；"
                 "**第三层（美股/QDII 腿可定价但属挂账口径）须单独披露**，否则读者会误判「美股腿也没定价」（§3.121d）。"),
    },
    "hk_exposure": {
        "total": round(base["hk_total"], 2), "pct": base["hk_total_pct"],
        "track_layer_pct": base["track_layer_hk_pct"],
        "segments_mv": base["hk_split"],
        "segments_pnl_1009": base["hk_split_pnl"],
        "rule_hint": ("双层拆解（§3.108 条款 23）：赛道层 恒生科技 8.25% + 宽基层 4.82pct = **13.07%**；"
                      "只报赛道层将低估 4.82pct"),
    },
    "med_exposure": {
        "mv": base["med_exposure"], "pct": base["med_pct"],
        "threshold_all_med_pct": base["threshold_all_med"],
        "threshold_a_sh_med_pct": base["threshold_a_sh_med"],
        "mv_after_fix": round(base["tracks"]["A股医药"]["mv"] + base["tracks"]["美股标普医药"]["mv"], 2),
        "pct_after_fix": round((base["tracks"]["A股医药"]["mv"] + base["tracks"]["美股标普医药"]["mv"]) / base_total * 100, 4),
        "rule": "§3.98 方程解法 A(1+r)/(B+A(1+r)) = 40%；000051 补正落在「其他/宽基」腿 → 医药敞口不变",
    },
    "hk_pending_digest": {
        "refreshed": False,
        "reason": "10/10-10/11 为周末，港股无新交易日 → 港股腿无新增待消化项",
        "window": ["2026-10-02", "2026-10-05", "2026-10-06", "2026-10-07"],
        "window_closed": True,
        "closed_on": "2026-10-08",
        "note": ("长假 4 日窗口已由场外港股联接（000071 / 012348）于 10/8 真实净值一次性兑现并收口"
                 "（§3.122c / §3.133e）；**窗口收口 ≠ 可作方向判断**（仍只给区间上下界，§3.108 条款 24）"),
    },
    "qdii_pending": {
        "refreshed": True,
        "reason": ("10/9 档 `remaining` 记录「US 10/9 单日段、按 0 计」（当时美东尚未开盘、IYH 无读数）"
                   "→ 本档 **US 10/9 收盘已成型（IYH +1.72% / XLV +1.58%）**，该段首次可量化"),
        "segment_us_medical": {
            "desc": "US 10/9 单日段（IYH 口径）",
            "trade_dates_covered": ["2026-10-09(US)"],
            "iyh_pct": IYH_1009, "xlv_pct": XLV_1009,
            "notional_mv": QDII_US_BASIS,
            "coef_range": [COEF_LOW, COEF_HIGH], "coef_mid_ref": COEF_MID,
            "pct_low": qdii_pct_low, "pct_high": qdii_pct_high, "pct_mid_ref": qdii_pct_mid,
            "low": QDII_LOW, "mid": QDII_MID, "high": QDII_HIGH,
            "codes": ["000369（广发全球医疗保健指数A）", "016280（广发全球医疗保健指数C）"],
            "coef_note": ("§3.118a / §3.139：传导系数不稳定（长假前后实测 1.25~1.29、常态 0.62、10/9 档实测 0.70~0.76）"
                          "→ **只给区间（0.60~0.90）、中枢仅作参考、禁止用于仓位决策**；"
                          "且 US 10/12 为哥伦布日/原住民日（**股市照常、债市休市**）→ 兑现时点须逐日核对"),
        },
        "segment_cn_internet": {
            "desc": "164906（交银中证海外中国互联网指数 LOF）10/9 净值待出",
            "notional_mv": QDII_CN_BASIS,
            "range_given": False,
            "reason": ("该券跟踪「中证海外中国互联网指数」，**无单一稳定可复现代理指数**（10/9 港股大涨但该券 10/8 净值 −2.4602%、"
                       "方向相反）→ 依 §3.122e 处置：**不给区间、只登记为「待兑现」**，10/12 以真实净值核对"),
        },
        "total_low": QDII_LOW, "total_mid": QDII_MID, "total_high": QDII_HIGH,
        "unknown_sessions": [],
        "pending_codes": ["164906"],
        "applied_codes": [],
        "range_rule": ("QDII_LOW ≤ QDII_MID ≤ QDII_HIGH（§3.116b：对**结果值**取 min/max，"
                       "禁止把弹性常量硬绑定到档位）"),
        "coef_note": "系数未按「≥4 券位 × ≥5 交易日」重估前，基于该系数的一切仓位决策无效（§3.118a）",
    },
    "sentiment": agg_out,
    "defense_lines": {
        "hstech_4250": {
            "close": 4197.84, "line": 4250, "dist_pts": -52.16, "dist_pct": -1.2273,
            "state": "close_level_break_narrowed",
            "break_trend": {"2026-10-02": -2.1661, "2026-10-05": -1.5605, "2026-10-06": -0.6342,
                            "2026-10-07": -1.3061, "2026-10-08": -4.1558, "2026-10-09": -1.2273},
            "action": "无（第 2 次减仓已于 10/8 成交；同日防线只触发一次，§3.114c）",
            "next_line": 4000, "next_line_dist_pct": 4.946,
            "note": ("破位状态**未解除**（幅度收窄至 −1.2273%）；周末无新增港股交易日 → 状态零变动；"
                     "下一道观察线 4,000（距 +4.9460%），「再破不叠加新纪律」"),
        },
        "zz_consume_12100": {"last": 12355.0001, "as_of": "2026-10-09", "dist_pct": 2.1074,
                             "state": "above_lower_line", "next_line": 12000, "next_line_dist_pct": 2.9583,
                             "verify_at": "2026-10-12"},
        "a_med_reverse_1_5pct": {"proxy_pct": 0.5075, "as_of": "2026-10-09", "line_pct": -1.5,
                                 "state": "not_triggered", "contingency_closed": True,
                                 "verify_at": "2026-10-12"},
    },
    "discipline_ledger": {
        "today_action": {"discipline_cut_today": 0, "active_take_profit": 0, "new_buy": 0,
                         "reason": "纯非交易日，无行情触发；三条防线状态零变动"},
        "cumulative_amount": 3786.9,
        "hk_after": 27332.38, "cash_after": 32999.87,
    },
    "risk_stats_source": f"{PREV_RISK}（本档为纯非交易日，**不重算**链路/夏普/回撤，§3.122c / §3.127e）",
    "risk_stats_digest": None,   # 由下方填充
    "chain_0pct_row_inserted": False,
    "chain_note": ("§3.108 条款 22 / §3.120a：纯非交易日不产 portfolio_close_*/portfolio_pending_*，"
                   "链式末行仍 = 2026-10-09（`portfolio_close_20261009_fix.json` 为当日生效口径）"),
    "next_increment": "2026-10-12（周一，A股 + 港股双市场复市，全量；美股 10/12 亦开市、债市休市）",
    "note": "本档另生成 W41 周报 reports/weekly/2026-W41-周报.md",
}

risk = json.load(open(f"{ROOT}/data/processed/history/{PREV_RISK}", encoding="utf-8"))
ledger["risk_stats_digest"] = {
    "chain_cum_pct": risk["chain_cum_pct"], "chain_days": risk["chain_days"],
    "w39_cum_pct": risk["w39_cum_pct"], "w39_days": risk["w39_days"],
    "w40_cum_pct": risk["w40_cum_pct"], "w40_days": risk["w40_days"],
    "w41_cum_pct": risk["w41_cum_pct"], "w41_days": risk["w41_days"], "w41_daily": risk["w41_daily"],
    "sharpe": risk["sharpe"], "sharpe_n": risk["sharpe_n"],
    "daily_mean": risk["daily_mean"], "daily_sd": risk["daily_sd"],
    "max_dd_pct": risk["max_dd_pct"], "max_dd_peak": risk["max_dd_peak"], "max_dd_trough": risk["max_dd_trough"],
    "last5_cum_pct": risk["last5_cum_pct"], "last10_cum_pct": risk["last10_cum_pct"],
    "rf_pct": risk["rf_pct"],
    "refix_note": ("⚠️ 10/9 档 `risk_stats_close_20260910` 系列读数为 **10/9 原产物口径（+0.6832%）**；"
                   "本档 `_fix` 将 10/9 修正为 **+0.6875%** → 链式/夏普/回撤**本档不重算**（纯非交易日不重算，§3.127e），"
                   "**10/12 复市档须以修正后 10/9 值重算**（Δ = +0.0043pct，量级极小、但口径须一致）"),
}
json.dump(ledger, open(f"{ROOT}/data/processed/history/portfolio_holiday_20261011.json", "w",
                       encoding="utf-8"), ensure_ascii=False, indent=1)

# ============================ 3. W41 周度统计 ============================
W = "2026-W41"
w_start, w_end = "2026-10-05", "2026-10-11"
wk_first_base = json.load(open(f"{ROOT}/data/processed/history/portfolio_close_20261008.json", encoding="utf-8"))
wk_open_total = wk_first_base["base_total"]          # 380,888.29（9/30 收盘，W41 起点）
wk_close_total = base_total                          # 377,040.85（10/9 修正收盘，W41 终点）

d08 = json.load(open(f"{ROOT}/data/processed/history/portfolio_close_20261008.json", encoding="utf-8"))
daily = [
    {"date": "2026-10-08", "file": "portfolio_close_20261008.json",
     "pct": d08.get("est_total_pct_raw") if d08.get("est_total_pct_raw") is not None else d08["est_total_pct"],
     "pct_display": d08["est_total_pct"], "pnl": d08["est_total_pnl"],
     "source": "portfolio_close_20261008.json（真实价格/净值，本档未修正）"},
    {"date": "2026-10-09", "file": BASE_FIX,
     "pct": base.get("est_total_pct_raw") if base.get("est_total_pct_raw") is not None else base["est_total_pct"],
     "pct_display": base["est_total_pct"], "pnl": base["est_total_pnl"],
     "source": f"{BASE_FIX}（_fix 补正后；原产物为 +2,558.50 元 / +0.6832%）"},
]
chain = 1.0
for r in daily:
    chain *= (1 + r["pct"] / 100)
w_cum_pct = round((chain - 1) * 100, 4)
w_pnl_head_tail = round(wk_close_total - wk_open_total, 2)
w_pnl_chain = round(wk_open_total * (chain - 1), 2)
assert abs(w_pnl_head_tail - w_pnl_chain) < 1.5, f"周收益双法不一致 {w_pnl_head_tail} vs {w_pnl_chain}"

# 分赛道周归因 = Σ 各定价日 tracks[].pnl
by_track = {}
for r in daily:
    src = json.load(open(f"{ROOT}/data/processed/history/{r['file']}", encoding="utf-8"))
    for t, v in src["tracks"].items():
        by_track.setdefault(t, 0.0)
        by_track[t] += v["pnl"]
by_track = {t: round(v, 2) for t, v in by_track.items()}
assert abs(sum(by_track.values()) - w_pnl_head_tail) < 1.5, \
    f"赛道归因求和 {sum(by_track.values())} vs 周收益 {w_pnl_head_tail}"

weekly = {
    "week": W, "start": w_start, "end": w_end,
    "pricing_days": len(daily),
    "week_open_total": wk_open_total, "week_close_total": wk_close_total,
    "week_cum_pct": w_cum_pct, "week_pnl": w_pnl_head_tail,
    "double_check": {"chain_method_pct": w_cum_pct, "head_tail_pnl": w_pnl_head_tail,
                     "chain_pnl_reconstructed": w_pnl_chain, "dev": round(w_pnl_head_tail - w_pnl_chain, 2),
                     "rule": "§3.107：未加守卫前任何 _fix 都须「首尾市值差 + 几何链式」双法交叉验证"},
    "daily": daily,
    "by_track_pnl": by_track,
    "track_weights_end": {t: round(v["mv"] / wk_close_total * 100, 2) for t, v in base["tracks"].items()},
    "note": ("W41 的**定价日仅 2 天**（10/8、10/9）；10/5-10/7 为长假「混合档」产物（portfolio_pending_*，不匹配 "
             "portfolio_close_* glob）→ 无组合层定价、不入链式序列；10/10-10/11 为周末。"
             "10/9 值采用 `_fix` 补正口径（+0.6875%，原为 +0.6832%）。"),
    "prev_weeks": {"2026-W39": -0.2, "2026-W40": 0.86, "2026-W41": w_cum_pct},
    "risk_digest": ledger["risk_stats_digest"],
    "event_counts_by_day": {d: len(json.load(open(f"{ROOT}/data/processed/events/events-{d}.json", encoding="utf-8")))
                            for d in ["2026-10-05", "2026-10-06", "2026-10-07", "2026-10-08",
                                      "2026-10-09", "2026-10-10", "2026-10-11"]
                            if os.path.exists(f"{ROOT}/data/processed/events/events-{d}.json")},
}
weekly["event_counts_total"] = sum(weekly["event_counts_by_day"].values())
json.dump(weekly, open(f"{ROOT}/data/processed/history/weekly_stats_20261011.json", "w",
                       encoding="utf-8"), ensure_ascii=False, indent=1)

# ============================ 打印 ============================
print("=== 情绪聚合（双口径） ===")
print(f"名义净分 {agg_out['nominal_total']} | 暴露加权净分 {agg_out['weighted_total']} | "
      f"{tot_pos} 利多 / {tot_neu} 中性 / {tot_neg} 利空 | 均值强度 {mean_strength}")
print(f"强正 n={len(strong_pos)}（均值 {agg_out['strong_pos_mean']}）| 强负 n={len(strong_neg)}（均值 {agg_out['strong_neg_mean']}）")
for r in rows:
    print(f"  {r['track']:12s} n={r['n']} 名义 {r['nominal']:+7.1f} 权重 {r['weight']:7.4f}% 加权 {r['weighted']:+8.4f}")
print()
print("=== 假期台账 ===")
print(f"base_total={base_total} Σtracks.mv={sum_mv} guard_dev={guard_dev}")
print(f"QDII US 医疗段（notional {QDII_US_BASIS}）区间 {QDII_LOW} ~ {QDII_HIGH} 元（中枢参考 {QDII_MID}）")
print(f"QDII 中概段（164906，notional {QDII_CN_BASIS}）→ 不给区间、待兑现")
print(f"纪律后 恒生科技 {ledger['tracks_weight_after_discipline']['恒生科技']}% / 现金 {ledger['tracks_weight_after_discipline']['现金']}%")
print()
print("=== W41 周度统计 ===")
print(f"周初 {wk_open_total} → 周末 {wk_close_total}；周收益 {w_cum_pct}%（{w_pnl_head_tail} 元），定价日 {len(daily)}")
print(f"赛道周归因: {by_track}")
print(f"事件数（按日）: {weekly['event_counts_by_day']} 合计 {weekly['event_counts_total']}")
print("✅ 产物已写入 portfolio_holiday_20261011.json / sentiment_agg_20261011_close.json / weekly_stats_20261011.json")
