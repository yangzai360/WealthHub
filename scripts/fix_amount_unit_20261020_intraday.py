#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fix_amount_unit_20261020.py — 「绝对金额必须带元」补齐器 / 回归守卫
（2026-10-20 **13:45 盘中调仓建议档** · 档型③「双市场同开市的正常交易日盘中」）

⚠️ §3.112e / §3.145g：白名单**逐档重建**，来源 = 本档产物
   data/processed/history/portfolio_intraday_20261020.json  （本档：tracks mv/delta / 敏感性 / 港联系三段 / 纪律台账 / QDII 区间）
   data/processed/history/portfolio_close_20261019.json      （修正前原值，用于「原值→修正值」三件套）
   data/processed/history/portfolio_preopen_20261020.json    （本档：med_mv / 港联系三段 / 纪律台账 / QDII 区间 / 情景合计）
⚠️ 白名单禁纳：① 指数点位（3,730.92 / 4,108.24 / 12,467.0785）② 百分比与 β ③ 计数类（3,079 / 53 / 32 / n 值）
   ④ 两位及以下纯整数（§3.145g 硬红线）⑤ 批价（12 大单品总价 10,784 / 普五 807 / 国窖 897 —— 正文已逐处带「元」）
   ⑥ 原油价（103.66 / 98.15 / 109.50 / 115 美元）⑦ 网格倍数与点位差（141.76 点）

用法：python scripts/fix_amount_unit_20261020.py [--dry]
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
    < 1 的金额不入：本档正文已逐处带「元」，且小数两位极易与指数/净值误撞。"""
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

# ---- 本档盘中产物（白名单唯一来源，§3.112e 逐档重建）----
po = json.load(open(os.path.join(H, 'portfolio_intraday_20261020.json'), encoding='utf-8'))
for k in ('archived_base', 'weight_base', 'est_total_archived_base', 'est_total_weight_base',
          'total_delta', 'med_exposure'):
    if po.get(k) is not None:
        AMOUNTS |= forms(abs(po[k]))
for t, v in po['tracks'].items():
    AMOUNTS |= forms(v['mv'])
    AMOUNTS |= forms(abs(v['delta']))
    AMOUNTS |= forms(v['mv0'])
for k, v in po['sensitivity'].items():
    AMOUNTS |= forms(abs(v['delta']))
for k in ('pure_hk', 'cn_internet', 'hk_broad', 'total'):
    AMOUNTS |= forms(po['hk_split'][k])
AMOUNTS |= forms(po['hk_split']['segment_identity']['pure_plus_cn_internet'])
d = po['discipline_cut']
for k in ('cut1', 'cut2', 'cumulative_amount', 'after_hk', 'after_cash'):
    AMOUNTS |= forms(d[k])
sn = po['stale_nav_legs']
AMOUNTS |= forms(sn['us_medical']['notional_mv'])
for k in ('band_low', 'band_mid', 'band_high'):
    AMOUNTS |= forms(abs(sn['us_medical'][k]))
AMOUNTS |= forms(sn['cn_internet']['notional_mv'])

# ---- 报告侧派生值（逐项可复算，来源写明）----
# 302,024.28 / 70,139.69 = 可定价 / 不可定价市值（372,163.97 − 61,040.91 − 9,098.78）
# 546.36 = 港联系较 10/19 收盘（49,054.08）下降额
# 393.53 = 大消费腿 000248(−220.66) + 519915(−172.87)
# 439.89 = 三条主动基（002708 两券位 / 161616 / 000727）合计 delta
# 511.13 = 弹性区间宽度（−441.85 至 +69.28）；2,576.17 = 尾盘两情景差
AMOUNTS |= {'302,024.28', '70,139.69', '546.36', '393.53', '439.89',
            '511.13', '2,576.17', '1,882.46', '1,904.44', '1,882', '1,904',
            '1,851.30', '1,851'}
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
        print(f'   白名单 {len(AMOUNTS)} 条；「## 」{len(re.findall(r"^## ", s, re.M))}；「### 」{len(re.findall(r"^### ", s, re.M))}；正文 {len(s)} 字符')
        grand += len(ch)
        if not dry and ch:
            open(f, 'w', encoding='utf-8').write(out)
    print(f'合计 {grand} 处' + ('（dry-run，未写盘）' if dry else ''))


if __name__ == '__main__':
    main()
