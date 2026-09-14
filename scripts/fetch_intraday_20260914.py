# -*- coding: utf-8 -*-
"""2026-09-14 盘中档行情抓取：A股/港股指数实时 + 场内ETF实时 + 场外基金盘中估算"""
import json, re, urllib.request, ssl, time
import akshare as ak

ctx = ssl.create_default_context(); ctx.check_hostname=False; ctx.verify_mode=ssl.CERT_NONE
out = {}

def retry(fn, n=3, name=""):
    for i in range(n):
        try:
            r = fn()
            if r is not None:
                return r
        except Exception as e:
            print(f"[warn] {name} try{i+1}: {e}")
            time.sleep(1)
    print(f"[FAIL] {name}")
    return None

# 1. A股指数实时（新浪源）
def _a():
    df = ak.stock_zh_index_spot_sina()
    df["c6"] = df["代码"].astype(str).map(lambda x: re.sub(r"\D", "", x))
    want = {"000001":"上证指数","399001":"深证成指","399006":"创业板指","000300":"沪深300","000932":"中证消费"}
    res = {}
    for k,v in want.items():
        row = df[df["c6"]==k]
        if len(row):
            r = row.iloc[0]
            res[v] = {"code":k, "close":float(r["最新价"]), "pct":float(r["涨跌幅"]), "amount":float(r.get("成交额",0) or 0)}
    return res
out["a_index"] = retry(_a, name="A股指数spot") or {}

# 2. 港股指数实时（新浪源）
def _hk():
    df = ak.stock_hk_index_spot_sina()
    cols = list(df.columns)
    res = {}
    want = {"HSI":"恒生指数","HSTECH":"恒生科技"}
    for k,v in want.items():
        row = df[df[cols[0]].astype(str).str.contains(k, case=False, na=False)]
        if len(row):
            r = row.iloc[0]
            res[v] = {"close": float(r[cols[1]]), "pct": float(r[cols[3]]), "row": [str(x) for x in r.tolist()]}
    return res
out["hk_index"] = retry(_hk, name="港股指数spot") or {}

# 3. 场内ETF实时
def _etf():
    df = ak.fund_etf_spot_em()
    codes = ["513050","159928","512170","513180","159920","512880","512980","515180","159938"]
    res = {}
    df["c"] = df["代码"].astype(str)
    for c in codes:
        row = df[df["c"]==c]
        if len(row):
            r = row.iloc[0]
            res[c] = {"name": r["名称"], "price": float(r["最新价"]), "pct": float(r["涨跌幅"]),
                      "amount": float(r.get("成交额",0) or 0), "high": float(r.get("最高价",0) or 0), "low": float(r.get("最低价",0) or 0)}
    return res
out["etf"] = retry(_etf, name="场内ETF spot") or {}

# 4. 场外基金盘中估算净值（天天基金估值接口）
funds = {
 "002708":"大摩健康产业混合A","000968":"广发养老产业A","002742":"泓德裕祥债券A","004752":"广发传媒联接A",
 "005368":"富国清洁能源A","110020":"易方达沪深300联接A","000369":"广发全球医疗A(QDII)","100032":"富国红利增强A",
 "001180":"广发医药卫生联接A","161616":"融通医疗保健A/B","000051":"华夏沪深300联接A","519915":"富国消费主题A",
 "000071":"华夏恒生ETF联接A","012348":"天弘恒生科技联接A","001551":"天弘医药100C","164906":"交银海外互联(QDII)",
 "000248":"汇添富主要消费联接A","016280":"广发全球医疗C(QDII)","001469":"广发金融地产联接A","001552":"天弘证券保险A",
 "012323":"华宝中证医疗联接C","000727":"融通健康产业A/B","004424":"汇添富文体娱乐A",
}
gz = {}
for code in funds:
    try:
        url = f"https://fundgz.1234567.com.cn/js/{code}.js?rt={int(time.time()*1000)}"
        req = urllib.request.Request(url, headers={"User-Agent":"Mozilla/5.0","Referer":"https://fund.eastmoney.com/"})
        with urllib.request.urlopen(req, timeout=15, context=ctx) as r:
            txt = r.read().decode("utf-8", "ignore")
        m = re.search(r"jsonpgz\((.*)\)", txt)
        if m and m.group(1).strip():
            d = json.loads(m.group(1))
            gz[code] = {"name": d.get("name"), "dwjz": d.get("dwjz"), "gsz": d.get("gsz"), "gszzl": d.get("gszzl"), "gztime": d.get("gztime")}
    except Exception as e:
        gz[code] = {"err": str(e)[:60]}
out["fund_gz"] = gz

# 5. 个股（盘中最后可用日线 + 标注）
def _stock(sym):
    df = ak.stock_zh_a_daily(symbol=sym, adjust="qfq")
    return {"last_date": str(df["date"].iloc[-1]), "last_close": float(df["close"].iloc[-1]),
            "prev_close": float(df["close"].iloc[-2])}
out["stock"] = {}
for sym,nm in [("sz002410","广联达"),("sh600438","通威股份")]:
    try: out["stock"][nm] = _stock(sym)
    except Exception as e: out["stock"][nm] = {"err": str(e)[:60]}

# 6. 十年国债收益率
try:
    df = ak.bond_zh_us_rate(start_date="20260901")
    out["bond10y"] = {"date": str(df["日期"].iloc[-1]), "y10": float(df["中国国债收益率10年"].iloc[-1])}
except Exception as e:
    out["bond10y"] = {"err": str(e)[:80]}

json.dump(out, open("/tmp/intraday_20260914.json","w"), ensure_ascii=False, indent=1)
print(json.dumps(out, ensure_ascii=False, indent=1)[:6000])
