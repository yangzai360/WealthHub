#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fix_amount_unit_close_20261023.py — 「绝对金额必须带元」补齐器 / 回归守卫
（2026-10-23 **20:00 盘后复盘档** · 档型②「正常交易日双收盘」：A股 15:00 + 港股 16:00 + 美股未开盘）

⚠️ §3.112e / §3.145g：白名单**逐档重建**，来源 = 本档产物
   data/processed/history/portfolio_close_20261022_fix.json      （基准修正件）
   data/processed/history/portfolio_close_20261023.json          （本档收盘：tracks / unpriced / hk_split / 纪律台账）
   data/processed/history/portfolio_strategy_close_20261023.json （本档策略：预案 / 累计 / 减仓后权重）
   data/processed/history/portfolio_intraday_20261023.json       （盘中档对照：分腿 mv / delta）
⚠️ 白名单禁纳：① 指数点位（3,690.48 / 3,871.66 / 12,425.26）② 百分比与 β
   ③ 计数类（3,326 / 70 / 18 / 63 / 20 / n 值 / 117）④ 两位及以下纯整数（§3.145g 硬红线）
   ⑤ 批价与零售价（1,335.00 / 1,343.88）⑥ 商品与油价（115 / 14,232）
   ⑦ 亿元/万元类（19,562.58 亿元 / 6,937.76 亿元 / 7,000 万元 / 16.70 亿港元）

用法：python scripts/fix_amount_unit_close_20261023.py [--dry]
"""
import os
import re
import sys
import json

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
H = os.path.join(REPO, 'data/processed/history')
TARGETS = [os.path.join(REPO, 'reports', 'daily', '2026-10-23.md')]


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

# ---- 基准：10/22 收盘修正件 ----
fx = json.load(open(os.path.join(H, 'portfolio_close_20261022_fix.json'), encoding='utf-8'))
for k in ('total_mv', 'base_total'):
    if k in fx:
        AMOUNTS |= forms(fx[k])
for t, v in fx['tracks'].items():
    AMOUNTS |= forms(v['mv'])
    AMOUNTS |= forms(abs(v['pnl']))
AMOUNTS |= forms(abs(fx['est_total_pnl']))

# ---- 本档收盘产物 ----
pc = json.load(open(os.path.join(H, 'portfolio_close_20261023.json'), encoding='utf-8'))
AMOUNTS |= forms(pc['total_mv'])
AMOUNTS |= forms(abs(pc['est_total_pnl']))
AMOUNTS |= forms(pc['base_total'])
for t, v in pc['tracks'].items():
    AMOUNTS |= forms(v['mv'])
    AMOUNTS |= forms(abs(v['pnl']))
AMOUNTS |= forms(pc['med_exposure'])
AMOUNTS |= forms(pc['unpriced_total'])
AMOUNTS |= forms(pc.get('priceable_total') or 0)
AMOUNTS |= forms(pc['qdii_mv'])
AMOUNTS |= forms(pc['lof_164906_mv'])
for k in ('pure', 'concept', 'broad'):
    AMOUNTS |= forms(pc['hk_split'][k])
for k, v in pc['hk_split_pnl'].items():
    AMOUNTS |= forms(abs(v))
AMOUNTS |= forms(pc['hk_total'])
for u in pc['unpriced']:
    AMOUNTS |= forms(u['mv'])
for x in pc['detail']:
    AMOUNTS |= forms(abs(x.get('est_pnl') or 0))
    AMOUNTS |= forms(x.get('mv0_new') or 0)
sh = pc['unpriced_shadow']
AMOUNTS |= forms(sh['total_est_pnl_lo'])
AMOUNTS |= forms(sh['total_est_pnl_hi'])
for r in sh['rows']:
    AMOUNTS |= forms(r['mv'])
    AMOUNTS |= forms(r['est_pnl_lo'])
    AMOUNTS |= forms(r['est_pnl_hi'])
d = pc['discipline']
AMOUNTS |= forms(d['cumulative_amount'])
AMOUNTS |= forms(d['hk_after'])
AMOUNTS |= forms(d['cash_after'])
AMOUNTS |= forms(d['today_action']['discipline_cut_today'])
for key in ('cut1', 'cut2', 'cut3'):
    if isinstance(d.get(key), dict) and 'amount' in d[key]:
        AMOUNTS |= forms(d[key]['amount'])
for p in d['pending_plans']:
    AMOUNTS |= forms(p.get('amount') or 0)

# ---- 本档策略产物 ----
sp = json.load(open(os.path.join(H, 'portfolio_strategy_close_20261023.json'), encoding='utf-8'))
for a in sp['track_actions']:
    if a.get('amount'):
        AMOUNTS |= forms(abs(a['amount']))
    AMOUNTS |= forms(a['mv'])
    AMOUNTS |= forms(abs(a['pnl_today']))
AMOUNTS |= forms(sp['constraints']['med_exposure']['mv'])
AMOUNTS |= forms(sp['total_mv'])
ps = sp['constraints']['pending_plan_stack']
AMOUNTS |= forms(ps['hstech_4000_awaiting_confirm']['amount'])
AMOUNTS |= forms(ps['hstech_3950_executed']['amount'])
AMOUNTS |= forms(sp['discipline_total'])

# ---- 盘中档对照（分腿 mv / delta）----
ip = json.load(open(os.path.join(H, 'portfolio_intraday_20261023.json'), encoding='utf-8'))
AMOUNTS |= forms(ip['archived_base'])
AMOUNTS |= forms(abs(ip['total_delta']))
for t, v in ip['tracks'].items():
    AMOUNTS |= forms(v['mv'])
    AMOUNTS |= forms(abs(v['delta']))
AMOUNTS |= forms(ip['med_exposure'])

# ---- 报告侧派生/手算值（逐项标注来源）----
DERIVED = {
    '1,569.59': '收盘 − 盘中 = 5,434.15 − 3,864.56',
    '892.45': '其他/宽基 92,768.39 − 91,875.94',
    '232.86': 'A股医药 82,247.91 − 82,015.05（口径切换：未定价计 0）',
    '237.18': '恒生科技 29,449.57 − 29,212.39（含 164906 净值 −3.24%）',
    '204.63': '大消费 75,348.69 − 75,144.06',
    '286.77': '164906 双账户拖累 = −150.54 − 136.23',
    '202.98': 'QDII 上越界 = 942.55 − 739.57',
    '1,856.43': '剧本 B 新线建案 = 0.5% × 371,285.52',
    '4,275.58': '两市放量 = 19,562.58 − 15,287（本地同口径）',
    '7,508.89': '累计 + 4,000 案 = 5,645.56 + 1,863.33',
    '21,703.50': '若 4,000 案执行后恒科 = 23,566.83 − 1,863.33',
    '36,721.86': '若 4,000 案执行后现金 = 34,858.53 + 1,863.33',
    '23,566.83': 'cut3 后恒科 = 29,212.39 − 5,645.56',
    '34,858.53': 'cut3 后现金 = 29,212.97 + 5,645.56',
    '3,786.90': 'cut1 + cut2 = 1,882.46 + 1,904.44',
}
for k in DERIVED:
    AMOUNTS.add(k)
    if k.count(',') >= 2:
        AMOUNTS.add(f'{float(k.replace(",", "")):.2f}')

AMOUNTS = {a for a in AMOUNTS if not re.fullmatch(r'\d{1,2}', a)}
# 守卫：权重合计 / 情绪分等「非金额」数字即使命中白名单也不补（§3.112e 复发项）
DENY = {'100.00', '1.30', '4.94', '0.00', '0.01'}
AMOUNTS -= DENY

NOT_SUFFIX = (r'(?![\d,.])(?!\s*(?:%|元|万|亿|美元|港元|点|bp|倍|条|次|只|家|个|日|年|月|季|pct|股|桶))'
              r'(?!\s*[~～—－])'
              r'(?!\s*/\s*(?:\d|total|n\b))')

CTX_GUARD = re.compile(
    r'(?:n\s*=\s*\d*\s*/\s*\d*\s*/\s*|样本量[^，。；]{0,12}|bytes[^，。；]{0,3}'
    r'|\d{2,}\s*/\s*|指数[^，。；]{0,6}|点位[^，。；]{0,4}|收盘[^，。；]{0,6}|报\s*$|收\s*$'
    r'|Σ\s*(?:pct|权重|tracks)|权重\s*=|合计\s*=|=\s*\*\*$'
    r'|(?:负面|正面|中性|利多|利空)\s*$|置信度\s*$|强度\s*$|波动(?:高|中|低)?\s*$'
    r'|净值[^，。；]{0,4}|批价[^，。；]{0,4}|β|得分\s*$|净分[^，。；]{0,6}|暴露加权[^，。；]{0,6}'
    r'|条[^，。；]{0,2}|行[^，。；]{0,2}|张[^，。；]{0,2}|亿元[^，。；]{0,2}'
    r'|计算项[^，。；]{0,10}|ARCHIVED|notional[^，。；]{0,14}|自证|LOF[\s）]'
    r'|事件\s*$|留空\s*$|回填\s*$|新增\s*$|匹配\s*$|条数\s*$|交易日\s*$|第\s*$|档\s*$'
    r'|HTTP\s*$|（\s*$|分为\s*$|净分\s*$|评分\s*$|得分\s*$'
    r'|总价[^，。；]{0,4}|万桶|桶/日|美元/桶|点\s*$|距[^，。；]{0,3}$'
    r'|点位|成交额[^，。；]{0,4}|开\s*$|收于\s*$|报于\s*$)'
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
