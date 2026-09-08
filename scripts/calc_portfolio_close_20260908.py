# -*- coding: utf-8 -*-
"""2026-09-08 盘后组合估值: 基准 portfolio_preopen_20260908(9/7全量净值 384,808.58)
+ 当日真实收盘(个股/ETF/已出净值) + 指数/ETF 代理(未出净值场外) → portfolio_close_20260908.json"""
import json, os
from collections import defaultdict

BASE = '/Users/jieyang/Documents/WealthHub'
HIST = os.path.join(BASE, 'data/processed/history')
TODAY = '2026-09-08'

with open(os.path.join(HIST, 'portfolio_preopen_20260908.json'), encoding='utf-8') as f:
    base = json.load(f)
with open(os.path.join(HIST, 'close_20260908.json'), encoding='utf-8') as f:
    close = json.load(f)

ETF_PCT = {e['code']: e['pct'] for e in close['etf']}
NAV_REAL = {r['code']: r['pct'] for r in close['fund_navs'] if r['nav_date'] == '2026-09-08' and r['pct'] is not None}
print('当日真实净值已出:', NAV_REAL)

MED_ETF_AVG = round((ETF_PCT.get('512170', 0) + ETF_PCT.get('159938', 0)) / 2, 2)  # (1.19+0.47)/2=0.83

# code -> 当日估算涨跌(%)
CODE_PCT = {
    # 个股真实收盘
    '002410': 0.68,   # 广联达 8.87 真实收盘 (+0.68, 盘中最高8.94仍未触9.0)
    '600438': 1.63,   # 通威 11.86 真实收盘
    # 场内ETF 真实收盘
    '513050': ETF_PCT.get('513050', 0), '159928': ETF_PCT.get('159928', 0),
    '159938': ETF_PCT.get('159938', 0), '512170': ETF_PCT.get('512170', 0),
    '513180': ETF_PCT.get('513180', 0), '159920': ETF_PCT.get('159920', 0),
    '512880': ETF_PCT.get('512880', 0), '515180': ETF_PCT.get('515180', 0),
    '512980': ETF_PCT.get('512980', 0),
    # 场外: 当日已出真实净值
    '000051': NAV_REAL.get('000051'),   # 华夏沪深300联接 -0.34
    '100032': NAV_REAL.get('100032'),   # 富国红利增强 +1.24
    # 场外: 指数/ETF 代理 (未出)
    '000248': 0.00,   # 主要消费 → 消费ETF 0.00 (中证消费 -0.00 平盘)
    '519915': 0.10,   # 富国消费主题主动(含非白酒,白酒弱农业零售强)
    '000968': 0.40,   # 养老(医药+消费 混合)
    '004424': 0.00,   # 文体娱乐(传媒0+消费0)
    '012323': 1.19,   # 华宝医疗C → 医疗ETF +1.19
    '001180': MED_ETF_AVG,   # 广发医药卫生 → ETF均值 0.83
    '002708': 0.80,   # 大摩健康(CXO/创新药, CXO爆发但创新药权重分化)
    '161616': 1.19,   # 融通医疗保健 → 医疗ETF
    '000727': 0.80,   # 融通健康(CXO)
    '001551': MED_ETF_AVG,   # 天弘医药100C
    '012348': ETF_PCT.get('513180', 0),   # 恒科QDII → 恒指科技ETF -1.58
    '000071': ETF_PCT.get('159920', 0),   # 恒生ETF联接 → 恒生ETF华夏 -0.60
    '164906': ETF_PCT.get('513050', 0),   # 交银海外互联 → 中概互联ETF -0.67
    '000369': -0.27, '016280': -0.27,   # QDII美股医疗: C类9/7净值补更-0.27(基准未含), A用C近似
    '110020': -0.36,  # 易方达沪深300联接 → 沪深300 -0.36
    '001552': -0.80,  # 天弘证券保险(证券-0.55/保险弱-港股平安-1.78人寿-3.08)
    '001469': 0.10,   # 广发金融地产(地产涨银行弱 对冲)
    '005368': 0.80,   # 富国清洁能源(通威+1.63光伏 锂电拖累)
    '004752': ETF_PCT.get('512980', 0),  # 广发传媒 → 传媒ETF 0.00
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
    'as_of': '2026-09-08收盘(代理口径,场外净值T+1)',
    'base_total': base_total,
    'est_total_pct': total_pct,
    'est_total_pnl': round(total_pnl, 2),
    'total_mv': round(new_total, 2),
    'tracks': tracks_out,
    'med_exposure': round(med_exp, 2),
    'med_pct': round(med_exp / new_total * 100, 2),
    'detail': detail,
    'note': '当日2只场外净值已出(富国红利增强+1.24/华夏沪深300-0.34);广联达8.87(+0.68)盘中最高8.94未触9.0减仓顺延/通威11.86(+1.63)真实收盘;医疗ETF+1.19午后CXO爆发(医药生物+1.12);恒科4,454.85(-1.61)跌破4,500收盘确认→明日减仓0.5%;QDII美股医疗C类9/7净值-0.27%补更(A用C近似,基准未含)'
}
with open(os.path.join(HIST, 'portfolio_close_20260908.json'), 'w', encoding='utf-8') as f:
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
