#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""2026-W40 周报（9/28-10/4）统计产物
产出 data/processed/history/weekly_stats_20261004.json
守卫：Σ 赛道周盈亏 == 首尾市值差；W40 cum == 几何链式结果
"""
import json

ROOT = "/Users/jieyang/Documents/WealthHub"
H = f"{ROOT}/data/processed/history"

closes = {}
for d in ["20260928", "20260929", "20260930"]:
    closes[d] = json.load(open(f"{H}/portfolio_close_{d}_fix.json"))

base = 377630.12                 # 9/24 修正收盘（W39 末有效估值日）
end = closes["20260930"]["total_mv"]
assert abs(closes["20260928"]["base_total"] - base) < 0.02

days = ["2026-09-28", "2026-09-29", "2026-09-30"]
daily_pct = []
track_daily = {}
for d, ds in zip(days, ["20260928", "20260929", "20260930"]):
    c = closes[ds]
    daily_pct.append([d, round(c["est_total_pct_raw"], 4)])
    for t, v in c["tracks"].items():
        track_daily.setdefault(t, {})[d] = round(v["pnl"], 2)

track_week = {t: round(sum(v.values()), 2) for t, v in track_daily.items()}
sum_week = round(sum(track_week.values()), 2)
first_last = round(end - base, 2)
assert abs(sum_week - first_last) < 1.5, f"守卫失败: Σ赛道 {sum_week} vs 首尾 {first_last}"

# 几何链式
nav = 1.0
for _, p in daily_pct:
    nav *= (1 + p / 100)
cum = round((nav - 1) * 100, 4)
assert abs(cum - (end / base - 1) * 100) < 0.01, f"链式 {cum} vs 直算 {(end/base-1)*100}"

end_weights = {t: v["pct_of_total"] for t, v in closes["20260930"]["tracks"].items()}
risk = json.load(open(f"{H}/risk_stats_20261002_preopen.json"))
hk = json.load(open(f"{H}/portfolio_pending_20261002.json"))["hk_pending_digest"]
hol = json.load(open(f"{H}/portfolio_holiday_20261004.json"))

out = {
    "date": "2026-10-04",
    "week": "2026-W40",
    "week_range": "2026-09-28 ~ 2026-10-04",
    "base_total": base,
    "base_date": "2026-09-24",
    "end_total": end,
    "end_date": "2026-09-30",
    "w40": {"cum_pct": cum, "days": 3, "daily": daily_pct, "pnl": first_last,
            "note": "10/1-10/4 为国庆长假 → 无定价，不计入；W40 仅 3 个定价日"},
    "track_week_pnl": track_week,
    "track_week_daily": track_daily,
    "track_end_weights": end_weights,
    "chain": {
        "chain_cum_pct": risk["chain_cum_pct"], "chain_days": risk["chain_days"],
        "w38_cum_pct": risk["w38_cum_pct"], "w39_cum_pct": risk["w39_cum_pct"],
        "sharpe": risk["sharpe"], "sharpe_n": risk["sharpe_n"],
        "daily_mean": risk["daily_mean"], "daily_sd": risk["daily_sd"],
        "max_dd_pct": risk["max_dd_pct"], "max_dd_peak": risk["max_dd_peak"],
        "max_dd_trough": risk["max_dd_trough"], "last5_cum_pct": risk["last5_cum_pct"],
        "last10_cum_pct": risk["last10_cum_pct"], "rf_pct": risk["rf_pct"],
        "chain_0pct_row_inserted": False,
        "note": "本档为纯非交易日，不重算链路/夏普/回撤；末行仍 = 2026-09-30，10/8 盘后档统一重算",
    },
    "exposure": {
        "med_mv": hol["med_exposure"]["mv"], "med_pct": hol["med_exposure"]["pct"],
        "med_threshold_all_pct": hol["med_exposure"]["threshold_all_med_pct"],
        "med_threshold_a_sh_pct": hol["med_exposure"]["threshold_a_sh_med_pct"],
        "hk_total": hol["hk_exposure"]["total"], "hk_pct": hol["hk_exposure"]["pct"],
        "hk_segments": hol["hk_exposure"]["segments"],
        "hk_rule": "只报赛道层 8.29% 将低估 4.84pct（宽基恒生系），§3.108 条款 23",
    },
    "pending_next": {
        "hk_leg": {"window": hk["window"], "priced_days": hk["priced_days"], "total_days": hk["total_days"],
                   "low": hk["total_low"], "mid": hk["mid_proxy_avg"], "high": hk["total_high"],
                   "segments": {k: v for k, v in hk["segments"].items()},
                   "rule": "只给区间上下界、不得作方向判断（§3.108 条款 24）"},
        "qdii_leg": {"low": hol["qdii_pending"]["total_low"], "mid": hol["qdii_pending"]["total_mid"],
                     "high": hol["qdii_pending"]["total_high"],
                     "known_sessions": ["2026-09-30", "2026-10-01", "2026-10-02"],
                     "unknown_sessions": hol["qdii_pending"]["unknown_sessions"],
                     "coef_note": hol["qdii_pending"]["coef_note"]},
        "a_share_leg": {"priced": False, "reason": "A股 10/1-10/7 休市", "next": "2026-10-08",
                        "catalysts": ["央行 12,000 亿元买断式逆回购（10/8 投放）", "9 月官方制造业 PMI 50.1%",
                                      "卖方 10 月「科技反弹 + 高股息底仓」杠铃共识（与组合结构错配）"]},
        "discipline_pending": {"track": "恒生科技", "pct": 0.5, "amount": 1904.44,
                               "judged_at": "2026-10-02 收盘级", "execute_at": "2026-10-08",
                               "targets": ["012348", "513180"], "note": "标的不落中概（513050 / 164906）"},
    },
    "note": "W40 = 9/28-10/4；组合收益为估算口径（链式法）；赛道周盈亏求和与首尾市值差已通过 <1.5 元守卫",
}
json.dump(out, open(f"{H}/weekly_stats_20261004.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

print(f"base {base} → end {end}  首尾差 {first_last} 元")
print(f"W40 链式 {cum}%  |  Σ赛道周盈亏 {sum_week} 元（守卫通过）")
for t, v in sorted(track_week.items(), key=lambda x: -x[1]):
    print(f"  {t:12s} {v:+9.2f} 元  权重 {end_weights[t]:5.2f}%")
print("daily:", daily_pct)
print("✅ weekly_stats_20261004.json 已写入")
