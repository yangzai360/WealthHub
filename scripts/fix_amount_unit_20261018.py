#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fix_amount_unit_20261018.py — 「绝对金额必须带元」补齐器 / 回归守卫
（2026-10-18 **20:00 盘后复盘档（第三章）+ W42 周报** · 档型①「纯非交易日」）

⚠️ §3.112e / §3.145g：白名单**逐档重建**，且本档为「最终档」→ 须覆盖**当日全 3 章 + 周报**
   （本档无盘前/盘中档，第一、二章为占位，正文金额集中在第三章与周报）。
⚠️ 白名单来源（本档产物）：
   data/processed/history/portfolio_close_20261016_fix.json   （本档基准：tracks mv/pnl / total_mv / med / 港联系分段）
   data/processed/history/portfolio_close_20261016.json       （修正前原值，用于「修正前后」明细）
   data/processed/history/risk_stats_close_20261018.json      （链路/夏普/回撤相关金额引用）
   data/processed/history/weekly_stats_20261018.json          （W42 首尾市值 / 赛道周盈亏 / 逐日 pnl）
   data/processed/history/event_stats_20261018_close.json     （事件库计数**不入白名单**，见 CTX_GUARD）
⚠️ 取数口径（§3.104 / §3.112a）：赛道市值一律取 `tracks[track].mv`；`detail[].mv` 为陈旧继承值，禁用。
⚠️ 白名单禁纳：① 计数类（事件条数 2,993 / 样本 n 值 / 交易日数）② 指数点位（3,716.28 / 4,108.24）
   ③ 百分比（−1.8269%）④ 两位及以下纯整数（§3.145g）

用法：python scripts/fix_amount_unit_20261018.py [--dry]
"""
import os
import re
import sys
import json

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
H = os.path.join(REPO, 'data/processed/history')

TARGETS = [
    os.path.join(REPO, 'reports', 'daily', '2026-10-18.md'),
    os.path.join(REPO, 'reports', 'weekly', '2026-W42-周报.md'),
]


def forms(x):
    """exact（千分位）与四舍五入（整数千分位）两种记法；两位及以下纯整数不入（§3.145g）。"""
    out = set()
    v = float(x)
    a = f'{abs(v):,.2f}'
    out.add(a)
    b = f'{round(abs(v)):,d}'
    if ',' in b or len(b) > 3:
        out.add(b)
    return out


AMOUNTS = set()

# ---------- ① 10/16 修正件（本档基准） ----------
fx = json.load(open(os.path.join(H, 'portfolio_close_20261016_fix.json'), encoding='utf-8'))
for k in ('total_mv', 'base_total'):
    AMOUNTS |= forms(fx[k])
for t, v in fx['tracks'].items():
    AMOUNTS |= forms(v['mv'])
    AMOUNTS |= forms(abs(v['pnl']))
AMOUNTS |= forms(abs(fx['est_total_pnl']))
AMOUNTS |= forms(fx['med_exposure'])

# ---------- ② 10/16 原件（修正前原值） ----------
og = json.load(open(os.path.join(H, 'portfolio_close_20261016.json'), encoding='utf-8'))
AMOUNTS |= forms(og['total_mv'])
AMOUNTS |= forms(abs(og['est_total_pnl']))
for t, v in og['tracks'].items():
    AMOUNTS |= forms(abs(v['pnl']))

# ---------- ③ W42 周度 ----------
wk = json.load(open(os.path.join(H, 'weekly_stats_20261018.json'), encoding='utf-8'))
for k in ('base_total', 'end_total'):
    AMOUNTS |= forms(wk[k])
AMOUNTS |= forms(abs(wk['w42']['pnl']))
for t, v in wk['track_week_pnl'].items():
    AMOUNTS |= forms(abs(v))

# ---------- ④ 10/16 `_fix` 逐行明细（fix.rows_fixed） ----------
for r in fx['fix']['rows_fixed']:
    AMOUNTS |= forms(r['mv0_new'])
    AMOUNTS |= forms(abs(r['pnl']))

# ---------- ⑤ 港联系三层 / 纪律台账 / QDII 挂账（报告侧手算值） ----------
AMOUNTS |= {'49,016.02', '49,016', '16,413.29', '16,413', '14,482.05', '14,482', '18,120.68', '18,121',
            '3,786.90', '3,787', '1,882.46', '1,882', '1,904.44', '1,904',
            '27,108.44', '27,108', '32,999.87', '33,000',
            '61,040.92', '61,041', '59,330.09', '59,330', '9,091.59', '9,092',
            '33,129.95', '33,130', '58,318.17', '58,318',
            '1,851.30', '1,851', '401.87', '402', '395.57', '396', '370.11', '370', '25.46', '6.30',
            '137.65', '138', '206.50', '207', '165.20', '165', '229.41', '229',
            '9,068.20', '9,068', '2,722.75', '2,723', '5,736.41', '5,736', '3,331.79', '3,332',
            '1,290.01', '1,290', '2,598.48', '2,598', '2,521.74', '2,522', '1,530.57', '1,531',
            '1,798.15', '1,798', '1,198.49', '1,198', '1,354.74', '1,355', '1,042.85', '1,043',
            '908.27', '908', '922.99', '923', '760.21', '760', '762.83', '763', '674.77', '675',
            '550.63', '551', '496.44', '496', '349.01', '349', '351.70', '352', '318.85', '319',
            '288.65', '289', '256.02', '256', '253.05', '253', '223.94', '224', '166.91', '167',
            '142.08', '142', '163.75', '164', '114.94', '115', '77.76', '78', '129.64', '130',
            '509.68', '510', '107.81', '108', '120.63', '121', '6,888.24', '6,888', '107.81'}
# ---------- ⑥ 逐日赛道级 pnl（周报矩阵表单元格；§3.158b 本档新增） ----------
#  白名单原仅含「周合计/赛道市值」，矩阵表逐日单元格（如 −632.40 / −85.09 / −651.49）不在库内 → 漏补。
#  逐日赛道 pnl 的真相源 = 各日 portfolio_close_<D>_fix.json 的 tracks[track].pnl（§3.104）。
for _ds in ('20261012', '20261013', '20261014', '20261015', '20261016'):
    _p = os.path.join(H, f'portfolio_close_{_ds}_fix.json')
    if not os.path.exists(_p):
        _p = os.path.join(H, f'portfolio_close_{_ds}.json')
    _d = json.load(open(_p, encoding='utf-8'))
    for _t, _v in _d['tracks'].items():
        AMOUNTS |= forms(abs(_v['pnl']))
    AMOUNTS |= forms(abs(_d['est_total_pnl']))

AMOUNTS = {a for a in AMOUNTS if not re.fullmatch(r'\d{1,2}', a)}

# 右侧边界（§3.111c / §3.112e / §3.146a）
NOT_SUFFIX = (r'(?![\d,.])(?!\s*(?:%|元|万|亿|美元|港元|点|bp|倍|条|次|只|家|个|日|年|月|季|pct|股))'
              r'(?!\s*[~～—－])'
              r'(?!\s*/\s*(?:\d|total|n\b))')

# 上下文守卫（§3.109 / §3.112e / §3.156b / §3.145g）
CTX_GUARD = re.compile(
    r'(n\s*=\s*\d*\s*/\s*\d*\s*/\s*|样本量[^，。；]{0,12}|bytes[^，。；]{0,3}'
    r'|\d{2,}\s*/\s*|指数[^，。；]{0,6}|点位[^，。；]{0,4}|收盘[^，。；]{0,6}|报\s*$|收\s*$'
    r'|(?:负面|正面|中性|利多|利空)\s*$|置信度\s*$|强度\s*$|波动(?:高|中|低)?\s*$'
    r'|净值[^，。；]{0,4}|批价[^，。；]{0,4}|零售[^，。；]{0,4}|终端价[^，。；]{0,4}'
    r'|B\s*/?\s*|条[^，。；]{0,2}|行[^，。；]{0,2}|张[^，。；]{0,2}|亿元[^，。；]{0,2}'
    r'|%（\s*$)'
    r'|(?:adjustedCount|investedUnit|planUnit(?:_sum|cat_sum)?|unit|份数|份|个品种)[\s=]{0,3}[^，。；]{0,10}'
    r'|计算项[^，。；]{0,10}|ARCHIVED|notional[^，。；]{0,14}|自证|LOF[\s）]'
    # §3.158（本档新增）：事件库/统计计数上下文（如「全库 2,993 条」「回填 7 条」「n=46」）
    r'|事件\s*$|留空\s*$|回填\s*$|新增\s*$|匹配\s*$|条数\s*$|交易日\s*$|第\s*$|档\s*$'
    # §3.158c（本档新增）：HTTP 状态码（402/500/429…）不是金额——`HTTP 402` 曾被 forms(401.87)→'402'
    #   反推命中并补成「HTTP 402 元」，属**白名单数值碰撞**，必须靠上下文守卫拦截。
    r'|HTTP\s*$|（\s*$|分为\s*$|净分\s*$|评分\s*$|得分\s*$'
)


def _url_spans(text):
    spans = []
    for m in re.finditer(r'\]\(([^)\s]+)\)', text):
        spans.append((m.start(1), m.end(1)))
    for m in re.finditer(r'https?://[^\s)\]，。；]+', text):
        spans.append((m.start(), m.end()))
    return spans


def fix(text: str):
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
        print(f'   白名单 {len(AMOUNTS)} 条；「## 」章节 {len(re.findall(r"^## ", s, re.M))}；'
              f'「### 」小节 {len(re.findall(r"^### ", s, re.M))}；正文 {len(s)} 字符')
        grand += len(ch)
        if not dry and ch:
            open(f, 'w', encoding='utf-8').write(out)
    print(f'合计 {grand} 处' + ('（dry-run，未写盘）' if dry else ''))


if __name__ == '__main__':
    main()
