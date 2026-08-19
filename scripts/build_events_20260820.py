# -*- coding: utf-8 -*-
"""盘前档 2026-08-20 事件库构建：从 sentiment 转 events（含 id/reference/strength）+ 回填 8/19 遗留事件 + 历史样本统计"""
import json, os, glob

BASE = '/Users/jieyang/Documents/WealthHub'
NEWS_DIR = os.path.join(BASE, 'data/processed/news')
EVT_DIR = os.path.join(BASE, 'data/processed/events')
DATE = '2026-08-20'

with open(os.path.join(NEWS_DIR, f'news-{DATE}.json'), encoding='utf-8') as f:
    news = json.load(f)

# sentiment 文件（与 news 同构，独立归档）
sent_path = os.path.join(NEWS_DIR, f'sentiment-{DATE}.json')
with open(sent_path, 'w', encoding='utf-8') as f:
    json.dump(news, f, ensure_ascii=False, indent=1)
print(f'sentiment-{DATE}.json 写入 {len(news)} 条')

# 事件库
events = []
for i, n in enumerate(news, 1):
    ev = {
        'id': f'N{DATE.replace("-", "")}-{i:03d}',
        'date': DATE,
        'track': n['track'],
        'category': n['category'],
        'title': n['title'],
        'summary': n['summary'],
        'source': n['source'],
        'source_url': n['source_url'],
        'sentiment': n['sentiment'],
        'score': n['score'],
        'strength': n['strength'],
        'direction': n['direction'],
        'volatility': n['volatility'],
        'reason': n['reason'],
        'reference': {'ret_3d': None, 'ret_5d': None, 'ret_10d': None, 'actual_ret_1d': None, 'note': '盘前事件，actual_ret_1d 待今日收盘回填'},
    }
    events.append(ev)

ev_path = os.path.join(EVT_DIR, f'events-{DATE}.json')
with open(ev_path, 'w', encoding='utf-8') as f:
    json.dump(events, f, ensure_ascii=False, indent=1)
print(f'events-{DATE}.json 写入 {len(events)} 条')

# ---------- 回填 8/19 遗留事件（8/19 盘后追加 7 条 + 盘前美股医药 2 条，用 8/19 实际收盘） ----------
ev19_path = os.path.join(EVT_DIR, 'events-2026-08-19.json')
with open(ev19_path, encoding='utf-8') as f:
    ev19 = json.load(f)

# 8/19 各赛道收盘口径（indices/ETF/净值交叉确认）
FILLS = {
    'N20260819-014': ('美股标普医药', 3.51, 'XLV 8/19 收盘(+3.51%)，IYH +3.71%'),
    'N20260819-015': ('美股标普医药', 3.51, 'XLV 8/19 收盘(+3.51%)，IYH +3.71%'),
    'N20260819-025': ('宏观', -2.40, '上证 8/19 收盘 -2.40%'),
    'N20260819-026': ('恒生科技', -1.21, '恒科 8/19 收盘 -1.21%'),
    'N20260819-027': ('恒生科技', -1.21, '恒科 8/19 收盘 -1.21%'),
    'N20260819-028': ('A股医药', -2.55, '医疗ETF 512170 8/19 收盘 -2.55%'),
    'N20260819-029': ('大消费', -1.08, '中证消费 8/19 收盘 -1.08%'),
    'N20260819-030': ('A股医药', -2.55, '医疗ETF 512170 8/19 收盘 -2.55%（赛道口径）'),
    # N20260819-031（美联储纪要）影响在 8/20，留空待 8/20 盘后回填
}
filled = 0
for e in ev19:
    fid = e['id']
    if fid in FILLS:
        track, ret, ref = FILLS[fid]
        if e.get('reference', {}).get('actual_ret_1d') is None:
            e.setdefault('reference', {})['actual_ret_1d'] = ret
            e['reference']['actual_date'] = '2026-08-19'
            e['reference']['ret_1d_ref'] = ref
            e['reference']['note'] = '盘前档回填'
            filled += 1
            print(f'  回填 {fid} [{track}]: {ret}% ({ref})')
with open(ev19_path, 'w', encoding='utf-8') as f:
    json.dump(ev19, f, ensure_ascii=False, indent=1)
print(f'events-2026-08-19.json 回填 {filled} 条（N20260819-031 美联储纪要留空待 8/20 收盘）')

# ---------- 历史事件库统计（1日样本，截至 8/19） ----------
all_ev = []
for p in sorted(glob.glob(os.path.join(EVT_DIR, 'events-*.json'))):
    if DATE in p:
        continue
    with open(p, encoding='utf-8') as f:
        all_ev.extend(json.load(f))

print(f'\n事件库累计（不含今日）: {len(all_ev)} 条')
stats = {}
for track in ['A股医药', '大消费', '恒生科技', '美股标普医药', '宏观']:
    evs = [e for e in all_ev if e.get('track') == track]
    rets = []
    for e in evs:
        v = e.get('actual_ret_1d')
        if v is None:
            v = e.get('reference', {}).get('actual_ret_1d')
        if v is not None:
            try:
                rets.append(float(v))
            except:
                pass
    if rets:
        avg = sum(rets) / len(rets)
        worst = min(rets)
        pos = sum(1 for r in rets if r > 0) / len(rets) * 100
        stats[track] = {'n': len(rets), 'avg': round(avg, 2), 'worst': round(worst, 2), 'pos': round(pos, 0)}
        print(f'  {track}: 样本{len(rets)}条 1日均值 {avg:+.2f}% 最差 {worst:+.2f}% 正收益占比 {pos:.0f}%')
    else:
        print(f'  {track}: 样本{len(evs)}条 无回填')

# 情绪分布
pos = sum(1 for n in news if n['sentiment'] == '正面')
neg = sum(1 for n in news if n['sentiment'] == '负面')
neu = sum(1 for n in news if n['sentiment'] == '中性')
strengths = [n['strength'] for n in news]
print(f'\n今日情绪分布: {pos}利多 {neu}中性 {neg}利空，均值强度 {sum(strengths)/len(strengths):.0f}')

with open(os.path.join(BASE, 'data/processed/history/event_stats_20260820.json'), 'w', encoding='utf-8') as f:
    json.dump({'stats': stats, 'n_news': len(news), 'pos': pos, 'neu': neu, 'neg': neg,
               'avg_strength': round(sum(strengths)/len(strengths), 1)}, f, ensure_ascii=False, indent=1)
print('已保存 event_stats_20260820.json')
