# -*- coding: utf-8 -*-
"""2026-09-24 盘后：抓取场外基金净值（天天基金 F10 直连，§3.79）+ 合并进 close_20260924.json
§3.95：pageSize=8 + 扫描 lst[:4]（补 T+1/T+2 中间缺口）
"""
import json, os, time, urllib.request
from collections import Counter

BASE = '/Users/jieyang/Documents/WealthHub'
HIST = os.path.join(BASE, 'data/processed/history')
TODAY = '2026-09-24'
OUT = os.path.join(HIST, 'close_' + TODAY.replace('-', '') + '.json')

funds = [
    ('002708', '大摩健康产业混合A'), ('000968', '广发养老产业'), ('002742', '泓德裕祥债券A'),
    ('004752', '广发传媒联接A'), ('005368', '富国清洁能源'), ('110020', '易方达沪深300联接'),
    ('000369', '广发全球医疗A'), ('100032', '富国红利增强A'), ('001180', '广发医药卫生'),
    ('161616', '融通医疗保健'), ('000051', '华夏沪深300联接'), ('519915', '富国消费主题'),
    ('000071', '华夏恒生ETF联接A'), ('012348', '天弘恒生科技A'), ('001551', '天弘医药100C'),
    ('164906', '交银海外互联A'), ('000248', '汇添富主要消费A'), ('016280', '广发全球医疗C'),
    ('001469', '广发金融地产'), ('001552', '天弘证券保险'), ('012323', '华宝中证医疗C'),
    ('000727', '融通健康产业A/B'), ('004424', '汇添富文体娱乐'),
]


def f10_nav(code, size=8):
    url = f'https://api.fund.eastmoney.com/f10/lsjz?fundCode={code}&pageIndex=1&pageSize={size}'
    req = urllib.request.Request(url, headers={
        'Referer': 'https://fundf10.eastmoney.com/',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode('utf-8'))


navs = []
fail = []
for code, name in funds:
    d = None
    for i in range(3):
        try:
            d = f10_nav(code)
            break
        except Exception as e:
            print(f'  [{name}] 第{i+1}次失败 {e}')
            time.sleep(2)
    if d and d.get('Data') and d['Data'].get('LSJZList'):
        rows = d['Data']['LSJZList'][:4]
        for r in rows:
            nd = str(r.get('FSRQ', ''))[:10]
            try:
                nav = round(float(r.get('DWJZ')), 4)
            except Exception:
                continue
            pr = r.get('JZZZL')
            try:
                p = float(pr) if pr not in ('', None) else None
            except Exception:
                p = None
            navs.append({'code': code, 'name': name, 'nav_date': nd, 'nav': nav, 'pct': p})
        print(f'  {name}({code}) 最新 {rows[0].get("FSRQ")} {rows[0].get("DWJZ")} {rows[0].get("JZZZL")}%')
    else:
        fail.append((code, name))
        print(f'  {name}({code}) 抓取失败/无数据')

data = json.load(open(OUT, encoding='utf-8'))
data['fund_navs'] = navs
json.dump(data, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

c = Counter(n['nav_date'] for n in navs if n['nav_date'] >= '2026-09-11')
print('\n净值日分布(>=9/11):', dict(c))
t = [n for n in navs if n['nav_date'] == TODAY]
print(f'\n已出 {TODAY} 净值 {len(t)} 只:')
for n in sorted(t, key=lambda x: -(x['pct'] or 0)):
    print(f"  {n['name']:20s} {n['code']} {n['nav']:.4f} {n['pct']:+.2f}%")
print(f'\n抓取失败 {len(fail)} 只: {fail}')
print(f'SAVED {OUT}  fund_navs={len(navs)}')
