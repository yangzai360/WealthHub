# -*- coding: utf-8 -*-
"""2026-09-27 周日盘后档：W39（9/21-9/27）周度统计 + 9/28 复市待消化测算
- 链路日收益样本：日期从【文件名】推导（§3.91）；起点 8/6 手工补入；同日期 _fix 优先（§3.98）
- 赛道周度贡献：逐日 portfolio_close_*.json 的 tracks[k]['pnl'] 累加（全部用 _fix 口径）
- 待消化：港股 9/25 静态测算（三段法，§3.108）+ QDII 预告（IYH × 0.72，§3.106）
"""
import json, os, csv, glob, re
from collections import defaultdict

BASE = '/Users/jieyang/Documents/WealthHub'
HIST = os.path.join(BASE, 'data/processed/history')
W_START, W_END = '2026-09-21', '2026-09-27'
TODAY = '2026-09-27'

# ---------- 1. 链路序列 ----------
seen = {}
for p in glob.glob(os.path.join(HIST, 'portfolio_close_*.json')):
    m = re.search(r'(\d{8})', os.path.basename(p))
    if not m:
        continue
    ds = m.group(1); date = f'{ds[:4]}-{ds[4:6]}-{ds[6:]}'
    d = json.load(open(p, encoding='utf-8'))
    pct = d.get('est_total_pct_raw')
    if pct is None:
        pct = d.get('est_total_pct')
    if pct is None:
        continue
    isfix = '_fix' in os.path.basename(p)
    if date not in seen or (isfix and not seen[date][1]):
        seen[date] = (float(pct), isfix, d.get('total_mv'), os.path.basename(p))
seq = sorted((d, v[0], v[2], v[3]) for d, v in seen.items())
seq.insert(0, ('2026-08-06', -0.68, None, 'manual-seed'))

wk = [s for s in seq if W_START <= s[0] <= W_END]
print('【W39 日收益序列】')
for d, p, mv, src in wk:
    print(f'  {d}  {p:+.4f}%  mv={mv if mv is None else format(mv, ",.2f")}  ({src})')
cum = 1.0
for _, p, _, _ in wk:
    cum *= (1 + p / 100)
print(f'  → W39 累计 {(cum - 1) * 100:+.2f}%（{len(wk)} 个定价日；9/25 为「混合档」未定价，不计入）')

print('\n【链路累计】')
c = 1.0
for _, p, _, _ in seq:
    c *= (1 + p / 100)
print(f'  {" → ".join(f"{d[5:]} {p:+.2f}%" for d, p, _, _ in seq[-6:])}')
print(f'  8/6 起 {len(seq)} 日累计 {(c - 1) * 100:+.2f}%')

# ---------- 2. 赛道周度贡献 ----------
print('\n【W39 赛道周度贡献（逐日 tracks.pnl 累加，全部 _fix 口径）】')
day_files = {}
for p in glob.glob(os.path.join(HIST, 'portfolio_close_*.json')):
    m = re.search(r'(\d{8})', os.path.basename(p))
    if not m:
        continue
    ds = m.group(1); date = f'{ds[:4]}-{ds[4:6]}-{ds[6:]}'
    isfix = '_fix' in os.path.basename(p)
    if date not in day_files or (isfix and not day_files[date][1]):
        day_files[date] = (p, isfix)

track_week = defaultdict(lambda: defaultdict(float))
for d, _, _, _ in wk:
    if d not in day_files:
        continue
    dd = json.load(open(day_files[d][0], encoding='utf-8'))
    for k, v in dd['tracks'].items():
        track_week[k][d] = v['pnl']

for k in sorted(track_week, key=lambda x: -abs(sum(track_week[x].values()))):
    tot = sum(track_week[k].values())
    daily = ' / '.join(f"{d[5:]} {track_week[k].get(d, 0):+,.0f}" for d, _, _, _ in wk)
    print(f'  {k:12s} 周贡献 {tot:>+11,.2f} 元 | {daily}')

tot_pnl = sum(sum(v.values()) for v in track_week.values())
print(f'  → 合计 {tot_pnl:+,.2f} 元')

# ---------- 3. 指数窗口 ----------
rows = list(csv.reader(open(os.path.join(HIST, 'indices.csv'), encoding='utf-8-sig')))[1:]
by, usby = defaultdict(list), defaultdict(list)
for r in rows:
    if len(r) < 6 or not r[4]:
        continue
    try:
        if r[0] == 'index':
            by[r[3]].append((r[1], float(r[4])))
        elif r[0] == 'us_index':
            usby[r[3]].append((r[1], float(r[4])))
    except Exception:
        pass

print('\n【W39 周内指数变化】')
for code, name, end in [('000001', '上证指数', '2026-09-24'), ('399006', '创业板指', '2026-09-24'),
                        ('000300', '沪深300', '2026-09-24'), ('000932', '中证消费', '2026-09-24'),
                        ('000933', '中证医药', '2026-09-24'), ('399989', '中证医疗', '2026-09-24'),
                        ('399997', '中证白酒', '2026-09-24'), ('HSTECH', '恒生科技', '2026-09-25'),
                        ('HSI', '恒生指数', '2026-09-25'), ('HSCEI', '恒生国企', '2026-09-25')]:
    v = sorted({d: cc for d, cc in by.get(code, [])}.items())
    a = [x for x in v if x[0] <= '2026-09-18']
    b = [x for x in v if x[0] <= end]
    if a and b:
        print(f'  {name:10s} {a[-1][1]:>10.2f} ({a[-1][0]}) → {b[-1][1]:>10.2f} ({b[-1][0]})  {(b[-1][1] / a[-1][1] - 1) * 100:+.2f}%')
    else:
        print(f'  {name:10s} 样本不足')
print('  --- 美股（W39 可比区间：9/18 → 9/25） ---')
for code in ['XLV', 'IYH', 'QQQ', 'DIA', 'SPY']:
    v = sorted({d: cc for d, cc in usby.get(code, [])}.items())
    a = [x for x in v if x[0] <= '2026-09-18']
    b = [x for x in v if x[0] <= '2026-09-25']
    if a and b:
        print(f'  {code:10s} {a[-1][1]:>10.2f} ({a[-1][0]}) → {b[-1][1]:>10.2f} ({b[-1][0]})  {(b[-1][1] / a[-1][1] - 1) * 100:+.2f}%')

# ---------- 4. 9/28 复市待消化测算 ----------
pend = json.load(open(os.path.join(HIST, 'portfolio_pending_20260925.json'), encoding='utf-8'))
hk = pend['pending_consume']
qd = pend['qdii_forecast']
close = json.load(open(os.path.join(HIST, 'close_20260927.json'), encoding='utf-8'))
us = {x['code']: x for x in close['us']}
iyh_25 = us['IYH']['pct_change']
mv_usmed = pend['tracks']['美股标普医药']
qd25_pct = round(iyh_25 * 0.72, 4)
qd25_pnl = round(mv_usmed * qd25_pct / 100, 2)
qd25_hi = round(mv_usmed * iyh_25 * 1.25 / 100, 2)

net_mid = hk['mid_pnl'] + qd['pnl'] + qd25_pnl
net_low = hk['low_pnl'] + 0 + 0
net_high = hk['high_pnl'] + qd['range_hi_pnl'] + qd25_hi

print('\n【9/28 复市待消化测算】')
print(f"  港股 9/25 静态测算（三段法）: 中枢 {hk['mid_pnl']:+,.2f} 元 ({hk['mid_pct']:+.4f}%)  "
      f"区间 {hk['low_pnl']:+,.2f} ~ {hk['high_pnl']:+,.2f}")
for k, v in hk['components'].items():
    print(f"      {k:16s} {v:+,.2f}")
print(f"  QDII 预告 ①（US 9/24 IYH {qd['iyh_pct']:+.2f}% × 0.72 = {qd['pct']:+.2f}%）: "
      f"{qd['pnl']:+,.2f} 元（0 ~ {qd['range_hi_pnl']:+,.2f}）")
print(f"  QDII 预告 ②（US 9/25 IYH {iyh_25:+.2f}% × 0.72 = {qd25_pct:+.4f}%）: "
      f"{qd25_pnl:+,.2f} 元（0 ~ {qd25_hi:+,.2f}）")
print(f"  → 净值口径合计: {net_mid:+,.2f} 元（{net_mid / pend['base_total'] * 100:+.4f}%）"
      f"  区间 {net_low:+,.2f} ~ {net_high:+,.2f}")
print(f"  ⚠️ 区间跨越 0 → 「方向不可判定」（§3.108 条款 5）")

out = {'date': TODAY, 'base_total': pend['base_total'],
       'w39': {'cum_pct': round((cum - 1) * 100, 2), 'days': len(wk),
               'daily': [[d, round(p, 4)] for d, p, _, _ in wk]},
       'chain_cum_pct': round((c - 1) * 100, 2), 'chain_days': len(seq),
       'track_week_pnl': {k: round(sum(v.values()), 2) for k, v in track_week.items()},
       'track_week_daily': {k: {d: round(x, 2) for d, x in v.items()} for k, v in track_week.items()},
       'pending_20260928': {
           'hk_consume': hk, 'qdii_us0924': qd,
           'qdii_us0925': {'iyh_pct': iyh_25, 'coef': 0.72, 'pct': qd25_pct,
                           'mv': mv_usmed, 'pnl': qd25_pnl, 'range_hi_pnl': qd25_hi},
           'net_mid_pnl': round(net_mid, 2), 'net_mid_pct': round(net_mid / pend['base_total'] * 100, 4),
           'net_low_pnl': round(net_low, 2), 'net_high_pnl': round(net_high, 2),
           'direction_determinable': not (net_low < 0 < net_high)},
       'note': '静态测算只可给区间上下界，不得作方向判断（§3.108）；QDII 兑付时点 T+1~T+2 错位，不得假定同日全额对冲'}
json.dump(out, open(os.path.join(HIST, 'weekly_stats_20260927.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('\nSAVED weekly_stats_20260927.json')
