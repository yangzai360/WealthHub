# -*- coding: utf-8 -*-
"""2026-10-22 盘后档（20:00）：且慢 REST pmdj 探针（三端点）—— 预期仍为 HTTP 200 / size 0B
⚠️ 计数常量人工核对（§3.121c / §3.169c）：10/21 收盘 = 116 个 A股 交易日 → 10/22 为**新增 1 个 A股 交易日** → **本档推进至 117**
   （与上一档差值必须 = 新增交易日数，§3.169c）
   （该计数为人工维护、历史存在 ±1 记录差异，已登记为口径待清理项）
"""
import json, os, urllib.request, ssl

ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
U = {
 "plan": "https://qieman.com/pmdj/v2/long-win/plan?prodCode=LONG_WIN",
 "nav": "https://qieman.com/pmdj/v2/long-win/plan/nav-history?prodCode=LONG_WIN",
 "adjustments": "https://qieman.com/pmdj/v2/long-win/plan/adjustments?desc=true&prodCode=LONG_WIN",
}
out = {"date": "2026-10-22", "session": "close-2000", "session_type": "normal_trading_day_close"}
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
json.dump(out, open("/Users/jieyang/Documents/WealthHub/data/processed/history/qieman_rest_close_20261022.json", "w",
                    encoding="utf-8"), ensure_ascii=False, indent=1)
print("已保存 qieman_rest_close_20261022.json")
