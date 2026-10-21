# -*- coding: utf-8 -*-
"""盘前档 2026-10-21(周三) 行情抓取 —— **A股 + 港股 + 美股 三市场正常交易日盘前**:
★档型判定：**档型③「正常交易日盘前」**
   - A股：10/21 周三，正常交易日（10/20 已收盘）
   - 港股：10/21 周三，正常交易日（10/20 已复市并收盘）
   - 美股：10/20 周二正常交易日，收盘成型于北京 10/21 04:00 → **本档唯一新增真实定价**
   → 依 §3.109 / §3.110 档型③：**`close` 与 `pending` 产物均不产出**，待消化沿用上一档
   （`portfolio_close_20261020.json#pending_release`），报告须声明「本档无新增 A股/港股定价」。

★本档与上一档（10/20 盘前）的结构差异（**必须核对**，§3.141c 反面）：
   1) **US 10/20（周二）收盘成型于北京 10/21 04:00** → **indices.csv 预期新增美股行**
   2) 10/20 为 A股 正常交易日 → 本档 A股 复核末行应为 **2026-10-20**
   3) **港股 10/20 已复市且已收盘** → hq 日期字段应为 **2026/10/20 16:0x**
      → 恒科 4,250 / 4,000 两线本档可用 10/20 收盘判定（10/20 收盘档已给出 4,045.91）
   4) 场外基金：10/20 为 A股 交易日 → 当日净值已于 10/20 盘后档部分落地
      → **本档须兜底复抓上一收盘档「全部未定价行」**（§3.155a）：
        `012348`（sean+jasy 双行）/ `000051` 的 10/20 净值是否出库（10/20 盘后档为 10/19）
      → 若出库 → **触发 §3.140a 跨档补正**，须生成 `portfolio_close_20261020_fix.json`
   5) **QDII 000369 / 016280 的净值须复核是否推进至 10/19**（10/20 盘后档已按 10/19 净值核销 −349.01 元）
1) 场外基金净值增量 —— 天天基金 F10 直连(§3.95)；判重 key = (code, nav_date) 二元组(§3.108 / §3.116a / §3.52)
2) 美股: 逐 code 读末行日期 → 相等即 SKIP（§3.141c）
3) A股: 复核指数日线末行应为 10/20（今日 09:30 开盘）
4) 港股: hq 直连复核日期字段（应为 2026/10/20 16:0x）
5) 000300 / 000933 / 399006 稀疏序列复查(§3.112b：distinct 交易日数 + 起点错位 + 日历跨度)
6) 且慢 pmdj 复测 + 代理探针
★§3.150f: 三表增量以写盘前后行数取差自证（nlines() 取差）
⚠️ 禁止整表行尾归一化(§3.87/§3.89): indices.csv 为混合行尾, 仅按「末行 EOL」字节追加
⚠️ §3.103: fund_etf_spot_em() 已连续多档失败, 本档不再重试该接口
⚠️ §3.158d: 新浪 hq `rt_hk*` 字段序 f[3]=昨收、f[6]=现价（不得用 f[3] 当现价）
"""
import json, os, sys, time, csv, urllib.request, socket, re

sys.path.insert(0, '/Users/jieyang/.workbuddy/binaries/python/envs/default/lib/python3.13/site-packages')
import akshare as ak

BASE = '/Users/jieyang/Documents/WealthHub'
HIST = os.path.join(BASE, 'data/processed/history')
TODAY = '2026-10-21'
PREV_DATE = '2026-10-20'
SESSION_TYPE = 'normal_trading_day_preopen'
socket.setdefaulttimeout(25)
summary = {'date': TODAY, 'session': 'preopen', 'session_type': SESSION_TYPE,
           'session_type_note': '档型③「正常交易日盘前」= A股 10/21 正常交易日 + 港股 10/21 正常交易日（10/20 已复市收盘）+ 美股 10/21 正常交易日；08:00 A股/港股均无当日价格 → 不产 close/pending，待消化沿用上一档（10/20 收盘件）',
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

HDRS = {'Referer': 'https://fundf10.eastmoney.com/', 'User-Agent': 'Mozilla/5.0'}


def fetch_f10(code, size=10):
    url = (f'https://api.fund.eastmoney.com/f10/lsjz?fundCode={code}'
           f'&pageIndex=1&pageSize={size}')
    req = urllib.request.Request(url, headers=HDRS)
    with urllib.request.urlopen(req, timeout=20) as resp:
        d = json.loads(resp.read().decode('utf-8', errors='ignore'))
    return (d.get('Data') or {}).get('LSJZList') or []


# ★§3.155a 兜底复抓名单：上一收盘档全部「计 0 / 未推进」行
FALLBACK_CODES = set()
_prev_close_path = os.path.join(HIST, f'portfolio_close_{PREV_DATE.replace("-", "")}.json')
_prev_close = None
if os.path.exists(_prev_close_path):
    _prev_close = json.load(open(_prev_close_path, encoding='utf-8'))
    for _u in (_prev_close.get('unpriced') or []):
        FALLBACK_CODES.add(str(_u.get('code')))
FALLBACK_CODES.add('002708')   # §3.150b 固定工序
print(f'§3.155a 兜底复抓名单（上一收盘档 unpriced ∪ 002708）= {sorted(FALLBACK_CODES)}')

new_rows = []
fetched_latest = {}
print('--- 场外基金净值增量（10/20 为 A股 交易日 → 当日净值已于 10/20 盘后档部分落地；本档重点：012348×2 / 000051 未推进券 + QDII 推进核查）---')
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
    rows = []
    for it in lst:
        nd = str(it.get('FSRQ'))[:10]
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
        new_rows.append((TODAY, code, nm, nd, nav, pct))
        existing.add((code, nd))
        added += 1
        print(f'  NEW {nm}({code}): nav_date={nd} nav={nav} pct={pct}'
              + (' ***兜底复抓***' if code in FALLBACK_CODES else ''))
    if not added:
        print(f'  SKIP {nm}({code}) 库内最新 {last_nav.get(code, ("?",))[0]} / 源最新 {latest[0] if latest else "-"}')

_b0 = nlines(csv_path)
if new_rows:
    new_rows.sort(key=lambda r: (r[3], r[1]))
    append_rows(csv_path, new_rows)
_b1 = nlines(csv_path)
print(f'fund_nav.csv 新增 {_b1 - _b0} 行（§3.150f：写盘前后行数取差自证）')
summary['tables']['fund_nav'] = _b1 - _b0

print('\n--- 净值出库情况汇总（含真实值，供组合兜底修正）---')
for code in sorted(fetched_latest):
    v = fetched_latest[code]
    if not v:
        continue
    flag = ' [QDII]' if code in QDII_WATCH else (' [兜底]' if code in FALLBACK_CODES else '')
    print(f'  {code} {fund_map[code]}: {v["nav_date"]} nav={v["nav"]} pct={v["pct"]}{flag}')

# ★§3.155a / §3.140a：兜底复抓判定（逐券比对上一收盘档基准 `price_src` 净值日）
print('\n--- §3.155a/§3.140a 兜底复抓判定（对比 portfolio_close_20261020.json 基准净值日）---')
fallback_verdict = {}
if _prev_close is not None:
    prev_navday_by_code = {}
    for _d in _prev_close.get('detail', []):
        _c = str(_d.get('code', ''))
        _c6 = _c.split('.')[-1][-6:] if _c else ''
        _ps = str(_d.get('price_src', ''))
        _m = re.search(r'(20\d{2}-\d{2}-\d{2})', _ps)
        if _c6 and _m:
            prev_navday_by_code.setdefault(_c6, set()).add(_m.group(1))
    for _c in sorted(FALLBACK_CODES):
        _prev_days = sorted(prev_navday_by_code.get(_c, []))
        _now = fetched_latest.get(_c)
        _verd = 'no_source'
        if _now:
            _maxp = max(_prev_days) if _prev_days else ''
            if _now['nav_date'] > _maxp:
                _verd = 'NEW_NAVDAY_NEED_FIX'
            else:
                _verd = 'unchanged'
        fallback_verdict[_c] = {'prev_navdays': _prev_days,
                                'refetch_nav_date': _now['nav_date'] if _now else None,
                                'refetch_nav': _now['nav'] if _now else None,
                                'refetch_pct': _now['pct'] if _now else None,
                                'verdict': _verd}
        print(f'  {_c} {fund_map.get(_c, "")}: 基准净值日 {_prev_days} → 复抓 {_now["nav_date"] if _now else "-"} '
              f'({_now["nav"] if _now else "-"} / {_now["pct"] if _now else "-"}) → {_verd}')
summary['fallback_verdict'] = fallback_verdict

# ★QDII 净值推进与占位复核（10/20 盘后档已按 10/19 净值核销 −349.01 元）
print('\n--- QDII 000369/016280 净值推进复核（基准 10/16 疑似占位 → 10/19 已核销）---')
qdii_revision = {}
for _c in ['000369', '016280', '164906']:
    _lst = fetched_latest.get(_c)
    qdii_revision[_c] = {'refetch_latest': _lst}
    print(f'  {_c}: 源最新 {_lst}')
summary['qdii_latest_recheck'] = qdii_revision

# ---------- 2. 美股: US 10/20 收盘成型于北京 10/21 04:00 → 本档可新增 ----------
idx_path = os.path.join(HIST, 'indices.csv')
existing_idx = set()
last_by_code = {}
with open(idx_path, encoding='utf-8-sig') as f:
    for row in csv.DictReader(f):
        key = (row['type'], row['date'][:10], row['code'])
        existing_idx.add(key)
        c = row['code']
        d = row['date'][:10]
        if c not in last_by_code or d > last_by_code[c]:
            last_by_code[c] = d

print('\n--- 美股(US 10/20 周二正常交易日; 收盘成型于北京 10/21 04:00 → 本档可新增) ---')
us_rows = []
us_snapshot = {}
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
    print(f'  {nm} {sym}: 最新 {last_date} close={closes[-1]} ({pct}%)  前值 {dates[-2]} {closes[-2]}'
          f'  | 本地末行 {last_by_code.get(sym)}')
    us_snapshot[sym] = {'date': last_date, 'close': closes[-1], 'pct': pct, 'prev_date': dates[-2]}
    if last_by_code.get(sym) == last_date:
        print('    SKIP 本地末行日期已等于抓取日期（§3.141c 禁止重复计入）')
        continue
    if ('us_index', last_date, sym) in existing_idx:
        print('    SKIP 已存在')
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
    print(f'  {nm} {sym}: 最新 {last_date} close={closes[-1]} ({pct}%)  前值 {dates[-2]} {closes[-2]}'
          f'  | 本地末行 {last_by_code.get(sym)}')
    us_snapshot[sym] = {'date': last_date, 'close': closes[-1], 'pct': pct, 'prev_date': dates[-2]}
    if last_by_code.get(sym) == last_date:
        print('    SKIP 本地末行日期已等于抓取日期（§3.141c 禁止重复计入）')
        continue
    if ('us_index', last_date, sym) in existing_idx:
        print('    SKIP 已存在')
        continue
    us_rows.append(['us_index', last_date, nm, sym, str(closes[-1]),
                    str(pct) if pct is not None else '', '美股收盘'])
    existing_idx.add(('us_index', last_date, sym))

_i0 = nlines(idx_path)
if us_rows:
    append_rows(idx_path, us_rows)
_i1 = nlines(idx_path)
print(f'indices.csv 新增美股 {_i1 - _i0} 行（§3.150f：行数取差自证）')
summary['tables']['indices_us'] = _i1 - _i0
summary['us_snapshot'] = us_snapshot

# ---------- 3. A股 复核(末行应为 10/20; 今日 10/21 开盘) ----------
print('\n--- A股复核: 指数日线末行(应=10/20; 10/21 今日 09:30 开盘) ---')
a_snapshot = {}
for sym, nm in [('sh000001', '上证指数'), ('sh000932', '中证消费'),
                ('sz399006', '创业板指'), ('sh000300', '沪深300'),
                ('sh000933', '中证医药'), ('sh000913', '300医药'),
                ('sz399989', '中证医疗'), ('sz399997', '中证白酒'),
                ('sh000905', '中证500'), ('sz399005', '中小100')]:
    df = retry(ak.stock_zh_index_daily, symbol=sym)
    if df is None or len(df) < 2:
        print(f'  WARN {nm} 日线暂缺')
        continue
    dts = [str(d)[:10] for d in df['date'].tolist()]
    cls = df['close'].tolist()
    pct = round((cls[-1] / cls[-2] - 1) * 100, 2)
    print(f'  {nm}: 最新 {dts[-1]} {cls[-1]} ({pct}%)  前值 {dts[-2]} {cls[-2]}  distinct={len(set(dts))}')
    a_snapshot[sym] = {'date': dts[-1], 'close': cls[-1], 'pct': pct, 'distinct_days': len(set(dts))}
summary['a_snapshot'] = a_snapshot

# ---------- 4. 港股 hq 直连 ----------
print('\n--- 港股 hq 直连(日期字段应=2026/10/20 16:0x; 10/21 今日 09:30 开盘) ---')
HK = 'rt_hkHSI,rt_hkHSTECH,rt_hkHSCEI,rt_hkHSHCI,rt_hkHSCI'
HK_ALT = 'hkHSI,hkHSTECH,hkHSCEI'
hk_snapshot = {}
try:
    req = urllib.request.Request(f'https://hq.sinajs.cn/list={HK}',
                                 headers={'Referer': 'https://finance.sina.com.cn'})
    with urllib.request.urlopen(req, timeout=15) as resp:
        txt = resp.read().decode('gbk', errors='ignore')
        for line in txt.strip().split('\n'):
            print('  ' + line.strip()[:230])
            hk_snapshot[line.split('=')[0].strip().replace('var hq_str_', '')] = line.strip()[:230]
except Exception as e:
    print(f'  港股 hq FAIL: {e}')

# §3.150a 对照：`hk*` 延迟口径
hk_alt_raw, hk_crosscheck = {}, {}
try:
    req = urllib.request.Request(f'https://hq.sinajs.cn/list={HK_ALT}',
                                 headers={'Referer': 'https://finance.sina.com.cn'})
    with urllib.request.urlopen(req, timeout=15) as resp:
        txt = resp.read().decode('gbk', errors='ignore')
    for line in txt.strip().split('\n'):
        k = line.split('=')[0].strip().replace('var hq_str_', '')
        hk_alt_raw[k] = line.strip()[:230]
    for k, raw in hk_snapshot.items():
        k2 = k.replace('rt_', '')
        if k2 in hk_alt_raw:
            try:
                p1 = float(raw.split('="')[1].split(',')[6])
                p2 = float(hk_alt_raw[k2].split('="')[1].split(',')[6])
                hk_crosscheck[k] = {'rt_price': p1, 'hk_price': p2, 'diff_pts': round(p1 - p2, 3)}
            except Exception:
                pass
    print('  §3.150a rt_hk*/hk* 双码对照:', hk_crosscheck)
except Exception as e:
    print(f'  HK alt FAIL: {e}')

summary['hk_snapshot'] = hk_snapshot
summary['hk_crosscheck'] = hk_crosscheck

# ---------- 5. 稀疏序列复查 ----------
print('\n--- 稀疏序列复查(§3.112b: distinct 交易日数 + 覆盖起点) ---')
sparse = {}
for sym in ['sh000300', 'sh000933', 'sz399006', 'sz399989']:
    df = retry(ak.stock_zh_index_daily, symbol=sym)
    if df is None or not len(df):
        continue
    dts = [str(d)[:10] for d in df['date'].tolist()]
    sparse[sym] = {'rows': len(df), 'distinct_days': len(set(dts)),
                   'first': dts[0], 'last': dts[-1]}
    print(f'  {sym}: rows={len(df)} distinct={len(set(dts))} {dts[0]} → {dts[-1]}')
summary['sparse'] = sparse

# ---------- 6. 且慢探针 ----------
print('\n--- 且慢 REST 探针 ---')
qieman = {}
try:
    for path in ['https://qieman.com/pmdj/v2/long-win/plan',
                 'https://qieman.com/pmdj/v2/long-win/adjustments',
                 'https://qieman.com/pmdj/v2/long-win/nav-history']:
        try:
            req = urllib.request.Request(path, headers={'User-Agent': 'Mozilla/5.0',
                                                        'Referer': 'https://qieman.com/'})
            with urllib.request.urlopen(req, timeout=15) as resp:
                body = resp.read()
            qieman[path.split('/')[-1]] = {'status': resp.status, 'size': len(body)}
        except Exception as e:
            qieman[path.split('/')[-1]] = {'error': str(e)}
    print('  ', qieman)
except Exception as e:
    print('  且慢探针 FAIL', e)
summary['qieman'] = qieman

# ---------- 7. 代理探针 ----------
proxy = {k: v for k, v in os.environ.items() if 'proxy' in k.lower()}
summary['proxy_env'] = proxy
print('  proxy env:', proxy if proxy else '(none)')

AFTER_TABLES = {p: nlines(os.path.join(HIST, p)) for p in ('fund_nav.csv', 'indices.csv', 'etf_intraday.csv')}
summary['table_lines_after'] = AFTER_TABLES

out = os.path.join(HIST, f'fetch_summary_{TODAY}_preopen.json')
with open(out, 'w', encoding='utf-8') as f:
    json.dump(summary, f, ensure_ascii=False, indent=2, default=str)
print('\nwritten', out)
