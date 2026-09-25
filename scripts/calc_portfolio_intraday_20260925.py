# -*- coding: utf-8 -*-
"""2026-09-25 盘中档：组合口径计算（A股休市 → 当日可实现盈亏 = 0；港股增量 → 9/28 待消化）
⚠️ §3.104：赛道基准必须用 mv + est_pnl 还原（mv0 口径坑），并加硬守卫
⚠️ 情绪：同时给出「名义净情绪分」与「暴露加权净分」（§3.104 第四形态）
"""
import json, os, glob, csv, re

BASE = '/Users/jieyang/Documents/WealthHub'
TODAY = '2026-09-25'
HIST = os.path.join(BASE, 'data/processed/history')

# ---------- 1. 基准：9/24 收盘修正链式（portfolio_close_20260924_fix.json） ----------
fix = json.load(open(os.path.join(HIST, 'portfolio_close_20260924_fix.json'), encoding='utf-8'))
print('fix keys:', list(fix.keys()))
# ⚠️ 口径修正（本档新发现，§3.107）：`*_fix.json` 中 `tracks[track].mv` 已是「修正后收盘市值」，
#    可直接作次日基准；`detail[].mv` 是继承旧值且与 mv0/est_pnl 不自洽（例：广联达 mv=38617.6
#    但 mv0+est_pnl=37631.99）→ 二者不可混用。守卫加在 Σ tracks.mv vs total_mv 上。
total_mv = fix.get('total_mv')
tracks = fix.get('tracks') or {}
restored = {tr: v.get('mv') for tr, v in tracks.items() if v.get('mv') is not None}
s = sum(restored.values())
print(f'total_mv(文件) = {total_mv}')
print(f'Σ tracks.mv    = {s:.2f}')
if total_mv:
    assert abs(s - total_mv) < 1.5, f'硬守卫失败: Σ tracks.mv {s:.2f} vs total_mv {total_mv}'
print('✅ 硬守卫通过：Σ tracks[track].mv == total_mv')
for k, v in sorted(restored.items(), key=lambda x: -x[1]):
    print(f'  {k:12s} {v:>12,.2f} 元  {v/s*100:>6.2f}%')
BASE_TOTAL = s
print(f'基准总资产 = {BASE_TOTAL:,.2f} 元')

# ---------- 2. 本档港股盘中（intraday_hq_20260925.json） ----------
hq = json.load(open(os.path.join(HIST, 'intraday_hq_20260925.json'), encoding='utf-8'))
print('\n=== 港股指数 ===')
for k, v in hq['indices_hk'].items():
    print(f"  {k:10s} {v['cur']:>11.3f} {v['pct']:>+7.2f}%  H{v['high']} L{v['low']}")
print('=== 港股个股 ===')
for k, v in hq['hk_stocks'].items():
    print(f"  {k:16s} {v['cur']:>9.2f} {v['pct']:>+7.2f}%")

hstech = hq['indices_hk']['恒生科技']['pct']
hsi = hq['indices_hk']['恒生指数']['pct']
hstech_cur = hq['indices_hk']['恒生科技']['cur']

# ---------- 3. 组合当日（A股休市） ----------
print('\n=== 组合当日估算 ===')
print('A股/场外基金/场内ETF 全部不可定价 → 当日可实现盈亏 = 0.00 元（0.000%）')
print(f'估算总资产维持 = {BASE_TOTAL:,.2f} 元')

# 9/28 待消化（恒生科技赛道，混合代理）
hk_mv = restored.get('恒生科技', 0)
proxy_low = hstech                      # 恒生科技指数
proxy_high = -1.70                      # 中概互联 proxy（阿里/腾讯/京东/美团/百度 简单均值）
mid = (proxy_low + proxy_high) / 2
print(f'\n=== 恒生科技赛道「9/28 待消化」 ===')
print(f'  赛道市值 {hk_mv:,.2f} 元（{hk_mv/BASE_TOTAL*100:.2f}%）')
for nm, p in (('恒生科技指数代理', proxy_low), ('中概互联 proxy', proxy_high), ('混合中枢', mid)):
    print(f'  {nm:14s} {p:+.2f}%  → {hk_mv*p/100:+,.2f} 元')
print(f'  区间: {hk_mv*proxy_high/100:+,.2f} ~ {hk_mv*proxy_low/100:+,.2f} 元')

# ---------- 4. 情绪（名义 + 暴露加权） ----------
sent = json.load(open(os.path.join(BASE, f'data/processed/news/sentiment-{TODAY}.json'), encoding='utf-8'))
win = [x for x in sent['items'] if x.get('window') == '盘中(07:30-13:30)']
print(f'\n=== 情绪（盘中窗口 {len(win)} 条） ===')
from collections import defaultdict
byt = defaultdict(lambda: {'n': 0, 'net': 0, 'sum': 0, 'pos': 0, 'neg': 0, 'neu': 0})
for x in win:
    t = byt[x['track']]
    t['n'] += 1
    t['sum'] += x['strength']
    if x['direction'] == '利多':
        t['net'] += x['strength']; t['pos'] += 1
    elif x['direction'] == '利空':
        t['net'] -= x['strength']; t['neg'] += 1
    else:
        t['neu'] += 1
nominal = sum(v['net'] for v in byt.values())
print(f'名义净情绪分（Σ利多强度 − Σ利空强度）= {nominal:+.1f}')
print(f"{'赛道':12s} {'n':>3s} {'均值强度':>8s} {'净分':>8s} {'权重':>7s} {'加权':>8s}")
wsum = 0.0
for t, v in sorted(byt.items(), key=lambda x: -x[1]['n']):
    w = restored.get(t)
    if w is None:
        print(f"{t:12s} {v['n']:>3d} {v['sum']/v['n']:>8.1f} {v['net']:>+8.1f}   (无直接暴露)      —")
        continue
    wt = w / BASE_TOTAL
    contrib = wt * (v['net'] / v['n'])
    wsum += contrib
    print(f"{t:12s} {v['n']:>3d} {v['sum']/v['n']:>8.1f} {v['net']:>+8.1f} {wt*100:>6.2f}% {contrib:>+8.3f}")
print(f'暴露加权净分 = {wsum:+.3f}（单位：强度分 × 权重；负值=按持仓暴露折算后偏负）')

# ---------- 5. 防线 ----------
print('\n=== 防线状态 ===')
c = json.load(open(os.path.join(HIST, 'event_stats_intraday_20260925.json'), encoding='utf-8'))
idx = defaultdict(dict)
with open(os.path.join(HIST, 'indices.csv'), encoding='utf-8-sig') as fh:
    for row in csv.DictReader(fh):
        try:
            idx[row['code']][row['date']] = float(row['close'])
        except Exception:
            pass
cons = idx.get('000932', {}).get('2026-09-24')
hk25 = hstech_cur
print(f'  大消费下沿 000932 = {cons} (9/24 收盘，A股休市无更新)  距 12,100 = {(cons-12100)/12100*100:+.3f}%')
print(f'  恒生科技下沿 HSTECH = {hk25} (9/25 盘中)  距 4,250 = {(hk25-4250)/4250*100:+.3f}%')
print(f'  恒生科技自 9/22 高点 4,510.06 = {(hk25/4510.06-1)*100:+.3f}%')
print(f'  恒生科技距 4,400 = {(hk25-4400)/4400*100:+.3f}%')

# ---------- 6. 敏感性 ----------
print('\n=== 敏感性（9/28 恒生科技赛道） ===')
for nm, p in (('乐观（恒科 −1.00%）', -1.00), ('中枢（−1.45%）', -1.45), ('悲观（−1.80%）', -1.80)):
    print(f'  {nm:20s} {hk_mv*p/100:>+10,.2f} 元  （占基准 {hk_mv*p/100/BASE_TOTAL*100:+.3f}%）')
