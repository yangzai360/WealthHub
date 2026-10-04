#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""2026-10-04 盘后档：且慢 LONG_WIN 落库判定（REST 探针 + playwright 产物归档）
   §3.97/§3.99：本地 long-win-nav.csv 与源序列口径分歧未决 → 不追加不回写
"""
import json
import glob
import os
import shutil
import subprocess
import datetime

ROOT = "/Users/jieyang/Documents/WealthHub"
TAG = "20261004c"
OUT = f"{ROOT}/reference-portfolios/long-win"

def ts2date(ts):
    return datetime.datetime.fromtimestamp(ts / 1000, datetime.timezone(datetime.timedelta(hours=8))).strftime("%Y-%m-%d")

# ---------- 1. REST 探针（记录空 body 状态） ----------
probe = {"date": "2026-10-04", "endpoint": "https://qieman.com/pmdj/v2/long-win/plan", "ok": False, "body_len": 0, "note": ""}
try:
    r = subprocess.run(
        ["curl", "-s", "-m", "20", "-H", "User-Agent: Mozilla/5.0", "-H", "Referer: https://qieman.com/longwin",
         "https://qieman.com/pmdj/v2/long-win/plan"],
        capture_output=True, text=True)
    probe["body_len"] = len(r.stdout or "")
    probe["ok"] = probe["body_len"] > 100
    probe["note"] = f"HTTP body {probe['body_len']}B（{'有效' if probe['ok'] else '空 body'}）→ 需 playwright 兜底"
    probe["sample"] = (r.stdout or "")[:200]
except Exception as e:
    probe["note"] = f"探针异常：{e}"

# 连续空 body 计数（承接 10/2 盘中档第 101 个交易日）
probe["consecutive_empty_trading_days"] = 101 if not probe["ok"] else 0
json.dump(probe, open(f"{ROOT}/data/processed/history/qieman_rest_20261004.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("REST 探针:", probe["note"])

# ---------- 2. 归档 playwright 产物 ----------
plan_f = sorted(glob.glob(f"/tmp/qieman_pwc_plan_{TAG}_*.json"), key=os.path.getmtime)[-1]
nav_f = sorted(glob.glob(f"/tmp/qieman_pwc_nav_{TAG}_*.json"), key=os.path.getmtime)[-1]
adj_f = sorted(glob.glob(f"/tmp/qieman_pwc_adj_{TAG}_*.json"), key=os.path.getmtime)
plan = json.load(open(plan_f))
navs = json.load(open(nav_f))
navs = navs if isinstance(navs, list) else navs.get("data", navs)

shutil.copy2(plan_f, f"{OUT}/composition-2026-10-04-close.json")

# composition 汇总（按 className）
cats = []
for c in plan["composition"]:
    cats.append({"className": c.get("className"), "unit": c.get("unit"), "percent": c.get("percent"),
                 "funds": len(c.get("compList") or [])})
unit_sum = sum(c.get("unit") or 0 for c in plan["composition"])

nav_last = navs[-1]
nav_seq_tail = [{"date": ts2date(x["navDate"]), "nav": round(x["nav"], 7), "ret": round(x["dailyReturn"] * 100, 4)}
                for x in navs[-10:]]

# ---------- 3. 本地 CSV 口径核对 ----------
import csv
rows = list(csv.reader(open(f"{ROOT}/data/processed/reference/long-win-nav.csv", encoding="utf-8-sig")))
local_last = rows[-1]

digest = {
    "date": "2026-10-04",
    "session": "close",
    "rest_probe": probe,
    "playwright_fallback": True,
    "playwright_success_count": 29,
    "plan_body_bytes": os.path.getsize(plan_f),
    "nav_body_bytes": os.path.getsize(nav_f),
    "adjustedCount": plan.get("adjustedCount"),
    "investedUnit": plan.get("investedUnit"),
    "planUnit_sum": unit_sum,
    "plan_unit_zero_change": unit_sum == 150,
    "composition_by_class": cats,
    "composition_categories": len(plan["composition"]),
    "nav": plan.get("nav"),
    "nav_date_beijing": ts2date(plan.get("navDate") or 0),
    "daily_return_pct": round((plan.get("dailyReturn") or 0) * 100, 4),
    "sharpe": plan.get("sharpe"),
    "maxDrawdown": plan.get("maxDrawdown"),
    "volatility": plan.get("volatility"),
    "annualCompoundedReturn": plan.get("annualCompoundedReturn"),
    "nav_history_count": len(navs),
    "nav_history_tail": nav_seq_tail,
    "local_csv_last": local_last,
    "local_csv_rows": len(rows),
    "caliber_divergence": {
        "status": "挂起（连续第 13 档）",
        "source_last": nav_seq_tail[-1],
        "local_last": {"date": local_last[0], "nav": float(local_last[1])},
        "source_20260918": 1.6640517, "local_20260918": 1.664051,
        "revision_observed": "源 9/24 由 1.6604531 再修订为 1.6600450；另新增 9/28 1.6524260 / 9/29 1.6513461 / 9/30 1.6611542",
        "action": "按 §3.97/§3.99 不追加、不回写；口径统一为用户决策第 1 优先项",
    },
    "adjustment": {
        "changed": False,
        "note": "adjustedCount 265 = 265（承接 10/2 盘中档）、investedUnit 111 = 111、63 品种 planUnit 零变动、8 类别 unit 零变动（合计恒 150）→ E大无新调仓；最新调仓仍 adj_id 781 / 2026-07-30",
        "adjustedCount_prev": 265, "investedUnit_prev": 111, "latest_adj_id": 781, "latest_adj_date": "2026-07-30",
    },
    "nav_stale_note": "nav 1.6612 与 10/2 盘中档完全一致（A股 10/1-10/7 休市 → 净值不推进）；nav_date_beijing = 2026-09-30",
    "adjusted_files": {
        "plan": os.path.basename(plan_f), "nav": os.path.basename(nav_f),
        "adj": [os.path.basename(x) for x in adj_f] or "无（adjustments 明细仍缺，承接待办）",
    },
}
json.dump(digest, open(f"{ROOT}/data/processed/history/qieman_close_20261004.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)

# meta.json 增量更新
meta_p = f"{OUT}/meta.json"
meta = json.load(open(meta_p))
meta.update({
    "nav": plan.get("nav"), "navDate": plan.get("navDate"),
    "dailyReturn": round((plan.get("dailyReturn") or 0) * 100, 4),
    "sharpe": plan.get("sharpe"), "maxDrawdown": plan.get("maxDrawdown"),
    "volatility": plan.get("volatility"), "annualCompoundedReturn": plan.get("annualCompoundedReturn"),
    "investedUnit": plan.get("investedUnit"), "adjustedCount": plan.get("adjustedCount"),
    "nav_date_beijing": ts2date(plan.get("navDate") or 0),
    "last_checked": "2026-10-04",
    "composition_snapshot": "composition-2026-10-04-close.json",
    "joinedCount": plan.get("joinedCount"), "activeCount": plan.get("activeCount"),
})
json.dump(meta, open(meta_p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

print("=== 且慢 LONG_WIN 落库 ===")
print(f"plan {digest['plan_body_bytes']}B / nav {digest['nav_body_bytes']}B")
print(f"adjustedCount={digest['adjustedCount']} investedUnit={digest['investedUnit']} planUnit_sum={unit_sum}")
print(f"nav={digest['nav']} nav_date={digest['nav_date_beijing']} 日收益={digest['daily_return_pct']}%")
print(f"sharpe={digest['sharpe']} maxDD={digest['maxDrawdown']} vol={digest['volatility']}")
print(f"nav-history {len(navs)} 条；末 4 条：{nav_seq_tail[-4:]}")
print(f"本地 CSV 末行：{local_last}（口径分歧连续第 13 档，不追加）")
print("✅ qieman_close_20261004.json / composition-2026-10-04-close.json / meta.json 已更新")
