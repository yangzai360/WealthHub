# -*- coding: utf-8 -*-
"""2026-09-25 盘后档：且慢 LONG_WIN 落库 + E大调仓三重交叉验证 + nav 口径比对
输出：
  reference-portfolios/long-win/composition-2026-09-25-close.json
  reference-portfolios/long-win/meta.json（更新）
  data/processed/history/qieman_close_20260925.json（本档摘要）
"""
import json, os, glob, datetime, csv

BASE = '/Users/jieyang/Documents/WealthHub'
NAVCSV = os.path.join(BASE, 'data/processed/reference/long-win-nav.csv')
REF = os.path.join(BASE, 'reference-portfolios/long-win')
TODAY = '2026-09-25'
TAG = '20260925c'
BJ = datetime.timezone(datetime.timedelta(hours=8))

# ---------- 1. plan ----------
cands = sorted(glob.glob(f'/tmp/qieman_pwc_plan_{TAG}_*.json'), key=os.path.getmtime, reverse=True)
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
comp = data.get('composition')
navd = data.get('navDate')
nav_bj = datetime.datetime.fromtimestamp(navd / 1000, BJ).strftime('%Y-%m-%d') if navd else None
print(f"adjustedCount={data.get('adjustedCount')} investedUnit={data.get('investedUnit')} "
      f"nav={data.get('nav')} navDate(北京)={nav_bj} dailyReturn={data.get('dailyReturn')}")
for k in ('sharpe', 'maxDrawdown', 'volatility', 'totalReturn', 'followerCount', 'activeFollowerCount'):
    if k in data:
        print(f'  {k} = {data[k]}')

meta_path = os.path.join(REF, 'meta.json')
old_meta = json.load(open(meta_path, encoding='utf-8')) if os.path.exists(meta_path) else {}
print(f"\n本地 meta.adjustedCount={old_meta.get('adjustedCount')} vs 源={data.get('adjustedCount')}"
      f" -> {'无新调仓' if old_meta.get('adjustedCount') == data.get('adjustedCount') else '⚠️ 有新调仓'}")
print(f"本地 meta.investedUnit={old_meta.get('investedUnit')} vs 源={data.get('investedUnit')}"
      f" -> {'投入份数不变' if old_meta.get('investedUnit') == data.get('investedUnit') else '⚠️ 投入份数变化'}")


def flatten(c):
    d, cls = {}, {}
    if not c:
        return d, cls
    for cl in c:
        cls[cl.get('className')] = cl.get('unit')
        for it in (cl.get('compList') or []):
            fu = it.get('fund') or {}
            d[fu.get('fundCode') or it.get('variety') or fu.get('fundName')] = it.get('planUnit')
    return d, cls


new_pu, new_cls = flatten(comp)
print(f'\ncomposition 品种数={len(new_pu)} planUnit 合计={sum(v for v in new_pu.values() if v)} 类别数={len(new_cls)}')

# 两个基线：① 9/24（跨档基线，判 E大新调仓）② 本日 13:45 版（判盘中→盘后是否变动）
for label, path in [('昨晚档基线(9/24)', os.path.join(REF, 'composition-2026-09-24.json')),
                    ('本日盘中档(13:45)', os.path.join(REF, 'composition-2026-09-25.json'))]:
    if not os.path.exists(path):
        print(f'\n[{label}] 快照不存在，跳过')
        continue
    pu, cls = flatten(json.load(open(path, encoding='utf-8')).get('composition'))
    diffs = [(k, pu.get(k), new_pu.get(k)) for k in set(pu) | set(new_pu) if pu.get(k) != new_pu.get(k)]
    cdiffs = [(k, cls.get(k), new_cls.get(k)) for k in set(cls) | set(new_cls) if cls.get(k) != new_cls.get(k)]
    print(f'\n=== 对照 {label}（品种 {len(pu)}，planUnit 合计 {sum(v for v in pu.values() if v)}） ===')
    print('  品种 planUnit：' + ('无变动 ✅' if not diffs else str(diffs)))
    print('  类别 unit：' + ('无变动 ✅' if not cdiffs else str(cdiffs)))

# ---------- 2. 落库 ----------
snap = {'poCode': 'LONG_WIN', 'date': TODAY, 'session': 'close',
        'source': 'playwright 兜底 (qieman.com/longwin 页面响应，REST pmdj 连续第 92 日空 body)',
        'nav': data.get('nav'), 'navDate_bj': nav_bj, 'dailyReturn': data.get('dailyReturn'),
        'adjustedCount': data.get('adjustedCount'), 'investedUnit': data.get('investedUnit'),
        'composition': comp, 'prodSummaries_count': len(data.get('prodSummaries') or [])}
json.dump(snap, open(os.path.join(REF, f'composition-{TODAY}-close.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
print(f'\n已归档 composition-{TODAY}-close.json')

new_meta = dict(old_meta)
new_meta.update({'date': TODAY, 'nav': data.get('nav'), 'navDate_bj': nav_bj,
                 'dailyReturn': data.get('dailyReturn'), 'adjustedCount': data.get('adjustedCount'),
                 'investedUnit': data.get('investedUnit')})
json.dump(new_meta, open(meta_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('已更新 meta.json')

# ---------- 3. nav-history 口径比对（§3.97/§3.99：不追加、不回写） ----------
navf = sorted(glob.glob(f'/tmp/qieman_pwc_nav_{TAG}_*.json'), key=os.path.getmtime, reverse=True)
src_rows = []
if navf:
    raw = json.load(open(navf[0], encoding='utf-8'))
    lst = raw
    if isinstance(lst, dict):
        lst = lst.get('data', lst)
        if isinstance(lst, dict):
            lst = lst.get('list') or lst.get('navList') or []
    if not isinstance(lst, list):
        lst = []
    for it in lst:
        ts = it.get('navDate') or it.get('date') or it.get('ts')
        if ts is None:
            continue
        if isinstance(ts, (int, float)):
            d = datetime.datetime.fromtimestamp(ts / 1000, BJ).strftime('%Y-%m-%d')
        else:
            d = str(ts)[:10]
        src_rows.append((d, it.get('nav')))
    print(f'\nnav-history 源 {len(src_rows)} 条；最新 8 条:')
    for d, v in src_rows[-8:]:
        print(f'   {d}  {v}')

loc = []
if os.path.exists(NAVCSV):
    with open(NAVCSV, encoding='utf-8-sig') as fh:
        for row in csv.reader(fh):
            if len(row) >= 2:
                loc.append((row[0][:10], row[1]))
loc = [x for x in loc if x[0][:2] == '20']
loc.sort()
print(f'本地 long-win-nav.csv {len(loc)} 条；最新 5 条:')
for d, v in loc[-5:]:
    print(f'   {d}  {v}')
src_last = src_rows[-1] if src_rows else None
loc_last = loc[-1] if loc else None
print(f'\n源最新 {src_last} | 本地最新 {loc_last} -> '
      f'{"同日期" if src_last and loc_last and src_last[0] == loc_last[0] else "⚠️ 口径分歧（按 §3.97/§3.99 不追加、不回写）"}')

out = {'date': TODAY, 'session': 'close', 'rest_all_empty': True,
       'plan_bytes': os.path.getsize(cands[0]) if cands else 0,
       'nav_bytes': os.path.getsize(navf[0]) if navf else 0,
       'adjustedCount': data.get('adjustedCount'), 'investedUnit': data.get('investedUnit'),
       'nav': data.get('nav'), 'navDate_bj': nav_bj, 'dailyReturn': data.get('dailyReturn'),
       'new_adjustment': old_meta.get('adjustedCount') != data.get('adjustedCount'),
       'nav_src_latest': src_last, 'nav_local_latest': loc_last,
       'nav_serial_divergence': not (src_last and loc_last and src_last[0] == loc_last[0]),
       'policy': '按 §3.97/§3.99：源与本地口径分歧时不追加、不回写（用户决策项）'}
json.dump(out, open(os.path.join(BASE, f'data/processed/history/qieman_close_{TODAY.replace("-","")}.json'), 'w',
                    encoding='utf-8'), ensure_ascii=False, indent=1)
print(f'\n已保存 qieman_close_{TODAY.replace("-","")}.json')
