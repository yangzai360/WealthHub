# -*- coding: utf-8 -*-
"""补齐 indices.csv 中 000300（沪深300）的日线缺口（§3.116d 待办闭环）
- 目标：distinct 交易日数 ≥ 20（当前 17）
- 数据源：akshare stock_zh_index_daily('sh000300')（新浪源，§3.84 接口清单内）
- 仅补「2026-08-06 起、且 indices.csv 中缺失」的交易日行；已有日期不动
- 用整行判重（type,date,name,code,close,pct,note），追加前备份 + git diff 复核
输出：indices.csv 增量行
"""
import csv, os, shutil, json
import akshare as ak

BASE = '/Users/jieyang/Documents/WealthHub'
HIST = os.path.join(BASE, 'data/processed/history')
P = os.path.join(HIST, 'indices.csv')
START = '2026-08-06'

rows = list(csv.reader(open(P, encoding='utf-8-sig')))
header, body = rows[0], rows[1:]
print('header:', header)
exist = {tuple(r) for r in body}
have_days = sorted({r[1] for r in body if len(r) > 3 and r[3] == '000300'})
print(f'000300 现有 distinct 日 = {len(have_days)}')

df = ak.stock_zh_index_daily(symbol='sh000300')
df['date'] = df['date'].astype(str)
df = df[df['date'] >= START].reset_index(drop=True)
print(f'akshare 返回 {len(df)} 行（自 {START}）：{df["date"].iloc[0]} ~ {df["date"].iloc[-1]}')

cand = []
prev = None
for i, r in enumerate(df.itertuples(index=False)):
    d = str(r.date)
    close = round(float(r.close), 2)
    if prev is None:
        # 起点无前收 → 用 df 首行前一交易日不可得，取当日 pct 置 0 并标注
        pct = 0.0
    else:
        pct = round((close / prev - 1) * 100, 2)
    prev = close
    row = ['index', d, '沪深300', '000300', str(close), str(pct), '盘后补录(新浪日线,§3.116d)']
    if d not in have_days:
        cand.append(row)

# 起点行（df 首行）若 pct=0 不可信，剔除该行（避免写入伪 0%）
cand = [r for r in cand if r[1] != str(df['date'].iloc[0])]
print(f'待补 {len(cand)} 行：{[r[1] for r in cand]}')

if cand:
    shutil.copy2(P, P + '.bak')
    data = open(P, 'rb').read()
    assert data[:3] == b'\xef\xbb\xbf', 'indices.csv 缺 BOM，终止'
    assert data.endswith(b'\n'), '末行无换行，终止'
    eol = b'\r\n' if data.endswith(b'\r\n') else b'\n'
    buf = b''.join((','.join(r) + '\n').encode('utf-8').replace(b'\n', eol) for r in cand)
    with open(P, 'ab') as f:
        f.write(buf)
    print(f'✅ indices.csv +{len(cand)} 行（已备份 {P}.bak）')
else:
    print('无需补写')

rows2 = list(csv.reader(open(P, encoding='utf-8-sig')))
have2 = sorted({r[1] for r in rows2[1:] if len(r) > 3 and r[3] == '000300'})
print(f'补后 000300 distinct 日 = {len(have2)}（门槛 20）→ {"PASS" if len(have2) >= 20 else "STILL FAIL"}')
