# -*- coding: utf-8 -*-
"""2026-09-02 盘中: 组合当日收益估算（8/31 收盘市值为基准 + 盘中实时涨跌）+ 赛道敞口"""
import json, os

base = "/Users/jieyang/Documents/WealthHub"

# 9/2 盘中涨跌（%）：场内ETF实时 + 指数盘中（13:44-13:45 抓取）
intraday = {
    # 场内ETF
    "513050": -1.23, "159928": -0.59, "512170": -0.88, "513180": -1.91,
    "159920": -0.67, "512880": -1.71, "512980": -2.00, "515180": -1.29,
    "159938": -0.46,
    # 指数
    "sh000001": -0.79, "sz399006": -2.00, "sh000932": -0.58,
    "HSTECH": -1.40, "HSI": -0.71,
    # 美股(9/1 XLV +0.66% 于 9/3-4 兑现, 盘中估算按 0)
    "XLV": 0.0, "IYH": 0.0,
}

# 持仓基准: 8/31 收盘口径市值 (portfolio_preopen_20260902.json)
with open(os.path.join(base, "data/processed/history/portfolio_preopen_20260902.json"), encoding="utf-8") as f:
    preopen = json.load(f)
holdings = [(d["account"], d["name"], d["code"], d["mv"], d["track"]) for d in preopen["detail"]]

MED_AVG = round((intraday["512170"] + intraday["159938"]) / 2, 2)  # A股医药场外代理均值 +0.38

# 标的 -> 近似涨跌来源（场外基金按赛道用 ETF/指数近似）
def approx_pct(code, name):
    code6 = "".join(c for c in code if c.isdigit())
    if code6 == "" or "余额宝" in name or "现金" in name or "帮你投" in name or "泓德" in name:
        return 0.0
    if code6 in intraday:
        return intraday[code6]
    if code6 in ("002708", "161616", "001180", "001551", "012323", "000727"):
        return MED_AVG                  # A股医药 -> 医疗/医药ETF均值
    if code6 in ("000248", "519915", "000968"):
        return intraday["sh000932"]     # 大消费 -> 中证消费
    if code6 in ("004424",):
        return intraday["512980"]       # 文体娱乐 -> 传媒ETF(消费/传媒混合)
    if code6 in ("012348",):
        return intraday["513180"]       # 恒生科技QDII -> 恒指科技ETF
    if code6 in ("164906",):
        return intraday["513050"]       # 中概互联 -> 中概互联ETF
    if code6 in ("000369", "016280"):
        return intraday["IYH"]          # 美股医药QDII -> IYH(今日兑现按0)
    if code6 in ("000071",):
        return intraday["159920"]       # 恒生ETF联接 -> 恒生ETF华夏
    if code6 in ("000051", "110020"):
        return intraday["sh000001"]     # 沪深300 -> 上证
    if code6 in ("001469", "001552"):
        return intraday["512880"]       # 金融地产/证券保险 -> 证券ETF
    if code6 in ("005368",):
        return intraday["sh000001"]     # 清洁能源 -> 上证(保守)
    if code6 in ("100032",):
        return intraday["515180"]       # 红利 -> 100红利
    if code6 in ("002410",):
        return intraday["sz399006"]     # 广联达 -> 创业板指
    if code6 in ("600438",):
        return intraday["sh000001"]     # 通威 -> 上证(保守)
    if code6 in ("004752",):
        return intraday["512980"]       # 传媒 -> 传媒ETF
    if code6 in ("002742",):
        return intraday["sh000932"]     # 其他消费类 -> 中证消费(保守)
    return 0.0

total = preopen["total_mv"]
sector_amt = {}
for _, _, _, amt, sec in holdings:
    sector_amt[sec] = sector_amt.get(sec, 0) + amt
print(f"总资产(8/31收盘口径): {total:,.2f} 元")
print("\n== 赛道敞口(8/31收盘口径) ==")
for sec, amt in sector_amt.items():
    print(f"  {sec}: {amt:,.2f} ({amt/total*100:.2f}%)")
med = sector_amt.get("A股医药",0)+sector_amt.get("美股标普医药",0)
print(f"  医药总敞口: {med:,.2f} ({med/total*100:.2f}%)")

print("\n== 9/2 盘中组合估算 (13:45) ==")
pnl = 0.0
contrib = {}
items = []
for acct, name, code, amt, sec in holdings:
    p = approx_pct(code, name)
    w = amt * p / 100
    contrib[sec] = contrib.get(sec, 0) + w
    pnl += w
    if abs(w) > 20:
        items.append((name, p, w))
print(f"  组合估算: {pnl:,.2f} 元 ({pnl/total*100:.2f}%)")
for sec, c in sorted(contrib.items(), key=lambda x: -abs(x[1])):
    print(f"    {sec}: {c:,.2f} 元 ({c/total*100:.2f}pct)")
print("\n  主要贡献标的:")
for name, p, w in sorted(items, key=lambda x: -abs(x[2]))[:8]:
    print(f"    {name}: {p}% -> {w:,.2f} 元")

# 保存结果供日报引用
out = {"total": total, "pnl": pnl, "pct": pnl/total*100,
       "sector_amt": sector_amt, "sector_pct": {k: v/total*100 for k, v in sector_amt.items()},
       "contrib": contrib, "approx": {i[1]: i[2] for i in items}}
with open("/tmp/portfolio_intraday_20260902.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)
print("\n已存 /tmp/portfolio_intraday_20260902.json")
