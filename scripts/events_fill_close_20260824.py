# -*- coding: utf-8 -*-
"""盘后档 2026-08-24：①回填 8/23 周末 14 条（首个交易日 8/24 收盘）②回填 8/24 当日 21 条
③追加盘后 8 条事件(id 022-029) ④美股标普医药留空待 8/25 ⑤全库完整性扫描+样本统计"""
import json, os, glob
from collections import defaultdict

BASE = '/Users/jieyang/Documents/WealthHub'
EV = os.path.join(BASE, 'data/processed/events')
TODAY = '2026-08-24'

# ---------- 8/24 各赛道实际收盘走势（用于回填） ----------
track_ret = {
    'A股医药': -3.02,        # 医疗ETF -2.87% / 医药ETF广发 -3.17% 均值（医药生物板块 -3.24%、CRO -3.91%、创新药 -3.11%、药明 -4.31%）
    '大消费': 0.34,          # 中证消费 12,418.76 +0.34%（消费ETF添富 +0.15%、茅台 +2.50% 收1,304.66 站上1,300）
    '恒生科技': -3.61,       # HSTECH 4,594.04 -3.61% 跌破4,600（恒指 25,517.33 -1.89%；阿里 -8.54% 配售抽血；南向净买115亿）
    '宏观': -0.59,           # 上证指数 3,882.01 -0.59%（创业板 -3.21%、成交20,214亿放量）
    '其他/宽基': -1.86,      # 广联达 -1.22% / 通威 -2.49% 平均
    # 美股标普医药留空（8/24 美股未收盘，待 8/25 盘前用 XLV/IYH 回填）
}
def get_ret1d(e):
    v = e.get('actual_ret_1d')
    if v is None:
        v = e.get('reference', {}).get('actual_ret_1d')
    return v
def set_ret1d(e, v, ref_text):
    r = e.setdefault('reference', {})
    r['actual_ret_1d'] = v
    r['actual_date'] = TODAY
    r['ret_1d_ref'] = ref_text

# ---------- 1. 回填 8/23 周末 14 条（首个交易日 8/24 收盘；美股标普医药 2 条留空待 8/25） ----------
ev23_path = os.path.join(EV, 'events-2026-08-23.json')
ev23 = json.load(open(ev23_path, encoding='utf-8'))
fix23 = 0
for x in ev23:
    if get_ret1d(x) is not None:
        continue
    t = x.get('track')
    if t in track_ret:
        set_ret1d(x, track_ret[t], '8/24收盘(周末事件首个交易日)')
        fix23 += 1
json.dump(ev23, open(ev23_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
left23 = [x for x in ev23 if get_ret1d(x) is None]
print(f'8/23 周末回填 {fix23} 条；留空 {len(left23)} 条（美股标普医药待 8/25）')
for x in left23:
    print(f'  留空: {x["id"]} [{x["track"]}] {x["title"][:40]}')

# ---------- 2. 回填 8/24 当日 21 条 ----------
ev24_path = os.path.join(EV, 'events-2026-08-24.json')
ev24 = json.load(open(ev24_path, encoding='utf-8'))
fix24 = 0
for x in ev24:
    if get_ret1d(x) is not None:
        continue
    t = x.get('track')
    if t in track_ret:
        set_ret1d(x, track_ret[t], '赛道指数/ETF收盘')
        fix24 += 1
json.dump(ev24, open(ev24_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
left24 = [x for x in ev24 if get_ret1d(x) is None]
print(f'8/24 当日回填 {fix24} 条；留空 {len(left24)} 条（美股标普医药待 8/25）')

# ---------- 3. 追加盘后 8 条事件（id 022-029） ----------
sent = json.load(open(os.path.join(BASE, 'data/processed/news/sentiment-2026-08-24.json'), encoding='utf-8'))
sent_by_title = {s['title']: s for s in sent}
existing_titles = set(e['title'] for e in ev24)

# 历史样本统计（供 reference）
all_events = []
for p in sorted(glob.glob(os.path.join(EV, 'events-*.json'))):
    if '2026-08-24' in p:
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

TRACK_MAP = {
    'A股收评（8/24）': '宏观',
    '港股收评（8/24）': '恒生科技',
    '创新药哑火原因拆解（8/24）': 'A股医药',
    'CRO概念8/24下跌': 'A股医药',
    '贵州茅台8/24收1,304.66': '大消费',
    '吃喝板块8/24逆市走高': '大消费',
    '拼多多Q2财报落地（8/24': '恒生科技',
    '美股盘前（8/24）': '宏观',
}
def get_track(title):
    for k, v in TRACK_MAP.items():
        if title.startswith(k):
            return v
    return '宏观'

new_events = []
news_all = json.load(open(os.path.join(BASE, 'data/processed/news/news-2026-08-24.json'), encoding='utf-8'))
for n in news_all:
    if n['title'] in existing_titles:
        continue
    s = sent_by_title.get(n['title'], {})
    t = get_track(n['title'])
    st = track_stats.get(t, {})
    seq = len(ev24) + len(new_events) + 1
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
            'actual_ret_1d': track_ret.get(t),
            'actual_date': TODAY if track_ret.get(t) is not None else None,
            'ret_1d_ref': '赛道指数/ETF收盘' if track_ret.get(t) is not None else None,
            'track_stats': {
                'track_n': st.get('n'), 'track_avg': st.get('avg'),
                'track_worst': st.get('worst'), 'track_best': st.get('best'),
                'track_pos_ratio': st.get('pos'),
            }
        }
    })

combined = ev24 + new_events
json.dump(combined, open(ev24_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(f'\n追加盘后事件 {len(new_events)} 条，events-2026-08-24.json 共 {len(combined)} 条')
for e in new_events:
    print(f"  {e['id']} [{e['track']}] {e['sentiment']}{e['score']}/{e['strength']} ret1d={e['reference']['actual_ret_1d']} | {e['title'][:40]}")

# ---------- 4. 全库完整性扫描 + 样本统计 + 方向验证 ----------
all_ev = []
for f in sorted(glob.glob(os.path.join(EV, 'events-*.json'))):
    all_ev += json.load(open(f, encoding='utf-8'))
nulls = [x for x in all_ev if get_ret1d(x) is None]
print(f'\n事件库全量累计: {len(all_ev)} 条；actual_ret_1d 留空: {len(nulls)} 条')
for x in nulls:
    print(f'  留空: {x.get("id")} [{x.get("track")}] {x.get("title","")[:50]}')

final = defaultdict(lambda: {'n': 0, 'rets': [], 'sp': {'n': 0, 'rets': []}, 'sn': {'n': 0, 'rets': []}, 'dir_ok': 0, 'dir_n': 0})
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
    # 方向验证（sentiment 口径）
    senti = x.get('sentiment')
    if senti in ('正面', '负面'):
        s['dir_n'] += 1
        if (senti == '正面' and float(v) > 0) or (senti == '负面' and float(v) < 0):
            s['dir_ok'] += 1
print('\n赛道 1 日样本统计（含 8/24 回填）：')
tot_n = tot_ok = tot_sample = 0
for t, s in sorted(final.items()):
    def avg(lst): return round(sum(lst)/len(lst), 2) if lst else None
    print(f"  {t}: n={s['n']} 均值={avg(s['rets'])} | 强正面 n={s['sp']['n']} 均值={avg(s['sp']['rets'])} | 强负面 n={s['sn']['n']} 均值={avg(s['sn']['rets'])} | 方向 {s['dir_ok']}/{s['dir_n']}")
    tot_n += s['dir_n']; tot_ok += s['dir_ok']; tot_sample += s['n']
print(f'\n方向验证全局: {tot_ok}/{tot_n}（{round(tot_ok/tot_n*100) if tot_n else 0}%）；1 日样本总量 {tot_sample}')
