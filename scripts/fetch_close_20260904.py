# -*- coding: utf-8 -*-
"""2026-09-04 盘后档行情抓取: A股指数日线收盘/港股hq直取/场内ETF收盘/场外基金当日净值+QDII补更/个股真实收盘
输出 data/processed/history/close_20260904.json"""
import json, os, time, re, urllib.request

BASE = '/Users/jieyang/Documents/WealthHub'
HIST = os.path.join(BASE, 'data/processed/history')
TODAY = '2026-09-04'
OUT = os.path.join(HIST, f'close_{TODAY.replace("-", "")}.json')

import akshare as ak

result = {'date': TODAY, 'indices': [], 'hk': [], 'etf': [], 'fund_navs': [], 'stocks': []}

def retry(fn, n=2, desc=''):
    for i in range(n + 1):
        try:
            return fn()
        except Exception as e:
            print(f'  [{desc}] 第{i+1}次失败: {e}')
            time.sleep(2)
    return None

# ---------- 1. A股指数收盘（日线接口末两行） ----------
a_idx = {'sh000001': ('上证指数', '000001'), 'sz399001': ('深证成指', '399001'),
         'sz399006': ('创业板指', '399006'), 'sh000932': ('中证消费', '000932')}
for sym, (name, code) in a_idx.items():
    def _f(sym=sym):
        df = ak.stock_zh_index_daily(symbol=sym)
        return df.tail(2)
    df = retry(_f, desc=f'A股指数 {sym}')
    if df is not None and len(df) >= 2:
        prev_c, cur_c = float(df.iloc[-2]['close']), float(df.iloc[-1]['close'])
        pct = round((cur_c / prev_c - 1) * 100, 2)
        result['indices'].append({'type': 'index', 'date': TODAY, 'name': name, 'code': code,
                                  'close': round(cur_c, 2), 'pct_change': pct, 'note': '收盘20:00(日线)'})
        print(f'  A股 {name} {round(cur_c,2)} {pct}%')
    else:
        print(f'  A股 {name} 数据暂缺')
        result['indices'].append({'type': 'index', 'date': TODAY, 'name': name, 'code': code,
                                  'close': None, 'pct_change': None, 'note': '收盘20:00(日线)'})

# ---------- 2. 港股收盘（hq.sinajs.cn 直取） ----------
def fetch_hq():
    req = urllib.request.Request('https://hq.sinajs.cn/list=hkHSI,hkHSTECH',
                                 headers={'Referer': 'https://finance.sina.com.cn'})
    with urllib.request.urlopen(req, timeout=10) as resp:
        return resp.read().decode('gbk', errors='ignore')
hq_txt = retry(fetch_hq, n=2, desc='港股 hq')
hk_data = {}
if hq_txt:
    for line in hq_txt.strip().split('\n'):
        m = re.match(r'var hq_str_hk(HSTECH|HSI)="(.*?)"', line.strip())
        if m:
            code, payload = m.group(1), m.group(2)
            parts = payload.split(',')
            if len(parts) > 8:
                # hk 格式: name,engname,open,prev_close,high,low,last,change,change_pct,... (parts[6]=收盘/最新)
                try:
                    last = float(parts[6])
                    prev = float(parts[3])
                    pct = round((last / prev - 1) * 100, 2)
                    hk_data[code] = (last, pct)
                    print(f'  hq {code}: {last} {pct}%')
                except Exception as e:
                    print(f'  hq {code} 解析失败: {e}')
else:
    print('  hq 全部失败')

hk_map = {'HSI': ('恒生指数', 'HSI'), 'HSTECH': ('恒生科技', 'HSTECH')}
for c, (name, code) in hk_map.items():
    if c in hk_data:
        result['hk'].append({'type': 'index', 'date': TODAY, 'name': name, 'code': code,
                             'close': hk_data[c][0], 'pct_change': hk_data[c][1], 'note': '收盘20:00(新浪hq直取)'})
    else:
        print(f'  港股 {name} 数据暂缺(待WebSearch补录)')

# ---------- 3. 场内 ETF 收盘 ----------
etf_codes = {'513050': '中概互联', '159928': '消费ETF添富', '159938': '医药ETF广发',
             '512170': '医疗ETF', '513180': '恒指科技', '159920': '恒生ETF华夏',
             '512880': '证券ETF', '515180': '100红利', '512980': '传媒ETF'}
def _spot():
    df = ak.fund_etf_spot_em()
    df['code'] = df['代码'].astype(str)
    return df
df = retry(_spot, desc='ETF spot')
if df is not None:
    for code, name in etf_codes.items():
        row = df[df['code'] == code]
        if len(row):
            r = row.iloc[0]
            result['etf'].append({'date': TODAY, 'code': code, 'name': name,
                                  'price': float(r['最新价']), 'pct': float(r['涨跌幅']),
                                  'amount_wan': float(r['成交额']), 'note': '收盘20:00'})
            print(f'  ETF {name} {r["最新价"]} {r["涨跌幅"]}%')
        else:
            print(f'  ETF {name} {code} 数据暂缺')
else:
    print('  ETF spot 抓取失败')

# ---------- 4. 场外基金净值（当日已出 + QDII 补更） ----------
funds = [
    # (code, name, type) type: a=A股基金(T+1), q=QDII(T+1~T+2)
    ('002708', '大摩健康产业', 'a'), ('000968', '广发养老产业', 'a'), ('002742', '泓德裕祥债券', 'a'),
    ('004752', '广发传媒联接A', 'a'), ('005368', '富国清洁能源', 'a'), ('110020', '易方达沪深300联接', 'a'),
    ('000369', '广发全球医疗A', 'q'), ('100032', '富国红利增强A', 'a'), ('001180', '广发医药卫生', 'a'),
    ('161616', '融通医疗保健', 'a'), ('000051', '华夏沪深300联接', 'a'), ('519915', '富国消费主题', 'a'),
    ('000071', '华夏恒生ETF联接A', 'q'), ('012348', '天弘恒生科技A', 'q'), ('001551', '天弘医药100C', 'a'),
    ('164906', '交银海外互联A', 'q'), ('000248', '汇添富主要消费A', 'a'), ('016280', '广发全球医疗C', 'q'),
    ('001469', '广发金融地产', 'a'), ('001552', '天弘证券保险', 'a'), ('012323', '华宝中证医疗C', 'a'),
    ('000727', '融通健康产业A/B', 'a'), ('004424', '汇添富文体娱乐', 'a'),
]

def _nav(code):
    df = ak.fund_open_fund_info_em(symbol=code, indicator='单位净值走势')
    return df.tail(3)
for code, name, ftype in funds:
    df = retry(lambda c=code: _nav(c), desc=f'基金 {name}')
    if df is not None and len(df):
        for _, r in df.iterrows():
            nav_date = str(r['净值日期'])[:10]
            nav = float(r['单位净值'])
            pct = float(r['日增长率']) if str(r['日增长率']) not in ('', 'nan', 'None') else None
            result['fund_navs'].append({'code': code, 'name': name, 'nav_date': nav_date,
                                        'nav': nav, 'pct': pct})
        newest = df.iloc[-1]
        print(f'  基金 {name} 最新净值日期 {str(newest["净值日期"])[:10]} nav={newest["单位净值"]}')
    else:
        print(f'  基金 {name} 抓取失败')

with open(OUT, 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=1)
print(f'\nSAVED {OUT}')
print(f'indices {len(result["indices"])} / hk {len(result["hk"])} / etf {len(result["etf"])} / fund_navs {len(result["fund_navs"])}')
