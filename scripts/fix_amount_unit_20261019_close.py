#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fix_amount_unit_20261019_close.py — 「绝对金额必须带元」补齐器 / 回归守卫
（2026-10-19 **20:00 盘后复盘档（第三章）** · 档型②「反向混合档」收盘）
（同日 08:00 盘前档已有 `fix_amount_unit_20261019.py`；本文件为盘后阶段独立白名单，不覆盖前档）

⚠️ §3.112e / §3.145g：白名单**逐档重建**，覆盖当日全 3 章
⚠️ 白名单来源（本档产物）：
   portfolio_close_20261019.json  （tracks mv/pnl / total_mv / base_total / med / 港联系分段 / unpriced / detail）
   portfolio_close_20261016_fix.json（本档基准 total_mv）
   portfolio_intraday_20261019.json（盘中估算，用于「收盘 vs 盘中」对比）
⚠️ 取数口径：赛道市值一律 `tracks[track].mv`；`detail[].mv` 为陈旧继承值，禁用（§3.104）
⚠️ 白名单禁纳：计数类（事件 3,047 条 / n 值 / 交易日数）、指数点位、百分比、两位及以下纯整数
用法：python scripts/fix_amount_unit_20261019_close.py [--dry]
"""
import os
import re
import sys
import json

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
H = os.path.join(REPO, 'data/processed/history')

TARGETS = [os.path.join(REPO, 'reports', 'daily', '2026-10-19.md')]


def forms(x):
    out = set()
    v = float(x)
    out.add(f'{abs(v):,.2f}')
    b = f'{round(abs(v)):,d}'
    if ',' in b or len(b) > 3:
        out.add(b)
    return out


AMOUNTS = set()

pc = json.load(open(os.path.join(H, 'portfolio_close_20261019.json'), encoding='utf-8'))
for k in ('total_mv', 'base_total', 'med_exposure', 'hk_total', 'unpriced_total',
          'priceable_total', 'qdii_mv', 'lof_164906_mv'):
    AMOUNTS |= forms(pc[k])
AMOUNTS |= forms(abs(pc['est_total_pnl']))
for t, v in pc['tracks'].items():
    AMOUNTS |= forms(v['mv'])
    AMOUNTS |= forms(abs(v['pnl']))
for k, v in pc['hk_split'].items():
    AMOUNTS |= forms(v)
for k, v in pc['hk_split_pnl'].items():
    AMOUNTS |= forms(abs(v))
for u in pc['unpriced']:
    AMOUNTS |= forms(u['notional'])
for d in pc['detail']:
    AMOUNTS |= forms(abs(d['est_pnl']))

pi = json.load(open(os.path.join(H, 'portfolio_intraday_20261019.json'), encoding='utf-8'))
AMOUNTS |= forms(abs(pi['total_delta']))
for t, v in pi['tracks'].items():
    AMOUNTS |= forms(abs(v['delta']))

base = json.load(open(os.path.join(H, 'portfolio_close_20261016_fix.json'), encoding='utf-8'))
AMOUNTS |= forms(base['total_mv'])

# 报告侧手算值（§3.145g：仅绝对金额，两位以上）
AMOUNTS |= {
    '3,786.90', '3,787', '1,882.46', '1,882', '1,904.44', '1,904',
    '27,150.28', '27,150', '32,999.87', '33,000',
    '61,040.91', '61,041', '59,330.09', '59,330',
    '20,084.79', '20,085', '15,131.41', '15,131', '4,939.20', '4,939',
    '20,070.61', '20,071', '351,861.66', '351,862',
    '49,054.08', '49,054', '16,406.00', '16,406', '14,531.18', '14,531', '18,116.90', '18,117',
    '1,851.30', '1,851', '206.50', '207', '137.65', '138', '165.20', '165',
    '424.79', '425', '716.80', '717', '76.13', '76', '49.13', '49',
    '128.39', '128', '430.60', '431', '213.79', '214', '256.08', '256', '89.13', '89',
}

AMOUNTS = {a for a in AMOUNTS if not re.fullmatch(r'\d{1,2}', a)}

NOT_SUFFIX = (r'(?![\d,.])(?!\s*(?:%|元|万|亿|美元|港元|点|bp|倍|条|次|只|家|个|日|年|月|季|pct|股))'
              r'(?!\s*[~～—－])'
              r'(?!\s*/\s*(?:\d|total|n\b))')

CTX_GUARD = re.compile(
    r'(n\s*=\s*\d*\s*/\s*\d*\s*/\s*|样本量[^，。；]{0,12}|bytes[^，。；]{0,3}'
    r'|\d{2,}\s*/\s*|指数[^，。；]{0,6}|点位[^，。；]{0,4}|收盘[^，。；]{0,6}|报\s*$|收\s*$'
    r'|(?:负面|正面|中性|利多|利空)\s*$|置信度\s*$|强度\s*$|波动(?:高|中|低)?\s*$'
    r'|净值[^，。；]{0,4}|批价[^，。；]{0,4}|零售[^，。；]{0,4}|终端价[^，。；]{0,4}'
    r'|B\s*/?\s*|条[^，。；]{0,2}|行[^，。；]{0,2}|张[^，。；]{0,2}|亿元[^，。；]{0,2}'
    r'|%（\s*$)'
    r'|(?:adjustedCount|investedUnit|planUnit(?:_sum|cat_sum)?|unit|份数|份|个品种)[\s=]{0,3}[^，。；]{0,10}'
    r'|计算项[^，。；]{0,10}|ARCHIVED|notional[^，。；]{0,14}|自证|LOF[\s）]'
    r'|事件\s*$|留空\s*$|回填\s*$|新增\s*$|匹配\s*$|条数\s*$|交易日\s*$|第\s*$|档\s*$'
    r'|HTTP\s*$|（\s*$|分为\s*$|净分\s*$|评分\s*$|得分\s*$'
)



def _guard_v2(head, tail):
    """§3.112e 追加守卫：偏差序列 / 纯表格单元格 / 守卫值上下文。"""
    # ① 守卫值上下文：mv 0.01 / pnl 0.00 / 还原式 0.0000 / 偏差 0.00（单位是「元」但语义是偏差，且常并列出现）
    if re.search(r'(?:\bmv|\bpnl|还原式|偏差|\bdev)\s*(?:\*\*)?\s*$', head):
        return True
    # ② 斜杠分隔的序列（如 （−27.00 / +76.13 / −4.85））
    if re.search(r'/\s*$', head) and re.match(r'\s*[+\u2212-]?\d', tail):
        return True
    if re.search(r'[（(]\s*(?:\*\*)?\s*[+\u2212-]?\s*$', head) and re.match(r'\s*/\s*[+\u2212-]?\d', tail):
        return True
    # ③ 纯表格单元格（允许 ** 包夹）：| 0.00 | 或 | **0.00** |
    if re.search(r'\|\s*(?:\*\*)?\s*$', head) and re.match(r'\s*(?:\*\*)?\s*\|', tail):
        return True
    return False


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
            tail = text[m.end():m.end() + 8]
            if CTX_GUARD.search(head):
                return m.group(0)
            if _guard_v2(head, tail):
                return m.group(0)
            changes.append(text[max(0, m.start() - 18):m.end() + 6].replace('\n', ' '))
            return m.group(0) + ' 元'

        text = pat.sub(rep, text)
    return text, changes


def main():
    dry = '--dry' in sys.argv
    grand = 0
    print(f'白名单 {len(AMOUNTS)} 条；目标 {len(TARGETS)} 个文件')
    for p in TARGETS:
        if not os.path.exists(p):
            print('MISS', p)
            continue
        s = open(p, encoding='utf-8').read()
        new, ch = fix(s)
        grand += len(ch)
        print(f'\n{os.path.basename(p)}: 补「元」{len(ch)} 处')
        for c in ch:
            print('   ', c)
        if not dry and ch:
            open(p, 'w', encoding='utf-8').write(new)
    print(f'合计 {grand} 处' + ('（dry-run，未写盘）' if dry else ''))


if __name__ == '__main__':
    main()
