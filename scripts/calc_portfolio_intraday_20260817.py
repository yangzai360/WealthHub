# -*- coding: utf-8 -*-
"""2026-08-17 盘中: 组合当日收益估算（场外基金用赛道ETF盘中涨跌近似）+ 赛道敞口"""
import json, os

base = "/Users/jieyang/Documents/WealthHub"

# 8/17 盘中涨跌（%）：场内ETF实时 + 指数盘中
intraday = {
    # 场内ETF
    "513050": 1.92, "159928": -1.19, "512170": 0.28, "513180": 1.68,
    "159920": 1.49, "512880": 0.28, "512980": -1.63, "515180": 0.21,
    "159938": 0.29,
    # 指数
    "sh000001": 0.96, "sz399006": 2.41, "sh000932": -1.38,
    "HSTECH": 2.23, "HSI": 1.71,
    # 美股(8/14收盘, QDII滞后反映)
    "XLV": -0.60, "IYH": -0.65,
}

# 持仓: (账户, 名称, code, 金额, 赛道)
holdings = [
    # sean-alipay-fund (snapshot 8/5)
    ("sean", "大摩健康产业A", "002708", 18538.14, "A股医药"),
    ("sean", "广发养老产业", "000968", 6871.47, "大消费"),
    ("sean", "泓德裕祥债券A", "002742", 9.39, "其他/宽基"),
    ("sean", "广发传媒联接A", "004752", 1.00, "其他/宽基"),
    ("sean", "富国清洁能源", "005368", 6811.56, "其他/宽基"),
    ("sean", "易方达沪深300联接A", "110020", 5209.15, "其他/宽基"),
    ("sean", "广发全球医疗A", "000369", 12947.21, "美股标普医药"),
    ("sean", "富国红利增强A", "100032", 4.69, "其他/宽基"),
    ("sean", "广发医药卫生", "001180", 8941.22, "A股医药"),
    ("sean", "融通医疗保健A/B", "161616", 16005.09, "A股医药"),
    ("sean", "华夏沪深300联接A", "000051", 10011.97, "其他/宽基"),
    ("sean", "富国消费主题A", "519915", 2982.08, "大消费"),
    ("sean", "华夏恒生ETF联接A", "000071", 6848.26, "其他/宽基"),
    ("sean", "天弘恒生科技A", "012348", 4261.22, "恒生科技"),
    ("sean", "天弘医药100C", "001551", 2779.06, "A股医药"),
    ("sean", "交银中概互联A", "164906", 5593.16, "恒生科技"),
    ("sean", "汇添富主要消费A", "000248", 27184.11, "大消费"),
    ("sean", "广发全球医疗C", "016280", 12374.10, "美股标普医药"),
    ("sean", "余额宝", "cash", 240.55, "现金"),
    # jasy-alipay-fund (snapshot 8/12)
    ("jasy", "摩根健康产业A", "002708", 7730.40, "A股医药"),
    ("jasy", "广发金融地产A", "001469", 4241.54, "其他/宽基"),
    ("jasy", "恒生ETF联接A", "000071", 12351.76, "其他/宽基"),
    ("jasy", "广发全球医疗A", "000369", 17508.55, "美股标普医药"),
    ("jasy", "天弘证券保险A", "001552", 9241.03, "其他/宽基"),
    ("jasy", "汇添富主要消费A", "000248", 1889.11, "大消费"),
    ("jasy", "华宝中证医疗C", "012323", 21093.74, "A股医药"),
    ("jasy", "融通健康产业A/B", "000727", 5236.49, "A股医药"),
    ("jasy", "天弘恒生科技A", "012348", 12242.66, "恒生科技"),
    ("jasy", "汇添富文体娱乐A", "004424", 3977.74, "其他/宽基"),
    ("jasy", "交银中概互联A", "164906", 5085.31, "恒生科技"),
    ("jasy", "广发全球医疗C", "016280", 16479.74, "美股标普医药"),
    ("jasy", "富国消费主题A", "519915", 22097.63, "大消费"),
    ("jasy", "余额宝", "cash", 4858.02, "现金"),
    # stock-brokerage (snapshot 8/12)
    ("stock", "广联达", "002410", 43635.20, "其他/宽基"),
    ("stock", "中概互联ETF", "513050", 6123.60, "恒生科技"),
    ("stock", "消费ETF添富", "159928", 12873.40, "大消费"),
    ("stock", "医疗ETF", "512170", 5998.60, "A股医药"),
    ("stock", "通威股份", "600438", 3837.00, "其他/宽基"),
    ("stock", "恒指科技ETF", "513180", 2995.20, "恒生科技"),
    ("stock", "100红利ETF", "515180", 979.30, "其他/宽基"),
    ("stock", "恒生ETF华夏", "159920", 152.80, "恒生科技"),
    ("stock", "证券ETF", "512880", 110.90, "其他/宽基"),
    ("stock", "传媒ETF", "512980", 88.10, "其他/宽基"),
    ("stock", "现金", "cash", 24114.40, "现金"),
]

# 标的 -> 近似涨跌来源（场外基金按赛道用 ETF/指数近似）
def approx_pct(code, name):
    if code == "cash":
        return 0.0
    if code in intraday:
        return intraday[code]
    if code in ("002708", "161616", "001180", "001551", "012323", "000727"):
        return intraday["512170"]       # A股医药 -> 医疗ETF
    if code in ("000248", "519915", "000968"):
        return intraday["sh000932"]     # 大消费 -> 中证消费
    if code in ("012348",):
        return intraday["513180"]       # 恒生科技QDII -> 恒指科技ETF
    if code in ("164906",):
        return intraday["513050"]       # 中概互联 -> 中概互联ETF
    if code in ("000369", "016280"):
        return intraday["IYH"]          # 美股医药QDII -> IYH(8/14)
    if code in ("000071",):
        return intraday["159920"]       # 恒生ETF联接 -> 恒生ETF华夏
    if code in ("000051", "110020"):
        return intraday["sh000001"]     # 沪深300 -> 上证
    if code in ("001469", "001552"):
        return intraday["512880"]       # 金融地产/证券保险 -> 证券ETF
    if code in ("004424", "004752"):
        return intraday["512980"]       # 文体娱乐/传媒 -> 传媒ETF
    if code in ("005368",):
        return intraday["sh000001"]     # 清洁能源 -> 上证(保守)
    if code in ("100032",):
        return intraday["515180"]       # 红利 -> 100红利
    if code in ("002410",):
        return intraday["sz399006"]     # 广联达 -> 创业板指
    if code in ("600438",):
        return intraday["sh000001"]     # 通威 -> 上证(保守)
    if code in ("002742",):
        return 0.0                      # 债券
    return 0.0

total = sum(h[3] for h in holdings)
sector_amt = {}
for _, _, _, amt, sec in holdings:
    sector_amt[sec] = sector_amt.get(sec, 0) + amt
print(f"总资产(快照口径): {total:,.2f} 元")
print("\n== 赛道敞口(快照口径) ==")
for sec, amt in sector_amt.items():
    print(f"  {sec}: {amt:,.2f} ({amt/total*100:.2f}%)")
med = sector_amt.get("A股医药",0)+sector_amt.get("美股标普医药",0)
print(f"  医药总敞口: {med:,.2f} ({med/total*100:.2f}%)")

print("\n== 8/17 盘中组合估算 ==")
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
with open("/tmp/portfolio_intraday_20260817.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)
print("\n已存 /tmp/portfolio_intraday_20260817.json")
