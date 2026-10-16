# -*- coding: utf-8 -*-
"""盘前档 2026-10-16(周五) 行情抓取 —— **A股 + 港股 + 美股 三市场正常交易日盘前**:
★档型判定：**档型③「正常交易日盘前」**（A股与港股当日均为正常交易日，但 08:00 双方均无新价格）
   → 依 §3.28 / §3.110 档型③ / §3.115c / §3.134c：**`close` 与 `pending` 产物均不产出**，待消化沿用上一档
   （`portfolio_close_20261015.json#pending_release`），并在报告声明「本档无新增 A股/港股定价」。
   ★与档型①「纯非交易日」的区别：档型① 用最近收盘修正件求和作基准**且不做待消化**；
     本档型**仅不产 close/pending、待消化照做（沿用上一档）**。
   ★与档型②「混合档」的区别：混合档**须产** `portfolio_pending_<DATE>.json`。
SESSION_TYPE = 'normal_trading_day_preopen'

★本档与上一档（10/15 盘前）的结构差异（**必须核对**，§3.141c 反面）：
   1) **US 10/15（周四，美股正常交易日）收盘成型于北京 10/16 04:00**
      → **本档 indices.csv 预期新增美股行**（XLV/IYH/QQQ/DIA/SPY + .IXIC/.DJI/.INX 逐 code 比对末行日期后再写）
   2) 10/15 为 A股 + 港股**双双正常交易日**（上证 −0.29% 报 3,756.31 / **恒生科技 4,060.99 −2.72%**）
      → 本档 A股/港股复核末行应为 **2026-10-15**
   3) 场外基金：10/15 为 A股 交易日 → 当日净值已于 10/15 盘后档全量落地 → **本档预期 +0 行**（非抓取失败，§3.142f）
      ⚠️ 但 QDII 三只（000369 / 016280 / 164906）**当前最新净值日待核**；10/15 为 A股 + 美股双交易日
         → 本档观察 **10/15 净值日是否释放**（§3.137d / §3.141b / §3.105）
   ★§3.150b 固定工序：**逐档兜底复抓 002708（sean/jasy 双账户）当日净值**（10/13 / 10/14 连续 2 日同机制迟滞）
1) 场外基金净值增量 —— 天天基金 F10 直连(§3.79); 判重 key = (code, nav_date) 二元组(§3.108 / §3.116a / §3.52)
2) 美股: 逐 code 读末行日期 → 相等即 SKIP（§3.141c）
3) A股: 复核指数日线末行应为 10/15, 10/16 今日 09:30 开盘
4) 港股: hq 直连复核日期字段（应为 2026/10/15 16:0x → 证明 10/15 已收盘、10/16 今日待开 09:30）
5) 000300 / 000933 稀疏序列复查(§3.112b)
6) 且慢 pmdj 复测 + 代理探针
★§3.150f 修正：三表增量**以写盘前后行数取差自证**（不再依赖 `fetch_summary.tables` 计数变量）
⚠️ 禁止整表行尾归一化(§3.87/§3.89): indices.csv 为混合行尾, 仅按「末行 EOL」字节追加
⚠️ §3.103: fund_etf_spot_em() 已连续多档失败, 本档不再重试该接口
"""
import json, os, sys, time, csv, urllib.request, socket

sys.path.insert(0, '/Users/jieyang/.workbuddy/binaries/python/envs/default/lib/python3.13/site-packages')
import akshare as ak

BASE = '/Users/jieyang/Documents/WealthHub'
HIST = os.path.join(BASE, 'data/processed/history')
TODAY = '2026-10-16'
SESSION_TYPE = 'normal_trading_day_preopen'
socket.setdefaulttimeout(25)
summary = {'date': TODAY, 'session': 'preopen', 'session_type': SESSION_TYPE,
           'session_type_note': '档型③「正常交易日盘前」= A股 10/16 正常交易日 + 港股 10/16 正常交易日 + 美股 10/16 正常交易日；08:00 A股/港股均无当日价格 → 不产 close/pending，待消化沿用上一档（10/15 收盘件）',
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


# ---------- 1. 场外基金净值增量 (F10 直连, §3.95 扫描最新 8 行) ----------
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
# §3.52 / §3.116a: 判重键语义恒为 (code, nav_date)，但「取哪两列」必须从表头解析
with open(csv_path, encoding='utf-8-sig') as f:
    _hdr = f.readline().strip().lstrip('\ufeff').split(',')
CI_CODE, CI_NAVD = _hdr.index('code'), _hdr.index('nav_date')
print(f'fund_nav.csv 表头 = {_hdr} → CI_CODE={CI_CODE} CI_NAVD={CI_NAVD}')
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
print('--- 场外基金净值增量（10/15 为 A股 交易日 → 当日净值已于 10/15 盘后档全量落地，本档预期 +0；观察 QDII 10/15 净值日是否释放）---')
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
    for r in lst[:8]:
        nd = str(r['FSRQ'])[:10]
        try:
            nav = float(r['DWJZ'])
        except Exception:
            continue
        if code not in nav_latest:
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
    tag = ' ***QDII***' if code in QDII_WATCH else ''
    if not added:
        print(f'  SKIP {nm} ({code}) 最新 {str(lst[0]["FSRQ"])[:10]} 已存在 nav={lst[0]["DWJZ"]}{tag}')

_n0 = nlines(csv_path)
if new_rows:
    append_rows(csv_path, new_rows)
_n1 = nlines(csv_path)
print(f'fund_nav.csv 新增 {_n1 - _n0} 行（§3.150f：以写盘前后行数取差自证）')
summary['tables']['fund_nav'] = _n1 - _n0

print('\n--- 净值出库情况汇总(含真实值, 供组合兜底修正) ---')
for code in sorted(nav_latest):
    nd, nav, pct = nav_latest[code]
    flag = ' [QDII]' if code in QDII_WATCH else ''
    print(f'  {code} {fund_map[code]}: {nd} nav={nav} pct={pct}{flag}')

# ★§3.150b 固定工序：002708 兜底复抓自证（与上一档基准 `price_src` 比对）
_prev_close = os.path.join(HIST, 'portfolio_close_20261015.json')
if os.path.exists(_prev_close):
    _pc = json.load(open(_prev_close, encoding='utf-8'))
    _prev_navdays = set()
    for _d in _pc.get('detail', []):
        if str(_d.get('code', '')).endswith('002708') or str(_d.get('code', '')) == '002708':
            _ps = str(_d.get('price_src', ''))
            import re as _re
            _m = _re.search(r'净值 (\d{2}/\d{2})', _ps)
            if _m:
                _prev_navdays.add(_m.group(1))
    print(f'\n--- §3.150b 002708 兜底复抓自证：上一档（10/15 收盘件）基准净值日 = {sorted(_prev_navdays)}')
    _now_nd = nav_latest.get('002708', (None,))[0]
    print(f'    本档 08:00 复抓最新净值日 = {_now_nd}  ->  '
          f'{"无需补正" if _now_nd is None or _now_nd <= "2026-10-15" else "⚠️ 发现新净值日，须核查"}')
    summary['fallback_refetch_002708'] = {'prev_base_navday': sorted(_prev_navdays), 'refetch_nav_date': _now_nd}

json.dump({'date': TODAY, 'session': 'preopen', 'session_type': SESSION_TYPE,
           'nav_latest': {k: {'nav_date': v[0], 'nav': v[1], 'pct': v[2]} for k, v in nav_latest.items()},
           'new_rows': _n1 - _n0},
          open(os.path.join(HIST, f'fundnav_{TODAY.replace("-", "")}.json'), 'w'),
          ensure_ascii=False, indent=1)

# ---------- 2. 美股: US 10/15 收盘成型于北京 10/16 04:00 → 本档可新增 ----------
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

print('\n--- 美股(US 10/15 正常交易日; 收盘成型于北京 10/16 04:00 → 本档可新增) ---')
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

# ---------- 3. A股 复核(末行应为 10/15; 今日 10/16 开盘) ----------
print('\n--- A股复核: 指数日线末行(应=10/15; 10/16 今日 09:30 开盘) ---')
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
    print(f'  {nm}: 最新 {dts[-1]} {cls[-1]} ({pct}%)  前值 {dts[-2]} {cls[-2]}')
    a_snapshot[sym] = {'date': dts[-1], 'close': cls[-1], 'pct': pct}
summary['a_snapshot'] = a_snapshot

# ---------- 4. 港股 hq 直连 ----------
print('\n--- 港股 hq 直连(日期字段应=2026/10/15 16:0x; 10/16 今日待开 09:30) ---')
# ★ §3.150a（10/15 档新发现）：新浪 hq 港股指数有 `rt_hk*` 与 `hk*` 两套 code，**同一时刻返回的收盘值不同**
#   （实测 HSTECH rt=4174.470 / hk=4169.020，差 −5.45 点；HSI −6.50；HSCEI −6.81）。
#   收盘档（fetch_close_*.py）用的是 `rt_hk*` → **盘前档复核必须同用 `rt_hk*`**，否则会误判为「昨收被修订」。
HK = 'rt_hkHSI,rt_hkHSTECH,rt_hkHSCEI,rt_hkHSHCI,rt_hkHSCI'
HK_ALT = 'hkHSI,hkHSTECH,hkHSCEI'   # 对照口径（仅用于自证两套差异）
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

# §3.150a 对照：同时抓 `hk*`（延迟口径）以自证两套 code 差异
hk_alt_raw, hk_rt_crosscheck = {}, {}
try:
    req = urllib.request.Request(f'https://hq.sinajs.cn/list={HK_ALT}',
                                 headers={'Referer': 'https://finance.sina.com.cn'})
    with urllib.request.urlopen(req, timeout=15) as resp:
        txt = resp.read().decode('gbk', errors='ignore')
    for line in txt.strip().split('\n'):
        k = line.split('=')[0].strip().replace('var hq_str_', '')
        hk_alt_raw[k] = line.strip()[:230]

    def _close(raw):
        try:
            return float(raw.split('="')[1].split(',')[6])
        except Exception:
            return None
    for rt_k, alt_k in [('rt_hkHSI', 'hkHSI'), ('rt_hkHSTECH', 'hkHSTECH'), ('rt_hkHSCEI', 'hkHSCEI')]:
        v_rt, v_alt = _close(hk_snapshot.get(rt_k, '')), _close(hk_alt_raw.get(alt_k, ''))
        diff = round(v_rt - v_alt, 4) if (v_rt is not None and v_alt is not None) else None
        hk_rt_crosscheck[rt_k] = {'rt_close': v_rt, 'alt_close': v_alt, 'diff_pts': diff}
        print(f'  [rt vs hk] {rt_k}: rt={v_rt}  hk({alt_k})={v_alt}  差 {diff} 点')
except Exception as e:
    print(f'  港股 hq 对照 FAIL: {e}')
summary['hk_hq_alt_raw'] = hk_alt_raw
summary['hk_rt_vs_alt_crosscheck'] = hk_rt_crosscheck

print('\n--- 港股实时(新浪源, 探针) ---')
try:
    df = retry(ak.stock_hk_index_spot_sina)
    if df is not None:
        print(df.head(8).to_string())
except Exception as e:
    print(f'  港股实时 FAIL: {e}')

summary['hk_hq_snapshot'] = hk_snapshot

# ---------- 5. 稀疏序列复查(§3.112b) ----------
print('\n--- 代理指数 distinct 交易日复查(§3.112b) ---')
try:
    from collections import defaultdict
    cnt = defaultdict(set)
    with open(idx_path, encoding='utf-8-sig') as f:
        for row in csv.DictReader(f):
            cnt[row['code']].add(row['date'][:10])
    for c in ['000300', '399006', '000932', 'HSTECH', 'XLV', '000001', '000933', 'HSHCI']:
        print(f'  {c}: distinct 交易日 = {len(cnt.get(c, ()))}')
    summary['distinct_days'] = {c: len(cnt.get(c, ())) for c in
                                ['000300', '399006', '000932', 'HSTECH', 'XLV', '000001', '000933', 'HSHCI']}
except Exception as e:
    print(f'  FAIL: {e}')

# ---------- 6. 且慢 pmdj 复测 ----------
try:
    req = urllib.request.Request('https://qieman.com/pmdj/v2/long-win/plan?prodCode=LONG_WIN',
                                 headers={'Referer': 'https://qieman.com/'})
    with urllib.request.urlopen(req, timeout=20) as resp:
        body = resp.read()
        print(f'\n  qieman pmdj plan: HTTP {resp.status} SIZE={len(body)}')
        json.dump({'date': TODAY, 'http': resp.status, 'size': len(body),
                   'body': body.decode('utf-8', errors='ignore')[:400]},
                  open(os.path.join(HIST, f'qieman_rest_{TODAY.replace("-", "")}.json'), 'w'),
                  ensure_ascii=False, indent=1)
except Exception as e:
    print(f'\n  qieman pmdj plan: FAIL {e}')

# ---------- 7. 代理探针 ----------
print('\n--- 代理探针 ---')
found = False
for k in ('HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy'):
    if os.environ.get(k):
        print(f'  {k}={os.environ.get(k)}')
        found = True
if not found:
    print('  (无 HTTP(S)_PROXY 环境变量, 直连)')

json.dump(summary, open(os.path.join(HIST, f'fetch_summary_{TODAY.replace("-", "")}_preopen.json'), 'w'),
          ensure_ascii=False, indent=1)
print('\nDONE fetch_preopen_20261016')
