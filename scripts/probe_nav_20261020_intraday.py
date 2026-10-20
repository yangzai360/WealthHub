# -*- coding: utf-8 -*-
"""2026-10-20 盘中档：场外净值最新日期抽查（QDII 是否出 10/19、港股联接与 A股基金最新净值日）"""
import akshare as ak
codes = {
    "000369": "广发全球医疗保健A", "016280": "广发全球医疗保健C",
    "164906": "交银中证海外中国互联网LOF", "000071": "恒生ETF联接A", "012348": "天弘恒生科技联接A",
    "002708": "大摩健康产业A", "161616": "融通医疗保健", "012323": "华宝中证医疗联接C",
}
for c, n in codes.items():
    try:
        df = ak.fund_open_fund_info_em(symbol=c, indicator="单位净值走势")
        d = df.tail(3)
        print(f"{c} {n:12s} -> " + " | ".join(f"{str(r['净值日期'])[:10]}={r['单位净值']}" for _, r in d.iterrows()))
    except Exception as e:
        print(c, n, "FAIL", str(e)[:60])
