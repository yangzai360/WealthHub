# -*- coding: utf-8 -*-
"""盘后档 2026-08-20：①回填 8/19 遗留 1 条(N20260819-031) ②回填 8/20 当日 21 条
③追加盘后新增 8 条事件(id 022-029) ④美股标普医药留空待 8/21 ⑤样本统计"""
import json, os, glob
from collections import defaultdict

BASE = '/Users/jieyang/Documents/WealthHub'
EV = os.path.join(BASE, 'data/processed/events')
TODAY = '2026-08-20'

# ---------- 8/20 各赛道实际收盘走势（用于回填） ----------
track_ret = {
    'A股医药': 3.53,        # 医疗ETF +4.36% / 医药ETF广发 +2.69% 均值（医药生物板块 +3.73%、38股涨停居首）
    '大消费': 0.71,          # 中证消费 12,578.17 +0.71%（消费ETF添富 +0.75%、富国消费 +0.80%；白酒/酒类逆势下跌内部分化）
    '恒生科技': 0.39,        # HSTECH 4,700.53 +0.39%（康希诺+37%/云顶新耀+41% vs 快手-11%；南向净卖出104.12亿）
    '宏观': 0.24,            # 上证指数 3,903.72 +0.24%（成交2.09万亿缩量4,361亿、涨停83/跌停13）
    '其他/宽基': 1.44,       # 广联达 +2.71% / 通威 +0.16% 平均（沪深300约 +0.3%）
    # 美股标普医药留空（8/20 美股未收盘，待 8/21 盘前用 XLV/IYH 回填）
}
def get_ret1d(e):
    v = e.get('actual_ret_1d')
    if v is None:
        v = e.get('reference', {}).get('actual_ret_1d')
    return v

# ---------- 1. 回填 8/19 遗留 1 条（N20260819-031 美联储纪要，影响在 8/20） ----------
ev19_path = os.path.join(EV, 'events-2026-08-19.json')
ev19 = json.load(open(ev19_path, encoding='utf-8'))
ret19 = {
    'N20260819-031': ('宏观', 0.24),      # 美联储纪要影响在 8/20：上证 +0.24%
}
fix19 = 0
for x in ev19:
    r = x.get('reference') or {}
    if r.get('actual_ret_1d') is not None:
        continue
    if x['id'] in ret19:
        r['actual_ret_1d'] = ret19[x['id']][1]
        r['actual_date'] = TODAY
        r['ret_1d_ref'] = '8/20收盘(纪要影响日)'
        fix19 += 1
json.dump(ev19, open(ev19_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(f'8/19 遗留回填 {fix19} 条')
still19 = [x['id'] for x in ev19 if get_ret1d(x) is None]
print(f'  8/19 仍留空: {still19}')

# ---------- 2. 回填 8/20 当日 21 条 ----------
ev20_path = os.path.join(EV, 'events-2026-08-20.json')
ev20 = json.load(open(ev20_path, encoding='utf-8'))
fix20 = 0
for x in ev20:
    r = x.get('reference') or {}
    if r.get('actual_ret_1d') is not None:
        continue
    if x.get('track') in track_ret:
        r['actual_ret_1d'] = track_ret[x['track']]
        r['actual_date'] = TODAY
        r['ret_1d_ref'] = '赛道指数/ETF收盘'
        fix20 += 1
json.dump(ev20, open(ev20_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(f'8/20 当日回填 {fix20} 条；美股标普医药留空 {sum(1 for x in ev20 if x["track"]=="美股标普医药" and get_ret1d(x) is None)} 条待 8/21')

# ---------- 3. 追加盘后新增 8 条事件（id 022-029） ----------
sent = json.load(open(os.path.join(BASE, 'data/processed/news/sentiment-2026-08-20.json'), encoding='utf-8'))
sent_by_title = {s['title']: s for s in sent}
existing_titles = set(e['title'] for e in ev20)

TRACK_MAP = {
    'A股收评（8/20）': '宏观',
    '港股收评（8/20，新华社）': '恒生科技',
    '阿里巴巴2027财年Q1财报': '恒生科技',
    '网易2026年Q2财报': '恒生科技',
    '南向资金8/20净卖出104.12亿': '恒生科技',
    '上海六部门印发《关于优化本市房地产政策措施的通知》': '宏观',
    'Moderna盘前跌近10%': '美股标普医药',
    '现货黄金冲高回落': '宏观',
}
def get_track(title):
    for k, v in TRACK_MAP.items():
        if title.startswith(k):
            return v
    return '宏观'

# 历史样本统计（供 reference）
all_events = []
for p in sorted(glob.glob(os.path.join(EV, 'events-*.json'))):
    if '2026-08-20' in p:
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
news_all = json.load(open(os.path.join(BASE, 'data/processed/news/news-2026-08-20.json'), encoding='utf-8'))
for n in news_all:
    if n['title'] in existing_titles:
        continue
    s = sent_by_title.get(n['title'], {})
    t = get_track(n['title'])
    st = track_stats.get(t, {})
    seq = len(ev20) + len(new_events) + 1
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
            'actual_ret_1d': track_ret.get(t),  # 盘后新事件直接用当日收盘回填（除美股标普医药留空）
            'actual_date': TODAY if track_ret.get(t) is not None else None,
            'ret_1d_ref': {
                'track_n': st.get('n'), 'track_avg': st.get('avg'),
                'track_worst': st.get('worst'), 'track_best': st.get('best'),
                'track_pos_ratio': st.get('pos'),
            }
        }
    })

combined = ev20 + new_events
json.dump(combined, open(ev20_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(f'\n追加盘后事件 {len(new_events)} 条，events-2026-08-20.json 共 {len(combined)} 条')
for e in new_events:
    print(f"  {e['id']} [{e['track']}] {e['sentiment']}{e['score']}/{e['strength']} ret1d={e['reference']['actual_ret_1d']} | {e['title'][:40]}")

# ---------- 4. 全量样本统计 ----------
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
print('\n赛道 1 日样本统计（含 8/20 回填）：')
for t, s in sorted(final.items()):
    def avg(lst): return round(sum(lst)/len(lst), 2) if lst else None
    print(f"  {t}: n={s['n']} 均值={avg(s['rets'])} | 强正面 n={s['sp']['n']} 均值={avg(s['sp']['rets'])} | 强负面 n={s['sn']['n']} 均值={avg(s['sn']['rets'])}")
