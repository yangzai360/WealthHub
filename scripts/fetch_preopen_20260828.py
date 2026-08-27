# -*- coding: utf-8 -*-
"""盘前档 2026-08-28(周五) 行情抓取：场外基金净值增量(8/27周四净值, 周五早盘全量可抓, QDII 8/26) + 隔夜美股 8/27(美东周四)收盘归档"""
import json, os, sys, time, csv

sys.path.insert(0, '/Users/jieyang/.workbuddy/binaries/python/envs/default/lib/python3.13/site-packages')
import akshare as ak

BASE = '/Users/jieyang/Documents/WealthHub'
HIST = os.path.join(BASE, 'data/processed/history')
TODAY = '2026-08-28'

def retry(fn, *args, times=3, **kwargs):
    for i in range(times):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            if i == times - 1:
                print(f'  FAIL {fn.__name__} {args}: {e}')
                return None
            time.sleep(2)

# ---------- 1. 场外基金净值增量（8/27 周四净值，周五早盘全量可抓，QDII T+1~T+2 至 8/26） ----------
fund_map = {
    '002708': '大摩健康产业混合A', '000968': '广发养老产业', '002742': '泓德裕祥债券A',
    '004752': '广发传媒ETF联接A', '005368': '富国清洁能源', '110020': '易方达沪深300',
    '000369': '广发全球医疗A', '100032': '富国红利增强A', '001180': '广发医药卫生',
    '161616': '融通医疗保健', '000051': '华夏沪深300', '519915': '富国消费主题',
    '000071': '华夏恒生ETF联接A', '012348': '天弘恒生科技A', '001551': '天弘医药100C',
    '164906': '交银海外互联', '000248': '汇添富主要消费A', '016280': '广发全球医疗C',
    '001469': '广发金融地产', '001552': '天弘证券保险', '012323': '华宝中证医疗C',
    '000727': '融通健康产业A/B', '004424': '汇添富文体娱乐',
}
existing = set()
csv_path = os.path.join(HIST, 'fund_nav.csv')
with open(csv_path, encoding='utf-8-sig') as f:
    for row in csv.DictReader(f):
        existing.add((row['code'], row['nav_date']))

new_rows = []
for code, nm in fund_map.items():
    df = retry(ak.fund_open_fund_info_em, symbol=code, indicator='单位净值走势')
    if df is None or len(df) < 1:
        print(f'  WARN 基金 {nm} {code} 净值暂缺')
        continue
    last = df.iloc[-1]
    nav_date = str(last['净值日期'])[:10]
    nav = float(last['单位净值'])
    pct = last['日增长率']
    try:
        pct = float(pct)
    except:
        pct = None
    if (code, nav_date) in existing:
        print(f'  SKIP {nm}: {nav_date} 已存在')
        continue
    new_rows.append([TODAY, code, nm, nav_date, str(nav), str(round(pct, 2)) if pct is not None else ''])
    existing.add((code, nav_date))
    print(f'  NEW {nm}: nav_date={nav_date} nav={nav} pct={pct}')

with open(csv_path, 'a', encoding='utf-8-sig') as f:
    for r in new_rows:
        f.write(','.join(r) + '\n')
print(f'fund_nav.csv 新增 {len(new_rows)} 行')

# ---------- 2. 隔夜美股 8/27(美东周四) 收盘归档 ----------
def fetch_us_etf(symbol, name, note='美股收盘'):
    df = retry(ak.stock_us_daily, symbol=symbol)
    if df is None or len(df) < 2:
        print(f'  WARN {name} {symbol} 数据暂缺')
        return None
    last2 = df.tail(2)
    close = float(last2.iloc[-1]['close'])
    prev = float(last2.iloc[-2]['close'])
    pct = (close / prev - 1) * 100
    d = str(last2.iloc[-1]['date'])[:10]
    return [d, symbol, name, str(round(close, 2)), str(round(pct, 2)), note]

def fetch_us_index(symbol, name):
    df = retry(ak.index_us_stock_sina, symbol=symbol)
    if df is None or len(df) < 2:
        print(f'  WARN 指数 {name} {symbol} 数据暂缺')
        return None
    last2 = df.tail(2)
    close = float(last2.iloc[-1]['close'])
    prev = float(last2.iloc[-2]['close'])
    pct = (close / prev - 1) * 100
    d = str(last2.iloc[-1]['date'])[:10]
    return [d, symbol, name, str(round(close, 2)), str(round(pct, 2)), '美股收盘']

us_rows = []
for sym, nm in [('XLV', '医疗保健ETF'), ('IYH', '美股医疗IYH'), ('QQQ', '纳指100ETF'), ('DIA', '道指ETF')]:
    r = fetch_us_etf(sym, nm)
    if r:
        us_rows.append(['us_index'] + r)
        print(f'  [美股ETF] {nm} {r[0]} close={r[3]} pct={r[4]}%')
for sym, nm in [('.IXIC', '纳斯达克'), ('.DJI', '道琼斯')]:
    r = fetch_us_index(sym, nm)
    if r:
        us_rows.append(['us_index'] + r)
        print(f'  [美股指数] {nm} {r[0]} close={r[3]} pct={r[4]}%')

# 增量写入 indices.csv（按 (code,date,note) 判重）
existing_idx = set()
idx_path = os.path.join(HIST, 'indices.csv')
with open(idx_path, encoding='utf-8-sig') as f:
    for row in csv.DictReader(f):
        existing_idx.add((row['code'], row['date'], row['note']))
added = 0
with open(idx_path, 'a', encoding='utf-8-sig') as f:
    for r in us_rows:
        key = (r[2], r[1], r[5])
        if key in existing_idx:
            print(f'  SKIP {r[2]}: 已存在')
            continue
        f.write(','.join(r) + '\n')
        existing_idx.add(key)
        added += 1
print(f'indices.csv 新增美股 {added} 行')

# ---------- 3. 验证 A股/港股 8/27 收盘已在库 ----------
with open(idx_path, encoding='utf-8-sig') as f:
    for row in csv.DictReader(f):
        if row['date'].startswith('2026-08-27') and '收盘' in row.get('note', ''):
            print(f"  [已归档] {row['name']} {row['date']} close={row['close']} pct={row.get('pct', '')}%")

# ---------- 4. 且慢 pmdj 复测（第 33 日, 预期空 body 标注即可） ----------
try:
    import urllib.request
    req = urllib.request.Request('https://qieman.com/pmdj/v2/long-win/plan?prodCode=LONG_WIN',
                                 headers={'Referer': 'https://qieman.com/'})
    with urllib.request.urlopen(req, timeout=20) as resp:
        body = resp.read()
        print(f'  qieman pmdj plan: HTTP {resp.status} SIZE={len(body)}')
except Exception as e:
    print(f'  qieman pmdj plan: FAIL {e}')
