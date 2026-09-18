# -*- coding: utf-8 -*-
"""盘前档 2026-09-18(周五) 行情抓取:
1) 场外基金净值增量 —— 天天基金 F10 直连(§3.79); 判重 key = (code, nav_date) 二元组(§3.86)
   fund_nav.csv 现状(实测): 无 BOM + 全 LF + 末行 LF -> 直接字节追加 '\n'
2) 美股(美东 9/17 周四收盘 = 隔夜, FOMC 后第 2 个交易日)
3) 港股 hq 直连(9/17 收盘) + A股指数日线(9/17 收盘) + 个股
4) 且慢 pmdj 复测
⚠️ 禁止整表行尾归一化(§3.87/§3.89): indices.csv 为混合行尾(796 CRLF + 855 LF), 仅按「末行 EOL」字节追加
"""
import json, os, sys, time, csv, urllib.request, socket

sys.path.insert(0, '/Users/jieyang/.workbuddy/binaries/python/envs/default/lib/python3.13/site-packages')
import akshare as ak

BASE = '/Users/jieyang/Documents/WealthHub'
HIST = os.path.join(BASE, 'data/processed/history')
TODAY = '2026-09-18'
socket.setdefaulttimeout(25)


def retry(fn, *args, times=3, **kwargs):
    for i in range(times):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            if i == times - 1:
                print(f'  FAIL {fn.__name__} {args}: {e}')
                return None
            time.sleep(2)


def append_rows(path, rows):
    """§3.87 固化: 字节追加, 新行 EOL 与「末行」一致; 禁止整表归一化"""
    with open(path, 'rb') as f:
        d = f.read()
    eol = b'\r\n' if d.endswith(b'\r\n') else b'\n'
    if not d.endswith(b'\n'):
        with open(path, 'ab') as f:
            f.write(b'\n')
    with open(path, 'ab') as f:
        for r in rows:
            f.write((','.join(str(x) for x in r)).encode('utf-8') + eol)
    print(f'  -> {os.path.basename(path)} 追加 {len(rows)} 行 (BOM={d[:3] == b"\xef\xbb\xbf"} EOL={eol!r})')


# ---------- 1. 场外基金净值增量 (F10 直连) ----------
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

csv_path = os.path.join(HIST, 'fund_nav.csv')
existing = set()
with open(csv_path, encoding='utf-8-sig') as f:
    for row in csv.DictReader(f):
        existing.add((row['code'], row['nav_date']))

HDRS = {'Referer': 'https://fundf10.eastmoney.com/', 'User-Agent': 'Mozilla/5.0'}


def fetch_f10(code):
    url = (f'https://api.fund.eastmoney.com/f10/lsjz?fundCode={code}'
           f'&pageIndex=1&pageSize=8')
    req = urllib.request.Request(url, headers=HDRS)
    with urllib.request.urlopen(req, timeout=20) as resp:
        d = json.loads(resp.read().decode('utf-8', errors='ignore'))
    lst = (d.get('Data') or {}).get('LSJZList') or []
    if not lst:
        return None
    r = lst[0]
    pct = r.get('JZZZL')
    try:
        pct = float(pct)
    except Exception:
        pct = None
    return str(r['FSRQ'])[:10], float(r['DWJZ']), pct


new_rows = []
for code, nm in fund_map.items():
    got = None
    for i in range(3):
        try:
            got = fetch_f10(code)
            break
        except Exception as e:
            if i == 2:
                print(f'  FAIL {nm} {code}: {e}')
            time.sleep(1)
    if not got:
        print(f'  WARN 基金 {nm} {code} 净值暂缺')
        continue
    nav_date, nav, pct = got
    if (code, nav_date) in existing:
        print(f'  SKIP {nm}: {nav_date} 已存在 (nav={nav})')
        continue
    new_rows.append([TODAY, code, nm, nav_date, str(round(nav, 4)),
                     str(round(pct, 2)) if pct is not None else ''])
    existing.add((code, nav_date))
    print(f'  NEW {nm}: nav_date={nav_date} nav={nav} pct={pct}')

if new_rows:
    append_rows(csv_path, new_rows)
print(f'fund_nav.csv 新增 {len(new_rows)} 行')

# ---------- 2. 美股: 美东 9/17 周四收盘 ----------
idx_path = os.path.join(HIST, 'indices.csv')
existing_idx = set()
with open(idx_path, encoding='utf-8-sig') as f:
    for row in csv.DictReader(f):
        existing_idx.add((row['type'], row['date'][:10], row['code']))

us_rows = []
for sym, nm in [('XLV', '美股医疗XLV'), ('IYH', '美股医疗IYH'),
                ('QQQ', '纳指100ETF'), ('DIA', '道指ETF'),
                ('SPY', '标普500ETF')]:
    df = retry(ak.stock_us_daily, symbol=sym)
    if df is None or len(df) < 2:
        print(f'  WARN {sym} 数据暂缺')
        continue
    dates = [str(d)[:10] for d in df['date'].tolist()]
    closes = df['close'].tolist()
    last_date = dates[-1]
    pct = round((closes[-1] / closes[-2] - 1) * 100, 2) if closes[-2] else None
    if ('us_index', last_date, sym) in existing_idx:
        print(f'  SKIP {nm} {sym}: {last_date} 已存在 close={closes[-1]} pct={pct}')
        continue
    us_rows.append(['us_index', last_date, nm, sym, str(closes[-1]),
                    str(pct) if pct is not None else '', '美股收盘'])
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
    pct = round((closes[-1] / closes[-2] - 1) * 100, 2) if closes[-2] else None
    if ('us_index', last_date, sym) in existing_idx:
        print(f'  SKIP {nm} {sym}: {last_date} 已存在 close={closes[-1]} pct={pct}')
        continue
    us_rows.append(['us_index', last_date, nm, sym, str(closes[-1]),
                    str(pct) if pct is not None else '', '美股收盘'])
    existing_idx.add(('us_index', last_date, sym))
    print(f'  NEW {nm} {sym}: {last_date} close={closes[-1]} pct={pct}%')

if us_rows:
    append_rows(idx_path, us_rows)
print(f'indices.csv 新增美股 {len(us_rows)} 行')

# ---------- 3. 港股 hq 直连(9/17 收盘) ----------
print('\n--- 港股 hq 直连 ---')
try:
    req = urllib.request.Request('https://hq.sinajs.cn/list=hkHSI,hkHSTECH,hkHSCEI',
                                 headers={'Referer': 'https://finance.sina.com.cn'})
    with urllib.request.urlopen(req, timeout=15) as resp:
        txt = resp.read().decode('gbk', errors='ignore')
        print('  ' + txt.replace('\n', ' | '))
except Exception as e:
    print(f'  港股 hq FAIL: {e}')

# ---------- 3b. A股指数日线(9/17 收盘) ----------
print('\n--- A股指数日线(9/17 收盘) ---')
for sym, nm in [('sh000001', '上证指数'), ('sh000932', '中证消费'),
                ('sz399006', '创业板指'), ('sh000300', '沪深300'),
                ('sh000688', '科创50'), ('sh000933', '中证医药')]:
    df = retry(ak.stock_zh_index_daily, symbol=sym)
    if df is None or len(df) < 2:
        print(f'  WARN {nm} 日线暂缺')
        continue
    dts = [str(d)[:10] for d in df['date'].tolist()]
    cls = df['close'].tolist()
    pct = round((cls[-1] / cls[-2] - 1) * 100, 2)
    print(f'  {nm}: {dts[-1]} {cls[-1]} ({pct}%)  前值 {dts[-2]} {cls[-2]}')

# ---------- 3c. A股个股 9/17 收盘 ----------
print('\n--- A股个股日线(9/17 收盘) ---')
for sym, nm in [('sz002410', '广联达'), ('sh600438', '通威股份'), ('sh600519', '贵州茅台')]:
    df = retry(ak.stock_zh_a_daily, symbol=sym, adjust='qfq')
    if df is None or len(df) < 2:
        print(f'  WARN {nm} 日线暂缺')
        continue
    dts = [str(d)[:10] for d in df['date'].tolist()]
    cls = df['close'].tolist()
    pct = round((cls[-1] / cls[-2] - 1) * 100, 2)
    print(f'  {nm}: {dts[-1]} {cls[-1]} ({pct}%)')

# ---------- 3d. 场内 ETF 实时/收盘(9/17) ----------
print('\n--- 场内 ETF (fund_etf_spot_em 兜底复核) ---')
try:
    etf = ak.fund_etf_spot_em()
    want = {'513050', '159928', '159938', '512170', '513180', '512880', '515180', '512980', '159920'}
    sub = etf[etf['代码'].isin(want)]
    for _, r in sub.iterrows():
        print(f"  {r['代码']} {r['名称']}: {r['最新价']} ({r['涨跌幅']}%)")
except Exception as e:
    print(f'  ETF spot FAIL: {e}')

# ---------- 4. 且慢 pmdj 复测 ----------
try:
    req = urllib.request.Request('https://qieman.com/pmdj/v2/long-win/plan?prodCode=LONG_WIN',
                                 headers={'Referer': 'https://qieman.com/'})
    with urllib.request.urlopen(req, timeout=20) as resp:
        body = resp.read()
        print(f'\n  qieman pmdj plan: HTTP {resp.status} SIZE={len(body)}')
except Exception as e:
    print(f'\n  qieman pmdj plan: FAIL {e}')

print('\nDONE fetch_preopen_20260918')
