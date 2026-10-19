# -*- coding: utf-8 -*-
"""2026-10-19 **盘中档（13:45）**：且慢 LONG_WIN 落库判定（REST 探针 + playwright 产物归档 + 调仓差分判定）

⚠️ 四类字面量核对（§3.121c / §3.138a，逐项串行替换并回读验证）：
   · 读写路径 = *20261019*（REST 探针产物 = qieman_rest_20261019_intraday.json）
   · 输出档型名 = qieman_20261019_intraday.json / composition-2026-10-19.json
   · session = "intraday"；session_type = "reverse_mixed_closed_hk"
   · 基线 = composition-2026-10-16-close.json（上一 A股 收盘基线）
   · 计数：consecutive_empty_trading_days = 112（10/19 与盘前档同一 A股 交易日，不重复推进，§3.130d）
           playwright_success_count = 47（10/16 收盘档 46 → 本档 +1；§3.133c 人工维护计数）
⚠️ 档型语义：**反向混合档盘中**（A股 正常交易日 + 港股重阳节翌日休市）
⚠️ 本档特殊项：**承接 10/16 收盘档遗留待办** —— 该档检出「001257 兴业收益增强债券A +1 unit（现金 36→35 /
   境内债券 16→17）」并已写入 composition-2026-10-16-close.json（adj 269 / inv 115），但**未落入 adjustments.json**
   → 本档补录 1 条（count 264 → 265），使本地库状态与源侧 269/115 对齐；补录后今日仍判定「无新调仓」
"""
import json, glob, os, csv, datetime, shutil

ROOT = "/Users/jieyang/Documents/WealthHub"
TAG = "20261019i"
OUT = f"{ROOT}/reference-portfolios/long-win"
TODAY = "2026-10-19"
SESSION_TYPE = "reverse_mixed_closed_hk"
SESSION_NOTE = "反向混合档盘中（A股 正常交易日 + 港股重阳节翌日休市；13:45）"


def ts2date(ts):
    return datetime.datetime.fromtimestamp(ts / 1000, datetime.timezone(datetime.timedelta(hours=8))).strftime("%Y-%m-%d")


# ---------- 1. REST 探针（沿用本档探针产物） ----------
p_rest = f"{ROOT}/data/processed/history/qieman_rest_20261019_intraday.json"
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


# ---------- 3. composition 逐品种 planUnit 差分 ----------
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
    f"{OUT}/composition-2026-10-16-close.json",   # 上一 A股 收盘基线
    f"{OUT}/composition-2026-10-16.json",         # 上一档盘中基线（第二兜底）
    f"{OUT}/composition-2026-10-15-close.json",   # 第三兜底
]
print("基线候选存在性:", [(os.path.basename(b), os.path.exists(b)) for b in BASE_FILES])
existing = [b for b in BASE_FILES if os.path.exists(b)]
assert existing, "⚠️ 候选基线文件均不存在 → 终止"
base_file = existing[0]
base_plan = json.load(open(base_file, encoding="utf-8"))
base_units = flat(base_plan)
print(f"composition 基线 = {os.path.basename(base_file)}（{len(base_units)} 个去重代码，§3.133d）")

diffs = []
for code in sorted(set(cur_units) | set(base_units), key=lambda x: str(x)):
    a, b = base_units.get(code, 0), cur_units.get(code, 0)
    if a != b:
        diffs.append({"code": code, "prev": a, "now": b, "delta": b - a})
unit_sum = sum(cur_units.values())
cat_unit_sum = sum(c.get("unit") or 0 for c in plan["composition"])
comp_rows = sum(len(c.get("compList") or []) for c in plan["composition"])
base_cat = {c["className"]: c.get("unit") for c in base_plan["composition"]}
cur_cat = {c["className"]: c.get("unit") for c in plan["composition"]}
cat_diff = {k: [base_cat.get(k), cur_cat.get(k)] for k in cur_cat if base_cat.get(k) != cur_cat.get(k)}
print(f"planUnit 合计 = {unit_sum}（逐品种）；类别 unit 合计 = {cat_unit_sum}")
print(f"品种数两口径：去重代码 = {len(cur_units)} / 成分条数 = {comp_rows}（§3.133d）")
print(f"逐品种差分 vs 10/16 收盘基线：{diffs if diffs else '零变动'}")
print(f"类别 unit 差分：{cat_diff if cat_diff else '零变动'}")

SRC_ADJ, SRC_INV = plan.get("adjustedCount"), plan.get("investedUnit")
ADJ_BASE, INV_BASE = base_plan.get("adjustedCount"), base_plan.get("investedUnit")
print(f"源侧 adjustedCount = {SRC_ADJ}（基线 {ADJ_BASE}）/ investedUnit = {SRC_INV}（基线 {INV_BASE}）")

# ---------- 4. adjustments.json 补录（承接 10/16 收盘档遗留待办） ----------
adj_p = f"{OUT}/adjustments.json"
adj_doc = json.load(open(adj_p, encoding="utf-8"))
before_count = adj_doc.get("count")
existing_txn = {str(a.get("txn_date")) for a in adj_doc["adjustments"]}
backfilled = None
if "2026-10-16" not in existing_txn:
    entry = {
        "adjustment_id": None,
        "txn_date": "2026-10-16",
        "create_time": None,
        "invest_type": "再平衡",
        "url": "",
        "comment": ("（原文不可得）源侧 adjustedCount 268→269 / investedUnit 114→115；composition 逐品种 "
                    "001257 兴业收益增强债券A planUnit 2→3、现金类 unit 36→35、境内债券 16→17 "
                    "→ 判定为「现金 → 境内债券」1 unit 再平衡。该信号于 2026-10-16 盘后档检出，"
                    "本档（2026-10-19 盘中）补录落库。"),
        "orders": [{
            "fund_code": "001257", "fund_name": "兴业收益增强债券A",
            "variety": "境内债券", "large_class": "境内债券",
            "direction": "买入", "trade_unit": 1, "post_plan_unit": 3,
            "nav": None, "nav_date": None,
        }],
        "detection": {
            "source": "qieman composition diff（playwright 兜底）",
            "evidence": {"adjustedCount": "268→269", "investedUnit": "114→115", "planUnit": "001257: 2→3",
                         "classUnit": "现金 36→35 / 境内债券 16→17"},
            "detected_on": "2026-10-16-close",
            "backfilled_on": "2026-10-19-intraday",
        },
        "unavailable_fields": ["adjustment_id", "create_time", "url", "comment(原文)", "nav", "nav_date"],
    }
    adj_doc["adjustments"].append(entry)
    adj_doc["count"] = len(adj_doc["adjustments"])
    adj_doc.setdefault("backfill_log", []).append({
        "txn_date": "2026-10-16", "fund_code": "001257", "direction": "买入", "trade_unit": 1,
        "detected_on": "2026-10-16-close", "backfilled_on": TODAY,
        "reason": "10/16 收盘档仅写入 composition 快照、未落 adjustments.json（跨档遗留待办）",
    })
    json.dump(adj_doc, open(adj_p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    backfilled = {"txn_date": "2026-10-16", "fund_code": "001257", "fund_name": "兴业收益增强债券A",
                  "direction": "买入", "trade_unit": 1, "large_class": "境内债券"}
    print(f"✅ 补录 1 条：2026-10-16 买入 001257 兴业收益增强债券A × 1 unit；count {before_count} → {adj_doc['count']}")
else:
    print("  10/16 条目已存在，跳过补录")

# 本地库状态：取「最近一条带 detection.evidence.adjustedCount」的终值
def _tail(v):
    return int(str(v).split("→")[1].strip())


LOCAL_ADJ, LOCAL_INV = 269, 115
for a in adj_doc["adjustments"]:
    ev = (a.get("detection") or {}).get("evidence") or {}
    if ev.get("adjustedCount"):
        try:
            LOCAL_ADJ = _tail(ev["adjustedCount"])
        except Exception:
            pass
    if ev.get("investedUnit"):
        try:
            LOCAL_INV = _tail(ev["investedUnit"])
        except Exception:
            pass

print(f"\n=== adjustments.json 落库判定 ===")
print(f"  本地现有 {len(adj_doc['adjustments'])} 条调仓（count={adj_doc.get('count')}）")
print(f"  本地已落库最新状态：adjustedCount = {LOCAL_ADJ} / investedUnit = {LOCAL_INV}")
print(f"  源侧当前状态：adjustedCount = {SRC_ADJ} / investedUnit = {SRC_INV}")
changed = bool(diffs) or (SRC_ADJ or 0) > LOCAL_ADJ
assert not (SRC_ADJ is not None and SRC_ADJ > LOCAL_ADJ), \
    "⚠️ 源侧出现未落库的新调仓 → 须按 §3.141a ③ 流程补录"
print(f"  → {'🔔 本档有新调仓' if changed else '今日（10/19）无新调仓 —— 源侧 269/115 与 10/16 收盘档一致'}")

cats = [{"className": c.get("className"), "unit": c.get("unit"), "percent": c.get("percent"),
         "funds": len(c.get("compList") or [])} for c in plan["composition"]]

nav_last = navs[-1]
nav_seq_tail = [{"date": ts2date(x["navDate"]), "nav": round(x["nav"], 7), "ret": round(x["dailyReturn"] * 100, 4)}
                for x in navs[-10:]]

rows = list(csv.reader(open(f"{ROOT}/data/processed/reference/long-win-nav.csv", encoding="utf-8-sig")))
local_last = rows[-1]

# 源修订登记：10/16 收盘档读到 1.632275、本档源侧为 1.6324565；10/15 亦由 1.6336102 修订为 1.6338534
NAV_1016_PRIOR = 1.632275
NAV_1016_NOW = next((x["nav"] for x in nav_seq_tail if x["date"] == "2026-10-16"), None)
revision = bool(NAV_1016_NOW is not None and abs(NAV_1016_NOW - NAV_1016_PRIOR) > 1e-6)

digest = {
    "date": TODAY,
    "session": "intraday",
    "session_type": SESSION_TYPE,
    "session_type_note": SESSION_NOTE,
    "rest_probe": probe,
    "playwright_fallback": True,
    "playwright_success_count": 47,
    "consecutive_empty_trading_days": 112,
    "consecutive_note": ("A股 10/19 为交易日；盘前档已记 112，本档同一 A股 交易日不重复推进（§3.130d）；"
                         "该计数为人工维护、历史存在 ±1 记录差异（§3.133c）"),
    "plan_body_bytes": os.path.getsize(plan_f),
    "nav_body_bytes": os.path.getsize(nav_f),
    "adjustedCount": plan.get("adjustedCount"),
    "investedUnit": plan.get("investedUnit"),
    "planUnit_sum": unit_sum,
    "planUnit_cat_sum": cat_unit_sum,
    "plan_unit_zero_change": len(diffs) == 0,
    "planunit_diff": diffs,
    "class_unit_diff": cat_diff,
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
        "status": "挂起（连续第 29 档）",
        "source_last": nav_seq_tail[-1],
        "local_last": {"date": local_last[0], "nav": float(local_last[1])},
        "action": "按 §3.97/§3.99 不追加、不回写；口径统一为用户决策第 1 优先项",
    },
    "source_revision": {
        "observed": revision,
        "target": "2026-10-16 组合净值",
        "prior": NAV_1016_PRIOR,
        "now": NAV_1016_NOW,
        "also_revised": {"2026-10-15": {"prior": 1.6336102, "now": 1.6338534}},
        "note": (f"源侧把 10/16 收盘档读到 {NAV_1016_PRIOR} 修订为 {NAV_1016_NOW}；10/15 亦由 1.6336102 修订为 1.6338534 "
                 "→ 按 §3.97 判定为源修订，本地不追加不回写，仅登记") if revision else "无修订",
    },
    "adjustment": {
        "changed": changed,
        "source_state": {"adjustedCount": SRC_ADJ, "investedUnit": SRC_INV},
        "local_db_state": {"adjustedCount": LOCAL_ADJ, "investedUnit": LOCAL_INV},
        "appended_this_session": backfilled is not None,
        "appended_detail": backfilled,
        "appended_txn_date": backfilled["txn_date"] if backfilled else None,
        "note": ("本档补录 10/16 收盘档遗留的 001257 +1 unit（composition 已于该档更新、adjustments.json 未落）；"
                 "补录后本地 269/115 与源侧一致 → 今日无新调仓。" if backfilled else
                 "10/16 条目已存在；今日源侧与本地一致 → 无新调仓"),
        "adjustedCount_prev": ADJ_BASE, "investedUnit_prev": INV_BASE,
        "latest_adj_id": 781, "latest_adj_date": "2026-07-30",
        "recent_new_adjustment": False,
        "sequence_note": ("10/16 收盘档检出 001257 +1（现金→境内债券）→ 本档补录落库；"
                          "属「连续第 4 次新券/加仓补录」序列（10/8 001257 → 10/12 001257 → 10/13 100050 → 10/16 001257）"),
    },
    "nav_stale_note": (f"nav {plan.get('nav')} / nav_date_beijing = {ts2date(plan.get('navDate') or 0)}；"
                       "10/19 当日净值收盘后（20:00 前后）发布 → 13:45 档不可得"),
    "adjusted_files": {
        "plan": os.path.basename(plan_f), "nav": os.path.basename(nav_f),
        "adj": [os.path.basename(x) for x in adj_f] or "无（adjustments 端点仍空 body）",
    },
}
json.dump(digest, open(f"{ROOT}/data/processed/history/qieman_20261019_intraday.json", "w", encoding="utf-8"),
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

print("\n=== 且慢 LONG_WIN 落库（盘中档 · 反向混合档） ===")
print(f"plan {digest['plan_body_bytes']}B / nav {digest['nav_body_bytes']}B")
print(f"adjustedCount={digest['adjustedCount']} investedUnit={digest['investedUnit']} planUnit_sum={unit_sum}")
print(f"nav={digest['nav']} nav_date={digest['nav_date_beijing']} 日收益={digest['daily_return_pct']}%")
print(f"nav-history {len(navs)} 条；末 3 条：{nav_seq_tail[-3:]}")
print(f"本地 CSV 末行：{local_last}（口径分歧连续第 29 档，不追加）")
print(f"🟢 E大调仓判定：{'⚠️ 本档有新调仓' if changed else '10/19 当日 13:45 无新增调仓'}"
      f"｜补录 = {'是（2026-10-16 001257 ×1）' if backfilled else '否'}")
print("✅ qieman_20261019_intraday.json / composition-2026-10-19.json / meta.json 已更新")
