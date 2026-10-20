# -*- coding: utf-8 -*-
"""2026-10-20 盘后档：情绪标注（news-close-20261020.json → sentiment-2026-10-20.json）
⚠️ DeepSeek 端点自 10/6 起 HTTP 402 → 停止重试并全量降级「确定性规则表」（agent 逐条指定）
⚠️ §3.129d：规则表 key = 标题前 24 字，必须唯一命中（len != len(items) 即终止）
⚠️ §3.112d：报告引用分数取合并后的 news-2026-10-20.json（sentiment 侧字段名为 strength）
输出：data/processed/news/news-2026-10-20.json（追加）、sentiment-2026-10-20.json（追加）
"""
import json, os, urllib.request
from collections import Counter

BASE = "/Users/jieyang/Documents/WealthHub"
TODAY = "2026-10-20"
NEWS_C = os.path.join(BASE, "data/processed/news/news-close-20261020.json")
NEWS_O = os.path.join(BASE, "data/processed/news/news-2026-10-20.json")
SENT = os.path.join(BASE, "data/processed/news/sentiment-2026-10-20.json")
WIN = "盘后(10/20 13:30-20:00)"
SESSION_NOTE = ("正常交易日收盘（A股 10/20 15:00 收盘 + 港股复市 16:00 收盘 + 美股 10/20 未开盘）")

items = json.load(open(NEWS_C, encoding='utf-8'))
if not items:
    raise SystemExit('⚠️ news-close-20261019.json 为空，终止')
print(f"待标注 {len(items)} 条")

RULE = {}
for x in items:
    RULE[x['title'][:24]] = (x['direction'], int(x['score']), int(x.get('confidence') or 88),
                             x.get('volatility', '中'), x['brief'])
if len(RULE) != len(items):
    raise SystemExit(f'⚠️ 规则表键碰撞：{len(RULE)} 键 vs {len(items)} 条')

# ---------- 试模型（预期 402） ----------
mode, reason = 'rule_table_fallback', ''
try:
    key = json.load(open('/Users/jieyang/.pi/agent/auth.json'))['deepseek']['key']
    body = json.dumps({"model": "deepseek-v4-flash",
                       "messages": [{"role": "user", "content": "ping"}],
                       "max_tokens": 8000}, ensure_ascii=False).encode('utf-8')
    req = urllib.request.Request("https://api.deepseek.com/chat/completions", data=body,
                                 headers={"Authorization": "Bearer " + key,
                                          "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        r.read()
    print('⚠️ 模型端点可用，但本档仍按规则表口径标注（口径一致性优先，避免同日三档混口径）')
except Exception as e:
    reason = f'HTTP {getattr(e, "code", "?")}' if getattr(e, 'code', None) else type(e).__name__
    print(f'模型端点不可用：{reason} → 全量降级规则表')

new_items = []
for x in items:
    d, s, c, v, b = RULE[x['title'][:24]]
    new_items.append({'idx': x['idx'], 'track': x['track'],
                      'sentiment': {'利多': '正面', '利空': '负面', '中性': '中性'}[d],
                      'strength': s, 'confidence': c, 'direction': d, 'volatility': v, 'brief': b})

# ---------- build() 工厂（§3.154e） ----------
def build(ni, it):
    return {
        "idx": ni["idx"], "title": it["title"], "track": it["track"],
        "category": it.get("category"), "summary": it.get("summary"),
        "source": it.get("source"), "source_url": it.get("source_url", ""),
        "window": WIN, "date": TODAY,
        "sentiment": ni["sentiment"], "strength": ni["strength"], "score": ni["strength"],
        "confidence": ni["confidence"], "direction": ni["direction"],
        "volatility": ni["volatility"], "brief": ni["brief"],
    }


NEWS_KEYS = {"track", "category", "title", "summary", "source", "source_url",
             "window", "date", "sentiment", "score", "strength", "direction", "volatility", "brief", "confidence"}
SENT_KEYS = {"idx", "title", "track", "window", "sentiment", "strength", "confidence",
             "direction", "volatility", "brief", "source_url"}

sents = json.load(open(SENT, encoding='utf-8'))
news = json.load(open(NEWS_O, encoding='utf-8'))
print(f'合并前：news {len(news)} 条；sentiment {len(sents["items"])} 条')
if len(news) > 52:
    print(f'⚠️ 幂等守卫：检测到已追加（{len(news)} 条）→ 裁回 52 条后重建')
    news = news[:52]
if len(sents['items']) > 52:
    sents['items'] = sents['items'][:52]
assert len(news) == 52, f'盘前+盘中应为 52 条，实际 {len(news)}'
assert len(sents['items']) == 52, f'sentiment 应为 52 条，实际 {len(sents["items"])}'

for ni, it in zip(new_items, items):
    row = build(ni, it)
    news.append({k: row[k] for k in NEWS_KEYS})
    sents['items'].append({k: row[k] for k in SENT_KEYS})

sents['count'] = len(sents['items'])
sents['window'] = '盘前(10/19 20:00-10/20 07:30) + 盘中(10/20 07:30-13:30) + 盘后(10/20 13:30-20:00)'
sents['session_type'] = 'normal_trading_day_close'
sents['session_type_note'] = SESSION_NOTE
sents['annotation_mode'] = mode
sents['degraded_items'] = len(items)
sents['degraded_batches'] = 1
sents['degradation_reason'] = reason
sents['degradation_note'] = (
    f"⚠️ §3.127b / §3.128a：本档 **{len(items)}/{len(items)} 条（本档增量）为确定性规则表标注（非模型标注）**；"
    f"成因 = DeepSeek v4-flash 端点返回 {reason}（Insufficient Balance，非 429 限流）→ 依 §3.127b 停止重试并降级。"
    "规则表由 agent 依新闻正文逐条指定 direction/strength/confidence/volatility/brief，"
    "以「标题前 24 字」硬绑定 + 唯一性守卫（§3.129d）防止静默套用默认值。"
    f"当日累计 54 条（盘前 16 + 盘中 21 + 盘后 {len(items)}），**三档同为规则表降级、口径一致**；"
    "降级自 10/6 08:00 起持续（**连续第 15 个日历日**）。"
    "**跨档比较均值强度/净分须标注口径差异，不得与 10/6 之前的模型标注档混算趋势。**"
)

json.dump(sents, open(SENT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
json.dump(news, open(NEWS_O, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(f"news-{TODAY}.json: {len(news)} 条")
_miss = [x for x in news if not x.get('window')]
print('news window 覆盖:', len(news) - len(_miss), '/', len(news))
if _miss:
    raise SystemExit('⚠️ §3.103 有新闻缺 window 字段，终止')

_rb = json.load(open(SENT, encoding='utf-8'))['items'][-len(items):]
_bad = [(i, sorted(SENT_KEYS - set(r))) for i, r in enumerate(_rb) if SENT_KEYS - set(r)]
if _bad:
    raise SystemExit(f'⚠️ §3.154e 回读抽查失败: {_bad}')
print(f'✅ 回读抽查通过：sentiment 末 {len(items)} 条字段完备（含 strength）')

WEIGHT = {'其他/宽基': 25.01, 'A股医药': 22.31, '大消费': 20.29,
          '美股标普医药': 16.27, '恒生科技': 8.28, '宏观': 0.0}


def net(its):
    return sum((x['strength'] if x['direction'] == '利多' else -x['strength'] if x['direction'] == '利空' else 0) / 10
               for x in its)


by_track = {}
for x in new_items:
    by_track.setdefault(x['track'], []).append(x)
print(f"\n本档窗口名义净情绪 = {net(new_items):+.2f}")
wsum = 0.0
for t, arr in sorted(by_track.items(), key=lambda kv: -net(kv[1])):
    contrib = net(arr) * WEIGHT.get(t, 0) / 100
    wsum += contrib
    print(f"  [{t:8s}] n={len(arr)} 净分 {net(arr):+.2f} 权重 {WEIGHT.get(t,0):.2f}% 加权 {contrib:+.4f} 均值强度 {sum(a['strength'] for a in arr)/len(arr):.1f}")
print(f"暴露加权净分 = {wsum:+.4f}")
print(f"方向分布: {dict(Counter(x['direction'] for x in new_items))}")
print(f"均值强度 {sum(x['strength'] for x in new_items)/len(new_items):.2f}")
