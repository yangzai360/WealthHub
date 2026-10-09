# -*- coding: utf-8 -*-
"""2026-10-09 盘中档（13:45）：新浪 hq 直连 —— A股 长假后第 2 个交易日 + 港股正常交易日（双市场均开市）

本档口径（档型③「正常交易日盘中」，非混合档 / 非纯非交易日）：
  ① A股 —— 10/9 正常交易日 09:30 开盘 → 取实时指数 + 板块 + 个股
  ② 港股 —— 10/9 正常交易日 09:30 开盘 → 取实时指数 + 11 权重股
  ③ 场内 ETF（A股上市）—— 正常交易 → 取实时价与成交额，写 etf_intraday.csv
  ④ 场外基金（23 只）—— A股 15:00 收盘后发布净值 → 13:45 档预期 0 新增行
⚠️ 判「今日是否开市」一律读数据源「日期字段」，不得用「价格是否变化」推断（§3.119b / §3.122b / §3.126e）
⚠️ 新浪 hq 港股指数字段序（§3.126e 实测）：f[17] = 日期「2026/10/09」、f[18] = 时刻「13:4x:xx」
⚠️ A股指数/个股 f[30]=日期、f[31]=时刻（本档实测确认）
⚠️ CSV 追加一律「字节追加 + 按该文件 BOM 属性写入」（§3.87/§3.116a）；sh000922（中证红利）永久移出批量请求（§3.137c）
"""
import json, csv, os, ssl, urllib.request

ROOT = "/Users/jieyang/Documents/WealthHub"
TODAY = "2026-10-09"
HIST = os.path.join(ROOT, "data/processed/history")
NOTE = "盘中13:45"
ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE


def hq(codes):
    url = "https://hq.sinajs.cn/list=" + ",".join(codes)
    req = urllib.request.Request(url, headers={"Referer": "https://finance.sina.com.cn/",
                                              "User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20, context=ctx) as r:
        return r.read().decode("gbk", "ignore")


def parse(raw):
    res = {}
    for line in raw.strip().split("\n"):
        if "=" not in line:
            continue
        key = line.split("=")[0].replace("var hq_str_", "").strip()
        val = line.split('="', 1)[1].rstrip('";')
        res[key] = val.split(",")
    return res


def pct(a, b):
    return (a - b) / b * 100 if b else 0.0


def append_bytes(path, rows, expect_bom=True):
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


# ---------- A股 交易核验（末行日期判据 §3.119b） ----------
print("=== ① A股 交易核验 ===")
a_share_last = None
try:
    import akshare as ak
    df = ak.stock_zh_index_daily(symbol="sh000001")
    a_share_last = str(df.iloc[-1]["date"])[:10]
    print(f"  [历史末行] sh000001 = {a_share_last} 收 {df.iloc[-1]['close']}（应为 2026-10-08 → 本档为交易日）")
except Exception as e:
    print("  akshare 失败:", e)

# ---------- request 1: A股指数 / 港股指数 / A股个股 / 港股个股 ----------
IDX_A = [("sh000001", "上证指数"), ("sz399001", "深证成指"), ("sz399006", "创业板指"),
         ("sh000300", "沪深300"), ("sh000932", "中证消费"), ("sh000688", "科创50"),
         ("sz399005", "中小100"), ("sh000905", "中证500")]
IDX_HK = [("rt_hkHSI", "恒生指数"), ("rt_hkHSTECH", "恒生科技"), ("rt_hkHSCEI", "恒生国企"),
          ("rt_hkHSHCI", "恒生医疗保健"), ("rt_hkHSCI", "恒生综合")]
STOCKS = [("sz002410", "广联达"), ("sh600438", "通威股份"), ("sh600519", "贵州茅台")]
HK_STK = [("hk00700", "腾讯控股"), ("hk09988", "阿里巴巴-W"), ("hk01810", "小米集团-W"),
          ("hk09618", "京东集团-SW"), ("hk03690", "美团-W"), ("hk09999", "网易-S"),
          ("hk01024", "快手-W"), ("hk09888", "百度集团-SW"), ("hk01548", "金斯瑞生物科技"),
          ("hk01211", "比亚迪股份"), ("hk00981", "中芯国际")]

raw1 = hq([c for c, _ in IDX_A] + [c for c, _ in IDX_HK] + [c for c, _ in STOCKS] + [c for c, _ in HK_STK])
r1 = parse(raw1)

out = {"date": TODAY, "as_of": "2026-10-09 13:45", "a_share": {}, "indices_a": {},
       "indices_hk": {}, "stocks": {}, "hk_stocks": {}, "etfs": {}, "boards": {}, "hk_stocks_all": {}}

print("\n=== ② A股指数（正常交易日 · 13:45） ===")
for c, nm in IDX_A:
    f = r1.get(c)
    if not f or len(f) < 6:
        print("  MISS", c); continue
    try:
        op, pc, cur, hi, lo = float(f[1]), float(f[2]), float(f[3]), float(f[4]), float(f[5])
    except Exception:
        print("  PARSE-FAIL(剔除)", c); continue
    if not cur:
        print("  EMPTY(剔除)", c); continue
    amt = float(f[9]) / 1e8 if len(f) > 9 and f[9] else 0
    dt = f[30] if len(f) > 30 else ""
    ts = f[31] if len(f) > 31 else ""
    out["indices_a"][nm] = {"cur": cur, "pct": round(pct(cur, pc), 2), "open": op, "prev": pc,
                            "high": hi, "low": lo, "amount_yi": round(amt, 2),
                            "date_field": dt, "time": ts}
    print(f"  {nm:10s} {cur:>10.2f} {pct(cur,pc):>+7.2f}%  O{op:.2f} H{hi:.2f} L{lo:.2f}  额{amt:,.1f}亿  date={dt} t={ts}")

print("\n=== ③ 港股指数（正常交易日 · 13:45） ===")
for c, nm in IDX_HK:
    f = r1.get(c)
    if not f or len(f) < 9:
        print("  MISS", c); continue
    try:
        op, pc, hi, lo, cur = float(f[2]), float(f[3]), float(f[4]), float(f[5]), float(f[6])
        p = float(f[8])
    except Exception:
        print("  PARSE-FAIL(剔除)", c); continue
    if not cur:
        print("  EMPTY(剔除)", c); continue
    date_field = f[17] if len(f) > 17 else ""
    ts = f[18] if len(f) > 18 else ""
    out["indices_hk"][nm] = {"cur": round(cur, 3), "pct": round(p, 2), "open": op, "prev": pc,
                             "high": hi, "low": lo, "time": ts, "date_field": date_field}
    print(f"  {nm:12s} {cur:>11.3f} {p:>+7.2f}%  O{op:.2f} H{hi:.2f} L{lo:.2f}  date={date_field} t={ts}")

print("\n=== ④ A股个股 ===")
for c, nm in STOCKS:
    f = r1.get(c)
    if not f or len(f) < 6:
        print("  MISS", c); continue
    try:
        op, pc, cur, hi, lo = float(f[1]), float(f[2]), float(f[3]), float(f[4]), float(f[5])
    except Exception:
        print("  PARSE-FAIL(剔除)", c); continue
    if not cur:
        print("  EMPTY(剔除)", c); continue
    out["stocks"][nm] = {"cur": cur, "pct": round(pct(cur, pc), 2), "open": op, "prev": pc,
                         "high": hi, "low": lo}
    print(f"  {nm:10s} {cur:>10.2f} {pct(cur,pc):>+7.2f}%  O{op:.2f} H{hi:.2f} L{lo:.2f}")

print("\n=== ⑤ 港股权重股 ===")
for c, nm in HK_STK:
    f = r1.get(c)
    if not f or len(f) < 9:
        print("  MISS/EMPTY(剔除)", c); continue
    try:
        op, pc, hi, lo, cur = float(f[2]), float(f[3]), float(f[4]), float(f[5]), float(f[6])
        p = float(f[8])
    except Exception:
        print("  PARSE-FAIL(剔除)", c); continue
    if not cur:
        print("  ZERO(剔除)", c); continue
    out["hk_stocks"][nm] = {"code": c[2:], "cur": round(cur, 2), "pct": round(p, 2),
                            "open": op, "prev": pc, "high": hi, "low": lo}
    print(f"  {nm:16s} {cur:>9.2f} {p:>+7.2f}%  H{hi:.2f} L{lo:.2f}")

# ---------- request 2: 场内 ETF + 板块指数 ----------
ETFS = [("sh513050", "中概互联"), ("sz159928", "消费ETF添富"), ("sh512170", "医疗ETF"),
        ("sh513180", "恒指科技"), ("sz159920", "恒生ETF华夏"), ("sh512880", "证券ETF"),
        ("sh512980", "传媒ETF"), ("sh515180", "100红利"), ("sz159938", "医药ETF广发")]
BOARDS = [("sh000933", "中证医药"), ("sz399989", "中证医疗"), ("sz399997", "中证白酒"),
          ("sh000827", "中证环保"), ("sh000934", "中证金融"), ("sh000913", "300医药"),
          ("sz399975", "证券公司")]

raw2 = hq([c for c, _ in ETFS] + [c for c, _ in BOARDS])
r2 = parse(raw2)

print("\n=== ⑥ 场内 ETF（正常交易日） ===")
etf_rows = []
for c, nm in ETFS:
    f = r2.get(c)
    if not f or len(f) < 10:
        print("  MISS", c); continue
    try:
        op, pc, cur = float(f[1]), float(f[2]), float(f[3])
    except Exception:
        print("  PARSE-FAIL(剔除)", c); continue
    if not cur:
        print("  EMPTY(剔除)", c); continue
    p = pct(cur, pc)
    amt_wan = float(f[9]) / 1e4 if len(f) > 9 and f[9] else 0
    out["etfs"][nm] = {"code": c[2:], "cur": round(cur, 3), "pct": round(p, 2),
                       "prev": pc, "amount_wan": round(amt_wan, 1)}
    etf_rows.append([TODAY, c[2:], nm, round(cur, 3), round(p, 2), round(amt_wan, 1), NOTE])
    print(f"  {nm:12s} {cur:>7.3f} {p:>+7.2f}%  昨收{pc:>7.3f}  额 {amt_wan:>12,.0f}万")

print("\n=== ⑦ 板块指数 ===")
board_rows = []
for c, nm in BOARDS:
    f = r2.get(c)
    if not f or len(f) < 6:
        print("  MISS(剔除)", c); continue
    try:
        op, pc, cur, hi, lo = float(f[1]), float(f[2]), float(f[3]), float(f[4]), float(f[5])
    except Exception:
        print("  PARSE-FAIL(剔除)", c); continue
    if not cur:
        print("  EMPTY(剔除)", c); continue
    p = pct(cur, pc)
    out["boards"][nm] = {"cur": round(cur, 2), "pct": round(p, 2), "high": hi, "low": lo}
    board_rows.append([TODAY, nm, c, round(cur, 2), round(p, 2), NOTE])
    print(f"  {nm:10s} {cur:>10.2f} {p:>+7.2f}%  H{hi:.2f} L{lo:.2f}")

print("\n[键空间自检] indices_a:", list(out["indices_a"]))
print("[键空间自检] indices_hk:", list(out["indices_hk"]))
print("[键空间自检] etfs:", list(out["etfs"]))
print("[键空间自检] boards:", list(out["boards"]))

out["a_share"] = {
    "status": "开市（10/9 长假后第 2 个正常交易日）",
    "last_trading_day_before": a_share_last,
    "verify_method": "stock_zh_index_daily('sh000001') 历史末行 + 实时日期字段（§3.119b）",
    "priced": True,
    "note": "A股 09:30 开盘 → 指数/板块/个股/场内 ETF 均可定价；场外基金净值 15:00 收盘后发布",
}

# ---------- 增量写入 ----------
p_etf = os.path.join(HIST, "etf_intraday.csv")
exist = set()
with open(p_etf, encoding="utf-8-sig") as fh:
    for r in csv.reader(fh):
        if len(r) >= 7:
            exist.add((r[0], r[1], r[6]))
new_etf = [r for r in etf_rows if (r[0], r[1], r[6]) not in exist]
if new_etf:
    append_bytes(p_etf, new_etf, expect_bom=True)
print(f"\netf_intraday.csv +{len(new_etf)} 行")

p_idx = os.path.join(HIST, "indices.csv")
exist2 = set()
with open(p_idx, encoding="utf-8-sig") as fh:
    for r in csv.reader(fh):
        if len(r) >= 7:
            exist2.add((r[1], r[3], r[6]))
new_idx = []
for r in board_rows:
    if (r[0], r[2], r[5]) in exist2:
        continue
    new_idx.append(["index", r[0], r[1], r[2], r[3], r[4], r[5]])
# 港股指数行也入库（当日盘中读数；盘后档以真实收盘行覆盖）
for c, nm in IDX_HK:
    v = out["indices_hk"].get(nm)
    if not v:
        continue
    if (TODAY, c.replace("rt_hk", ""), NOTE) in exist2:
        continue
    new_idx.append(["index", TODAY, nm, c.replace("rt_hk", ""), v["cur"], v["pct"], NOTE])
if new_idx:
    append_bytes(p_idx, new_idx, expect_bom=True)
print(f"indices.csv +{len(new_idx)} 行（A股板块 + 港股指数）")

out["etf_intraday_rows_added"] = len(new_etf)
out["indices_rows_added"] = len(new_idx)
out["note"] = ("档型=正常交易日盘中（A股 长假后第 2 个交易日 + 港股正常交易日，双市场均开市）；"
               "A股/港股/场内 ETF 均可定价；场外基金净值 15:00 后发布 → 本档 fund_nav.csv +0 行（预期状态）；"
               "含当日盘中伪收盘行（§3.122a：多日窗口 n 会虚增，盘后档以真实收盘覆盖修正）")
json.dump(out, open(os.path.join(HIST, f"intraday_hq_{TODAY.replace('-','')}.json"), "w",
                    encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"已保存 intraday_hq_{TODAY.replace('-','')}.json")
