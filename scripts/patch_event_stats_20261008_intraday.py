# -*- coding: utf-8 -*-
"""2026-10-08 盘中档：`event_stats_intraday_20261008.json` 分阶段增量修补（§3.130c / §3.112c 复发处置）

背景：本档 `events_intraday_20261008.py` 执行 2 次 ——
  ① 首跑（修复前）：+18 条落库、`added = 18`、`session_added = 18`，但脚本在**幂等守卫**处抛
     `AssertionError: 增量与窗口条数不符`（原模板缺陷：守卫未含「已落库跳过」计数，二次执行
     `added` 归零即误判）→ **产物已写出但退出码非 0**；
  ② 修守卫后复跑（幂等验证）：事件库命中 18 条全部跳过 → `added = 0` / `session_added = 0`，
     **把首跑真实增量覆盖为 0**（§3.112c 第 N 次复发）。
处置：本脚本**只改 `session_*` / `added` / `note` 类字段，不触碰任何统计读数**（§3.130c）。
⚠️ 四类字面量核对（§3.121c）：读写路径 = event_stats_intraday_20261008.json / 日期常量 = 2026-10-08 /
   docstring 档型语义 = 正常交易日盘中 / note 字段档型语义 = 同 docstring
"""
import json, os

HIST = '/Users/jieyang/Documents/WealthHub/data/processed/history'
P = os.path.join(HIST, 'event_stats_intraday_20261008.json')

d = json.load(open(P, encoding='utf-8'))

# ---- 首跑真值（从事件库实测反查，不手写常量，§3.133a） ----
EV = '/Users/jieyang/Documents/WealthHub/data/processed/events/events-2026-10-08.json'
ev = json.load(open(EV, encoding='utf-8'))
WIN = '盘中(10/8 07:30-13:30)'
ws = [e for e in ev if e.get('window') == WIN]
FIRST_RUN = len(ws)
assert FIRST_RUN == 18, f'⚠️ 事件库本窗口条数 = {FIRST_RUN}，与首跑记录 18 不符 → 终止人工核对'

before = {'added': d.get('added'), 'session_added': d.get('session_added')}

d['added'] = FIRST_RUN
d['session_added'] = FIRST_RUN
d['workingset'] = FIRST_RUN
d['session_added_note'] = (
    f'首跑真实增量 = {FIRST_RUN} 条（进程内）；二次执行因幂等跳过 18 条 → `added` 归零，'
    '本字段按「事件库本窗口条数」反查还原（§3.133a：展示/计数字段须现算自校验，禁手写常量）')
d['session_phases'] = [
    {'phase': 1, 'script': 'events_intraday_20261008.py', 'run': '首跑（守卫修复前）',
     'added': FIRST_RUN, 'skipped': 0, 'backfilled': 0,
     'exit': 'AssertionError（幂等守卫缺陷）→ 但 json.dump 已执行、产物已落盘'},
    {'phase': 2, 'script': 'events_intraday_20261008.py', 'run': '复跑（守卫修复后，幂等验证）',
     'added': 0, 'skipped': FIRST_RUN, 'backfilled': 0, 'exit': 0},
    {'phase': 3, 'script': 'patch_event_stats_20261008_intraday.py', 'run': '会话计数还原',
     'added': None, 'skipped': None, 'backfilled': None, 'exit': 0,
     'note': '仅改 session_* / added / note 类字段，未触碰统计读数'},
]
d['session_phase_note'] = (
    '三阶段执行：① 首跑 +18 条落库（守卫缺陷致非 0 退出）；② 修守卫后复跑（幂等，跳过 18）；'
    '③ 本修补脚本还原 session 计数。**统计读数（windows / onesample / direction_hit_strict / '
    'similarity_by_track / pseudo_close_n_delta）全程只由第 ① 次执行产生、未被后续执行改动。**')
d['guard_fix_note'] = (
    '⚠️ 模板缺陷修正（§3.112c/§3.113f 补强）：原 `events_intraday_*` 守卫写 '
    '`assert len(added) + len(miss) == len(win_sent)` → 二次执行 `added` 归零即误判中止；'
    '本档已改为 `assert len(added) + len(miss) + skipped == len(win_sent)`，并新增 `skipped` 计数与打印。')
d['rerun_note'] = '可重入脚本：二次执行 added 归零；工作集取自库内本窗口条目（§3.113f）；会话真值见 session_added'

json.dump(d, open(P, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(f'已修补 {os.path.basename(P)}')
print(f'  added/session_added: {before} → {{"added": {d["added"]}, "session_added": {d["session_added"]}}}')
print(f'  统计读数未改动：windows 赛道数 = {len(d["windows"])}，今天事件 = {d["today_events"]}，全库 = {d["total_events"]}')
