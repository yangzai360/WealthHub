# -*- coding: utf-8 -*-
"""2026-09-13 周日盘后档（非交易日）行情抓取:
   仅归档美股 2026-09-11（美东周五）收盘数据（A股/港股/场外基金非交易日跳过）
   输出 data/processed/history/close_20260913.json
"""
import json, os, time

BASE = '/Users/jieyang/Documents/WealthHub'
HIST = os.path.join(BASE, 'data/processed/history')
TODAY = '2026-09-13'
OUT = os.path.join(HIST, f'close_{TODAY.replace("-", "")}.json')

import akshare as ak

result = {'date': TODAY, 'us': [], 'note': '非交易日(周日)，仅归档美股9/11收盘'}


def retry(fn, n=2, desc=''):
    for i in range(n + 1):
        try:
            return fn()
        except Exception as e:
            print(f'  [{desc}] 第{i+1}次失败: {e}')
            time.sleep(2)
    return None


# ---------- 美股 ETF 日线（新浪源）----------
us_etfs = {
    'XLV': ('美股医疗ETF(XLV)', 'XLV'),
    'IYH': ('美股医疗IYH', 'IYH'),
    'QQQ': ('纳指100ETF(QQQ)', 'QQQ'),
    'DIA': ('道指ETF(DIA)', 'DIA'),
}
for sym, (name, code) in us_etfs.items():
    def _f(sym=sym):
        df = ak.stock_us_daily(symbol=sym)
        return df.tail(2)
    df = retry(_f, desc=f'美股ETF {sym}')
    if df is not None and len(df) >= 2:
        prev_c, cur_c = float(df.iloc[-2]['close']), float(df.iloc[-1]['close'])
        pct = round((cur_c / prev_c - 1) * 100, 2)
        d = str(df.iloc[-1]['date'])[:10]
        result['us'].append({'type': 'us_index', 'date': TODAY, 'name': name, 'code': code,
                             'close': round(cur_c, 2), 'pct_change': pct,
                             'note': f'美股{d}收盘(非交易日归档)'})
        print(f'  US {sym} 数据日期={d} close={round(cur_c,2)} pct={pct}%')
    else:
        print(f'  US {sym} 数据暂缺')
        result['us'].append({'type': 'us_index', 'date': TODAY, 'name': name, 'code': code,
                             'close': None, 'pct_change': None, 'note': '数据暂缺'})

# ---------- 美股指数（新浪源）----------
us_idx = {
    '.IXIC': ('纳斯达克', '.IXIC'),
    '.DJI': ('道琼斯', '.DJI'),
    '.INX': ('标普500', '.INX'),
}
for sym, (name, code) in us_idx.items():
    def _f(sym=sym):
        df = ak.index_us_stock_sina(symbol=sym)
        return df.tail(2)
    df = retry(_f, desc=f'美股指数 {sym}')
    if df is not None and len(df) >= 2:
        prev_c, cur_c = float(df.iloc[-2]['close']), float(df.iloc[-1]['close'])
        pct = round((cur_c / prev_c - 1) * 100, 2)
        d = str(df.iloc[-1]['date'])[:10]
        result['us'].append({'type': 'us_index', 'date': TODAY, 'name': name, 'code': code,
                             'close': round(cur_c, 2), 'pct_change': pct,
                             'note': f'美股{d}收盘(非交易日归档)'})
        print(f'  US {sym} 数据日期={d} close={round(cur_c,2)} pct={pct}%')
    else:
        print(f'  US {sym} 数据暂缺（间歇 IndexError 属已知，代理口径处理）')

with open(OUT, 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=1)
print(f'\nSAVED {OUT}')
print(f'us rows {len(result["us"])}')
