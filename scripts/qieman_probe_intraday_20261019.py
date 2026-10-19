# -*- coding: utf-8 -*-
"""2026-10-19 盘中档（13:45）：且慢 REST pmdj 探针（三端点）—— 预期仍为 HTTP 200 / size 0B
⚠️ 计数常量人工核对（§3.121c / §3.130d）：10/14 = 109、10/15 = 110、10/16 = 111
   → **10/19 为 A股 新交易日 → 计数推进为 112**
   （该计数为人工维护、历史存在 ±1 记录差异，已登记为口径待清理项，不以「精确计数」口吻书写）
   ⚠️ 与盘前档 10/19 已记的「连续第 112 个」同值 —— 同一 A股 交易日内不重复推进
"""
import json, os, urllib.request, ssl

ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
U = {
 "plan": "https://qieman.com/pmdj/v2/long-win/plan?prodCode=LONG_WIN",
 "nav": "https://qieman.com/pmdj/v2/long-win/plan/nav-history?prodCode=LONG_WIN",
 "adjustments": "https://qieman.com/pmdj/v2/long-win/plan/adjustments?desc=true&prodCode=LONG_WIN",
}
out = {"date": "2026-10-19", "session": "intraday-1345", "session_type": "reverse_mixed_closed_hk",
       "session_type_note": "反向混合档盘中（A股 正常交易日 + 港股重阳节翌日休市；13:45）"}
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
json.dump(out, open("/Users/jieyang/Documents/WealthHub/data/processed/history/qieman_rest_20261019_intraday.json", "w",
                    encoding="utf-8"), ensure_ascii=False, indent=1)
print("已保存 qieman_rest_20261019_intraday.json")
