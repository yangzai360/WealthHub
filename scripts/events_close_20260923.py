# -*- coding: utf-8 -*-
"""2026-09-23 盘后档事件库处理：
  ① 追加盘后 25 条事件（过滤 window == '盘后(14:00-20:00)'，含 §3.88 空集硬守卫）
     ⚠️ §3.102 修复：`ev.extend(added)` 后必须 json.dump 回写（9/21 盘后档漏写 → 18 条事件丢失）
  ② 补偿性恢复 9/21 盘后 18 条丢失事件（从 news-2026-09-21.json 的 window=='close' 重建，标记 recovered）
  ③ 回填 9/23 全部留空事件（参考交易日 = 9/23；固定映射表见 §3.100）
  ④ 全库完整性扫描 + 1日样本 + 方向验证 + 3/5/10日窗口统计 → event_stats_20260923_close.json
⚠️ A股医药 3/5/10 日窗口仍用 399006（创业板指）代理（000933 仅 7 行 < 15，§3.90 待办未清）
⚠️ 事件统计脚本中 windows 可能为空列表 → 除零守卫（§3.93）
"""
import json, os, glob, csv
from collections import defaultdict

BASE = '/Users/jieyang/Documents/WealthHub'
EV = os.path.join(BASE, 'data/processed/events')
HIST = os.path.join(BASE, 'data/processed/history')
TODAY = '2026-09-23'
WIN = '盘后(14:00-20:00)'

# 9/23 收盘口径赛道涨跌（§3.100 固定映射表：1 日实测口径用板块指数）
track_ret = {
    '宏观': -0.39,       # 000001 上证指数 3,936.52 -0.39%
    'A股医药': 0.07,     # 000933 中证医药 7,948.6794 +0.07%（中证医疗 +0.28% / 300医药 -0.23%）
    '大消费': -0.27,     # 000932 中证消费 12,288.7946 -0.27%（中证白酒 -0.23%）
    '恒生科技': -1.33,   # HSTECH 4,379.07 -1.33%（恒生指数 -1.01%）
    '其他/宽基': -0.60,  # 000300 沪深300 4,517.28 -0.60%
    # 美股标普医药：XLV 9/23 尚未收盘（美东 9/23 开盘 = 北京 9/23 21:30）→ 留空待 9/24 盘前档兜底（§3.97⑤ 永久 T+1）
}
REF = {
    '宏观': '9/23 收盘：000001 上证指数 3936.52 -0.39%',
    'A股医药': '9/23 收盘：000933 中证医药 7948.6794 +0.07%（中证医疗 6887.99 +0.28% / 300医药 8233.97 -0.23%）',
    '大消费': '9/23 收盘：000932 中证消费 12288.7946 -0.27%（中证白酒 6237.18 -0.23%）',
    '恒生科技': '9/23 收盘：HSTECH 4379.07 -1.33%（恒生指数 24834.12 -1.01%）',
    '其他/宽基': '9/23 收盘：000300 沪深300 4517.28 -0.60%',
}
# 9/21 补偿恢复用（沿用 events_close_20260921.py 已定义口径）
R21 = {'A股医药': 2.83, '大消费': 0.88, '恒生科技': 0.40, '宏观': 0.97,
       '其他/宽基': 2.25, '美股标普医药': 0.3682}
REF21 = {'A股医药': '9/21 收盘：医药ETF广发 0.655 +3.31% / 医疗ETF 0.348 +2.35%（中证医药 7,954.82 +3.04%）',
         '大消费': '9/21 收盘：中证消费 12,321.63 +0.88%',
         '恒生科技': '9/21 收盘：HSTECH 4,423.29 +0.40%',
         '宏观': '9/21 收盘：上证指数 3,949.91 +0.97%',
         '其他/宽基': '9/21 收盘：个股均值（广联达 8.60 +2.38% / 通威股份 11.59 +2.11%）',
         '美股标普医药': '9/21 收盘：XLV 169.01 +0.3682%（补偿口径）'}

# ---------- ① 追加盘后事件 ----------
news = json.load(open(os.path.join(BASE, 'data/processed/news/news-2026-09-23.json'), encoding='utf-8'))
sent = json.load(open(os.path.join(BASE, 'data/processed/news/sentiment-2026-09-23.json'), encoding='utf-8'))
items = sent['items'] if isinstance(sent, dict) else sent
ev_path = os.path.join(EV, f'events-{TODAY}.json')
ev = json.load(open(ev_path, encoding='utf-8'))
existing = {e['title'] for e in ev}

close_sent = [x for x in items if x.get('window') == WIN]
if not close_sent:
    raise SystemExit('⚠️ 盘后窗口 sentiment 为 0 条 → per-item `window` 字段可能缺失（§3.88），终止以免静默跳过事件入库')
added = []
for x in close_sent:
    n = next((y for y in news if y['title'][:60] == x['title']), None)
    if n is None or n['title'] in existing:
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
        'window': WIN,
        'reference': {'ret_3d': None, 'ret_5d': None, 'ret_10d': None,
                      'max_vol': {'低': 1.5, '中': 4.8, '高': 9.0}.get(n.get('volatility'), 4.8),
                      'confidence': n.get('confidence')},
    })
ev.extend(added)
json.dump(ev, open(ev_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)   # §3.102 修复：必须回写
print(f'事件库 {TODAY} +{len(added)} 条 → {len(ev)} 条（已回写）')

# ---------- ② 补偿恢复 9/21 盘后 18 条 ----------
p21 = os.path.join(EV, 'events-2026-09-21.json')
e21 = json.load(open(p21, encoding='utf-8'))
have21 = {e['title'] for e in e21}
news21 = json.load(open(os.path.join(BASE, 'data/processed/news/news-2026-09-21.json'), encoding='utf-8'))
rec = []
for n in news21:
    if n.get('window') != 'close' or n['title'] in have21:
        continue
    seq = len(e21) + len(rec) + 1
    rec.append({'id': f'N20260921-{seq:03d}', 'date': '2026-09-21', 'track': n['track'],
                'category': n.get('category', '行业事件类'), 'title': n['title'],
                'summary': n.get('summary', ''), 'source': n.get('source', 'WebSearch'),
                'source_url': n.get('source_url', ''), 'sentiment': n.get('sentiment'),
                'score': n.get('score'), 'strength': n.get('strength'),
                'direction': n.get('direction'), 'volatility': n.get('volatility'),
                'reason': n.get('brief', ''), 'window': 'close',
                'recovered': True,
                'recovered_note': '9/21 盘后档 events 脚本漏写回盘（§3.102）→ 本档从 news-2026-09-21.json(window=close) 补偿重建',
                'reference': {'ret_3d': None, 'ret_5d': None, 'ret_10d': None,
                              'max_vol': {'低': 1.5, '中': 4.8, '高': 9.0}.get(n.get('volatility'), 4.8),
                              'confidence': n.get('confidence')}})
e21.extend(rec)
json.dump(e21, open(p21, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(f'9/21 补偿恢复盘后事件 +{len(rec)} 条 → {len(e21)} 条')

# ---------- ③ 回填 9/23 留空事件 ----------
filled, blank = 0, 0
blank_detail = defaultdict(int)
e2 = json.load(open(ev_path, encoding='utf-8'))
for e in e2:
    r = e.setdefault('reference', {})
    if r.get('actual_ret_1d') is not None:
        continue
    t = e['track']
    if t in track_ret:
        r['actual_ret_1d'] = track_ret[t]
        r['actual_date'] = TODAY
        r['ret_1d_ref'] = REF[t]
        filled += 1
    else:
        blank += 1
        blank_detail[t] += 1
json.dump(e2, open(ev_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(f'9/23 回填 {filled} 条；留空 {blank} 条 {dict(blank_detail)}（美股标普医药，待 9/24 盘前档按 XLV 9/23 收盘兜底）')

# 同时给 9/21 补偿事件补回填
ch21 = 0
for e in e21:
    r = e.setdefault('reference', {})
    if r.get('actual_ret_1d') is None and e['track'] in R21:
        r['actual_ret_1d'] = R21[e['track']]
        r['actual_date'] = '2026-09-21'
        r['ret_1d_ref'] = REF21[e['track']]
        ch21 += 1
json.dump(e21, open(p21, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(f'9/21 补偿事件回填 {ch21} 条')

# ---------- ④ 全库完整性扫描 ----------
files = sorted(glob.glob(os.path.join(EV, 'events-*.json')))
all_ev = []
for f in files:
    all_ev.extend(json.load(open(f, encoding='utf-8')))
n_blank = sum(1 for e in all_ev if e.get('reference', {}).get('actual_ret_1d') is None)
print(f'\n全库 {len(all_ev)} 条 / {len(files)} 日；留空 {n_blank} 条')

# ---------- ⑤ 统计 ----------
idx = defaultdict(dict)
with open(os.path.join(HIST, 'indices.csv'), encoding='utf-8-sig') as fh:
    for row in csv.DictReader(fh):
        try:
            idx[row['code']][row['date']] = float(row['close'])
        except Exception:
            pass
track_index = {'A股医药': '399006', '大消费': '000932', '恒生科技': 'HSTECH',
               '美股标普医药': 'XLV', '其他/宽基': '000300'}
avail = {k: len(v) for k, v in idx.items()}


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


win = defaultdict(lambda: defaultdict(list))
win_unavail = defaultdict(lambda: defaultdict(int))
ones = defaultdict(list)
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
        else:
            win_unavail[t][n] += 1

print('\n1 日样本（按赛道）:')
for t, arr in sorted(ones.items()):
    vs = [a[0] for a in arr]
    if not vs:
        continue
    sp = [a[0] for a in arr if a[1] == '利多' and (a[2] or 0) >= 70]
    sn = [a[0] for a in arr if a[1] == '利空' and (a[2] or 0) >= 70]
    f = lambda a: f"{sum(a)/len(a):+.2f}%(n={len(a)})" if a else 'n/a'
    print(f"  {t:8s} n={len(vs):>4d} 均值={sum(vs)/len(vs):+.2f}% 最差={min(vs):+.2f}% 最好={max(vs):+.2f}% "
          f"上涨占比={sum(1 for v in vs if v>0)/len(vs):.2f} 强正面={f(sp)} 强负面={f(sn)}")

print('\n3/5/10 日窗口:')
for t, d in sorted(win.items()):
    row = []
    for n in (3, 5, 10):
        a = d[n]
        row.append(f"{n}日={sum(a)/len(a):+.2f}%(n={len(a)})" if a else f"{n}日=n/a(不可用 {win_unavail[t][n]} 条)")
    print(f"  {t:8s} " + ' | '.join(row))

# 方向验证（9/23 当日）
today_ev = [e for e in all_ev if e['date'] == TODAY]
hit, tot = 0, 0
per = defaultdict(lambda: [0, 0])
for e in today_ev:
    r = e.get('reference', {})
    v, d = r.get('actual_ret_1d'), e.get('direction')
    if v is None or d not in ('利多', '利空'):
        continue
    tot += 1
    ok = (v > 0) if d == '利多' else (v < 0)
    hit += ok
    per[d][0] += ok
    per[d][1] += 1
msg = f'\n方向验证（9/23 当日，sentiment 口径，参考交易日=9/23）: {hit}/{tot}（{hit/tot*100:.0f}%）' if tot else '\n方向验证: 无有效样本'
if per['利空'][1] and per['利多'][1]:
    msg += (f" — 利多 {per['利多'][0]}/{per['利多'][1]}（{per['利多'][0]/per['利多'][1]*100:.0f}%）"
            f" vs 利空 {per['利空'][0]}/{per['利空'][1]}（{per['利空'][0]/per['利空'][1]*100:.0f}%）")
print(msg)

# 按赛道加权的净方向（§3.101「暴露错配」判据）
expo = {'A股医药': 23.58, '大消费': 19.75, '恒生科技': 8.49, '其他/宽基': 25.01,
        '美股标普医药': 15.55}
netscore = defaultdict(float)
cnt = defaultdict(int)
for e in today_ev:
    t = e['track']
    s = e.get('strength') or 0
    d = e.get('direction')
    netscore[t] += (s if d == '利多' else -s if d == '利空' else 0)
    cnt[t] += 1
print('\n赛道净情绪分与暴露加权（§3.101）:')
wsum = 0.0
for t in expo:
    ns = netscore[t] / max(cnt[t], 1)
    wsum += expo[t] / 100 * ns
    print(f'  {t:8s} 暴露 {expo[t]:>5.2f}%  条数 {cnt[t]:>2d}  净情绪分 {ns:+.2f}  加权 {expo[t]/100*ns:+.2f}')
print(f'  → 暴露加权净方向分 {wsum:+.2f}（组合当日实际 {track_ret.get("其他/宽基")} 等；组合日收益 -0.1393%）')

out = {
    'date': TODAY, 'window': 'close', 'total_events': len(all_ev),
    'days': len(files), 'today_events': len(today_ev), 'blank': n_blank,
    'blank_tracks': dict(blank_detail), 'blank_by_date_track': {'2026-09-23': dict(blank_detail)},
    'track_ret_1d': track_ret, 'ref': REF,
    'recovered_9_21': len(rec),
    'onesample': {t: {'n': len(a), 'mean': round(sum(x[0] for x in a) / len(a), 4),
                      'min': min(x[0] for x in a), 'max': max(x[0] for x in a),
                      'up_ratio': round(sum(1 for x in a if x[0] > 0) / len(a), 4),
                      'strong_pos': {'n': len([x for x in a if x[1] == '利多' and (x[2] or 0) >= 70]),
                                     'mean': round(sum(x[0] for x in a if x[1] == '利多' and (x[2] or 0) >= 70) /
                                                   max(len([x for x in a if x[1] == '利多' and (x[2] or 0) >= 70]), 1), 4)},
                      'strong_neg': {'n': len([x for x in a if x[1] == '利空' and (x[2] or 0) >= 70]),
                                     'mean': round(sum(x[0] for x in a if x[1] == '利空' and (x[2] or 0) >= 70) /
                                                   max(len([x for x in a if x[1] == '利空' and (x[2] or 0) >= 70]), 1), 4)}}
                  for t, a in ones.items() if a},
    'windows': {t: {str(n): ({'n': len(a), 'mean': round(sum(a) / len(a), 4)} if a else {'n': 0, 'mean': None,
                                                                                        'unavailable': win_unavail[t][n]})
                     for n, a in d.items()}
                for t, d in win.items()},
    'direction_check': {'hit': hit, 'total': tot,
                        'by_dir': {k: {'hit': v[0], 'total': v[1]} for k, v in per.items()}},
    'exposure_weighted_net': {t: round(netscore[t] / max(cnt[t], 1), 2) for t in expo},
    'exposure_weighted_net_score': round(wsum, 2),
    'track_index_map': track_index,
    'index_avail_rows': avail,
    'note': 'A股医药 3/5/10 日窗口序列实际使用 399006（创业板指）代理（000933 仅 7 行 < 15，见知识库 §3.90）；宏观类无 3/5/10 日窗口映射；9/21 盘后 18 条事件为补偿恢复（§3.102）',
}
json.dump(out, open(os.path.join(HIST, 'event_stats_20260923_close.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
print('\nSAVED event_stats_20260923_close.json')
