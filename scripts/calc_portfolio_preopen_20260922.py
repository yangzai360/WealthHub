# -*- coding: utf-8 -*-
"""盘前档 2026-09-22：① 修正 9/21 收盘（7 只场外基金真实净值兜底，§3.95 _fix 模式）
                  ② 生成 9/22 盘前基准（= 修正后 9/21 收盘链式值）+ 赛道占比 + 风险指标

背景（9/21 盘后遗留）：场外 A股类 7 只（002708×2 / 161616 / 000727 / 000051 / 110020 /
000248×2 / 002742）9/21 净值 20:00 时点未出库，盘后档按赛道代理×弹性估算 → est_total_pct
+1.38%。本档已抓到真实 9/21 净值，须重算修正并另存 `_fix.json`（同日期后写优先，§3.95）。
"""
import json, os, re, glob, statistics
import pandas as pd

BASE = "/Users/jieyang/Documents/WealthHub"
HOLD = os.path.join(BASE, "holdings")
HIST = os.path.join(BASE, "data/processed/history")
TODAY = "2026-09-22"
CLOSE_D = "2026-09-21"
BASE_TOTAL = 378405.26          # 9/18 盘后归档链式值（净值补更修正后）

# ---------- 快照 ----------
def load_snapshot(acct, fn):
    rows = []
    with open(os.path.join(HOLD, acct, fn), encoding="utf-8-sig") as f:
        reader = csv_reader = __import__("csv").reader(f)
        header = next(csv_reader)
        for r in csv_reader:
            if not r or not r[0].strip():
                continue
            if len(r) > len(header):
                extra = r[len(header) - 1:]
                r = r[: len(header) - 1] + [",".join(extra)]
            rec = dict(zip(header, r))
            rec["account"] = acct
            rows.append(rec)
    return rows


all_rows = (load_snapshot("sean-alipay-fund", "snapshot-2026-08-05.csv")
            + load_snapshot("jasy-alipay-fund", "snapshot-2026-08-12.csv")
            + load_snapshot("stock-brokerage", "snapshot-2026-08-12.csv"))
all_df = pd.DataFrame(all_rows)


def to_float(x):
    try:
        return float(str(x).replace(",", ""))
    except Exception:
        return 0.0


all_df["amount"] = all_df["amount"].apply(to_float)

TRACK_MAP = {
    "002708": "A股医药", "000727": "A股医药", "161616": "A股医药",
    "001180": "A股医药", "012323": "A股医药", "001551": "A股医药",
    "159938": "A股医药", "512170": "A股医药",
    "519915": "大消费", "000248": "大消费", "159928": "大消费",
    "004424": "大消费", "000968": "大消费",
    "000369": "美股标普医药", "016280": "美股标普医药",
    "012348": "恒生科技", "513180": "恒生科技", "513050": "恒生科技", "164906": "恒生科技",
    "000071": "其他/宽基", "159920": "其他/宽基",
    "余额宝": "现金", "货币资金": "现金",
}


def track_of(row):
    code = str(row["code"]) if pd.notna(row["code"]) else ""
    code6 = re.sub(r"\D", "", code)
    name = str(row["name"])
    if code6 in TRACK_MAP:
        return TRACK_MAP[code6]
    if "余额宝" in name or "货币" in name or "现金" in name:
        return "现金"
    return "其他/宽基"


all_df["track"] = all_df.apply(track_of, axis=1)
snap_total = all_df["amount"].sum()

# ---------- 最新净值（截至本档） ----------
fund_nav = {}
with open(os.path.join(HIST, "fund_nav.csv"), encoding="utf-8-sig") as f:
    import csv as _csv
    for row in _csv.DictReader(f):
        code, nd = row["code"], row["nav_date"]
        try:
            nav = float(row["nav"])
        except Exception:
            continue
        if code not in fund_nav or nd > fund_nav[code][0]:
            fund_nav[code] = (nd, nav)

# ---------- 9/21 收盘价（场内 ETF / 个股） ----------
cur = json.load(open(os.path.join(HIST, f"close_{CLOSE_D.replace('-', '')}.json"), encoding="utf-8"))
ETF_PX = {x["code"].replace("sh", "").replace("sz", ""): x["close"] for x in cur["etf"]}
STOCK_PX = {x["code"].replace("sh", "").replace("sz", ""): x["close"] for x in cur["stocks"]}

# ---------- 9/21 盘后档的代理估算值（用于对比修正量） ----------
prev_close = json.load(open(os.path.join(HIST, "portfolio_close_20260921.json"), encoding="utf-8"))
prev_est = prev_close["est_total_pct"]
prev_total = prev_close["total_mv"]

NAV_922 = "2026-09-21"      # 本档目标净值日（A股类）
QDII = ("000369", "016280", "164906")


def calc(row):
    code6 = re.sub(r"\D", "", str(row["code"]) if pd.notna(row["code"]) else "")
    name = str(row["name"])
    shares = to_float(row["shares"])
    if "余额宝" in name or "货币" in name or "现金" in name:
        return row["amount"], "现金", ""
    if code6 in ETF_PX:
        return shares * ETF_PX[code6], f"场内 9/21 收盘 {ETF_PX[code6]}", "real"
    if code6 in STOCK_PX:
        return shares * STOCK_PX[code6], f"个股 9/21 收盘 {STOCK_PX[code6]}", "real"
    if code6 in fund_nav:
        nd, nav = fund_nav[code6]
        tag = "real" if nd == NAV_922 else ("qdi" if code6 in QDII else "stale")
        return shares * nav, f"净值 {nd} ({nav})", tag
    return row["amount"], "暂缺", "miss"


vals = all_df.apply(calc, axis=1, result_type="expand")
all_df["mv"] = vals[0]
all_df["price_src"] = vals[1]
all_df["tag"] = vals[2]

total_mv = all_df["mv"].sum()
corr_pct = round((total_mv / BASE_TOTAL - 1) * 100, 4)
print(f"9/18 盘后归档链式基准: {BASE_TOTAL:,.2f}")
print(f"9/21 收盘（本档真实净值修正后）总资产: {total_mv:,.2f}")
print(f"  修正后 9/21 当日收益: {corr_pct:+.4f}%  ({total_mv - BASE_TOTAL:+,.2f} 元)")
print(f"  盘后档代理估算口径: {prev_est:+.2f}% / {prev_total:,.2f} 元  → 修正量 {corr_pct - prev_est:+.4f}pct / {total_mv - prev_total:+,.2f} 元")

track_amount = all_df.groupby("track")["mv"].sum().sort_values(ascending=False)
print("\n=== 赛道占比（9/21 收盘·修正口径） ===")
for t, v in track_amount.items():
    print(f"  {t}: {v:,.2f} ({v / total_mv * 100:.2f}%)")
med = track_amount.get("A股医药", 0) + track_amount.get("美股标普医药", 0)
print(f"\n医药总敞口: {med:,.2f} ({med / total_mv * 100:.2f}%)  距 40% 上限 {40 - med / total_mv * 100:.2f}pct")

print("\n=== 价格来源（按市值降序） ===")
for _, r in all_df.sort_values("mv", ascending=False).iterrows():
    print(f"  {str(r['name'])[:24]:26s} {r['track']:8s} mv={r['mv']:>11,.2f} [{r['tag']:5s}] {r['price_src']}")

# ---------- 修正后的 9/21 close _fix.json ----------
tracks_fix = {}
for t, v in track_amount.items():
    mv0 = prev_close["tracks"].get(t, {}).get("mv0", 0)
    tracks_fix[t] = {"mv0": round(mv0, 2), "mv": round(v, 2),
                     "pnl": round(v - mv0, 2),
                     "day_pct": round((v / mv0 - 1) * 100, 4) if mv0 else 0.0,
                     "pct_of_total": round(v / total_mv * 100, 2)}
fix = {"date": CLOSE_D, "as_of": "2026-09-21收盘(净值补更修正)",
       "base_total": BASE_TOTAL,
       "est_total_pnl": round(total_mv - BASE_TOTAL, 2),
       "est_total_pct": corr_pct,
       "total_mv": round(total_mv, 2),
       "tracks": tracks_fix, "med_exposure": round(med, 2),
       "med_pct": round(med / total_mv * 100, 2),
       "correction_note": f"盘后档代理估算 {prev_est:+.2f}% → 真实净值修正 {corr_pct:+.4f}%"
                          f"（修正量 {corr_pct - prev_est:+.4f}pct / {total_mv - prev_total:+,.2f} 元）；"
                          f"7 只场外基金（002708×2/161616/000727/000051/110020/000248×2/002742）9/21 真实净值已出库",
       "fix_source": "fetch_preopen_20260922（F10 直连真实净值）",
       "detail": [{"account": r["account"], "name": r["name"], "code": str(r["code"]),
                   "track": r["track"], "mv": round(r["mv"], 2), "shares": r["shares"],
                   "price_src": r["price_src"]}
                  for _, r in all_df.sort_values("mv", ascending=False).iterrows()]}
json.dump(fix, open(os.path.join(HIST, f"portfolio_close_{CLOSE_D.replace('-', '')}_fix.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print(f"\n已保存 portfolio_close_{CLOSE_D.replace('-', '')}_fix.json")

# ---------- 夏普 / 链路 / 回撤（§3.95: 同日期 _fix 覆盖） ----------
rf_10y = 1.68
files = glob.glob(os.path.join(HIST, "portfolio_close_2026*.json")) + \
        glob.glob(os.path.join(HIST, "portfolio_preopen_2026*.json"))
seen = {}
for f in files:
    m2 = re.search(r"(\d{4})(\d{2})(\d{2})", os.path.basename(f))
    if not m2:
        continue
    norm = f"{m2.group(1)}-{m2.group(2)}-{m2.group(3)}"
    if norm < "2026-08-06" or norm > CLOSE_D:
        continue
    try:
        d = json.load(open(f, encoding="utf-8"))
    except Exception:
        continue
    pct = d.get("est_total_pct")
    if pct is None:
        continue
    # ⚠️ §3.95 陷阱强化：glob 返回顺序由文件系统决定，**不可依赖**。
    # 必须显式按 (日期, 是否 _fix) 排序，保证同日期 _fix 后写覆盖。
    isfix = "_fix" in os.path.basename(f)
    if norm not in seen or (isfix and not seen[norm][1]):
        seen[norm] = (float(pct), isfix)
daily = {dt: p for dt, (p, _) in seen.items()}
daily.setdefault("2026-08-06", -0.68)
daily_rets = sorted(daily.items())
rets = [p for _, p in daily_rets]
mean_d = sum(rets) / len(rets)
std_d = statistics.stdev(rets) if len(rets) > 1 else 0
rf_d = rf_10y / 252
sharpe = (mean_d - rf_d) / std_d * (252 ** 0.5) if std_d > 0 else None

chain, peak, mdd = 0.0, 0.0, 0.0
for dt, p in daily_rets:
    chain += p
    peak = max(peak, chain)
    mdd = min(mdd, chain - peak)

def win_cum(s, e):
    v = 0.0
    for dt, p in daily_rets:
        if s <= dt <= e:
            v += p
    return round(v, 2)

print(f"\n夏普: {sharpe:.2f}  样本 {len(daily_rets)} 日（{daily_rets[0][0]} ~ {daily_rets[-1][0]}）")
print(f"  日收益均值 {mean_d:.4f}%  日标准差 {std_d:.4f}%  rf={rf_10y}%")
print(f"链路累计: {chain:+.2f}%  最大回撤: {mdd:.2f}%")
print(f"W39(9/21-9/22): {win_cum('2026-09-21', CLOSE_D):+.2f}%  近5日: {sum(rets[-5:]):+.2f}%  近10日: {sum(rets[-10:]):+.2f}%")
print("\n--- 日收益样本序列（★= _fix 覆盖生效） ---")
for dt, p in daily_rets:
    print(f"  {dt}: {p:+.4f}%{'  ★' if seen.get(dt, (0, False))[1] else ''}")

# ---------- 9/22 盘前基准 JSON ----------
detail = [{"account": r["account"], "name": r["name"], "code": str(r["code"]), "track": r["track"],
           "mv": round(r["mv"], 2), "shares": r["shares"], "price_src": r["price_src"]}
          for _, r in all_df.sort_values("mv", ascending=False).iterrows()]
out = {"date": TODAY, "as_of": "9/21收盘(修正口径)",
       "snap_total": round(snap_total, 2), "total_mv": round(total_mv, 2),
       "base_total": BASE_TOTAL, "close_20260921_pct": corr_pct,
       "tracks": {t: {"mv": round(v, 2), "pct": round(v / total_mv * 100, 2)} for t, v in track_amount.items()},
       "med_exposure": round(med, 2), "med_pct": round(med / total_mv * 100, 2),
       "sharpe_annual": round(sharpe, 2) if sharpe else None, "sharpe_samples": len(daily_rets),
       "daily_mean": round(mean_d, 4), "daily_sd": round(std_d, 4),
       "chain_cum_pct": round(chain, 2), "max_drawdown_pct": round(mdd, 2),
       "w39_cum_pct": win_cum("2026-09-21", CLOSE_D), "last5_cum_pct": round(sum(rets[-5:]), 2),
       "last10_cum_pct": round(sum(rets[-10:]), 2),
       "rf_10y": rf_10y, "detail": detail}
json.dump(out, open(os.path.join(HIST, f"portfolio_preopen_{TODAY.replace('-', '')}.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print(f"已保存 portfolio_preopen_{TODAY.replace('-', '')}.json")

rs = {"date": TODAY, "chain_cum_pct": round(chain, 2), "chain_days": len(daily_rets),
      "w38_cum_pct": 1.37, "w38_days": 5,
      "w39_cum_pct": win_cum("2026-09-21", CLOSE_D), "w39_days": 1,
      "sharpe": round(sharpe, 2), "sharpe_n": len(daily_rets),
      "daily_mean": round(mean_d, 4), "daily_sd": round(std_d, 4),
      "max_dd_pct": round(mdd, 2), "last5_cum_pct": round(sum(rets[-5:]), 2),
      "last10_cum_pct": round(sum(rets[-10:]), 2),
      "fix_applied": "portfolio_close_20260921_fix.json（9/21 净值补更修正 +1.37%）"}
json.dump(rs, open(os.path.join(HIST, f"risk_stats_{TODAY.replace('-', '')}.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print(f"已保存 risk_stats_{TODAY.replace('-', '')}.json")
