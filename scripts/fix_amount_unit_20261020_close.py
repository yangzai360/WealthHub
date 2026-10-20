#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fix_amount_unit_20261020_close.py — 「绝对金额必须带元」补齐器 / 回归守卫
（2026-10-20 **20:00 盘后复盘档** · 档型「正常交易日收盘」A股 15:00 + 港股复市 16:00）

⚠️ §3.112e / §3.145g / §3.112e：白名单**逐档重建**，来源 = 本档产物
   data/processed/history/portfolio_close_20261020.json （tracks mv/pnl、detail mv0_new/est_pnl、
   未定价 notional、影子估算、港联系三段、纪律台账、QDII 兑现额）
   data/processed/history/portfolio_close_20261019_fix.json （基准对比值）
⚠️ 白名单禁纳：① 指数点位（3,735.37 / 4,045.91 / 12,422.9632）
   ② 百分比与 β ③ 计数类（3,121 / 74 / 22 / n 值 / 回填 71）
   ④ 两位及以下纯整数（§3.145g 硬红线）⑤ 批价（1,730-1,760 / 770 / 820）⑥ 油价（109.55 / 103.66 美元）

用法：python scripts/fix_amount_unit_20261020_close.py [--dry]
"""
import os
import re
import sys
import json

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
H = os.path.join(REPO, 'data/processed/history')
TARGETS = [os.path.join(REPO, 'reports', 'daily', '2026-10-20.md')]


def forms(x):
    """exact（千分位两位小数）与四舍五入（整数千分位）两种记法；两位及以下纯整数不入（§3.145g）。
    零值不入白名单：`0.00` 会误伤表格中的 β / 涨跌幅单元格（§3.145g 误伤复盘）。
    < 1 的金额不入：正文已逐处带「元」，且小数两位极易与指数/净值误撞。"""
    out = set()
    v = float(x)
    if abs(v) < 1:
        return out
    out.add(f'{abs(v):,.2f}')
    b = f'{round(abs(v)):,d}'
    if ',' in b or len(b) > 3:
        out.add(b)
    return out


AMOUNTS = set()

pc = json.load(open(os.path.join(H, 'portfolio_close_20261020.json'), encoding='utf-8'))
for k in ('base_total', 'total_mv', 'est_total_pnl', 'est_total_pnl_best', 'est_total_pnl_worst',
          'est_total_pnl_high', 'est_total_pnl_low', 'unpriced_total', 'priceable_total',
          'med_exposure', 'qdii_mv', 'lof_164906_mv', 'hk_total'):
    if pc.get(k) is not None:
        AMOUNTS |= forms(abs(pc[k]))
for t, v in pc['tracks'].items():
    AMOUNTS |= forms(v['mv'])
    AMOUNTS |= forms(abs(v['pnl']))
for x in pc['detail']:
    if x.get('mv0_new'):
        AMOUNTS |= forms(x['mv0_new'])
    if x.get('est_pnl'):
        AMOUNTS |= forms(abs(x['est_pnl']))
for u in pc['unpriced']:
    AMOUNTS |= forms(u['mv'])
for k, v in pc['hk_split'].items():
    AMOUNTS |= forms(v)
for k, v in pc['hk_split_pnl'].items():
    AMOUNTS |= forms(abs(v))
AMOUNTS |= forms(abs(pc['unpriced_shadow']['total_est_pnl']))
for r in pc['unpriced_shadow']['rows']:
    AMOUNTS |= forms(r['mv'])
    if r['est_pnl']:
        AMOUNTS |= forms(abs(r['est_pnl']))
d = pc['discipline']
for k in ('cut1', 'cut2', 'cumulative_amount'):
    if isinstance(d[k], dict):
        AMOUNTS |= forms(d[k]['amount'])
    else:
        AMOUNTS |= forms(d[k])
# 10/19 基准件对比值
b19 = json.load(open(os.path.join(H, 'portfolio_close_20261019_fix.json'), encoding='utf-8'))
AMOUNTS |= forms(b19['total_mv'])
AMOUNTS |= forms(abs(b19['est_total_pnl']))
for t, v in b19['tracks'].items():
    AMOUNTS |= forms(v['mv'])
    AMOUNTS |= forms(abs(v['pnl']))

# ---- 报告侧派生值（逐项可复算，来源写明）----
# 1,256.96÷756.05 = 1.66 倍（正文已带「倍」）；527.94 = 756.05 − 228.11（真实收益）
# 23,006.75 = 13,943.60 + 9,063.15（未定价 notional）；1,864.60 = 372,920.01 × 0.5%
# 5,651.50 = 3,786.90 + 1,864.60；2,500 = 83,205.02 × 3% 量级
# 373.10 = 144.99 + 138.11 + 90.00；297.31 = 19.20 + 51.92 + 226.19
AMOUNTS |= {'23,006.75', '527.94', '1,864.60', '1,864', '5,651.50', '5,651',
            '373.10', '373', '297.31', '297', '2,500', '410.87', '232.37',
            '230.72', '124.60', '627.22', '144.99', '138.11', '90.00', '88.10',
            '57.30', '54.54', '19.20', '51.92', '226.19', '170.35', '180.15',
            '47.96', '136.00', '214.00', '568.00', '88.40', '62.60', '40.90'}
AMOUNTS = {a for a in AMOUNTS if not re.fullmatch(r'\d{1,2}', a)}

NOT_SUFFIX = (r'(?![\d,.])(?!\s*(?:%|元|万|亿|美元|港元|点|bp|倍|条|次|只|家|个|日|年|月|季|pct|股|桶))'
              r'(?!\s*[~～—－])'
              r'(?!\s*[×÷*])'
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
    r'|总价[^，。；]{0,4}|万桶|桶/日|美元/桶|点\s*$|距[^，。；]{0,3}$'
    r'|n\s*=\s*\d+|全库\s*$|累计\s*$|共\s*$|约\s*$|[×÷*/]\s*$)'
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
