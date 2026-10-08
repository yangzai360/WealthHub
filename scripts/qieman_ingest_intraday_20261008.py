# -*- coding: utf-8 -*-
"""2026-10-08 **盘中档（13:45）**：且慢 LONG_WIN 落库判定（REST 探针 + playwright 产物归档）

⚠️ 与盘前档 `qieman_ingest_20261008.py` 的差异（§3.121c 四类字面量核对）：
   · 读写路径 = *20261008*（REST 探针产物沿用盘前档，本档不覆盖）
   · 输出档型名 = qieman_20261008_intraday.json / composition-2026-10-08.json
   · session = "intraday"；session_type = "normal_trading_day_intraday"
   · 基线 = composition-2026-10-07-close.json（上一收盘基线）
   · 计数：consecutive_empty_trading_days = 105（10/8 为 A股 交易日，本档同日不重复推进）
           playwright_success_count = 36（盘前档 35 → 本档 +1）
"""
import json, glob, os, csv, datetime, shutil

ROOT = "/Users/jieyang/Documents/WealthHub"
TAG = "20261008p"
OUT = f"{ROOT}/reference-portfolios/long-win"
TODAY = "2026-10-08"


def ts2date(ts):
    return datetime.datetime.fromtimestamp(ts / 1000, datetime.timezone(datetime.timedelta(hours=8))).strftime("%Y-%m-%d")


# ---------- 1. REST 探针（沿用盘前档产物，不改写） ----------
p_rest = f"{ROOT}/data/processed/history/qieman_rest_20261008.json"
probe = json.load(open(p_rest, encoding="utf-8"))
probe["session_ref"] = "preopen-0800（沿用；本档 13:45 未复测）"
print("REST 探针（沿用盘前档）:", {k: v for k, v in probe.items() if isinstance(v, dict)})

# ---------- 2. 归档 playwright 产物 ----------
plan_f = sorted(glob.glob(f"/tmp/qieman_pwc_plan_{TAG}_*.json"), key=os.path.getmtime)[-1]
nav_f = sorted(glob.glob(f"/tmp/qieman_pwc_nav_{TAG}_*.json"), key=os.path.getmtime)[-1]
adj_f = sorted(glob.glob(f"/tmp/qieman_pwc_adj_{TAG}_*.json"), key=os.path.getmtime)
for p in (plan_f, nav_f):
    assert os.path.exists(p), f"⚠️ 路径不存在: {p}"
plan = json.load(open(plan_f))
navs = json.load(open(nav_f))
navs = navs if isinstance(navs, list) else navs.get("data", navs)

shutil.copy2(plan_f, f"{OUT}/composition-{TODAY}.json")


# ---------- 3. composition 逐品种 planUnit 差分（§3.93 两层嵌套） ----------
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
BASE_FILES = [
    f"{OUT}/composition-2026-10-07-close.json",
    f"{OUT}/composition-2026-10-08-preopen.json",
    f"{OUT}/composition-2026-10-06-close.json",
]
print("基线候选存在性:", [(os.path.basename(b), os.path.exists(b)) for b in BASE_FILES])
existing = [b for b in BASE_FILES if os.path.exists(b)]
assert existing, "⚠️ 候选基线文件均不存在 → 终止"
base_file = existing[0]
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
print(f"planUnit 合计 = {unit_sum}（逐品种）；类别 unit 合计 = {cat_unit_sum}")
print(f"品种数两口径：去重代码 = {len(cur_units)} / 成分条数 = {comp_rows}（§3.133d）")
print(f"逐品种差分：{diffs if diffs else '零变动'}")

cats = [{"className": c.get("className"), "unit": c.get("unit"), "percent": c.get("percent"),
         "funds": len(c.get("compList") or [])} for c in plan["composition"]]

nav_last = navs[-1]
nav_seq_tail = [{"date": ts2date(x["navDate"]), "nav": round(x["nav"], 7), "ret": round(x["dailyReturn"] * 100, 4)}
                for x in navs[-10:]]

rows = list(csv.reader(open(f"{ROOT}/data/processed/reference/long-win-nav.csv", encoding="utf-8-sig")))
local_last = rows[-1]

ADJ_PREV, INV_PREV = 265, 111
changed = bool(diffs) or plan.get("adjustedCount") != ADJ_PREV or plan.get("investedUnit") != INV_PREV

digest = {
    "date": TODAY,
    "session": "intraday",
    "session_type": "normal_trading_day_intraday",
    "session_type_note": "正常交易日盘中档（A股 10/8 长假后复市首日 + 港股 10/8 正常交易日；13:45 双方均开市）",
    "rest_probe": probe,
    "playwright_fallback": True,
    "playwright_success_count": 36,
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
        "status": "挂起（连续第 19 档）",
        "source_last": nav_seq_tail[-1],
        "local_last": {"date": local_last[0], "nav": float(local_last[1])},
        "action": "按 §3.97/§3.99 不追加、不回写；口径统一为用户决策第 1 优先项",
    },
    "adjustment": {
        "changed": changed,
        "note": (f"adjustedCount {plan.get('adjustedCount')} = {ADJ_PREV}、investedUnit {plan.get('investedUnit')} = {INV_PREV}、"
                 f"逐品种 planUnit 差分零变动（{len(cur_units)} 个去重代码合计恒 {unit_sum}）、{len(plan['composition'])} 类别 unit 零变动（合计恒 {cat_unit_sum}）"
                 f" → **E大无新调仓**；最新调仓仍 adj_id 781 / 2026-07-30") if not changed else
                f"⚠️ 检测到调仓：差分 {diffs}；建议用户在且慢 App 核对",
        "adjustedCount_prev": ADJ_PREV, "investedUnit_prev": INV_PREV,
        "latest_adj_id": 781, "latest_adj_date": "2026-07-30",
    },
    "nav_stale_note": (f"nav {plan.get('nav')} / nav_date_beijing = {ts2date(plan.get('navDate') or 0)}；"
                       f"⚠️ 10/8 为 A股 复市首日，当日净值收盘后（20:00 前后）发布 → 13:45 档不可得"),
    "adjusted_files": {
        "plan": os.path.basename(plan_f), "nav": os.path.basename(nav_f),
        "adj": [os.path.basename(x) for x in adj_f] or "无（adjustments 明细仍缺，承接待办）",
    },
}
json.dump(digest, open(f"{ROOT}/data/processed/history/qieman_20261008_intraday.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)

meta_p = f"{OUT}/meta.json"
meta = json.load(open(meta_p))
meta.update({
    "nav": plan.get("nav"), "navDate": plan.get("navDate"),
    "dailyReturn": round((plan.get("dailyReturn") or 0) * 100, 4),
    "sharpe": plan.get("sharpe"), "maxDrawdown": plan.get("maxDrawdown"),
    "volatility": plan.get("volatility"), "annualCompoundedReturn": plan.get("annualCompoundedReturn"),
    "investedUnit": plan.get("investedUnit"), "adjustedCount": plan.get("adjustedCount"),
    "nav_date_beijing": ts2date(plan.get("navDate") or 0),
    "last_checked": TODAY, "composition_snapshot": f"composition-{TODAY}-intraday.json",
    "joinedCount": plan.get("joinedCount"), "activeCount": plan.get("activeCount"),
    "date": TODAY, "navDate_bj": ts2date(plan.get("navDate") or 0),
    "latest_adj_id": 781, "latest_adj_date": "2026-07-30",
})
json.dump(meta, open(meta_p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

print("=== 且慢 LONG_WIN 落库（盘中档） ===")
print(f"plan {digest['plan_body_bytes']}B / nav {digest['nav_body_bytes']}B")
print(f"adjustedCount={digest['adjustedCount']} investedUnit={digest['investedUnit']} planUnit_sum={unit_sum}")
print(f"nav={digest['nav']} nav_date={digest['nav_date_beijing']} 日收益={digest['daily_return_pct']}%")
print(f"nav-history {len(navs)} 条；末 4 条：{nav_seq_tail[-4:]}")
print(f"本地 CSV 末行：{local_last}（口径分歧连续第 19 档，不追加）")
print(f"🟢 E大调仓判定：{'⚠️ 有新调仓' if changed else '无新调仓（最新仍 adj_id 781 / 2026-07-30）'}")
print("✅ qieman_20261008_intraday.json / composition-2026-10-08.json / meta.json 已更新")
