# -*- coding: utf-8 -*-
"""盘后档 2026-09-03：①回填 9/3 当日 27 条
②追加盘后 7 条事件(id 028-034)并回填 ③全库完整性扫描
④1日样本统计+方向验证 ⑤3/5日窗口统计更新"""
import json, os, glob
from collections import defaultdict

BASE = '/Users/jieyang/Documents/WealthHub'
EV = os.path.join(BASE, 'data/processed/events')
TODAY = '2026-09-03'

# ---------- 9/3 各赛道实际收盘走势（用于回填） ----------
track_ret = {
    'A股医药': 0.39,           # ETF均值（医疗ETF +0.30% / 医药ETF广发 +0.47%）；医药生物板块 +0.24% 午后翻红
    '大消费': -0.30,           # 中证消费 12,478.59 -0.30% 收于12,500下方第2日（守12,400）
    '恒生科技': -1.08,         # HSTECH 4,468.48 -1.08% 收盘跌破4,500（盘中最低4,451.56破4,460；恒指 -0.39% 25,213.31）
    '宏观': 0.02,              # 上证指数 3,942.09 +0.02%（深成指 +0.10%、创业板 +0.01%、成交1.76万亿缩量323亿）
    '其他/宽基': -0.81,        # 广联达 -0.92% / 通威 -0.70% 平均（证券ETF +0.73%对冲；传媒ETF -0.48%）
    # 美股标普医药 9/3 当日事件（N20260903-0xx 3条）留空待 9/4 用 XLV/IYH 9/3 收盘回填
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

# ---------- 1. 回填 9/3 当日 27 条 ----------
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
print(f'9/3 当日回填 {fix} 条；留空 {len(left)} 条')
for x in left:
    print(f'  留空: {x["id"]} [{x["track"]}] {x["title"][:45]}')

# ---------- 2. 追加盘后 7 条事件（id 028-034）+ 回填 ----------
sent = json.load(open(os.path.join(BASE, 'data/processed/news/sentiment-2026-09-03.json'), encoding='utf-8'))
sent_by_title = {s['title']: s for s in sent}
existing_titles = set(e['title'] for e in ev)

# 历史样本统计（供 reference，不含 9/3）
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

# 手动归类 track（盘后 7 条）
def classify_track(title):
    t = title
    if any(k in t for k in ['港股9/3收评', '恒生科技', '恒指']):
        return '恒生科技'
    if any(k in t for k in ['白酒', '消费9/3收盘', '茅台']):
        return '大消费'
    if any(k in t for k in ['医药9/3收盘', '医药生物', '和黄医药', 'GSK', '创新药']):
        return 'A股医药'
    if any(k in t for k in ['每经盘后', 'XLV', '美股']):
        return '宏观'
    return '宏观'

new_events = []
for n in sorted([x for x in sent if x.get('time', '') >= '2026-09-03T14:00'], key=lambda x: x['time']):
    if n['title'] in existing_titles:
        continue
    t = classify_track(n['title'])
    # 宏观类细分为 category
    cat = n.get('category', '行业事件类')
    # A股9/3收盘微涨/美股盘前 -> 宏观
    if '收评' in n['title'] and '港股' not in n['title']:
        t = '宏观'
    if '美股9/3盘前' in n['title']:
        t = '宏观'
    if '每经盘后播报' in n['title']:
        t = 'A股医药'  # 创新药三逻辑利多
    new_events.append({
        'id': f"N{TODAY.replace('-', '')}-{len(ev) + len(new_events) + 1:03d}",
        'date': TODAY, 'track': t, 'category': cat,
        'title': n['title'], 'summary': n.get('summary', ''),
        'source': 'WebSearch', 'source_url': n.get('source_url', ''),
        'sentiment': n.get('sentiment'), 'score': n.get('score'), 'strength': n.get('strength', n.get('score', 50)),
        'direction': n.get('direction'), 'volatility': n.get('volatility'),
        'reason': n.get('reason', ''),
        'reference': {
            'ret_3d': None, 'ret_5d': None, 'ret_10d': None, 'max_vol': None, 'confidence': None,
            'actual_ret_1d': None, 'note': '盘后事件,actual_ret_1d 待 9/3 收盘回填',
        },
    })
print(f'\n盘后新增事件 {len(new_events)} 条')
for e in new_events:
    print(f'  {e["id"]} [{e["track"]}] {e["direction"]}{e["score"]} | {e["title"][:40]}')
ev.extend(new_events)

# 追加事件二次回填（§3.28 教训：追加后立即回填）
fix2 = 0
for x in new_events:
    t = x.get('track')
    if t in track_ret and get_ret1d(x) is None:
        set_ret1d(x, track_ret[t], '赛道指数/ETF收盘(盘后追加)')
        fix2 += 1
json.dump(ev, open(ev_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(f'盘后追加事件二次回填 {fix2} 条')
left2 = [x for x in ev if get_ret1d(x) is None]
print(f'9/3 最终留空 {len(left2)} 条:')
for x in left2:
    print(f'  {x["id"]} [{x["track"]}]')

# ---------- 3. 全库完整性扫描（周日/盘后档规则 §3.35） ----------
all_ev = []
for p in sorted(glob.glob(os.path.join(EV, 'events-*.json'))):
    all_ev += json.load(open(p, encoding='utf-8'))
all_left = [x for x in all_ev if get_ret1d(x) is None]
print(f'\n全库共 {len(all_ev)} 条, 留空 {len(all_left)} 条')
for x in all_left:
    print(f'  {x["id"]} {x.get("date")} [{x.get("track")}]')

# ---------- 4. 1日样本统计 + 方向验证（sentiment 口径） ----------
samples = defaultdict(lambda: {'n': 0, 'rets': [], 'pos': 0, 'spos': 0, 'sneg': 0, 'spos_rets': [], 'sneg_rets': []})
direction_ok = 0
direction_total = 0
for e in all_ev:
    v = get_ret1d(e)
    if v is None:
        continue
    t = e.get('track', '?')
    s = samples[t]
    s['n'] += 1
    s['rets'].append(float(v))
    if float(v) > 0:
        s['pos'] += 1
    # 方向验证（sentiment 口径）：正面且 ret>0 / 负面且 ret<0 / 中性恒 ok
    senti = e.get('sentiment')
    if senti == '正面' and float(v) > 0:
        direction_ok += 1
    elif senti == '负面' and float(v) < 0:
        direction_ok += 1
    elif senti == '中性':
        direction_ok += 1
    elif senti is None:
        pass  # 不计
    else:
        direction_total_before = direction_total
    # 计数（仅 有 sentiment 的）
    if senti:
        direction_total += 1
        if senti == '正面' and not (float(v) > 0):
            pass
        if senti == '负面' and not (float(v) < 0):
            pass
        if senti not in ('正面', '负面', '中性'):
            pass
    # 强样本
    score = e.get('score')
    try:
        score = int(score)
    except:
        score = None
    if senti == '正面' and score is not None and score >= 65:
        s['spos'] += 1
        s['spos_rets'].append(float(v))
    if senti == '负面' and score is not None and score <= 40:
        s['sneg'] += 1
        s['sneg_rets'].append(float(v))

# 修正 direction 计数逻辑（口径与 9/2 一致：中性事件不计入分子分母，只统计 正面/负面 事件的方向兑现）
direction_ok = 0
direction_total = 0
track_dv = defaultdict(lambda: [0, 0])
for e in all_ev:
    v = get_ret1d(e)
    if v is None:
        continue
    senti = e.get('sentiment')
    if senti not in ('正面', '负面'):
        continue
    direction_total += 1
    t = e.get('track', '?')
    track_dv[t][1] += 1
    ok = (senti == '正面' and float(v) > 0) or (senti == '负面' and float(v) < 0)
    if ok:
        direction_ok += 1
        track_dv[t][0] += 1

print('\n=== 1日样本统计（截至 9/3 收盘） ===')
out_stats = {}
for t, s in samples.items():
    if s['n'] == 0:
        continue
    rec = {
        'n': s['n'],
        'avg': round(sum(s['rets'])/len(s['rets']), 2),
        'worst': round(min(s['rets']), 2),
        'best': round(max(s['rets']), 2),
        'pos': round(s['pos']/s['n'], 2),
        'strong_pos_n': s['spos'],
        'strong_pos_avg': round(sum(s['spos_rets'])/len(s['spos_rets']), 2) if s['spos_rets'] else None,
        'strong_neg_n': s['sneg'],
        'strong_neg_avg': round(sum(s['sneg_rets'])/len(s['sneg_rets']), 2) if s['sneg_rets'] else None,
    }
    out_stats[t] = rec
    print(f"  {t}: n={rec['n']} avg={rec['avg']}% worst={rec['worst']} best={rec['best']} pos率={rec['pos']} 强正{rec['strong_pos_n']}条均值{rec['strong_pos_avg']} 强负{rec['strong_neg_n']}条均值{rec['strong_neg_avg']}")

print(f'\n=== 方向验证（sentiment 口径，1日样本） ===')
print(f'  全局 {direction_ok}/{direction_total} ({round(direction_ok/direction_total*100)}%)')
for t, (ok, tot) in sorted(track_dv.items(), key=lambda x: -x[1][0]):
    if tot > 0:
        print(f'  {t}: {ok}/{tot} ({round(ok/tot*100)}%)')

# ---------- 5. 3/5日窗口统计（indices.csv 赛道指数日线） ----------
import csv
idx_rows = list(csv.reader(open(os.path.join(BASE, 'data/processed/history/indices.csv'), encoding='utf-8-sig')))
# 赛道 -> 指数代码映射（用日线序列）
track_index = {
    'A股医药': ('sz399006', '创业板指'),   # A股医药用创业板指近似（§3.41）
    '大消费': ('sh000932', '中证消费'),
    '恒生科技': ('HSTECH', '恒生科技'),
    '宏观': ('sh000001', '上证指数'),
    '美股标普医药': ('XLV', '美股医疗XLV'),
}
def build_series(code):
    dates, closes = [], []
    for r in idx_rows:
        if r and len(r) >= 6 and r[3] == code and r[1] != '':
            try:
                d = r[1][:10]
                c = float(r[4])
            except:
                continue
            # 去重（保留 note 含收盘/美股收盘 优先）
            dates.append(d)
            closes.append(c)
    # 按日期排序去重取最后
    seen = {}
    for d, c in zip(dates, closes):
        seen[d] = c
    ds = sorted(seen.items())
    return [d for d, _ in ds], [c for _, c in ds]

def window_stats(ev_date, code, n_days):
    """事件日之后 n_days 个交易日的赛道累计收益"""
    dates, closes = build_series(code)
    if not dates:
        return None
    try:
        i0 = dates.index(ev_date)
    except ValueError:
        return None
    # 从 i0+1 起累计 n_days 个交易日
    ret = 1.0
    cnt = 0
    for i in range(i0 + 1, len(dates)):
        if cnt >= n_days:
            break
        if closes[i] is None or closes[i-1] in (None, 0):
            continue
        ret *= closes[i] / closes[i-1]
        cnt += 1
    if cnt < n_days:
        return None
    return (ret - 1) * 100

win3 = defaultdict(lambda: {'n': 0, 'rets': []})
win5 = defaultdict(lambda: {'n': 0, 'rets': []})
for e in all_ev:
    d = e.get('date')
    t = e.get('track')
    if not d or t not in track_index:
        continue
    code = track_index[t][0]
    r3 = window_stats(d, code, 3)
    r5 = window_stats(d, code, 5)
    if r3 is not None:
        win3[t]['n'] += 1
        win3[t]['rets'].append(r3)
    if r5 is not None:
        win5[t]['n'] += 1
        win5[t]['rets'].append(r5)

def agg(w):
    out = {}
    for t, s in w.items():
        if s['n']:
            out[t] = {'n': s['n'], 'avg': round(sum(s['rets'])/len(s['rets']), 2)}
    return out
w3, w5 = agg(win3), agg(win5)
print('\n=== 3日窗口统计 ===')
for t, v in sorted(w3.items(), key=lambda x: -x[1]['avg']):
    print(f'  {t}: n={v["n"]} 均值 {v["avg"]}%')
print('=== 5日窗口统计 ===')
for t, v in sorted(w5.items(), key=lambda x: -x[1]['avg']):
    print(f'  {t}: n={v["n"]} 均值 {v["avg"]}%')

# 存统计结果
with open(os.path.join(BASE, 'data/processed/events/event_stats_20260903.json'), 'w', encoding='utf-8') as f:
    json.dump({
        'date': TODAY,
        'total_events': len(all_ev),
        'null_ret': len(all_left),
        'track_1d': out_stats,
        'direction': {'ok': direction_ok, 'total': direction_total, 'rate': round(direction_ok/direction_total*100, 1) if direction_total else None,
                      'by_track': {t: {'ok': v[0], 'total': v[1]} for t, v in track_dv.items()}},
        'win3': w3, 'win5': w5,
    }, f, ensure_ascii=False, indent=1)
print('\n已保存 event_stats_20260903.json')
