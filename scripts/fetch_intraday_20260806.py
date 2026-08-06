# -*- coding: utf-8 -*-
"""
盘中行情抓取 (2026-08-06 13:45 档)
源: akshare 新浪源 + 天天基金源 (东财 push2 已被代理拦截, 不适用)
输出: data/processed/history/indices.csv (增量), data/processed/history/etf_intraday.csv, data/processed/history/fund_nav.csv
"""
import os, sys, time, json, re
import akshare as ak
import pandas as pd

BASE = "/Users/jieyang/Documents/WealthHub"
HIST = os.path.join(BASE, "data/processed/history")
os.makedirs(HIST, exist_ok=True)

def retry(fn, *args, retries=2, **kwargs):
    last = None
    for i in range(retries + 1):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            last = e
            time.sleep(1.5)
    raise last

results = {"indices": [], "etf": [], "fund_nav": []}
errors = []

# ---------- 1. A股指数实时 (新浪源) ----------
try:
    idx = retry(ak.stock_zh_index_spot_sina)
    want = {"000001": "上证指数", "399006": "创业板指", "399932": "中证消费"}
    for _, row in idx.iterrows():
        raw = str(row["代码"])
        code = re.sub(r"\D", "", raw)  # 去 sh/sz 前缀
        code = code.zfill(6) if code else code
        if code in want:
            results["indices"].append({
                "type": "index", "date": "2026-08-06", "name": want[code],
                "code": code, "close": round(float(row["最新价"]), 2),
                "pct_change": round(float(row["涨跌幅"]), 2),
                "note": "盘中13:45"
            })
except Exception as e:
    errors.append(f"stock_zh_index_spot_sina: {e}")

# ---------- 3. 恒生科技 (新浪港股源) ----------
try:
    hk = retry(ak.stock_hk_index_spot_sina)
    for _, row in hk.iterrows():
        if "HSTECH" in str(row.get("代码", "")):
            results["indices"].append({
                "type": "index", "date": "2026-08-06", "name": "恒生科技",
                "code": "HSTECH", "close": round(float(row["最新价"]), 2),
                "pct_change": round(float(row["涨跌幅"]), 2),
                "note": "盘中13:45"
            })
except Exception as e:
    errors.append(f"stock_hk_index_spot_sina: {e}")

# ---------- 4. 场内 ETF 实时 (持仓) ----------
ETF_MAP = {
    "513050": "中概互联", "159928": "消费ETF添富", "159938": "医药ETF广发",
    "512170": "医疗ETF", "513180": "恒指科技", "159920": "恒生ETF华夏",
    "512880": "证券ETF", "512980": "传媒ETF", "515180": "100红利",
}
try:
    etf = retry(ak.fund_etf_spot_em)
    for _, row in etf.iterrows():
        code = str(row["代码"]).zfill(6)
        if code in ETF_MAP:
            results["etf"].append({
                "date": "2026-08-06", "code": code, "name": ETF_MAP[code],
                "price": round(float(row["最新价"]), 3),
                "pct": round(float(row["涨跌幅"]), 2),
                "amount_wan": round(float(row.get("成交额", 0)) / 1e4, 1),
                "note": "盘中13:45"
            })
except Exception as e:
    errors.append(f"fund_etf_spot_em: {e}")

# ---------- 5. 场外基金净值 (天天基金源, 支付宝账户数据源) ----------
FUND_MAP = {
    "000369": "广发全球医疗保健A", "016280": "广发全球医疗保健C",
    "002708": "大摩健康产业", "000727": "融通健康产业",
    "012348": "天弘恒生科技A", "000071": "华夏恒生ETF联接A",
    "000248": "汇添富主要消费A", "519915": "富国消费主题",
    "012323": "华宝中证医疗C", "161616": "融通医疗保健",
    "001180": "广发医药卫生", "001551": "天弘医药100C",
}
for code, name in FUND_MAP.items():
    try:
        nav = retry(ak.fund_open_fund_info_em, symbol=code, indicator="单位净值走势")
        if nav is not None and len(nav) > 0:
            last = nav.iloc[-1]
            results["fund_nav"].append({
                "date": "2026-08-06", "code": code, "name": name,
                "nav_date": str(last["净值日期"]),
                "nav": round(float(last["单位净值"]), 4),
                "pct": round(float(last["日增长率"]), 2)
            })
    except Exception as e:
        errors.append(f"fund {code}: {e}")

# ---------- 写入 ----------
# indices.csv 增量 (同日同代码覆盖为最新盘中快照, 跨日保留)
idx_path = os.path.join(HIST, "indices.csv")
if results["indices"]:
    df_new = pd.DataFrame(results["indices"])
    if os.path.exists(idx_path):
        df_old = pd.read_csv(idx_path, encoding="utf-8-sig")
        # 去掉同日同代码旧记录, 用最新盘中数据覆盖
        drop_keys = set(zip(df_new["date"], df_new["code"]))
        df_old = df_old[~df_old.apply(lambda r: (r["date"], r["code"]) in drop_keys, axis=1)]
        pd.concat([df_old, df_new], ignore_index=True).to_csv(idx_path, index=False, encoding="utf-8-sig")
        print(f"[indices] 覆盖更新 {len(df_new)} 条 (同日同代码)")
    else:
        df_new.to_csv(idx_path, index=False, encoding="utf-8-sig")
        print(f"[indices] 新建写入 {len(df_new)} 条")

# etf_intraday.csv (整文件覆盖当日)
etf_path = os.path.join(HIST, "etf_intraday.csv")
if results["etf"]:
    pd.DataFrame(results["etf"]).to_csv(etf_path, index=False, encoding="utf-8-sig")
    print(f"[etf] 写入 {len(results['etf'])} 条")

# fund_nav.csv (整文件覆盖当日)
nav_path = os.path.join(HIST, "fund_nav.csv")
if results["fund_nav"]:
    pd.DataFrame(results["fund_nav"]).to_csv(nav_path, index=False, encoding="utf-8-sig")
    print(f"[fund_nav] 写入 {len(results['fund_nav'])} 条")

# 汇总 JSON (供报告生成)
with open(os.path.join(HIST, "intraday_20260806.json"), "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print("\n=== 结果汇总 ===")
print("Indices:")
for r in results["indices"]:
    print(f"  {r['name']} {r['code']} {r['close']} {r['pct_change']}%")
print("ETF:")
for r in results["etf"]:
    print(f"  {r['name']} {r['code']} {r['price']} {r['pct']}%")
print("Fund NAV:")
for r in results["fund_nav"]:
    print(f"  {r['name']} {r['code']} {r['nav_date']} {r['nav']} {r['pct']}%")
if errors:
    print("\n[errors]")
    for e in errors:
        print(f"  {e}")
