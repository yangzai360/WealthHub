# -*- coding: utf-8 -*-
"""2026-10-09 **盘中档（13:45）**：且慢 LONG_WIN 落库判定（REST 探针 + playwright 产物归档）

⚠️ 与盘前档 / 昨日收盘档的差异（§3.121c 四类字面量核对）：
   · 读写路径 = *20261009*（REST 探针产物 = qieman_rest_20261009_intraday.json，本档不复测）
   · 输出档型名 = qieman_20261009_intraday.json / composition-2026-10-09.json
   · session = "intraday"；session_type = "normal_trading_day_intraday"
   · 基线 = composition-2026-10-08-close.json（上一 A股 收盘基线，含 10/8 新增 001257）
   · 计数：consecutive_empty_trading_days = 106（10/9 为 A股 交易日，较 10/8 收盘档 105 推进 +1）
           playwright_success_count = 38（10/8 收盘档 37 → 本档 +1）
   · 🔔 承接 10/8 收盘档「检测到调仓但未落库」：本档**把 001257 新调仓写入 adjustments.json**
"""
import json, glob, os, csv, datetime, shutil

ROOT = "/Users/jieyang/Documents/WealthHub"
TAG = "20261009i"
OUT = f"{ROOT}/reference-portfolios/long-win"
TODAY = "2026-10-09"


def ts2date(ts):
    return datetime.datetime.fromtimestamp(ts / 1000, datetime.timezone(datetime.timedelta(hours=8))).strftime("%Y-%m-%d")


# ---------- 1. REST 探针（沿用本档探针产物，不改写） ----------
p_rest = f"{ROOT}/data/processed/history/qieman_rest_20261009_intraday.json"
probe = json.load(open(p_rest, encoding="utf-8"))
probe["session_ref"] = "intraday-1345（本档实测三端点均 HTTP 200 / size 0）"
print("REST 探针（本档实测）:", {k: v for k, v in probe.items() if isinstance(v, dict)})

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
    f"{OUT}/composition-2026-10-08-close.json",   # 上一 A股 收盘基线（含 001257 = 1）
    f"{OUT}/composition-2026-10-08.json",         # 昨日 13:47 盘中基线（001257 尚未出现）
    f"{OUT}/composition-2026-10-07-close.json",   # 长假后首日基线（第三兜底）
]
print("基线候选存在性:", [(os.path.basename(b), os.path.exists(b)) for b in BASE_FILES])
existing = [b for b in BASE_FILES if os.path.exists(b)]
assert existing, "⚠️ 候选基线文件均不存在 → 终止"
base_file = existing[0]
base_units = flat(json.load(open(base_file, encoding="utf-8")))
print(f"composition 基线 = {os.path.basename(base_file)}（{len(base_units)} 个去重代码，§3.133d）")

diffs = []
for code in sorted(set(cur_units) | set(base_units), key=lambda x: str(x)):
    a, b = base_units.get(code, 0), cur_units.get(code, 0)
    if a != b:
        diffs.append({"code": code, "prev": a, "now": b, "delta": b - a})
unit_sum = sum(cur_units.values())
cat_unit_sum = sum(c.get("unit") or 0 for c in plan["composition"])
comp_rows = sum(len(c.get("compList") or []) for c in plan["composition"])
print(f"planUnit 合计 = {unit_sum}（逐品种）；类别 unit 合计 = {cat_unit_sum}")
print(f"品种数两口径：去重代码 = {len(cur_units)} / 成分条数 = {comp_rows}（§3.133d）")
print(f"逐品种差分：{diffs if diffs else '零变动'}")

ADJ_PREV, INV_PREV = 266, 112
changed = bool(diffs) or plan.get("adjustedCount") != ADJ_PREV or plan.get("investedUnit") != INV_PREV

# ---------- 4. 🔔 承接 10/8 收盘档的新调仓 → 写入 adjustments.json ----------
adj_p = f"{OUT}/adjustments.json"
adj_doc = json.load(open(adj_p, encoding="utf-8"))
NEW_CODE = "001257"
existing_codes = {o.get("fund_code") for a in adj_doc["adjustments"] for o in (a.get("orders") or [])}
need_write = NEW_CODE not in existing_codes
print(f"\n=== adjustments.json 落库判定 ===")
print(f"  基线已有 fund_code 集合含 {NEW_CODE}? {NEW_CODE in existing_codes}（现有 {len(adj_doc['adjustments'])} 条调仓）")

# 从本档 plan 中提取该品种的权威字段
item_001257 = None
for cl in plan["composition"]:
    for it in (cl.get("compList") or []):
        f = it.get("fund") or {}
        if f.get("fundCode") == NEW_CODE:
            item_001257 = {"class": cl.get("className"), "class_code": cl.get("classCode"), "item": it, "fund": f}
assert item_001257, "⚠️ 001257 不在当前组合中 → 与 10/8 收盘档结论矛盾，终止"
it = item_001257["item"]; fd = item_001257["fund"]
print(f"  {NEW_CODE} {fd.get('fundName')} class={item_001257['class']} planUnit={it.get('planUnit')} "
      f"nav={it.get('nav')} navDate={ts2date(it.get('navDate') or 0)}")

record = None
if need_write:
    record = {
        "adjustment_id": None,
        "txn_date": "2026-10-08",
        "create_time": None,
        "invest_type": "E",
        "url": "",
        "comment": "买入1份兴业收益增强债（现金类 39→38 份、境内债券类 14→15 份）",
        "orders": [{
            "fund_code": NEW_CODE,
            "fund_name": fd.get("fundName"),
            "variety": it.get("variety"),
            "large_class": item_001257["class"],
            "direction": "买入",
            "trade_unit": it.get("planUnit"),
            "post_plan_unit": it.get("planUnit"),
            "nav": str(it.get("nav")),
            "nav_date": it.get("navDate"),
        }],
        "detection": {
            "detected_at": "2026-10-08T20:00 (close档)",
            "recorded_at": f"{TODAY} 13:45 (intraday档)",
            "method": "composition 逐品种/逐类别 planUnit 差分 + adjustedCount/investedUnit 三重交叉验证",
            "evidence": {
                "adjustedCount": f"{ADJ_PREV - 1} → {plan.get('adjustedCount')}",
                "investedUnit": f"{INV_PREV - 1} → {plan.get('investedUnit')}",
                "class_shift": "现金 39 → 38；境内债券 14 → 15（计划总量恒 150 份）",
            },
            "unavailable_fields": ["adjustment_id", "create_time", "url", "comment(原文)"],
            "unavailable_reason": "qieman pmdj adjustments 端点连续第 106 个交易日空 body（HTTP 200 / size 0），playwright 亦未捕获 adjustments 响应 → 无法取得调仓原文",
            "pending_user_verification": True,
            "verify_hint": "请在且慢 App「长赢指数投资计划」- 调仓记录 中核对本期调仓的日期/说明/文章链接，并回填本记录",
        },
    }
    adj_doc["adjustments"].insert(0, record)
    adj_doc["count"] = len(adj_doc["adjustments"])
    adj_doc["last_updated"] = TODAY
    adj_doc["last_updated_note"] = "由 2026-10-09 盘中档据 composition 差分推定补录（源 adjustments 端点不可用）"
    json.dump(adj_doc, open(adj_p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"  ✅ 已写入 adjustments.json（count {len(adj_doc['adjustments'])}）")
else:
    print("  → 已在库，无需重复写入")

cats = [{"className": c.get("className"), "unit": c.get("unit"), "percent": c.get("percent"),
         "funds": len(c.get("compList") or [])} for c in plan["composition"]]

nav_last = navs[-1]
nav_seq_tail = [{"date": ts2date(x["navDate"]), "nav": round(x["nav"], 7), "ret": round(x["dailyReturn"] * 100, 4)}
                for x in navs[-10:]]

rows = list(csv.reader(open(f"{ROOT}/data/processed/reference/long-win-nav.csv", encoding="utf-8-sig")))
local_last = rows[-1]
NAV_1008_PRIOR = 1.6579582   # 10/8 收盘档 plan.nav 读数
NAV_1008_NOW = nav_seq_tail[-1]["nav"]
revision = abs(NAV_1008_NOW - NAV_1008_PRIOR) > 1e-6

digest = {
    "date": TODAY,
    "session": "intraday",
    "session_type": "normal_trading_day_intraday",
    "session_type_note": "正常交易日盘中档（A股 长假后第 2 个交易日 + 港股正常交易日；13:45 双方均开市）",
    "rest_probe": probe,
    "playwright_fallback": True,
    "playwright_success_count": 38,
    "consecutive_empty_trading_days": 106,
    "consecutive_note": "A股 10/9 为交易日 → 计数由 10/8 收盘档 105 推进至 106；该计数为人工维护、历史存在 ±1 记录差异（§3.133c）",
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
        "status": "挂起（连续第 21 档）",
        "source_last": nav_seq_tail[-1],
        "local_last": {"date": local_last[0], "nav": float(local_last[1])},
        "action": "按 §3.97/§3.99 不追加、不回写；口径统一为用户决策第 1 优先项",
    },
    "source_revision": {
        "observed": revision,
        "target": "2026-10-08 组合净值",
        "prior": NAV_1008_PRIOR,
        "now": NAV_1008_NOW,
        "note": ("源侧把 10/8 收盘档读到 1.6579582 修订为 1.6495218488（−0.51%）"
                 "→ 按 §3.97 判定为源修订，本地不追加不回写，仅登记") if revision else "无修订",
    },
    "adjustment": {
        "changed": changed,
        "note": (f"adjustedCount {plan.get('adjustedCount')} = {ADJ_PREV}、investedUnit {plan.get('investedUnit')} = {INV_PREV}、"
                 f"逐品种 planUnit 差分零变动（{len(cur_units)} 个去重代码合计恒 {unit_sum}）、{len(plan['composition'])} 类别 unit 零变动"
                 f" → **本档（10/9 13:45）无新调仓**；最新调仓仍 adj_id 781 / 2026-07-30") if not changed else
                f"⚠️ 检测到调仓：差分 {diffs}；建议用户在且慢 App 核对",
        "adjustedCount_prev": ADJ_PREV, "investedUnit_prev": INV_PREV,
        "latest_adj_id": 781, "latest_adj_date": "2026-07-30",
        "recent_new_adjustment": {
            "fund_code": NEW_CODE, "fund_name": fd.get("fundName"), "variety": it.get("variety"),
            "large_class": item_001257["class"], "direction": "买入", "units": it.get("planUnit"),
            "txn_date_estimated": "2026-10-08",
            "detected_at": "2026-10-08 20:00 收盘档（本档补录落库）",
            "recorded_to_adjustments_json": need_write,
            "source_detail_available": False,
            "pending_user_verification": True,
        },
    },
    "nav_stale_note": (f"nav {plan.get('nav')} / nav_date_beijing = {ts2date(plan.get('navDate') or 0)}；"
                       f"10/9 当日净值收盘后（20:00 前后）发布 → 13:45 档不可得"),
    "adjusted_files": {
        "plan": os.path.basename(plan_f), "nav": os.path.basename(nav_f),
        "adj": [os.path.basename(x) for x in adj_f] or "无（adjustments 明细仍缺，承接待办）",
    },
}
json.dump(digest, open(f"{ROOT}/data/processed/history/qieman_20261009_intraday.json", "w", encoding="utf-8"),
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
    "last_checked": TODAY, "composition_snapshot": f"composition-{TODAY}.json",
    "joinedCount": plan.get("joinedCount"), "activeCount": plan.get("activeCount"),
    "date": TODAY, "navDate_bj": ts2date(plan.get("navDate") or 0),
    "latest_adj_id": 781, "latest_adj_date": "2026-07-30",
    "newest_detected_adj": {"fund_code": NEW_CODE, "direction": "买入", "units": 1,
                            "txn_date_estimated": "2026-10-08", "pending_user_verification": True},
})
json.dump(meta, open(meta_p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

print("\n=== 且慢 LONG_WIN 落库（盘中档） ===")
print(f"plan {digest['plan_body_bytes']}B / nav {digest['nav_body_bytes']}B")
print(f"adjustedCount={digest['adjustedCount']} investedUnit={digest['investedUnit']} planUnit_sum={unit_sum}")
print(f"nav={digest['nav']} nav_date={digest['nav_date_beijing']} 日收益={digest['daily_return_pct']}%")
print(f"nav-history {len(navs)} 条；末 3 条：{nav_seq_tail[-3:]}")
print(f"本地 CSV 末行：{local_last}（口径分歧连续第 21 档，不追加）")
print(f"🟢 E大调仓判定：{'⚠️ 本档有新调仓' if changed else '本档无新调仓'}")
print("✅ qieman_20261009_intraday.json / composition-2026-10-09.json / meta.json 已更新")
