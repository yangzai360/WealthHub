# -*- coding: utf-8 -*-
"""尝试抓取广联达/通威个股实时行情(新浪源)"""
import akshare as ak

try:
    df = ak.stock_zh_a_spot()
    print("OK cols:", list(df.columns))
    print("rows:", len(df))
    for code in ["002410", "600438"]:
        col = df.columns[0]
        sub = df[df[col].astype(str).str.contains(code)]
        if not sub.empty:
            print(sub.to_string())
        else:
            print(code, "未找到")
except Exception as e:
    print("FAIL:", repr(e)[:400])
