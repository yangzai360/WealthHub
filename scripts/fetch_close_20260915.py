# -*- coding: utf-8 -*-
"""2026-09-15 盘后：抓取收盘行情（新浪 hq 直连，一次调用拿全，§3.84 推荐做法）"""
import json, os, re, urllib.request

BASE = '/Users/jieyang/Documents/WealthHub'
HIST = os.path.join(BASE, 'data/processed/history')
TODAY = '2026-09-15'
OUT = os.path.join(HIST, 'close_' + TODAY.replace('-', '') + '.json')

HDR = {'Referer': 'https://finance.sina.com.cn/', 'User-Agent': 'Mozilla/5.0'}


def hq(codes):
    url = 'https://hq.sinajs.cn/list=' + ','.join(codes)
    req = urllib.request.Request(url, headers=HDR)
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                return r.read().decode('gbk', errors='replace')
        except Exception as e:
            print('retry', attempt, e)
    return ''


# ---- A股指数 / 港股指数 / 个股 ----
CODES_1 = ['sh000001', 'sz399001', 'sz399006', 'sh000300', 'sh000932', 'sh000933',
           'sz399989', 'sz399997', 'sh000688', 'sh000827',
           'sz002410', 'sh600438', 'sh600519']
txt1 = hq(CODES_1 + ['rt_hkHSI', 'rt_hkHSTECH'])

data = {'date': TODAY, 'indices': [], 'etf': [], 'stocks': [], 'hk': []}

for line in txt1.split(';'):
    line = line.strip()
    if not line or '="' not in line:
        continue
    code = line.split('=')[0].replace('var hq_str_', '').strip()
    payload = line.split('="', 1)[1].rstrip('"')
    f = payload.split(',')
    if code.startswith('rt_hk'):
        if len(f) < 9:
            continue
        data['hk'].append({'code': code.replace('rt_hk', ''), 'name': f[1],
                           'open': float(f[2]), 'prev': float(f[3]), 'high': float(f[4]),
                           'low': float(f[5]), 'close': float(f[6]), 'chg': float(f[7]),
                           'pct': float(f[8])})
    elif code.startswith('sz002410') or code.startswith('sh600438') or code.startswith('sh600519'):
        if len(f) < 10:
            continue
        close = float(f[3]); prev = float(f[2])
        data['stocks'].append({'code': code, 'name': f[0], 'open': float(f[1]),
                               'prev': prev, 'close': close, 'high': float(f[4]),
                               'low': float(f[5]), 'pct': round((close - prev) / prev * 100, 2)})
    else:
        if len(f) < 10:
            continue
        close = float(f[3]); prev = float(f[2])
        data['indices'].append({'code': code, 'name': f[0], 'open': float(f[1]),
                                'prev': prev, 'close': close, 'high': float(f[4]),
                                'low': float(f[5]), 'pct': round((close - prev) / prev * 100, 2),
                                'vol': f[8], 'amount': f[9]})

# ---- 场内 ETF（持仓 9 只）----
ETFS = ['sh513050', 'sz159928', 'sz159938', 'sh512170', 'sh513180',
        'sz159920', 'sh512880', 'sh512980', 'sh515180']
txt2 = hq(ETFS)
for line in txt2.split(';'):
    line = line.strip()
    if not line or '="' not in line:
        continue
    code = line.split('=')[0].replace('var hq_str_', '').strip()
    payload = line.split('="', 1)[1].rstrip('"')
    f = payload.split(',')
    if len(f) < 10:
        continue
    close = float(f[3]); prev = float(f[2])
    data['etf'].append({'code': code, 'name': f[0], 'open': float(f[1]), 'prev': prev,
                        'close': close, 'high': float(f[4]), 'low': float(f[5]),
                        'pct': round((close - prev) / prev * 100, 2),
                        'vol': f[8], 'amount': f[9]})

json.dump(data, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('written', OUT)
print('--- indices', len(data['indices']))
for x in data['indices']:
    print(f"  {x['name']:10s} {x['code']:10s} close={x['close']:>10.2f} pct={x['pct']:+.2f}%  H/L={x['high']}/{x['low']}  amt={x['amount']}")
print('--- hk', len(data['hk']))
for x in data['hk']:
    print(f"  {x['name']:10s} {x['code']:10s} close={x['close']:>10.2f} pct={x['pct']:+.2f}%  H/L={x['high']}/{x['low']}")
print('--- etf', len(data['etf']))
for x in data['etf']:
    print(f"  {x['name']:12s} {x['code']:10s} close={x['close']:>7.3f} pct={x['pct']:+.2f}%  amt={x['amount']}")
print('--- stocks', len(data['stocks']))
for x in data['stocks']:
    print(f"  {x['name']:10s} {x['code']:10s} close={x['close']:>9.2f} pct={x['pct']:+.2f}%")
