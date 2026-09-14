# -*- coding: utf-8 -*-
"""2026-09-14 且慢长赢(LONG_WIN) playwright 兜底数据落库
   - nav-history 增量 → data/processed/reference/long-win-nav.csv
   - plan 详情 → reference-portfolios/long-win/composition-2026-09-14.json + meta.json
口径沿用 §3.78/上次脚本: navDate ms → UTC 日期 为净值日（= 北京时间 -1 天）"""
import json, os, glob, datetime

BASE = '/Users/jieyang/Documents/WealthHub'
NAV = os.path.join(BASE, 'data/processed/reference/long-win-nav.csv')
REF = os.path.join(BASE, 'reference-portfolios/long-win')
TODAY = '2026-09-14'

# ---------- 1. nav-history 增量 ----------
f = sorted(glob.glob('/tmp/qieman_pw_nav-history_*.json'), key=os.path.getsize)[-1]
nav = json.load(open(f, encoding='utf-8'))
rows = []
for it in nav:
    d = datetime.datetime.fromtimestamp(it['navDate'] / 1000, datetime.timezone.utc).strftime('%Y-%m-%d')
    rows.append((d, round(float(it['nav']), 6),
                 round(float(it['dailyReturn']) * 100, 4) if it.get('dailyReturn') is not None else ''))
existing = set()
if os.path.exists(NAV):
    for line in open(NAV, encoding='utf-8-sig').read().strip().split('\n')[1:]:
        if line:
            existing.add(line.split(',')[0])
add = [r for r in rows if r[0] not in existing]
with open(NAV, 'a', encoding='utf-8') as fh:
    for r in add:
        fh.write(','.join(str(x) for x in r) + '\n')
print(f'nav-history: 源 {len(rows)} 条, 本地已有 {len(existing)} 日, 新增 {len(add)} 行')
for r in add:
    print('   +', r)

# ---------- 2. plan 详情 ----------
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

if plan:
    data = plan.get('data', plan)
    comp = data.get('composition')
    prods = data.get('prodSummaries')
    meta = json.load(open(os.path.join(REF, 'meta.json'), encoding='utf-8'))
    snap = {
        'poCode': 'LONG_WIN',
        'date': TODAY,
        'source': 'playwright 兜底 (qieman.com/longwin 页面响应)',
        'composition': comp,
        'prodSummaries_count': len(prods) if prods else 0,
        'prodSummaries': prods,
    }
    out = os.path.join(REF, f'composition-{TODAY}.json')
    json.dump(snap, open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'SAVED {out}')
    for k in ('nav', 'navDate', 'dailyReturn', 'sharpe', 'maxDrawdown', 'volatility',
              'annualCompoundedReturn', 'investedUnit', 'adjustedCount', 'followers', 'totalUnit'):
        if k in data:
            meta[k] = data[k]
    meta['updated'] = TODAY
    nd_raw = data.get('navDate', meta.get('snapshot', {}).get('nav_date'))
    if isinstance(nd_raw, (int, float)) and nd_raw > 1e11:   # ms 时间戳 → 日期串（§3.78）
        nd = datetime.datetime.fromtimestamp(nd_raw / 1000, datetime.timezone.utc).strftime('%Y-%m-%d')
    else:
        nd = str(nd_raw)[:10]
    meta['navDate'] = nd
    meta['snapshot'] = {
        'nav_date': nd,
        'nav': data.get('nav'), 'daily_return': data.get('dailyReturn'),
        'from_setup_return': data.get('fromSetupReturn'),
        'annual_compounded_return': data.get('annualCompoundedReturn'),
        'invested_acr': data.get('investedAcr'),
        'max_drawdown': data.get('maxDrawdown'), 'volatility': data.get('volatility'),
        'sharpe': data.get('sharpe'),
    }
    json.dump(meta, open(os.path.join(REF, 'meta.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('meta updated:', json.dumps({k: meta[k] for k in ('nav', 'navDate', 'sharpe', 'maxDrawdown', 'volatility', 'adjustedCount') if k in meta}, ensure_ascii=False))
else:
    print('⚠️ 未找到含 composition/prodSummaries 的 plan 响应')

# ---------- 3. 调仓记录比对 ----------
adj = json.load(open(os.path.join(REF, 'adjustments.json'), encoding='utf-8'))
print(f"本地 adjustments: count={adj['count']} / 列表 {len(adj['adjustments'])} 条; meta.adjust_count={json.load(open(os.path.join(REF,'meta.json'),encoding='utf-8')).get('adjust_count')}")
print('→ E大新调仓判定: 见上方 adjustedCount 与本地比对')
