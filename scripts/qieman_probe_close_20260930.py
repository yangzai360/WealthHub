# -*- coding: utf-8 -*-
"""2026-09-30 盘后：且慢 LONG_WIN（E大）REST 探测（预期连续第 97 日空 body）"""
import json, os, urllib.request, ssl

BASE = '/Users/jieyang/Documents/WealthHub'
TODAY = '2026-09-30'
ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
HDR = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
       'Referer': 'https://qieman.com/'}

urls = {
    'plan': 'https://qieman.com/pmdj/v2/long-win/plan?key=LONG_WIN',
    'nav': 'https://qieman.com/pmdj/v2/long-win/nav-history?key=LONG_WIN',
    'adjust_i': 'https://qieman.com/pmdj/v2/long-win/plan/adjustments?desc=true&prodCode=LONG_WIN',
}
res = {}
for k, u in urls.items():
    try:
        req = urllib.request.Request(u, headers=HDR)
        with urllib.request.urlopen(req, timeout=25, context=ctx) as r:
            b = r.read()
        res[k] = {'bytes': len(b)}
        print(f'  REST {k}: {len(b)} bytes')
    except Exception as e:
        res[k] = {'bytes': 0, 'error': str(e)}
        print(f'  REST {k}: FAIL {e}')

empty = all(v['bytes'] == 0 for v in res.values())
print(f'\nREST 全空 body? {empty}')
json.dump({'date': TODAY, 'rest': res, 'rest_all_empty': bool(empty)},
          open(os.path.join(BASE, f'data/processed/history/qieman_rest_close_{TODAY.replace("-","")}.json'), 'w',
               encoding='utf-8'), ensure_ascii=False, indent=1)
