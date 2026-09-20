# -*- coding: utf-8 -*-
"""2026-09-20 周日盘后档（非交易日）行情抓取:
   ① 归档美股 2026-09-18（美东周五）收盘：XLV/IYH/QQQ/DIA/SPY 五 ETF + .IXIC/.DJI/.INX 三指数（§3.91 推荐集合）
   ② 场外基金最新净值（天天基金 F10 直连，§3.79）：兜底 9/18 未出标的 + QDII T+1
   A股/港股非交易日跳过。
   输出 data/processed/history/close_20260920.json
"""
import json, os, time, urllib.request
from collections import Counter

BASE = '/Users/jieyang/Documents/WealthHub'
HIST = os.path.join(BASE, 'data/processed/history')
TODAY = '2026-09-20'
OUT = os.path.join(HIST, 'close_' + TODAY.replace('-', '') + '.json')

import akshare as ak

result = {'date': TODAY, 'us': [], 'fund_navs': [],
          'note': '非交易日(周日)，归档美股9/18收盘 + 场外基金净值兜底'}


def retry(fn, n=2, desc=''):
    for i in range(n + 1):
        try:
            return fn()
        except Exception as e:
            print(f'  [{desc}] 第{i+1}次失败: {e}')
            time.sleep(2)
    return None


# ---------- ① 美股 ETF 日线（新浪源）----------
us_etfs = {
    'XLV': '美股医疗ETF(XLV)', 'IYH': '美股医疗IYH', 'QQQ': '纳指100ETF(QQQ)',
    'DIA': '道指ETF(DIA)', 'SPY': '标普500ETF(SPY)',
}
for sym, name in us_etfs.items():
    def _f(sym=sym):
        return ak.stock_us_daily(symbol=sym).tail(3)
    df = retry(_f, desc=f'美股ETF {sym}')
    if df is not None and len(df) >= 2:
        prev_c, cur_c = float(df.iloc[-2]['close']), float(df.iloc[-1]['close'])
        pct = round((cur_c / prev_c - 1) * 100, 2)
        d = str(df.iloc[-1]['date'])[:10]
        result['us'].append({'type': 'us_index', 'name': name, 'code': sym,
                             'close': round(cur_c, 2), 'pct_change': pct,
                             'note': f'美股{d}收盘(非交易日归档)'})
        print(f'  US {sym:5s} 行情日={d} close={round(cur_c,2):>9.2f} pct={pct:+.2f}%')
    else:
        print(f'  US {sym} 数据暂缺')
        result['us'].append({'type': 'us_index', 'name': name, 'code': sym,
                             'close': None, 'pct_change': None, 'note': '数据暂缺'})

# ---------- ② 美股官方指数（新浪源）----------
us_idx = {'.IXIC': '纳斯达克', '.DJI': '道琼斯', '.INX': '标普500'}
for sym, name in us_idx.items():
    def _f(sym=sym):
        return ak.index_us_stock_sina(symbol=sym).tail(3)
    df = retry(_f, desc=f'美股指数 {sym}')
    if df is not None and len(df) >= 2:
        prev_c, cur_c = float(df.iloc[-2]['close']), float(df.iloc[-1]['close'])
        pct = round((cur_c / prev_c - 1) * 100, 2)
        d = str(df.iloc[-1]['date'])[:10]
        result['us'].append({'type': 'us_index', 'name': name, 'code': sym,
                             'close': round(cur_c, 2), 'pct_change': pct,
                             'note': f'美股{d}收盘(非交易日归档)'})
        print(f'  USIDX {sym:6s} 行情日={d} close={round(cur_c,2):>10.2f} pct={pct:+.2f}%')
    else:
        print(f'  USIDX {sym} 数据暂缺')

# ---------- ③ 场外基金净值（天天基金 F10 直连）----------
funds = [
    ('002708', '大摩健康产业混合A'), ('000968', '广发养老产业'), ('002742', '泓德裕祥债券A'),
    ('004752', '广发传媒联接A'), ('005368', '富国清洁能源'), ('110020', '易方达沪深300联接'),
    ('000369', '广发全球医疗A'), ('100032', '富国红利增强A'), ('001180', '广发医药卫生'),
    ('161616', '融通医疗保健'), ('000051', '华夏沪深300联接'), ('519915', '富国消费主题'),
    ('000071', '华夏恒生ETF联接A'), ('012348', '天弘恒生科技A'), ('001551', '天弘医药100C'),
    ('164906', '交银海外互联A'), ('000248', '汇添富主要消费A'), ('016280', '广发全球医疗C'),
    ('001469', '广发金融地产'), ('001552', '天弘证券保险'), ('012323', '华宝中证医疗C'),
    ('000727', '融通健康产业A/B'), ('004424', '汇添富文体娱乐'),
]


def f10_nav(code, size=8):
    url = f'https://api.fund.eastmoney.com/f10/lsjz?fundCode={code}&pageIndex=1&pageSize={size}'
    req = urllib.request.Request(url, headers={
        'Referer': 'https://fundf10.eastmoney.com/',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode('utf-8'))


fail = []
for code, name in funds:
    d = None
    for i in range(3):
        try:
            d = f10_nav(code)
            break
        except Exception as e:
            print(f'  [{name}] 第{i+1}次失败 {e}')
            time.sleep(2)
    if d and d.get('Data') and d['Data'].get('LSJZList'):
        rows = d['Data']['LSJZList']
        for r in rows:
            nd = str(r.get('FSRQ', ''))[:10]
            try:
                nav = round(float(r.get('DWJZ')), 4)
            except Exception:
                continue
            pr = r.get('JZZZL')
            try:
                p = float(pr) if pr not in ('', None) else None
            except Exception:
                p = None
            result['fund_navs'].append({'code': code, 'name': name, 'nav_date': nd,
                                        'nav': nav, 'pct': p})
        print(f'  {name}({code}) 最新 {rows[0].get("FSRQ")} {rows[0].get("DWJZ")} {rows[0].get("JZZZL")}%')
    else:
        fail.append((code, name))
        print(f'  {name}({code}) 抓取失败/无数据')

json.dump(result, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

c = Counter(n['nav_date'] for n in result['fund_navs'] if n['nav_date'] >= '2026-09-16')
print('\n净值日分布(>=9/16):', dict(c))
latest = {}
for n in result['fund_navs']:
    if n['code'] not in latest or n['nav_date'] > latest[n['code']]['nav_date']:
        latest[n['code']] = n
c2 = Counter(v['nav_date'] for v in latest.values())
print('各基金最新净值日分布:', dict(c2))
for n in sorted(latest.values(), key=lambda x: (x['nav_date'], x['code'])):
    print(f"  {n['nav_date']}  {n['name']:20s} {n['code']} {n['nav']:.4f} {'' if n['pct'] is None else format(n['pct'], '+.2f')}%")
print(f'\n抓取失败 {len(fail)} 只: {fail}')
print(f'SAVED {OUT}  us={len(result["us"])}  fund_navs={len(result["fund_navs"])}')
