#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""2026-09-21 盘后档：且慢 long-win-nav.csv 时区口径修复（最小侵入）

背景（本档发现）:
  qieman nav-history 的 navDate 是「北京时间 00:00」的毫秒时间戳。
  用 datetime.timezone.utc 转换会得到「北京日期 - 1 天」。
  本档入库脚本误用 UTC → 最新一行被写成 2026-09-20（实为 2026-09-21）。

本次仅做两处「无歧义」修正（不做全量重写，历史段偏移问题另行专项处理）:
  1) 末行 2026-09-20 → 2026-09-21（该 nav 的 BJ+8 日期为 9/21，且 9/20 为周日非交易日）
  2) 补入缺失的 2026-09-18 行（源存在，本地缺失）
"""
import csv, json, glob, os, shutil, datetime
from zoneinfo import ZoneInfo

REPO = '/Users/jieyang/Documents/WealthHub'
CSV = os.path.join(REPO, 'data/processed/reference/long-win-nav.csv')
BJ = ZoneInfo('Asia/Shanghai')

# ---- 读源（playwright 兜底产物）----
fs = sorted(glob.glob('/tmp/qieman_pw_nav-history_*.json'), key=os.path.getmtime)
assert fs, '未找到 nav-history 源文件'
src = {}
for it in json.load(open(fs[-1], encoding='utf-8')):
    d = datetime.datetime.fromtimestamp(it['navDate'] / 1000, BJ).strftime('%Y-%m-%d')
    src[d] = round(float(it['nav']), 6)

# ---- 读本地 ----
rows = [l.split(',') for l in open(CSV, encoding='utf-8-sig').read().strip().split('\n')]
header, body = rows[0], [r for r in rows[1:] if r and r[0]]

shutil.copy2(CSV, CSV + '.bak-20260921')
print('备份 →', CSV + '.bak-20260921')

by_date = {r[0]: r for r in body}

# 修正 1: 末行日期 9/20 → 9/21
last = body[-1]
if last[0] == '2026-09-20' and abs(float(last[1]) - src.get('2026-09-21', 0)) < 1e-4:
    last[0] = '2026-09-21'
    print(f'修正1: 末行日期 2026-09-20 → 2026-09-21 (nav={last[1]}, pct={last[2]})')
else:
    print('修正1: 末行无需修正')

# 修正 2: 补 2026-09-18
if '2026-09-18' not in by_date and '2026-09-18' in src:
    prev = float(by_date['2026-09-17'][1])
    nav18 = src['2026-09-18']
    pct18 = (nav18 / prev - 1) * 100
    idx = [i for i, r in enumerate(body) if r[0] == '2026-09-17'][0]
    body.insert(idx + 1, ['2026-09-18', f'{nav18:.6f}', f'{pct18:.4f}'])
    print(f'修正2: 补入 2026-09-18 nav={nav18:.6f} pct={pct18:+.4f}% (基准 9/17={prev})')
else:
    print('修正2: 2026-09-18 已存在或源缺失，跳过')

body.sort(key=lambda r: r[0])
with open(CSV, 'w', encoding='utf-8-sig', newline='') as f:
    w = csv.writer(f)
    w.writerow(header)
    for r in body:
        w.writerow(r)
print(f'写入完成: 总行 {len(body)}')

# ---- 校验 ----
chk = {l.split(',')[0]: l.split(',')[1] for l in open(CSV, encoding='utf-8-sig').read().strip().split('\n')[1:] if l}
print('\n尾部 6 行校验:')
for d in sorted(chk)[-6:]:
    s = src.get(d)
    tag = 'OK' if s and abs(float(chk[d]) / s - 1) * 100 < 0.02 else ('源缺' if not s else 'DIFF')
    print(f'  {d} local={chk[d]:<12s} src={s if s else "-":<12} {tag}')
dups = len(chk) != len([l for l in open(CSV, encoding='utf-8-sig').read().strip().split('\n')[1:] if l])
print('重复日期:', '有' if dups else '无')
