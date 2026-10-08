# -*- coding: utf-8 -*-
"""追加 2026-10-08 日报「三、盘后复盘」章节（单文件日报约定：仅追加、不覆盖前两章）"""
import os, re

BASE = '/Users/jieyang/Documents/WealthHub'
REPORT = os.path.join(BASE, 'reports/daily/2026-10-08.md')
SRC = '/tmp/close_section_20261008.md'
SEC = '## 三、盘后复盘（20:00 档）'

body = open(SRC, encoding='utf-8').read().rstrip() + '\n'
cur = open(REPORT, encoding='utf-8').read()

if SEC in cur:
    # 幂等：截断到该章节之前再重写
    cur = cur.split(SEC)[0].rstrip() + '\n\n---\n\n'
    print('⚠️ 已存在「三、盘后复盘」→ 覆盖该章节（前两章保留）')
else:
    cur = cur.rstrip() + '\n\n---\n\n'

new = cur + body
open(REPORT, 'w', encoding='utf-8').write(new)

# ---------- 三项质检（§3.100 / §3.106 / §3.129e） ----------
text = open(REPORT, encoding='utf-8').read()
secs = re.findall(r'^## ', text, flags=re.M)
ph = re.findall(r'@[A-Z_0-9]{2,}@', text)
dup = re.findall(r'元\s+元', text)
trip = re.findall(r'^(-{3,})\s*\n\s*\1', text, flags=re.M)
hr = text.count('\n---\n')
words = '章节数 = %d | 占位符残留 = %d | 「元」重复后缀 = %d | 连续分隔线 = %d | 分隔线总数 = %d' % (
    len(secs), len(ph), len(dup), len(trip), hr)
print('✅ 质检：' + words)
assert len(secs) == 3, '章节数不为 3'
assert len(ph) == 0, '存在占位符残留: %s' % ph[:5]
assert len(dup) == 0, '存在「元 元」双后缀'
assert len(trip) == 0, '存在连续分隔线'
print('✅ 追加完成，报告行数 = %d' % len(text.splitlines()))
