# -*- coding: utf-8 -*-
"""§3.93 三重交叉验证（修正版）：composition 嵌套结构（className → compList → planUnit）逐品种差分
对照对象：git HEAD 的 composition-2026-09-18.json（9/18 盘后归档版本）
"""
import json, os, subprocess

BASE = '/Users/jieyang/Documents/WealthHub'
CUR = 'reference-portfolios/long-win/composition-2026-09-20.json'
OLD_REV = 'HEAD:reference-portfolios/long-win/composition-2026-09-18.json'


def pmap(comp):
    m = {}
    for cl in comp or []:
        for it in cl.get('compList') or []:
            f = it.get('fund') or {}
            key = f"{f.get('fundCode')}|{it.get('variety') or f.get('fundName')}"
            m[key] = (it.get('planUnit'), it.get('nav'), it.get('dailyReturn'), cl.get('className'))
    return m


cur = json.load(open(os.path.join(BASE, CUR), encoding='utf-8'))
old = json.loads(subprocess.run(['git', 'show', OLD_REV], cwd=BASE,
                                capture_output=True, text=True, check=True).stdout)

mo, mn = pmap(old.get('composition')), pmap(cur.get('composition'))
print(f'品种数 旧 {len(mo)} / 新 {len(mn)}')
so = sum(v[0] for v in mo.values() if v[0] is not None)
sn = sum(v[0] for v in mn.values() if v[0] is not None)
print(f'planUnit 合计 旧 {so} / 新 {sn}')
diffs = [(k, mo.get(k), mn.get(k)) for k in sorted(set(mo) | set(mn)) if (mo.get(k) or (None,))[0] != (mn.get(k) or (None,))[0]]
if diffs:
    print('\n⚠️ planUnit 变动:')
    for k, o, n in diffs:
        print(f'  {k}  planUnit {o[0] if o else None} → {n[0] if n else None}  '
              f'({o[3] if o else "-"} → {n[3] if n else "-"})')
else:
    print('\n✅ 全组合 planUnit 无变动 → E大本周末无新调仓')

# nav 漂移（planUnit 相同但净值变化，属正常）
print('\n各资产类别 unit 对比:')
co = {c['className']: c.get('unit') for c in old.get('composition') or []}
cn = {c['className']: c.get('unit') for c in cur.get('composition') or []}
for k in sorted(set(co) | set(cn)):
    flag = '⚠️' if co.get(k) != cn.get(k) else '  '
    print(f'  {flag} {k:16s} {co.get(k)} → {cn.get(k)}')
