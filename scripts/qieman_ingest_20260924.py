# -*- coding: utf-8 -*-
"""盘中档 2026-09-24：且慢长赢(LONG_WIN) playwright 兜底数据落库（§3.82：mtime 最新 + 校验 composition）
   - plan 详情 → composition-2026-09-24.json + meta.json（含 nav_date_beijing）
   - 新调仓判定：adjustedCount / investedUnit / composition planUnit 三重交叉验证（§3.93 + §3.94 嵌套坑修正）
口径（§3.86/§3.97 定论）: ms 时间戳 = 北京时间零点 → 一律用 ZoneInfo('Asia/Shanghai') 转换，
                         禁止用 timezone.utc（会得到「北京日期 − 1 天」）
本档 REST pmdj adjustments 仍空 body（连续第 90 日）→ playwright 兜底
⚠️ 本档对照基线改为「mtime 最新的 composition 快照」（= 2026-09-23-close），避免 intraday/close 命名差异漏比
"""
import json, os, glob, datetime

BASE = '/Users/jieyang/Documents/WealthHub'
NAV = os.path.join(BASE, 'data/processed/reference/long-win-nav.csv')
REF = os.path.join(BASE, 'reference-portfolios/long-win')
TODAY = '2026-09-24'
BJ = datetime.timezone(datetime.timedelta(hours=8))

# ---------- 1. plan 详情（§3.82 规则：按 mtime 最新且含 composition 的响应） ----------
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
comp = data.get('composition')
prods = data.get('prodSummaries')
navd = data.get('navDate')
nav_bj = datetime.datetime.fromtimestamp(navd / 1000, BJ).strftime('%Y-%m-%d') if navd else None
print(f"adjustedCount={data.get('adjustedCount')} investedUnit={data.get('investedUnit')} "
      f"nav={data.get('nav')} navDate={navd} (北京 {nav_bj}) dailyReturn={data.get('dailyReturn')}")

meta_path = os.path.join(REF, 'meta.json')
old_meta = json.load(open(meta_path, encoding='utf-8')) if os.path.exists(meta_path) else {}
old_cnt = old_meta.get('adjustedCount')
new_cnt = data.get('adjustedCount')
old_inv = old_meta.get('investedUnit')
new_inv = data.get('investedUnit')
print(f'本地 meta.adjustedCount={old_cnt} vs 源={new_cnt} -> {"无新调仓" if old_cnt == new_cnt else "⚠️ 有新调仓"}')
print(f'本地 meta.investedUnit={old_inv} vs 源={new_inv} -> {"投入份数不变" if old_inv == new_inv else "⚠️ 投入份数变化"}')


# ---------- 2. composition 逐品种 planUnit 差分（§3.94 两层嵌套修正） ----------
def flatten_planunits(c):
    """返回 {key: planUnit}；key 优先 fundCode，缺失则用 variety。同时返回各类别 unit"""
    d, cls = {}, {}
    if not c:
        return d, cls
    for cl in c:
        cls[cl.get('className')] = cl.get('unit')
        for it in (cl.get('compList') or []):
            fu = it.get('fund') or {}
            k = fu.get('fundCode') or it.get('variety') or fu.get('fundName')
            d[k] = it.get('planUnit')
    return d, cls


new_pu, new_cls = flatten_planunits(comp)
print(f'\ncomposition 品种数={len(new_pu)}  planUnit 合计={sum(v for v in new_pu.values() if v)}  类别数={len(new_cls)}')

# 基线 = mtime 最新的历史 composition 快照（排除今日）
snaps = [f for f in glob.glob(os.path.join(REF, 'composition-*.json'))
         if TODAY not in os.path.basename(f)]
snaps.sort(key=os.path.getmtime, reverse=True)
prev_pu, prev_cls = ({}, {})
if snaps:
    b = snaps[0]
    prev_pu, prev_cls = flatten_planunits(json.load(open(b, encoding='utf-8')).get('composition'))
    print(f'对照基线 {os.path.basename(b)}（mtime {datetime.datetime.fromtimestamp(os.path.getmtime(b)):%Y-%m-%d %H:%M}）'
          f' 品种数={len(prev_pu)}  planUnit 合计={sum(v for v in prev_pu.values() if v)}')
else:
    print('⚠️ 无历史 composition 快照可对照')

diffs = [(k, prev_pu.get(k), new_pu.get(k)) for k in set(prev_pu) | set(new_pu) if prev_pu.get(k) != new_pu.get(k)]
print('\n=== planUnit 差分 ===')
if not diffs:
    print('  无品种 planUnit 变动')
for k, a, b in sorted(diffs):
    print(f'  {k}: {a} -> {b}')
cls_diffs = [(k, prev_cls.get(k), new_cls.get(k)) for k in set(prev_cls) | set(new_cls) if prev_cls.get(k) != new_cls.get(k)]
print('=== 资产类别 unit 差分 ===')
print('  无类别变动' if not cls_diffs else '\n'.join(f'  {k}: {a} -> {b}' for k, a, b in cls_diffs))

# ---------- 3. 落库 ----------
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
    'investedUnit': new_inv,
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
print(f'\n已更新 {meta_path} / composition-{TODAY}.json')

# ---------- 4. nav-history 诊断（同日期值不同=源修订，不追加） ----------
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

print('\n=== nav-history 源(北京时间) vs 本地 对齐诊断（§3.97：navDate 为北京时间零点） ===')
hit = 0
rows = sorted(src.items())
for i, (d, (v, r)) in enumerate(rows):
    lv = loc.get(d)
    ok = lv is not None and abs(lv - v) < 0.0006
    hit += 1 if ok else 0
    print(f'  源 {d} nav={v:.6f} ret={r:+.4f}%  ->  本地 {d} nav={lv if lv else "--"}  {"匹配" if ok else "不匹配"}')
print(f'  -> 近 {len(rows)} 个源日期中 {hit} 个与本地同日行数值匹配')
new_rows = [d for d in src if d not in loc]
print(f'  -> 源中不存在于本地的日期: {sorted(new_rows) if new_rows else "无"}')
print(f'  -> 本地最新 {max(loc)}；源最新(北京) {max(src)}')
