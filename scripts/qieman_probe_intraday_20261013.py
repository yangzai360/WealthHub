# -*- coding: utf-8 -*-
"""2026-10-13 盘中档（13:45）：且慢 REST pmdj 探针（三端点）—— 预期仍为 HTTP 200 / size 0B
⚠️ 计数常量人工核对（§3.121c / §3.130d）：10/07 盘后 = 104、10/08 = 106、10/09 = 106
   → **10/10-10/11 为周末（非交易日）→ 不推进；10/12 = 107；10/13 为 A股 新交易日 → 计数推进为 108**
   （该计数为人工维护、历史存在 ±1 记录差异，已登记为口径待清理项，不以「精确计数」口吻书写）
"""
import json, os, urllib.request, ssl

ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
U = {
 "plan": "https://qieman.com/pmdj/v2/long-win/plan?prodCode=LONG_WIN",
 "nav": "https://qieman.com/pmdj/v2/long-win/plan/nav-history?prodCode=LONG_WIN",
 "adjustments": "https://qieman.com/pmdj/v2/long-win/plan/adjustments?desc=true&prodCode=LONG_WIN",
}
out = {"date": "2026-10-13", "session": "intraday-1345", "session_type": "normal_trading_day_intraday",
       "session_type_note": "正常交易日盘中档（A股 + 港股均开市；13:45）"}
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
json.dump(out, open("/Users/jieyang/Documents/WealthHub/data/processed/history/qieman_rest_20261013_intraday.json", "w",
                    encoding="utf-8"), ensure_ascii=False, indent=1)
print("已保存 qieman_rest_20261013_intraday.json")
