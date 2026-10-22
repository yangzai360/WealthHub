#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fix_amount_unit_20261022_intraday.py — 「绝对金额必须带元」补齐器 / 回归守卫
（2026-10-22 **13:45 盘中调仓建议档** · 档型③「正常交易日盘中」：A股 + 港股 双开市、美股未开盘）

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

# ---- 本档盘中产物 ----
ip = json.load(open(os.path.join(H, 'portfolio_intraday_20261022.json'), encoding='utf-8'))
AMOUNTS |= forms(ip['archived_base'])
AMOUNTS |= forms(ip['est_total_weight_base'])
AMOUNTS |= forms(abs(ip['total_delta']))
for t, v in ip['tracks'].items():
    AMOUNTS |= forms(v['mv'])
    AMOUNTS |= forms(abs(v['delta']))
AMOUNTS |= forms(ip['med_exposure'])
AMOUNTS |= forms(ip['est_total_weight_base'] - ip['med_exposure'])   # 非医药含现金 B
for k in ('pure_hk', 'cn_internet', 'hk_broad', 'total'):
    AMOUNTS |= forms(ip['hk_split'][k])
sl = ip['stale_nav_legs']
AMOUNTS |= forms(sl['us_medical']['notional_mv'])
for k in ('band_low', 'band_mid', 'band_high'):
    AMOUNTS |= forms(abs(sl['us_medical'][k]))
AMOUNTS |= forms(sl['cn_internet']['notional_mv'])
for k, v in ip['sensitivity'].items():
    AMOUNTS |= forms(abs(v['delta']))
dc = ip['discipline_cut']
AMOUNTS |= forms(dc['cut1'])
AMOUNTS |= forms(dc['cut2'])
AMOUNTS |= forms(dc['cumulative_amount'])
pp = dc['preplan']
AMOUNTS |= forms(pp['amount'])
AMOUNTS |= forms(pp['cum_after'])
AMOUNTS |= forms(pp['hk_after'])
AMOUNTS |= forms(pp['cash_after'])
np_ = dc['new_plan_3950']
AMOUNTS |= forms(np_['amount'])
# 逐券今日盘中损益（归因段引用）
for x in ip['detail']:
    AMOUNTS |= forms(abs(x.get('delta') or 0))

# ---- 基准修正件（跨档对照值）----
for v in (7129.76, 3694.64):
    AMOUNTS |= forms(v)

# ---- 报告侧派生/手算值（逐项标注来源）----
# 1,332.86 = 弹性区间宽度（6,659.06 − 5,326.20）
# 4,464.82 = 尾盘两端差（8,110.40 − 3,645.58）
# 1,831.10 = 0.5% × 366,220.34 元（医药反向线减配预案，下一档建）
# 11,098.02 = 两市成交额（亿元口径，NOT_SUFFIX 已排除「亿」）
AMOUNTS |= {'1,332.86', '1,332', '4,464.82', '4,464', '1,831.10', '1,831'}

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
