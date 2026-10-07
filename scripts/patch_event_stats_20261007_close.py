# -*- coding: utf-8 -*-
"""2026-10-07 盘后档：event_stats 的 `session_*` 分阶段字段修正（§3.114b / §3.130c）
⚠️ 只改 `session_*` 与 `note` 类字段，**不触碰任何统计读数**（attempt/blank/windows/direction_hit 一律不动）
⚠️ 成因：10/7 盘中档脚本把 session_added 写成「本进程新增」（26）而非「当档累计」（35+26），
   且 session_backfilled_total 归零（丢失盘前档的 10 条）；本档以「三阶段求和」修正为权威值。
"""
import json, os

BASE = '/Users/jieyang/Documents/WealthHub'
HIST = os.path.join(BASE, 'data/processed/history')
TODAY = '2026-10-07'

p_close = os.path.join(HIST, 'event_stats_20261007_close.json')
p_intra = os.path.join(HIST, 'event_stats_intraday_20261007.json')
p_pre = os.path.join(HIST, 'event_stats_20261007_preopen.json')

pre = json.load(open(p_pre, encoding='utf-8'))
intra = json.load(open(p_intra, encoding='utf-8'))
close = json.load(open(p_close, encoding='utf-8'))

ev = json.load(open(os.path.join(BASE, 'data/processed/events/events-2026-10-07.json'), encoding='utf-8'))
today_total = len(ev)
print(f'events-{TODAY}.json = {today_total} 条（本档权威口径）')

# ⚠️ 盘前档产物无 `added` 字段（该档 session_added 即为本进程新增）→ 回退取 session_added
ADD_PHASES = {'preopen': pre.get('added', pre.get('session_added')),
              'intraday': intra.get('added'), 'close': close.get('added')}
BF_PHASES = {'preopen': pre.get('session_backfilled_total', 0),
             'intraday': intra.get('session_backfilled_this_run', 0),
             'close': close.get('session_backfilled_this_run', 0)}

sum_add = sum(v for v in ADD_PHASES.values() if isinstance(v, int))
sum_bf = sum(BF_PHASES.values())
print(f'三阶段新增 {ADD_PHASES} → 合计 {sum_add}')
print(f'三阶段回填 {BF_PHASES} → 合计 {sum_bf}')

assert sum_add == today_total, f'⚠️ 新增合计 {sum_add} != 当日事件数 {today_total}（不得写盘）'

close['session_added'] = sum_add
close['session_backfilled_total'] = sum_bf
close['session_backfilled_this_run'] = BF_PHASES['close']
close['session_prior_filled'] = sum_bf - BF_PHASES['close']
close['session_added_phases'] = ADD_PHASES
close['session_backfilled_phases'] = BF_PHASES
close['session_phase_note'] = (
    f'三阶段逐项（§3.114b 修订）：① 盘前档 +{ADD_PHASES["preopen"]} 条事件 / 回填 {BF_PHASES["preopen"]} 条'
    f'（美股标普医药 10/6 类，参考指数 XLV 于 10/6 有真实收盘）；'
    f'② 盘中档 +{ADD_PHASES["intraday"]} 条 / 回填 {BF_PHASES["intraday"]} 条（13:45 港股未收盘、A股休市）；'
    f'③ 盘后档 +{ADD_PHASES["close"]} 条 / 回填 {BF_PHASES["close"]} 条'
    f'（恒生科技类，参考指数 HSTECH 2026-10-07 收盘 4,194.49 / −0.68%，真实收盘行）。'
    f'→ 当档累计 session_added = {sum_add}（= 当日 events-{TODAY}.json 条数，硬守卫通过）、'
    f'session_backfilled_total = {sum_bf}。'
    'A股类（A股医药/大消费/其他·宽基/宏观）参考交易日 = 2026-10-08；'
    '美股标普医药 10/7 事件参考交易日 = 2026-10-07（收盘成型于北京 10/8 04:00）。'
    '⚠️ 口径更正：盘中档脚本曾以「本进程新增」覆盖 `session_added` 并把 `session_backfilled_total` 置 0，'
    '致跨阶段累计丢失（§3.112c / §3.114b 复发形态）。本档改为「三阶段逐项求和」并写入 '
    '`session_added_phases` / `session_backfilled_phases` 供审计。'
)
close.setdefault('note', '')
close['patch_note'] = (f'本文件由 patch_event_stats_{TODAY.replace("-","")}_close.py 修正 session_* 字段；'
                       '统计读数（windows / onesample / direction_hit_strict / blank / similarity）**未被改动**。')

json.dump(close, open(p_close, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('已修正并写盘:', os.path.basename(p_close))

# ---------- 回读末序列抽查（§3.98） ----------
chk = json.load(open(p_close, encoding='utf-8'))
print('回读校验：session_added =', chk['session_added'],
      '| session_backfilled_total =', chk['session_backfilled_total'],
      '| session_prior_filled =', chk['session_prior_filled'])
print('统计读数未动：windows 恒生科技 =', chk['windows'].get('恒生科技'),
      '| blank =', chk['blank'], '| today_events =', chk['today_events'])
assert chk['today_events'] == today_total
print('✅ 抽查连续性通过')
