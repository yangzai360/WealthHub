# -*- coding: utf-8 -*-
"""2026-09-24 盘前档：历史相似事件匹配（品类+赛道+关键词 Jaccard → Top3）→ 3/5/10 日窗口
⚠️ §3.99：fwd() 要求事件日之后有 n+1 个交易日 → 距今不足的样本窗口不可用，必须显式标注，
   禁止以 3 日值静默代替 5/10 日；输出层必须过滤 nan。
⚠️ §3.99：若 Top3 样本全部落在同一趋势段，须标注「趋势段偏差」，均值降级为方向参考。
"""
import json, os, glob, csv, re
from collections import defaultdict, Counter

BASE = '/Users/jieyang/Documents/WealthHub'
EV = os.path.join(BASE, 'data/processed/events')
HIST = os.path.join(BASE, 'data/processed/history')
TODAY = '2026-09-24'
WIN = '盘前(9/23 18:00-9/24 07:30)'
TRACK_INDEX = {'A股医药': '399006', '大消费': '000932', '恒生科技': 'HSTECH',
               '美股标普医药': 'XLV', '其他/宽基': '000300', '宏观': '000001'}

idx = defaultdict(dict)
with open(os.path.join(HIST, 'indices.csv'), encoding='utf-8-sig') as fh:
    for row in csv.DictReader(fh):
        try:
            idx[row['code']][row['date']] = float(row['close'])
        except Exception:
            pass


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


def toks(s):
    s = re.sub(r'[^\u4e00-\u9fffA-Za-z0-9]', '', s or '')
    zh = [s[i:i + 2] for i in range(len(s) - 1) if '\u4e00' <= s[i] <= '\u9fff']
    en = re.findall(r'[A-Za-z0-9]{2,}', s or '')
    return set(zh) | set(e.lower() for e in en)


allv = []
for f in sorted(glob.glob(os.path.join(EV, 'events-*.json'))):
    allv.extend(json.load(open(f, encoding='utf-8')))
sent = json.load(open(os.path.join(BASE, 'data/processed/news/sentiment-2026-09-23.json'), encoding='utf-8'))
news = json.load(open(os.path.join(BASE, 'data/processed/news/news-2026-09-24.json'), encoding='utf-8'))
todays = [n for n in news if n.get('window') == WIN]
print(f'全库 {len(allv)} 条；本档待匹配 {len(todays)} 条（窗口 {WIN}）')

hist = [e for e in allv if e['date'] < TODAY]
res = {}
track_tops = defaultdict(list)
for n in todays:
    tk = toks(n['title'] + (n.get('summary') or ''))
    cand = []
    for e in hist:
        if e['track'] != n['track']:
            continue
        j = len(tk & toks(e['title'] + (e.get('summary') or ''))) / max(len(tk | toks(e['title'] + (e.get('summary') or ''))), 1)
        cand.append((j, e))
    cand.sort(key=lambda x: -x[0])
    tops = []
    code = TRACK_INDEX.get(n['track'])
    for j, e in cand[:3]:
        w = {str(k): fwd(code, e['date'], k) for k in (3, 5, 10)} if code else {'3': None, '5': None, '10': None}
        tops.append({'date': e['date'], 'title': e['title'][:70], 'jaccard': round(j, 4),
                     'sentiment': e.get('sentiment'), 'direction': e.get('direction'),
                     'score': e.get('score'),
                     'actual_ret_1d': e.get('reference', {}).get('actual_ret_1d'),
                     'fwd': w})
        track_tops[n['track']].append({'date': e['date'], 'fwd': w, 'jaccard': round(j, 4)})
    res[n['title'][:60]] = {'track': n['track'], 'category': n.get('category'), 'tops': tops}

# ---- 赛道聚合（Top3 × 本档条数）----
agg = {}
for t in sorted(track_tops):
    arr = track_tops[t]
    row = {'n_items': len([n for n in todays if n['track'] == t]), 'n_matched': len(arr),
           'mean_conf': None}
    for k in ('3', '5', '10'):
        vs = [a['fwd'][k] for a in arr if a['fwd'].get(k) is not None]
        unavail = len([a for a in arr if a['fwd'].get(k) is None])
        row[f'{k}d_mean'] = round(sum(vs) / len(vs), 2) if vs else None
        row[f'{k}d_n'] = len(vs)
        row[f'{k}d_unavailable'] = unavail
    jac = [a['jaccard'] for a in arr]
    row['mean_jaccard'] = round(sum(jac) / len(jac), 3) if jac else None
    # 趋势段偏差判据：Top3 样本日期的跨度
    ds = sorted(set(a['date'] for a in arr))
    row['sample_dates'] = ds[-6:]
    row['trend_bias'] = bool(ds) and (ds[-1] >= '2026-08-20' and ds[0] >= '2026-08-15')
    agg[t] = row

print('\n=== 赛道聚合（Top3 相似事件 × 3/5/10 日窗口）===')
for t, r in agg.items():
    print(f"  {t:8s} n={r['n_items']} 匹配{r['n_matched']} 置信度(Jaccard)={r['mean_jaccard']}"
          f" | 3日={r['3d_mean']}(n={r['3d_n']},缺{r['3d_unavailable']})"
          f" | 5日={r['5d_mean']}(n={r['5d_n']},缺{r['5d_unavailable']})"
          f" | 10日={r['10d_mean']}(n={r['10d_n']},缺{r['10d_unavailable']})"
          f" | 趋势段偏差={'是' if r['trend_bias'] else '否'}")

out = {'date': TODAY, 'window': WIN, 'n_items': len(todays),
       'track_agg': agg, 'per_item': res,
       'track_index_map': TRACK_INDEX,
       'note': ('A股医药 3/5/10 日窗口用 399006 代理（§3.90）；宏观窗口用 000001；'
                '窗口不可用时返回 None 并在 agg 中以 `*d_unavailable` 计数，禁止以 3 日值静默代替（§3.99）')}
json.dump(out, open(os.path.join(HIST, 'history_ref_20260924_preopen.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
print('\nSAVED history_ref_20260924_preopen.json')

print('\n=== 逐条 Top3（前 6 条展示）===')
for k, v in list(res.items())[:6]:
    print(f"\n[{v['track']}] {k}")
    for x in v['tops']:
        print(f"   {x['date']} J={x['jaccard']} 1d={x['actual_ret_1d']} 3/5/10={x['fwd']['3']}/{x['fwd']['5']}/{x['fwd']['10']} | {x['title'][:52]}")
