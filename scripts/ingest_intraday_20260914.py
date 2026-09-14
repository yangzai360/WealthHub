# -*- coding: utf-8 -*-
"""2026-09-14 盘中档：事件入库 + sentiment 合并 + CSV 增量 + 组合盘中估算"""
import json, csv, os, glob, math, statistics as st

ROOT = "/Users/jieyang/Documents/WealthHub"
os.chdir(ROOT)
news = json.load(open('/tmp/news_intraday_20260914.json'))
hq = json.load(open('/tmp/intraday_hq_20260914.json'))
etf = json.load(open('/tmp/intraday_20260914.json'))['etf']

CAT = {"宏观":"宏观类","A股医药":"政策类","大消费":"行业事件类","美股标普医药":"行业事件类","恒生科技":"行业事件类"}

# ---------- 1. 事件入库 ----------
ev_f = "data/processed/events/events-2026-09-14.json"
events = json.load(open(ev_f, encoding="utf-8"))
start = len(events) + 1
new_events = []
for i, n in enumerate(news):
    eid = f"N20260914-{start+i:03d}"
    new_events.append({
        "id": eid, "date": "2026-09-14", "track": n["track"], "category": CAT.get(n["track"], "行业事件类"),
        "title": n["title"], "summary": n["brief"], "source": "盘中定向抓取(WebSearch)",
        "source_url": n["source_url"], "sentiment": n["sentiment"], "score": n["strength"],
        "strength": n["strength"], "direction": n["direction"], "volatility": n["volatility"],
        "reason": n["brief"], "window": "盘中(07:30-13:30)",
        "reference": {"ret_3d": None, "ret_5d": None, "ret_10d": None, "max_vol": None,
                      "confidence": n["confidence"], "actual_ret_1d": None, "actual_date": None,
                      "ret_1d_ref": None},
    })
events.extend(new_events)
json.dump(events, open(ev_f, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("events", ev_f, len(events), "(+%d)" % len(new_events))

# ---------- 2. sentiment 合并 ----------
sf = "data/processed/news/sentiment-2026-09-14.json"
sd = json.load(open(sf, encoding="utf-8"))
base = len(sd["items"])
merged = list(sd["items"])
for i, n in enumerate(news):
    merged.append({"idx": base+i+1, "title": n["title"], "track": n["track"],
                   "sentiment": n["sentiment"], "strength": n["strength"],
                   "confidence": n["confidence"], "direction": n["direction"],
                   "volatility": n["volatility"], "brief": n["brief"],
                   "source_url": n["source_url"], "window": "盘中(07:30-13:30)"})
sd["items"] = merged
sd["window"] = sd.get("window", "") + " | 盘中(07:30-13:30) 追加 %d 条" % len(news)
json.dump(sd, open(sf, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("sentiment", sf, base, "->", len(merged))

# ---------- 3. CSV 增量（整行判重） ----------
def append_csv(path, header, rows):
    old = []
    if os.path.exists(path):
        with open(path, encoding="utf-8-sig") as f:
            old = list(csv.reader(f))
    existing = set(tuple(r) for r in old)
    added = 0
    with open(path, "a", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        if not old:
            w.writerow(header)
        for r in rows:
            r = [str(x) for x in r]
            if tuple(r) not in existing:
                w.writerow(r); existing.add(tuple(r)); added += 1
    return added

# indices.csv：盘中 A股/港股 行（note 区分盘中）
note_idx = "盘中13:42"
irows = []
for nm, code in [("上证指数","sh000001"),("深证成指","sz399001"),("创业板指","sz399006"),
                 ("沪深300","sh000300"),("中证消费","sh000932")]:
    d = hq[nm]
    irows.append(["index","2026-09-14",nm,code,round(d["cur"],4),round(d["pct"],2),note_idx])
for nm, code in [("恒生指数","HSI"),("恒生科技","HSTECH")]:
    d = hq[nm]
    irows.append(["index","2026-09-14",nm,code,round(d["cur"],3),round(d["pct"],2),note_idx])
n1 = append_csv("data/processed/history/indices.csv",
                ["type","date","name","code","close","pct_change","note"], irows)
print("indices.csv +", n1)

# etf_intraday.csv
NAME = {"513050":"中概互联","159928":"消费ETF添富","512170":"医疗ETF","513180":"恒指科技",
        "159920":"恒生ETF华夏","512880":"证券ETF","512980":"传媒ETF","515180":"100红利","159938":"医药ETF广发"}
erows = []
for c, d in etf.items():
    erows.append(["2026-09-14", c, NAME.get(c, d["name"]), round(d["price"],3),
                  round(d["pct"],2), round(d["amount"]/1e4,1), note_idx])
n2 = append_csv("data/processed/history/etf_intraday.csv",
                ["date","code","name","price","pct","amount_wan","note"], erows)
print("etf_intraday.csv +", n2)

# ---------- 4. 组合盘中估算（基准 = 9/11 盘后归档 373,320.35） ----------
BASE_TOTAL = 373320.35
TRACK = {
    "其他/宽基":      {"v": 94685.88, "pct": None},
    "A股医药":        {"v": 82932.66, "pct": None},
    "大消费":         {"v": 75347.69, "pct": None},
    "美股标普医药":   {"v": 58317.74, "pct": 0.0},
    "恒生科技":       {"v": 32108.23, "pct": None},
    "现金":           {"v": 29212.97, "pct": 0.0},
}
# 代理涨跌幅（盘中实时）
TRACK["A股医药"]["pct"] = 1.70     # 医疗ETF+1.53/医药ETF广发+1.94/医药生物+1.81/创新药+1.94 → 加权约+1.70
TRACK["大消费"]["pct"] = -0.10     # 中证消费-0.24/消费ETF添富0.00/白酒板块+0.13 → 约-0.10
TRACK["恒生科技"]["pct"] = 0.02    # 恒科-0.02/恒指科技-0.18/中概互联-0.10 → 约+0.02
# 其他/宽基：宽基指数-0.69、证券ETF-0.28、传媒ETF-1.22、红利-0.21、恒生ETF华夏+0.34、广联达+0.97、通威+2.26
# 按明细加权（宽基约 40% / 证券保险约 8% / 红利金融地产约 8% / 恒生联接约 5% / 个股约 33% / 清洁能源养老传媒约 6%）
TRACK["其他/宽基"]["pct"] = round(
    0.40*(-0.69) + 0.08*(-0.28) + 0.08*(-0.21) + 0.05*(0.34) +
    0.33*((0.97+2.26)/2) + 0.06*(-0.9), 3)

tot = 0.0
rows = []
for k, d in TRACK.items():
    contrib = d["v"] * d["pct"] / 100
    tot += contrib
    rows.append((k, d["v"], d["v"]/BASE_TOTAL*100, d["pct"], contrib, contrib/BASE_TOTAL*100))
print("\n=== 组合盘中估算 ===")
for r in rows:
    print(f"{r[0]:14s} {r[1]:11,.2f} {r[2]:6.2f}%  pct={r[3]:+.3f}%  贡献={r[4]:+9,.2f}  {r[5]:+.4f}pct")
print(f"合计 {BASE_TOTAL:,.2f} 元  估算 {tot:+,.2f} 元  ({tot/BASE_TOTAL*100:+.3f}%)")

json.dump({"date":"2026-09-14","time":"13:42","base_total":BASE_TOTAL,"est_pnl":round(tot,2),
           "est_pct":round(tot/BASE_TOTAL*100,3),
           "tracks":{r[0]:{"value":round(r[1],2),"weight":round(r[2],2),"pct":r[3],
                           "contrib":round(r[4],2)} for r in rows}},
          open("data/processed/history/portfolio_intraday_20260914.json","w",encoding="utf-8"),
          ensure_ascii=False, indent=1)

# ---------- 5. 全库事件统计 ----------
all_ev = []
for f in sorted(glob.glob("data/processed/events/events-*.json")):
    try: all_ev.extend(json.load(open(f, encoding="utf-8")))
    except Exception as e: print("skip", f, e)
print("\n事件库总量:", len(all_ev))
def stat(track=None, field="actual_ret_1d", sent=None):
    v = [e["reference"][field] for e in all_ev
         if e["reference"].get(field) is not None and (track is None or e["track"] == track)
         and (sent is None or e["sentiment"] == sent)]
    if not v: return None
    return {"n": len(v), "avg": round(sum(v)/len(v), 3), "worst": round(min(v), 2), "best": round(max(v), 2),
            "pos": round(len([x for x in v if x > 0])/len(v), 2)}
summary = {}
for t in ["A股医药","恒生科技","美股标普医药","大消费","宏观","其他/宽基"]:
    summary[t] = {"1d": stat(t), "pos_1d": stat(t, sent="正面"), "neg_1d": stat(t, sent="负面"),
                  "3d": stat(t,"ret_3d"), "5d": stat(t,"ret_5d"), "10d": stat(t,"ret_10d")}
print(json.dumps(summary, ensure_ascii=False, indent=1))

# 方向验证
hit = tot_n = 0
for e in all_ev:
    r = e["reference"].get("actual_ret_1d")
    if r is None or e["direction"] == "中性": continue
    tot_n += 1
    if (e["direction"] == "利多" and r > 0) or (e["direction"] == "利空" and r < 0): hit += 1
print(f"方向验证 {hit}/{tot_n} = {hit/tot_n*100:.1f}%")
json.dump({"date":"2026-09-14","total":len(all_ev),
           "blank":len([e for e in all_ev if e["reference"].get("actual_ret_1d") is None]),
           "by_track":{k:{"n":summary[k]["1d"]["n"],"avg":summary[k]["1d"]["avg"]} for k in summary},
           "dir_verify":{"hit":hit,"total":tot_n},
           "window":{k:{"d3":summary[k]["3d"],"d5":summary[k]["5d"],"d10":summary[k]["10d"]} for k in summary}},
          open("data/processed/history/event_stats_20260914.json","w",encoding="utf-8"),
          ensure_ascii=False, indent=1)
