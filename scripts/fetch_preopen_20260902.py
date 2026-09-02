# -*- coding: utf-8 -*-
"""盘前档 2026-09-02(周三) 行情抓取：场外基金净值增量(9/1周二净值, 周三早盘全量可抓, QDII T+1~T+2至8/31) + 美股9/1(美东周二)收盘新抓 + ETF 9/1收盘"""
import json, os, sys, time, csv

sys.path.insert(0, '/Users/jieyang/.workbuddy/binaries/python/envs/default/lib/python3.13/site-packages')
import akshare as ak

BASE = '/Users/jieyang/Documents/WealthHub'
HIST = os.path.join(BASE, 'data/processed/history')
TODAY = '2026-09-02'

def retry(fn, *args, times=3, **kwargs):
    for i in range(times):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            if i == times - 1:
                print(f'  FAIL {fn.__name__} {args}: {e}')
                return None
            time.sleep(2)

# ---------- 1. 场外基金净值增量（9/1 周二净值，周三早盘全量可抓，QDII T+1~T+2） ----------
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

# ---------- 2. 美股 9/1(美东周二) 收盘新抓 ----------
idx_path = os.path.join(HIST, 'indices.csv')
existing_idx = set()
with open(idx_path, encoding='utf-8-sig') as f:
    for row in csv.DictReader(f):
        existing_idx.add((row['type'], row['date'][:10], row['code']))

us_rows = []
for sym, nm in [('XLV', '美股医疗XLV'), ('IYH', '美股医疗IYH'), ('QQQ', '纳指100ETF'), ('DIA', '道指ETF')]:
    df = retry(ak.stock_us_daily, symbol=sym)
    if df is None or len(df) < 2:
        print(f'  WARN {sym} 数据暂缺')
        continue
    dates = [str(d)[:10] for d in df['date'].tolist()]
    closes = df['close'].tolist()
    last_date = dates[-1]
    pct = None
    if len(closes) >= 2 and closes[-2] not in (None, 0):
        pct = round((closes[-1] / closes[-2] - 1) * 100, 2)
    if ('us_index', last_date, sym) in existing_idx:
        print(f'  SKIP {nm} {sym}: {last_date} 已存在 close={closes[-1]} pct={pct}')
        continue
    us_rows.append(['us_index', last_date, nm, sym, str(closes[-1]), str(pct) if pct is not None else '', '美股收盘'])
    existing_idx.add(('us_index', last_date, sym))
    print(f'  NEW {nm} {sym}: {last_date} close={closes[-1]} pct={pct}%')

for sym, nm in [('.IXIC', '纳斯达克'), ('.DJI', '道琼斯'), ('.INX', '标普500')]:
    df = retry(ak.index_us_stock_sina, symbol=sym)
    if df is None or len(df) < 2:
        print(f'  WARN 指数 {sym} 数据暂缺')
        continue
    dates = [str(d)[:10] for d in df['date'].tolist()]
    closes = df['close'].tolist()
    last_date = dates[-1]
    pct = None
    if len(closes) >= 2 and closes[-2] not in (None, 0):
        pct = round((closes[-1] / closes[-2] - 1) * 100, 2)
    if ('us_index', last_date, sym) in existing_idx:
        print(f'  SKIP {nm} {sym}: {last_date} 已存在 close={closes[-1]} pct={pct}')
        continue
    us_rows.append(['us_index', last_date, nm, sym, str(closes[-1]), str(pct) if pct is not None else '', '美股收盘'])
    existing_idx.add(('us_index', last_date, sym))
    print(f'  NEW {nm} {sym}: {last_date} close={closes[-1]} pct={pct}%')

with open(idx_path, 'a', encoding='utf-8-sig') as f:
    for r in us_rows:
        f.write(','.join(r) + '\n')
print(f'indices.csv 新增美股 {len(us_rows)} 行')

# ---------- 3. 场内 ETF 9/1 收盘（盘前抓取返回上一交易日收盘） ----------
print('\n--- 场内 ETF 9/1 收盘 ---')
etf_out = {}
try:
    df = retry(ak.fund_etf_spot_em, times=2)
    if df is not None and len(df) > 0:
        for code6 in ['513050', '159928', '512170', '513180', '515180', '159920', '512880', '512980', '159938']:
            sub = df[df['代码'] == code6]
            if len(sub):
                r = sub.iloc[0]
                price = float(r['最新价'])
                pct = float(r['涨跌幅'])
                etf_out[code6] = {'price': price, 'pct': pct}
                print(f'  {code6} {r["名称"]}: {price} ({pct}%)')
    else:
        print('  ETF spot 空返回')
except Exception as e:
    print(f'  ETF spot FAIL: {e}')
with open(os.path.join(HIST, 'etf_close_20260902.json'), 'w', encoding='utf-8') as f:
    json.dump(etf_out, f, ensure_ascii=False, indent=1)

# ---------- 4. 港股 spot 盘前尝试 ----------
print('\n--- 港股 spot 盘前 ---')
try:
    df = retry(ak.stock_hk_index_spot_sina, times=2)
    if df is not None and len(df) > 0:
        for _, r in df.iterrows():
            nm = str(r['名称'])
            if '恒生科技' in nm or ('恒生' in nm and '指数' in nm):
                print(f"  {nm}: {r['最新价']} ({r['涨跌幅']}%)")
    else:
        print('  港股 spot 盘前空返回')
except Exception as e:
    print(f'  港股 spot FAIL: {e}')

# ---------- 5. 且慢 pmdj 复测 ----------
try:
    import urllib.request
    req = urllib.request.Request('https://qieman.com/pmdj/v2/long-win/plan?prodCode=LONG_WIN',
                                 headers={'Referer': 'https://qieman.com/'})
    with urllib.request.urlopen(req, timeout=20) as resp:
        body = resp.read()
        print(f'  qieman pmdj plan: HTTP {resp.status} SIZE={len(body)}')
except Exception as e:
    print(f'  qieman pmdj plan: FAIL {e}')

print('\nDONE fetch_preopen_20260902')
