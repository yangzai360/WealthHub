# -*- coding: utf-8 -*-
"""盘前档 2026-08-25：批量回填 8/23-8/24 遗留美股标普医药事件 actual_ret_1d（用 IYH 8/24 收盘 -0.07%，XLV 新浪源滞后停在 8/21 不可用，取最新可用者）"""
import json, os

BASE = '/Users/jieyang/Documents/WealthHub'
EVT = os.path.join(BASE, 'data/processed/events')

# IYH 2026-08-24 收盘：73.84，-0.07%（XLV 滞后停在 8/21 +1.29%，取最新可用者）
FILL = {
    'actual_ret_1d': -0.07,
    'ret_1d_ref': 'IYH 8/24收盘 -0.07%（XLV 新浪源滞后停在 8/21）',
}

targets = [
    ('events-2026-08-23.json', ['N20260823-013', 'N20260823-014']),
    ('events-2026-08-24.json', ['N20260824-009', 'N20260824-010', 'N20260824-011']),
]

for fn, ids in targets:
    path = os.path.join(EVT, fn)
    with open(path, encoding='utf-8') as f:
        evs = json.load(f)
    filled = 0
    for e in evs:
        if e.get('id') in ids:
            ref = e.setdefault('reference', {})
            ref['actual_ret_1d'] = FILL['actual_ret_1d']
            ref['ret_1d_ref'] = FILL['ret_1d_ref']
            filled += 1
            print(f'  回填 {e["id"]} {e["track"]}: {FILL["actual_ret_1d"]}%')
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(evs, f, ensure_ascii=False, indent=1)
    print(f'{fn}: 回填 {filled} 条')

# 全库完整性扫描
print('\n=== 全库 actual_ret_1d 留空扫描 ===')
for fn in sorted(os.listdir(EVT)):
    if not fn.startswith('events-') or not fn.endswith('.json'):
        continue
    with open(os.path.join(EVT, fn), encoding='utf-8') as f:
        evs = json.load(f)
    none_ones = [e for e in evs if not isinstance(e.get('reference'), dict) or e['reference'].get('actual_ret_1d') is None]
    if none_ones:
        print(f'{fn}: {len(none_ones)} 条留空 -> {[e.get("id") for e in none_ones]}')
print('扫描完成')
