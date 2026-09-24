# -*- coding: utf-8 -*-
"""2026-09-24 盘前档事件库处理：
  ① 回填：9/23 遗留的 11 条留空事件（**全为「美股标普医药」**，参考日 = XLV 9/23 收盘 168.80 / -0.64%）
  ② 追加本档 43 条盘前事件（window == '盘前(9/23 18:00-9/24 07:30)'，含空集硬守卫）
  ③ 全库完整性扫描（留空按「日期×赛道」二维落库，§3.98；留空健康基线判据 §3.102）
  ④ 1日样本 + 3/5/10日窗口统计 → history/event_stats_20260924_preopen.json
⚠️ 口径问题：A股医药 3/5/10 日窗口序列实际使用 399006（创业板指）作代理（§3.90），报告须显式披露。
⚠️ 参考交易日规则（§3.95/§3.100）：事件日之后的第一个交易日；美股标普医药用 XLV 序列（美东交易日）；
   宏观类参考交易日 = 上证指数 000001；A股医药 1 日 = 000933，3/5/10 日用 399006 代理（双口径并存）。
⚠️ 方向验证（§3.102）：分母只统计 `actual_date` 等于当日的事件，须标注「有效样本 n / 全部 n」。
"""
import json, os, glob, csv
from collections import defaultdict

BASE = '/Users/jieyang/Documents/WealthHub'
EV = os.path.join(BASE, 'data/processed/events')
HIST = os.path.join(BASE, 'data/processed/history')
TODAY = '2026-09-24'
WIN = '盘前(9/23 18:00-9/24 07:30)'
REF_INDEX = {'宏观': '000001', 'A股医药': '000933', '大消费': '000932', '恒生科技': 'HSTECH',
             '美股标普医药': 'XLV', '其他/宽基': '000300'}

# ---------- 指数序列 ----------
idx = defaultdict(dict)
with open(os.path.join(HIST, 'indices.csv'), encoding='utf-8-sig') as fh:
    for row in csv.DictReader(fh):
        try:
            idx[row['code']][row['date']] = float(row['close'])
        except Exception:
            pass
for code in REF_INDEX.values():
    ds = sorted(idx.get(code, {}))
    print(f'  {code}: {len(ds)} 个交易日，尾部 ' + ' | '.join(f'{d}:{idx[code][d]}' for d in ds[-3:]))


def ref_ret(code, event_date):
    """事件日之后（含当日）的第一个交易日及其单日涨跌幅"""
    ser = idx.get(code)
    if not ser:
        return None, None
    ds = sorted(ser)
    for i, d in enumerate(ds):
        if d >= event_date and i > 0:
            return d, round((ser[d] / ser[ds[i - 1]] - 1) * 100, 4)
    return None, None


# ---------- ① 回填 ----------
backfilled, back_detail = 0, []
for f in sorted(glob.glob(os.path.join(EV, 'events-*.json'))):
    ev = json.load(open(f, encoding='utf-8'))
    touched = False
    for e in ev:
        code = REF_INDEX.get(e['track'])
        if not code:
            continue
        ref = e.setdefault('reference', {})
        if ref.get('actual_ret_1d') is not None:
            continue
        d, r = ref_ret(code, e['date'])
        if r is None:
            continue
        ref['actual_ret_1d'] = r
        ref['actual_date'] = d
        ref['ret_1d_ref'] = f'{d} 收盘：{code} {idx[code][d]} {r:+.2f}%'
        backfilled += 1
        touched = True
        back_detail.append({'file': os.path.basename(f), 'date': e['date'], 'track': e['track'],
                            'actual_date': d, 'ret_1d': r})
    if touched:
        json.dump(ev, open(f, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
by_evdate, by_track_bf = defaultdict(int), defaultdict(int)
for x in back_detail:
    by_evdate[x['date']] += 1
    by_track_bf[x['track']] += 1
print(f'\n回填 {backfilled} 条；按事件日 {dict(by_evdate)}；按赛道 {dict(by_track_bf)}')

# ---------- ② 追加本档事件 ----------
news = json.load(open(os.path.join(BASE, f'data/processed/news/news-{TODAY}.json'), encoding='utf-8'))
sent = json.load(open(os.path.join(BASE, f'data/processed/news/sentiment-{TODAY}.json'), encoding='utf-8'))
ev_path = os.path.join(EV, f'events-{TODAY}.json')
ev = json.load(open(ev_path, encoding='utf-8')) if os.path.exists(ev_path) else []
existing = {e['title'][:60] for e in ev}

win_sent = [x for x in sent['items'] if x.get('window') == WIN]
if not win_sent:
    raise SystemExit('⚠️ 盘前窗口 sentiment 为 0 条 → per-item `window` 字段可能缺失（§3.88），终止以免静默跳过入库')
added = []
for x in win_sent:
    n = next((y for y in news if y['title'][:60] == x['title']), None)
    if n is None or n['title'][:60] in existing:
        continue
    seq = len(ev) + len(added) + 1
    added.append({
        'id': f"N{TODAY.replace('-', '')}-{seq:03d}", 'date': TODAY, 'track': n['track'],
        'category': n.get('category', '行业事件类'), 'title': n['title'],
        'summary': n.get('summary', ''), 'source': n.get('source', 'WebSearch'),
        'source_url': n.get('source_url', ''), 'sentiment': n.get('sentiment'),
        'score': n.get('score'), 'strength': n.get('strength'),
        'direction': n.get('direction'), 'volatility': n.get('volatility'),
        'reason': n.get('brief', ''),
        'reference': {'ret_3d': None, 'ret_5d': None, 'ret_10d': None,
                      'actual_ret_1d': None,
                      'max_vol': {'低': 1.5, '中': 4.8, '高': 9.0}.get(n.get('volatility'), 4.8),
                      'confidence': n.get('confidence')},
    })
ev.extend(added)
json.dump(ev, open(ev_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(f'事件库 {TODAY} +{len(added)} 条 → 当日 {len(ev)} 条')

# ---------- ③ 完整性扫描 ----------
files = sorted(glob.glob(os.path.join(EV, 'events-*.json')))
all_ev, dup = [], {}
for f in files:
    for e in json.load(open(f, encoding='utf-8')):
        all_ev.append(e)
        dup[e['title'][:60]] = dup.get(e['title'][:60], 0) + 1
n_blank = sum(1 for e in all_ev if e.get('reference', {}).get('actual_ret_1d') is None)
blank_by_date, blank_by_track = defaultdict(int), defaultdict(int)
for e in all_ev:
    if e.get('reference', {}).get('actual_ret_1d') is None:
        blank_by_date[e['date']] += 1
        blank_by_track[e['track']] += 1
print(f'\n全库 {len(all_ev)} 条 / {len(files)} 日；留空 {n_blank} 条')
print(f'  留空按日: {dict(blank_by_date)}')
print(f'  留空按赛道: {dict(blank_by_track)}')
print(f'  跨日重复标题 {sum(1 for v in dup.values() if v > 1)} 组')
today_us = sum(1 for e in all_ev if e['date'] == TODAY and e['track'] == '美股标普医药')
print(f'  【§3.102 留空健康基线】当日({TODAY})美股标普医药新增数 = {today_us}，全库留空 = {n_blank} '
      f'→ {"✅ 相符" if today_us == n_blank else "⚠️ 不符，存在跨档未闭环"}')

# ---------- ④ 统计 ----------
track_index = {'A股医药': '399006', '大消费': '000932', '恒生科技': 'HSTECH',
               '美股标普医药': 'XLV', '其他/宽基': '000300'}


def fwd(code, d0, n):
    ser = idx.get(code)
    if not ser:
        return None
    ds = sorted(d for d in ser if d >= d0)
    if len(ds) < n + 1:
        return None
    try:
        return round((ser[ds[n]] / ser[ds[0]] - 1) * 100, 4)
    except Exception:
        return None


win, ones = defaultdict(lambda: defaultdict(list)), defaultdict(list)
for e in all_ev:
    t = e['track']
    r = e.get('reference', {})
    v = r.get('actual_ret_1d')
    if v is not None and t in track_index:
        ones[t].append((v, e.get('direction'), e.get('strength')))
    code = track_index.get(t)
    if not code:
        continue
    for n in (3, 5, 10):
        x = fwd(code, e['date'], n)
        if x is not None:
            win[t][n].append(x)

print('\n1 日样本（按赛道，全库）:')
for t, arr in sorted(ones.items()):
    vs = [a[0] for a in arr]
    sp = [a[0] for a in arr if a[1] == '利多' and (a[2] or 0) >= 70]
    sn = [a[0] for a in arr if a[1] == '利空' and (a[2] or 0) >= 70]
    line = (f"  {t:8s} n={len(vs):>4d} 均值={sum(vs)/len(vs):+.4f}% "
            f"上涨占比={sum(1 for v in vs if v>0)/len(vs):.4f}")
    if sp:
        line += f" 强正面={sum(sp)/len(sp):+.4f}%(n={len(sp)})"
    if sn:
        line += f" 强负面={sum(sn)/len(sn):+.4f}%(n={len(sn)})"
    print(line)

print('\n3/5/10 日窗口:')
for t, d in sorted(win.items()):
    row = []
    for n in (3, 5, 10):
        a = d[n]
        row.append(f"{n}日={sum(a)/len(a):+.4f}%(n={len(a)})" if a else f"{n}日=n/a")
    print(f"  {t:8s} " + ' | '.join(row))

# 方向验证：仅统计 actual_date == 2026-09-23 的事件（§3.102 有效样本口径）
hit, tot, all_tot = 0, 0, 0
by_dir = defaultdict(lambda: [0, 0])
for e in all_ev:
    r0 = e.get('reference', {})
    if e['date'] != '2026-09-23':
        continue
    all_tot += 1
    if r0.get('actual_date') != '2026-09-23':
        continue
    v, d = r0.get('actual_ret_1d'), e.get('direction')
    if v is None or d not in ('利多', '利空'):
        continue
    tot += 1
    ok = (v > 0) if d == '利多' else (v < 0)
    hit += ok
    by_dir[d][0] += ok
    by_dir[d][1] += 1
print(f"\n方向验证（参考日 9/23，有效样本口径 §3.102）: {hit}/{tot}"
      + (f"（{hit/tot*100:.1f}%）" if tot else "")
      + (f" — 利多 {by_dir['利多'][0]}/{by_dir['利多'][1]}、利空 {by_dir['利空'][0]}/{by_dir['利空'][1]}" if tot else "")
      + f" ｜ 有效样本 {tot} / 全部当日事件 {all_tot}")

# 主线/暴露加权净情绪分（§3.101「暴露错配」判据）
sent_all = json.load(open(os.path.join(BASE, f'data/processed/news/sentiment-{TODAY}.json'), encoding='utf-8'))
EXPO = {'大消费': 19.74, 'A股医药': 23.58, '美股标普医药': 15.55, '恒生科技': 8.49, '其他/宽基': 25.01}
net = defaultdict(float)
for x in sent_all['items']:
    if x.get('window') != WIN:
        continue
    sg = 1 if x['direction'] == '利多' else (-1 if x['direction'] == '利空' else 0)
    net[x['track']] += sg * x['strength'] / 100
print('\n赛道净情绪分（Σ方向×强度/100）与暴露加权:')
expo_weighted = 0.0
for t in EXPO:
    print(f"  {t:8s} 净分={net[t]:+.2f}  暴露={EXPO[t]:.2f}%")
    expo_weighted += net[t] * EXPO[t] / 100
print(f'  → **暴露加权净情绪分 = {expo_weighted:+.2f}**（§3.101 暴露错配判据：>0 但组合收跌则提示暴露错配）')

out = {
    'date': TODAY, 'window': 'preopen', 'total_events': len(all_ev),
    'today_events': len(ev), 'blank': n_blank,
    'blank_by_date': dict(blank_by_date), 'blank_by_track': dict(blank_by_track),
    'backfilled': backfilled, 'backfill_by_event_date': dict(by_evdate),
    'backfill_by_track': dict(by_track_bf),
    'onesample': {t: {'n': len(a), 'mean': round(sum(x[0] for x in a) / len(a), 4),
                      'min': min(x[0] for x in a), 'max': max(x[0] for x in a),
                      'up_ratio': round(sum(1 for x in a if x[0] > 0) / len(a), 4)}
                  for t, a in ones.items()},
    'windows': {t: {str(n): ({'n': len(a), 'mean': round(sum(a) / len(a), 4)} if a else {'n': 0, 'mean': None})
                    for n, a in d.items()}
                for t, d in win.items()},
    'direction_check_0923': {'hit': hit, 'total': tot, 'all_today': all_tot,
                             'by_dir': {k: {'hit': v[0], 'total': v[1]} for k, v in by_dir.items()}},
    'exposure_weighted_net_sentiment': round(expo_weighted, 3),
    'track_net_sentiment': {k: round(v, 4) for k, v in net.items()},
    'track_index_map': track_index,
    'ref_index_map': REF_INDEX,
    'note': ('A股医药 3/5/10 日窗口序列实际使用 399006（创业板指）代理（§3.90），1 日窗口用 000933；'
             '本档回填 9/23 遗留 11 条（全部为美股标普医药，参考日 = XLV 9/23 收盘 168.80 / -0.64%）；'
             '本档 43 条事件参考交易日=9/24（尚未收盘）→ 留空待 9/24 盘后档；'
             '方向验证分母仅统计 actual_date=2026-09-23 的有效样本（§3.102）'),
}
json.dump(out, open(os.path.join(HIST, f'event_stats_{TODAY.replace("-", "")}_preopen.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
print(f"\n已保存 event_stats_{TODAY.replace('-', '')}_preopen.json")
