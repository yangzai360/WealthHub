# -*- coding: utf-8 -*-
"""2026-08-14 盘前行情抓取：隔夜美股(8/13收盘) + 港股参考 + 场外基金净值补更(8/13)"""
import sys, os, json, re, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import akshare as ak
import pandas as pd

HIST = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "processed", "history"))
os.makedirs(HIST, exist_ok=True)
INDICES = os.path.join(HIST, "indices.csv")
FUND_NAV = os.path.join(HIST, "fund_nav.csv")
TODAY = "2026-08-14"

def read_csv(path, cols):
    if not os.path.exists(path):
        return pd.DataFrame(columns=cols)
    try:
        df = pd.read_csv(path, encoding="utf-8-sig", dtype=str)
        for c in cols:
            if c not in df.columns:
                df[c] = ""
        return df
    except Exception as e:
        print(f"read_csv warn {path}: {e}")
        return pd.DataFrame(columns=cols)

def append_rows(path, rows, cols):
    df = read_csv(path, cols)
    for r in rows:
        assert len(r) == len(cols), f"row len {len(r)} != {len(cols)}"
        df = pd.concat([df, pd.DataFrame([dict(zip(cols, r))])], ignore_index=True)
    df = df.drop_duplicates()
    df.to_csv(path, index=False, encoding="utf-8-sig")
    print(f"  -> {path} 现 {len(df)} 行, 本次+{len(rows)}")

def try_call(fn, *args, retries=2, **kwargs):
    for i in range(retries + 1):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            print(f"  retry {i}: {fn.__name__} err {e}")
            time.sleep(2)
    return None

def pct_from_last_two(df, col="close"):
    if df is None or len(df) < 2:
        return None, None
    c = pd.to_numeric(df[col], errors="coerce").dropna()
    if len(c) < 2:
        return None, None
    last, prev = c.iloc[-1], c.iloc[-2]
    return float(last), float((last / prev - 1) * 100)

# 已存在 key 集合（type,date,code,note）
existing_idx = read_csv(INDICES, ["type", "date", "name", "code", "close", "pct_change", "note"])
exist_idx_keys = set()
for _, r in existing_idx.iterrows():
    exist_idx_keys.add((str(r["type"]).strip(), str(r["date"]).strip(), str(r["code"]).strip(), str(r["note"]).strip()))

# ---------- 1. 隔夜美股 (8/13 收盘) ----------
us_rows = []
us_tickers = [("QQQ", "纳指100ETF(QQQ)"), ("DIA", "道指ETF(DIA)"), ("IYH", "美股医疗IYH"), ("XLV", "美股医疗XLV")]
print("== 美股 ETF ==")
for code, name in us_tickers:
    df = try_call(ak.stock_us_daily, symbol=code)
    if df is not None and len(df) >= 2:
        d = str(df.iloc[-1]["date"])[:10]
        close, pct = pct_from_last_two(df)
        note = "美股收盘(隔夜)"
        key = ("us_index", d, code, note)
        if key not in exist_idx_keys:
            us_rows.append(["us_index", d, name, code, f"{close:.2f}", f"{pct:.2f}", note])
            print(f"  + {name} {d} close={close:.2f} pct={pct:.2f}%")
        else:
            print(f"  = {name} {d} 已存在")
    else:
        print(f"  {name} 数据暂缺")

for code, name in [(".IXIC", "纳指指数"), (".DJI", "道指指数")]:
    df = try_call(ak.index_us_stock_sina, symbol=code)
    if df is not None and len(df) >= 2:
        d = str(df.iloc[-1]["date"])[:10]
        close, pct = pct_from_last_two(df)
        note = "美股指数收盘(隔夜)"
        key = ("us_index", d, code, note)
        if key not in exist_idx_keys:
            us_rows.append(["us_index", d, name, code, f"{close:.2f}", f"{pct:.2f}", note])
            print(f"  + {name} {d} close={close:.2f} pct={pct:.2f}%")
        else:
            print(f"  = {name} {d} 已存在")
    else:
        print(f"  {name} 数据暂缺")

if us_rows:
    append_rows(INDICES, us_rows, ["type", "date", "name", "code", "close", "pct_change", "note"])

# ---------- 2. 港股 spot（盘前参考，8/13 收盘值） ----------
print("== 港股指数 (spot) ==")
hk_df = try_call(ak.stock_hk_index_spot_sina)
if hk_df is not None:
    for code, name in [("HSI", "恒生指数"), ("HSTECH", "恒生科技")]:
        row = hk_df[hk_df["代码"] == code]
        if len(row):
            print(f"  {name} {row.iloc[0]['最新价']} {row.iloc[0]['涨跌幅']}%")

# ---------- 3. 场外基金净值补更 (8/13 未出的继续抓) ----------
print("== 场外基金净值补更 ==")
funds = {
    "002708": "大摩健康产业A", "000968": "广发养老产业", "002742": "泓德裕祥债券A",
    "004752": "广发传媒联接A", "005368": "富国清洁能源", "110020": "易方达沪深300联接A",
    "000369": "广发全球医疗A", "100032": "富国红利增强A", "001180": "广发医药卫生",
    "161616": "融通医疗保健A/B", "000051": "华夏沪深300联接A", "519915": "富国消费主题A",
    "000071": "华夏恒生ETF联接A", "012348": "天弘恒生科技A", "001551": "天弘医药100C",
    "164906": "交银中概互联A", "000248": "汇添富主要消费A", "016280": "广发全球医疗C",
    "001469": "广发金融地产A", "001552": "天弘证券保险A", "012323": "华宝中证医疗C",
    "000727": "融通健康产业A/B", "004424": "汇添富文体娱乐A",
}

existing_nav = read_csv(FUND_NAV, ["date", "code", "name", "nav_date", "nav", "pct"])
exist_nav_keys = set()
for _, r in existing_nav.iterrows():
    exist_nav_keys.add((str(r["code"]).strip(), str(r["nav_date"]).strip()))

nav_rows = []
for code, nm in funds.items():
    df = try_call(ak.fund_open_fund_info_em, symbol=code, indicator="单位净值走势")
    if df is None or len(df) == 0:
        print(f"  {code} {nm}: 数据暂缺")
        continue
    last = df.iloc[-1]
    nav_date = str(last["净值日期"])[:10]
    nav = str(last["单位净值"])
    pct = str(last["日增长率"])
    if (code, nav_date) not in exist_nav_keys:
        nav_rows.append([TODAY, code, nm, nav_date, nav, pct])
        print(f"  + {code} {nm} {nav_date} nav={nav} pct={pct}%")
    else:
        print(f"  = {code} {nm} {nav_date} 已存在")

if nav_rows:
    append_rows(FUND_NAV, nav_rows, ["date", "code", "name", "nav_date", "nav", "pct"])

print("DONE")
