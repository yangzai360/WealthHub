# -*- coding: utf-8 -*-
"""周日(8/30)盘后档:抓取美股 8/28(美东周五)收盘数据,归档 indices.csv
- 修复 8/28 盘前误标日期行: XLV 171.58(-1.13%) 实为 8/27 收盘, 改日期为 2026-08-27
- 补录 IYH 8/27 收盘(72.63, -1.05%)
- 增量写入 XLV/IYH/QQQ/DIA/.IXIC/.DJI 8/28 收盘"""
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
            date = str(last['date'])[:10]
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
            date = str(last['date'])[:10]
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
    rows = []
    with open(INDICES_CSV, encoding='utf-8-sig') as f:
        for row in csv.DictReader(f):
            rows.append(row)

    # 1) 修复误标日期行: XLV 2026-08-28 171.58 -1.13 新闻口径 -> 2026-08-27
    fixed = 0
    for r in rows:
        if r['code'] == 'XLV' and r['date'] == '2026-08-28' and '新闻口径' in r['note']:
            r['date'] = '2026-08-27'
            fixed += 1
    print(f'修复误标 XLV 行: {fixed}')

    existing = {(r['code'], r['date'], r['note']) for r in rows}

    def add(typ, date, name, code, close, pct, note):
        key = (code, date, note)
        if key in existing:
            print(f'[SKIP] 已存在: {code} {date} {note}')
            return False
        rows.append({'type': typ, 'date': date, 'name': name, 'code': code,
                     'close': f'{close:.2f}', 'pct_change': f'{pct:.2f}', 'note': note})
        existing.add(key)
        return True

    added = 0
    # 2) 补录 IYH 8/27 (72.63, -1.05%)
    if add('us_index', '2026-08-27', '美股医疗IYH', 'IYH', 72.63, -1.05, '美股收盘'):
        added += 1
        print('补录 IYH 8/27: 72.63 (-1.05%)')

    # 3) 8/28 收盘增量
    for sym, name in [('XLV', '医疗保健ETF'), ('IYH', '美股医疗IYH'), ('QQQ', '纳指100ETF'), ('DIA', '道指ETF')]:
        r = fetch_us_etf(sym)
        if r:
            date, close, pct = r
            if add('us_index', date, name, sym, close, pct, '美股收盘'):
                added += 1
            print(f'{sym}: {date} {close:.2f} ({pct:+.2f}%)')
        else:
            print(f'{sym}: 抓取失败')

    for sym, name in [('.IXIC', '纳斯达克'), ('.DJI', '道琼斯')]:
        r = fetch_us_index(sym)
        if r:
            date, close, pct = r
            if add('us_index', date, name, sym, close, pct, '美股收盘'):
                added += 1
            print(f'{sym}: {date} {close:.2f} ({pct:+.2f}%)')
        else:
            print(f'{sym}: 抓取失败')

    # 写回(保持表头顺序)
    header = ['type', 'date', 'name', 'code', 'close', 'pct_change', 'note']
    with open(INDICES_CSV, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=header)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, '') for k in header})
    print(f'\n新增 {added} 行, 总行数 {len(rows)}')

if __name__ == '__main__':
    main()
