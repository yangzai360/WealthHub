# -*- coding: utf-8 -*-
"""盘后档 2026-08-21：①回填 8/21 当日 19 条 ②追加盘后新增 8 条事件(id 020-027)
③美股标普医药留空待 8/24（XLV 8/21 收盘）④样本统计"""
import json, os, glob
from collections import defaultdict

BASE = '/Users/jieyang/Documents/WealthHub'
EV = os.path.join(BASE, 'data/processed/events')
TODAY = '2026-08-21'

# ---------- 8/21 各赛道实际收盘走势（用于回填） ----------
track_ret = {
    'A股医药': -3.14,        # 医疗ETF -2.79% / 医药ETF广发 -3.49% 均值（医药生物板块 -3.48%、创新药 -3.78%、主力净流出86.86亿）
    '大消费': -1.60,          # 中证消费 12,376.78 -1.60%（消费ETF添富 -1.49%、茅台 -1.45% 收1,272.83）
    '恒生科技': 1.40,         # HSTECH 4,766.16 +1.40%（恒指 26,009.46 +1.21% 5连升；南向净卖出76亿）
    '宏观': 0.04,             # 上证指数 3,905.20 +0.04%（成交1.89万亿缩量约2,000亿）
    '其他/宽基': -0.11,       # 广联达 -1.10% / 通威 +0.89% 平均
    # 美股标普医药留空（8/21 美股未收盘，待 8/24 盘前用 XLV/IYH 回填）
}
def get_ret1d(e):
    v = e.get('actual_ret_1d')
    if v is None:
        v = e.get('reference', {}).get('actual_ret_1d')
    return v

# ---------- 1. 回填 8/21 当日 19 条 ----------
ev21_path = os.path.join(EV, 'events-2026-08-21.json')
ev21 = json.load(open(ev21_path, encoding='utf-8'))
fix21 = 0
for x in ev21:
    r = x.get('reference') or {}
    if r.get('actual_ret_1d') is not None:
        continue
    if x.get('track') in track_ret:
        r['actual_ret_1d'] = track_ret[x['track']]
        r['actual_date'] = TODAY
        r['ret_1d_ref'] = '赛道指数/ETF收盘'
        fix21 += 1
json.dump(ev21, open(ev21_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(f'8/21 当日回填 {fix21} 条；美股标普医药留空 {sum(1 for x in ev21 if x["track"]=="美股标普医药" and get_ret1d(x) is None)} 条待 8/24')

# ---------- 2. 追加盘后新增 8 条事件（id 020-027） ----------
sent = json.load(open(os.path.join(BASE, 'data/processed/news/sentiment-2026-08-21.json'), encoding='utf-8'))
sent_by_title = {s['title']: s for s in sent}
existing_titles = set(e['title'] for e in ev21)

TRACK_MAP = {
    'A股收评（8/21）': '宏观',
    '港股收评（8/21）': '恒生科技',
    '医药板块收盘大幅回调（8/21）': 'A股医药',
    '贵州茅台业绩会（8/21': '大消费',
    '8/21白酒批价企稳分化': '大消费',
    '现货黄金突破4,550美元': '宏观',
    '南向资金8/21净卖出': '恒生科技',
    '华西医药深度报告': 'A股医药',
}
def get_track(title):
    for k, v in TRACK_MAP.items():
        if title.startswith(k):
            return v
    return '宏观'

# 历史样本统计（供 reference）
all_events = []
for p in sorted(glob.glob(os.path.join(EV, 'events-*.json'))):
    if '2026-08-21' in p:
        continue
    all_events += json.load(open(p, encoding='utf-8'))
stats = defaultdict(lambda: {'n': 0, 'rets': [], 'pos': 0})
for e in all_events:
    v = get_ret1d(e)
    if v is None:
        continue
    t = e.get('track', '?')
    stats[t]['n'] += 1
    stats[t]['rets'].append(float(v))
    if float(v) > 0:
        stats[t]['pos'] += 1
track_stats = {}
for t, s in stats.items():
    track_stats[t] = {
        'n': s['n'],
        'avg': round(sum(s['rets'])/len(s['rets']), 2) if s['rets'] else None,
        'worst': round(min(s['rets']), 2) if s['rets'] else None,
        'best': round(max(s['rets']), 2) if s['rets'] else None,
        'pos': round(s['pos']/s['n'], 2) if s['n'] else None,
    }

new_events = []
news_all = json.load(open(os.path.join(BASE, 'data/processed/news/news-2026-08-21.json'), encoding='utf-8'))
for n in news_all:
    if n['title'] in existing_titles:
        continue
    s = sent_by_title.get(n['title'], {})
    t = get_track(n['title'])
    st = track_stats.get(t, {})
    seq = len(ev21) + len(new_events) + 1
    new_events.append({
        'id': f'N{TODAY.replace("-", "")}-{seq:03d}',
        'date': TODAY,
        'track': t,
        'category': n.get('category', '行业事件类'),
        'title': n['title'],
        'summary': n.get('summary', ''),
        'source': n.get('source', 'WebSearch'),
        'source_url': n.get('source_url', ''),
        'sentiment': s.get('sentiment', '中性'),
        'score': s.get('score', 50),
        'strength': s.get('strength', s.get('score', 50)),
        'direction': s.get('direction', '中性'),
        'volatility': s.get('volatility', '中'),
        'reason': s.get('reason', ''),
        'reference': {
            'ret_3d': None, 'ret_5d': None, 'ret_10d': None,
            'max_vol': None,
            'confidence': min(90, 40 + st.get('n', 0) * 2),
            'actual_ret_1d': track_ret.get(t),  # 盘后新事件直接用当日赛道收盘回填（除美股标普医药留空）
            'actual_date': TODAY if track_ret.get(t) is not None else None,
            'ret_1d_ref': {
                'track_n': st.get('n'), 'track_avg': st.get('avg'),
                'track_worst': st.get('worst'), 'track_best': st.get('best'),
                'track_pos_ratio': st.get('pos'),
            }
        }
    })

combined = ev21 + new_events
json.dump(combined, open(ev21_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(f'\n追加盘后事件 {len(new_events)} 条，events-2026-08-21.json 共 {len(combined)} 条')
for e in new_events:
    print(f"  {e['id']} [{e['track']}] {e['sentiment']}{e['score']}/{e['strength']} ret1d={e['reference']['actual_ret_1d']} | {e['title'][:40]}")

# ---------- 3. 全量样本统计 ----------
all_ev = []
for f in sorted(glob.glob(os.path.join(EV, 'events-*.json'))):
    all_ev += json.load(open(f, encoding='utf-8'))
print('\n事件库全量累计:', len(all_ev), '条')
final = defaultdict(lambda: {'n': 0, 'rets': [], 'sp': {'n': 0, 'rets': []}, 'sn': {'n': 0, 'rets': []}})
for x in all_ev:
    v = get_ret1d(x)
    if v is None:
        continue
    t = x.get('track', '?'); s = final[t]
    s['n'] += 1; s['rets'].append(float(v))
    strength = x.get('strength') or x.get('score') or 0
    if strength >= 60 and x.get('sentiment') == '正面':
        s['sp']['n'] += 1; s['sp']['rets'].append(float(v))
    if strength >= 60 and x.get('sentiment') == '负面':
        s['sn']['n'] += 1; s['sn']['rets'].append(float(v))
print('\n赛道 1 日样本统计（含 8/21 回填）：')
for t, s in sorted(final.items()):
    def avg(lst): return round(sum(lst)/len(lst), 2) if lst else None
    print(f"  {t}: n={s['n']} 均值={avg(s['rets'])} | 强正面 n={s['sp']['n']} 均值={avg(s['sp']['rets'])} | 强负面 n={s['sn']['n']} 均值={avg(s['sn']['rets'])}")
