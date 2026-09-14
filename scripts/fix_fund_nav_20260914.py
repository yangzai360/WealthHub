# -*- coding: utf-8 -*-
"""修正 fund_nav.csv 归档日=2026-09-14 的重复行（同 date+code+nav_date 多条，name 口径不一致）
保留首次出现（盘前档写入的规范 name），删除本次追加的重复行。
并重试 3 只 A股类基金 9/14 净值（F10 直连）。"""
import csv, os, collections, json, urllib.request, time

BASE = '/Users/jieyang/Documents/WealthHub'
HIST = os.path.join(BASE, 'data/processed/history')
P = os.path.join(HIST, 'fund_nav.csv')
TODAY = '2026-09-14'

with open(P, encoding='utf-8-sig') as f:
    lines = [l for l in f.read().splitlines() if l.strip()]
header, data = lines[0], lines[1:]

seen = set(); keep = []; dropped = []
for ln in data:
    parts = ln.split(',')
    key = (parts[0], parts[1], parts[3])
    if key in seen:
        dropped.append(ln)
        continue
    seen.add(key); keep.append(ln)

with open(P, 'w', encoding='utf-8') as f:
    f.write(header + '\n')
    for ln in keep:
        f.write(ln + '\n')
print(f'去重完成: 保留 {len(keep)} 行，删除 {len(dropped)} 行')
for d in dropped:
    print('  -', d)

# ---- 重试 3 只 A股类基金 9/14 净值 ----
def f10_nav(code, size=8):
    url = f'https://api.fund.eastmoney.com/f10/lsjz?fundCode={code}&pageIndex=1&pageSize={size}'
    req = urllib.request.Request(url, headers={
        'Referer': 'https://fundf10.eastmoney.com/',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode('utf-8'))

retry_list = [('002708', '大摩健康产业混合A'), ('002742', '泓德裕祥债券A'), ('012323', '华宝中证医疗C')]
add_rows = []
for code, name in retry_list:
    ok = False
    for i in range(3):
        try:
            d = f10_nav(code)
            rows = d['Data']['LSJZList']
            print(f'  {name}({code}) 最新 {rows[0].get("FSRQ")} nav={rows[0].get("DWJZ")} pct={rows[0].get("JZZZL")}')
            if str(rows[0].get('FSRQ'))[:10] == TODAY:
                for r in rows:
                    if str(r.get('FSRQ'))[:10] == TODAY:
                        add_rows.append([TODAY, code, name, TODAY, r.get('DWJZ'), r.get('JZZZL')])
                ok = True
            break
        except Exception as e:
            print(f'  {name} 第{i+1}次失败: {e}'); time.sleep(2)
    if not ok:
        print(f'  {name} 9/14 净值暂未出（T+1）')

if add_rows:
    existing = set(l for l in open(P, encoding='utf-8-sig').read().splitlines()[1:] if l.strip())
    with open(P, 'a', encoding='utf-8') as f:
        for r in add_rows:
            ln = ','.join(str(x) for x in r)
            if ln not in existing:
                f.write(ln + '\n'); print('  +', ln)

with open(P, encoding='utf-8-sig') as f:
    print('最终 fund_nav.csv 数据行:', len([l for l in f.read().splitlines() if l.strip()]) - 1)
