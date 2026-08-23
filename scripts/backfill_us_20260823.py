# -*- coding: utf-8 -*-
"""周日(8/23)盘后档:回填 8/21 遗留美股标普医药事件(用 XLV 8/21 +1.29%)"""
import json, os

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
    if e.get('actual_ret_1d') is not None:
        return False
    if 'reference' not in e or not isinstance(e.get('reference'), dict):
        e['reference'] = {}
    if e['reference'].get('actual_ret_1d') is not None:
        return False
    e['reference']['actual_ret_1d'] = val
    e['reference']['ret_1d_ref'] = note
    return True

# 1) 8/21 遗留美股标普医药 2 条,用 XLV 8/21 +1.29% 回填
events, p = load_events('2026-08-21')
filled = 0
for e in events:
    if e.get('id') in ('N20260821-006', 'N20260821-007') and get_ret(e) is None:
        if set_ret(e, 1.29, 'XLV 8/21收盘 +1.29%(周日盘后补回填)'):
            filled += 1
            print(f'回填 {e["id"]} -> 1.29')
save_events(events, p)
print(f'8/21 回填 {filled} 条')

# 2) 检查全部事件库留空情况(统计)
import glob
all_empty = []
for fp in sorted(glob.glob('/Users/jieyang/Documents/WealthHub/data/processed/events/events-*.json')):
    with open(fp, encoding='utf-8') as f:
        evs = json.load(f)
    for e in evs:
        if get_ret(e) is None:
            all_empty.append((os.path.basename(fp), e.get('id'), e.get('track'), e.get('title','')[:50]))
print(f'\n全库留空 {len(all_empty)} 条:')
for d, i, t, tt in all_empty:
    print(f'  {d} {i} {t} {tt}')
