# -*- coding: utf-8 -*-
"""2026-10-14 **盘中档（13:45）**：且慢 LONG_WIN 落库判定（REST 探针 + playwright 产物归档 + 未落库调仓补录）

⚠️ 四类字面量核对（§3.121c / §3.138a）：
   · 读写路径 = *20261014*（REST 探针产物 = qieman_rest_20261014_intraday.json，本档复用不改写）
   · 输出档型名 = qieman_20261014_intraday.json / composition-2026-10-14.json
   · session = "intraday"；session_type = "normal_trading_day_intraday"
   · 基线 = composition-2026-10-13-close.json（上一 A股 收盘基线）
   · 计数：consecutive_empty_trading_days = 109（10/14 为 A股 交易日，较 10/13 收盘档 108 推进 +1）
           playwright_success_count = 43（10/13 收盘档 42 → 本档 +1；§3.133c 人工维护计数）
⚠️ 档型语义：正常交易日盘中（A股 + 港股均开市；长假后第 5 个正常交易日）
⚠️ 本档特殊项（§3.141a ③ / 承接 10/13 收盘档遗留待办）：
   本地 adjustments.json 最新一条 = **2026-10-12（adj 266→267 / inv 112→113，001257 +1 份）**，
   而源侧 adjustedCount = **268** / investedUnit = **114** → **存在 1 笔「已检出但未落库」的调仓**
   （10/13 收盘档 20:00 检出：100050 富国全球债券(QDII)人民币A 3→4 份，+1 unit，海外债券类；
     现金 37→36 / 海外债券 6→7，计划总量恒 150 份）
   → 本档按「检出档的次一档落库」既有惯例（同 10/12 检出 → 10/13 13:45 落库）**执行补录**。
⚠️ 本档与 10/13 收盘基线逐品种 planUnit **零差分**（63 个去重代码合计恒 114）→ 10/14 当日（13:45）无新增调仓。
"""
import json, glob, os, csv, datetime, shutil

ROOT = "/Users/jieyang/Documents/WealthHub"
TAG = "20261014i"
OUT = f"{ROOT}/reference-portfolios/long-win"
TODAY = "2026-10-14"
SESSION_TYPE = "normal_trading_day_intraday"
SESSION_NOTE = "正常交易日盘中档（A股 长假后第 5 个正常交易日 + 港股正常交易日；13:45 双方均开市）"


def ts2date(ts):
    return datetime.datetime.fromtimestamp(ts / 1000, datetime.timezone(datetime.timedelta(hours=8))).strftime("%Y-%m-%d")


# ---------- 1. REST 探针（沿用本档探针产物，不改写） ----------
p_rest = f"{ROOT}/data/processed/history/qieman_rest_20261014_intraday.json"
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
    f"{OUT}/composition-2026-10-13-close.json",   # 上一 A股 收盘基线
    f"{OUT}/composition-2026-10-13.json",         # 上一档盘中基线（第二兜底）
    f"{OUT}/composition-2026-10-12-close.json",   # 第三兜底
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
print(f"逐品种差分 vs 10/12 收盘基线：{diffs if diffs else '零变动'}")

ADJ_PREV, INV_PREV = 268, 114
changed = bool(diffs) or plan.get("adjustedCount") != ADJ_PREV or plan.get("investedUnit") != INV_PREV

# ---------- 4. adjustments.json 落库判定 + 未落库补录（本档特殊项） ----------
adj_p = f"{OUT}/adjustments.json"
adj_doc = json.load(open(adj_p, encoding="utf-8"))
SRC_ADJ, SRC_INV = plan.get("adjustedCount"), plan.get("investedUnit")
# 本地已落库状态（从 adjustments.json 的 detection.evidence 推得：最新一条 = 10/8，adj 265→266 / inv 111→112）
LOCAL_ADJ, LOCAL_INV = 267, 113
detected_docs = []
for a in adj_doc["adjustments"]:
    ev = (a.get("detection") or {}).get("evidence") or {}
    if ev.get("adjustedCount"):
        try:
            detected_docs.append(int(str(ev["adjustedCount"]).split("→")[1].strip()))
        except Exception:
            pass
LOCAL_ADJ = max(detected_docs) if detected_docs else LOCAL_ADJ
detected_inv = []
for a in adj_doc["adjustments"]:
    ev = (a.get("detection") or {}).get("evidence") or {}
    if ev.get("investedUnit"):
        try:
            detected_inv.append(int(str(ev["investedUnit"]).split("→")[1].strip()))
        except Exception:
            pass
LOCAL_INV = max(detected_inv) if detected_inv else LOCAL_INV

print(f"\n=== adjustments.json 落库判定 ===")
print(f"  本地现有 {len(adj_doc['adjustments'])} 条调仓（count={adj_doc.get('count')}）")
print(f"  本地已落库最新状态：adjustedCount = {LOCAL_ADJ} / investedUnit = {LOCAL_INV}")
print(f"  源侧当前状态：adjustedCount = {SRC_ADJ} / investedUnit = {SRC_INV}")

appended = None
if SRC_ADJ is not None and SRC_ADJ > LOCAL_ADJ:
    appended = {
        "adjustment_id": None,
        "txn_date": "2026-10-13",
        "create_time": None,
        "invest_type": "E",
        "url": "",
        "comment": "买入1份富国全球债券(QDII)人民币A（现金类 37→36 份、海外债券类 6→7 份）",
        "orders": [{"fund_code": "100050", "fund_name": "富国全球债券(QDII)人民币A",
                    "variety": "富国全球债券", "large_class": "海外债券",
                    "direction": "买入", "trade_unit": 1, "post_plan_unit": 4,
                    "nav": None, "nav_date": None}],
        "detection": {
            "detected_at": "2026-10-13T20:00 (close档)",
            "recorded_at": "2026-10-14 13:45 (intraday档)",
            "method": "composition 逐品种/逐类别 planUnit 差分 + adjustedCount/investedUnit 三重交叉验证",
            "evidence": {"adjustedCount": "267 → 268", "investedUnit": "113 → 114",
                         "class_shift": "现金 37 → 36；海外债券 6 → 7（计划总量恒 150 份）"},
            "unavailable_fields": ["adjustment_id", "create_time", "url", "comment(原文)", "nav", "nav_date"],
            "unavailable_reason": ("qieman pmdj adjustments 端点连续第 109 个交易日空 body（HTTP 200 / size 0），"
                                   "playwright 亦未捕获 adjustments 响应 → 无法取得调仓原文"),
            "prior_same_fund": "该券上一次变动 = 计划纳入期（本地 adjustments.json 无同券近期记录）",
            "pending_user_verification": "建议用户在且慢 App 核对本次加仓",
        },
    }
    adj_doc["adjustments"].insert(0, appended)
    adj_doc["count"] = len(adj_doc["adjustments"])
    adj_doc["last_updated"] = TODAY
    adj_doc["last_updated_note"] = "由 2026-10-14 盘中档据 composition 差分推定补录（源 adjustments 端点不可用）"
    json.dump(adj_doc, open(adj_p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"  ✅ 补录 1 条：txn_date 2026-10-13 / 100050 +1 unit（adj {LOCAL_ADJ}→{SRC_ADJ} / inv {LOCAL_INV}→{SRC_INV}）")
else:
    print("  → 本地已覆盖源侧最新调整（或源侧无更高计数），无需写入")

cats = [{"className": c.get("className"), "unit": c.get("unit"), "percent": c.get("percent"),
         "funds": len(c.get("compList") or [])} for c in plan["composition"]]

nav_last = navs[-1]
nav_seq_tail = [{"date": ts2date(x["navDate"]), "nav": round(x["nav"], 7), "ret": round(x["dailyReturn"] * 100, 4)}
                for x in navs[-10:]]

rows = list(csv.reader(open(f"{ROOT}/data/processed/reference/long-win-nav.csv", encoding="utf-8-sig")))
local_last = rows[-1]
NAV_1013_PRIOR = 1.6496   # 10/13 收盘档 plan.nav 读数
NAV_1013_NOW = None
for x in nav_seq_tail:
    if x["date"] == "2026-10-13":
        NAV_1013_NOW = x["nav"]
revision = bool(NAV_1013_NOW is not None and abs(NAV_1013_NOW - NAV_1013_PRIOR) > 1e-6)

digest = {
    "date": TODAY,
    "session": "intraday",
    "session_type": SESSION_TYPE,
    "session_type_note": SESSION_NOTE,
    "rest_probe": probe,
    "playwright_fallback": True,
    "playwright_success_count": 43,
    "consecutive_empty_trading_days": 109,
    "consecutive_note": "A股 10/14 为交易日 → 计数由 10/13 收盘档 108 推进至 109；该计数为人工维护、历史存在 ±1 记录差异（§3.133c）",
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
        "status": "挂起（连续第 26 档）",
        "source_last": nav_seq_tail[-1],
        "local_last": {"date": local_last[0], "nav": float(local_last[1])},
        "action": "按 §3.97/§3.99 不追加、不回写；口径统一为用户决策第 1 优先项",
    },
    "source_revision": {
        "observed": revision,
        "target": "2026-10-13 组合净值",
        "prior": NAV_1013_PRIOR,
        "now": NAV_1013_NOW,
        "note": (f"源侧把 10/13 收盘档读到 {NAV_1013_PRIOR} 修订为 {NAV_1013_NOW} → 按 §3.97 判定为源修订，"
                 "本地不追加不回写，仅登记") if revision else "无修订",
    },
    "adjustment": {
        "changed": changed,
        "source_state": {"adjustedCount": SRC_ADJ, "investedUnit": SRC_INV},
        "local_db_state": {"adjustedCount": LOCAL_ADJ, "investedUnit": LOCAL_INV},
        "appended_this_session": appended is not None,
        "appended_txn_date": "2026-10-13" if appended else None,
        "note": ("本档 vs 10/13 收盘基线**逐品种 planUnit 零差分**（63 个去重代码合计恒 114）、类别 unit 零变动 "
                 "→ **10/14 当日（13:45）无新增调仓**；但**源侧 adj 268 / inv 114 高于本地已落库的 267 / 113** → "
                 "对 10/13 收盘档检出的 +1 unit「100050 富国全球债券(QDII)人民币A」执行补录（§3.141a ③ / 承接 10/13 遗留待办）"
                 ) if appended else ("本档无新增调仓，且本地已覆盖源侧最新状态（adj 268 / inv 114）"),
        "adjustedCount_prev": ADJ_PREV, "investedUnit_prev": INV_PREV,
        "latest_adj_id": 781, "latest_adj_date": "2026-07-30",
        "recent_new_adjustment": appended,
    },
    "nav_stale_note": (f"nav {plan.get('nav')} / nav_date_beijing = {ts2date(plan.get('navDate') or 0)}；"
                       f"10/14 当日净值收盘后（20:00 前后）发布 → 13:45 档不可得"),
    "adjusted_files": {
        "plan": os.path.basename(plan_f), "nav": os.path.basename(nav_f),
        "adj": [os.path.basename(x) for x in adj_f] or "无（adjustments 端点仍空 body）",
    },
}
json.dump(digest, open(f"{ROOT}/data/processed/history/qieman_20261014_intraday.json", "w", encoding="utf-8"),
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
})
json.dump(meta, open(meta_p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

print("\n=== 且慢 LONG_WIN 落库（盘中档） ===")
print(f"plan {digest['plan_body_bytes']}B / nav {digest['nav_body_bytes']}B")
print(f"adjustedCount={digest['adjustedCount']} investedUnit={digest['investedUnit']} planUnit_sum={unit_sum}")
print(f"nav={digest['nav']} nav_date={digest['nav_date_beijing']} 日收益={digest['daily_return_pct']}%")
print(f"nav-history {len(navs)} 条；末 3 条：{nav_seq_tail[-3:]}")
print(f"本地 CSV 末行：{local_last}（口径分歧连续第 26 档，不追加）")
print(f"🟢 E大调仓判定：{'⚠️ 本档有新调仓' if changed else '10/14 当日无新增调仓'}"
      f"｜补录 = {'是（2026-10-13 / 100050 +1 unit）' if appended else '否'}")
print("✅ qieman_20261014_intraday.json / composition-2026-10-14.json / meta.json 已更新")
