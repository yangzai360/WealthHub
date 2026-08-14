# -*- coding: utf-8 -*-
"""盘后档 2026-08-14：事件库当日回填 actual_ret_1d + 8/13 遗留美股医药用 IYH/XLV 8/13 回填 + 样本统计"""
import json, os, re, glob
from collections import defaultdict, Counter

BASE = '/Users/jieyang/Documents/WealthHub'
EV = os.path.join(BASE, 'data/processed/events')
TODAY = '2026-08-14'

ev14 = json.load(open(os.path.join(EV, f'events-{TODAY}.json'), encoding='utf-8'))

# ---------- 1. 按标题关键词归类赛道（含美股医疗前置规则） ----------
def classify(title):
    t = title
    if re.search(r'美股医疗|XLV|IYH|标普医药|礼来|辉瑞|强生|默沙东', t):
        return '美股标普医药'
    if re.search(r'创新药|医药|医疗|药明|CRO|基药|集采|医药股|药企|免疫', t):
        return 'A股医药'
    if re.search(r'白酒|茅台|五粮液|消费|食品饮料|飞天|批价|奶价|酒', t):
        return '大消费'
    if re.search(r'恒生科技|腾讯|联想|港股|恒指|中概|智谱|MSCI|科网|MiniMax|京东', t):
        return '恒生科技'
    if re.search(r'CPI|美联储|加息|美股|油价|黄金|央行|逆回购|日本|日元|宏观|指数|PPI|伊朗|霍尔木兹', t):
        return '宏观'
    return '其他/宽基'

for x in ev14:
    if x.get('track') in ('宏观', '业绩', '行业事件', '政策', None, ''):
        x['track'] = classify(x.get('title', ''))
    if not isinstance(x.get('reference'), dict):
        x['reference'] = {'ret_3d': None, 'ret_5d': None, 'ret_10d': None, 'max_vol': None,
                          'confidence': None, 'actual_ret_1d': None, 'actual_date': None, 'ret_1d_ref': None}
    # strength 从 sentiment 回填
    if not x.get('strength') and x.get('score'):
        x['strength'] = x['score']

# ---------- 2. 回填 8/14 当日 actual_ret_1d（赛道当日实际走势） ----------
track_ret = {
    'A股医药': -1.08,       # 医疗ETF -1.13% / 医药ETF广发 -1.02% 均值（CRO高位分化日，药明-1.90%）
    '大消费': -1.45,         # 中证消费 12,658.53 -1.45%（茅台中报前夜白酒领跌）
    '恒生科技': -1.77,       # HSTECH 4,707.62 -1.77%（跌破4,780，京东-10.41%/AI双雄领跌）
    '宏观': 0.01,            # 上证指数 3,927.18 +0.01%（CPO/光纤强势 vs 日本加息预期）
    '其他/宽基': -0.15,      # 广联达-1.29%/通威-0.70% 近似
    # 美股标普医药留空（8/14 美股未开盘，待 8/15 盘前用 IYH/XLV 回填）
}
cnt = 0
for x in ev14:
    r = x['reference']
    if r.get('actual_ret_1d') is not None:
        continue
    if x['track'] in track_ret:
        r['actual_ret_1d'] = track_ret[x['track']]
        r['actual_date'] = TODAY
        r['ret_1d_ref'] = '赛道指数/ETF收盘'
        cnt += 1
json.dump(ev14, open(os.path.join(EV, f'events-{TODAY}.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(f'8/14 当日回填 {cnt} 条；美股标普医药留空 {sum(1 for x in ev14 if x["track"]=="美股标普医药" and x["reference"].get("actual_ret_1d") is None)} 条待 8/15')
print('8/14 track 分布:', dict(Counter(x['track'] for x in ev14)))

# ---------- 3. 8/13 遗留美股标普医药回填（用 XLV/IYH 8/13 收盘） ----------
# XLV 8/13: 168.38 -0.04%（8/14 盘前已归档）；IYH 8/13: 71.17 +0.39% 滞后至8/12
us_ret = -0.04  # XLV 8/13 -0.04%（IYH 滞后取 XLV）
ev13_path = os.path.join(EV, 'events-2026-08-13.json')
ev13 = json.load(open(ev13_path, encoding='utf-8'))
fix13 = 0
for x in ev13:
    r = x.get('reference') or {}
    if x.get('track') == '美股标普医药' and r.get('actual_ret_1d') is None:
        r['actual_ret_1d'] = us_ret
        r['actual_date'] = '2026-08-13'
        r['ret_1d_ref'] = 'XLV 8/13收盘(-0.04%)'
        fix13 += 1
json.dump(ev13, open(ev13_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(f'8/13 遗留美股医药回填 {fix13} 条')

# ---------- 4. 全量样本统计 ----------
all_ev = []
for f in sorted(glob.glob(os.path.join(EV, 'events-*.json'))):
    all_ev += json.load(open(f, encoding='utf-8'))
print('事件库全量累计:', len(all_ev), '条')
stats = defaultdict(lambda: {'n': 0, 'rets': [], 'sp': {'n': 0, 'rets': []}, 'sn': {'n': 0, 'rets': []}})
for x in all_ev:
    r = x.get('reference') or {}
    v = r.get('actual_ret_1d')
    if v is None:
        v = x.get('actual_ret_1d')  # 兼容顶层字段
    if v is None:
        continue
    t = x.get('track', '?'); s = stats[t]
    s['n'] += 1; s['rets'].append(v)
    strength = x.get('strength') or x.get('score') or 0
    if strength >= 60 and x.get('sentiment') == '正面':
        s['sp']['n'] += 1; s['sp']['rets'].append(v)
    if strength >= 60 and x.get('sentiment') == '负面':
        s['sn']['n'] += 1; s['sn']['rets'].append(v)
print('\n赛道 1 日样本统计（含 8/14）:')
for t, s in sorted(stats.items()):
    def avg(lst): return round(sum(lst)/len(lst), 2) if lst else None
    print(f"  {t}: n={s['n']} 均值={avg(s['rets'])} | 强正面 n={s['sp']['n']} 均值={avg(s['sp']['rets'])} | 强负面 n={s['sn']['n']} 均值={avg(s['sn']['rets'])}")
