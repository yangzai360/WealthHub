# -*- coding: utf-8 -*-
"""2026-09-09 盘后组合估值: 基准 portfolio_preopen_20260909(9/8净值全量修正 385,461.42)
+ 当日真实收盘(个股/ETF/已出净值) + 指数/ETF 代理(未出净值场外) → portfolio_close_20260909.json"""
import json, os
from collections import defaultdict

BASE = '/Users/jieyang/Documents/WealthHub'
HIST = os.path.join(BASE, 'data/processed/history')
TODAY = '2026-09-09'

with open(os.path.join(HIST, 'portfolio_preopen_20260909.json'), encoding='utf-8') as f:
    base = json.load(f)
with open(os.path.join(HIST, 'close_20260909.json'), encoding='utf-8') as f:
    close = json.load(f)

ETF_PCT = {e['code']: e['pct'] for e in close['etf']}
NAV_REAL = {r['code']: r['pct'] for r in close['fund_navs'] if r['nav_date'] == '2026-09-09' and r['pct'] is not None}
print('当日真实净值已出:', NAV_REAL)

MED_ETF_AVG = round((ETF_PCT.get('512170', 0) + ETF_PCT.get('159938', 0)) / 2, 2)  # (-1.17-1.24)/2=-1.21

# code -> 当日估算涨跌(%)
CODE_PCT = {
    # 个股真实收盘
    '002410': -3.61,   # 广联达 8.55 真实收盘 (软件/高位题材退潮拖累)
    '600438': -1.26,   # 通威 11.71 真实收盘
    # 场内ETF 真实收盘
    '513050': ETF_PCT.get('513050', 0), '159928': ETF_PCT.get('159928', 0),
    '159938': ETF_PCT.get('159938', 0), '512170': ETF_PCT.get('512170', 0),
    '513180': ETF_PCT.get('513180', 0), '159920': ETF_PCT.get('159920', 0),
    '512880': ETF_PCT.get('512880', 0), '515180': ETF_PCT.get('515180', 0),
    '512980': ETF_PCT.get('512980', 0),
    # 场外: 当日已出真实净值
    '519915': NAV_REAL.get('519915'),   # 富国消费主题 -0.86
    '012348': NAV_REAL.get('012348'),   # 天弘恒生科技A -0.79
    '012323': NAV_REAL.get('012323'),   # 华宝医疗C -1.31
    # 场外: 指数/ETF 代理 (未出)
    '000248': -0.56,   # 主要消费 → 中证消费 -0.56
    '000968': -0.90,   # 养老(医药+消费混合)
    '004424': -3.00,   # 文体娱乐(传媒/游戏/AI应用重仓, 传媒ETF-2.76+游戏大跌)
    '001180': MED_ETF_AVG,   # 广发医药卫生 → ETF均值 -1.21
    '002708': -1.20,   # 大摩健康(CXO/创新药: 创新药-1.31 vs CXO局部逆势博腾+5.41)
    '161616': -1.17,   # 融通医疗保健 → 医疗ETF
    '000727': -1.20,   # 融通健康(CXO)
    '001551': MED_ETF_AVG,   # 天弘医药100C
    '000071': ETF_PCT.get('159920', 0),   # 恒生ETF联接 → 恒生ETF华夏 -0.34
    '164906': ETF_PCT.get('513050', 0),   # 交银海外互联 → 中概互联ETF -1.25
    '000051': 0.30,   # 华夏沪深300联接 → 沪深300 +0.30
    '110020': 0.30,   # 易方达沪深300联接
    '001552': 0.00,   # 天弘证券保险(证券0.00/保险弱对冲)
    '001469': 0.10,   # 广发金融地产(银行涨/地产跌)
    '005368': -1.26,  # 富国清洁能源(通威-1.26光伏)
    '004752': ETF_PCT.get('512980', 0),  # 广发传媒 → 传媒ETF -2.76
    '100032': 1.17,   # 富国红利增强 → 100红利 +1.17
    '002742': 0.05,   # 泓德裕祥债券
    '000369': 0.0, '016280': 0.0,   # QDII美股医疗: 停9/7净值(基准已含), XLV 9/8 -2.52% 于9/10-11兑现
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
    'as_of': '2026-09-09收盘(代理口径,场外净值T+1)',
    'base_total': base_total,
    'est_total_pct': total_pct,
    'est_total_pnl': round(total_pnl, 2),
    'total_mv': round(new_total, 2),
    'tracks': tracks_out,
    'med_exposure': round(med_exp, 2),
    'med_pct': round(med_exp / new_total * 100, 2),
    'detail': detail,
    'note': '当日3只场外净值已出(富国消费主题-0.86/天弘恒生科技A-0.79/华宝医疗C-1.31);广联达8.55(-3.61)高位题材退潮拖累/通威11.71(-1.26)真实收盘;恒科4,420.79(-0.76)破4500第2日减仓0.5%执行预案;中证消费12,704(-0.56)守12600;QDII停9/7(XLV9/8-2.52%于9/10-11兑现)'
}
with open(os.path.join(HIST, 'portfolio_close_20260909.json'), 'w', encoding='utf-8') as f:
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
