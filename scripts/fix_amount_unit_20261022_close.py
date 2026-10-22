#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fix_amount_unit_20261022_close.py — 「绝对金额必须带元」补齐器 / 回归守卫
（2026-10-22 **20:00 盘后复盘档** · 档型②「正常交易日收盘」）

⚠️ §3.112e / §3.145g：白名单**逐档重建**，且**按字段路径挑选**（不递归抽取全部数值叶子——
   递归会把 idx / hk_mkt / etf_close / stocks_close 的**指数点位**误纳，本档 dry-run 实测误伤 101 处，
   §3.112e-补「白名单禁止纳入指数点位」再次实测）。
⚠️ 白名单来源 = 本档 4 个产物的**金额类字段路径**：
   tracks[].mv/mv0/pnl、detail[].est_pnl/mv0_new/mv、discipline.*.amount、hk_split*、qdii_pending.*、
   active_mult.*.mv、proxy_check.*.mv、unpriced_total、unpriced_shadow.*、intraday_vs_close.*
⚠️ 禁纳：指数点位 / 百分比 / β / 计数类（3,256 / 70 / 63 / 20 / n 值 / 交易日 50）/ 两位纯整数 / 点位门槛（3,950 等）
用法：python scripts/fix_amount_unit_20261022_close.py [--dry]
"""
import os
import re
import sys
import json

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
H = os.path.join(REPO, 'data/processed/history')
TARGETS = [os.path.join(REPO, 'reports', 'daily', '2026-10-22.md')]


def forms(x):
    out = set()
    try:
        v = float(x)
    except (TypeError, ValueError):
        return out
    if abs(v) < 1:
        return out
    out.add(f'{abs(v):,.2f}')
    b = f'{round(abs(v)):,d}'
    if ',' in b or len(b) > 3:
        out.add(b)
    return out


AMT_KEYS = {'amount', 'mv', 'mv0', 'mv0_new', 'pnl', 'est_pnl', 'total_mv', 'est_total_pnl',
            'base_total', 'med_exposure', 'detail_restore_total', 'unpriced_total', 'priceable_total',
            'hk_total', 'qdii_mv', 'lof_164906_mv', 'cumulative_amount', 'hk_after', 'cash_after',
            'discipline_total', 'total_est_pnl_lo', 'total_est_pnl_hi', 'intraday_pnl', 'close_pnl',
            'delta', 'pure', 'concept', 'broad'}
EXCLUDE_PREFIX = ('idx', 'hk_mkt', 'etf_close', 'stocks_close', 'board_detail', 'board_med',
                  'sentiment', 'events', 'financial', 'weights', 'risk')

AMOUNTS = set()


def walk(o, path=''):
    if isinstance(o, dict):
        for k, v in o.items():
            walk(v, f'{path}/{k}')
    elif isinstance(o, list):
        for i, v in enumerate(o):
            walk(v, f'{path}[]')
    elif isinstance(o, (int, float)) and not isinstance(o, bool):
        key = path.rsplit('/', 1)[-1]
        root = path.lstrip('/').split('/')[0]
        if key in AMT_KEYS and root not in EXCLUDE_PREFIX:
            AMOUNTS.update(forms(o))


for fn in ('portfolio_close_20261022.json',
           'portfolio_strategy_close_20261022.json',
           'portfolio_close_20261021_fix.json',
           'portfolio_close_20261021.json'):
    p = os.path.join(H, fn)
    if os.path.exists(p):
        walk(json.load(open(p, encoding='utf-8')))

# ---- 报告侧派生 / 手算值（逐项标注来源，禁止直接照抄指数点位）----
# 5,580.65  = 1,863.33 + 1,858.66 + 1,858.66（三案合计，若全执行）
# 5,650.23  = 3,786.90 + 1,863.33（4,000 案若执行后的累计）
# 502.15    = 000071 恒生ETF联接双账户两行合计
# 784.02 / 163.33 / 91.66 / 253.48 = 盘中→收盘四段对账分解（报告中已逐项列出算式）
# 7,129.76 / 4,327.42 = 还原式机器判据的两个候选式偏差（用于「已排除」结论）
# 371,732.04 = Σ base_val（与 base_total 差 0.01）
EXTRA = [5580.65, 5650.23, 502.15, 784.02, 163.33, 91.66, 253.48, 7129.76, 4327.42, 371732.04]
for v in EXTRA:
    AMOUNTS.update(forms(v))

AMOUNTS = {a for a in AMOUNTS if not re.fullmatch(r'\d{1,2}', a)}

NOT_SUFFIX = (r'(?![\d,.])(?!\s*(?:%|元|万|亿|美元|港元|点|bp|倍|条|次|只|家|个|日|年|月|季|pct|股|桶))'
              r'(?!\s*[~～—－])'
              r'(?!\s*/\s*(?:\d|total|n\b))')

CTX_GUARD = re.compile(
    r'(?:n\s*=\s*\d*\s*/\s*\d*\s*/\s*|样本量[^，。；]{0,12}|bytes[^，。；]{0,3}'
    r'|\d{2,}\s*/\s*|指数[^，。；]{0,6}|点位[^，。；]{0,4}|收盘[^，。；]{0,6}|报\s*$|收\s*$'
    r'|(?:负面|正面|中性|利多|利空)\s*$|置信度\s*$|强度\s*$|波动(?:高|中|低)?\s*$'
    r'|净值[^，。；]{0,4}|批价[^，。；]{0,4}|β|得分\s*$'
    r'|条[^，。；]{0,2}|行[^，。；]{0,2}|张[^，。；]{0,2}|亿元[^，。；]{0,2}'
    r'|计算项[^，。；]{0,10}|ARCHIVED|notional[^，。；]{0,14}|自证|LOF[\s）]'
    r'|事件\s*$|留空\s*$|回填\s*$|新增\s*$|匹配\s*$|条数\s*$|交易日\s*$|第\s*$|档\s*$'
    r'|HTTP\s*$|（\s*$|分为\s*$|净分\s*$|评分\s*$|得分\s*$'
    r'|总价[^，。；]{0,4}|万桶|桶/日|美元/桶|点\s*$|距[^，。；]{0,3}$)'
)


def _url_spans(text):
    spans = []
    for m in re.finditer(r'\]\(([^)\s]+)\)', text):
        spans.append((m.start(1), m.end(1)))
    for m in re.finditer(r'https?://[^\s)\]，。；]+', text):
        spans.append((m.start(), m.end()))
    return spans


def fix(text):
    changes = []
    urls = _url_spans(text)
    for amt in sorted(AMOUNTS, key=len, reverse=True):
        pat = re.compile(r'(?<![\d,.=])([+-]?)' + re.escape(amt) + NOT_SUFFIX)

        def rep(m):
            if any(a <= m.start() and m.end() <= b for a, b in urls):
                return m.group(0)
            head = text[max(0, m.start() - 30):m.start()]
            if CTX_GUARD.search(head):
                return m.group(0)
            changes.append(text[max(0, m.start() - 18):m.end() + 6].replace('\n', ' '))
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
        for c in ch:
            print('    ·', c)
        print(f'   白名单 {len(AMOUNTS)} 条；「## 」{len(re.findall(r"^## ", s, re.M))}；'
              f'「### 」{len(re.findall(r"^### ", s, re.M))}；正文 {len(s)} 字符')
        grand += len(ch)
        if not dry and ch:
            open(f, 'w', encoding='utf-8').write(out)
    print(f'合计 {grand} 处' + ('（dry-run，未写盘）' if dry else ''))


if __name__ == '__main__':
    main()
