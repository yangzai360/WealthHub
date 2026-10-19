# -*- coding: utf-8 -*-
"""盘前档 2026-10-19(周一) 行情抓取 —— **档型②「混合档·镜像」**:
★档型判定：**A股 10/19 正常交易日（周一）+ 港股 10/19 重阳节翌日休市**（反向混合档）
   → 依 §3.121b / §3.134c / §3.110：**不产 `portfolio_close_*`**；
     08:00 A股亦无当日价格 → **`pending` 只在「港股当日有收盘」的混合档才有实体意义**，
     本档港股休市 → 无新增港股定价 → **`close` 与 `pending` 均不产**，待消化沿用 10/16 收盘件
     （`portfolio_close_20261016_fix.json#pending_release`），报告须声明「本档无新增 A股/港股定价」。
   ★与档型③的区别：档型③ 港股当日有收盘（16:00 后可得）；本档港股**全天休市**。
SESSION_TYPE = 'mixed_session_preopen_hk_closed'

1) 场外基金净值增量 —— 天天基金 F10 直连(§3.95); 判重 key = (code, nav_date) 二元组(§3.108/§3.116a/§3.52)
2) 美股: 逐 code 读末行日期 → 相等即 SKIP（§3.141c）；US 10/16 已于 10/18 档归档 → 本档预期 +0
3) A股: 复核指数日线末行应为 10/16（10/19 今日 09:30 开盘）
4) 港股: hq 直连复核日期字段（应为 2026/10/16 16:0x → 10/17-10/18 周末 + 10/19 重阳翌日休市）
5) 000300 / 000933 稀疏序列复查(§3.112b)
6) 且慢 pmdj 复测 + 代理探针
★§3.155a: 逐档兜底复抓「上一收盘档全部『计 0/未推进』行」+ QDII 三只（000369/016280/164906）净值日推进核查
★§3.150f: 三表增量以写盘前后行数取差自证（nlines() 取差）
⚠️ 禁止整表行尾归一化(§3.87/§3.89): indices.csv 为混合行尾, 仅按「末行 EOL」字节追加
⚠️ §3.103: fund_etf_spot_em() 已连续多档失败, 本档不再重试该接口
"""
import json, os, sys, time, csv, urllib.request, socket

sys.path.insert(0, '/Users/jieyang/.workbuddy/binaries/python/envs/default/lib/python3.13/site-packages')
import akshare as ak

BASE = '/Users/jieyang/Documents/WealthHub'
HIST = os.path.join(BASE, 'data/processed/history')
TODAY = '2026-10-19'
SESSION_TYPE = 'mixed_session_preopen_hk_closed'
socket.setdefaulttimeout(25)
summary = {'date': TODAY, 'session': 'preopen', 'session_type': SESSION_TYPE,
           'session_type_note': '档型②反向「混合档」= A股 10/19 正常交易日（周一）+ 港股 10/19 重阳节翌日休市 + 美股 10/19 待开盘；08:00 三市场均无当日价格 → 不产 close/pending，待消化沿用上一档（10/16 收盘修正件）',
           'tables': {}}


def retry(fn, *args, times=3, **kwargs):
    for i in range(times):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            if i == times - 1:
                print(f'  FAIL {getattr(fn, "__name__", fn)} {args}: {e}')
                return None
            time.sleep(2)


def nlines(path):
    with open(path, 'rb') as f:
        return f.read().count(b'\n')


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
QDII_WATCH = ['000369', '016280', '164906']

csv_path = os.path.join(HIST, 'fund_nav.csv')
with open(csv_path, encoding='utf-8-sig') as f:
    _hdr = f.readline().strip().lstrip('\ufeff').split(',')
CI_CODE, CI_NAVD = _hdr.index('code'), _hdr.index('nav_date')
print(f'fund_nav.csv 表头 = {_hdr} → CI_CODE={CI_CODE} CI_NAVD={CI_NAVD}')
existing = set()
last_nav = {}
with open(csv_path, encoding='utf-8-sig') as f:
    for row in csv.DictReader(f):
        existing.add((row['code'], row['nav_date']))
        c = row['code']
        if c not in last_nav or row['nav_date'] > last_nav[c][0]:
            last_nav[c] = (row['nav_date'], row['nav'])

BEFORE = {p: nlines(os.path.join(HIST, p)) for p in ('fund_nav.csv', 'indices.csv', 'etf_intraday.csv')}
_prev_summary_path = os.path.join(HIST, f'fetch_summary_{TODAY}_preopen.json')
_prev_tables_first = None
if os.path.exists(_prev_summary_path):
    try:
        _ps = json.load(open(_prev_summary_path))
        _prev_tables_first = _ps.get('tables_first_run')
    except Exception:
        _prev_tables_first = None

HDRS = {'Referer': 'https://fundf10.eastmoney.com/', 'User-Agent': 'Mozilla/5.0'}


def fetch_f10(code, size=10):
    url = (f'https://api.fund.eastmoney.com/f10/lsjz?fundCode={code}'
           f'&pageIndex=1&pageSize={size}')
    req = urllib.request.Request(url, headers=HDRS)
    with urllib.request.urlopen(req, timeout=20) as resp:
        d = json.loads(resp.read().decode('utf-8', errors='ignore'))
    return (d.get('Data') or {}).get('LSJZList') or []


new_rows = []
fetched_latest = {}
print('--- 场外基金净值增量（10/16 为 A股 交易日 → 10/16 净值已于 10/18 档落库；本档观察 ①§3.141b 卫生补位 ②QDII 10/16 净值日是否释放）---')
for code, nm in fund_map.items():
    lst = None
    for i in range(3):
        try:
            lst = fetch_f10(code)
            break
        except Exception as e:
            if i == 2:
                print(f'  FAIL {code} {nm}: {e}')
            time.sleep(1)
    if not lst:
        continue
    rows = []
    for it in lst:
        nd = it.get('FSRQ')
        nav = it.get('DWJZ')
        pct = it.get('JZZZL')
        if not nd or not nav:
            continue
        rows.append((nd, str(nav), str(pct if pct not in (None, '') else '')))
    rows.sort(key=lambda x: x[0])
    latest = rows[-1] if rows else None
    fetched_latest[code] = {'nav_date': latest[0], 'nav': latest[1], 'pct': latest[2]} if latest else None
    added = 0
    for nd, nav, pct in rows:
        if (code, nd) in existing:
            continue
        new_rows.append(('%s' % TODAY, code, nm, nd, nav, pct))
        existing.add((code, nd))
        added += 1
    if added:
        print(f'  {code} {nm}: +{added} 行（最新 {latest[0]} {latest[1]}）')
    else:
        print(f'  {code} {nm}: +0（库内最新 {last_nav.get(code, ("?",))[0]} / 源最新 {latest[0] if latest else "-"}）')

if new_rows:
    new_rows.sort(key=lambda r: (r[3], r[1]))
    append_rows(csv_path, new_rows)

# ---------- 2. 三市场状态核验 ----------
print('--- 三市场状态核验 ---')
mkt = {}
sh = retry(ak.stock_zh_index_daily, symbol='sh000001')
if sh is not None and len(sh):
    last = sh.iloc[-1]
    mkt['a_share'] = {'last_date': str(last['date'])[:10], 'close': float(last['close']),
                      'chg_pct': round((float(last['close']) / float(sh.iloc[-2]['close']) - 1) * 100, 4)}
    print('  A股 sh000001 末行', mkt['a_share'])

us = {}
for code in ['XLV', 'IYH']:
    df = retry(ak.stock_us_daily, symbol=code)
    if df is not None and len(df):
        us[code] = {'last_date': str(df['date'].iloc[-1])[:10], 'close': float(df['close'].iloc[-1]),
                    'prev_close': float(df['close'].iloc[-2]),
                    'pct': round((float(df['close'].iloc[-1]) / float(df['close'].iloc[-2]) - 1) * 100, 4)}
        print(f'  US {code} 末行', us[code])
mkt['us'] = us

# 港股 hq 直连（日期字段判定法 §3.119b）
HK_URL = 'https://hq.sinajs.cn/list=rt_hkHSTECH,rt_hkHSI,rt_hkHSCEI'
hk = {}
try:
    req = urllib.request.Request(HK_URL, headers={'Referer': 'https://finance.sina.com.cn', 'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=15) as resp:
        txt = resp.read().decode('gbk', errors='ignore')
    for line in txt.strip().split('\n'):
        if '="' not in line:
            continue
        name = line.split('=')[0].split('_')[-1]
        body = line.split('="')[1].rstrip('";')
        f = body.split(',')
        # ★字段序实测（2026-10-19 校正）：0 英文名 / 1 中文名 / 2 开盘 / 3 昨收 / 4 最高 / 5 最低 /
        #   6 现价 / 7 涨跌额 / 8 涨跌幅 / 17 日期 / 18 时刻 —— 此前注释写 f[3]=现价 属误记
        hk[name] = {'name': f[1], 'open': f[2], 'prev': f[3], 'price': f[6], 'high': f[4], 'low': f[5],
                    'chg': f[7], 'pct': f[8],
                    'date': f[17] if len(f) > 17 else '', 'time': f[18] if len(f) > 18 else '',
                    'raw_len': len(f)}
        print(f'  HK {name} 日期字段={f[17] if len(f)>17 else "?"} 时刻={f[18] if len(f)>18 else "?"} 现价={f[6]} 昨收={f[3]} 涨跌幅={f[8]}%')
except Exception as e:
    print('  HK hq FAIL', e)
mkt['hk'] = hk

# 备选代码交叉核验（§3.150a）
hk_alt = {}
try:
    req = urllib.request.Request('https://hq.sinajs.cn/list=hkHSTECH,hkHSI', headers={'Referer': 'https://finance.sina.com.cn', 'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=15) as resp:
        txt = resp.read().decode('gbk', errors='ignore')
    for line in txt.strip().split('\n'):
        if '="' not in line:
            continue
        key = line.split('=')[0].split('_')[-1]
        f = line.split('="')[1].rstrip('";').split(',')
        hk_alt[key] = {'price': f[6] if len(f) > 6 else '', 'prev': f[3] if len(f) > 3 else '',
                       'date': f[17] if len(f) > 17 else ''}
    print('  HK alt', hk_alt)
except Exception as e:
    print('  HK alt FAIL', e)

# ---------- 3. 指数末行日期（A股主要指数，用于确认无增量） ----------
idx_last = {}
for code in ['sh000932', 'sh000933', 'sh000300', 'sz399006']:
    df = retry(ak.stock_zh_index_daily, symbol=code)
    if df is not None and len(df):
        ddates = [str(x)[:10] for x in df['date']]
        idx_last[code] = {'last_date': ddates[-1], 'close': float(df['close'].iloc[-1]),
                          'distinct_days': len(set(ddates))}
print('  A股指数末行/稀疏度', idx_last)

AFTER = {p: nlines(os.path.join(HIST, p)) for p in ('fund_nav.csv', 'indices.csv', 'etf_intraday.csv')}
summary['tables'] = {p.replace('.csv', ''): AFTER[p] - BEFORE[p] for p in BEFORE}
summary['tables_first_run'] = _prev_tables_first or dict(summary['tables'])
if _prev_tables_first:
    summary['rerun_note'] = '二次执行（修正港股字段序/美股日期解析）：tables 为本次 0 增量，真实首跑增量见 tables_first_run'
print('  三表增量(nlines 取差):', summary['tables'])

summary['market'] = mkt
summary['hk_alt_crosscheck'] = hk_alt
summary['idx_last'] = idx_last
summary['fetched_latest'] = fetched_latest
summary['csv_before'] = {k: last_nav.get(k) for k in fund_map}
summary['qdii_watch'] = {k: fetched_latest.get(k) for k in QDII_WATCH}
summary['new_rows'] = [{'code': r[1], 'nav_date': r[3], 'nav': r[4], 'pct': r[5]} for r in new_rows]

out = os.path.join(HIST, f'fetch_summary_{TODAY}_preopen.json')
with open(out, 'w', encoding='utf-8') as f:
    json.dump(summary, f, ensure_ascii=False, indent=2)
print('written', out)
