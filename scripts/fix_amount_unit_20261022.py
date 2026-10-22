#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fix_amount_unit_20261022.py — 「绝对金额必须带元」补齐器 / 回归守卫
（2026-10-22 **08:00 盘前分析档** · 档型③「正常交易日盘前」：A股 + 港股 + 美股 均正常交易日）

⚠️ §3.112e / §3.145g：白名单**逐档重建**，来源 = 本档产物
   data/processed/history/portfolio_close_20261021_fix.json （基准修正件：tracks mv/pnl / total_mv / est_total_pnl）
   data/processed/history/portfolio_close_20261021.json     （修正前原值，用于「−810.48 元 → −934.57 元」三件套）
   data/processed/history/portfolio_preopen_20261022.json   （本档：med_mv / 港联系三段 / QDII 区间 / 情景合计 / 预案）
⚠️ 白名单禁纳：① 指数点位（3,713.0277 / 3,994.77 / 12,300.0884 / 178.94）② 百分比与 β
   ③ 计数类（3,216 / 68 / 30 / 43 / n 值）④ 两位及以下纯整数（§3.145g 硬红线）
   ⑤ 批价与零售价（1,309.69 / 1,700）⑥ 原油价（97.15 美元）⑦ 点位差与点数（5.23 点 / 360.21 点）
   ⑧ 亿元类（42,433 亿元 / 324.4 亿元 / 1.1 亿美元 / 11.85 亿美元）

用法：python scripts/fix_amount_unit_20261022.py [--dry]
"""
import os
import re
import sys
import json

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
H = os.path.join(REPO, 'data/processed/history')
TARGETS = [os.path.join(REPO, 'reports', 'daily', '2026-10-22.md')]


def forms(x):
    """exact（千分位两位小数）与四舍五入（整数千分位）两种记法；两位及以下纯整数不入（§3.145g）。
    零值不入白名单；< 1 的金额不入。"""
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

# ---- 基准：10/21 收盘修正件 ----
fx = json.load(open(os.path.join(H, 'portfolio_close_20261021_fix.json'), encoding='utf-8'))
for k in ('total_mv', 'base_total', 'mv0_new'):
    if k in fx:
        AMOUNTS |= forms(fx[k])
for t, v in fx['tracks'].items():
    AMOUNTS |= forms(v['mv'])
    AMOUNTS |= forms(abs(v['pnl']))
AMOUNTS |= forms(abs(fx['est_total_pnl']))
AMOUNTS |= forms(fx.get('med_mv', 0))

# ---- 修正前原值（用于「−810.48 元 → −934.57 元」三件套）----
og = json.load(open(os.path.join(H, 'portfolio_close_20261021.json'), encoding='utf-8'))
AMOUNTS |= forms(og['total_mv'])
AMOUNTS |= forms(abs(og['est_total_pnl']))
for t, v in og['tracks'].items():
    AMOUNTS |= forms(abs(v['pnl']))

# ---- 本档盘前产物 ----
po = json.load(open(os.path.join(H, 'portfolio_preopen_20261022.json'), encoding='utf-8'))
AMOUNTS |= forms(po['med_mv'])
AMOUNTS |= forms(po['med_mv'] - po['tracks']['美股标普医药']['mv'])
for v in po['hk_pending_digest']['segments'].values():
    AMOUNTS |= forms(v)
AMOUNTS |= forms(po['hk_pending_digest']['total_mv'])
AMOUNTS |= forms(po['qdii_pending']['notional'])
AMOUNTS |= forms(abs(po['qdii_pending']['low']))
AMOUNTS |= forms(abs(po['qdii_pending']['mid']))
AMOUNTS |= forms(abs(po['qdii_pending']['high']))
AMOUNTS |= forms(po['qdii_pending']['lof_164906_mv'])
AMOUNTS |= forms(po['discipline']['cumulative_amount'])
AMOUNTS |= forms(po['discipline']['hk_after'])
AMOUNTS |= forms(po['discipline']['cash_after'])
for c in po['scenario']['cases']:
    AMOUNTS |= forms(abs(c['total_pnl']))
    for leg in c['detail'].values():
        AMOUNTS |= forms(abs(leg['pnl']))
# 预案（preplan）四项
pp = po['preplan']
AMOUNTS |= forms(pp['amount'])
AMOUNTS |= forms(pp['amount_alt_basis']['amount'])
AMOUNTS |= forms(pp['cum_after_plan'])
AMOUNTS |= forms(pp['cum_before_plan'])
AMOUNTS |= forms(pp['hk_after_plan'])
AMOUNTS |= forms(pp['cash_after_plan'])

# ---- 报告侧手算/派生值（逐项来自产物字段或逐券明细）----
# 124.09 = 本次跨档补正 Δ；124.07 / 0.02 = 逐赛道 Δ；7,129.76 = mv0 式还原偏差（已排除式）
# 1,858.66 = 备选分母金额；2,144.48 = 四条负腿合计；4.67 = 两分母差额
AMOUNTS |= {'124.09', '124', '124.07', '7,129.76', '7,129',
            '1,858.66', '1,858', '2,144.48', '2,144', '4.67'}

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
