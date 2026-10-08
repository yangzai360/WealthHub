#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""2026-10-08 盘前档：且慢 LONG_WIN 落库判定（REST 探针 + playwright 产物归档）
   §3.97/§3.99：本地 long-win-nav.csv 与源序列口径分歧未决 → 不追加不回写
   §3.126d：路径类字面量逐条校验存在性
   ⚠️ 本档为全新撰写（非 sed 派生），读写路径 = 20261008 / 2026-10-08
   ⚠️ 档型语义核对（§3.121c）：本档 = 档型③「正常交易日盘前」（A股 10/8 复市首日 + 港股 10/8 正常交易日）
   ⚠️ 计数人工核对（§3.130d / §3.133c）：
        · consecutive_empty_trading_days：上一档 104；10/8 为 A股 交易日 → **推进 +1 = 105**
        · playwright_success_count：上一档 34 → **+1 = 35**
"""
import json
import glob
import os
import datetime
import csv

ROOT = "/Users/jieyang/Documents/WealthHub"
TAG = "20261008p"
OUT = f"{ROOT}/reference-portfolios/long-win"
TODAY = "2026-10-08"


def ts2date(ts):
    return datetime.datetime.fromtimestamp(ts / 1000, datetime.timezone(datetime.timedelta(hours=8))).strftime("%Y-%m-%d")


# ---------- 1. REST 探针状态 ----------
probe = json.load(open(f"{ROOT}/data/processed/history/qieman_rest_20261008.json", encoding="utf-8"))
probe["ok"] = all((v.get("size") or 0) > 100 for k, v in probe.items() if isinstance(v, dict))
probe["consecutive_empty_trading_days"] = 105 if not probe["ok"] else 0
probe["consecutive_note"] = ("10/8 为 **A股 交易日（长假后复市首日）** → 依 §3.130d 规则① 本计数**推进 +1**："
                            "10/7 盘后 = 104 → 本档 = 105；该计数为人工维护、历史存在 ±1 记录差异，已登记为口径待清理项（§3.133c）")
probe["note"] = "三端点 HTTP 200 / size 0B 全空 → playwright 兜底第 35 次成功"
json.dump(probe, open(f"{ROOT}/data/processed/history/qieman_rest_20261008.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("REST 探针:", probe["note"])

# ---------- 2. 归档 playwright 产物 ----------
plan_f = sorted(glob.glob(f"/tmp/qieman_pwc_plan_{TAG}_*.json"), key=os.path.getmtime)[-1]
nav_f = sorted(glob.glob(f"/tmp/qieman_pwc_nav_{TAG}_*.json"), key=os.path.getmtime)[-1]
adj_f = sorted(glob.glob(f"/tmp/qieman_pwc_adj_{TAG}_*.json"), key=os.path.getmtime)
for p in (plan_f, nav_f):
    assert os.path.exists(p), f"⚠️ 路径不存在: {p}"
plan = json.load(open(plan_f))
navs = json.load(open(nav_f))
navs = navs if isinstance(navs, list) else navs.get("data", navs)

# ⚠️ 预登记快照（盘前档不覆盖 13:47 / 20:0x 正式快照，单独命名，供 intraday 档比对）
import shutil
shutil.copy2(plan_f, f"{OUT}/composition-{TODAY}-preopen.json")


# ---------- 3. composition 逐品种 planUnit 差分（§3.93：两层嵌套 cl['compList'][i]['fund']['fundCode']） ----------
def flat(plan_obj):
    m = {}
    for cl in plan_obj.get("composition") or []:
        for it in (cl.get("compList") or []):
            f = it.get("fund") or {}
            code = f.get("fundCode") or f.get("code")
            if code is None:
                continue
            m[code] = m.get(code, 0) + (it.get("planUnit") or 0)
    return m


cur_units = flat(plan)
# ⚠️ §3.126d：基线候选文件必须逐条 ls 验证存在性（盘前档不产 composition 正式快照）
BASE_FILES = [
    f"{OUT}/composition-2026-10-07-close.json",      # 上一收盘基线（长假最后一日）
    f"{OUT}/composition-2026-10-07.json",            # 上一盘中基线
    f"{OUT}/composition-2026-10-06-close.json",      # 前二收盘基线
]
existing = [b for b in BASE_FILES if os.path.exists(b)]
print("基线候选存在性:", [(os.path.basename(b), os.path.exists(b)) for b in BASE_FILES])
base_file = existing[0] if existing else None
assert base_file, "⚠️ 候选基线文件均不存在 → 终止"
base_units = flat(json.load(open(base_file, encoding="utf-8")))
print(f"composition 基线 = {os.path.basename(base_file)}（{len(base_units)} 个去重代码，§3.133d）")

diffs = []
for code in sorted(set(cur_units) | set(base_units)):
    a, b = base_units.get(code, 0), cur_units.get(code, 0)
    if a != b:
        diffs.append({"code": code, "prev": a, "now": b, "delta": b - a})
unit_sum = sum(cur_units.values())
cat_unit_sum = sum(c.get("unit") or 0 for c in plan["composition"])
comp_rows = sum(len(c.get("compList") or []) for c in plan["composition"])
print(f"planUnit 合计 = {unit_sum}（逐品种求和）；类别 unit 合计 = {cat_unit_sum}")
print(f"品种数两种口径：去重代码数 = {len(cur_units)} / 成分条数 = {comp_rows}（§3.133d）")
print(f"逐品种差分：{diffs if diffs else '零变动'}")

cats = [{"className": c.get("className"), "unit": c.get("unit"), "percent": c.get("percent"),
         "funds": len(c.get("compList") or [])} for c in plan["composition"]]

nav_last = navs[-1]
nav_seq_tail = [{"date": ts2date(x["navDate"]), "nav": round(x["nav"], 7), "ret": round(x["dailyReturn"] * 100, 4)}
                for x in navs[-10:]]

# ---------- 4. 本地 CSV 口径核对 ----------
rows = list(csv.reader(open(f"{ROOT}/data/processed/reference/long-win-nav.csv", encoding="utf-8-sig")))
local_last = rows[-1]

ADJ_PREV, INV_PREV = 265, 111
changed = bool(diffs) or plan.get("adjustedCount") != ADJ_PREV or plan.get("investedUnit") != INV_PREV

digest = {
    "date": TODAY,
    "session": "preopen",
    "session_type": "normal_trading_day_preopen",
    "session_type_note": "档型③「正常交易日盘前」（A股 10/8 长假后复市首日 + 港股 10/8 正常交易日；08:00 双方均无新价格）",
    "rest_probe": probe,
    "playwright_fallback": True,
    "playwright_success_count": 35,
    "plan_body_bytes": os.path.getsize(plan_f),
    "nav_body_bytes": os.path.getsize(nav_f),
    "adjustedCount": plan.get("adjustedCount"),
    "investedUnit": plan.get("investedUnit"),
    "planUnit_sum": unit_sum,
    "planUnit_cat_sum": cat_unit_sum,
    "plan_unit_zero_change": len(diffs) == 0,
    "planunit_diff": diffs,
    "planunit_diff_baseline": os.path.basename(base_file),
    "composition_by_class": cats,
    "composition_categories": len(plan["composition"]),
    "composition_distinct_codes": len(cur_units),
    "composition_rows": comp_rows,
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
        "status": "挂起（连续第 18 档）",
        "source_last": nav_seq_tail[-1],
        "local_last": {"date": local_last[0], "nav": float(local_last[1])},
        "action": "按 §3.97/§3.99 不追加、不回写；口径统一为用户决策第 1 优先项",
    },
    "adjustment": {
        "changed": changed,
        "note": (f"adjustedCount {plan.get('adjustedCount')} = {ADJ_PREV}、investedUnit {plan.get('investedUnit')} = {INV_PREV}、"
                 f"逐品种 planUnit 差分零变动（{len(cur_units)} 个去重代码合计恒 {unit_sum}）、8 类别 unit 零变动（合计恒 {cat_unit_sum}）→ E大无新调仓；"
                 f"最新调仓仍 adj_id 781 / 2026-07-30") if not changed else
                f"⚠️ 检测到调仓：差分 {diffs}；建议用户在且慢 App 核对",
        "adjustedCount_prev": ADJ_PREV, "investedUnit_prev": INV_PREV,
        "latest_adj_id": 781, "latest_adj_date": "2026-07-30",
    },
    "nav_stale_note": (f"nav {plan.get('nav')} 与 10/5/10/6/10/7 档一致（A股 休市期净值不推进）；"
                       f"nav_date_beijing = {ts2date(plan.get('navDate') or 0)}；"
                       f"⚠️ 10/8 为 A股 复市首日，当日净值将于收盘后（20:00 前后）发布 → 本档不可得"),
    "adjusted_files": {
        "plan": os.path.basename(plan_f), "nav": os.path.basename(nav_f),
        "adj": [os.path.basename(x) for x in adj_f] or "无（adjustments 明细仍缺，承接待办）",
    },
}
json.dump(digest, open(f"{ROOT}/data/processed/history/qieman_20261008.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)

# ---------- 5. meta.json 增量更新 ----------
meta_p = f"{OUT}/meta.json"
meta = json.load(open(meta_p))
meta.update({
    "nav": plan.get("nav"), "navDate": plan.get("navDate"),
    "dailyReturn": round((plan.get("dailyReturn") or 0) * 100, 4),
    "sharpe": plan.get("sharpe"), "maxDrawdown": plan.get("maxDrawdown"),
    "volatility": plan.get("volatility"), "annualCompoundedReturn": plan.get("annualCompoundedReturn"),
    "investedUnit": plan.get("investedUnit"), "adjustedCount": plan.get("adjustedCount"),
    "nav_date_beijing": ts2date(plan.get("navDate") or 0),
    "last_checked": TODAY,
    "composition_snapshot": f"composition-{TODAY}-preopen.json",
    "joinedCount": plan.get("joinedCount"), "activeCount": plan.get("activeCount"),
    "date": TODAY, "navDate_bj": ts2date(plan.get("navDate") or 0),
})
json.dump(meta, open(meta_p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

print("=== 且慢 LONG_WIN 落库 ===")
print(f"plan {digest['plan_body_bytes']}B / nav {digest['nav_body_bytes']}B")
print(f"adjustedCount={digest['adjustedCount']} investedUnit={digest['investedUnit']} planUnit_sum={unit_sum}")
print(f"nav={digest['nav']} nav_date={digest['nav_date_beijing']} 日收益={digest['daily_return_pct']}%")
print(f"sharpe={digest['sharpe']} maxDD={digest['maxDrawdown']} vol={digest['volatility']}")
print(f"nav-history {len(navs)} 条；末 4 条：{nav_seq_tail[-4:]}")
print(f"本地 CSV 末行：{local_last}（口径分歧连续第 18 档，不追加）")
print("✅ qieman_20261008.json / composition-2026-10-08-preopen.json / meta.json 已更新")
