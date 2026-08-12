# -*- coding: utf-8 -*-
"""盘后档 2026-08-12 增量写入 indices.csv / etf_intraday.csv / fund_nav.csv（含港股手动补录）"""
import json, os, csv

BASE = '/Users/jieyang/Documents/WealthHub'
HIST = os.path.join(BASE, 'data/processed/history')
TODAY = '2026-08-12'

def load_rows(path):
    if not os.path.exists(path):
        return []
    with open(path, encoding='utf-8-sig') as f:
        return list(csv.DictReader(f))

def append_rows(path, header, rows):
    new = not os.path.exists(path)
    with open(path, 'a', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=header)
        if new:
            w.writeheader()
        for r in rows:
            w.writerow({k: str(r.get(k, '')) for k in header})

# ---------- 1. indices.csv ----------
idx_header = ['type', 'date', 'name', 'code', 'close', 'pct_change', 'note']
idx_exist = load_rows(os.path.join(HIST, 'indices.csv'))
idx_keys = {(r['type'], r['date'], r['name'], r['note']) for r in idx_exist}

new_indices = [
    # A股日线
    {'type': 'index', 'date': '2026-08-12', 'name': '上证指数', 'code': '000001', 'close': 3946.68, 'pct_change': 0.32, 'note': '收盘20:00'},
    {'type': 'index', 'date': '2026-08-12', 'name': '创业板指', 'code': '399006', 'close': 3602.08, 'pct_change': 1.49, 'note': '收盘20:00'},
    {'type': 'index', 'date': '2026-08-12', 'name': '中证消费', 'code': '000932', 'close': 12823.67, 'pct_change': 0.25, 'note': '收盘20:00'},
    # 港股手动补录（spot 接口失败，来自收盘新闻确认）
    {'type': 'index', 'date': '2026-08-12', 'name': '恒生指数', 'code': 'HSI', 'close': 25440.17, 'pct_change': -0.83, 'note': '收盘20:00'},
    {'type': 'index', 'date': '2026-08-12', 'name': '恒生科技', 'code': 'HSTECH', 'close': 4776.44, 'pct_change': -0.99, 'note': '收盘20:00'},
    # 美股 8/11 收盘（XLV/IYH 新浪补更）
    {'type': 'us_index', 'date': '2026-08-11', 'name': '美股医疗XLV', 'code': 'XLV', 'close': 168.01, 'pct_change': -0.26, 'note': '美股收盘(8/11)'},
    {'type': 'us_index', 'date': '2026-08-11', 'name': '美股医疗IYH', 'code': 'IYH', 'close': 70.89, 'pct_change': -0.35, 'note': '美股收盘(8/11)'},
]
to_add = [r for r in new_indices if (r['type'], r['date'], r['name'], r['note']) not in idx_keys]
append_rows(os.path.join(HIST, 'indices.csv'), idx_header, to_add)
print(f'indices.csv: 新增 {len(to_add)} 行')

# ---------- 2. etf_intraday.csv ----------
etf_header = ['date', 'code', 'name', 'price', 'pct', 'amount_wan', 'note']
etf_exist = load_rows(os.path.join(HIST, 'etf_intraday.csv'))
etf_keys = {(r['date'], r['code'], r['note']) for r in etf_exist}

etf_data = json.load(open(os.path.join(HIST, 'close_20260812.json')))['etf']
etf_rows = [{'date': e['date'], 'code': e['code'], 'name': e['name'], 'price': e['price'],
             'pct': e['pct'], 'amount_wan': e['amount_wan'], 'note': e['note']} for e in etf_data]
to_add = [r for r in etf_rows if (r['date'], r['code'], r['note']) not in etf_keys]
append_rows(os.path.join(HIST, 'etf_intraday.csv'), etf_header, to_add)
print(f'etf_intraday.csv: 新增 {len(to_add)} 行')

# ---------- 3. fund_nav.csv（按 (code, nav_date) 去重） ----------
fund_header = ['date', 'code', 'name', 'nav_date', 'nav', 'pct']
fund_exist = load_rows(os.path.join(HIST, 'fund_nav.csv'))
fund_keys = {(r['code'], r['nav_date']) for r in fund_exist}

fund_navs = json.load(open(os.path.join(HIST, 'close_20260812.json')))['fund_navs']
to_add = []
for f in fund_navs:
    if (f['code'], f['nav_date']) not in fund_keys:
        to_add.append({'date': f['date'], 'code': f['code'], 'name': f['name'],
                       'nav_date': f['nav_date'], 'nav': f['nav'], 'pct': f['pct']})
append_rows(os.path.join(HIST, 'fund_nav.csv'), fund_header, to_add)
print(f'fund_nav.csv: 新增 {len(to_add)} 行 (按 code+nav_date 去重)')

print('DONE')
