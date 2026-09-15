# -*- coding: utf-8 -*-
"""2026-09-15 盘中：场内ETF + 板块指数 hq 直连，增量写入 etf_intraday.csv / indices.csv"""
import json, csv, os, ssl, urllib.request

ROOT = "/Users/jieyang/Documents/WealthHub"
TODAY = "2026-09-15"
NOTE = "盘中13:47"
ctx = ssl.create_default_context(); ctx.check_hostname=False; ctx.verify_mode=ssl.CERT_NONE

def hq(codes):
    url = "https://hq.sinajs.cn/list=" + ",".join(codes)
    req = urllib.request.Request(url, headers={"Referer":"https://finance.sina.com.cn/","User-Agent":"Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15, context=ctx) as r:
        return r.read().decode("gbk","ignore")

ETFS = [("sh513050","中概互联"),("sz159928","消费ETF添富"),("sh512170","医疗ETF"),
        ("sh513180","恒指科技"),("sz159920","恒生ETF华夏"),("sh512880","证券ETF"),
        ("sh512980","传媒ETF"),("sh515180","100红利"),("sz159938","医药ETF广发")]
# 板块指数（A股）: sh000933 中证医药 / sz399989 中证医疗 / sz399997 中证白酒 / sh000928 中证能源? -> 用中证800医药? 取常用
BOARDS = [("sh000933","中证医药"),("sz399989","中证医疗"),("sz399997","中证白酒"),("sh000827","中证环保")]

raw = hq([c for c,_ in ETFS] + [c for c,_ in BOARDS])
res = {}
for line in raw.strip().split("\n"):
    if "=" not in line: continue
    key = line.split("=")[0].replace("var hq_str_","").strip()
    val = line.split('="',1)[1].rstrip('";')
    res[key] = val.split(",")

rows = []
for c, nm in ETFS:
    f = res.get(c)
    if not f or len(f) < 10: 
        print("MISS", c); continue
    op, pc, cur = float(f[1]), float(f[2]), float(f[3])
    pct = (cur-pc)/pc*100
    amt_wan = float(f[9])/1e4 if len(f) > 9 and f[9] else 0
    rows.append([TODAY, c[2:], nm, round(cur,3), round(pct,2), round(amt_wan,1), NOTE])
    print(f"{nm:12s} {cur:7.3f} {pct:+6.2f}%  额 {amt_wan:,.0f}万")

print("--- boards ---")
brows = []
for c, nm in BOARDS:
    f = res.get(c)
    if not f or len(f) < 5:
        print("MISS", c); continue
    op, pc, cur, hi, lo = float(f[1]), float(f[2]), float(f[3]), float(f[4]), float(f[5])
    pct = (cur-pc)/pc*100
    print(f"{nm:10s} {cur:10.2f} {pct:+6.2f}%  H{hi:.2f} L{lo:.2f}")
    brows.append([TODAY, nm, c, round(cur,2), round(pct,2), NOTE])

# 增量写入 etf_intraday.csv
p = os.path.join(ROOT, "data/processed/history/etf_intraday.csv")
exist = set()
if os.path.exists(p):
    with open(p, encoding="utf-8-sig") as fh:
        for r in csv.reader(fh):
            if len(r) >= 7: exist.add((r[0], r[1], r[6]))
new = [r for r in rows if (r[0], r[1], r[6]) not in exist]
with open(p, "a", newline="", encoding="utf-8-sig") as fh:
    csv.writer(fh).writerows(new)
print(f"\netf_intraday.csv +{len(new)} 行")

# 板块指数写入 indices.csv (type=index)
p2 = os.path.join(ROOT, "data/processed/history/indices.csv")
exist2 = set()
if os.path.exists(p2):
    with open(p2, encoding="utf-8-sig") as fh:
        for r in csv.reader(fh):
            if len(r) >= 6: exist2.add((r[1], r[3], r[5]))
new2 = []
for r in brows:
    key = (r[0], r[2], r[5])
    if key in exist2: continue
    new2.append(["index", r[0], r[1], r[2], r[3], r[4], r[5]])
with open(p2, "a", newline="", encoding="utf-8-sig") as fh:
    csv.writer(fh).writerows(new2)
print(f"indices.csv +{len(new2)} 行")
json.dump({"etf": rows, "board": brows}, open("/tmp/etf_intraday_20260915.json","w"), ensure_ascii=False, indent=1)
