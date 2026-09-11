# -*- coding: utf-8 -*-
"""2026-09-11 盘后: 防御式补齐盘中 news/sentiment 缺失的 track/strength 字段 (§3.64/§3.75)"""
import json, os

BASE = '/Users/jieyang/Documents/WealthHub'
ND = os.path.join(BASE, 'data/processed/news')
NEWS_FILE = os.path.join(ND, 'news-2026-09-11.json')
SENT_FILE = os.path.join(ND, 'sentiment-2026-09-11.json')

RULES = [
    (['医药生物', '创新药', '医疗', 'CRO', '药明', '恒瑞', '百济', 'BD', '集采', '医保', '疫苗'], 'A股医药'),
    (['恒生科技', '港股', '南向', '恒指', '科网', '阿里', '腾讯', '小米', '智谱', 'MINIMAX'], '恒生科技'),
    (['消费', '白酒', '茅台', '五粮液', '食品饮料', '餐饮', '零售', '猪'], '大消费'),
    (['XLV', 'IYH', '美股医药', 'FDA', '阿斯利康', '礼来'], '美股标普医药'),
    (['收评', '沪指', '上证', '创业板', '深成指', '科创', '北证', '成交', '主力资金', 'CPI', 'PPI', '美债', '油价', '美联储', '加息', '央行', '财政'], '宏观'),
]


def guess_track(title):
    for kws, t in RULES:
        for k in kws:
            if k in title:
                return t
    return '其他/宽基'


for path in (NEWS_FILE, SENT_FILE):
    with open(path, encoding='utf-8') as f:
        arr = json.load(f)
    fixed = 0
    for x in arr:
        t = x.get('title') or ''
        if not x.get('track'):
            x['track'] = guess_track(t)
            fixed += 1
        if path == SENT_FILE and not x.get('strength'):
            x['strength'] = x.get('score', 50)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(arr, f, ensure_ascii=False, indent=1)
    print(f'{os.path.basename(path)}: 补 track {fixed} 条')
