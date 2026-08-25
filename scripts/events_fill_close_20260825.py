# -*- coding: utf-8 -*-
"""盘后档 2026-08-25：①回填 8/25 当日 23 条（美股标普医药留空待 8/26）
②追加盘后 8 条事件(id 024-031)并二次回填 ③全库完整性扫描 ④1日样本统计+方向验证 ⑤3日窗口首次统计"""
import json, os, glob
from collections import defaultdict

BASE = '/Users/jieyang/Documents/WealthHub'
EV = os.path.join(BASE, 'data/processed/events')
TODAY = '2026-08-25'

# ---------- 8/25 各赛道实际收盘走势（用于回填） ----------
track_ret = {
    'A股医药': 2.04,        # ETF均值（医疗ETF +2.36% / 医药ETF广发 +1.71%）；医疗服务 +3.40%/创新药 +2.38%/生物医药 +2.53%、凯莱英涨停、药明 +3.31%
    '大消费': 0.59,         # 中证消费 12,492.24 +0.59% 站稳12,400（茅台 -0.05% 收1,304.00、泸州老窖 -0.91%）
    '恒生科技': -0.12,      # HSTECH 4,588.54 -0.12%（恒指 25,511.10 -0.02%；药明系领涨、南向净卖出66亿）
    '宏观': 0.19,           # 上证指数 3,889.45 +0.19%（创业板 -1.00%、成交18,445亿缩量1,769亿）
    '其他/宽基': -2.09,     # 广联达 -3.26% / 通威 -0.91% 平均
    # 美股标普医药留空（8/25 美股未收盘，待 8/26 用 XLV/IYH 回填）
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

# ---------- 1. 回填 8/25 当日 23 条（盘前 15 + 盘中 8） ----------
ev25_path = os.path.join(EV, 'events-2026-08-25.json')
ev25 = json.load(open(ev25_path, encoding='utf-8'))
fix25 = 0
for x in ev25:
    if get_ret1d(x) is not None:
        continue
    t = x.get('track')
    if t in track_ret:
        set_ret1d(x, track_ret[t], '赛道指数/ETF收盘')
        fix25 += 1
json.dump(ev25, open(ev25_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
left25 = [x for x in ev25 if get_ret1d(x) is None]
print(f'8/25 当日回填 {fix25} 条；留空 {len(left25)} 条（美股标普医药待 8/26）')
for x in left25:
    print(f'  留空: {x["id"]} [{x["track"]}] {x["title"][:40]}')

# ---------- 2. 追加盘后 8 条事件（id 024-031）+ 二次回填 ----------
sent = json.load(open(os.path.join(BASE, 'data/processed/news/sentiment-2026-08-25.json'), encoding='utf-8'))
sent_by_title = {s['title']: s for s in sent}
existing_titles = set(e['title'] for e in ev25)

# 历史样本统计（供 reference，不含 8/25）
all_events = []
for p in sorted(glob.glob(os.path.join(EV, 'events-*.json'))):
    if '2026-08-25' in p:
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
    'A股收评（8/25）': '宏观',
    '港股收评（8/25）': '恒生科技',
    '医药板块8/25逆市领涨': 'A股医药',
    '泸州老窖2026年半年报爆雷': '大消费',
    '消费资金\'高低切\'迹象': '大消费',
    '白酒批价周报（8/19-8/25）': '大消费',
    '英伟达Groq 3 LPX全面投产': '宏观',
    '美股盘前（8/25）': '宏观',
}
def get_track(title):
    for k, v in TRACK_MAP.items():
        if title.startswith(k):
            return v
    return '宏观'

new_events = []
news_all = json.load(open(os.path.join(BASE, 'data/processed/news/news-2026-08-25.json'), encoding='utf-8'))
for n in news_all:
    if n['title'] in existing_titles:
        continue
    s = sent_by_title.get(n['title'], {})
    t = get_track(n['title'])
    st = track_stats.get(t, {})
    seq = len(ev25) + len(new_events) + 1
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
        'reason': s.get('reason', ''),
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

combined = ev25 + new_events
json.dump(combined, open(ev25_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(f'\n追加盘后事件 {len(new_events)} 条，events-2026-08-25.json 共 {len(combined)} 条')
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

# ---------- 4. 1 日样本统计 + 方向验证 ----------
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
print('\n赛道 1 日样本统计（含 8/25 回填）：')
tot_n = tot_ok = tot_sample = 0
for t, s in sorted(final.items()):
    def avg(lst): return round(sum(lst)/len(lst), 2) if lst else None
    print(f"  {t}: n={s['n']} 均值={avg(s['rets'])} | 强正面 n={s['sp']['n']} 均值={avg(s['sp']['rets'])} | 强负面 n={s['sn']['n']} 均值={avg(s['sn']['rets'])} | 方向 {s['dir_ok']}/{s['dir_n']}")
    tot_n += s['dir_n']; tot_ok += s['dir_ok']; tot_sample += s['n']
print(f'\n方向验证全局: {tot_ok}/{tot_n}（{round(tot_ok/tot_n*100) if tot_n else 0}%）；1 日样本总量 {tot_sample}')

# ---------- 5. 3 日窗口首次统计（事件 date+1 起连续 3 个交易日的赛道指数累计收益，部分样本可用） ----------
print('\n--- 3 日窗口统计（数据就绪部分，8/6-8/19 事件） ---')
# 读 indices.csv 建赛道指数日线（收盘口径）
idx_series = defaultdict(dict)  # {code: {date: pct}}
with open(os.path.join(BASE, 'data/processed/history/indices.csv'), encoding='utf-8-sig') as f:
    import csv
    for row in csv.reader(f):
        if len(row) >= 7 and row[0] == 'index':
            d, code, pct = row[1], row[3], row[5]
            try:
                idx_series[code][d] = float(pct)
            except Exception:
                pass
# 赛道 → 指数代码（收盘口径）
track_idx = {
    '宏观': '000001',          # 上证指数
    'A股医药': '399006',       # 创业板指（近似，医药ETF日线暂无独立存档；用创业板近似并标注）
    '大消费': '000932',        # 中证消费
    '恒生科技': 'HSTECH',      # 恒生科技
    '美股标普医药': 'XLV',     # XLV（us_index）
    '其他/宽基': '000001',
}
# us_index 类型也读入
with open(os.path.join(BASE, 'data/processed/history/indices.csv'), encoding='utf-8-sig') as f:
    for row in csv.reader(f):
        if len(row) >= 7 and row[0] == 'us_index':
            d, code, pct = row[1], row[3], row[5]
            try:
                idx_series[code][d] = float(pct)
            except Exception:
                pass

trade_dates = sorted(idx_series.get('000001', {}).keys())
print(f'交易日数量（沪指）: {len(trade_dates)}，区间 {trade_dates[0] if trade_dates else "?"} ~ {trade_dates[-1] if trade_dates else "?"}')

# 对每条事件计算 ret_3d（事件日之后 3 个交易日的赛道累计涨幅，使用交易日序列）
ev_dated = []
for x in all_ev:
    v = get_ret1d(x)
    if v is None:
        continue
    d = x.get('date')
    if not d:
        continue
    ev_dated.append((d, x))
ret3_stats = defaultdict(lambda: {'n': 0, 'rets': []})
for d, x in ev_dated:
    t = x.get('track', '?')
    code = track_idx.get(t)
    if not code:
        continue
    dates = sorted(idx_series.get(code, {}).keys())
    if d not in dates:
        continue
    idx_pos = dates.index(d)
    if idx_pos + 3 >= len(dates):
        continue
    # 事件日收盘到其后第3个交易日的累计收益（用每日 pct 连乘近似）
    cum = 1.0
    for i in range(idx_pos + 1, idx_pos + 4):
        cum *= (1 + idx_series[code][dates[i]] / 100.0)
    ret3 = (cum - 1) * 100
    ret3_stats[t]['n'] += 1
    ret3_stats[t]['rets'].append(ret3)
for t, s in ret3_stats.items():
    avg = sum(s['rets']) / len(s['rets'])
    print(f"  {t}: 3日样本 n={s['n']} 均值={avg:.2f}% 最差={min(s['rets']):.2f}% 最好={max(s['rets']):.2f}%")

print('\nDONE 事件回填+统计完成')
