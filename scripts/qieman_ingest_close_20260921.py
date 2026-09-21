# -*- coding: utf-8 -*-
"""2026-09-21 盘后档：且慢长赢(LONG_WIN) playwright 兜底数据落库（§3.82 / §3.93 / §3.94 规则）
   - plan 详情 → composition-2026-09-21.json（覆盖盘中 13:47 版）+ meta.json
   - 新调仓判定：adjustedCount / investedUnit / composition 逐品种 planUnit 三重交叉验证
     ⚠️ §3.94：composition 为两层嵌套 [{className, classCode, unit, compList:[{fund:{fundCode,...}, planUnit}]}]
   - nav-history 增量：判重必须同时比对 nav 值（§3.94：同日期值不同 = 源修订，不追加）
口径（§3.86 定论）: ms 时间戳 = 北京时间零点；本地按 UTC 日期落库（= 真实净值日 -1 天）
"""
import json, os, glob, datetime, subprocess

BASE = '/Users/jieyang/Documents/WealthHub'
NAV = os.path.join(BASE, 'data/processed/reference/long-win-nav.csv')
REF = os.path.join(BASE, 'reference-portfolios/long-win')
TODAY = '2026-09-21'
BJ = datetime.timezone(datetime.timedelta(hours=8))


def pmap(comp):
    """逐品种 planUnit 映射（§3.94 两层嵌套适配）"""
    out = {}
    for cl in comp or []:
        for it in (cl.get('compList') or []):
            f = it.get('fund') or {}
            k = f.get('fundCode') or it.get('variety') or it.get('code')
            if k:
                out[k] = (it.get('planUnit'), f.get('fundName') or it.get('name') or k)
    return out


# ---------- 1. 新 plan 响应（mtime 最新 + 含 composition） ----------
cands = sorted(glob.glob('/tmp/qieman_pw_plan_*.json'), key=os.path.getmtime, reverse=True)
plan = None
for c in cands:
    try:
        p = json.load(open(c, encoding='utf-8'))
        if isinstance(p, dict) and 'composition' in (p.get('data', p)):
            plan = p
            print(f'plan 源: {c} ({os.path.getsize(c)} bytes)')
            break
    except Exception:
        pass
if plan is None:
    raise SystemExit('未找到含 composition 的 plan 响应')
data = plan.get('data', plan)
new_comp = data.get('composition')

# ---------- 2. 旧 composition（git HEAD = 盘中 13:47 版） ----------
old_comp = None
try:
    raw = subprocess.run(['git', '--no-pager', 'show', 'HEAD:reference-portfolios/long-win/composition-2026-09-21.json'],
                         capture_output=True, text=True, cwd=BASE).stdout
    old_comp = json.loads(raw).get('composition')
    print('旧 composition 源: git HEAD（盘中 13:47 版）')
except Exception as e:
    print('读取 git HEAD 旧 composition 失败:', e)
if old_comp is None:
    old_comp = json.load(open(os.path.join(REF, f'composition-{TODAY}.json'), encoding='utf-8')).get('composition')
    print('旧 composition 源: 本地文件（可能已是盘后版，差分失效）')

# ---------- 3. 三重交叉验证 ----------
meta = json.load(open(os.path.join(REF, 'meta.json'), encoding='utf-8'))
print(f"\n[E大调仓三重交叉验证]")
print(f"  adjustedCount: 本地 {meta.get('adjustedCount')} → 源 {data.get('adjustedCount')}")
print(f"  investedUnit : 本地 {meta.get('investedUnit')} → 源 {data.get('investedUnit')}")
om, nm = pmap(old_comp), pmap(new_comp)
old_sum = sum(v[0] or 0 for v in om.values())
new_sum = sum(v[0] or 0 for v in nm.values())
print(f"  planUnit 合计: 旧 {old_sum} → 新 {new_sum}（品种数 旧 {len(om)} → 新 {len(nm)}）")
diffs = [(k, om.get(k, (None,))[0], nm.get(k, (None,))[0], nm.get(k, (None, ''))[1])
         for k in sorted(set(om) | set(nm)) if om.get(k, (None,))[0] != nm.get(k, (None,))[0]]
if diffs:
    print('  ⚠️ 逐品种 planUnit 变动:')
    for k, a, b, n in diffs:
        print(f'    {k} {n}: {a} → {b}')
else:
    print('  ✅ 逐品种 planUnit 零变动')
oc = {c.get('classCode'): c.get('unit') for c in old_comp or []}
nc = {c.get('classCode'): c.get('unit') for c in new_comp or []}
unit_diff = {k: (oc.get(k), nc.get(k)) for k in set(oc) | set(nc) if oc.get(k) != nc.get(k)}
print(f"  资产类别 unit 变动: {unit_diff if unit_diff else '全部持平'}")

# ---------- 4. 落库 ----------
data_out = {'poCode': 'LONG_WIN', 'date': TODAY,
            'source': 'playwright 兜底 (qieman.com/longwin 页面响应)',
            'composition': new_comp,
            'prodSummaries_count': len(data.get('prodSummaries') or []),
            'prodSummaries': data.get('prodSummaries')}
out = os.path.join(REF, f'composition-{TODAY}.json')
json.dump(data_out, open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(f'SAVED {out}')

for k in ('nav', 'navDate', 'dailyReturn', 'sharpe', 'maxDrawdown', 'volatility',
          'annualCompoundedReturn', 'investedUnit', 'adjustedCount', 'followers', 'totalUnit'):
    if k in data:
        meta[k] = data[k]
meta['updated'] = TODAY
nd_raw = data.get('navDate')
nd = (datetime.datetime.fromtimestamp(nd_raw / 1000, BJ).strftime('%Y-%m-%d')
      if isinstance(nd_raw, (int, float)) and nd_raw > 1e11 else str(nd_raw)[:10])
meta['navDate'] = nd
meta['nav_date_beijing'] = (datetime.datetime.fromtimestamp(nd_raw / 1000, BJ).strftime('%Y-%m-%d')
                            if isinstance(nd_raw, (int, float)) and nd_raw > 1e11 else nd)
meta['snapshot'] = {'nav_date': nd, 'nav': data.get('nav'), 'daily_return': data.get('dailyReturn'),
                    'from_setup_return': data.get('fromSetupReturn'),
                    'annual_compounded_return': data.get('annualCompoundedReturn'),
                    'invested_acr': data.get('investedAcr'),
                    'max_drawdown': data.get('maxDrawdown'), 'volatility': data.get('volatility'),
                    'sharpe': data.get('sharpe')}
json.dump(meta, open(os.path.join(REF, 'meta.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('meta updated:', json.dumps({k: meta.get(k) for k in
      ('nav', 'navDate', 'nav_date_beijing', 'dailyReturn', 'sharpe', 'maxDrawdown', 'volatility',
       'adjustedCount', 'investedUnit')}, ensure_ascii=False))

# ---------- 5. nav-history 增量（§3.94：判重须比对 nav 值） ----------
f = sorted(glob.glob('/tmp/qieman_pw_nav-history_*.json'), key=os.path.getmtime)[-1]
nav = json.load(open(f, encoding='utf-8'))
rows = []
for it in nav:
    d = datetime.datetime.fromtimestamp(it['navDate'] / 1000, BJ).strftime('%Y-%m-%d')
    rows.append((d, round(float(it['nav']), 6),
                 round(float(it['dailyReturn']) * 100, 4) if it.get('dailyReturn') is not None else ''))
existing = {}
if os.path.exists(NAV):
    for line in open(NAV, encoding='utf-8-sig').read().strip().split('\n')[1:]:
        if line:
            p = line.split(',')
            existing[p[0]] = p[1]
add, revised = [], []
for r in rows:
    if r[0] not in existing:
        add.append(r)
    elif str(r[1]) != existing[r[0]]:
        revised.append((r[0], existing[r[0]], r[1]))
with open(NAV, 'a', encoding='utf-8') as fh:
    for r in add:
        fh.write(','.join(str(x) for x in r) + '\n')
print(f'\nnav-history: 源 {len(rows)} 条, 本地已有 {len(existing)} 日, 新增 {len(add)} 行（§3.94 判重含 nav 值比对）')
for r in add:
    print('   +', r)
print(f'源修订（同日期 nav 值不同，按 §3.94 不追加）{len(revised)} 条:')
for r in revised[-6:]:
    print('   ~', r)
print('源末 3 行(UTC 口径):')
for it in nav[-3:]:
    d = datetime.datetime.fromtimestamp(it['navDate'] / 1000, BJ).strftime('%Y-%m-%d')
    print(f"   {d} nav={it['nav']} ret={it.get('dailyReturn')}")

adj = json.load(open(os.path.join(REF, 'adjustments.json'), encoding='utf-8'))
print(f"\nadjustments.json: count={adj['count']} / 列表 {len(adj['adjustments'])} 条；meta.adjustedCount={meta.get('adjustedCount')}")
print('\n本地 long-win-nav.csv 末 5 行:')
for l in open(NAV, encoding='utf-8-sig').read().strip().split('\n')[-5:]:
    print('   ', l)
