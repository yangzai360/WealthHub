#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix_amount_unit_20261002.py — 「绝对金额必须带元」补齐器 / 回归守卫（10/2 混合档：A股休市 + 港股复市首日）

背景（§3.105 / §3.109 / §3.112e 复发保护）：
  build_site.py 对受保护章节只对「数字 + 元」与千分位金额打码。
  日报若在「区间 A ~ B 元」「赛道日盈亏流水」两处以**裸数字**书写绝对金额，
  区间下界与赛道盈亏额将不被掩码（网页可见，且「金额 ÷ 涨跌%」可反推市值）。

白名单来源（本档）：
  portfolio_close_20260930_fix.json   （9/30 收盘修正基准：六赛道市值/盈亏、医药敞口、港联系三段）
  portfolio_preopen_20261002.json      （本档盘前：挂账区间、恒科减仓台账、门槛方程、基准修订 Δ）
  报告引用值                          （区间端点、还原式偏差、逐券市值）

用法：python scripts/fix_amount_unit_20261002.py [--dry]
验收标准（§3.112e）：报告写完先 `--dry`，期望「补「元」0 处」；
非 0 须逐条判定「漏补 vs 误伤」后才可正式执行。
"""
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

TARGETS = [
    os.path.join(REPO, 'reports', 'daily', '2026-10-02.md'),
]

# 白名单（无符号）：绝对金额（元）。含 exact 与「流水记法」四舍五入形式。

AMOUNTS = [
    '380,888.29',
    '380,888.30',
    '381,437.68',
    '549.39',
    '4,396.76',
    '4,946.15',
    '95,005.73',
    '89,776.91',
    '75,675.43',
    '59,644.42',
    '31,572.84',
    '29,212.97',
    '710.16',
    '2,579.22',
    '1,180.39',
    '73.01',
    '1,009',
    '149,421.33',
    '231,466.96',
    '50,024.26',
    '17,017.68',
    '14,555.16',
    '18,451.42',
    '22.44',
    '1,882.46',
    '29,690.38',
    '31,095.43',
    '267.82',
    '910.05',
    '564.23',
    '655.23',
    '819.04',
    '832.05',
    '923.05',
    '1,086.86',
    '9,325.07',
    '2,468.33',
    '333.12',
    '380,888',
    '381,438',
    '95,006',
    '89,777',
    '75,675',
    '59,644',
    '31,573',
    '29,213',
    '149,421',
    '231,467',
    '50,024',
    '17,018',
    '14,555',
    '18,451',
    '1,882',
    '29,690',
    '31,095',
    '9,325',
    '2,468',
]

# 右侧边界（§3.111c 扩展）：除「非数字 + 非%/元/万/亿」外，追加**比率/计数守卫** ——
# 形如 `91 / 183`（方向命中率）、`n = 197`（样本量）的同形数字是**计数**而非金额，不得补「元」
NOT_SUFFIX = r'(?![\d,.])(?!\s*(?:%|元|万|亿|美元|港元|点|bp|倍|条|次|只|家|个|日|年|月|季))(?!\s*/\s*(?:\d|total|n\b))'


def fix(text: str):
    changes = []
    # 上下文守卫（§3.109 复发保护）：样本量/字节数/年份/指数点位等场景下的同形数字不得补「元」
    CTX_GUARD = re.compile(
        r'(n\s*=\s*\d*\s*/\s*\d*\s*/\s*|样本量[^，。；]{0,12}|bytes[^，。；]{0,3}'
        r'|\d{2,}\s*/\s*|指数[^，。；]{0,6}|点位[^，。；]{0,4}|收盘[^，。；]{0,6}|报\s*$|收\s*$'
        r'|(?:负面|正面|中性|利多|利空)\s*$|置信度\s*$|强度\s*$|波动(?:高|中|低)?\s*$'
        r'|净值[^，。；]{0,4}|批价[^，。；]{0,4}|零售[^，。；]{0,4}|终端价[^，。；]{0,4})'
    )
    for amt in AMOUNTS:
        pat = re.compile(r'(?<![\d,.=])([+-]?)' + re.escape(amt) + NOT_SUFFIX)

        def rep(m):
            head = text[max(0, m.start() - 30):m.start()]
            if CTX_GUARD.search(head):
                return m.group(0)          # 守卫命中：不是金额，不补
            changes.append(m.group(0))
            return m.group(0) + ' 元'

        text = pat.sub(rep, text)
    return text, changes


def main():
    dry = '--dry' in sys.argv
    grand = 0
    for f in TARGETS:
        if not os.path.exists(f):
            print(f'{os.path.relpath(f, REPO)}: 不存在，跳过')
            continue
        s = open(f, encoding='utf-8').read()
        out, ch = fix(s)
        print(f'{os.path.relpath(f, REPO)}: 补「元」{len(ch)} 处')
        if ch:
            print('   ', ch)
        grand += len(ch)
        if not dry and ch:
            open(f, 'w', encoding='utf-8').write(out)
    print(f'合计 {grand} 处' + ('（dry-run，未写盘）' if dry else ''))


if __name__ == '__main__':
    main()
