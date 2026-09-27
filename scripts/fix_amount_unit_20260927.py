#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix_amount_unit_20260927.py — 「绝对金额必须带元」补齐器（W39 档）

背景（§3.105 复发实例，W38/W39 两档回归）：
  build_site.py 对受保护章节只对「数字 + 元」与 6 位千分位金额打码。
  本档日报/周报在「区间 A ~ B 元」与「赛道日盈亏流水」两处以**裸数字**书写绝对金额，
  导致区间下界与赛道盈亏额未被掩码（网页可见，且「金额 ÷ 涨跌%」可反推市值）。
  本脚本按**白名单**（取自 portfolio_close_*_fix.json 的真实赛道/组合盈亏）为裸数字补「元」，
  使脱敏规则命中。

用法：python scripts/fix_amount_unit_20260927.py [--dry]
"""
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

TARGETS = [
    os.path.join(REPO, 'reports', 'daily', '2026-09-27.md'),
    os.path.join(REPO, 'reports', 'weekly', '2026-W39-周报.md'),
]

# 白名单（无符号）：绝对金额（元）。含 exact 与「流水记法」四舍五入形式。
AMOUNTS = [
    # W39 各日赛道盈亏 exact
    '2,648.32', '1,400.75', '853.28', '298.92', '209.41',
    '202.78', '145.78', '107.33', '236.14', '349.00',
    '1,131.43', '268.89', '837.25', '229.43', '232.69',
    '973.77', '1,122.15', '2,717.58', '383.78', '211.60',
    # 组合日/周盈亏
    '4,658.74', '534.81', '559.81', '5,408.88', '775.14', '5,231.18', '4,991.86', '572.44', '239.32',
    # 待消化 / QDII 预告区间端点
    '758.01', '460.73', '623.49', '554.80', '463.94', '90.88', '532.61', '924.67', '232.19',
    '369.87', '349',
    # 流水记法（四舍五入/截断）
    '2,648', '1,401', '853', '299', '209',
    '203', '236', '146', '107',
    '1,131', '269', '837', '229', '233',
    '974', '1,122', '2,718', '384', '212',
]

# 右侧边界：必须紧跟非数字字符（排除 2030年 / URL尾号 / n=269 的统计样本数等误伤），
# 且其后不得已是 %/元/万/亿 口径；左侧边界排除紧跟数字或 '='（如 n=269）。
NOT_SUFFIX = r'(?![\d,.])(?!\s*(?:%|元|万|亿|美元|港元))'


def fix(text: str):
    changes = []
    for amt in AMOUNTS:
        pat = re.compile(r'(?<![\d,.=])([+-]?)' + re.escape(amt) + NOT_SUFFIX)
        def rep(m):
            changes.append(m.group(0))
            return m.group(0) + ' 元'
        text = pat.sub(rep, text)
    return text, changes


def main():
    dry = '--dry' in sys.argv
    grand = 0
    for f in TARGETS:
        s = open(f, encoding='utf-8').read()
        out, ch = fix(s)
        print(f'{os.path.relpath(f, REPO)}: 补「元」{len(ch)} 处')
        print('   ', ch)
        grand += len(ch)
        if not dry and ch:
            open(f, 'w', encoding='utf-8').write(out)
    print(f'合计 {grand} 处' + ('（dry-run，未写盘）' if dry else ''))


if __name__ == '__main__':
    main()
