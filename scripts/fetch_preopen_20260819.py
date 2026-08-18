# -*- coding: utf-8 -*-
"""盘前档 2026-08-19(周三) 行情抓取：场外基金净值增量(8/18周二净值) + 隔夜美股(8/18收盘) + A股/恒科指数参考 + 且慢pmdj复测(第14日)"""
import json, os, sys, time, csv

sys.path.insert(0, '/Users/jieyang/.workbuddy/binaries/python/envs/default/lib/python3.13/site-packages')
import akshare as ak

BASE = '/Users/jieyang/Documents/WealthHub'
HIST = os.path.join(BASE, 'data/processed/history')
TODAY = '2026-08-19'

def retry(fn, *args, times=3, **kwargs):
    for i in range(times):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            if i == times - 1:
                print(f'  FAIL {fn.__name__} {args}: {e}')
                return None
            time.sleep(2)

# ---------- 1. 场外基金净值增量（8/18 周二净值，周三早盘全量可抓，QDII 停 8/14 T+1） ----------
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

# ---------- 2. 隔夜美股（8/18 周二收盘） ----------
us_map = {'QQQ': '纳指100ETF', 'DIA': '道指ETF', 'XLV': '医疗保健ETF', 'IYH': '美股医疗ETF'}
us_idx = {}
for sym, nm in us_map.items():
    df = retry(ak.stock_us_daily, symbol=sym)
    if df is None or len(df) < 2:
        print(f'  WARN 美股 {nm} 数据暂缺')
        continue
    last = df.iloc[-1]; prev = df.iloc[-2]
    close = float(last['close']); prev_close = float(prev['close'])
    pct = (close / prev_close - 1) * 100
    date_str = str(last['date'])[:10]
    us_idx[sym] = {'name': nm, 'date': date_str, 'close': round(close, 2), 'pct': round(pct, 2)}
    print(f'  US {nm}: {date_str} close={close:.2f} pct={pct:+.2f}%')

idx_us_map = {'.IXIC': '纳斯达克', '.DJI': '道琼斯'}
for sym, nm in idx_us_map.items():
    df = retry(ak.index_us_stock_sina, symbol=sym)
    if df is None or len(df) < 2:
        print(f'  WARN 美股指数 {nm} 数据暂缺')
        continue
    last = df.iloc[-1]; prev = df.iloc[-2]
    close = float(last['close']); prev_close = float(prev['close'])
    pct = (close / prev_close - 1) * 100
    date_str = str(last['date'])[:10]
    us_idx[f'IDX_{sym}'] = {'name': nm, 'date': date_str, 'close': round(close, 2), 'pct': round(pct, 2)}
    print(f'  US IDX {nm}: {date_str} close={close:.2f} pct={pct:+.2f}%')

idx_csv = os.path.join(HIST, 'indices.csv')
with open(idx_csv, encoding='utf-8-sig') as f:
    idx_existing = set()
    for row in csv.DictReader(f):
        idx_existing.add((row['code'], row['date'], row['note']))
us_rows = []
for sym, v in us_idx.items():
    note = '美股收盘'
    code = sym
    if sym.startswith('IDX_'):
        code = sym.replace('IDX_', '')
    if (code, v['date'], note) in idx_existing:
        print(f'  SKIP indices {code} {v["date"]} 已存在')
        continue
    us_rows.append(['us_index', v['date'], v['name'], code, str(v['close']), str(v['pct']), note])
    idx_existing.add((code, v['date'], note))
with open(idx_csv, 'a', encoding='utf-8-sig') as f:
    for r in us_rows:
        f.write(','.join(r) + '\n')
print(f'indices.csv 新增美股 {len(us_rows)} 行')

# ---------- 3. A股指数日线（确认 8/18 收盘已在库，仅参考） ----------
idx_map = {'sh000001': '上证指数', 'sz399006': '创业板指', 'sh000932': '中证消费'}
indices = []
for sym, name in idx_map.items():
    df = retry(ak.stock_zh_index_daily, symbol=sym)
    if df is None or len(df) < 2:
        print(f'  WARN 指数 {name} 数据暂缺')
        continue
    last = df.iloc[-1]; prev = df.iloc[-2]
    close = float(last['close']); prev_close = float(prev['close'])
    pct = (close / prev_close - 1) * 100
    date_str = str(last['date'])[:10]
    indices.append({'name': name, 'code': sym[2:], 'date': date_str, 'close': round(close, 2), 'pct': round(pct, 2)})
    print(f'  {name}: {date_str} close={close:.2f} pct={pct:+.2f}%')

# ---------- 4. 港股指数 spot（盘前第7日预期失败，直接用已归档 8/18 收盘） ----------
hk_done = {}
hk_map = {'HSI': '恒生指数', 'HSTECH': '恒生科技'}
for attempt in range(2):
    try:
        hk = retry(ak.stock_hk_index_spot_sina)
        if hk is not None and len(hk) > 0:
            for _, row in hk.iterrows():
                nm = str(row.get('name', ''))
                for code, cname in hk_map.items():
                    if code in str(row.get('code', '')) or (code == 'HSI' and '恒生指数' in nm) or (code == 'HSTECH' and '恒生科技' in nm):
                        if code not in hk_done:
                            hk_done[code] = {'name': cname, 'close': round(float(row['最新价']), 2),
                                             'pct': round(float(row['涨跌幅']), 2)}
                            print(f'  {cname}: {row["最新价"]} pct={row["涨跌幅"]}%')
            if len(hk_done) == 2:
                break
    except Exception as e:
        print(f'  WARN 港股接口异常(第{attempt+1}次): {e}')
    time.sleep(2)
if len(hk_done) < 2:
    print('  WARN 港股 spot 盘前仍空（连续第7日），沿用 indices.csv 8/18 收盘')

# ---------- 5. 且慢 pmdj 复测（第14日，预期空 body） ----------
qieman = {}
try:
    import urllib.request
    req = urllib.request.Request('https://qieman.com/pmdj/v2/long-win/plan?prodCode=LONG_WIN',
                                 headers={'Referer': 'https://qieman.com/', 'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=20) as resp:
        body = resp.read()
    qieman['plan'] = {'ok': len(body) > 0, 'size': len(body)}
    print(f'  pmdj plan: ok={len(body)>0} size={len(body)}')
except Exception as e:
    qieman['plan'] = {'ok': False, 'error': str(e)}
    print(f'  pmdj plan FAIL: {e}')

out = {'date': TODAY, 'indices': indices, 'hk': hk_done, 'us': us_idx,
       'fund_new': len(new_rows), 'qieman': qieman}
with open(os.path.join(HIST, 'preopen_20260819.json'), 'w', encoding='utf-8') as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
print('\nDONE -> preopen_20260819.json')
