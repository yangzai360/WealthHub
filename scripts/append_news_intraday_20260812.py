#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""2026-08-12 盘中档: 追加新闻 JSON + DeepSeek 情绪标注
窗口: 8/12 07:30 - 13:30 新增
产出: news-2026-08-12.json / sentiment-2026-08-12.json (追加)
"""
import json, os, urllib.request, sys, time

BASE = "/Users/jieyang/Documents/WealthHub"
NEWS = os.path.join(BASE, "data/processed/news")
NEWS_FILE = os.path.join(NEWS, "news-2026-08-12.json")
SENT_FILE = os.path.join(NEWS, "sentiment-2026-08-12.json")

# ---------- 1. 盘中新增新闻条目 ----------
new_news = [
 {
  "id": "N20260812-013", "track": "A股医药", "category": "行业事件类",
  "title": "百花医药7连板！政策助推药企出海 创新药板块延续强势 医药ETF(512120)跌0.40% 生物医药ETF涨0.23%",
  "summary": "8/12早盘创新药概念延续强势：百花医药7连板成为板块核心标的（截至10:50，医药ETF 512120 -0.40%、生物医药ETF 159508 +0.23%、港股通生物科技ETF 159102 -0.61%；新和成+2.40%、康龙化成+1.98%、凯莱英+0.65%）。催化来自上海市商务委等七部门印发《上海市国家服务贸易创新发展示范区建设方案》，明确支持生物医药产业创新发展，鼓励创新药、现代中药、高端医疗器械开展全球注册认证并推动出海销售。机构关注：创新药最受关注，其次科研服务和CXO，ADC/PD1PLUS/小核酸/自免细分突出，AI制药为新兴方向。",
  "source": "WebSearch/每日经济新闻",
  "source_url": "https://www.nbd.com.cn/articles/2026-08-12/4539395.html",
 },
 {
  "id": "N20260812-014", "track": "A股医药", "category": "行业事件类",
  "title": "创新药高位分歧加剧：百花医药7连板后发布风险提示（Q1净利-67.94% PE 184倍）CRO领跌 诚达药业-10.19%",
  "summary": "8/12盘初创新药持续活跃但高位分歧加剧：百花医药7连板（8/4-8/11六个交易日涨停涨幅77.07%）后公司发布股票交易风险提示，称公司是小分子化学仿制药研发为主的CRO企业、不涉及创新药研发，主营业务未发生重大变化，Q1营收6718万(-30.68%)、净利664万(-67.94%)，滚动PE 184.25倍（同行34.96倍）；万邦医药+6.12%、誉衡药业+9.40%跟涨，但CRO/工业金属板块跌幅居前，诚达药业-10.19%（主力净流出1.34亿）、羚锐制药-8.91%，创新药内部涨跌分化明显。",
  "source": "WebSearch/证券时报+上证报",
  "source_url": "https://www.stcn.com/article/detail/4071003.html",
 },
 {
  "id": "N20260812-015", "track": "大消费", "category": "行业事件类",
  "title": "8/12酒价11大单品六涨三平两跌：精品茅台2454元续创近月新高 飞天1789元创7/18调价以来最高 总价10022元破万",
  "summary": "新浪酒价内参8/12数据显示：白酒11大单品六涨三平两跌，盘面分化显著。上涨：精品茅台放量大涨22元至2454元（连续三天单日涨幅超10元、续创近一个月新高）、飞天茅台+8元至1789元（创7/18上调价格以来最高纪录）、青花汾20 +1元至391元、洋河梦之蓝M6+ +7元至599元、古井贡古20 +7元至534元（三连阳创20多天新高）、习酒君品+6元至637元；下跌：国窖1573 -8元至882元（技术性调整）、青花郎-7元至699元（三连跌失守700元）；五粮液普五/1618/水晶剑平稳（808/826/403元）。11大单品总价10022元较昨日+36元，创3月下旬以来新高、突破万元整数关。",
  "source": "WebSearch/新浪财经酒价内参",
  "source_url": "https://k.sina.com.cn/article_5953466437_162dab0450670b8noo.html",
 },
 {
  "id": "N20260812-016", "track": "大消费", "category": "行业事件类",
  "title": "白酒板块有望率先实现估值修复：今世缘领涨7.48% 中证主要消费-0.10% 开源证券：板块估值处近年底部",
  "summary": "截至8/12 11:00，中证主要消费指数-0.10%，成分股涨跌互现：今世缘领涨7.48%、古井贡酒+2.52%、乖宝宠物+2.07%，圣农发展领跌、金龙鱼/双汇跟跌。国海证券指出美股消费龙头长期表现优异的核心支撑在于消费主导经济+品牌护城河+长线资金偏好；开源证券指出目前白酒板块估值已处于近年来底部、筹码结构优化，龙头企业凭借品牌壁垒/渠道掌控力/定价权在调整期展现更强韧性，有望率先实现估值修复和业绩兑现。中证主要消费前十大权重合计68.18%（茅台/伊利/五粮液/牧原/温氏/泸州老窖/海天/汾酒/海大/东鹏）。",
  "source": "WebSearch/新浪财经",
  "source_url": "https://cj.sina.com.cn/articles/view/5182171545/134e1a99902002i3x4?finpagefr=p_104",
 },
 {
  "id": "N20260812-017", "track": "恒生科技", "category": "行业事件类",
  "title": "港股午评：恒指-1.17%恒生科技-1.17%报4767.88 腾讯跌近3%阿里跌超3%美团跌近2% 芯片股逆势走强（华虹+7%）",
  "summary": "8/12港股午间收盘：恒指-1.17%（报25352.13）、国企指数-1.27%（8420.08）、恒生科技-1.17%（4767.88），三大指数延续昨日低迷。大型科网股普跌：腾讯控股-2.9%（收458.80、-2.55%）、阿里巴巴-W-3.24%、京东-3%、百度-2%、美团-1.88%、小米-1.58%、B站-3.69%、网易-3.50%、腾讯音乐-SW-13.59%；云办公/手游/云计算/乳制品/航空/石油/教育齐跌。逆势：存储半导体/光通信走强（华虹宏力+7.13%、中芯国际+3%、澜起科技+7%、兆易创新+6%），内房股普涨（'十五五'城市更新+北京限购松绑），太阳能走强（协鑫科技+3.47%）。",
  "source": "WebSearch/财联社+格隆汇",
  "source_url": "https://www.163.com/dy/article/L44NGGHC05198CJN.html",
 },
 {
  "id": "N20260812-018", "track": "恒生科技", "category": "业绩类",
  "title": "腾讯财报公布前夕港互联网股普跌：腾讯自8/5高点497.8回落近10%至458 高盛前瞻Q2收入+9%调整EBIT 752亿",
  "summary": "腾讯8/12盘后公布Q2财报，公布前夕港股互联网股普跌（恒生科技连续回调，8/11收4824.42 -1.93%）。腾讯已从8/5创出的497.8港元阶段高点回落到458港元（跌幅近10%）。高盛前瞻：腾讯Q2收入同比+9%、经调整EBIT同比+9%至752亿元人民币，焦点包括AI资本开支及资源分配优先次序、混元模型策略、游戏产品线及广告AI上行空间；阿里-W 8/20公布首财季业绩（预期收入+9%、经调整EBITA -33%至260亿）。机构认为当前市场悲观预期已充分定价，指数处于'中高赔率+高胜率'配置窗口期，短期关注中报业绩及AI商业化落地催化。",
  "source": "WebSearch/香港商报",
  "source_url": "https://hkcd.com/hkcdweb/content/2026/08/12/content_8769258.html",
 },
]

# ---------- 2. 追加到 news JSON ----------
with open(NEWS_FILE, encoding="utf-8") as f:
    news_all = json.load(f)
existing_ids = {n["id"] for n in news_all}
added = [n for n in new_news if n["id"] not in existing_ids]
news_all.extend(added)
with open(NEWS_FILE, "w", encoding="utf-8") as f:
    json.dump(news_all, f, ensure_ascii=False, indent=1)
print(f"[news] 追加 {len(added)} 条, 当前共 {len(news_all)} 条")

# ---------- 3. DeepSeek 情绪标注 ----------
with open("/Users/jieyang/.pi/agent/auth.json") as f:
    key = json.load(f)["deepseek"]["key"]

def ds_sentiment(item):
    prompt = f"""你是A股/港股医药、消费、科技赛道的情绪分析专家。请对以下财经新闻做情绪标注，输出 JSON。

新闻标题: {item['title']}
新闻摘要: {item['summary']}
所属赛道: {item['track']}

输出格式(仅JSON):
{{"sentiment": "正面|中性|负面", "strength": 0-100整数, "impact_direction": "利多|中性|利空", "expected_volatility": "低|中|高", "reason": "一句话理由"}}

要求: 情绪强度strength反映该事件对{item['track']}赛道短期（1-3日）影响的强度；expected_volatility反映该事件引发的赛道波动幅度预期。"""
    data = {
        "model": "deepseek-v4-flash",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 8000,
        "temperature": 0.3,
    }
    req = urllib.request.Request("https://api.deepseek.com/chat/completions",
        data=json.dumps(data).encode(),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        result = json.load(resp)
    content = result["choices"][0]["message"]["content"]
    if not content:
        raise ValueError("empty content (retry)")
    # 提取 JSON 部分
    start = content.find("{")
    end = content.rfind("}") + 1
    return json.loads(content[start:end])

# 读取现有 sentiment
if os.path.exists(SENT_FILE):
    with open(SENT_FILE, encoding="utf-8") as f:
        sent_all = json.load(f)
else:
    sent_all = []
sent_ids = {s["id"] for s in sent_all}

for item in added:
    if item["id"] in sent_ids:
        continue
    for attempt in range(3):
        try:
            r = ds_sentiment(item)
            sent_all.append({
                "id": item["id"], "track": item["track"], "category": item["category"],
                "title": item["title"], "source_url": item["source_url"],
                "sentiment": r["sentiment"], "strength": r["strength"],
                "impact_direction": r["impact_direction"],
                "expected_volatility": r["expected_volatility"],
                "reason": r["reason"],
            })
            print(f"  {item['id']} {item['track']} {r['sentiment']} {r['strength']} 波动:{r['expected_volatility']} | {r['reason'][:40]}")
            break
        except Exception as e:
            print(f"  {item['id']} 重试 {attempt+1}: {e}")
            time.sleep(2)

with open(SENT_FILE, "w", encoding="utf-8") as f:
    json.dump(sent_all, f, ensure_ascii=False, indent=1)
print(f"[sentiment] 当前共 {len(sent_all)} 条")
