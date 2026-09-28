# -*- coding: utf-8 -*-
"""2026-09-28 盘后档事件库处理：
  ① 追加盘后 23 条事件（过滤 window == '盘后(14:00-20:00)'，§3.88 空集硬守卫）
  ② 回填全部参考交易日 = 2026-09-28 的留空事件（9/25 遗留 77 A股类 + 9/27 的 24 + 9/28 盘前 43 + 盘中 29 = 173）
     美股标普医药留空（XLV 9/28 未收盘 → T+1，§3.97⑤）
  ③ 全库完整性扫描 + 1日样本 + 方向验证（有效样本口径 §3.102/§3.103）+ 3/5/10日窗口 → event_stats_20260928_close.json
⚠️ §3.111b：A股医药 3/5/10 日窗口用 399006（创业板指）代理；1 日窗口用 000933 真实收盘
⚠️ windows 空列表除零守卫（§3.93）；全 None 不得聚合为 0.0（§3.104）
"""
import json, os, glob, csv
from collections import defaultdict

BASE = '/Users/jieyang/Documents/WealthHub'
EV = os.path.join(BASE, 'data/processed/events')
HIST = os.path.join(BASE, 'data/processed/history')
TODAY = '2026-09-28'
WIN = '盘后(14:00-20:00)'

track_ret = {
    '宏观': -1.67,       # 000001 上证指数 3,823.6206 -1.67%
    'A股医药': 0.26,     # 000933 中证医药 7,770.69 +0.26%（中证医疗 -0.14% / 300医药 +0.23%）
    '大消费': -0.11,     # 000932 中证消费 12,096.02 -0.11%（中证白酒 -0.91%）
    '恒生科技': -0.37,   # HSTECH 4,296.00 -0.37%（恒生指数 24,642.51 +0.54%）
    '其他/宽基': -2.22,  # 000300 沪深300 4,340.76 -2.22%
}
REF = {
    '宏观': '9/28 收盘：000001 上证指数 3823.6206 -1.67%（深成 -3.44% / 创业板指 -4.53%）',
    'A股医药': '9/28 收盘：000933 中证医药 7770.69 +0.26%（中证医疗 6721.58 -0.14% / 300医药 8052.78 +0.23%）',
    '大消费': '9/28 收盘：000932 中证消费 12096.02 -0.11%（中证白酒 6049.99 -0.91%）',
    '恒生科技': '9/28 收盘：HSTECH 4296.00 -0.37%（恒生指数 24642.51 +0.54%）',
    '其他/宽基': '9/28 收盘：000300 沪深300 4340.76 -2.22%',
}
MAXVOL = {'低': 1.5, '中': 4.8, '高': 9.0}

# ---------- ① 追加盘后事件 ----------
news = json.load(open(os.path.join(BASE, 'data/processed/news/news-2026-09-28.json'), encoding='utf-8'))
sent = json.load(open(os.path.join(BASE, 'data/processed/news/sentiment-2026-09-28.json'), encoding='utf-8'))
items = sent['items'] if isinstance(sent, dict) else sent
ev_path = os.path.join(EV, f'events-{TODAY}.json')
ev = json.load(open(ev_path, encoding='utf-8'))
existing = {e['title'] for e in ev}
print(f'事件库 {TODAY} 现有 {len(ev)} 条（盘前+盘中）')

close_sent = [x for x in items if x.get('window') == WIN]
if not close_sent:
    raise SystemExit('⚠️ 盘后窗口 sentiment 为 0 条 → per-item `window` 缺失（§3.88/§3.103），终止以免静默跳过')


def find_news(t):
    return next((y for y in news if y['title'][:60] == t), None)


added = []
for x in close_sent:
    n = find_news(x['title'])
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
        'reason': n.get('brief', ''), 'window': WIN,
        'reference': {'ret_3d': None, 'ret_5d': None, 'ret_10d': None,
                      'max_vol': MAXVOL.get(n.get('volatility'), 4.8),
                      'confidence': n.get('confidence')},
    })
ev.extend(added)
json.dump(ev, open(ev_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(f'盘后 +{len(added)} 条 → {len(ev)} 条（已回写）')

# ---------- ② 回填（全局：所有事件文件中「参考交易日 = 2026-09-28」的留空事件） ----------
# ⚠️ 本档修正：遗留留空分布在 9/25（77 条 A股类）、9/27（24 条，含 2 条美股）、9/28（11 条美股）
#    → 必须跨文件回填，禁止只处理当日文件（原 9/24 脚本只处理本日文件，当日恰好成立）
filled, blank = 0, 0
blank_by_date, blank_by_track = defaultdict(int), defaultdict(int)
fill_by_date, fill_by_track = defaultdict(int), defaultdict(int)
for fp in sorted(glob.glob(os.path.join(EV, 'events-*.json'))):
    e2 = json.load(open(fp, encoding='utf-8'))
    dirty = False
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
            fill_by_date[e['date']] += 1
            fill_by_track[t] += 1
            dirty = True
        else:
            blank += 1
            blank_by_date[e['date']] += 1
            blank_by_track[t] += 1
    if dirty:
        json.dump(e2, open(fp, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(f'全局回填 {filled} 条 按事件日={dict(fill_by_date)} 按赛道={dict(fill_by_track)}')
print(f'仍留空 {blank} 条 按日={dict(blank_by_date)} 按赛道={dict(blank_by_track)}')

# ---------- ③ 全库完整性扫描 ----------
files = sorted(glob.glob(os.path.join(EV, 'events-*.json')))
all_ev = []
for f in files:
    all_ev.extend(json.load(open(f, encoding='utf-8')))
bl = [e for e in all_ev if e.get('reference', {}).get('actual_ret_1d') is None]
n_blank = len(bl)
print(f'\n全库 {len(all_ev)} 条 / {len(files)} 日；留空 {n_blank} 条')
bt = defaultdict(int)
for e in bl:
    bt[e['track']] += 1
print(f'  留空按赛道 {dict(bt)}')
bd = defaultdict(int)
for e in bl:
    bd[e['date']] += 1
print(f'  留空按事件日 {dict(bd)}（参考交易日应全部 = {TODAY}）')
print(f'  当日({TODAY})新增事件 {sum(1 for e in all_ev if e["date"] == TODAY)} 条')

# ---------- ④ 统计 ----------
idx = defaultdict(dict)
with open(os.path.join(HIST, 'indices.csv'), encoding='utf-8-sig') as fh:
    for row in csv.DictReader(fh):
        try:
            idx[row['code']][row['date']] = float(row['close'])
        except Exception:
            pass
track_index = {'A股医药': '399006', '大消费': '000932', '恒生科技': 'HSTECH',
               '美股标普医药': 'XLV', '其他/宽基': '000300', '宏观': '000001'}
import datetime as _dt
for c in set(track_index.values()):
    print(f'  序列长度 {c} = {len(idx.get(c, {}))}')

# §3.111b 守卫口径修正：判据是「**distinct 交易日数**」而非 CSV 行数（CSV 同一日期可有多行：
# 盘中+收盘 note 不同）；distinct < 20 才视为稀疏不可用；并追加日历守卫（见 fwd）
MIN_DAYS = 20
SPARSE = set()
for c in set(track_index.values()):
    nd = len(idx.get(c, {}))
    if nd < MIN_DAYS:
        SPARSE.add(c)
        print(f'  🔴 {c} 仅 {nd} 个 distinct 交易日（< {MIN_DAYS}）→ 多日窗口不可用')
    else:
        print(f'  ✅ {c} {nd} 个 distinct 交易日')


def _cal_days(a, b):
    return (_dt.date.fromisoformat(b) - _dt.date.fromisoformat(a)).days


def fwd(code, d0, n):
    """§3.111b 补强：除「序列长度」外，追加**日历跨度守卫** —— 第 n 个可用观测与事件日的
    日历间隔不得超过 2.2n+3 天，否则视为「稀疏序列伪窗口」（000300 仅 19 行时，
    8/19 事件的「3 日窗口」实测跨越 3 周日历）。"""
    ser = idx.get(code)
    if not ser:
        return None
    ds = sorted(d for d in ser if d >= d0)
    if len(ds) < n + 1:
        return None
    if _cal_days(d0, ds[0]) > 5:          # 起点错位守卫：首个可用观测必须紧邻事件日
        return None
    if _cal_days(ds[0], ds[n]) > 2.2 * n + 3:
        return None
    try:
        return round((ser[ds[n]] / ser[ds[0]] - 1) * 100, 4)
    except Exception:
        return None


win = defaultdict(lambda: defaultdict(list))
win_unavail = defaultdict(lambda: defaultdict(int))
for e in all_ev:
    t = e['track']
    code = track_index.get(t)
    if not code:
        continue
    for n in (3, 5, 10):
        x = fwd(code, e['date'], n)
        if x is not None:
            win[t][n].append(x)
        else:
            win_unavail[t][n] += 1

# 方向验证（有效样本口径：actual_date == TODAY）
tot = pos = neg = 0
p_hit = n_hit = 0
p_tot = n_tot = 0
day_track_pnl = defaultdict(lambda: {'pos': [0, 0], 'neg': [0, 0]})
for e in all_ev:
    r = e.get('reference', {})
    if r.get('actual_date') != TODAY or r.get('actual_ret_1d') is None:
        continue
    v, d = r['actual_ret_1d'], e.get('direction')
    tot += 1
    if d == '利多':
        p_tot += 1
        h = 1 if v > 0 else 0
        p_hit += h
        day_track_pnl[e['track']]['pos'][0] += h
        day_track_pnl[e['track']]['pos'][1] += 1
    elif d == '利空':
        n_tot += 1
        h = 1 if v < 0 else 0
        n_hit += h
        day_track_pnl[e['track']]['neg'][0] += h
        day_track_pnl[e['track']]['neg'][1] += 1
if tot:
    print(f'\n方向验证（有效样本 = actual_date=={TODAY}）: {p_hit + n_hit}/{tot} '
          f'({(p_hit + n_hit) / tot * 100:.1f}%)  利多 {p_hit}/{p_tot}  利空 {n_hit}/{n_tot}')
    for t, v in day_track_pnl.items():
        print(f'    {t:8s} 利多 {v["pos"][0]}/{v["pos"][1]}  利空 {v["neg"][0]}/{v["neg"][1]}')
else:
    print('无有效样本')

# 暴露加权净情绪分（§3.101/§3.104）
pf = json.load(open(os.path.join(HIST, 'portfolio_close_20260928.json'), encoding='utf-8'))
w = {k: v['pct_of_total'] / 100 for k, v in pf['tracks'].items() if k != '现金'}
net = defaultdict(float)
cnt = defaultdict(int)
for e in all_ev:
    if e['date'] != TODAY:
        continue
    s = e.get('strength') or 0
    sg = 1 if e.get('direction') == '利多' else (-1 if e.get('direction') == '利空' else 0)
    net[e['track']] += s * sg
    cnt[e['track']] += 1
print('\n各赛道净情绪分（9/28 全部事件 95 条）:')
weighted = 0.0
for t, v in sorted(net.items(), key=lambda kv: -kv[1]):
    ww = w.get(t)
    print(f"  {t:8s} n={cnt[t]:>2d} 净分={v:+7.1f}  暴露权重={'n/a' if ww is None else f'{ww*100:.2f}%'}"
          f"{'' if ww is None else f'  加权={v*ww:+.2f}'}")
    if ww is not None:
        weighted += v * ww
print(f'  → 名义净分合计 {sum(net.values()):+.1f}；按赛道暴露加权后 {weighted:+.2f}（÷10 = {weighted/10:+.4f}）')

out = {'date': TODAY, 'as_of': '2026-09-28收盘',
       'events_added': len(added), 'events_backfilled': filled, 'blank': blank,
       'blank_by_date': dict(blank_by_date), 'blank_by_track': dict(blank_by_track),
       'total_events': len(all_ev), 'total_days': len(files),
       'direction_check': {'hit': p_hit + n_hit, 'total': tot,
                           'pct': round((p_hit + n_hit) / tot * 100, 1) if tot else None,
                           'pos_hit': p_hit, 'pos_total': p_tot,
                           'neg_hit': n_hit, 'neg_total': n_tot},
       'direction_by_track': {k: {'pos': v['pos'], 'neg': v['neg']} for k, v in day_track_pnl.items()},
       'net_sentiment_by_track': {k: round(v, 2) for k, v in net.items()},
       'net_sentiment_count': dict(cnt),
       'exposure_weighted_net': round(weighted, 2),
       'window_avg': {t: {str(n): (round(sum(v) / len(v), 4) if v else None) for n, v in d.items()}
                      for t, d in win.items()},
       'window_n': {t: {str(n): len(v) for n, v in d.items()} for t, d in win.items()},
       'window_unavailable': {t: {str(n): c for n, c in d.items()} for t, d in win_unavail.items()
                              if sum(d.values())},
       # §3.111b 透明化：稀疏代理指数（distinct 交易日 < MIN_DAYS）的多日窗口样本量须一并披露，
       # 不得以 n 小的读数作方向判断（本次 000300 仅 16 个 distinct 交易日）
       'window_sparse_tracks': sorted(SPARSE),
       'window_min_days': MIN_DAYS,
       'window_note': 'window_avg 已受「序列长度 + 起点错位 + 日历跨度 2.2n+3」三重守卫；稀疏代理指数的窗口 n 须随读数一并披露（§3.111b/§3.111c）',
       }
json.dump(out, open(os.path.join(HIST, f'event_stats_{TODAY.replace("-", "")}_close.json'), 'w',
                    encoding='utf-8'), ensure_ascii=False, indent=1)

print('\n3/5/10 日窗口历史均值（含样本量与窗口不可用计数，§3.111b）:')
for t in sorted(win):
    s = '  '.join(f"{n}日={(sum(win[t][n]) / len(win[t][n])):+.2f}%(n={len(win[t][n])})" if win[t][n] else f'{n}日=n/a'
                  for n in (3, 5, 10))
    u = ' '.join(f'{n}日不可用={win_unavail[t][n]}' for n in (3, 5, 10) if win_unavail[t][n])
    print(f'  {t:8s} {s}   {u}')
print(f'\n已保存 event_stats_{TODAY.replace("-", "")}_close.json')
