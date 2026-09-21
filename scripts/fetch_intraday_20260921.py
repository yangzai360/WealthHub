# -*- coding: utf-8 -*-
"""2026-09-21 盘中档：新浪 hq 直连「两次调用拿全」（§3.84 推荐做法）
request1: A股指数 + 港股指数 + 个股
request2: 场内ETF + A股板块指数
⚠️ CSV 追加必须按「末行 EOL 一致」的字节追加（§3.87/§3.89 固化），禁止整表重写
⚠️ §3.92：先打印键空间确认；空值条目显式剔除、pct 保持守卫
"""
import json, csv, os, ssl, urllib.request

ROOT = "/Users/jieyang/Documents/WealthHub"
TODAY = "2026-09-21"
NOTE = "盘中13:47"
ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE


def hq(codes):
    url = "https://hq.sinajs.cn/list=" + ",".join(codes)
    req = urllib.request.Request(url, headers={"Referer": "https://finance.sina.com.cn/",
                                              "User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15, context=ctx) as r:
        return r.read().decode("gbk", "ignore")


def parse(raw):
    res = {}
    for line in raw.strip().split("\n"):
        if "=" not in line: continue
        key = line.split("=")[0].replace("var hq_str_", "").strip()
        val = line.split('="', 1)[1].rstrip('";')
        res[key] = val.split(",")
    return res


def pct(a, b): return (a - b) / b * 100 if b else 0.0


def append_bytes(path, rows, expect_bom=True):
    """按末行 EOL 一致的字节追加（§3.87/§3.88 固化）"""
    d = open(path, 'rb').read()
    if expect_bom:
        assert d[:3] == b'\xef\xbb\xbf', 'BOM 缺失: ' + path
    eol = b'\r\n' if d.endswith(b'\r\n') else b'\n'
    if not d.endswith(eol):
        d = d + eol
    buf = b''.join(','.join(str(x) for x in r).encode('utf-8') + eol for r in rows)
    with open(path, 'ab') as fh:
        fh.write(buf)
    return eol


# ---------- request 1: A股指数 / 港股指数 / 个股 ----------
IDX_A = [("sh000001", "上证指数"), ("sz399001", "深证成指"), ("sz399006", "创业板指"),
         ("sh000300", "沪深300"), ("sh000932", "中证消费"), ("sh000688", "科创50"),
         ("sz399005", "中小100")]
IDX_HK = [("rt_hkHSI", "恒生指数"), ("rt_hkHSTECH", "恒生科技"), ("rt_hkHSCEI", "恒生国企")]
STOCKS = [("sz002410", "广联达"), ("sh600438", "通威股份"), ("sh600519", "贵州茅台")]

raw1 = hq([c for c, _ in IDX_A] + [c for c, _ in IDX_HK] + [c for c, _ in STOCKS])
r1 = parse(raw1)

out = {"indices_a": {}, "indices_hk": {}, "stocks": {}}
print("=== A股指数 ===")
for c, nm in IDX_A:
    f = r1.get(c)
    if not f or len(f) < 6:
        print("MISS", c); continue
    op, pc, cur, hi, lo = float(f[1]), float(f[2]), float(f[3]), float(f[4]), float(f[5])
    if not cur:
        print("EMPTY(剔除)", c); continue
    amt = float(f[9]) / 1e8 if len(f) > 9 and f[9] else 0
    out["indices_a"][nm] = {"cur": cur, "pct": round(pct(cur, pc), 2), "open": op, "prev": pc,
                            "high": hi, "low": lo, "amount_yi": round(amt, 2)}
    print(f"{nm:10s} {cur:>10.2f} {pct(cur,pc):>+7.2f}%  H{hi:.2f} L{lo:.2f} 额{amt:,.1f}亿")

print("=== 港股指数 ===")
for c, nm in IDX_HK:
    f = r1.get(c)
    if not f or len(f) < 9:
        print("MISS", c); continue
    op, pc, hi, lo, cur = float(f[2]), float(f[3]), float(f[4]), float(f[5]), float(f[6])
    if not cur:
        print("EMPTY(剔除)", c); continue
    out["indices_hk"][nm] = {"cur": cur, "pct": round(float(f[8]), 2), "open": op, "prev": pc,
                             "high": hi, "low": lo}
    print(f"{nm:10s} {cur:>10.2f} {float(f[8]):>+7.2f}%  H{hi:.2f} L{lo:.2f}")

print("=== 个股 ===")
for c, nm in STOCKS:
    f = r1.get(c)
    if not f or len(f) < 6:
        print("MISS", c); continue
    op, pc, cur, hi, lo = float(f[1]), float(f[2]), float(f[3]), float(f[4]), float(f[5])
    if not cur:
        print("EMPTY(剔除)", c); continue
    out["stocks"][nm] = {"cur": cur, "pct": round(pct(cur, pc), 2), "open": op, "prev": pc,
                         "high": hi, "low": lo}
    print(f"{nm:10s} {cur:>10.2f} {pct(cur,pc):>+7.2f}%  H{hi:.2f} L{lo:.2f}")

# ---------- request 2: 场内ETF + 板块指数 ----------
ETFS = [("sh513050", "中概互联"), ("sz159928", "消费ETF添富"), ("sh512170", "医疗ETF"),
        ("sh513180", "恒指科技"), ("sz159920", "恒生ETF华夏"), ("sh512880", "证券ETF"),
        ("sh512980", "传媒ETF"), ("sh515180", "100红利"), ("sz159938", "医药ETF广发")]
BOARDS = [("sh000933", "中证医药"), ("sz399989", "中证医疗"), ("sz399997", "中证白酒"),
          ("sh000827", "中证环保"), ("sh000934", "中证金融"), ("sh000913", "300医药"),
          ("sz399975", "证券公司"), ("sh000922", "中证红利")]

raw2 = hq([c for c, _ in ETFS] + [c for c, _ in BOARDS])
r2 = parse(raw2)

print("=== 场内ETF ===")
etf_rows = []
for c, nm in ETFS:
    f = r2.get(c)
    if not f or len(f) < 10:
        print("MISS", c); continue
    op, pc, cur = float(f[1]), float(f[2]), float(f[3])
    if not cur:
        print("EMPTY(剔除)", c); continue
    p = pct(cur, pc)
    amt_wan = float(f[9]) / 1e4 if len(f) > 9 and f[9] else 0
    out.setdefault("etfs", {})[nm] = {"code": c[2:], "cur": round(cur, 3), "pct": round(p, 2),
                                      "amount_wan": round(amt_wan, 1)}
    etf_rows.append([TODAY, c[2:], nm, round(cur, 3), round(p, 2), round(amt_wan, 1), NOTE])
    print(f"{nm:12s} {cur:>7.3f} {p:>+7.2f}%  额 {amt_wan:>12,.0f}万")

print("=== 板块指数 ===")
board_rows = []
for c, nm in BOARDS:
    f = r2.get(c)
    if not f or len(f) < 6:
        print("MISS(剔除)", c); continue
    op, pc, cur, hi, lo = float(f[1]), float(f[2]), float(f[3]), float(f[4]), float(f[5])
    if not cur:          # §3.87 空值守卫
        print("EMPTY(剔除)", c); continue
    p = pct(cur, pc)
    out.setdefault("boards", {})[nm] = {"cur": round(cur, 2), "pct": round(p, 2), "high": hi, "low": lo}
    board_rows.append([TODAY, nm, c, round(cur, 2), round(p, 2), NOTE])
    print(f"{nm:10s} {cur:>10.2f} {p:>+7.2f}%  H{hi:.2f} L{lo:.2f}")

print("\n[键空间自检] indices_a:", list(out["indices_a"]))
print("[键空间自检] boards:", list(out.get("boards", {})))
print("[键空间自检] indices_hk:", list(out["indices_hk"]))

# ---------- 增量写入（字节追加 + 末行 EOL 一致） ----------
p_etf = os.path.join(ROOT, "data/processed/history/etf_intraday.csv")
exist = set()
with open(p_etf, encoding="utf-8-sig") as fh:
    for r in csv.reader(fh):
        if len(r) >= 7: exist.add((r[0], r[1], r[6]))
new_etf = [r for r in etf_rows if (r[0], r[1], r[6]) not in exist]
if new_etf:
    append_bytes(p_etf, new_etf, expect_bom=True)
print(f"etf_intraday.csv +{len(new_etf)} 行")

p_idx = os.path.join(ROOT, "data/processed/history/indices.csv")
exist2 = set()
with open(p_idx, encoding="utf-8-sig") as fh:
    for r in csv.reader(fh):
        if len(r) >= 7: exist2.add((r[1], r[3], r[6]))
new_idx = []
for r in board_rows:
    if (r[0], r[2], r[5]) in exist2: continue
    new_idx.append(["index", r[0], r[1], r[2], r[3], r[4], r[5]])
if new_idx:
    append_bytes(p_idx, new_idx, expect_bom=True)
print(f"indices.csv +{len(new_idx)} 行（板块指数）")

json.dump(out, open(os.path.join(ROOT, "data/processed/history/intraday_hq_20260921.json"), "w",
                    encoding="utf-8"), ensure_ascii=False, indent=1)
print("已保存 intraday_hq_20260921.json")
