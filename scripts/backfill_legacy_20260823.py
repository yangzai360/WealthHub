# -*- coding: utf-8 -*-
"""周日(8/23)盘后档:批量补回填历史遗留事件 actual_ret_1d
- 8/08-8/09 美股标普医药 3 条 → XLV 8/10 +1.67%(首个交易日收盘)
- 8/17 当日 7 条(盘后追加未二次回填) → 8/17 各赛道收盘
"""
import json

def load_events(date):
    p = f'/Users/jieyang/Documents/WealthHub/data/processed/events/events-{date}.json'
    with open(p, encoding='utf-8') as f:
        return json.load(f), p

def save_events(events, p):
    with open(p, 'w', encoding='utf-8') as f:
        json.dump(events, f, ensure_ascii=False, indent=1)

def get_ret(e):
    return e.get('actual_ret_1d') if e.get('actual_ret_1d') is not None else e.get('reference', {}).get('actual_ret_1d')

def set_ret(e, val, note):
    if get_ret(e) is not None:
        return False
    if 'reference' not in e or not isinstance(e.get('reference'), dict):
        e['reference'] = {}
    e['reference']['actual_ret_1d'] = val
    e['reference']['ret_1d_ref'] = note
    return True

# 回填映射: (date, id) -> (ret, note)
MAP = {
    ('2026-08-08', 'N20260808-002'): (1.67, 'XLV 8/10收盘 +1.67%(周末事件首个交易日)'),
    ('2026-08-08', 'N20260808-003'): (1.67, 'XLV 8/10收盘 +1.67%(周末事件首个交易日)'),
    ('2026-08-09', 'N20260809-007'): (1.67, 'XLV 8/10收盘 +1.67%(周末事件首个交易日)'),
    ('2026-08-17', 'N20260817-022'): (1.41, '沪指 8/17收盘 +1.41%'),
    ('2026-08-17', 'N20260817-023'): (1.41, '沪指 8/17收盘 +1.41%'),
    ('2026-08-17', 'N20260817-024'): (-1.14, '中证消费 8/17收盘 -1.14%'),
    ('2026-08-17', 'N20260817-025'): (0.66, '医药ETF均值 8/17收盘 +0.66%'),
    ('2026-08-17', 'N20260817-026'): (1.58, '恒生科技 8/17收盘 +1.58%'),
    ('2026-08-17', 'N20260817-028'): (1.58, '恒生科技 8/17收盘 +1.58%'),
    ('2026-08-17', 'N20260817-029'): (1.41, '沪指 8/17收盘 +1.41%'),
}

done = 0
by_date = {}
for (date, eid), (ret, note) in MAP.items():
    by_date.setdefault(date, []).append((eid, ret, note))

for date, items in by_date.items():
    events, p = load_events(date)
    for eid, ret, note in items:
        for e in events:
            if e.get('id') == eid:
                if set_ret(e, ret, note):
                    print(f'{eid} -> {ret} ({note})')
                    done += 1
                else:
                    print(f'{eid} 已有回填,跳过')
                break
    save_events(events, p)

print(f'\n共回填 {done} 条')

# 复查全库留空
import glob, os
all_empty = []
for fp in sorted(glob.glob('/Users/jieyang/Documents/WealthHub/data/processed/events/events-*.json')):
    with open(fp, encoding='utf-8') as f:
        evs = json.load(f)
    for e in evs:
        if get_ret(e) is None:
            all_empty.append((os.path.basename(fp), e.get('id'), e.get('track'), e.get('title','')[:50]))
print(f'全库仍留空 {len(all_empty)} 条:')
for d, i, t, tt in all_empty:
    print(f'  {d} {i} {t} {tt}')
