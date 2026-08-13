# -*- coding: utf-8 -*-
"""盘后档 2026-08-13：修复事件库 track 归类 + 补齐 reference + 回填 actual_ret_1d + 样本统计"""
import json, os, re, glob
from collections import defaultdict

BASE = '/Users/jieyang/Documents/WealthHub'
EV = os.path.join(BASE, 'data/processed/events')
TODAY = '2026-08-13'

ev13 = json.load(open(os.path.join(EV, f'events-{TODAY}.json'), encoding='utf-8'))

# ---------- 1. 按标题关键词归类赛道 ----------
def classify(title, category):
    t = title
    if re.search(r'创新药|医药|医疗|药明|CRO|基药|集采|医药股|药企|免疫', t):
        return 'A股医药'
    if re.search(r'白酒|茅台|五粮液|消费|食品饮料|飞天|批价|奶价|酒', t):
        return '大消费'
    if re.search(r'恒生科技|腾讯|联想|港股|恒指|中概|智谱|MSCI|科网', t):
        return '恒生科技'
    if re.search(r'美股医疗|XLV|IYH|礼来|辉瑞', t):
        return '美股标普医药'
    if re.search(r'CPI|美联储|加息|美股|油价|黄金|央行|逆回购|日本|日元|中汽协|宏观|指数', t):
        return '宏观'
    return '其他/宽基'

for x in ev13:
    # 只有 track 是分类名（宏观/业绩/行业事件/政策）或缺失时才重归类
    if x.get('track') in ('宏观', '业绩', '行业事件', '政策', None, ''):
        x['track'] = classify(x.get('title', ''), x.get('category', ''))
    # 补齐 reference 结构
    if not isinstance(x.get('reference'), dict):
        x['reference'] = {'ret_3d': None, 'ret_5d': None, 'ret_10d': None, 'max_vol': None,
                          'confidence': None, 'actual_ret_1d': None, 'actual_date': None, 'ret_1d_ref': None}

# ---------- 2. 回填 8/13 当日 actual_ret_1d（赛道当日实际走势） ----------
track_ret = {
    'A股医药': 0.94,       # 医疗ETF 512170 +1.43% / 医药ETF广发 159938 +0.44% 均值（创新药/CRO领涨日）
    '大消费': 0.16,         # 中证消费 12,844.67 +0.16%
    '恒生科技': 0.33,       # HSTECH 4,792.39 +0.33%（腾讯-4.46% vs 联想+20.18% 分化）
    '宏观': -0.50,          # 上证指数 3,926.96 -0.50%（日本加息预期尾盘跳水）
    '其他/宽基': -0.50,     # 上证近似
    # 美股标普医药留空（8/13 美股未开盘，待 8/14 盘前用 IYH/XLV 回填）
}
cnt = 0
for x in ev13:
    r = x['reference']
    if r.get('actual_ret_1d') is not None:
        continue
    if x['track'] in track_ret:
        r['actual_ret_1d'] = track_ret[x['track']]
        r['actual_date'] = TODAY
        r['ret_1d_ref'] = '赛道指数/ETF收盘'
        cnt += 1
json.dump(ev13, open(os.path.join(EV, f'events-{TODAY}.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(f'8/13 当日回填 {cnt} 条；美股标普医药留空 {sum(1 for x in ev13 if x["track"]=="美股标普医药" and x["reference"].get("actual_ret_1d") is None)} 条待 8/14')
print('8/13 track 分布:', dict(defaultdict(int, {})), dict(Counter()) if False else '')

from collections import Counter
print('8/13 track 分布:', dict(Counter(x['track'] for x in ev13)))

# ---------- 3. 全量样本统计 ----------
all_ev = []
for f in sorted(glob.glob(os.path.join(EV, 'events-*.json'))):
    all_ev += json.load(open(f, encoding='utf-8'))
print('事件库全量累计:', len(all_ev), '条')
stats = defaultdict(lambda: {'n': 0, 'rets': [], 'sp': {'n': 0, 'rets': []}, 'sn': {'n': 0, 'rets': []}})
for x in all_ev:
    r = x.get('reference') or {}
    if r.get('actual_ret_1d') is None:
        continue
    t = x.get('track', '?'); s = stats[t]
    s['n'] += 1; s['rets'].append(r['actual_ret_1d'])
    if x.get('strength', 0) >= 60 and x.get('sentiment') == '正面':
        s['sp']['n'] += 1; s['sp']['rets'].append(r['actual_ret_1d'])
    if x.get('strength', 0) >= 60 and x.get('sentiment') == '负面':
        s['sn']['n'] += 1; s['sn']['rets'].append(r['actual_ret_1d'])
print('\n赛道 1 日样本统计（含 8/13）:')
for t, s in sorted(stats.items()):
    def avg(lst): return round(sum(lst)/len(lst), 2) if lst else None
    print(f"  {t}: n={s['n']} 均值={avg(s['rets'])} | 强正面 n={s['sp']['n']} 均值={avg(s['sp']['rets'])} | 强负面 n={s['sn']['n']} 均值={avg(s['sn']['rets'])}")
