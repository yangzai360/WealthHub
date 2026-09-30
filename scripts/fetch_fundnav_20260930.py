# -*- coding: utf-8 -*-
"""2026-09-30 盘中：场外基金净值检查（天天基金 F10 直连）+ 增量写入 fund_nav.csv
重点：①QDII 000369/016280 是否出 9/29 净值（对应美股 9/29 收盘 IYH -0.36%）
      ②164906 是否出 9/29 净值 ③A股类基金 9/29 净值是否已入库（盘前档已入 3 行）
⚠️ §3.108：fund_nav.csv 判重键 = (code, nav_date)，不含归档日；该文件无 BOM、纯 LF → 禁止统一 BOM 断言
"""
import json, os, time, urllib.request, csv
from collections import Counter

BASE = '/Users/jieyang/Documents/WealthHub'
HIST = os.path.join(BASE, 'data/processed/history')
TODAY = '2026-09-30'
OUT = os.path.join(HIST, 'fundnav_' + TODAY.replace('-', '') + '.json')
CSV_PATH = os.path.join(HIST, 'fund_nav.csv')

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

data = {'date': TODAY, 'fund_navs': navs}
json.dump(data, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

print('\n净值日分布(>=9/24):', dict(Counter(n['nav_date'] for n in navs if n['nav_date'] >= '2026-09-24')))

# ---------- 增量写入 fund_nav.csv（判重键 = (code, nav_date)，§3.108） ----------
exist = set()
raw = open(CSV_PATH, 'rb').read()
print(f"fund_nav.csv 属性自检：BOM={'有' if raw[:3]==b'\\xef\\xbb\\xbf' else '无'}  "
      f"CRLF行数={raw.count(b'\\r\\n')}  末尾EOL={'CRLF' if raw.endswith(b'\\r\\n') else 'LF'}")
with open(CSV_PATH, encoding='utf-8-sig') as fh:
    rd = csv.reader(fh)
    header = next(rd)
    for r in rd:
        if len(r) >= 6:
            # ⚠️ 实际列序 = date,code,name,nav_date,nav,pct → 判重键取 (r[1], r[3])（§3.108）
            exist.add((r[1].strip(), r[3].strip()))
print("CSV 表头:", header)
assert header[:4] == ['date', 'code', 'name', 'nav_date'], f"列序与预期不符: {header}"

new_rows = []
for n in navs:
    key = (n['code'], n['nav_date'])
    if key in exist:
        continue
    exist.add(key)
    pv = '' if n['pct'] is None else f"{n['pct']:.2f}"
    new_rows.append([TODAY, n['code'], n['name'], n['nav_date'], f"{n['nav']:.4f}", pv])
if new_rows:
    eol = b'\r\n' if raw.endswith(b'\r\n') else b'\n'
    buf = b''.join(','.join(str(x) for x in r).encode('utf-8') + eol for r in new_rows)
    with open(CSV_PATH, 'ab') as fh:
        fh.write(buf)
print(f"\nfund_nav.csv +{len(new_rows)} 行")
for r in new_rows:
    print("  NEW", r)

print('\n=== >=9/26 净值明细 ===')
for n in sorted(navs, key=lambda x: (x['nav_date'], x['code'])):
    if n['nav_date'] >= '2026-09-26':
        print(f"  {n['nav_date']}  {n['code']}  {n['name']:22s} {n['nav']:>8.4f}  {str(n['pct']):>7}%")
print('\n抓取失败:', fail)
