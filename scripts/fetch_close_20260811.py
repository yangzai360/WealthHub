# -*- coding: utf-8 -*-
"""盘后档 2026-08-11 收盘行情抓取：A股指数日线 / 港股 spot / 场内ETF / 个股 / 场外净值 / 美股"""
import json, os, sys, time, re, csv

sys.path.insert(0, '/Users/jieyang/.workbuddy/binaries/python/envs/default/lib/python3.13/site-packages')
import akshare as ak

BASE = '/Users/jieyang/Documents/WealthHub'
HIST = os.path.join(BASE, 'data/processed/history')
TODAY = '2026-08-11'

def retry(fn, *args, times=3, **kwargs):
    for i in range(times):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            if i == times - 1:
                print(f'  FAIL {fn.__name__} {args}: {e}')
                return None
            time.sleep(2)

# ---------- 1. A股指数日线收盘 ----------
idx_map = {'sh000001': '上证指数', 'sz399006': '创业板指', 'sh000932': '中证消费'}
indices = []
for sym, name in idx_map.items():
    df = retry(ak.stock_zh_index_daily, symbol=sym)
    if df is None or len(df) < 2:
        print(f'  WARN 指数 {name} 数据暂缺')
        indices.append({'type': 'index', 'date': TODAY, 'name': name, 'code': sym[2:],
                        'close': None, 'pct_change': None, 'note': '收盘20:00'})
        continue
    last = df.iloc[-1]; prev = df.iloc[-2]
    close = float(last['close']); prev_close = float(prev['close'])
    pct = (close / prev_close - 1) * 100
    # 校验日期
    date_str = str(last['date'])[:10]
    indices.append({'type': 'index', 'date': date_str, 'name': name, 'code': sym[2:],
                    'close': round(close, 2), 'pct_change': round(pct, 2), 'note': '收盘20:00'})
    print(f'  {name}: {date_str} close={close:.2f} pct={pct:+.2f}%')

# ---------- 2. 港股指数 spot ----------
hk_map = {'HSI': '恒生指数', 'HSTECH': '恒生科技'}
try:
    hk = retry(ak.stock_hk_index_spot_sina)
    if hk is not None:
        for _, row in hk.iterrows():
            nm = str(row.get('name', ''))
            for code, cname in hk_map.items():
                if code in str(row.get('code', '')) or (code == 'HSI' and '恒生指数' in nm) or (code == 'HSTECH' and '恒生科技' in nm):
                    indices.append({'type': 'index', 'date': TODAY, 'name': cname, 'code': code,
                                    'close': round(float(row['latest']), 2), 'pct_change': round(float(row['changepercent']), 2),
                                    'note': '收盘20:00'})
                    print(f'  {cname}: {row["latest"]} pct={row["changepercent"]}%')
    else:
        print('  WARN 港股指数数据暂缺')
except Exception as e:
    print('  WARN 港股接口异常:', e)

# ---------- 3. 场内 ETF ----------
etf_codes = {'513050': '中概互联', '159928': '消费ETF添富', '159938': '医药ETF广发',
             '512170': '医疗ETF', '513180': '恒指科技', '515180': '100红利',
             '159920': '恒生ETF华夏', '512880': '证券ETF', '512980': '传媒ETF'}
etfs = []
try:
    spot = retry(ak.fund_etf_spot_em)
    if spot is not None:
        for _, row in spot.iterrows():
            code = str(row['代码'])
            if code in etf_codes:
                etfs.append({'date': TODAY, 'code': code, 'name': etf_codes[code],
                             'price': round(float(row['最新价']), 3), 'pct': round(float(row['涨跌幅']), 2),
                             'amount_wan': round(float(row['成交额']), 1), 'note': '收盘20:00'})
                print(f'  ETF {etf_codes[code]} {code}: {row["最新价"]} pct={row["涨跌幅"]}%')
    else:
        print('  WARN 场内ETF数据暂缺')
except Exception as e:
    print('  WARN ETF接口异常:', e)

# ---------- 4. 个股收盘 ----------
stocks = {}
for sym, nm in [('sz002410', '广联达'), ('sh600438', '通威股份')]:
    df = retry(ak.stock_zh_a_daily, symbol=sym, adjust='qfq')
    if df is None or len(df) < 2:
        print(f'  WARN 个股 {nm} 数据暂缺')
        continue
    last = df.iloc[-1]; prev = df.iloc[-2]
    close = float(last['close']); prev_close = float(prev['close'])
    pct = (close / prev_close - 1) * 100
    stocks[nm] = {'date': str(last['date'])[:10], 'close': round(close, 2), 'pct': round(pct, 2)}
    print(f'  {nm}: {stocks[nm]}')

# ---------- 5. 场外基金净值 ----------
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
fund_navs = []
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
    fund_navs.append({'date': TODAY, 'code': code, 'name': nm, 'nav_date': nav_date,
                      'nav': nav, 'pct': round(pct, 2) if pct is not None else None})
    print(f'  {nm}: nav_date={nav_date} nav={nav} pct={pct}')

# ---------- 6. 美股（8/10 收盘，用于事件回填） ----------
us = {}
for sym, nm in [('XLV', '美股医疗XLV'), ('IYH', '美股医疗IYH')]:
    df = retry(ak.stock_us_daily, symbol=sym)
    if df is None or len(df) < 2:
        print(f'  WARN 美股 {nm} 数据暂缺')
        continue
    last = df.iloc[-1]; prev = df.iloc[-2]
    close = float(last['close']); prev_close = float(prev['close'])
    pct = (close / prev_close - 1) * 100
    us[sym] = {'date': str(last['date'])[:10], 'close': round(close, 2), 'pct': round(pct, 2)}
    print(f'  {nm}: {us[sym]}')

# ---------- 汇总输出 ----------
out = {'date': TODAY, 'indices': indices, 'etf': etfs, 'stocks': stocks, 'fund_navs': fund_navs, 'us': us}
with open(os.path.join(HIST, 'close_20260811.json'), 'w', encoding='utf-8') as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
print('\nDONE -> close_20260811.json')
