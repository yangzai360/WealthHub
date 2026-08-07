# -*- coding: utf-8 -*-
"""抓取广联达/通威个股盘中实时(新浪日线接口, 盘中最后一行=实时)"""
import akshare as ak

for sym, name in [("sz002410", "广联达"), ("sh600438", "通威股份")]:
    try:
        df = ak.stock_zh_a_daily(symbol=sym, adjust="qfq")
        last = df.iloc[-1]
        prev = df.iloc[-2]
        pct = (float(last["close"]) / float(prev["close"]) - 1) * 100
        print(f"{name} {sym}: date={last['date']} close={last['close']} pct={pct:.2f}%")
    except Exception as e:
        print(f"{name} FAIL: {repr(e)[:200]}")
