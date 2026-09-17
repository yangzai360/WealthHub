# -*- coding: utf-8 -*-
"""2026-09-17 盘后档：且慢长赢(LONG_WIN) playwright 兜底数据落库（§3.82 规则：mtime 最新 + 校验 composition）
   - nav-history 增量 → data/processed/reference/long-win-nav.csv
   - plan 详情 → composition-2026-09-17.json + meta.json
口径（§3.86 定论）: ms 时间戳 = 北京时间零点 → 本地按 UTC 日期落库（= 真实净值日 -1 天），沿用既有口径不回写
"""
import json, os, glob, datetime

BASE = '/Users/jieyang/Documents/WealthHub'
NAV = os.path.join(BASE, 'data/processed/reference/long-win-nav.csv')
REF = os.path.join(BASE, 'reference-portfolios/long-win')
TODAY = '2026-09-17'

# ---------- 1. nav-history 增量 ----------
f = sorted(glob.glob('/tmp/qieman_pw_nav-history_*.json'), key=os.path.getmtime)[-1]
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
print('源末 3 行(UTC 口径):')
for it in nav[-3:]:
    d = datetime.datetime.fromtimestamp(it['navDate'] / 1000, datetime.timezone.utc).strftime('%Y-%m-%d')
    print(f"   {d} nav={it['nav']} ret={it.get('dailyReturn')}")

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
    snap = {'poCode': 'LONG_WIN', 'date': TODAY,
            'source': 'playwright 兜底 (qieman.com/longwin 页面响应)',
            'composition': comp,
            'prodSummaries_count': len(prods) if prods else 0,
            'prodSummaries': prods}
    out = os.path.join(REF, f'composition-{TODAY}.json')
    json.dump(snap, open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'SAVED {out}')
    meta = json.load(open(os.path.join(REF, 'meta.json'), encoding='utf-8'))
    for k in ('nav', 'navDate', 'dailyReturn', 'sharpe', 'maxDrawdown', 'volatility',
              'annualCompoundedReturn', 'investedUnit', 'adjustedCount', 'followers', 'totalUnit'):
        if k in data:
            meta[k] = data[k]
    meta['updated'] = TODAY
    nd_raw = data.get('navDate')
    nd = (datetime.datetime.fromtimestamp(nd_raw / 1000, datetime.timezone.utc).strftime('%Y-%m-%d')
          if isinstance(nd_raw, (int, float)) and nd_raw > 1e11 else str(nd_raw)[:10])
    meta['navDate'] = nd
    meta['nav_date_beijing'] = (datetime.datetime.fromtimestamp(nd_raw / 1000, datetime.timezone(datetime.timedelta(hours=8))).strftime('%Y-%m-%d')
                                if isinstance(nd_raw, (int, float)) and nd_raw > 1e11 else nd)
    meta['snapshot'] = {'nav_date': nd, 'nav': data.get('nav'), 'daily_return': data.get('dailyReturn'),
                        'from_setup_return': data.get('fromSetupReturn'),
                        'annual_compounded_return': data.get('annualCompoundedReturn'),
                        'invested_acr': data.get('investedAcr'),
                        'max_drawdown': data.get('maxDrawdown'), 'volatility': data.get('volatility'),
                        'sharpe': data.get('sharpe')}
    json.dump(meta, open(os.path.join(REF, 'meta.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('meta updated:', json.dumps({k: meta[k] for k in ('nav', 'navDate', 'nav_date_beijing', 'sharpe', 'maxDrawdown', 'volatility', 'adjustedCount') if k in meta}, ensure_ascii=False))

# ---------- 3. 调仓比对 ----------
adj = json.load(open(os.path.join(REF, 'adjustments.json'), encoding='utf-8'))
m = json.load(open(os.path.join(REF, 'meta.json'), encoding='utf-8'))
print(f"\n本地 adjustments count={adj['count']} / 列表 {len(adj['adjustments'])} 条")
print(f"meta.adjustedCount={m.get('adjustedCount')}")
print(f"源 adjustedCount={plan.get('adjustedCount') if plan else 'NA'}")
last = sorted(adj['adjustments'], key=lambda x: x.get('adjustmentId') or x.get('adjustment_id') or 0)[-1]
print(f"本地最新调仓: id={last.get('adjustmentId') or last.get('adjustment_id')} date={last.get('txnDate') or last.get('txn_date')}")

# ---------- 4. 本地 nav 序列尾部核对 ----------
print('\n本地 long-win-nav.csv 末 6 行:')
lines = open(NAV, encoding='utf-8-sig').read().strip().split('\n')
for l in lines[-6:]:
    print('   ', l)
