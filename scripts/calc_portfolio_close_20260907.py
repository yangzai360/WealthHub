# -*- coding: utf-8 -*-
"""2026-09-07 盘后组合估值: 基准 portfolio_preopen_20260907(9/4净值全量 386,298.22)
+ 当日真实收盘(个股/ETF/已出净值) + 指数/ETF 代理(未出净值场外) → portfolio_close_20260907.json"""
import json, os
from collections import defaultdict

BASE = '/Users/jieyang/Documents/WealthHub'
HIST = os.path.join(BASE, 'data/processed/history')
TODAY = '2026-09-07'

with open(os.path.join(HIST, 'portfolio_preopen_20260907.json'), encoding='utf-8') as f:
    base = json.load(f)
with open(os.path.join(HIST, 'close_20260907.json'), encoding='utf-8') as f:
    close = json.load(f)

ETF_PCT = {e['code']: e['pct'] for e in close['etf']}
# 9/7 当日已出净值 (真实)
NAV_REAL = {r['code']: r['pct'] for r in close['fund_navs'] if r['nav_date'] == '2026-09-07' and r['pct'] is not None}
print('当日真实净值已出:', NAV_REAL)

MED_ETF_AVG = round((ETF_PCT.get('512170', 0) + ETF_PCT.get('159938', 0)) / 2, 2)  # -0.45

# code -> 当日估算涨跌(%)
CODE_PCT = {
    # 个股真实收盘
    '002410': -0.56,   # 广联达 8.81 真实收盘
    '600438': 2.46,    # 通威 11.67 真实收盘
    # 场内ETF 真实收盘
    '513050': ETF_PCT.get('513050', 0), '159928': ETF_PCT.get('159928', 0),
    '159938': ETF_PCT.get('159938', 0), '512170': ETF_PCT.get('512170', 0),
    '513180': ETF_PCT.get('513180', 0), '159920': ETF_PCT.get('159920', 0),
    '512880': ETF_PCT.get('512880', 0), '515180': ETF_PCT.get('515180', 0),
    '512980': ETF_PCT.get('512980', 0),
    # 场外: 当日已出真实净值
    '519915': NAV_REAL.get('519915'), '001551': NAV_REAL.get('001551'), '001469': NAV_REAL.get('001469'),
    # 场外: 指数/ETF 代理 (未出)
    '000248': -0.58,   # 主要消费 → 159928
    '000968': -0.40,   # 养老(医药+消费)
    '004424': 0.30,    # 文体娱乐(传媒+消费)
    '012323': -0.59,   # 华宝医疗C → 医疗ETF
    '001180': MED_ETF_AVG,   # 广发医药卫生 → ETF均值
    '002708': -0.45,   # 大摩健康主动(CXO权重)
    '161616': -0.45,   # 融通医疗主动
    '000727': -0.45,   # 融通健康(CXO)
    '012348': ETF_PCT.get('513180', 0),   # 恒科QDII → 恒指科技ETF
    '000071': ETF_PCT.get('159920', 0),   # 恒生ETF联接 → 恒生ETF华夏
    '164906': ETF_PCT.get('513050', 0),   # 交银海外互联 → 中概互联ETF
    '000369': 0.0, '016280': 0.0,   # 广发全球医疗 QDII (停9/4, 美股9/7休市, XLV 9/4 -1.04% 待9/8-9兑现)
    '000051': 0.59, '110020': 0.59,  # 沪深300联接 → 沪深300 +0.59%
    '001552': -1.30,  # 天弘证券保险(证券-1.27/保险更弱)
    '005368': 1.00,   # 富国清洁能源(通威+2.46光伏, 锂电拖累)
    '100032': -1.00,  # 富国红利增强(红利-1.17)
    '004752': ETF_PCT.get('512980', 0),  # 广发传媒 → 传媒ETF +1.52
    '002742': 0.05,   # 泓德裕祥债券
}

detail = []
missing = []
for x in base['detail']:
    code6 = ''.join(c for c in x['code'] if c.isdigit())
    name = x['name']
    if '现金' in name or '余额宝' in name or code6 == '':
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
    'as_of': '2026-09-07收盘(代理口径,场外净值T+1)',
    'base_total': base_total,
    'est_total_pct': total_pct,
    'est_total_pnl': round(total_pnl, 2),
    'total_mv': round(new_total, 2),
    'tracks': tracks_out,
    'med_exposure': round(med_exp, 2),
    'med_pct': round(med_exp / new_total * 100, 2),
    'detail': detail,
    'note': '当日3只场外净值已出(富国消费-0.53/医药100C-0.46/金融地产-1.51);广联达8.81(-0.56)/通威11.67(+2.46)真实收盘;QDII美股医疗按0(停9/4,XLV 9/4 -1.04% 待9/8-9兑现);恒科QDII用恒指科技ETF代理'
}
with open(os.path.join(HIST, 'portfolio_close_20260907.json'), 'w', encoding='utf-8') as f:
    json.dump(out, f, ensure_ascii=False, indent=1)

print(f"\n组合当日估算: {out['est_total_pct']}% ({out['est_total_pnl']:+,.2f} 元), 总资产 {out['total_mv']:,.2f}")
for t, v in tracks_out.items():
    print(f"  {t:8s} mv={v['mv']:>10,.2f} 占比={v['pct_of_total']:>5.2f}% 当日={v['day_pct']:+.2f}% pnl={v['pnl']:+,.2f}")
print(f"医药总敞口: {out['med_pct']:.2f}%")
print('未匹配持仓:', missing if missing else '无')
# 主要贡献
top = sorted([d for d in detail if abs(d['est_pnl']) > 20], key=lambda x: -abs(x['est_pnl']))[:10]
print('\n主要贡献:')
for d in top:
    print(f"  {d['name']}: {d['est_pct']}% -> {d['est_pnl']:+,.2f} 元")
