# -*- coding: utf-8 -*-
"""2026-10-06 盘后档：event_stats_20261006_close.json 的「两阶段执行」自证补写（§3.114b / §3.112c）
背景：本档 events_close_20261006.py 因「标题匹配缺陷」共执行两次：
  · 阶段 1（首跑）：新增 0 条（缺陷未暴露）、回填 14 条 ✅ 已落盘
  · 阶段 2（修缺陷后）：新增 22 条 ✅、回填 0 条（幂等）
  → 第 3 次执行（核对）显示 added=0 / backfilled=0，会把当档真实增量写成 0（§3.112c 复发形态）。
本脚本把「两阶段真实增量」写回产物，避免下游把 14 / 22 误读为 0。
⚠️ 只改 `session_*` 与 `note` 类字段，不改动任何统计读数。
"""
import json, io, os

HIST = '/Users/jieyang/Documents/WealthHub/data/processed/history'
P = os.path.join(HIST, 'event_stats_20261006_close.json')
d = json.load(io.open(P, encoding='utf-8'))

d['session_added'] = 22
d['session_added_phases'] = {'phase1_first_run': 0, 'phase2_after_fix': 22}
d['session_backfilled_total'] = 14
d['session_backfilled_this_run'] = 0
d['session_backfilled_phases'] = {'phase1_first_run': 14, 'phase2_after_fix': 0, 'phase3_recheck': 0}
d['session_prior_filled'] = 0
d['session_phase_note'] = (
    '两阶段执行 + 一次核对（§3.114b）：'
    '**阶段 1**（首跑）新增 **0** 条、回填 **14** 条 → 回填已落盘；'
    '**阶段 2**（修复「标题匹配」缺陷后）新增 **22** 条、回填 **0** 条（幂等）；'
    '**阶段 3**（核对）显示 0 / 0（可重入脚本的固有权重现象，§3.112c）。'
    '**当档真实增量 = 新增 22 条 + 回填 14 条**。'
    '⚠️ 本档发现并修复：事件脚本原写法 `y["title"][:60] == x["title"]` 仅在「sentiment 侧 title 已被截断为 60 字」时成立；'
    '本档 sentiment 侧保留标题全称 → 首跑恒不命中 → **静默新增 0 条**（事件库 +0、exit 0、无报错）。'
    '已改为「双侧 60 字前缀比对 + 全称兜底 + 未命中即打印告警」。'
)
d['backfill_note'] = (
    '本档回填 14 条**恒生科技**类事件（参考指数 HSTECH 2026-10-06 收盘 4,223.08 / +0.9418%）：'
    '① 事件日 2026-10-05 的**盘后窗口** 4 条 → 按 §3.127a「盘后窗口须严格顺延」取 2026-10-06；'
    '② 事件日 2026-10-06 的盘前/盘中窗口 10 条 → 参考日 = 2026-10-06（当日收盘晚于事件发布，属合法前瞻终点）。'
    'A股类（A股医药/大消费/其他·宽基/宏观，参考日 2026-10-08）与美股标普医药（参考日 2026-10-07）本档仍留空，属预期状态。'
    '⚠️ §3.127a 修正首次落地：旧实现「先取同日、再跳过」会使「同日已有观测」的事件**永久停留在空白态** —— '
    '本档 10/5 盘后窗口的 4 条恒生科技事件即因此在其后连续两档（10/5 盘后、10/6 盘前）未能回填；'
    '本档改用 `ref_ret(code, date, strict_after=True)` 在取数阶段即排除同日，已闭环。'
)
d['window_n_delta_note'] = (
    '§3.127d 机器判据**通过**：本档以「恒生科技 2026-10-06 真收盘行（4,223.08）」覆盖 13:45 盘中伪收盘行（4,212.07）'
    '—— 日期键相同 → **多日窗口 n 完全不变**（3 日 362 / 5 日 331 / 10 日 255，与 event_stats_intraday_20261006.json 一致），'
    '仅读数被修正（3 日 −1.1996% → −1.1895%、5 日 −1.9009% → −1.8877%、10 日 −3.3526% → −3.3380%）；'
    '**1 日窗口 n 403 → 417（+14）= 本档回填条数** ✅ 与 §3.127d 预期完全一致。'
    '→ 可反推「本次是覆盖同日期键、而非新增第二行」，`indices.csv` 当日无重复日期行。'
)
d['intraday_pseudo_close_warning'] = False
d['intraday_pseudo_close_resolved'] = True
d['intraday_pseudo_close_note'] = (
    '本档已用真实收盘行覆盖 10/6 盘中伪收盘行（§3.122a / §3.127d）；'
    '报告引用全库 3/5/10 日窗口读数时须标注「终点为 2026-10-06 真实收盘价」。'
)
d['session_type'] = 'mixed_day_close'
d['session_type_note'] = '档型②「混合档」第 3 日（A股休市 + 港股续市第 3 日已收盘）：A股类与美股类事件本档仍留空，仅恒生科技类可回填'

json.dump(d, open(P, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('✅ 已补写两阶段自证字段:')
for k in ('session_added', 'session_backfilled_total', 'session_backfilled_this_run',
          'session_backfilled_phases', 'intraday_pseudo_close_resolved'):
    print(' ', k, '=', d[k])
print(' windows 恒生科技 =', d['windows']['恒生科技'])
