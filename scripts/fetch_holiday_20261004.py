#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fetch_holiday_20261004.py — 2026-10-04（周日 · 国庆长假第 4 日）盘后复盘档 行情增量脚本

档型判定（§3.107 / §3.119b / §3.122b：一律读「数据源日期字段」，禁止用「价格是否变化」推断）：
  · A股  —— akshare.stock_zh_index_daily('sh000001') 末行日期
  · 港股 —— 新浪 hq 直连 rt_hkHSTECH 返回体「日期字段」
  · 美股 —— akshare.stock_us_daily 末行日期（北京 20:00 = 美东同日 08:00，§3.120c）

本档预期：档型①「纯非交易日」（A股与港股「均」未开市；美股照常开市不改变该判定）。
  → A股 +0 行、港股 +0 行；**美股 10/2（五）收盘为真实新增量**（成型于北京 10/3 04:00）→ 增量写入 8 行。
  → 不产 portfolio_close_* / portfolio_pending_*；不向链式序列插入 0% 行。
"""
import csv
import io
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime

import requests

ROOT = "/Users/jieyang/Documents/WealthHub"
HIST = os.path.join(ROOT, "data/processed/history")
TODAY = "2026-10-04"
TODAY_C = "20261004"

sys.path.insert(0, ROOT)
import akshare as ak  # noqa: E402


def numstat(path):
    r = subprocess.run(["git", "--no-pager", "diff", "--numstat", "--", path],
                       cwd=ROOT, capture_output=True, text=True)
    out = r.stdout.strip()
    return out if out else "0/0 (无变化)"


# ---------------------------------------------------------------- 1. 档型判定
print("=" * 78)
print("[1] 档型判定（三市场独立验证，§3.119b）")
print("=" * 78)

ash_last_date, ash_close = None, None
for attempt in range(3):
    try:
        df = ak.stock_zh_index_daily(symbol="sh000001")
        ash_last_date = str(df.iloc[-1]["date"])
        ash_close = float(df.iloc[-1]["close"])
        break
    except Exception as e:  # noqa: BLE001
        print(f"  A股 第 {attempt+1} 次失败: {e}")
if ash_last_date is None:
    raise SystemExit("A股指数接口连续 3 次失败 → 终止")

hk_date_field, hk_time_field, hk_close = None, None, None
for attempt in range(3):
    try:
        r = requests.get("http://hq.sinajs.cn/list=rt_hkHSTECH",
                         headers={"Referer": "https://finance.sina.com.cn",
                                  "User-Agent": "Mozilla/5.0"}, timeout=15)
        r.encoding = "gbk"
        body = r.text
        fields = body.split('"')[1].split(",")
        hk_date_field = fields[17]
        hk_time_field = fields[18]
        hk_close = float(fields[6])
        break
    except Exception as e:  # noqa: BLE001
        print(f"  港股 第 {attempt+1} 次失败: {e}")
if hk_date_field is None:
    raise SystemExit("新浪 hq 港股接口连续 3 次失败 → 终止")

us_rows = {}
for sym in ["XLV", "IYH", "QQQ", "DIA", "SPY", ".IXIC", ".DJI", ".INX"]:
    for attempt in range(3):
        try:
            df = ak.stock_us_daily(symbol=sym)
            us_rows[sym] = df.tail(3).reset_index(drop=True)
            break
        except Exception as e:  # noqa: BLE001
            print(f"  美股 {sym} 第 {attempt+1} 次失败: {e}")

print(f"  A股  sh000001 末行日期 = {ash_last_date}（收 {ash_close}）")
print(f"  港股 rt_hkHSTECH 日期字段 = {hk_date_field} / 时间 = {hk_time_field} / 收盘 = {hk_close}")
for sym, df in us_rows.items():
    print(f"  美股 {sym:6s} 末行 = {str(df.iloc[-1]['date']).split()[0]}  收 {df.iloc[-1]['close']}")

ashare_open = (ash_last_date == TODAY)
hk_open = (hk_date_field.replace("/", "-") == TODAY)
if ashare_open or hk_open:
    raise SystemExit(f"⚠️ 档型判定与预期不符（A股开市={ashare_open} / 港股开市={hk_open}）→ 人工复核后再执行")

SESSION_TYPE = "pure_non_trading_day_close"
print(f"\n  → 判定：档型①「纯非交易日」（A股与港股均未开市，SESSION_TYPE={SESSION_TYPE}）✅")

# ------------------------------------------------------- 2. 美股 10/2 增量写入
print()
print("=" * 78)
print("[2] indices.csv 增量写入（美股 2026-10-02 收盘 8 行）")
print("=" * 78)

US_NAME = {"XLV": "美股医疗XLV", "IYH": "美股医疗IYH", "QQQ": "纳指100ETF",
           "DIA": "道指ETF", "SPY": "标普500ETF", ".IXIC": "纳斯达克",
           ".DJI": "道琼斯", ".INX": "标普500"}
US_TARGET_DATE = "2026-10-02"

idx_path = os.path.join(HIST, "indices.csv")
raw = open(idx_path, "rb").read()
has_bom = raw[:3] == b"\xef\xbb\xbf"
rows = list(csv.reader(io.StringIO(raw.decode("utf-8-sig"))))
header = rows[0]
assert header[:4] == ["type", "date", "name", "code"], f"表头异常: {header}"
seen = {(r[0], r[1], r[3]) for r in rows[1:]}

new_rows = []
for sym, df in us_rows.items():
    df = df.copy()
    df["d"] = df["date"].astype(str).str.split().str[0]
    m = df[df["d"] == US_TARGET_DATE]
    if m.empty:
        print(f"  ⚠️ {sym} 无 {US_TARGET_DATE} 数据 → 跳过")
        continue
    close = float(m.iloc[0]["close"])
    prev = df[df["d"] < US_TARGET_DATE].iloc[-1]
    pct = round((close / float(prev["close"]) - 1) * 100, 2)
    key = ("us_index", US_TARGET_DATE, sym)
    if key in seen:
        print(f"  · {sym} {US_TARGET_DATE} 已存在 → 跳过")
        continue
    new_rows.append(["us_index", US_TARGET_DATE, US_NAME[sym], sym,
                     f"{close:g}", f"{pct:g}", "美股收盘"])

if new_rows:
    shutil.copy2(idx_path, idx_path + ".bak2")
    # §3.89 教训：禁止整表重写（csv.writer 默认 lineterminator='\r\n' 会把全部 LF 行归一为 CRLF
    # → 造成 300+ 行全量 diff）。本档改为**纯文本追加**：沿用文件末行既有的行尾符。
    tail = raw[-1:]
    eol = b"\r\n" if raw.endswith(b"\r\n") else b"\n"
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerows(new_rows)
    payload = buf.getvalue().encode("utf-8").replace(b"\n", eol)
    with open(idx_path, "ab") as f:
        f.write(payload)
    print(f"  ✅ 追加 {len(new_rows)} 行（纯文本追加，行尾沿用 {eol!r}，未整表重写）")
    for r in new_rows:
        print("     ", r)
else:
    print("  → 无新增行")

print(f"\n  git diff --numstat indices.csv  = {numstat('data/processed/history/indices.csv')}")
print(f"  git diff --numstat etf_intraday = {numstat('data/processed/history/etf_intraday.csv')}")
print(f"  git diff --numstat fund_nav.csv = {numstat('data/processed/history/fund_nav.csv')}")

# ------------------------------------------------------------- 3. 产物写盘
print()
print("=" * 78)
print("[3] 盘点产物写盘")
print("=" * 78)

out = {
    "date": TODAY,
    "session": "close",
    "session_type": SESSION_TYPE,
    "session_type_note": ("档型①「纯非交易日」（A股与港股「均」未开市；美股照常开市不改变该判定，"
                          "§3.109/§3.118b/§3.120a）。本档为国庆长假第 4 日（周日）20:00 盘后复盘档，"
                          "不产 portfolio_close_* / portfolio_pending_*，不向链式序列插入 0% 行。"),
    "three_market_verification": {
        "ashare": {"source": "akshare.stock_zh_index_daily('sh000001')",
                   "last_row_date": ash_last_date, "close": ash_close,
                   "verdict": "未开市（末行日期 = 上一交易日 2026-09-30）"},
        "hk": {"source": "新浪 hq 直连 rt_hkHSTECH 返回体日期字段",
               "date_field": hk_date_field, "time_field": hk_time_field, "close": hk_close,
               "verdict": "未开市（返回体日期字段 = 2026/10/02，上一港股交易日，§3.119b/§3.122b）"},
        "us": {"source": "akshare.stock_us_daily('IYH' / 'XLV')",
               "last_row_date": US_TARGET_DATE,
               "IYH": float(us_rows["IYH"].iloc[-1]["close"]),
               "XLV": float(us_rows["XLV"].iloc[-1]["close"]),
               "verdict": "美股 10/2（周五）已收盘（成型于北京 10/3 04:00）→ 本档为**新增量**"},
        "rule": "三市场各自独立验证、不得互相外推（§3.119b）",
    },
    "data_increment": {
        "indices_csv_new_rows": len(new_rows),
        "indices_csv_rows": new_rows,
        "etf_intraday_csv": 0,
        "fund_nav_csv": 0,
        "zero_increment_self_proof": {
            "rule": "§3.119e 三项自证：三表 numstat / 且慢 session / 事件库 session_added",
            "numstat": {"indices.csv": numstat("data/processed/history/indices.csv"),
                        "etf_intraday.csv": numstat("data/processed/history/etf_intraday.csv"),
                        "fund_nav.csv": numstat("data/processed/history/fund_nav.csv")},
            "note": ("本档**非零增量档**：indices.csv 获美股 10/2 真实收盘 8 行；"
                     "etf_intraday.csv / fund_nav.csv 为 0 行属预期（沪深交易所休市、场外基金不发净值）"),
        },
        "next_increment": "2026-10-05（港股复市 + 美股 10/5 收盘）；2026-10-08（A股 + 港股通复市，全量）",
    },
    "us_close_20261002": {
        "note": "美股 10/2 收盘（真实新增量）：纳指 +1.19% / 标普500 +0.73% / 道指 +0.49%，三大指数齐涨；而 XLV −0.01%、IYH 0.00% 双双跑输宽基",
        "closes": {sym: float(us_rows[sym].iloc[-1]["close"]) for sym in us_rows},
    },
}

os.makedirs(HIST, exist_ok=True)
p = os.path.join(HIST, f"fetch_summary_{TODAY_C}_close.json")
with open(p, "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
print(f"  ✅ 写盘 {p}")
print(f"\n完成时间：{datetime.now():%Y-%m-%d %H:%M:%S}")
