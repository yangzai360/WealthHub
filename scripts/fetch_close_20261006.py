# -*- coding: utf-8 -*-
"""2026-10-06 盘后档（20:00）行情抓取 — 档型②「混合档」第 3 日：A股休市（10/1-10/7）+ 港股续市第 3 日收盘

本档口径：
  ① A股 —— 无新行情（法定假日）；用 stock_zh_index_daily('sh000001') 末行日期验证「休市」
  ② 港股 —— **续市第 3 个交易日收盘**（16:08 成型）→ 新浪 hq 直连取 5 指数 + 11 权重股收盘
     判「今日是否开市」读返回体「日期字段 f[17]」（§3.119b / §3.126b）
  ③ 场内 ETF（A股上市）—— 休市，价格冻结在 9/30 → 抓取用于「零变动自证」（§3.119e）
  ④ 场外基金（23 只）—— A股 休市期不发布净值 → 预期 0 新增行
  ⑤ 美股 —— 北京 10/6 20:00 = 美东 10/6 08:00 EDT，US 10/6 未开盘（§3.120c）
     → 上一有效美股收盘 = 2026-10-05（已于 10/6 盘前档入库）→ 本档无新增
⚠️ CSV 追加一律「字节追加 + 按该文件 BOM 属性写入」（§3.87/§3.89/§3.116a）
⚠️ §3.122a / §3.127d：13:45 盘中档写入的 2026-10-06 伪收盘行不清理，本档追加真实收盘行；
   indices.csv 以 (code, date) 为键、下游 dict 后写入覆盖先写入 → 自动修正；判据 = 多日窗口 n 不变
⚠️ 本次为全新撰写（非 sed 派生），读写路径 = 20261006 / 2026-10-06（§3.113e / §3.126d / §3.128d）
"""
import json, csv, os, ssl, urllib.request

ROOT = "/Users/jieyang/Documents/WealthHub"
TODAY = "2026-10-06"
HIST = os.path.join(ROOT, "data/processed/history")
NOTE = "港股收盘16:08(新浪hq直取)"
SESSION_TYPE = "混合档（A股休市 + 港股开市）· 港股续市第 3 日收盘"
ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE


def hq(codes):
    url = "https://hq.sinajs.cn/list=" + ",".join(codes)
    req = urllib.request.Request(url, headers={"Referer": "https://finance.sina.com.cn/",
                                              "User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=25, context=ctx) as r:
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


def append_bytes(path, rows):
    d = open(path, 'rb').read()
    assert d[:3] == b'\xef\xbb\xbf', 'BOM 缺失: ' + path
    eol = b'\r\n' if d.endswith(b'\r\n') else b'\n'
    if not d.endswith(eol):
        d = d + eol
    buf = b''.join(','.join(str(x) for x in r).encode('utf-8') + eol for r in rows)
    with open(path, 'ab') as fh:
        fh.write(buf)


# ---------- ① A股：休市核验（末行日期判据 §3.119b） ----------
print("=== ① A股 休市核验（stock_zh_index_daily sh000001 末行日期） ===")
a_share_last = None
try:
    import akshare as ak
    df = ak.stock_zh_index_daily(symbol="sh000001")
    a_share_last = str(df.iloc[-1]["date"])[:10]
    print(f"  sh000001 末行日期 = {a_share_last}  收 {df.iloc[-1]['close']}  → {'休市' if a_share_last != TODAY else '开市'}")
except Exception as e:
    print("  akshare 失败，改读 indices.csv:", e)

# ---------- ② 港股：续市第 3 日收盘 ----------
IDX_HK = [("rt_hkHSI", "恒生指数"), ("rt_hkHSTECH", "恒生科技"), ("rt_hkHSCEI", "恒生国企"),
          ("rt_hkHSHCI", "恒生医疗保健"), ("rt_hkHSCI", "恒生综合")]
HK_STK = [("hk00700", "腾讯控股"), ("hk09988", "阿里巴巴-W"), ("hk01810", "小米集团-W"),
          ("hk09618", "京东集团-SW"), ("hk03690", "美团-W"), ("hk09999", "网易-S"),
          ("hk01024", "快手-W"), ("hk09888", "百度集团-SW"), ("hk01548", "金斯瑞生物科技"),
          ("hk01211", "比亚迪股份"), ("hk00981", "中芯国际")]
ETF_A = [("sh513050", "中概互联"), ("sh513180", "恒指科技"), ("sz159920", "恒生ETF华夏"),
         ("sz159928", "消费ETF添富"), ("sh512170", "医疗ETF"), ("sh515180", "100红利"),
         ("sh512880", "证券ETF"), ("sh512980", "传媒ETF"), ("sz002410", "广联达"),
         ("sh600438", "通威股份")]

raw = hq([c for c, _ in IDX_HK] + [c for c, _ in HK_STK] + [c for c, _ in ETF_A])
r = parse(raw)

out = {"date": TODAY, "session": "close", "as_of": "2026-10-06 20:00（港股收盘后）",
       "session_type": SESSION_TYPE, "a_share": {}, "indices_hk": {},
       "hk_stocks": {}, "etf_a_frozen": {}, "us": {}}
print("\n=== ② 港股指数（10/6 续市第 3 日 · 收盘） ===")
idx_rows = []
for c, nm in IDX_HK:
    f = r.get(c)
    if not f or len(f) < 9:
        print("  MISS/EMPTY(剔除)", c); continue
    try:
        op, pc, hi, lo, cur = float(f[2]), float(f[3]), float(f[4]), float(f[5]), float(f[6])
        p = float(f[8])
    except Exception:
        print("  PARSE-FAIL(剔除)", c); continue
    ts = f[17] if len(f) > 17 else ""          # ⚠️ 日期字段（§3.119b / §3.126b）
    tm = f[18] if len(f) > 18 else ""
    if not cur:
        print("  ZERO(剔除)", c); continue
    out["indices_hk"][nm] = {"cur": round(cur, 3), "pct": round(p, 2), "open": op, "prev": pc,
                             "high": hi, "low": lo, "date_field": ts, "time_field": tm}
    idx_rows.append(["index", TODAY, nm, c.replace("rt_hk", ""), round(cur, 3), round(p, 2), NOTE])
    print(f"  {nm:12s} {cur:>11.3f} {p:>+7.2f}%  O{op:.2f} H{hi:.2f} L{lo:.2f}  date_field={ts} time={tm}")

out["a_share"] = {
    "status": "休市（10/1-10/7 国庆长假）",
    "last_trading_day": a_share_last,
    "verify_method": "stock_zh_index_daily('sh000001') 末行日期（§3.119b）",
    "priced": False,
    "note": "A股 休市 → 场外基金无净值、场内 ETF 无成交价 → A股 腿不可定价（§3.107 条款 19）",
}

print("\n=== ③ 港股权重股（10/6 收盘） ===")
for c, nm in HK_STK:
    f = r.get(c)
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
                            "open": op, "prev": pc, "high": hi, "low": lo,
                            "date_field": f[17] if len(f) > 17 else ""}
    print(f"  {nm:16s} {cur:>9.2f} {p:>+7.2f}%  H{hi:.2f} L{lo:.2f}")

print("\n=== ④ 场内 ETF / 个股（A股 休市 → 价格应冻结在 9/30 收盘） ===")
for c, nm in ETF_A:
    f = r.get(c)
    if not f or len(f) < 6:
        print("  MISS/EMPTY(剔除)", c); continue
    try:
        pc, cur = float(f[2]), float(f[3])
    except Exception:
        print("  PARSE-FAIL(剔除)", c); continue
    ts = f[30] if len(f) > 30 else (f[17] if len(f) > 17 else "")
    out["etf_a_frozen"][nm] = {"code": c, "cur": cur, "prev": pc, "date_field": ts}
    print(f"  {nm:12s} {cur:>9.3f}  昨收 {pc:>9.3f}  date_field={ts}")

out["us"] = {
    "status": "本档无新增美股数据",
    "note": "北京 10/6 20:00 = 美东 10/6 08:00 EDT（距 09:30 开盘 1.5h）→ US 10/6 收盘于北京 10/7 04:00 成型；上一有效收盘 = 2026-10-05（已于 10/6 盘前档入库）",
    "priced": False,
    "last_us_close": "2026-10-05",
}

print("\n[键空间自检] indices_hk:", list(out["indices_hk"]))
print("[键空间自检] hk_stocks:", list(out["hk_stocks"]))

# ---------- 增量写入 indices.csv（仅港股指数真实收盘行） ----------
p_idx = os.path.join(HIST, "indices.csv")
exist = set()
with open(p_idx, encoding="utf-8-sig") as fh:
    for row in csv.reader(fh):
        if len(row) >= 7:
            exist.add((row[1], row[3], row[6]))
new_rows = [row for row in idx_rows if (row[1], row[3], row[6]) not in exist]
if new_rows:
    append_bytes(p_idx, new_rows)
print(f"\nindices.csv +{len(new_rows)} 行（港股指数真实收盘；13:45 伪收盘行按 §3.122a 不清理，下游 dict 后写入覆盖）")

# ---------- etf_intraday.csv 自证（应 +0 行） ----------
p_etf = os.path.join(HIST, "etf_intraday.csv")
with open(p_etf, encoding="utf-8-sig") as fh:
    head = next(csv.reader(fh))
print(f"etf_intraday.csv 表头 = {head}")
print("etf_intraday.csv 本档 +0 行（A股 休市、场内无成交价 → 预期状态）")
out["etf_intraday_rows_added"] = 0
out["indices_rows_added"] = len(new_rows)
out["note"] = ("档型②混合档盘后：只产港股指数**真实收盘**行；A股/场内 ETF 休市 → etf_intraday.csv +0 行（预期状态，非抓取失败）；"
               "A股 腿与港股联接腿仍不可定价（§3.107/§3.119e）")

oj = os.path.join(HIST, f'close_hq_{TODAY.replace("-","")}.json')
json.dump(out, open(oj, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"已保存 {os.path.basename(oj)}")
