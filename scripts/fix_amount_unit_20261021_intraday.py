#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fix_amount_unit_20261021_intraday.py — 「绝对金额必须带元」补齐器（盘中 13:45 档专用白名单）

档型③「双市场同开市的正常交易日盘中」（A股 第 10 个正常交易日 + 港股正常交易日）

⚠️ §3.112e / §3.149e：白名单**逐档重建**，本档来源 =
   data/processed/history/portfolio_intraday_20261021.json      （本档：delta / mv / 敏感性 / 港股三段 / 挂账区间 / 纪律累计）
   data/processed/history/portfolio_close_20261020_fix.json      （基准：tracks mv/pnl / total_mv / est_total_pnl）
   data/processed/history/portfolio_preopen_20261021.json        （承接：253.41 跨档补正 / 1,863.33 预案 / med_mv）
⚠️ 白名单禁纳（§3.145g 硬红线）：① 指数点位 ② 百分比/β/情绪分 ③ 计数类（条数/样本量/交易日数/字节数）
   ④ 两位及以下纯整数 ⑤ 批价与零售价 ⑥ 规则编号 §3.xxx ⑦ ETF 价格与净值
⚠️ 右侧边界含「比率/计数守卫」`(?!\\s*/\\s*(?:\\d|total|n\\b))`（§3.112e 条款 37）

用法：python scripts/fix_amount_unit_20261021_intraday.py [--dry]
"""
import os
import re
import sys
import json

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
H = os.path.join(REPO, 'data/processed/history')
TARGETS = [os.path.join(REPO, 'reports', 'daily', '2026-10-21.md')]


def forms(x):
    """exact（千分位两位小数）与四舍五入（整数千分位）两种记法；两位及以下纯整数不入。"""
    out = set()
    v = abs(float(x))
    if v < 1:
        return out
    out.add(f'{v:,.2f}')
    b = f'{round(v):,d}'
    if ',' in b or len(b) > 3:
        out.add(b)
    return out


AMOUNTS = set()

# ---- 本档盘中产物 ----
it = json.load(open(os.path.join(H, 'portfolio_intraday_20261021.json'), encoding='utf-8'))
AMOUNTS |= forms(it['archived_base'])
AMOUNTS |= forms(it['total_delta'])
AMOUNTS |= forms(it['est_total_archived_base'])
for t, v in it['tracks'].items():
    AMOUNTS |= forms(v['mv0'])
    AMOUNTS |= forms(v['mv'])
    AMOUNTS |= forms(v['delta'])
    AMOUNTS |= forms(abs(v['delta']))
for k in ('low', 'high', 'base', 'tail_weak', 'tail_strong'):
    AMOUNTS |= forms(it['sensitivity'][k]['delta'])
    AMOUNTS |= forms(abs(it['sensitivity'][k]['delta']))
for k in ('pure_hk', 'cn_internet', 'hk_broad', 'total'):
    AMOUNTS |= forms(it['hk_split'][k])
AMOUNTS |= forms(it['med_exposure'])
sl = it['stale_nav_legs']
AMOUNTS |= forms(sl['us_medical']['notional_mv'])
for k in ('band_low', 'band_mid', 'band_high'):
    AMOUNTS |= forms(sl['us_medical'][k])
AMOUNTS |= forms(sl['cn_internet']['notional_mv'])
dc = it['discipline_cut']
for k in ('cut1', 'cut2', 'cumulative_amount', 'after_hk', 'after_cash'):
    AMOUNTS |= forms(dc[k])
for d in it.get('detail', []):
    for k in ('mv', 'mv0', 'mv0_new', 'est_pnl', 'delta'):
        if k in d:
            AMOUNTS |= forms(d[k])
            AMOUNTS |= forms(abs(d[k]))

# ---- 基准修正件（跨档引用）----
fx = json.load(open(os.path.join(H, 'portfolio_close_20261020_fix.json'), encoding='utf-8'))
AMOUNTS |= forms(fx['total_mv'])
AMOUNTS |= forms(abs(fx['est_total_pnl']))
for t, v in fx['tracks'].items():
    AMOUNTS |= forms(v['mv'])
    AMOUNTS |= forms(abs(v['pnl']))

# ---- 承接盘前档产物 ----
po = json.load(open(os.path.join(H, 'portfolio_preopen_20261021.json'), encoding='utf-8'))
AMOUNTS |= forms(po['med_mv'])
AMOUNTS |= forms(abs(po['qdii_pending']['low']))
AMOUNTS |= forms(abs(po['qdii_pending']['mid']))
AMOUNTS |= forms(abs(po['qdii_pending']['high']))
AMOUNTS |= forms(po['qdii_pending']['notional'])

# ---- 报告侧手算/派生值 ----
# 1,863.33 = 0.5% 预案金额（372,666.60 × 0.5%）；2,234.09 = 尾盘两情景差（2,171.11 + 62.98）
# 62.13 = 弹性区间宽度（1,210.80 − 1,148.67）；8,386.72 / 3,685.08 = 已排除还原式偏差
AMOUNTS |= {'1,863.33', '1,863', '2,234.09', '2,234', '62.13', '8,386.72', '3,685.08'}

AMOUNTS = {a for a in AMOUNTS if not re.fullmatch(r'\d{1,2}', a)}

NOT_SUFFIX = (r'(?![\d,.])(?!\s*(?:%|元|万|亿|美元|港元|点|bp|倍|条|次|只|家|个|日|年|月|季|pct|股|桶|B\b|EFLOPS))'
              r'(?!\s*[~～—－])'
              r'(?!\s*/\s*(?:\d|total|n\b))')

CTX_GUARD = re.compile(
    r'(?:n\s*=\s*\d*\s*/\s*\d*\s*/\s*|样本量[^，。；]{0,12}|bytes[^，。；]{0,3}'
    r'|\d{2,}\s*/\s*|指数[^，。；]{0,6}|点位[^，。；]{0,4}|收盘[^，。；]{0,6}|报\s*$|收\s*$'
    r'|(?:负面|正面|中性|利多|利空)\s*$|置信度\s*$|强度\s*$|波动(?:高|中|低)?\s*$'
    r'|净值[^，。；]{0,4}|批价[^，。；]{0,4}|β|得分\s*$|净分\s*$|评分\s*$'
    r'|条[^，。；]{0,2}|行[^，。；]{0,2}|张[^，。；]{0,2}|亿元[^，。；]{0,2}'
    r'|计算项[^，。；]{0,10}|ARCHIVED|notional[^，。；]{0,14}|自证|LOF[\s）]'
    r'|事件\s*$|留空\s*$|回填\s*$|新增\s*$|匹配\s*$|条数\s*$|交易日\s*$|第\s*$|档\s*$'
    r'|HTTP\s*$|（\s*$|分为\s*$|§|条款\s*$|系数[^，。；]{0,3}|门槛\s*$'
    r'|总价[^，。；]{0,4}|万桶|桶/日|美元/桶|点\s*$|距[^，。；]{0,3}$|关口\s*$'
    r'|J\s*[<=>]|权重[^，。；]{0,2}|n\s*=\s*$)'
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
        pat = re.compile(r'(?<![\d,.=\-/])([+-]?)' + re.escape(amt) + NOT_SUFFIX)

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
