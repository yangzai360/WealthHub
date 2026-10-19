# -*- coding: utf-8 -*-
"""2026-10-19 盘中档（13:45）：新浪 hq 直连 —— **反向混合档**（A股 正常交易日 + 港股重阳节翌日休市）

本档口径（**档型② 镜像：A股 开市 + 港股休市**，非档型③）：
  ① A股 —— 10/19 正常交易日 09:30 开盘 → 取实时指数 + 板块 + 个股 + 场内 ETF
  ② 港股 —— **10/19 重阳节翌日休市** → rt_hk* 日期字段应为 2026/10/16 → **只作参照、不写 indices.csv**
     ⚠️ §3.159 新增：休市日**禁止**把 stale 港股价写成当日「盘中伪收盘行」，
        否则事件库 n 日窗口会把 10/19 当成港股交易日、并把 10/16 的涨跌重复计入
  ③ 场外基金 —— A股 15:00 后发布净值、港股联接休市不发布 → 本档 fund_nav.csv +0（预期）
  ④ 场内港股类 ETF（513050/513180/159920）—— **A股 开市即可交易**，取实时价（溢价/折价扰动须披露）
⚠️ 判「今日是否开市」一律读数据源「日期字段」（§3.119b / §3.122b）
⚠️ 新浪 hq 港股指数字段序：f[17]=日期 f[18]=时刻；A股指数 f[30]=日期 f[31]=时刻
⚠️ CSV 追加一律「字节追加 + 按该文件 BOM 属性写入」（§3.87/§3.116a）
"""
import json, csv, os, ssl, urllib.request

ROOT = "/Users/jieyang/Documents/WealthHub"
TODAY = "2026-10-19"
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
    print(f"  [历史末行] sh000001 = {a_share_last} 收 {df.iloc[-1]['close']}（应为 2026-10-16 → 本档为交易日）")
except Exception as e:
    print("  akshare 失败:", e)

# ---------- request 1 ----------
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

out = {"date": TODAY, "as_of": "2026-10-19 13:45", "a_share": {}, "indices_a": {},
       "indices_hk": {}, "indices_hk_stale_ref": {}, "stocks": {}, "hk_stocks": {},
       "etfs": {}, "boards": {}, "hk_market_state": {}, "nav_probe": {}}

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

print("\n=== ③ 港股指数（**重阳节翌日休市** · 只作 stale 参照，不入 CSV） ===")
hk_closed = True
for c, nm in IDX_HK:
    f = r1.get(c)
    if not f or len(f) < 9:
        print("  MISS", c); continue
    try:
        op, pc, hi, lo, cur = float(f[2]), float(f[3]), float(f[4]), float(f[5]), float(f[6])
        p = float(f[8])
    except Exception:
        print("  PARSE-FAIL(剔除)", c); continue
    date_field = f[17] if len(f) > 17 else ""
    ts = f[18] if len(f) > 18 else ""
    is_today = str(date_field).replace('/', '-')[:10] == TODAY
    out["indices_hk_stale_ref"][nm] = {"cur": round(cur, 3), "pct": round(p, 2),
                                       "prev": pc, "date_field": date_field, "time": ts,
                                       "is_today": is_today, "writable_to_csv": False}
    if is_today:
        hk_closed = False
        out["indices_hk"][nm] = {"cur": round(cur, 3), "pct": round(p, 2),
                                 "date_field": date_field, "time": ts}
    print(f"  {nm:12s} {cur:>11.3f} {p:>+7.2f}%  date={date_field} t={ts}  → {'今日' if is_today else '**休市(stale)**'}")

out["hk_market_state"] = {
    "closed": hk_closed,
    "reason": "2026-10-19 重阳节翌日，港股休市（沪深港通双向关闭、10/20 恢复）",
    "verify_method": "rt_hk* 返回体日期字段（§3.119b），实测 = 2026/10/16 16:08:38",
    "csi_rule": "§3.159：休市日禁止把 stale 港股价写成当日「盘中伪收盘行」→ 本档 indices.csv **不含任何港股行**",
    "resume_date": "2026-10-20",
}
print(f"  → hk_closed = {hk_closed}（休市日 indices.csv 写港股行 = 0 行，§3.159）")

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

print("\n=== ⑤ 港股权重股（休市 → 全部 stale，仅登记、不入库） ===")
for c, nm in HK_STK:
    f = r1.get(c)
    if not f or len(f) < 9:
        print("  MISS/EMPTY(剔除)", c); continue
    try:
        cur = float(f[6]); p = float(f[8]); pc = float(f[3])
    except Exception:
        print("  PARSE-FAIL(剔除)", c); continue
    if not cur:
        print("  ZERO(剔除)", c); continue
    out["hk_stocks"][nm] = {"code": c[2:], "cur": round(cur, 2), "pct": round(p, 2), "prev": pc,
                            "stale": True}
    print(f"  {nm:16s} {cur:>9.2f} {p:>+7.2f}%（10/16 收盘，休市 stale）")

# ---------- request 2: 场内 ETF + 板块指数 ----------
ETFS = [("sh513050", "中概互联"), ("sz159928", "消费ETF添富"), ("sh512170", "医疗ETF"),
        ("sh513180", "恒指科技"), ("sz159920", "恒生ETF华夏"), ("sh512880", "证券ETF"),
        ("sh512980", "传媒ETF"), ("sh515180", "100红利"), ("sz159938", "医药ETF广发")]
BOARDS = [("sh000933", "中证医药"), ("sz399989", "中证医疗"), ("sz399997", "中证白酒"),
          ("sh000827", "中证环保"), ("sh000934", "中证金融"), ("sh000913", "300医药"),
          ("sz399975", "证券公司")]

raw2 = hq([c for c, _ in ETFS] + [c for c, _ in BOARDS])
r2 = parse(raw2)

print("\n=== ⑥ 场内 ETF（A股 开市 → 可定价；港股类为溢价/折价口径） ===")
etf_rows = []
HK_LINKED_ETF = {"513050", "513180", "159920"}
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
                       "prev": pc, "amount_wan": round(amt_wan, 1),
                       "hk_linked": c[2:] in HK_LINKED_ETF}
    etf_rows.append([TODAY, c[2:], nm, round(cur, 3), round(p, 2), round(amt_wan, 1), NOTE])
    print(f"  {nm:12s} {cur:>7.3f} {p:>+7.2f}%  昨收{pc:>7.3f}  额 {amt_wan:>12,.0f}万"
          f"{'  ← 港股类（标的市场休市，价格为 A股 溢价/折价）' if c[2:] in HK_LINKED_ETF else ''}")

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

# ---------- 场外/QDII 净值日探针（只读，不写库） ----------
print("\n=== ⑧ QDII/LOF 净值日探针（13:45 预期仍迟滞） ===")
try:
    import akshare as ak
    for code in ("000369", "016280", "164906"):
        try:
            d = ak.fund_open_fund_info_em(symbol=code, indicator="单位净值走势")
            last = d.iloc[-1]
            out["nav_probe"][code] = {"nav_date": str(last["净值日期"])[:10], "nav": float(last["单位净值"])}
            print(f"  {code}: 最新净值日 {str(last['净值日期'])[:10]} / {last['单位净值']}")
        except Exception as e2:
            print(f"  {code} 探针失败: {e2}")
            out["nav_probe"][code] = {"error": str(e2)[:120]}
except Exception as e:
    print("  akshare 不可用:", e)

print("\n[键空间自检] indices_a:", list(out["indices_a"]))
print("[键空间自检] indices_hk:", list(out["indices_hk"]), "（应为空 → 休市）")
print("[键空间自检] etfs:", list(out["etfs"]))
print("[键空间自检] boards:", list(out["boards"]))

out["a_share"] = {
    "status": "开市（10/19 周一，长假后第 8 个正常交易日）",
    "last_trading_day_before": a_share_last,
    "verify_method": "stock_zh_index_daily('sh000001') 历史末行 + 实时日期字段（§3.119b）",
    "priced": True,
    "note": "A股 09:30 开盘 → 指数/板块/个股/场内 ETF 均可定价；场外基金净值 15:00 后发布",
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
# §3.159：港股休市 → **不写任何港股行**（stale 价写当日行会污染事件库 n 日窗口）
hk_rows_skipped = 0
if not hk_closed:
    for c, nm in IDX_HK:
        v = out["indices_hk"].get(nm)
        if not v:
            continue
        if (TODAY, c.replace("rt_hk", ""), NOTE) in exist2:
            continue
        new_idx.append(["index", TODAY, nm, c.replace("rt_hk", ""), v["cur"], v["pct"], NOTE])
else:
    hk_rows_skipped = len(IDX_HK)
if new_idx:
    append_bytes(p_idx, new_idx, expect_bom=True)
print(f"indices.csv +{len(new_idx)} 行（A股板块 7；港股 0 行——休市跳过 {hk_rows_skipped} 条，§3.159）")

out["etf_intraday_rows_added"] = len(new_etf)
out["indices_rows_added"] = len(new_idx)
out["hk_rows_skipped"] = hk_rows_skipped
out["note"] = ("档型=反向混合档（A股 正常交易日 + 港股重阳节翌日休市）；"
               "A股 指数/板块/个股/场内 ETF 可定价；港股 rt_hk* 为 10/16 stale 价 → 不写 CSV（§3.159）；"
               "场外基金净值 15:00 后发布、港股联接休市不发布 → fund_nav.csv +0 行（预期）；"
               "含 A股 板块「盘中 13:45」伪收盘行 7 行（§3.122a，盘后档以真实收盘覆盖）")
json.dump(out, open(os.path.join(HIST, f"intraday_hq_{TODAY.replace('-','')}.json"), "w",
                    encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"已保存 intraday_hq_{TODAY.replace('-','')}.json")
