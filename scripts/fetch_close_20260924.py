# -*- coding: utf-8 -*-
"""2026-09-24 盘后：抓取收盘行情（新浪 hq 直连，两次调用拿全，§3.84/§3.87/§3.104）
注意 §3.99：永久移除 sh000922（中证红利）；§3.104：fund_etf_spot_em 连续 4 档失败 → 场内 ETF 一律走 hq 直连。
"""
import json, os, urllib.request

BASE = '/Users/jieyang/Documents/WealthHub'
HIST = os.path.join(BASE, 'data/processed/history')
TODAY = '2026-09-24'
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


def pct(cur, base):
    if not base:
        return 0.0
    return round((cur - base) / base * 100, 2)


# ---- 请求 1：A股指数 / 板块指数 / 个股 / 港股指数 ----
CODES_1 = ['sh000001', 'sz399001', 'sz399006', 'sh000300', 'sh000932', 'sh000933',
           'sz399989', 'sz399997', 'sh000688', 'sh000827', 'sh000934', 'sh000913',
           'sz399975',
           'sz002410', 'sh600438', 'sh600519']
txt1 = hq(CODES_1 + ['rt_hkHSI', 'rt_hkHSTECH', 'rt_hkHSCEI'])

data = {'date': TODAY, 'indices': [], 'boards': [], 'etf': [], 'stocks': [], 'hk': []}
skipped = []

BOARD_CODES = {'sh000933', 'sz399989', 'sz399997', 'sh000827', 'sh000934',
               'sh000913', 'sz399975'}

for line in txt1.split(';'):
    line = line.strip()
    if not line or '="' not in line:
        continue
    code = line.split('=')[0].replace('var hq_str_', '').strip()
    payload = line.split('="', 1)[1].rstrip('"')
    f = payload.split(',')
    if code.startswith('rt_hk'):
        if len(f) < 9 or not f[6]:
            skipped.append(code); continue
        data['hk'].append({'code': code.replace('rt_hk', ''), 'name': f[1],
                           'open': float(f[2]), 'prev': float(f[3]), 'high': float(f[4]),
                           'low': float(f[5]), 'close': float(f[6]), 'chg': float(f[7]),
                           'pct': float(f[8])})
    elif code.startswith(('sz002410', 'sh600438', 'sh600519')):
        if len(f) < 10 or not f[3] or not f[2]:
            skipped.append(code); continue
        close = float(f[3]); prev = float(f[2])
        data['stocks'].append({'code': code, 'name': f[0], 'open': float(f[1]),
                               'prev': prev, 'close': close, 'high': float(f[4]),
                               'low': float(f[5]), 'pct': pct(close, prev)})
    else:
        if len(f) < 10 or not f[3] or not f[2]:
            skipped.append(code); continue
        close = float(f[3]); prev = float(f[2])
        rec = {'code': code, 'name': f[0], 'open': float(f[1]),
               'prev': prev, 'close': close, 'high': float(f[4]),
               'low': float(f[5]), 'pct': pct(close, prev),
               'vol': f[8], 'amount': f[9]}
        (data['boards'] if code in BOARD_CODES else data['indices']).append(rec)

# ---- 请求 2：场内 ETF（持仓 9 只）----
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
    if len(f) < 10 or not f[3] or not f[2]:
        skipped.append(code); continue
    close = float(f[3]); prev = float(f[2])
    data['etf'].append({'code': code, 'name': f[0], 'open': float(f[1]), 'prev': prev,
                        'close': close, 'high': float(f[4]), 'low': float(f[5]),
                        'pct': pct(close, prev),
                        'vol': f[8], 'amount': f[9]})

json.dump(data, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('written', OUT)
print('skipped(空值剔除):', skipped)
print('--- indices', len(data['indices']))
for x in data['indices']:
    print(f"  {x['name']:10s} {x['code']:10s} close={x['close']:>10.2f} pct={x['pct']:+.2f}%  H/L={x['high']}/{x['low']}  amt={x['amount']}")
print('--- boards', len(data['boards']))
for x in data['boards']:
    print(f"  {x['name']:10s} {x['code']:10s} close={x['close']:>10.2f} pct={x['pct']:+.2f}%  H/L={x['high']}/{x['low']}")
print('--- hk', len(data['hk']))
for x in data['hk']:
    print(f"  {x['name']:10s} {x['code']:10s} close={x['close']:>10.2f} pct={x['pct']:+.2f}%  H/L={x['high']}/{x['low']}")
print('--- etf', len(data['etf']))
for x in data['etf']:
    print(f"  {x['name']:12s} {x['code']:10s} close={x['close']:>7.3f} pct={x['pct']:+.2f}%  amt={x['amount']}")
print('--- stocks', len(data['stocks']))
for x in data['stocks']:
    print(f"  {x['name']:10s} {x['code']:10s} close={x['close']:>9.2f} pct={x['pct']:+.2f}%")
