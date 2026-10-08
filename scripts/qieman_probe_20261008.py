# -*- coding: utf-8 -*-
"""2026-10-08 盘前档（档型③「正常交易日盘前」· A股 + 港股通 双市场复市首日）：且慢 REST pmdj 探针（三端点）
—— 连续第 105 个交易日空 body 预期
⚠️ 计数常量人工核对（§3.130d / §3.133c）：上一档（10/7 盘后）= 104
   ★10/8 为 **A股 交易日**（长假后复市首日）→ 依 §3.130d 规则①：本计数**推进 +1** → **105**
⚠️ 四类字面量核对（§3.121c）：读写路径 / 日期常量 / docstring 档型语义 / note 字段档型语义
"""
import json, os, urllib.request, ssl

ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
U = {
 "plan": "https://qieman.com/pmdj/v2/long-win/plan?prodCode=LONG_WIN",
 "nav": "https://qieman.com/pmdj/v2/long-win/plan/nav-history?prodCode=LONG_WIN",
 "adjustments": "https://qieman.com/pmdj/v2/long-win/plan/adjustments?desc=true&prodCode=LONG_WIN",
}
out = {"date": "2026-10-08", "session": "preopen-0800",
       "session_type": "normal_trading_day_preopen",
       "session_type_note": "档型③「正常交易日盘前」（A股 10/8 复市首日 + 港股 10/8 正常交易日；08:00 双方均无新价格）"}
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
json.dump(out, open("/Users/jieyang/Documents/WealthHub/data/processed/history/qieman_rest_20261008.json", "w",
                    encoding="utf-8"), ensure_ascii=False, indent=1)
print("已保存 qieman_rest_20261008.json")
