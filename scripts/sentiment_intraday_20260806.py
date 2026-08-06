# -*- coding: utf-8 -*-
"""
盘中新闻情绪分析 (2026-08-06 13:45 档)
调用 DeepSeek v4-flash 对新增新闻输出情绪标签+强度分, 追加到 events 事件库
"""
import json, urllib.request, os, sys

# 读取 DeepSeek key
with open('/Users/jieyang/.pi/agent/auth.json') as f:
    auth = json.load(f)
key = auth['deepseek']['key']

BASE = "/Users/jieyang/Documents/WealthHub"

# 盘中新增新闻 (07:30-13:30 窗口, 已与盘前 8 条去重)
NEWS = [
    {"id": "N20260806-009", "date": "2026-08-06", "track": "恒生科技", "title": "港股午评:恒指跌1.75%,恒生科技跌1.87%,权重科技股普跌",
     "summary": "港股午间收盘,恒指跌1.75%报25463点,恒生科技跌1.87%。百度、阿里巴巴跌超3%,小米、京东跌超2%;芯片股下挫,中芯国际跌逾4%、华虹宏力跌超3%。",
     "source": "财联社", "time": "2026-08-06 12:03", "category": "行业事件类"},
    {"id": "N20260806-010", "date": "2026-08-06", "track": "恒生科技", "title": "港险保单收益开征20%个税,友邦保险跌8.75%",
     "summary": "据报港险保单收益开征20%个税,友邦保险跌8.75%,保诚跌5.8%,拖累港股金融板块情绪。",
     "source": "同花顺/智通财经", "time": "2026-08-06 12:03", "category": "政策类"},
    {"id": "N20260806-011", "date": "2026-08-06", "track": "恒生科技", "title": "光大证券对港股转中性:反弹后短期性价比下降,美联储加息概率上升压制估值",
     "summary": "光大证券称港股反弹核心驱动力是海外科技链调整期间亚太配置资金跷跷板迁移,但反弹后短期性价比下降,AH溢价收敛空间有限,且美联储加息概率上升可能压制估值,对港股转为中性评级。",
     "source": "光大证券", "time": "2026-08-06 上午", "category": "宏观类"},
    {"id": "N20260806-012", "date": "2026-08-06", "track": "A股医药", "title": "创新药概念持续强势:诺诚健华、荣昌生物涨超3%,百花医药3连板",
     "summary": "8月6日盘中创新药概念延续强势,陇神戎发涨超11%,百花医药、石药景峰涨停,华兰股份涨近10%,诺诚健华、荣昌生物涨超3%,万邦医药涨超7%。",
     "source": "格隆汇/金融界", "time": "2026-08-06 11:22", "category": "行业事件类"},
    {"id": "N20260806-013", "date": "2026-08-06", "track": "A股医药", "title": "科伦博泰SKB565新药临床试验获批,金斯瑞CARVYKTI销售大增",
     "summary": "科伦博泰生物(06990)午前涨3.8%,新型双载荷ADC药物SKB565新药临床试验申请获批;金斯瑞生物(01548)再涨超6%,本月中旬发业绩,上半年CARVYKTI销售同比大增。",
     "source": "智通财经", "time": "2026-08-06 12:03", "category": "行业事件类"},
    {"id": "N20260806-014", "date": "2026-08-06", "track": "大消费", "title": "九部委印发《关于加快零售业创新发展的意见》,消费券对接数字人民币",
     "summary": "商务部、央行等九部委联合印发意见,支持零售经营主体数字化改造,明确消费券发放、核销、结算全流程接入数字人民币,实现财政消费补贴精准下发,大规模拓宽线下实体支付场景。",
     "source": "每经/腾讯新闻", "time": "2026-08-06 上午", "category": "政策类"},
    {"id": "N20260806-015", "date": "2026-08-06", "track": "大消费", "title": "吃喝板块小幅回调,细分食品指数PE处于近10年4.89%分位",
     "summary": "食品ETF(515710)盘中微跌0.16%,东鹏饮料跌超2%、贵州茅台跌幅居前;细分食品指数市盈率20.05倍,位于近10年4.89%分位低位,恒泰/爱建证券提示白酒底部配置机会,今世缘预计行业实质性好转在2026下半年。",
     "source": "ETF盘中资讯/券商观点", "time": "2026-08-06 上午", "category": "行业事件类"},
    {"id": "N20260806-016", "date": "2026-08-06", "track": "美股标普医药", "title": "百时美施贵宝(BMY)跌3.43%,安进(AMGN)创52周新高",
     "summary": "美股8/5收盘:BMY跌3.43%报63.63美元(或受合并传闻降温影响),默沙东MRK涨0.26%报128.33,安进AMGN涨3.05%报401.91创52周新高,盘后继续涨1.81%。",
     "source": "公开行情", "time": "2026-08-06 04:00(美东)", "category": "行业事件类"},
]

prompt = f"""你是资深医药/消费/科技行业投研分析师。对以下 8 条财经新闻, 每条输出 JSON 格式的情绪分析:
{{
  "id": 新闻id,
  "sentiment": "正面|中性|负面",
  "strength": 0-100 的强度分,
  "impact_direction": "利多|利空|中性",
  "expected_volatility": "高|中|低",
  "reason": "一句话分析理由(40字内)"
}}

新闻列表:
{json.dumps(NEWS, ensure_ascii=False, indent=1)}

要求:
1. sentiment 只允许 正面/中性/负面; strength 按影响强度打分(重大业绩/政策≥70, 一般事件40-60, 弱影响<40)
2. impact_direction 只允许 利多/利空/中性
3. 只输出 JSON 数组, 不要输出任何其他文字或 markdown 代码块标记"""

data = {
    "model": "deepseek-v4-flash",
    "messages": [{"role": "user", "content": prompt}],
    "max_tokens": 8000,
    "temperature": 0.3,
}
req = urllib.request.Request("https://api.deepseek.com/chat/completions",
    data=json.dumps(data).encode(),
    headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
with urllib.request.urlopen(req, timeout=180) as resp:
    result = json.load(resp)
content = result['choices'][0]['message']['content']
if not content or not content.strip():
    print("[ERROR] DeepSeek content 为空, 退出", file=sys.stderr)
    sys.exit(1)
print(content)
