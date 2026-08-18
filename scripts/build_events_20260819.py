# -*- coding: utf-8 -*-
"""盘前档 2026-08-19 事件库构建：从 sentiment 转 events（含 id/reference/strength）+ 历史样本统计 + 回填 8/18 遗留美股医药事件"""
import json, os, sys, glob

BASE = '/Users/jieyang/Documents/WealthHub'
NEWS_DIR = os.path.join(BASE, 'data/processed/news')
EVT_DIR = os.path.join(BASE, 'data/processed/events')
DATE = '2026-08-19'

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

# ---------- 回填 8/18 遗留美股标普医药 3 条（用 XLV/IYH 8/18 收盘） ----------
# 8/18 盘后遗留：美股标普医药 3 条 actual_ret_1d 留空待 8/19 盘前回填
# IYH 8/18 收盘 71.67（+1.52%），XLV 新浪源滞后至 8/17（167.05 -0.19%）——取最新可用者 IYH
FILL_RET = 1.52  # IYH 8/18 +1.52%（XLV 滞后用 IYH 代理 §3.18）
FILL_REF = 'IYH 8/18 收盘(+1.52%)，XLV 新浪源滞后'
ev18_path = os.path.join(EVT_DIR, 'events-2026-08-18.json')
with open(ev18_path, encoding='utf-8') as f:
    ev18 = json.load(f)
filled = 0
for e in ev18:
    if e.get('track') == '美股标普医药' and e.get('reference', {}).get('actual_ret_1d') is None:
        e.setdefault('reference', {})['actual_ret_1d'] = FILL_RET
        e['reference']['actual_date'] = '2026-08-18'
        e['reference']['ret_1d_ref'] = FILL_REF
        e['reference']['note'] = '盘前档回填'
        filled += 1
        print(f'  回填 {e["id"]}: {e["title"][:30]} -> {FILL_RET}%')
with open(ev18_path, 'w', encoding='utf-8') as f:
    json.dump(ev18, f, ensure_ascii=False, indent=1)
print(f'events-2026-08-18.json 回填美股标普医药 {filled} 条')

# ---------- 历史事件库统计（1日样本，截至 8/18） ----------
all_ev = []
for p in sorted(glob.glob(os.path.join(EVT_DIR, 'events-*.json'))):
    if DATE in p:
        continue
    with open(p, encoding='utf-8') as f:
        all_ev.extend(json.load(f))

print(f'\n事件库累计（不含今日）: {len(all_ev)} 条')
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
        print(f'  {track}: 样本{len(rets)}条 1日均值 {avg:+.2f}% 最差 {worst:+.2f}% 正收益占比 {pos:.0f}%')
    else:
        print(f'  {track}: 样本{len(evs)}条 无回填')

# 情绪分布
pos = sum(1 for n in news if n['sentiment'] == '正面')
neg = sum(1 for n in news if n['sentiment'] == '负面')
neu = sum(1 for n in news if n['sentiment'] == '中性')
strengths = [n['strength'] for n in news]
print(f'\n今日情绪分布: {pos}利多 {neu}中性 {neg}利空，均值强度 {sum(strengths)/len(strengths):.0f}')
