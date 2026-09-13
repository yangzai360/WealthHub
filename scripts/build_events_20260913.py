# -*- coding: utf-8 -*-
"""2026-09-13 周日盘后档事件库:
   1) 回填 9/11 遗留事件 N20260911-014（阿斯利康，用 XLV 9/11 -0.18%）
   2) 生成周末事件 events-2026-09-13.json（19 条，track 按赛道名归类）
"""
import json, os

BASE = '/Users/jieyang/Documents/WealthHub'
EV = os.path.join(BASE, 'data/processed/events')
NEWS = os.path.join(BASE, 'data/processed/news')

# ---------- 1. 回填 9/11 遗留 ----------
p11 = os.path.join(EV, 'events-2026-09-11.json')
ev11 = json.load(open(p11, encoding='utf-8'))
filled = []
for e in ev11:
    if e.get('id') == 'N20260911-014':
        e.setdefault('reference', {})['actual_ret_1d'] = -0.18
        e['reference']['actual_date'] = '2026-09-11'
        e['reference']['ret_1d_ref'] = 'XLV 9/11(美东周五)收盘 165.36(-0.18%)'
        filled.append(e['id'])
json.dump(ev11, open(p11, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(f'回填 {filled}')

# ---------- 2. 周末事件 ----------
sent = json.load(open(os.path.join(NEWS, 'sentiment-2026-09-13.json'), encoding='utf-8'))['items']

titles = [
 "美国8月CPI同比+3.4%符合预期, 核心CPI环比+0.3%超预期——CME 9月加息概率69.6%→86.7%-90%",
 "美股9/11(美东周五)三大指数集体收涨终结四连跌: 道指+0.98%/标普+0.86%/纳指+0.96%, 医疗板块-0.14%为唯二下跌",
 "密歇根大学9月消费者信心初值47.8大幅低于预期51.4与前值51.7",
 "中东局势急变: 胡塞控制也门整个西部海岸+沙特东西输油管道遭袭预防性关闭+9/14阿曼会谈",
 "习近平出席金砖国家领导人第十八次会晤(新德里)提5项倡议, 中国2027年接任金砖主席国",
 "国常会强调完善算力基础设施与骨干光纤网络建设; 中国算力大会15项重大突破成果揭晓",
 "证监会发布《期货公司监督管理办法》+查处*ST卓然财务造假启动退市; 8月线下消费支付金额同比+2.6%",
 "高盛转鹰预计美联储9月加息25bp; Anthropic拟IPO募资至多1000亿美元、英伟达或投100亿",
 "港股本周连续5日调整: 恒指-3.30%报24,805.63/恒生科技-5.45%报4,320.57, 有色与大模型概念拖累",
 "南向资金9/11净买入44.31亿港元连续第5日; 7月以来净买入985.8亿港元, 恒指同期+8.41%领先全球",
 "下周港股政策催化: 香港新一版施政报告与五年规划发布 + 中证港股通人工智能应用指数9/21发布",
 "2026医保国谈收官: 124个目录外药品入围、12个商保创新药, CAR-T首次进谈判场, 新版目录11月发布",
 "国家药监局化学创新药工艺验证资料要求征求意见——全球同步申报品种可滚动提交, 利好创新药出海",
 "创新药长周期逻辑验证: 科创板28家2025年首次整体扭亏, 百济神州26H1净利+627.1%, 出海升级为全球分账",
 "飞天茅台批价企稳: 9/12散瓶1725(+5)/原箱1745(+5), 9/13持平; 五粮液普五批价790元",
 "茅台9/12启动企业直采通道: 飞天直供价1639元/瓶砍掉省代市代黄牛, 「全面向C」战略深化",
 "白酒板块本周-3.78%申万排名27/31; 56.6%经销商价格倒挂加剧、61.9%终端门店规模收缩; 8月酒类价格同比-2.9%",
 "美股医疗9/11为标普11大板块唯二下跌之一(-0.14%): XLV 165.36(-0.18%)/IYH 69.92(-0.11%)",
 "美股医药产业: Exelixis肠癌联合疗法NDA审评延期3个月; Vesremi获FDA扩大适应症; 类器官AI分析工具发表",
]
urls = [
 "https://www.stcn.com/article/detail/4182499.html",
 "https://www.cnfin.com/gs-lb/detail/20260912/4469035_1.html",
 "https://www.cnfin.com/gs-lb/detail/20260912/4469035_1.html",
 "https://www.cnstock.com/commonDetail/789406",
 "https://news.qq.com/rain/a/20260913A02WIA00",
 "https://www.toutiao.com/article/7684924529931452974/",
 "https://so.html5.qq.com/page/real/search_news?docid=70000021_2506aa663b366252",
 "https://news.qq.com/rain/a/20260913A02WIA00",
 "https://xueqiu.com/2753428279/409049370",
 "https://www.163.com/dy/article/L6K512B70552C2FY.html",
 "https://caifuhao.eastmoney.com/news/20260912000402132532840",
 "https://www.toutiao.com/article/7684616304438821427/",
 "https://so.html5.qq.com/page/real/search_news?docid=70000021_9636aa679d234252",
 "https://www.toutiao.com/article/7684616304438821427/",
 "https://xueqiu.com/1553736910/409099609",
 "",
 "https://stock.finance.sina.com.cn/stock/go.php/vReport_Show/kind/lastest/rptid/842621460148/index.phtml",
 "https://www.cnfin.com/gs-lb/detail/20260912/4469035_1.html",
 "",
]
cat_map = {
 "宏观": ["宏观类"] * 8,
 "恒生科技": ["行业事件类", "行业事件类", "政策类"],
 "A股医药": ["政策类", "政策类", "业绩类"],
 "大消费": ["行业事件类", "行业事件类", "行业事件类"],
 "美股标普医药": ["行业事件类", "行业事件类"],
}

events = []
trk_seq = {}
for i, o in enumerate(sent):
    t = o['track']
    k = trk_seq.get(t, 0)
    trk_seq[t] = k + 1
    events.append({
        "id": f"N20260913-{i+1:03d}",
        "date": "2026-09-13",
        "track": t,
        "category": cat_map[t][k],
        "title": titles[i],
        "summary": o['brief'],
        "source": "WebSearch(周末窗口)",
        "source_url": urls[i],
        "sentiment": o['sentiment'],
        "score": o['strength'],
        "strength": o['strength'],
        "direction": o['direction'],
        "volatility": o['volatility'],
        "reason": o['brief'],
        "reference": {"actual_ret_1d": None, "actual_date": None,
                      "ret_1d_ref": "待 2026-09-14(周一)收盘回填"},
    })
# 修正说明: category 已按轨道内序号在循环中直接赋值

out = os.path.join(EV, 'events-2026-09-13.json')
json.dump(events, open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(f'SAVED {out}  n={len(events)}')
from collections import Counter
print(Counter(e['track'] for e in events))
