# -*- coding: utf-8 -*-
"""盘后档 2026-09-02：①回填 9/2 当日 26 条
②追加盘后 8 条事件(id 027-034)并回填 ③全库完整性扫描
④1日样本统计+方向验证 ⑤3/5日窗口统计更新"""
import json, os, glob, csv
from collections import defaultdict

BASE = '/Users/jieyang/Documents/WealthHub'
EV = os.path.join(BASE, 'data/processed/events')
TODAY = '2026-09-02'

# ---------- 9/2 各赛道实际收盘走势（用于回填） ----------
track_ret = {
    'A股医药': -0.83,          # ETF均值（医疗ETF -0.88% / 医药ETF广发 -0.77%）；医药生物 -0.91% 但CRO净流入11.24亿
    '大消费': -0.85,           # 中证消费 12,516.21 -0.85% 守住12,500（白酒龙头温和回调、飞天批价+5续涨）
    '恒生科技': -0.74,         # HSTECH 4,517.16 -0.74% 收复4,500（盘中最低4,460；恒指 -0.07% 25,311.21）
    '宏观': -0.97,             # 上证指数 3,941.39 -0.97%（创业板 -2.39%、深成指 -1.88%、成交18,203亿缩量2,319亿）
    '其他/宽基': -3.24,        # 广联达 -2.58% / 通威 -3.89% 平均（传媒ETF -2.47%、证券ETF -2.07%、100红利 -1.43%）
    # 美股标普医药 9/2 当日事件（N20260902-012/013）留空待 9/3 用 XLV/IYH 9/2 收盘回填
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

# ---------- 1. 回填 9/2 当日 26 条 ----------
ev_path = os.path.join(EV, f'events-{TODAY}.json')
ev = json.load(open(ev_path, encoding='utf-8'))
fix = 0
for x in ev:
    if get_ret1d(x) is not None:
        continue
    t = x.get('track')
    if t in track_ret:
        set_ret1d(x, track_ret[t], '赛道指数/ETF收盘')
        fix += 1
json.dump(ev, open(ev_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
left = [x for x in ev if get_ret1d(x) is None]
print(f'9/2 当日回填 {fix} 条；留空 {len(left)} 条')
for x in left:
    print(f'  留空: {x["id"]} [{x["track"]}] {x["title"][:40]}')

# ---------- 2. 追加盘后 8 条事件（id 027-034）+ 回填 ----------
sent = json.load(open(os.path.join(BASE, 'data/processed/news/sentiment-2026-09-02.json'), encoding='utf-8'))
sent_by_title = {s['title']: s for s in sent}
existing_titles = set(e['title'] for e in ev)

# 历史样本统计（供 reference，不含 9/2）
all_events = []
for p in sorted(glob.glob(os.path.join(EV, 'events-*.json'))):
    if TODAY in p:
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
news_all = json.load(open(os.path.join(BASE, 'data/processed/news/news-2026-09-02.json'), encoding='utf-8'))
for n in news_all:
    if n['title'] in existing_titles:
        continue
    s = sent_by_title.get(n['title'], {})
    t = n.get('track') or '宏观'
    st = track_stats.get(t, {})
    seq = len(ev) + len(new_events) + 1
    ret1d = track_ret.get(t)
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
        'reason': s.get('comment', ''),
        'reference': {
            'ret_3d': None, 'ret_5d': None, 'ret_10d': None,
            'max_vol': None,
            'confidence': min(90, 40 + st.get('n', 0) * 2),
            'actual_ret_1d': ret1d,
            'actual_date': TODAY if ret1d is not None else None,
            'ret_1d_ref': '赛道指数/ETF收盘' if ret1d is not None else None,
            'track_stats': {
                'track_n': st.get('n'), 'track_avg': st.get('avg'),
                'track_worst': st.get('worst'), 'track_best': st.get('best'),
                'track_pos_ratio': st.get('pos'),
            }
        }
    })

combined = ev + new_events
json.dump(combined, open(ev_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(f'\n追加盘后事件 {len(new_events)} 条，events-2026-09-02.json 共 {len(combined)} 条')
for e in new_events:
    print(f"  {e['id']} [{e['track']}] {e['sentiment']}{e['score']}/{e['strength']} ret1d={e['reference']['actual_ret_1d']} | {e['title'][:40]}")

# ---------- 3. 全库完整性扫描 ----------
all_ev = []
for f in sorted(glob.glob(os.path.join(EV, 'events-*.json'))):
    all_ev += json.load(open(f, encoding='utf-8'))
nulls = [x for x in all_ev if get_ret1d(x) is None]
print(f'\n事件库全量累计: {len(all_ev)} 条；actual_ret_1d 留空: {len(nulls)} 条')
for x in nulls:
    print(f'  留空: {x.get("id")} [{x.get("track")}] {x.get("title","")[:50]}')

# ---------- 4. 1 日样本统计 + 方向验证（sentiment 口径） ----------
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
    senti = x.get('sentiment')
    if senti in ('正面', '负面'):
        s['dir_n'] += 1
        if (senti == '正面' and float(v) > 0) or (senti == '负面' and float(v) < 0):
            s['dir_ok'] += 1
print('\n赛道 1 日样本统计（含 9/2 回填）：')
tot_n = tot_ok = tot_sample = 0
for t, s in sorted(final.items()):
    def avg(lst): return round(sum(lst)/len(lst), 2) if lst else None
    print(f"  {t}: n={s['n']} 均值={avg(s['rets'])} | 强正面 n={s['sp']['n']} 均值={avg(s['sp']['rets'])} | 强负面 n={s['sn']['n']} 均值={avg(s['sn']['rets'])} | 方向 {s['dir_ok']}/{s['dir_n']}")
    tot_n += s['dir_n']; tot_ok += s['dir_ok']; tot_sample += s['n']
print(f'\n方向验证全局: {tot_ok}/{tot_n}（{round(tot_ok/tot_n*100) if tot_n else 0}%）；1 日样本总量 {tot_sample}')

# ---------- 5. 3/5 日窗口统计 ----------
print('\n--- 3/5 日窗口统计（截至 9/2 收盘数据） ---')
idx_series = defaultdict(dict)
with open(os.path.join(BASE, 'data/processed/history/indices.csv'), encoding='utf-8-sig') as f:
    for row in csv.reader(f):
        if len(row) >= 7 and row[0] in ('index', 'us_index'):
            d, code, pct = row[1], row[3], row[5]
            try:
                idx_series[code][d] = float(pct)
            except Exception:
                pass
track_idx = {
    '宏观': '000001', 'A股医药': '399006', '大消费': '000932',
    '恒生科技': 'HSTECH', '美股标普医药': 'XLV', '其他/宽基': '000001',
}
ev_dated = []
for x in all_ev:
    v = get_ret1d(x)
    if v is None:
        continue
    d = x.get('date')
    if not d:
        continue
    ev_dated.append((d, x))

def calc_window(ev_dated, idx_series, track_idx, win_days, label):
    ret_stats = defaultdict(lambda: {'n': 0, 'rets': []})
    for d, x in ev_dated:
        t = x.get('track', '?')
        code = track_idx.get(t)
        if not code:
            continue
        dates = sorted(idx_series.get(code, {}).keys())
        if d not in dates:
            continue
        idx_pos = dates.index(d)
        if idx_pos + win_days >= len(dates):
            continue
        cum = 1.0
        for i in range(idx_pos + 1, idx_pos + win_days + 1):
            if i >= len(dates):
                break
            cum *= (1 + idx_series[code][dates[i]] / 100.0)
        ret = (cum - 1) * 100
        ret_stats[t]['n'] += 1
        ret_stats[t]['rets'].append(ret)
    print(f'--- {label} ---')
    for t, s in ret_stats.items():
        if not s['rets']:
            continue
        avg = sum(s['rets']) / len(s['rets'])
        print(f"  {t}: n={s['n']} 均值={avg:.2f}% 最差={min(s['rets']):.2f}% 最好={max(s['rets']):.2f}%")

calc_window(ev_dated, idx_series, track_idx, 3, '3 日窗口（事件日+3 个交易日）')
calc_window(ev_dated, idx_series, track_idx, 5, '5 日窗口（事件日+5 个交易日）')

print('\nDONE 事件回填+统计完成')
