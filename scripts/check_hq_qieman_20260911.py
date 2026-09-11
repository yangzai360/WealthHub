# -*- coding: utf-8 -*-
"""2026-09-11 盘中: 个股实时(sina hq 直连, 带 Referer) + 指数交叉验证 + 且慢 E大调仓监控"""
import urllib.request, json, os, re, time

BASE = "/Users/jieyang/Documents/WealthHub"

def fetch(url, encoding="utf-8", timeout=25, referer=None):
    headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
    if referer:
        headers["Referer"] = referer
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode(encoding, errors="ignore")

print("=== 1. 个股/指数实时 (sina hq 直连, GBK, 带 Referer) ===")
try:
    url = "http://hq.sinajs.cn/list=sz002410,sh600438,sh600519,sh000001,sz399006,sh000932,sh000300,s_sz399006,s_sh000001"
    raw = fetch(url, encoding="gbk", referer="https://finance.sina.com.cn")
    for line in raw.strip().split("\n"):
        if "=" not in line:
            continue
        code = line.split("=")[0].split("_")[-1]
        payload = line.split('="')[-1].rstrip('";')
        parts = payload.split(",")
        if len(parts) > 5:
            name, open_, prev, cur, high, low = parts[0], parts[1], parts[2], parts[3], parts[4], parts[5]
            try:
                pct = (float(cur) - float(prev)) / float(prev) * 100
            except Exception:
                pct = float("nan")
            print(f"  {code} {name}: 现价 {cur} 开 {open_} 昨收 {prev} 高 {high} 低 {low} 涨跌 {pct:.2f}%")
except Exception as e:
    print(f"  [ERR] {e}")

print("\n=== 2. 且慢 E大长赢调仓 (adjustments) ===")
adj = None
for attempt in range(3):
    try:
        raw = fetch("https://qieman.com/pmdj/v2/long-win/plan/adjustments?desc=true&prodCode=LONG_WIN", timeout=30)
        print(f"  HTTP OK, SIZE={len(raw)}")
        if raw.strip():
            adj = json.loads(raw)
            break
        else:
            print("  [空 body]")
    except Exception as e:
        print(f"  [ERR attempt {attempt+1}] {e}")
    time.sleep(2)

local_path = os.path.join(BASE, "reference-portfolios/long-win/adjustments.json")
with open(local_path, encoding="utf-8") as f:
    local = json.load(f)
local_list = local if isinstance(local, list) else local.get("adjustments", [])
local_ids = set()
for a in local_list:
    local_ids.add(str(a.get("adjustment_id")))
print(f"  本地调仓记录 {len(local_list)} 条, 最新 adjustment_id 集合前3: {sorted(local_ids, key=lambda x: (len(x), x), reverse=True)[:3]}")

if adj is not None:
    data = adj.get("data") if isinstance(adj, dict) else adj
    if isinstance(data, dict):
        items = data.get("adjustments") or data.get("list") or []
    else:
        items = data or []
    print(f"  远端返回 {len(items)} 条")
    remote_ids = [str(i.get("adjustment_id")) for i in items]
    print(f"  远端最新 5 条 id: {remote_ids[:5]}")
    new = [i for i in items if str(i.get("adjustment_id")) not in local_ids]
    print(f"  >>> 未落库新调仓: {len(new)} 条")
    for i in new:
        print(f"      id={i.get('adjustment_id')} txn_date={i.get('txn_date')} invest_type={i.get('invest_type')}")
        print(f"      comment={str(i.get('comment'))[:200]}")
        print(f"      url={i.get('url')}")
        for o in (i.get("orders") or []):
            print(f"        order: {o.get('fund_code')} {o.get('fund_name')} {o.get('variety')} {o.get('direction')} {o.get('trade_unit')}份")
    with open("/tmp/qieman_remote_adjustments.json", "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=1)
    with open("/tmp/qieman_new_adjustments.json", "w", encoding="utf-8") as f:
        json.dump(new, f, ensure_ascii=False, indent=1)
else:
    print("  >>> E大调仓数据暂缺（pmdj 空 body），本地为准")
