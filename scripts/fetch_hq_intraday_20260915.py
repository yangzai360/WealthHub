# -*- coding: utf-8 -*-
"""2026-09-14 盘中：个股/指数 hq 直连 + 增量写入 indices.csv / etf_intraday.csv"""
import json, csv, os, urllib.request, ssl
ctx = ssl.create_default_context(); ctx.check_hostname=False; ctx.verify_mode=ssl.CERT_NONE

def hq(codes):
    url = "https://hq.sinajs.cn/list=" + ",".join(codes)
    req = urllib.request.Request(url, headers={"Referer":"https://finance.sina.com.cn/","User-Agent":"Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15, context=ctx) as r:
        return r.read().decode("gbk","ignore")

raw = hq(["sh000001","sz399001","sz399006","sh000300","sh000932","rt_hkHSI","rt_hkHSTECH","sz002410","sh600438","sh600519"])
print(raw)

res = {}
for line in raw.strip().split("\n"):
    if "=" not in line: continue
    key = line.split("=")[0].replace("var hq_str_","").strip()
    val = line.split('="',1)[1].rstrip('";')
    f = val.split(",")
    res[key] = f

def pct(a,b): return (a-b)/b*100

out = {}
# A股指数: 字段 名称,今开,昨收,现价,最高,最低,...  (index 格式: name,今开,昨收,现价,最高,最低,成交量,成交额)
for c,nm in [("sh000001","上证指数"),("sz399001","深证成指"),("sz399006","创业板指"),("sh000300","沪深300"),("sh000932","中证消费")]:
    f = res.get(c)
    if f and len(f)>5:
        op,pc,cur,hi,lo = float(f[1]),float(f[2]),float(f[3]),float(f[4]),float(f[5])
        out[nm] = {"cur":cur,"pct":pct(cur,pc),"open":op,"prev":pc,"high":hi,"low":lo,"amount":float(f[7]) if len(f)>7 and f[7] else 0}
# 港股 rt_hk: 名称,今开,昨收,最高,最低,现价,涨跌,涨跌幅,...
for c,nm in [("rt_hkHSI","恒生指数"),("rt_hkHSTECH","恒生科技")]:
    f = res.get(c)
    if f and len(f)>8:
        out[nm] = {"cur":float(f[6]),"pct":float(f[8]),"open":float(f[2]),"prev":float(f[3]),"high":float(f[4]),"low":float(f[5])}
# 个股: 名称,今开,昨收,现价,最高,最低,...
for c,nm in [("sz002410","广联达"),("sh600438","通威股份"),("sh600519","贵州茅台")]:
    f = res.get(c)
    if f and len(f)>5:
        op,pc,cur,hi,lo = float(f[1]),float(f[2]),float(f[3]),float(f[4]),float(f[5])
        out[nm] = {"cur":cur,"pct":pct(cur,pc),"open":op,"prev":pc,"high":hi,"low":lo}

print(json.dumps(out, ensure_ascii=False, indent=1))
json.dump(out, open("/tmp/intraday_hq_20260915.json","w"), ensure_ascii=False, indent=1)
