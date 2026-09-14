# -*- coding: utf-8 -*-
"""2026-09-14 盘后组合估值: 基准 = 9/11 盘后归档 373,320.35（与盘中档同口径）
+ 当日真实收盘(个股/ETF/已出净值) + 指数/ETF 代理(未出净值场外) + QDII 9/9→9/11 净值补更
→ portfolio_close_20260914.json"""
import json, os
from collections import defaultdict

BASE = '/Users/jieyang/Documents/WealthHub'
HIST = os.path.join(BASE, 'data/processed/history')
TODAY = '2026-09-14'
BASE_TOTAL = 373320.35   # 9/11 盘后归档口径（§3.79 规则：以盘后归档值为当日涨跌基准）

with open(os.path.join(HIST, 'portfolio_preopen_20260914.json'), encoding='utf-8') as f:
    base = json.load(f)
with open(os.path.join(HIST, 'close_20260914.json'), encoding='utf-8') as f:
    close = json.load(f)

ETF_PCT = {e['code']: e['pct'] for e in close['etf']}
NAV_REAL = {r['code']: r['pct'] for r in close['fund_navs'] if r['nav_date'] == TODAY and r['pct'] is not None}
NAV_0911 = {r['code']: r['pct'] for r in close['fund_navs'] if r['nav_date'] == '2026-09-11' and r['pct'] is not None}
STK = {s['name']: s for s in close['stocks']}

print('当日(9/14)真实净值已出:', {k: v for k, v in NAV_REAL.items()})
print('9/11 净值(补更):', {k: NAV_0911.get(k) for k in ['000369', '016280']})
print('个股真实收盘:', {k: (v['close'], v['pct']) for k, v in STK.items()})
print('ETF收盘:', ETF_PCT)

MED_ETF_AVG = round((ETF_PCT.get('512170', 0) + ETF_PCT.get('159938', 0)) / 2, 2)
print('医药ETF均值:', MED_ETF_AVG)

# QDII 补更：base(373,320.35) 含 9/9 净值 2.542/2.500；最新 9/11 净值 2.520/2.477
QDII_A = round((2.5200 / 2.5420 - 1) * 100, 2)   # -0.87
QDII_C = round((2.4770 / 2.5000 - 1) * 100, 2)   # -0.92
print('QDII 补更 A/C:', QDII_A, QDII_C)

CODE_PCT = {
    # 个股真实收盘
    '002410': STK['广联达']['pct'],      # +1.22
    '600438': STK['通威股份']['pct'],    # +1.99
    # 场内ETF 真实收盘
    '513050': ETF_PCT.get('513050', 0), '159928': ETF_PCT.get('159928', 0),
    '159938': ETF_PCT.get('159938', 0), '512170': ETF_PCT.get('512170', 0),
    '513180': ETF_PCT.get('513180', 0), '159920': ETF_PCT.get('159920', 0),
    '512880': ETF_PCT.get('512880', 0), '515180': ETF_PCT.get('515180', 0),
    '512980': ETF_PCT.get('512980', 0),
    # 场外 A股类: 9/14 真实净值已出
    '000968': NAV_REAL.get('000968'),    # +0.46
    '004752': NAV_REAL.get('004752'),    # -1.08
    '005368': NAV_REAL.get('005368'),    # -0.13
    '100032': NAV_REAL.get('100032'),    # -0.31
    '001551': NAV_REAL.get('001551'),    # +1.73
    '001552': NAV_REAL.get('001552'),    # -0.32
    '004424': NAV_REAL.get('004424'),    # +0.45
    '001180': NAV_REAL.get('001180'),    # +2.02
    '161616': NAV_REAL.get('161616'),    # +3.63
    '000051': NAV_REAL.get('000051'),    # -0.63
    '110020': NAV_REAL.get('110020'),    # -0.63
    '519915': NAV_REAL.get('519915'),    # +0.55
    '012348': NAV_REAL.get('012348'),    # -0.14
    '000248': NAV_REAL.get('000248'),    # -0.20
    '001469': NAV_REAL.get('001469'),    # +0.27
    '000727': NAV_REAL.get('000727'),    # +1.48
    '002742': 0.08,                      # 泓德裕祥债券A 9/14 真实净值 +0.08%（F10 补抓）
    '002708': NAV_REAL.get('002708'),    # 大摩健康产业混合A 9/14 真实净值 +4.50%（F10 补抓）
    # QDII 美股医疗: 9/9→9/11 补更
    '000369': QDII_A, '016280': QDII_C,
    # 场外未出净值 → 代理
    '012323': ETF_PCT.get('512170', 0),        # 华宝中证医疗C → 中证医疗(医疗ETF) +2.14
    '000071': ETF_PCT.get('159920', 0),        # 恒生ETF联接 → 恒生ETF华夏 +0.34
    '164906': ETF_PCT.get('513050', 0),        # 交银海外互联 → 中概互联ETF -0.30
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
total_pct = round(total_pnl / BASE_TOTAL * 100, 2)

tracks = defaultdict(lambda: {'mv': 0.0, 'pnl': 0.0})
for d in detail:
    t = d['track']
    tracks[t]['mv'] += d['mv']
    tracks[t]['pnl'] += d['est_pnl']
tracks_out = {}
for t, v in tracks.items():
    tracks_out[t] = {'mv': round(v['mv'], 2), 'pnl': round(v['pnl'], 2),
                     'pct_of_total': round(v['mv'] / BASE_TOTAL * 100, 2),
                     'day_pct': round(v['pnl'] / v['mv'] * 100, 2) if v['mv'] else 0}

med_exp = tracks_out.get('A股医药', {}).get('mv', 0) + tracks_out.get('美股标普医药', {}).get('mv', 0)
new_total = BASE_TOTAL + total_pnl

out = {
    'date': TODAY,
    'as_of': '2026-09-14收盘(场外净值16只已出/3只T+1代理/QDII 9/11补更)',
    'base_total': BASE_TOTAL,
    'est_total_pct': total_pct,
    'est_total_pnl': round(total_pnl, 2),
    'total_mv': round(new_total, 2),
    'tracks': tracks_out,
    'med_exposure': round(med_exp, 2),
    'med_pct': round(med_exp / new_total * 100, 2),
    'detail': detail,
    'note': ('9/14 收盘: 医药ETF广发+2.43%/医疗ETF+2.14%/融通医疗保健净值+3.63%/广发医药卫生+2.02%/天弘医药100C+1.73%;'
             '中证消费12,324.03(-0.21%)守12,300未收复12,400;恒生科技4,317.94(-0.06%)守住4,300;'
             '广联达8.33(+1.22%)/通威11.27(+1.99%);QDII 9/9→9/11补更(-0.87%/-0.92%,含XLV 9/10 -0.55%与9/11 -0.18%);'
             '未出净值代理: 012323→医疗ETF+2.14 / 000071→恒生ETF华夏+0.34 / 164906→中概互联-0.30')
}
with open(os.path.join(HIST, 'portfolio_close_20260914.json'), 'w', encoding='utf-8') as f:
    json.dump(out, f, ensure_ascii=False, indent=1)

print(f"\n组合当日估算: {out['est_total_pct']}% ({out['est_total_pnl']:+,.2f} 元), 总资产 {out['total_mv']:,.2f}")
for t, v in sorted(tracks_out.items(), key=lambda kv: -kv[1]['pct_of_total']):
    print(f"  {t:10s} mv={v['mv']:>11,.2f} 占比={v['pct_of_total']:>5.2f}% 当日={v['day_pct']:+.2f}% pnl={v['pnl']:+,.2f}")
print(f"医药总敞口: {out['med_pct']:.2f}% ({out['med_exposure']:,.2f})")
print('未匹配持仓:', missing if missing else '无')
top = sorted([d for d in detail if abs(d['est_pnl']) > 20], key=lambda x: -abs(x['est_pnl']))[:14]
print('\n主要贡献:')
for d in top:
    print(f"  {d['name'][:24]:26s} {d['est_pct']:+.2f}% -> {d['est_pnl']:+,.2f} 元")
