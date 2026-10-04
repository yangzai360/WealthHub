#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
2026-10-04 20:00 盘后复盘档（档型①「纯非交易日」）产物脚本
产出：
  1) data/processed/history/portfolio_holiday_20261004.json  —— 假期台账（纯非交易日不产 close/pending）
  2) data/processed/history/sentiment_agg_20261004_close.json —— 情绪双口径聚合
硬守卫：
  · |Σ tracks.mv − base_total| < 1.5
  · HK_LOW ≤ HK_MID ≤ HK_HIGH（§3.116b）
  · QDII_LOW ≤ QDII_MID ≤ QDII_HIGH
  · 三市场独立验证字段齐备
"""
import json
import os

ROOT = "/Users/jieyang/Documents/WealthHub"
D = "2026-10-04"

# ---------- 1. 情绪双口径聚合 ----------
sent = json.load(open(f"{ROOT}/data/processed/news/sentiment-2026-10-04.json"))
items = sent["items"]
WEIGHTS = {
    "其他/宽基": 24.94,
    "大消费": 19.87,
    "现金": 7.67,
    "A股医药": 23.57,
    "美股标普医药": 15.66,
    "恒生科技": 8.29,
    "宏观": 0.00,
}
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

rows = []
tot_n = tot_nom = 0
tot_w = 0.0
for t, a in agg.items():
    w = WEIGHTS.get(t, 0.0)
    contrib = a["nominal"] * w / 100.0
    rows.append({
        "track": t, "n": a["n"], "pos": a["pos"], "neg": a["neg"], "neu": a["neu"],
        "nominal": round(a["nominal"], 1),
        "mean_strength": round(a["strength_sum"] / a["n"], 1) if a["n"] else 0.0,
        "weight": w, "weighted": round(contrib, 4),
    })
    tot_n += a["n"]
    tot_nom += a["nominal"]
    tot_w += contrib

rows.sort(key=lambda r: -r["weighted"])
tot_pos = sum(a["pos"] for a in agg.values())
tot_neg = sum(a["neg"] for a in agg.values())
tot_neu = sum(a["neu"] for a in agg.values())
mean_strength = round(sum(i.get("strength", 0) for i in items) / len(items), 2)

agg_out = {
    "date": D, "window": sent.get("window"), "count": len(items),
    "nominal_total": round(tot_nom, 1),
    "weighted_total": round(tot_w, 4),
    "pos": tot_pos, "neg": tot_neg, "neu": tot_neu,
    "mean_strength": mean_strength,
    "distribution": rows,
    "dilution_note": "暴露加权 / 名义 比值 = %.4f%%（宏观类零暴露被完全剔除）" % (tot_w / tot_nom * 100 if tot_nom else 0),
}
json.dump(agg_out, open(f"{ROOT}/data/processed/history/sentiment_agg_20261004_close.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)

strong_pos = [i for i in items if i["sentiment"] == "正面" and i.get("strength", 0) >= 60]
strong_neg = [i for i in items if i["sentiment"] == "负面" and i.get("strength", 0) >= 60]
agg_out["strong_pos_n"] = len(strong_pos)
agg_out["strong_neg_n"] = len(strong_neg)
agg_out["strong_pos_mean"] = round(sum(i["strength"] for i in strong_pos) / len(strong_pos), 1) if strong_pos else 0.0
agg_out["strong_neg_mean"] = round(sum(i["strength"] for i in strong_neg) / len(strong_neg), 1) if strong_neg else 0.0
json.dump(agg_out, open(f"{ROOT}/data/processed/history/sentiment_agg_20261004_close.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)

# ---------- 2. 假期台账 ----------
base = json.load(open(f"{ROOT}/data/processed/history/portfolio_close_20260930_fix.json"))
tracks = {k: {"mv": round(v["mv"], 2), "pct_of_total": v["pct_of_total"]} for k, v in base["tracks"].items()}
sum_mv = sum(v["mv"] for v in tracks.values())
base_total = base["total_mv"]
guard_dev = round(sum_mv - base_total, 4)
assert abs(guard_dev) < 1.5, f"守卫失败: Σ tracks.mv − base_total = {guard_dev}"

# 港股腿待消化（承接 10/2 正式版，无新增港股交易日）
prev_pend = json.load(open(f"{ROOT}/data/processed/history/portfolio_pending_20261002.json"))
hk_dig = prev_pend["hk_pending_digest"]
HK_LOW, HK_HIGH, HK_MID = hk_dig["total_low"], hk_dig["total_high"], hk_dig["mid_proxy_avg"]
assert HK_LOW <= HK_MID <= HK_HIGH, "HK 区间守卫失败"

# QDII 挂账：新增 US 10/2 定价行（IYH 0.00% / XLV −0.01%）→ 复合不变
qdii = prev_pend["qdii_pending"]
qdii_low, qdii_mid, qdii_high = qdii["total_low"], qdii["total_mid"], qdii["total_high"]
assert qdii_low <= qdii_mid <= qdii_high, "QDII 区间守卫失败"

ledger = {
    "date": D,
    "session": "close",
    "session_type": "pure_non_trading_day_close",
    "session_type_note": (
        "档型①「纯非交易日」（A股与港股「均」未开市；美股周末亦休市，§3.109/§3.118b/§3.120a）。"
        "本档为国庆长假第 4 日（周日）20:00 盘后复盘档 → 不产 portfolio_close_* / portfolio_pending_*，"
        "不向链式序列插入 0% 行。"
    ),
    "three_market_verification": {
        "ashare": {"source": "akshare.stock_zh_index_daily('sh000001')", "last_row_date": "2026-09-30",
                   "close": 3842.195, "verdict": "未开市（末行日期 = 上一交易日 2026-09-30）"},
        "hk": {"source": "新浪 hq 直连 rt_hkHSTECH 返回体日期字段", "date_field": "2026/10/02",
               "time_field": "16:08:32", "close": 4157.94,
               "verdict": "未开市（10/3-10/4 为周末，返回体日期字段 = 上一港股交易日 2026/10/02，§3.119b/§3.122b）"},
        "us": {"source": "akshare.stock_us_daily('IYH' / 'XLV')", "last_row_date": "2026-10-02",
               "IYH": 70.4, "XLV": 166.18,
               "verdict": "美股 10/2（周五）已收盘（成型于北京 10/3 04:00）→ 本档为**新增量**；10/3-10/4 为周末休市"},
        "rule": "三市场各自独立验证、不得互相外推（§3.119b）",
    },
    "base": {
        "file": "portfolio_close_20260930_fix.json", "base_total": base_total,
        "sum_tracks_mv": round(sum_mv, 2), "guard_dev": guard_dev,
        "guard_rule": "|Σ tracks.mv − base_total| < 1.5",
        "base_revision": {"prev_total": None, "delta": 0.0,
                          "reason": "本档为纯非交易日、无新净值；基准沿用 9/30 修正收盘"},
        "restore_rule_used": base.get("restore_rule_used"),
    },
    "tracks": tracks,
    "tracks_weight_after_discipline": {
        "恒生科技": round(29668.40 / base_total * 100, 2),
        "现金": round(31117.41 / base_total * 100, 2),
        "note": "① 9/29 触发第 1 次 0.5% 减仓（1,882.46 元）已按 9/30 净值结算；② 10/2 触发第 2 次 0.5% 减仓（1,904.44 元）判定成立、执行待 10/8；两项均为价值中性、P&L 口径不变",
    },
    "day_result": {
        "est_pnl": 0.0, "est_pct": 0.0,
        "attribution": "全部持仓标的不可定价（非市场持平）",
        "reasons": [
            "A股 10/1-10/7 全休 → 20 只 A股类场外基金不发布净值、A股指数无新收盘（末行仍 = 2026-09-30）",
            "场内 ETF / LOF（513050 / 513180 / 159920 / 159928 等，沪深交易所）无交易时段",
            "场外港股联接（000071 / 012348）在 A股休市期不发布净值（§3.112i）",
            "港股 10/3-10/4 为周末休市 → 无新港股价格",
            "美股 10/2 收盘虽已入库，其组合传导属 QDII 挂账项、不在本档基准内",
        ],
        "note": "「0 元」是账面冻结，不构成任何方向判断（§3.107 / §3.117a / §3.118b）",
    },
    "hk_exposure": {
        "total": 50024.26, "pct": 13.13,
        "segments": hk_dig["segments"] and {k: v["mv"] for k, v in hk_dig["segments"].items()},
        "southbound_gap_days": ["2026-10-02", "2026-10-05", "2026-10-06", "2026-10-07"],
        "rule_hint": "只报赛道层 8.29% 将低估 4.84pct（宽基层），§3.108 条款 23",
    },
    "med_exposure": {
        "mv": base["med_exposure"], "pct": base["med_pct"],
        "threshold_all_med_pct": base["threshold_all_med"],
        "threshold_a_sh_med_pct": base["threshold_a_sh_med"],
        "rule": "§3.98 方程解法 A(1+r)/(B+A(1+r)) = 40%",
    },
    "hk_pending_digest": {
        "refreshed": False,
        "reason": "10/3-10/4 为周末，港股无新交易日 → 港股腿待消化区间沿用 10/2 正式版",
        "window": hk_dig["window"], "priced_days": hk_dig["priced_days"], "total_days": hk_dig["total_days"],
        "total_low": HK_LOW, "mid_proxy_avg": HK_MID, "total_high": HK_HIGH,
        "track_only_low": hk_dig["track_only_low"], "track_only_high": hk_dig["track_only_high"],
        "broad_hk_low": hk_dig["broad_hk_low"], "broad_hk_high": hk_dig["broad_hk_high"],
        "rule": "§3.108 条款 23/24 + §3.116b：只给区间上下界、不得作方向判断；累积窗口 4 日仅走完 1 日",
    },
    "qdii_pending": {
        "refreshed": True,
        "reason": "本档新增 US 10/2 定价行（IYH 70.40 / 0.00%、XLV 166.18 / −0.01%）→ 复合收益不变（10/2 贡献 0.00%），挂账区间零变动",
        "component_a": qdii["component_a"],
        "component_b": {
            "desc": "US 9/30 −1.17% × 10/1 −1.62% × 10/2 0.00% 复合 −2.7710%（IYH 口径）",
            "trade_dates_covered": ["2026-09-30", "2026-10-01", "2026-10-02"],
            "notional": qdii["component_b"]["notional"],
            "low": qdii["component_b"]["low"], "mid": qdii["component_b"]["mid"], "high": qdii["component_b"]["high"],
            "coef_range": qdii["component_b"]["coef_range"],
        },
        "total_low": qdii_low, "total_mid": qdii_mid, "total_high": qdii_high,
        "unknown_sessions": ["2026-10-05", "2026-10-06", "2026-10-07"],
        "coef_note": "§3.118a：长假前后实测隐含系数 1.25~1.29，远超标定 0.72 / 常态实测 0.62 → 只给区间、禁止中枢点值",
        "us_leg_20261002": {"XLV": -0.01, "IYH": 0.0,
                            "note": "美股 10/2 三大指数齐涨（纳指 +1.19% / 标普500 +0.73% / 道指 +0.49%），XLV/IYH 双双跑输宽基"},
    },
    "sentiment": agg_out,
    "defense_lines": {
        "hstech_4250": {"close": 4157.94, "line": 4250, "dist_pct": -2.1661,
                        "state": "close_level_break_confirmed（10/2 收盘级）",
                        "action": "第 2 次 0.5% 纪律减仓 1,904.44 元，执行待 10/8"},
        "zz_consume_12100": {"last": 12295.9591, "dist_pct": 1.6195, "state": "restored_close_level",
                             "verify_at": "2026-10-08"},
        "a_med_reverse_1_5pct": {"proxy_pct": 2.8697, "state": "not_triggered", "verify_at": "2026-10-08"},
    },
    "risk_stats_source": "risk_stats_20261002_preopen.json（本档为纯非交易日，不重算链路/夏普/回撤，§3.122c）",
    "risk_stats_digest": {
        "chain_cum_pct": -3.29, "chain_days": 39,
        "w38_cum_pct": 1.37, "w39_cum_pct": -0.2, "w40_cum_pct": 0.86, "w40_days": 3,
        "sharpe": -1.91, "sharpe_n": 39, "daily_mean": -0.0831, "daily_sd": 0.7469,
        "max_dd_pct": -6.31, "max_dd_peak": "2026-08-10", "max_dd_trough": "2026-09-11",
        "last5_cum_pct": -0.71, "last10_cum_pct": 1.43, "rf_pct": 1.68,
    },
    "chain_0pct_row_inserted": False,
    "chain_note": "§3.108 条款 22：纯非交易日不产 portfolio_close_*/portfolio_pending_*，链式末行仍 = 2026-09-30",
    "next_increment": "2026-10-05（港股复市 + 美股 10/5 收盘）；2026-10-08（A股 + 港股通复市，全量）",
    "note": "本档另生成 W40 周报 reports/weekly/2026-W40-周报.md",
}

json.dump(ledger, open(f"{ROOT}/data/processed/history/portfolio_holiday_20261004.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)

print("=== 情绪聚合（双口径） ===")
print(f"名义净分 {agg_out['nominal_total']} | 暴露加权净分 {agg_out['weighted_total']} | "
      f"{tot_pos} 利多 / {tot_neu} 中性 / {tot_neg} 利空 | 均值强度 {mean_strength}")
print(f"强正 n={len(strong_pos)}（均值 {agg_out['strong_pos_mean']}）| 强负 n={len(strong_neg)}（均值 {agg_out['strong_neg_mean']}）")
for r in rows:
    print(f"  {r['track']:12s} n={r['n']} 名义 {r['nominal']:+7.1f} 权重 {r['weight']:5.2f}% 加权 {r['weighted']:+8.4f}")
print()
print("=== 假期台账 ===")
print(f"base_total={base_total} Σtracks.mv={sum_mv:.2f} guard_dev={guard_dev}")
print(f"HK  待消化 {HK_LOW} ~ {HK_HIGH}（中枢参考 {HK_MID}）")
print(f"QDII 挂账 {qdii_low} ~ {qdii_high}（中枢参考 {qdii_mid}）")
print(f"恒科纪律后权重 {ledger['tracks_weight_after_discipline']['恒生科技']}% / 现金 {ledger['tracks_weight_after_discipline']['现金']}%")
print("✅ 产物已写入 portfolio_holiday_20261004.json / sentiment_agg_20261004_close.json")
