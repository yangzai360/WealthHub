# -*- coding: utf-8 -*-
"""2026-09-25 盘中档：新浪 hq 直连
⚠️ 本档 A股/场内ETF 全部休市（中秋 9/25-9/27）→ 不产出 A股行情行
   唯一增量 = 港股（9/25 正常交易）：HSI / HSTECH / HSCEI + 权重股 + 医疗保健
⚠️ CSV 追加必须按「末行 EOL 一致」的字节追加（§3.87/§3.89），禁止整表重写
"""
import json, csv, os, ssl, urllib.request

ROOT = "/Users/jieyang/Documents/WealthHub"
TODAY = "2026-09-25"
NOTE = "港股盘中13:45(新浪hq直取)"
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


def append_bytes(path, rows):
    d = open(path, 'rb').read()
    assert d[:3] == b'\xef\xbb\xbf', 'BOM 缺失: ' + path
    eol = b'\r\n' if d.endswith(b'\r\n') else b'\n'
    if not d.endswith(eol):
        d = d + eol
    buf = b''.join(','.join(str(x) for x in r).encode('utf-8') + eol for r in rows)
    with open(path, 'ab') as fh:
        fh.write(buf)


# ---------- 港股指数 + 权重股 + 医疗保健 ----------
IDX_HK = [("rt_hkHSI", "恒生指数"), ("rt_hkHSTECH", "恒生科技"), ("rt_hkHSCEI", "恒生国企"),
          ("rt_hkHSHCI", "恒生医疗保健"), ("rt_hkHSCI", "恒生综合")]
HK_STK = [("hk00700", "腾讯控股"), ("hk09988", "阿里巴巴-W"), ("hk01810", "小米集团-W"),
          ("hk09618", "京东集团-SW"), ("hk03690", "美团-W"), ("hk09999", "网易-S"),
          ("hk01024", "快手-W"), ("hk09888", "百度集团-SW"), ("hk01548", "金斯瑞生物科技"),
          ("hk01211", "比亚迪股份"), ("hk00981", "中芯国际")]

raw = hq([c for c, _ in IDX_HK] + [c for c, _ in HK_STK])
r = parse(raw)

out = {"indices_hk": {}, "hk_stocks": {}, "a_share": "休市(中秋 9/25-9/27)"}
print("=== 港股指数（9/25 盘中） ===")
idx_rows = []
for c, nm in IDX_HK:
    f = r.get(c)
    if not f or len(f) < 9:
        print("MISS/EMPTY(剔除)", c); continue
    try:
        op, pc, hi, lo, cur = float(f[2]), float(f[3]), float(f[4]), float(f[5]), float(f[6])
        p = float(f[8])
    except Exception:
        print("PARSE-FAIL(剔除)", c); continue
    if not cur:
        print("ZERO(剔除)", c); continue
    out["indices_hk"][nm] = {"cur": round(cur, 3), "pct": round(p, 2), "open": op, "prev": pc,
                             "high": hi, "low": lo, "time": f[17] if len(f) > 17 else ""}
    idx_rows.append(["index", TODAY, nm, c.replace("rt_hk", ""), round(cur, 3), round(p, 2), NOTE])
    print(f"{nm:12s} {cur:>11.3f} {p:>+7.2f}%  O{op:.2f} H{hi:.2f} L{lo:.2f}")

print("\n=== 港股个股（9/25 盘中） ===")
for c, nm in HK_STK:
    f = r.get(c)
    if not f or len(f) < 9:
        print("MISS/EMPTY(剔除)", c); continue
    try:
        op, pc, hi, lo, cur = float(f[2]), float(f[3]), float(f[4]), float(f[5]), float(f[6])
        p = float(f[8])
    except Exception:
        print("PARSE-FAIL(剔除)", c); continue
    if not cur:
        print("ZERO(剔除)", c); continue
    out["hk_stocks"][nm] = {"code": c[2:], "cur": round(cur, 2), "pct": round(p, 2),
                            "open": op, "prev": pc, "high": hi, "low": lo}
    print(f"{nm:16s} {cur:>9.2f} {p:>+7.2f}%  H{hi:.2f} L{lo:.2f}")

print("\n[键空间自检] indices_hk:", list(out["indices_hk"]))
print("[键空间自检] hk_stocks:", list(out["hk_stocks"]))

# ---------- 增量写入 indices.csv ----------
p_idx = os.path.join(ROOT, "data/processed/history/indices.csv")
exist = set()
with open(p_idx, encoding="utf-8-sig") as fh:
    for row in csv.reader(fh):
        if len(row) >= 7:
            exist.add((row[1], row[3], row[6]))
new_rows = [row for row in idx_rows if (row[1], row[3], row[6]) not in exist]
if new_rows:
    append_bytes(p_idx, new_rows)
print(f"\nindices.csv +{len(new_rows)} 行（港股指数，纯新增）")

json.dump(out, open(os.path.join(ROOT, f"data/processed/history/intraday_hq_{TODAY.replace('-','')}.json"),
                    "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"已保存 intraday_hq_{TODAY.replace('-','')}.json")
