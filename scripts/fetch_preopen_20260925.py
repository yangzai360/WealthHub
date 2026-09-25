# -*- coding: utf-8 -*-
"""盘前档 2026-09-25(周五, 中秋节·A股/港股休市) 行情抓取:
★本档为「非交易日档」——A股/港股无新行情, 不更新场内/指数行情, 不做调仓建议
1) 场外基金净值增量 —— 天天基金 F10 直连(§3.79); 判重 key = (code, nav_date) 二元组(§3.86)
   ★重点: QDII 三只(000369/016280) 9/23、9/24 净值是否出库(9/24 盘后档记为 T+2 未出→计0)
     + 002708 的 9/24 真实净值是否出库(9/24 盘后档用弹性估算)
2) 美股(美东 9/24 周四收盘 = 隔夜, ★新增交易日) —— XLV/IYH/QQQ/DIA/SPY + .IXIC/.DJI/.INX
   ★XLV 9/24 收盘用于回填 events-2026-09-24.json 中 9 条留空的「美股标普医药」事件
3) A股/港股: 仅做 9/24 收盘复核(确认本地库无缺), 不新增(休市)
4) 且慢 pmdj 复测 + 代理探针
⚠️ 禁止整表行尾归一化(§3.87/§3.89): indices.csv 为混合行尾, 仅按「末行 EOL」字节追加
⚠️ §3.103: fund_etf_spot_em() 已连续 5 档失败, 本档不再重试该接口
"""
import json, os, sys, time, csv, urllib.request, socket

sys.path.insert(0, '/Users/jieyang/.workbuddy/binaries/python/envs/default/lib/python3.13/site-packages')
import akshare as ak

BASE = '/Users/jieyang/Documents/WealthHub'
HIST = os.path.join(BASE, 'data/processed/history')
TODAY = '2026-09-25'
socket.setdefaulttimeout(25)


def retry(fn, *args, times=3, **kwargs):
    for i in range(times):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            if i == times - 1:
                print(f'  FAIL {getattr(fn, "__name__", fn)} {args}: {e}')
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


# ---------- 1. 场外基金净值增量 (F10 直连, §3.95 扫描最新 4 行) ----------
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
QDII_WATCH = ['000369', '016280', '164906']
EST_WATCH = ['002708']   # 9/24 盘后档弹性估算, 须复核真实净值

csv_path = os.path.join(HIST, 'fund_nav.csv')
existing = set()
with open(csv_path, encoding='utf-8-sig') as f:
    for row in csv.DictReader(f):
        existing.add((row['code'], row['nav_date']))

HDRS = {'Referer': 'https://fundf10.eastmoney.com/', 'User-Agent': 'Mozilla/5.0'}


def fetch_f10(code, size=8):
    url = (f'https://api.fund.eastmoney.com/f10/lsjz?fundCode={code}'
           f'&pageIndex=1&pageSize={size}')
    req = urllib.request.Request(url, headers=HDRS)
    with urllib.request.urlopen(req, timeout=20) as resp:
        d = json.loads(resp.read().decode('utf-8', errors='ignore'))
    return (d.get('Data') or {}).get('LSJZList') or []


new_rows = []
nav_latest = {}
print('--- 场外基金净值增量 ---')
for code, nm in fund_map.items():
    lst = None
    for i in range(3):
        try:
            lst = fetch_f10(code)
            break
        except Exception as e:
            if i == 2:
                print(f'  FAIL {nm} {code}: {e}')
            time.sleep(1)
    if not lst:
        print(f'  WARN 基金 {nm} {code} 净值暂缺')
        continue
    added = 0
    for r in lst[:4]:
        nd = str(r['FSRQ'])[:10]
        try:
            nav = float(r['DWJZ'])
        except Exception:
            continue
        nav_latest[code] = (nd, nav, r.get('JZZZL'))
        if (code, nd) in existing:
            continue
        try:
            pct = float(r['JZZZL'])
        except Exception:
            pct = None
        new_rows.append([TODAY, code, nm, nd, str(round(nav, 4)),
                         str(round(pct, 2)) if pct is not None else ''])
        existing.add((code, nd))
        added += 1
        print(f'  NEW {nm}: nav_date={nd} nav={nav} pct={pct}')
    tag = ''
    if code in QDII_WATCH:
        tag += ' ***QDII***'
    if code in EST_WATCH:
        tag += ' ***EST-FIX(9/24弹性估算兜底)***'
    if not added:
        print(f'  SKIP {nm} ({code}) 最新 {str(lst[0]["FSRQ"])[:10]} 已存在 nav={lst[0]["DWJZ"]}{tag}')

if new_rows:
    append_rows(csv_path, new_rows)
print(f'fund_nav.csv 新增 {len(new_rows)} 行')

print('\n--- 净值出库情况汇总(含真实值, 供组合兜底修正) ---')
for code in sorted(nav_latest):
    nd, nav, pct = nav_latest[code]
    flag = ''
    if code in QDII_WATCH:
        flag += ' [QDII]'
    if code in EST_WATCH:
        flag += ' [EST-FIX]'
    print(f'  {code} {fund_map[code]}: {nd} nav={nav} pct={pct}{flag}')

# ---------- 2. 美股: 美东 9/24 周四收盘 (★隔夜新增交易日) ----------
idx_path = os.path.join(HIST, 'indices.csv')
existing_idx = set()
with open(idx_path, encoding='utf-8-sig') as f:
    for row in csv.DictReader(f):
        existing_idx.add((row['type'], row['date'][:10], row['code']))

print('\n--- 美股 9/24 收盘抓取(隔夜) ---')
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
    print(f'  {nm} {sym}: 最新 {last_date} close={closes[-1]} ({pct}%)  前值 {dates[-2]} {closes[-2]}')
    if ('us_index', last_date, sym) in existing_idx:
        print(f'    SKIP 已存在')
        continue
    us_rows.append(['us_index', last_date, nm, sym, str(closes[-1]),
                    str(pct) if pct is not None else '', '美股收盘'])
    existing_idx.add(('us_index', last_date, sym))

for sym, nm in [('.IXIC', '纳斯达克'), ('.DJI', '道琼斯'), ('.INX', '标普500')]:
    df = retry(ak.index_us_stock_sina, symbol=sym)
    if df is None or len(df) < 2:
        print(f'  WARN 指数 {sym} 数据暂缺')
        continue
    dates = [str(d)[:10] for d in df['date'].tolist()]
    closes = df['close'].tolist()
    last_date = dates[-1]
    pct = round((closes[-1] / closes[-2] - 1) * 100, 2) if closes[-2] else None
    print(f'  {nm} {sym}: 最新 {last_date} close={closes[-1]} ({pct}%)  前值 {dates[-2]} {closes[-2]}')
    if ('us_index', last_date, sym) in existing_idx:
        print(f'    SKIP 已存在')
        continue
    us_rows.append(['us_index', last_date, nm, sym, str(closes[-1]),
                    str(pct) if pct is not None else '', '美股收盘'])
    existing_idx.add(('us_index', last_date, sym))

if us_rows:
    append_rows(idx_path, us_rows)
print(f'indices.csv 新增美股 {len(us_rows)} 行')

# ---------- 3. 非交易日: 仅复核 A股/港股 9/24 收盘已在库 ----------
print('\n--- 非交易日复核: A股指数日线最新日期(应为 9/24) ---')
for sym, nm in [('sh000001', '上证指数'), ('sh000932', '中证消费'),
                ('sz399006', '创业板指'), ('sh000300', '沪深300'),
                ('sh000933', '中证医药'), ('sh000913', '300医药'),
                ('sz399989', '中证医疗'), ('sz399997', '中证白酒')]:
    df = retry(ak.stock_zh_index_daily, symbol=sym)
    if df is None or len(df) < 2:
        print(f'  WARN {nm} 日线暂缺')
        continue
    dts = [str(d)[:10] for d in df['date'].tolist()]
    cls = df['close'].tolist()
    pct = round((cls[-1] / cls[-2] - 1) * 100, 2)
    print(f'  {nm}: 最新 {dts[-1]} {cls[-1]} ({pct}%)')

print('\n--- 非交易日复核: 港股 hq 直连(应为 9/24 收盘) ---')
try:
    req = urllib.request.Request('https://hq.sinajs.cn/list=hkHSI,hkHSTECH,hkHSCEI',
                                 headers={'Referer': 'https://finance.sina.com.cn'})
    with urllib.request.urlopen(req, timeout=15) as resp:
        txt = resp.read().decode('gbk', errors='ignore')
        print('  ' + txt.replace('\n', ' | '))
except Exception as e:
    print(f'  港股 hq FAIL: {e}')

# ---------- 4. 且慢 pmdj 复测 ----------
try:
    req = urllib.request.Request('https://qieman.com/pmdj/v2/long-win/plan?prodCode=LONG_WIN',
                                 headers={'Referer': 'https://qieman.com/'})
    with urllib.request.urlopen(req, timeout=20) as resp:
        body = resp.read()
        print(f'\n  qieman pmdj plan: HTTP {resp.status} SIZE={len(body)}')
except Exception as e:
    print(f'\n  qieman pmdj plan: FAIL {e}')

# ---------- 5. 代理探针 ----------
print('\n--- 代理探针 ---')
found = False
for k in ('HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy'):
    if os.environ.get(k):
        print(f'  {k}={os.environ.get(k)}')
        found = True
if not found:
    print('  (无 HTTP(S)_PROXY 环境变量, 直连)')

print('\nDONE fetch_preopen_20260925')
