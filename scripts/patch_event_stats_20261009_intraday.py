# -*- coding: utf-8 -*-
"""2026-10-09 盘中档：`event_stats_intraday_20261009.json` 会话计数修补（§3.130c / §3.112c 复发处置）

背景：本档 `events_intraday_20261009.py` 执行 2 次 ——
  ① 首跑：+23 条落库、`added = 23`、`session_added = 23`，退出码 0；**但首跑采用了经派生得到的
     `prev_path`（承袭 10/8 脚本的 `event_stats_intraday_20261007.json`）→ §3.122a 的「相对上一档
     n 变化」对照文件错位（应比对 10/8 盘中档）**；
  ② 修正 `prev_path`（→ `event_stats_intraday_20261008.json`）后复跑（幂等验证）：事件库命中 23 条
     全部跳过 → `added = 0` / `session_added = 0`，**把首跑真实增量覆盖为 0**（§3.112c 复发）。
处置：本脚本**只改 `session_*` / `added` / `note` 类字段，不触碰任何统计读数**（§3.130c）。
⚠️ 四类字面量核对（§3.121c，本档扩充为**五类**）：读写路径 = event_stats_intraday_20261009.json /
   日期常量 = 2026-10-09 / docstring 档型语义 = 正常交易日盘中 / `prev_path`（上一档对照文件）/
   note 字段档型语义 = 同 docstring
"""
import json, os

HIST = '/Users/jieyang/Documents/WealthHub/data/processed/history'
P = os.path.join(HIST, 'event_stats_intraday_20261009.json')

d = json.load(open(P, encoding='utf-8'))

# ---- 首跑真值（从事件库实测反查，不手写常量，§3.133a） ----
EV = '/Users/jieyang/Documents/WealthHub/data/processed/events/events-2026-10-09.json'
ev = json.load(open(EV, encoding='utf-8'))
WIN = '盘中(10/9 07:30-13:30)'
ws = [e for e in ev if e.get('window') == WIN]
FIRST_RUN = len(ws)
assert FIRST_RUN == 23, f'⚠️ 事件库本窗口条数 = {FIRST_RUN}，与首跑记录 23 不符 → 终止人工核对'

before = {'added': d.get('added'), 'session_added': d.get('session_added')}

d['added'] = FIRST_RUN
d['session_added'] = FIRST_RUN
d['workingset'] = FIRST_RUN
d['session_added_note'] = (
    f'首跑真实增量 = {FIRST_RUN} 条（进程内）；二次执行因幂等跳过 23 条 → added 归零，'
    '本字段按「事件库本窗口条数」反查还原（§3.133a：展示/计数字段须现算自校验，禁手写常量）')
d['session_phases'] = [
    {'phase': 1, 'script': 'events_intraday_20261009.py',
     'run': '首跑（prev_path 错位：指向 20261007）',
     'added': FIRST_RUN, 'skipped': 0, 'backfilled': 0, 'exit': 0,
     'note': '统计读数正确（与 prev_path 无关）；仅 §3.122a 对照文件错位'},
    {'phase': 2, 'script': 'events_intraday_20261009.py',
     'run': '复跑（修正 prev_path 后，幂等验证）',
     'added': 0, 'skipped': FIRST_RUN, 'backfilled': 0, 'exit': 0,
     'note': '对照文件已修正为 event_stats_intraday_20261008.json'},
    {'phase': 3, 'script': 'patch_event_stats_20261009_intraday.py', 'run': '会话计数还原',
     'added': None, 'skipped': None, 'backfilled': None, 'exit': 0,
     'note': '仅改 session_* / added / note 类字段，未触碰统计读数'},
]
d['session_phase_note'] = (
    '三阶段执行：① 首跑 +23 条落库（prev_path 错位、退出码 0）；② 修正 prev_path 后复跑（幂等，跳过 23）；'
    '③ 本修补脚本还原 session 计数。**统计读数（windows / onesample / direction_hit_strict / '
    'similarity_by_track / pseudo_close_n_delta）全程只由第 ① 次执行产生、未被后续执行改动；'
    '`pseudo_close_prev_stats` 以第 ② 次执行产出的对照文件名为准（= event_stats_intraday_20261008.json）。**')
d['guard_fix_note'] = (
    '⚠️ **本档新发现（§3.121c「派生脚本字面量核对」的第 5 类）**：由上一档派生的事件库脚本中，'
    '`prev_path` 为硬编码字符串；用 sed 把「20261008 → 20261009」替换时，'
    '**只会推进「本档」相关字面量，不会把 prev_path 从 20261007 推进到 20261008** '
    '→ §3.122a 的「相对上一档 n 变化」对照错位（本档首跑即踩）。'
    '**规则：派生脚本必须逐项核对「写盘路径 / 日期常量 / 档型语义 / prev_path（上一档对照文件）」。**')
d['rerun_note'] = '可重入脚本：二次执行 added 归零；工作集取自库内本窗口条目（§3.113f）；会话真值见 session_added'

json.dump(d, open(P, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(f'已修补 {os.path.basename(P)}')
print(f'  added/session_added: {before} → {{"added": {d["added"]}, "session_added": {d["session_added"]}}}')
print(f'  统计读数未改动：windows 赛道数 = {len(d["windows"])}，当日事件 = {d["today_events"]}，全库 = {d["total_events"]}')
print(f'  prev_stats = {d.get("pseudo_close_prev_stats")}')
