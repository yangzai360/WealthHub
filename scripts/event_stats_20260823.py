# -*- coding: utf-8 -*-
"""周日(8/23)盘后档:事件库统计——1日样本按赛道聚合 + 方向验证 + 3/5/10日样本可用性"""
import json, glob, os
from collections import defaultdict

def get_ret(e):
    v = e.get('actual_ret_1d')
    if v is None:
        v = e.get('reference', {}).get('actual_ret_1d')
    return v

# 加载全部事件
all_events = []
for fp in sorted(glob.glob('/Users/jieyang/Documents/WealthHub/data/processed/events/events-*.json')):
    with open(fp, encoding='utf-8') as f:
        all_events.extend(json.load(f))

total = len(all_events)
filled = [e for e in all_events if get_ret(e) is not None]
empty = [e for e in all_events if get_ret(e) is None]
print(f'事件库总条数: {total}')
print(f'已回填 1 日样本: {len(filled)}')
print(f'留空: {len(empty)}')

# 按赛道聚合 1 日样本
by_track = defaultdict(list)
for e in filled:
    by_track[e.get('track', '未知')].append((get_ret(e), e.get('sentiment'), e.get('strength', 50)))

print('\n=== 1 日样本按赛道统计 ===')
for track in ['A股医药', '大消费', '恒生科技', '美股标普医药', '宏观', '其他/宽基']:
    vals = by_track.get(track, [])
    if not vals:
        print(f'{track}: 无样本')
        continue
    rets = [v[0] for v in vals]
    pos = sum(1 for r in rets if r > 0)
    neg = sum(1 for r in rets if r < 0)
    # 强情绪样本
    strong = [v for v in vals if v[2] and v[2] >= 60]
    srets = [v[0] for v in strong]
    print(f'{track}: n={len(rets)} 均值={sum(rets)/len(rets):+.2f}% 最差={min(rets):+.2f}% 最好={max(rets):+.2f}% 正收益占比={pos/len(rets)*100:.0f}% | 强情绪n={len(strong)} 均值={sum(srets)/len(srets):+.2f}%' if srets else f'{track}: n={len(rets)} 均值={sum(rets)/len(rets):+.2f}% 最差={min(rets):+.2f}% 最好={max(rets):+.2f}% 正收益占比={pos/len(rets)*100:.0f}%')

# 方向验证: sentiment vs actual_ret_1d
print('\n=== 方向验证(利多事件→正收益/利空事件→负收益) ===')
ver_total = 0
ver_hit = 0
for track in ['A股医药', '大消费', '恒生科技', '美股标普医药', '宏观']:
    hits = 0
    n = 0
    for e in filled:
        if e.get('track') != track:
            continue
        r = get_ret(e)
        sent = e.get('sentiment')
        if sent in ('正面', '负面') and r is not None:
            n += 1
            if (sent == '正面' and r > 0) or (sent == '负面' and r < 0):
                hits += 1
    if n > 0:
        ver_total += n
        ver_hit += hits
        print(f'{track}: {hits}/{n} ({hits/n*100:.0f}%)')
    else:
        print(f'{track}: 无方向样本')
print(f'全局: {ver_hit}/{ver_total} ({ver_hit/ver_total*100:.0f}%)' if ver_total else '全局: 无样本')

# 3/5/10日样本可用性
from collections import Counter
dates = Counter(e.get('date') for e in all_events)
print(f'\n=== 事件日期分布(最近5天) ===')
for d in sorted(dates)[-5:]:
    print(f'{d}: {dates[d]} 条')

# 输出 stats json
stats = {
    "date": "2026-08-23",
    "total_events": total,
    "filled_1d": len(filled),
    "empty": len(empty),
    "by_track_1d": {
        t: {"n": len(v), "avg": round(sum(x[0] for x in v)/len(v), 2)} if v else {"n": 0, "avg": None}
        for t, v in by_track.items()
    },
    "direction_verification": {"hit": ver_hit, "total": ver_total}
}
os.makedirs('/Users/jieyang/Documents/WealthHub/data/processed/history', exist_ok=True)
with open('/Users/jieyang/Documents/WealthHub/data/processed/history/event_stats_20260823.json', 'w', encoding='utf-8') as f:
    json.dump(stats, f, ensure_ascii=False, indent=1)
print(f'\n统计已写入 data/processed/history/event_stats_20260823.json')
