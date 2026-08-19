# -*- coding: utf-8 -*-
"""盘后档 2026-08-19：①回填 8/18 盘后追加 7 条遗留(030-036) ②回填 8/19 当日 24 条
③追加盘后新增 7 条事件(id 025-031) ④美股标普医药留空待 8/20 ⑤样本统计"""
import json, os, glob
from collections import defaultdict

BASE = '/Users/jieyang/Documents/WealthHub'
EV = os.path.join(BASE, 'data/processed/events')
TODAY = '2026-08-19'

# ---------- 8/19 各赛道实际收盘走势（用于回填） ----------
track_ret = {
    'A股医药': -2.09,       # 医疗ETF -2.55% / 医药ETF广发 -1.62% 均值（药明 -1.90% 主力净卖出6.8亿）
    '大消费': -1.08,         # 中证消费 12,489.98 -1.08%（茅台逆势+0.76%收1307.88、白酒Ⅱ-0.17%抗跌但指数失守12,500）
    '恒生科技': -1.21,       # HSTECH 4,682.05 -1.21%（小米+5% vs 百度-11%、南向净卖出106.21亿）
    '宏观': -2.40,            # 上证指数 3,894.42 -2.40%（年内第四大单日跌幅、创业板-6.26%）
    '其他/宽基': -2.99,      # 广联达 -2.21% / 通威 -3.76% 平均（沪深300 -2.90%）
    # 美股标普医药留空（8/19 美股未收盘，待 8/20 盘前用 XLV/IYH 回填）
}
def get_ret1d(e):
    v = e.get('actual_ret_1d')
    if v is None:
        v = e.get('reference', {}).get('actual_ret_1d')
    return v

# ---------- 1. 回填 8/18 盘后追加 7 条遗留（030-036，用 8/18 实际收盘） ----------
ev18_path = os.path.join(EV, 'events-2026-08-18.json')
ev18 = json.load(open(ev18_path, encoding='utf-8'))
ret18 = {
    'N20260818-030': ('宏观', 0.19),      # A股收评 8/18 上证 +0.19%
    'N20260818-031': ('恒生科技', -0.90), # 港股收评 8/18 HSTECH -0.90%
    'N20260818-032': ('大消费', 0.89),    # 茅台尾盘翻红 中证消费 +0.89%
    'N20260818-033': ('恒生科技', -0.90), # 小米财报 HSTECH -0.90%
    'N20260818-034': ('A股医药', -0.22),  # 港股CXO走强 医药ETF均值 -0.22%
    'N20260818-035': ('大消费', 0.89),    # 生猪产能去化 中证消费 +0.89%
    'N20260818-036': ('宏观', 0.19),      # 伊朗 上证 +0.19%
}
fix18 = 0
for x in ev18:
    r = x.get('reference') or {}
    if r.get('actual_ret_1d') is not None:
        continue
    if x['id'] in ret18:
        r['actual_ret_1d'] = ret18[x['id']][1]
        r['actual_date'] = '2026-08-18'
        r['ret_1d_ref'] = '8/18收盘(盘后追加事件补回填)'
        fix18 += 1
json.dump(ev18, open(ev18_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(f'8/18 盘后追加遗留回填 {fix18} 条')
still18 = [x['id'] for x in ev18 if get_ret1d(x) is None]
print(f'  8/18 仍留空: {still18}')

# ---------- 2. 回填 8/19 当日 24 条 ----------
ev19_path = os.path.join(EV, 'events-2026-08-19.json')
ev19 = json.load(open(ev19_path, encoding='utf-8'))
fix19 = 0
for x in ev19:
    r = x.get('reference') or {}
    if r.get('actual_ret_1d') is not None:
        continue
    if x.get('track') in track_ret:
        r['actual_ret_1d'] = track_ret[x['track']]
        r['actual_date'] = TODAY
        r['ret_1d_ref'] = '赛道指数/ETF收盘'
        fix19 += 1
json.dump(ev19, open(ev19_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(f'8/19 当日回填 {fix19} 条；美股标普医药留空 {sum(1 for x in ev19 if x["track"]=="美股标普医药" and get_ret1d(x) is None)} 条待 8/20')

# ---------- 3. 追加盘后新增 7 条事件（id 025-031） ----------
sent = json.load(open(os.path.join(BASE, 'data/processed/news/sentiment-2026-08-19.json'), encoding='utf-8'))
sent_by_title = {s['title']: s for s in sent}
existing_titles = set(e['title'] for e in ev19)

TRACK_MAP = {
    'A股收评（8/19）': '宏观',
    '港股收评（8/19，证券时报）': '恒生科技',
    '南向资金8/19净卖出106.21亿': '恒生科技',
    '创新药避险失灵+医药生物板块大跌': 'A股医药',
    '茅台逆势+0.76%收1,307.88': '大消费',
    '港股创新药中报预喜+复星医药': 'A股医药',
    '美联储7月会议纪要今夜': '宏观',
}
def get_track(title):
    for k, v in TRACK_MAP.items():
        if title.startswith(k):
            return v
    return '宏观'

# 历史样本统计（供 reference）
all_events = []
for p in sorted(glob.glob(os.path.join(EV, 'events-*.json'))):
    if '2026-08-19' in p:
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
news_all = json.load(open(os.path.join(BASE, 'data/processed/news/news-2026-08-19.json'), encoding='utf-8'))
for n in news_all:
    if n['title'] in existing_titles:
        continue
    s = sent_by_title.get(n['title'], {})
    t = get_track(n['title'])
    st = track_stats.get(t, {})
    seq = len(ev19) + len(new_events) + 1
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
            'actual_ret_1d': None,
            'actual_date': None,
            'ret_1d_ref': {
                'track_n': st.get('n'), 'track_avg': st.get('avg'),
                'track_worst': st.get('worst'), 'track_best': st.get('best'),
                'track_pos_ratio': st.get('pos'),
            }
        }
    })

combined = ev19 + new_events
json.dump(combined, open(ev19_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(f'\n追加盘后事件 {len(new_events)} 条，events-2026-08-19.json 共 {len(combined)} 条')
for e in new_events:
    print(f"  {e['id']} [{e['track']}] {e['sentiment']}{e['score']}/{e['strength']} | {e['title'][:40]}")

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
print('\n赛道 1 日样本统计（含 8/18 回填 + 8/19）：')
for t, s in sorted(final.items()):
    def avg(lst): return round(sum(lst)/len(lst), 2) if lst else None
    print(f"  {t}: n={s['n']} 均值={avg(s['rets'])} | 强正面 n={s['sp']['n']} 均值={avg(s['sp']['rets'])} | 强负面 n={s['sn']['n']} 均值={avg(s['sn']['rets'])}")
