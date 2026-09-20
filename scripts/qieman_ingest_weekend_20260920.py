# -*- coding: utf-8 -*-
"""2026-09-20 周日盘后档：且慢长赢(LONG_WIN) playwright 兜底数据落库（§3.82：mtime 最新 + 校验 composition）
   - nav-history 增量 → data/processed/reference/long-win-nav.csv（判重：日期存在则视为源修订，不追加，§3.89）
   - plan 详情 → composition-2026-09-20.json + meta.json
   - §3.93 三重交叉验证：adjustedCount / investedUnit / composition 逐品种 planUnit 差分
口径（§3.86 定论）: ms 时间戳 = 北京时间零点 → 本地按 UTC 日期落库（= 真实净值日 -1 天），沿用既有口径不回写
"""
import json, os, glob, datetime, subprocess

BASE = '/Users/jieyang/Documents/WealthHub'
NAV = os.path.join(BASE, 'data/processed/reference/long-win-nav.csv')
REF = os.path.join(BASE, 'reference-portfolios/long-win')
TODAY = '2026-09-20'
PREV_SNAP = 'reference-portfolios/long-win/composition-2026-09-18.json'

# ---------- 0. REST adjustments 是否仍空 ----------
adj_files = sorted(glob.glob('/tmp/qieman_pw_adjustments_*.json'))
rest_empty = (len(adj_files) == 0)
print(f'REST adjustments 响应文件数: {len(adj_files)}（0 表示仍空 body）')

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
print('源末 4 行(UTC 口径 / 括号内为北京时间净值日):')
for it in nav[-4:]:
    du = datetime.datetime.fromtimestamp(it['navDate'] / 1000, datetime.timezone.utc).strftime('%Y-%m-%d')
    db = datetime.datetime.fromtimestamp(it['navDate'] / 1000,
                                         datetime.timezone(datetime.timedelta(hours=8))).strftime('%Y-%m-%d')
    print(f"   {du} ({db}) nav={it['nav']} ret={it.get('dailyReturn')}")

# ---------- 2. plan 详情 ----------
cands = sorted(glob.glob('/tmp/qieman_pw_plan_*.json'), key=os.path.getmtime, reverse=True)
plan = None
for c in cands:
    try:
        p = json.load(open(c, encoding='utf-8'))
        if isinstance(p, dict) and ('composition' in p or 'prodSummaries' in p):
            plan = p
            print(f'\nplan 源: {c} ({os.path.getsize(c)} bytes)')
            break
    except Exception:
        pass

if plan:
    data = plan
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
    old_count = meta.get('adjustedCount')
    for k in ('nav', 'navDate', 'dailyReturn', 'sharpe', 'maxDrawdown', 'volatility',
              'annualCompoundedReturn', 'investedUnit', 'adjustedCount', 'joinedCount',
              'activeCount', 'totalUnit'):
        if k in data:
            meta[k] = data[k]
    meta['followers'] = {'joined': data.get('joinedCount', (meta.get('followers') or {}).get('joined')),
                         'active': data.get('activeCount', (meta.get('followers') or {}).get('active'))}
    meta['updated'] = TODAY
    nd_raw = data.get('navDate')
    nd = (datetime.datetime.fromtimestamp(nd_raw / 1000, datetime.timezone.utc).strftime('%Y-%m-%d')
          if isinstance(nd_raw, (int, float)) and nd_raw > 1e11 else str(nd_raw)[:10])
    meta['navDate'] = nd
    meta['nav_date_beijing'] = (datetime.datetime.fromtimestamp(
        nd_raw / 1000, datetime.timezone(datetime.timedelta(hours=8))).strftime('%Y-%m-%d')
        if isinstance(nd_raw, (int, float)) and nd_raw > 1e11 else nd)
    meta['snapshot'] = {'nav_date': nd, 'nav': data.get('nav'), 'daily_return': data.get('dailyReturn'),
                        'from_setup_return': data.get('fromSetupReturn'),
                        'annual_compounded_return': data.get('annualCompoundedReturn'),
                        'invested_acr': data.get('investedACR'),
                        'max_drawdown': data.get('maxDrawdown'), 'volatility': data.get('volatility'),
                        'sharpe': data.get('sharpe')}
    json.dump(meta, open(os.path.join(REF, 'meta.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('meta updated:', json.dumps({k: meta[k] for k in ('nav', 'navDate', 'nav_date_beijing',
                                                            'sharpe', 'maxDrawdown', 'volatility',
                                                            'investedUnit', 'adjustedCount') if k in meta},
                                      ensure_ascii=False))
    print(f'adjustedCount: 本地旧 {old_count} → 源 {data.get("adjustedCount")}')

    # ---------- 3. composition 逐品种 planUnit 差分（§3.93，对照 git HEAD 的 9/18 版本） ----------
    print('\n【composition 逐品种 planUnit 差分】(对照 9/18 归档版本)')
    try:
        old = json.loads(subprocess.run(['git', 'show', f'HEAD:{PREV_SNAP}'], cwd=BASE,
                                        capture_output=True, text=True, check=True).stdout)
    except Exception as e:
        print('  取回旧快照失败:', e)
        old = None
    if old:
        def pmap(c):
            m = {}
            for x in (c or []):
                k = f"{x.get('fundCode') or x.get('code')}|{x.get('fundName') or x.get('name')}"
                m[k] = x.get('planUnit')
            return m
        mo, mn = pmap(old.get('composition')), pmap(comp)
        diffs = []
        for k in sorted(set(mo) | set(mn)):
            if mo.get(k) != mn.get(k):
                diffs.append((k, mo.get(k), mn.get(k)))
        print(f'  品种数 旧 {len(mo)} / 新 {len(mn)}；合计 planUnit 旧 {sum(v for v in mo.values() if v is not None)} '
              f'/ 新 {sum(v for v in mn.values() if v is not None)}')
        if diffs:
            for k, o, n in diffs:
                print(f'   ⚠️ 变化: {k}  planUnit {o} → {n}')
        else:
            print('  ✅ 无品种变动（E大无新调仓）')
else:
    print('⚠️ 未找到含 composition 的 plan 响应')

# ---------- 4. 调仓列表比对 ----------
adj = json.load(open(os.path.join(REF, 'adjustments.json'), encoding='utf-8'))
m = json.load(open(os.path.join(REF, 'meta.json'), encoding='utf-8'))
print(f"\n本地 adjustments count={adj['count']} / 列表 {len(adj['adjustments'])} 条")
print(f"meta.adjustedCount={m.get('adjustedCount')}（口径差 {len(adj['adjustments']) - (m.get('adjustedCount') or 0)}）")

print('\n本地 long-win-nav.csv 末 6 行:')
for l in open(NAV, encoding='utf-8-sig').read().strip().split('\n')[-6:]:
    print('   ', l)
