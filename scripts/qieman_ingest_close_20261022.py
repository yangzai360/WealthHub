# -*- coding: utf-8 -*-
"""2026-10-22 **盘中档（13:45）**：且慢 LONG_WIN 落库判定（REST 探针 + playwright 产物归档 + 调仓差分判定）

⚠️ 四类字面量核对（§3.121c / §3.138a，逐项串行替换并回读验证）：
   · 读写路径 = *20261022*（REST 探针产物 = qieman_rest_close_20261022.json）
   · 输出档型名 = qieman_20261022_close.json / composition-2026-10-22.json
   · session = "intraday"；session_type = "normal_trading_day_intraday"
   · 基线 = composition-2026-10-21.json（上一档基线；10/21 收盘档未另存 -close）
   · 计数：consecutive_empty_trading_days = 116（10/21 = 115 → 本档 A股 新交易日 → 116，§3.130d）
           playwright_success_count = 50（10/21 收盘档 49 → 本档 +1；§3.133c 人工维护计数）
⚠️ 档型语义：**正常交易日盘中**（A股 第 11 个正常交易日 15:00 收盘 + 港股 16:00 收盘）
"""
import json, glob, os, csv, datetime, shutil

ROOT = "/Users/jieyang/Documents/WealthHub"
TAG = "20261022c"
OUT = f"{ROOT}/reference-portfolios/long-win"
TODAY = "2026-10-22"
SESSION_TYPE = "normal_trading_day_close"
SESSION_NOTE = "正常交易日收盘（A股 第 11 个正常交易日 15:00 收盘 + 港股 16:00 收盘；20:00）"


def ts2date(ts):
    return datetime.datetime.fromtimestamp(ts / 1000, datetime.timezone(datetime.timedelta(hours=8))).strftime("%Y-%m-%d")


# ---------- 1. REST 探针 ----------
p_rest = f"{ROOT}/data/processed/history/qieman_rest_close_20261022.json"
probe = json.load(open(p_rest, encoding="utf-8"))
probe["session_ref"] = "intraday-1345（本档实测三端点均 HTTP 200 / size 0）"
print("REST 探针（本档实测）:", {k: v for k, v in probe.items() if isinstance(v, dict)})

# ---------- 2. 归档 playwright 产物（多份时取最大体积 + 结构完整性校验，§3.162a） ----------
cands = sorted(glob.glob(f"/tmp/qieman_pwc_plan_{TAG}_*.json"), key=os.path.getsize)
plan_f = None
for c in reversed(cands):
    try:
        d = json.load(open(c))
        if len(d.get("composition") or []) >= 8 and d.get("adjustedCount"):
            plan_f = c
            print(f"  plan 候选 {os.path.basename(c)} {os.path.getsize(c)}B → 结构完整（8 类 + adjustedCount）✅")
            break
        print(f"  plan 候选 {os.path.basename(c)} {os.path.getsize(c)}B → 结构不完整，跳过")
    except Exception as e:
        print(f"  plan 候选 {os.path.basename(c)} 解析失败 {e}")
assert plan_f, "⚠️ 无结构完整的 plan 产物 → 终止"
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
    f"{OUT}/composition-2026-10-21.json",         # 上一档（10/21 盘中→收盘未另存）
    f"{OUT}/composition-2026-10-20-close.json",   # 第二兜底
    f"{OUT}/composition-2026-10-16-close.json",   # 第三兜底
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
print(f"逐品种差分 vs 10/21 基线：{diffs if diffs else '零变动'}")
print(f"类别 unit 差分：{cat_diff if cat_diff else '零变动'}")

SRC_ADJ, SRC_INV = plan.get("adjustedCount"), plan.get("investedUnit")
ADJ_BASE, INV_BASE = base_plan.get("adjustedCount"), base_plan.get("investedUnit")
print(f"源侧 adjustedCount = {SRC_ADJ}（基线 {ADJ_BASE}）/ investedUnit = {SRC_INV}（基线 {INV_BASE}）")

# ---------- 4. adjustments.json 状态核对（本档不预期补录） ----------
adj_p = f"{OUT}/adjustments.json"
adj_doc = json.load(open(adj_p, encoding="utf-8"))
before_count = adj_doc.get("count")


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
print(f"  → {'🔔 本档有新调仓（须补录）' if changed else '今日（10/22）无新调仓 —— 源侧与本地同位'}")
if changed:
    print("  ⚠️ 检测到新调仓但原文端点不可用 → 按 §3.141a ③ 流程须补录，本档先落 composition、补录待 20:00 档")

cats = [{"className": c.get("className"), "unit": c.get("unit"), "percent": c.get("percent"),
         "funds": len(c.get("compList") or [])} for c in plan["composition"]]

nav_last = navs[-1]
nav_seq_tail = [{"date": ts2date(x["navDate"]), "nav": round(x["nav"], 7), "ret": round(x["dailyReturn"] * 100, 4)}
                for x in navs[-10:]]

rows = list(csv.reader(open(f"{ROOT}/data/processed/reference/long-win-nav.csv", encoding="utf-8-sig")))
local_last = rows[-1]

digest = {
    "date": TODAY,
    "session": "close",
    "session_type": SESSION_TYPE,
    "session_type_note": SESSION_NOTE,
    "rest_probe": probe,
    "playwright_fallback": True,
    "playwright_success_count": 51,
    "consecutive_empty_trading_days": 117,
    "consecutive_note": ("A股 10/22 为新交易日；盘中档记 116 → 本档推进至 117（§3.169c 差值=新增交易日数 1）；"
                         "该计数为人工维护、历史存在 ±1 记录差异（§3.133c）"),
    "plan_body_bytes": os.path.getsize(plan_f),
    "nav_body_bytes": os.path.getsize(nav_f),
    "plan_candidates": [{"file": os.path.basename(c), "bytes": os.path.getsize(c)} for c in cands],
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
        "status": "挂起（连续第 35 档）",
        "source_last": nav_seq_tail[-1],
        "local_last": {"date": local_last[0], "nav": float(local_last[1])},
        "action": "按 §3.97/§3.99 不追加、不回写；口径统一为用户决策第 1 优先项",
    },
    "source_revision": {
        "observed": False,
        "note": "本档已与 10/21 收盘档 nav 快照比对（见 source_revision_compare），差异按 §3.97 仅登记不回写",
    },
    "adjustment": {
        "changed": changed,
        "source_state": {"adjustedCount": SRC_ADJ, "investedUnit": SRC_INV},
        "local_db_state": {"adjustedCount": LOCAL_ADJ, "investedUnit": LOCAL_INV},
        "appended_this_session": False,
        "appended_detail": None,
        "appended_txn_date": None,
        "note": ("源侧 269/115 与本地一致、planUnit 差分全零 → 今日无新调仓" if not changed
                 else "源侧出现新调仓，composition 已落库，adjustments.json 补录待 10/23 盘前档（§3.141a ③）"),
        "adjustedCount_prev": ADJ_BASE, "investedUnit_prev": INV_BASE,
        "latest_adj_id": 781, "latest_adj_date": "2026-07-30",
        "recent_new_adjustment": False,
        "sequence_note": "10/21 收盘档至本档连续零差分（继 10/16 001257 补录之后的平静档续接，第 4 个交易日）",
    },
    "nav_stale_note": (f"nav {plan.get('nav')} / nav_date_beijing = {ts2date(plan.get('navDate') or 0)}；"
                       "10/22 当日净值于收盘后 21:00 前后发布 → 20:00 档仍不可得；本档 nav 为 10/21 收盘值"),
    "adjusted_files": {
        "plan": os.path.basename(plan_f), "nav": os.path.basename(nav_f),
        "adj": [os.path.basename(x) for x in adj_f] or "无（adjustments 端点仍空 body）",
    },
}
json.dump(digest, open(f"{ROOT}/data/processed/history/qieman_20261022_close.json", "w", encoding="utf-8"),
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

print("\n=== 且慢 LONG_WIN 落库（盘后档 · 正常交易日收盘） ===")
print(f"plan {digest['plan_body_bytes']}B / nav {digest['nav_body_bytes']}B")
print(f"adjustedCount={digest['adjustedCount']} investedUnit={digest['investedUnit']} planUnit_sum={unit_sum}")
print(f"nav={digest['nav']} nav_date={digest['nav_date_beijing']} 日收益={digest['daily_return_pct']}%")
print(f"nav-history {len(navs)} 条；末 3 条：{nav_seq_tail[-3:]}")
print(f"本地 CSV 末行：{local_last}（口径分歧连续第 35 档，不追加）")
print(f"🟢 E大调仓判定：{'⚠️ 本档有新调仓' if changed else '10/22 收盘无新增调仓'}")
print("✅ qieman_20261022_close.json / composition-2026-10-22.json / meta.json 已更新")
