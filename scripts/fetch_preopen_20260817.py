# -*- coding: utf-8 -*-
"""盘前档 2026-08-17(周一) 行情抓取：场外基金净值增量(8/14周五净值) + 恒科/A股指数盘前参考 + 且慢pmdj复测(第8日)"""
import json, os, sys, time, csv

sys.path.insert(0, '/Users/jieyang/.workbuddy/binaries/python/envs/default/lib/python3.13/site-packages')
import akshare as ak

BASE = '/Users/jieyang/Documents/WealthHub'
HIST = os.path.join(BASE, 'data/processed/history')
TODAY = '2026-08-17'

def retry(fn, *args, times=3, **kwargs):
    for i in range(times):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            if i == times - 1:
                print(f'  FAIL {fn.__name__} {args}: {e}')
                return None
            time.sleep(2)

# ---------- 1. 场外基金净值增量 ----------
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
# 读全库建 (code, nav_date) 主键
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

# ---------- 2. A股指数日线（盘前参考, 最新应为8/14） ----------
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

# ---------- 3. 港股指数 spot（盘前, 若开盘前则拿到8/14收盘） ----------
hk_done = {}
hk_map = {'HSI': '恒生指数', 'HSTECH': '恒生科技'}
for attempt in range(3):
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

# ---------- 4. 且慢 pmdj 复测（第8日） ----------
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

out = {'date': TODAY, 'indices': indices, 'hk': hk_done, 'fund_new': len(new_rows), 'qieman': qieman}
with open(os.path.join(HIST, 'preopen_20260817.json'), 'w', encoding='utf-8') as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
print('\nDONE -> preopen_20260817.json')
