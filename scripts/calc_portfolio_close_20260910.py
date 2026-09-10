# -*- coding: utf-8 -*-
"""2026-09-10 盘后组合估值: 基准 portfolio_preopen_20260910(9/9净值全量 + QDII 9/8兑现, 380,927.32)
+ 当日真实收盘(个股/ETF/已出净值) + 指数/ETF 代理(未出净值场外) → portfolio_close_20260910.json"""
import json, os
from collections import defaultdict

BASE = '/Users/jieyang/Documents/WealthHub'
HIST = os.path.join(BASE, 'data/processed/history')
TODAY = '2026-09-10'

with open(os.path.join(HIST, 'portfolio_preopen_20260910.json'), encoding='utf-8') as f:
    base = json.load(f)
with open(os.path.join(HIST, 'close_20260910.json'), encoding='utf-8') as f:
    close = json.load(f)

ETF_PCT = {e['code']: e['pct'] for e in close['etf']}
NAV_REAL = {r['code']: r['pct'] for r in close['fund_navs'] if r['nav_date'] == '2026-09-10' and r['pct'] is not None}
print('当日真实净值已出:', NAV_REAL)
STK = {s['name']: s for s in close['stocks']}
print('个股真实收盘:', {k: (v['close'], v['pct']) for k, v in STK.items()})

MED_ETF_AVG = round((ETF_PCT.get('512170', 0) + ETF_PCT.get('159938', 0)) / 2, 2)  # (-1.19-1.26)/2=-1.23
print('医药ETF均值:', MED_ETF_AVG)

# code -> 当日估算涨跌(%)
CODE_PCT = {
    # 个股真实收盘
    '002410': STK['广联达']['pct'],    # 广联达 8.39 (-1.87)
    '600438': STK['通威股份']['pct'],  # 通威 11.50 (-1.79)
    # 场内ETF 真实收盘
    '513050': ETF_PCT.get('513050', 0), '159928': ETF_PCT.get('159928', 0),
    '159938': ETF_PCT.get('159938', 0), '512170': ETF_PCT.get('512170', 0),
    '513180': ETF_PCT.get('513180', 0), '159920': ETF_PCT.get('159920', 0),
    '512880': ETF_PCT.get('512880', 0), '515180': ETF_PCT.get('515180', 0),
    '512980': ETF_PCT.get('512980', 0),
    # 场外: 当日已出真实净值(9/10)
    '005368': NAV_REAL.get('005368'),   # 富国清洁能源 -0.48
    '100032': NAV_REAL.get('100032'),   # 富国红利增强A -0.50
    '161616': NAV_REAL.get('161616'),   # 融通医疗保健 -1.08
    '519915': NAV_REAL.get('519915'),   # 富国消费主题 -0.92
    '004424': NAV_REAL.get('004424'),   # 汇添富文体娱乐 -1.50
    # 场外: 指数/ETF 代理 (未出)
    '000248': -1.80,   # 主要消费 → 中证消费 -1.80
    '000968': -1.30,   # 养老(医药+消费混合, 消费-1.80/医药-1.23)
    '001180': MED_ETF_AVG,   # 广发医药卫生 → ETF均值 -1.23
    '002708': -1.30,   # 大摩健康(CXO/创新药: CRO领跌深于ETF均值)
    '000727': -1.30,   # 融通健康(CXO)
    '001551': MED_ETF_AVG,   # 天弘医药100C
    '012323': MED_ETF_AVG,   # 华宝中证医疗联接C (9/10净值未出, 医疗ETF代理)
    '000071': ETF_PCT.get('159920', 0),   # 恒生ETF联接 → 恒生ETF华夏 -1.01
    '012348': ETF_PCT.get('513180', 0),   # 天弘恒生科技 → 恒指科技ETF -1.79
    '164906': ETF_PCT.get('513050', 0),   # 交银海外互联 → 中概互联ETF -1.85
    '000051': -0.53,   # 华夏沪深300联接 → 沪深300 -0.53
    '110020': -0.53,   # 易方达沪深300联接
    '001552': 0.20,    # 天弘证券保险(证券ETF +0.55 / 保险弱)
    '001469': 0.20,    # 广发金融地产(银行强/地产弱)
    '004752': ETF_PCT.get('512980', 0),  # 广发传媒 → 传媒ETF -1.30
    '002742': 0.03,    # 泓德裕祥债券
    '000369': 0.0, '016280': 0.0,   # QDII美股医疗: nav停9/8(基准已含), XLV 9/9 -0.33% 于9/11兑现
}

detail = []
missing = []
for x in base['detail']:
    code6 = ''.join(c for c in x['code'] if c.isdigit())
    name = x['name']
    if '现金' in name or '余额宝' in name or '帮你投' in name or code6 == '':
        pct = 0.0
    elif code6 in CODE_PCT and CODE_PCT[code6] is not None:
        pct = CODE_PCT[code6]
    else:
        pct = 0.0
        missing.append((code6, name))
    mv0 = float(x['mv'])
    detail.append({**x, 'est_pct': pct, 'est_pnl': round(mv0 * pct / 100, 2)})

total_pnl = sum(d['est_pnl'] for d in detail)
base_total = base['total_mv']
total_pct = round(total_pnl / base_total * 100, 2)

tracks = defaultdict(lambda: {'mv': 0.0, 'pnl': 0.0})
for d in detail:
    t = d['track']
    tracks[t]['mv'] += d['mv']
    tracks[t]['pnl'] += d['est_pnl']
tracks_out = {}
for t, v in tracks.items():
    tracks_out[t] = {'mv': round(v['mv'], 2), 'pnl': round(v['pnl'], 2),
                     'pct_of_total': round(v['mv'] / base_total * 100, 2),
                     'day_pct': round(v['pnl'] / v['mv'] * 100, 2) if v['mv'] else 0}

med_exp = tracks_out.get('A股医药', {}).get('mv', 0) + tracks_out.get('美股标普医药', {}).get('mv', 0)
new_total = base_total + total_pnl

out = {
    'date': TODAY,
    'as_of': '2026-09-10收盘(代理口径,场外净值T+1)',
    'base_total': base_total,
    'est_total_pct': total_pct,
    'est_total_pnl': round(total_pnl, 2),
    'total_mv': round(new_total, 2),
    'tracks': tracks_out,
    'med_exposure': round(med_exp, 2),
    'med_pct': round(med_exp / new_total * 100, 2),
    'detail': detail,
    'note': ('当日5只场外净值已出(富国清洁能源-0.48/富国红利增强A-0.50/融通医疗保健-1.08/富国消费主题-0.92/汇添富文体娱乐-1.50);'
             '广联达8.39(-1.87)真实收盘/通威11.50(-1.79);中证消费12,475.28(-1.80)收盘确认失守12,600→兑现0-0.5%预案触发;'
             '恒科4,330.49(-2.04)破4,400未破4,300不追加;医药ETF均值-1.23%未破-1.5%线持有;QDII nav停9/8(XLV9/9-0.33%于9/11兑现)')
}
with open(os.path.join(HIST, 'portfolio_close_20260910.json'), 'w', encoding='utf-8') as f:
    json.dump(out, f, ensure_ascii=False, indent=1)

print(f"\n组合当日估算: {out['est_total_pct']}% ({out['est_total_pnl']:+,.2f} 元), 总资产 {out['total_mv']:,.2f}")
for t, v in tracks_out.items():
    print(f"  {t:8s} mv={v['mv']:>10,.2f} 占比={v['pct_of_total']:>5.2f}% 当日={v['day_pct']:+.2f}% pnl={v['pnl']:+,.2f}")
print(f"医药总敞口: {out['med_pct']:.2f}%")
print('未匹配持仓:', missing if missing else '无')
top = sorted([d for d in detail if abs(d['est_pnl']) > 20], key=lambda x: -abs(x['est_pnl']))[:12]
print('\n主要贡献:')
for d in top:
    print(f"  {d['name']}: {d['est_pct']}% -> {d['est_pnl']:+,.2f} 元")
