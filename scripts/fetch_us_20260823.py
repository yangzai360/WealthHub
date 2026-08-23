# -*- coding: utf-8 -*-
"""周日(8/23)盘后档:抓取美股 8/21(美东周五)收盘数据,归档 indices.csv,回填美股医药遗留事件"""
import sys, os, csv
sys.path.insert(0, os.path.dirname(__file__))
import akshare as ak

INDICES_CSV = '/Users/jieyang/Documents/WealthHub/data/processed/history/indices.csv'

def fetch_us_etf(symbol):
    for i in range(3):
        try:
            df = ak.stock_us_daily(symbol=symbol)
            last = df.iloc[-1]
            prev = df.iloc[-2]
            date = str(last['date'])
            close = float(last['close'])
            pct = (close / float(prev['close']) - 1) * 100
            return date, close, pct
        except Exception as e:
            if i == 2:
                print(f'[FAIL] {symbol}: {e}')
                return None
    return None

def fetch_us_index(symbol):
    for i in range(3):
        try:
            df = ak.index_us_stock_sina(symbol=symbol)
            last = df.iloc[-1]
            prev = df.iloc[-2]
            date = str(last['date'])
            close = float(last['close'])
            pct = (close / float(prev['close']) - 1) * 100
            return date, close, pct
        except Exception as e:
            if i == 2:
                print(f'[FAIL] {symbol}: {e}')
            return None
    return None

def main():
    # 读取已存在行(key: code+date+note)
    existing = set()
    with open(INDICES_CSV, encoding='utf-8-sig') as f:
        for row in csv.DictReader(f):
            existing.add((row['code'], row['date'], row['note']))

    results = []
    # ETF 代理
    for sym, name, code in [('XLV', '医疗保健ETF', 'XLV'), ('IYH', '美股医疗IYH', 'IYH'),
                            ('QQQ', '纳指100ETF', 'QQQ'), ('DIA', '道指ETF', 'DIA')]:
        r = fetch_us_etf(sym)
        if r:
            date, close, pct = r
            results.append(('us_index', date, name, code, close, pct, '美股收盘'))
            print(f'{sym}: {date} {close} ({pct:+.2f}%)')
        else:
            print(f'{sym}: 抓取失败')

    # 美股指数
    for sym, name, code in [('.IXIC', '纳斯达克', '.IXIC'), ('.DJI', '道琼斯', '.DJI')]:
        r = fetch_us_index(sym)
        if r:
            date, close, pct = r
            results.append(('us_index', date, name, code, close, pct, '美股收盘'))
            print(f'{sym}: {date} {close} ({pct:+.2f}%)')

    # 增量写入
    added = 0
    with open(INDICES_CSV, 'a', encoding='utf-8', newline='') as f:
        w = csv.writer(f)
        for typ, date, name, code, close, pct, note in results:
            key = (code, date, note)
            if key in existing:
                print(f'[SKIP] 已存在: {code} {date} {note}')
                continue
            w.writerow([typ, date, name, code, f'{close:.2f}', f'{pct:.2f}', note])
            added += 1
            existing.add(key)
    print(f'新增 {added} 行')

if __name__ == '__main__':
    main()
