# -*- coding: utf-8 -*-
"""盘前档 2026-09-17：且慢长赢(LONG_WIN) playwright 兜底数据落库（§3.82 规则：mtime 最新 + 校验 composition）
   - plan 详情 → composition-2026-09-17.json + meta.json（含 nav_date_beijing）
   - nav-history 增量：本次经核对**不追加**（源序列近期数值与本地已落库行不再 1:1 匹配，见输出诊断）
口径（§3.86 定论）: ms 时间戳 = 北京时间零点；本地按 UTC 日期落库（= 真实净值日 -1 天）
"""
import json, os, glob, datetime

BASE = '/Users/jieyang/Documents/WealthHub'
NAV = os.path.join(BASE, 'data/processed/reference/long-win-nav.csv')
REF = os.path.join(BASE, 'reference-portfolios/long-win')
TODAY = '2026-09-17'
BJ = datetime.timezone(datetime.timedelta(hours=8))

# ---------- 1. plan 详情 ----------
cands = sorted(glob.glob('/tmp/qieman_pw_plan_*.json'), key=os.path.getmtime, reverse=True)
plan = None
for c in cands:
    try:
        p = json.load(open(c, encoding='utf-8'))
        if isinstance(p, dict) and ('composition' in p or 'prodSummaries' in p):
            plan = p
            print(f'plan 源: {c} ({os.path.getsize(c)} bytes)')
            break
    except Exception:
        pass
if plan is None:
    raise SystemExit('未找到含 composition/prodSummaries 的 plan 响应')

data = plan.get('data', plan)
comp = data.get('composition')
prods = data.get('prodSummaries')
navd = data.get('navDate')
nav_bj = datetime.datetime.fromtimestamp(navd / 1000, BJ).strftime('%Y-%m-%d') if navd else None
print(f"adjustedCount={data.get('adjustedCount')} nav={data.get('nav')} navDate={navd} (北京 {nav_bj}) "
      f"dailyReturn={data.get('dailyReturn')} sharpe={data.get('sharpe')} maxDD={data.get('maxDrawdown')}")

meta_path = os.path.join(REF, 'meta.json')
old_meta = json.load(open(meta_path, encoding='utf-8')) if os.path.exists(meta_path) else {}
old_cnt = old_meta.get('adjustedCount')
new_cnt = data.get('adjustedCount')
print(f'本地 meta.adjustedCount={old_cnt} vs 源={new_cnt} -> '
      f'{"无新调仓" if old_cnt == new_cnt else "⚠️ 有新调仓，需人工复核"}')

snap = {'poCode': 'LONG_WIN', 'date': TODAY,
        'source': 'playwright 兜底 (qieman.com/longwin 页面响应)',
        'composition': comp,
        'prodSummaries_count': len(prods) if prods else 0,
        'prodSummaries': prods}
json.dump(snap, open(os.path.join(REF, f'composition-{TODAY}.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)

meta = dict(old_meta)
meta.update({
    'poCode': 'LONG_WIN',
    'last_checked': TODAY,
    'adjustedCount': new_cnt,
    'nav': data.get('nav'),
    'navDate': navd,
    'nav_date_beijing': nav_bj,
    'dailyReturn': data.get('dailyReturn'),
    'sharpe': data.get('sharpe'),
    'maxDrawdown': data.get('maxDrawdown'),
    'volatility': data.get('volatility'),
    'latest_adj_id': old_meta.get('latest_adj_id', 781),
    'latest_adj_date': old_meta.get('latest_adj_date', '2026-07-30'),
    'composition_snapshot': f'composition-{TODAY}.json',
})
json.dump(meta, open(meta_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(f'已更新 {meta_path}')

# ---------- 2. nav-history 诊断（本次不追加） ----------
f = sorted(glob.glob('/tmp/qieman_pw_nav-history_*.json'), key=os.path.getmtime)[-1]
nav = json.load(open(f, encoding='utf-8'))
src = {}
for it in nav[-16:]:
    d = datetime.datetime.fromtimestamp(it['navDate'] / 1000, BJ).strftime('%Y-%m-%d')
    src[d] = (round(float(it['nav']), 6), round(float(it.get('dailyReturn') or 0) * 100, 4))
loc = {}
for line in open(NAV, encoding='utf-8-sig').read().strip().split('\n')[1:]:
    p = line.split(',')
    if len(p) < 2 or not p[1]:
        continue
    loc[p[0]] = float(p[1])

print('\n=== nav-history 源(北京时间) vs 本地(UTC 口径) 对齐诊断 ===')
hit = 0
tot = 0
for d, (v, r) in sorted(src.items()):
    prev = (datetime.datetime.strptime(d, '%Y-%m-%d') - datetime.timedelta(days=1)).strftime('%Y-%m-%d')
    lv = loc.get(prev)
    ok = lv is not None and abs(lv - v) < 1e-6
    tot += 1
    hit += 1 if ok else 0
    print(f'  源 {d} nav={v:.6f} ret={r:+.4f}%  ->  本地 {prev} nav={lv if lv else "--"}  {"匹配" if ok else "不匹配"}')
print(f'  -> 近 {tot} 个源日期中 {hit} 个与本地「-1 天」行数值精确匹配')
print(f'  -> 本地最新 {max(loc)}；源最新(北京) {max(src)}；**本档不追加任何行**（避免污染，待用户决策口径修正）')
