# -*- coding: utf-8 -*-
"""2026-10-02 盘中档：且慢 REST pmdj 探针（三端点）—— 连续第 101 个交易日空 body 预期"""
import json, os, urllib.request, ssl

ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
U = {
 "plan": "https://qieman.com/pmdj/v2/long-win/plan?prodCode=LONG_WIN",
 "nav": "https://qieman.com/pmdj/v2/long-win/plan/nav-history?prodCode=LONG_WIN",
 "adjustments": "https://qieman.com/pmdj/v2/long-win/plan/adjustments?desc=true&prodCode=LONG_WIN",
}
out = {"date": "2026-10-02", "session": "intraday-1345"}
for k, u in U.items():
    try:
        req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0", "Referer": "https://qieman.com/longwin"})
        with urllib.request.urlopen(req, timeout=20, context=ctx) as r:
            body = r.read()
        out[k] = {"status": r.status, "size": len(body)}
        print(f"{k:12s} HTTP {r.status}  size={len(body)}B  {'EMPTY ✅' if len(body) < 5 else 'HAS BODY'}")
    except Exception as e:
        out[k] = {"error": str(e)}
        print(f"{k:12s} ERROR {e}")
json.dump(out, open("/Users/jieyang/Documents/WealthHub/data/processed/history/qieman_rest_20261002.json", "w",
                    encoding="utf-8"), ensure_ascii=False, indent=1)
print("已保存 qieman_rest_20261002.json")
