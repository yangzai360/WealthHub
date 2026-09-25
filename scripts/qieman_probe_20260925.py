# -*- coding: utf-8 -*-
"""2026-09-25 盘后：且慢 LONG_WIN（E大）参考组合抓取
① 先试 REST pmdj（连续 91 日空 body，预期仍空）
② 空则浏览器渲染兜底
输出：reference-portfolios/long-win/qieman-20260925.json
"""
import json, os, urllib.request, ssl, sys

BASE = '/Users/jieyang/Documents/WealthHub'
TODAY = '2026-09-25'
ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
HDR = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
       'Referer': 'https://qieman.com/'}

urls = {
    'plan': 'https://qieman.com/pmdj/v2/long-win/plan?key=LONG_WIN',
    'nav': 'https://qieman.com/pmdj/v2/long-win/nav-history?key=LONG_WIN',
    'adjust': 'https://qieman.com/pmdj/v2/long-win/adjustments?key=LONG_WIN',
}
res = {}
for k, u in urls.items():
    try:
        req = urllib.request.Request(u, headers=HDR)
        with urllib.request.urlopen(req, timeout=25, context=ctx) as r:
            b = r.read()
        res[k] = {'bytes': len(b), 'json': (json.loads(b.decode('utf-8')) if b.strip() else None)}
        print(f'  REST {k}: {len(b)} bytes')
    except Exception as e:
        res[k] = {'bytes': 0, 'error': str(e)}
        print(f'  REST {k}: FAIL {e}')

empty = all(res[k]['bytes'] == 0 for k in res)
print(f'\nREST 全空 body? {empty}')
json.dump({'date': TODAY, 'rest': {k: {kk: vv for kk, vv in v.items() if kk != 'json'} for k, v in res.items()},
           'rest_all_empty': bool(empty)},
          open(os.path.join(BASE, f'data/processed/history/qieman_rest_{TODAY.replace("-","")}.json'), 'w',
               encoding='utf-8'), ensure_ascii=False, indent=1)
