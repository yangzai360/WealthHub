# -*- coding: utf-8 -*-
"""2026-09-04 盘后组合估值: 基于 portfolio_preopen(9/3净值口径基准 383,223.12) + 当日真实收盘/指数代理
输出 portfolio_close_20260904.json"""
import json, os

BASE = '/Users/jieyang/Documents/WealthHub'
HIST = os.path.join(BASE, 'data/processed/history')
TODAY = '2026-09-04'

with open(os.path.join(HIST, 'portfolio_preopen_20260904.json'), encoding='utf-8') as f:
    base = json.load(f)
with open(os.path.join(HIST, 'close_20260904.json'), encoding='utf-8') as f:
    close = json.load(f)

# 场内真实涨跌幅 (code -> pct)
ETF_PCT = {e['code']: e['pct'] for e in close['etf']}
STOCK_PCT = {'广联达': 3.02, '通威股份': 0.98}  # stock_zh_a_daily 真实收盘

def est_pct(name):
    """每只持仓的当日估算涨跌幅(%)。场外净值未出用指数代理,盘中口径保持一致。"""
    # 场内 ETF / 股票: 真实收盘
    if name == '广联达':
        return 3.02
    if name == '通威股份':
        return 0.98
    etf_map = {'消费ETF添富': '159928', '医疗ETF': '512170', '中概互联': '513050',
               '恒指科技': '513180', '恒生ETF华夏': '159920', '证券ETF': '512880',
               '100红利': '515180', '传媒ETF': '512980'}
    if name in etf_map:
        return ETF_PCT.get(etf_map[name], 0.0)
    # 场外基金: 指数代理
    track_map = {
        # 大消费 → 中证消费 +2.65%
        '汇添富中证主要消费ETF联接A': 2.65, '汇添富中证主要消费联接A': 2.65,
        '富国消费主题混合A': 2.65, '广发中证养老产业A': 2.0,
        '汇添富文体娱乐主题A': 2.5,
        # A股医药 → ETF均值 -0.08% (医疗ETF 0.00 + 医药ETF广发 -0.16), 主动基含CXO略调
        '华宝中证医疗联接C': -0.08, '大摩健康产业混合A': -0.35, '摩根士丹利健康产业混合A': -0.35,
        '融通医疗保健行业混合A/B': -0.35, '广发医药卫生ETF联接A': -0.08,
        '融通健康产业灵活配置A/B': -0.30, '天弘中证医药100指数C': -0.15,
        # 恒生科技 → HSTECH +2.27% (QDII净值T+1, 用指数代理当日)
        '天弘恒生科技联接A': 2.27, '天弘恒生科技ETF联接(QDII)A': 2.27,
        '交银中证海外中国互联网指数(LOF)A': 2.03, '交银中证海外中国互联网A': 2.03,
        # 美股标普医药 → 按0 (QDII净值停9/2, XLV 9/3 +0.18% 待9/7-8兑现)
        '广发全球医疗保健指数A': 0.0, '广发全球医疗保健指数C': 0.0,
        '广发全球医疗保健指数(QDII)A': 0.0, '广发全球医疗保健指数(QDII)C': 0.0,
        # 其他/宽基
        '恒生ETF联接A': 1.74, '华夏恒生ETF联接(QDII)A': 1.74,  # 恒指 +1.74%
        '华夏沪深300ETF联接A': -0.50, '易方达沪深300ETF联接A': -0.50,  # 沪深300 近似
        '天弘中证证券保险A': 0.64, '广发中证全指金融地产联接A': 0.55,
        '富国清洁能源产业灵活配置混合A': 0.30,  # 光伏微涨 vs 锂电碳酸锂大跌
        '广发中证传媒ETF联接A': 3.51,
        '富国中证红利指数增强A': 0.10,  # 9/4当日净值已出 +0.10%
        '泓德裕祥债券A': 0.05,
        '帮你投-锐意进取': 0.0,
    }
    return track_map.get(name, 0.0)

detail = []
for x in base['detail']:
    pct = est_pct(x['name'])
    mv0 = float(x['mv'])
    pnl = mv0 * pct / 100
    detail.append({**x, 'est_pct': pct, 'est_pnl': round(pnl, 2)})

total_pnl = sum(d['est_pnl'] for d in detail)
base_total = base['total_mv']  # 383223.12
total_pct = total_pnl / base_total * 100

# 按赛道汇总
from collections import defaultdict
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

med_exposure = tracks_out.get('A股医药', {}).get('mv', 0) + tracks_out.get('美股标普医药', {}).get('mv', 0)

out = {
    'date': TODAY,
    'as_of': '2026-09-04收盘(代理口径,场外净值T+1)',
    'base_total': base_total,
    'est_total_pct': round(total_pct, 2),
    'est_total_pnl': round(total_pnl, 2),
    'total_mv': round(base_total + total_pnl, 2),
    'tracks': tracks_out,
    'med_exposure': round(med_exposure, 2),
    'med_pct': round(med_exposure / (base_total + total_pnl) * 100, 2),
    'detail': detail,
    'note': '场外基金净值T+1未出用指数代理(消费/恒科/宽基);QDII美股标普医药按0(XLV 9/3 +0.18% 待9/7-8兑现);A股医药场外主动基用-0.35%(CXO拖累)指数基-0.08%(ETF均值);广联达+3.02%/通威+0.98%真实收盘'
}
with open(os.path.join(HIST, 'portfolio_close_20260904.json'), 'w', encoding='utf-8') as f:
    json.dump(out, f, ensure_ascii=False, indent=1)

print(f"组合当日估算: {out['est_total_pct']}% ({out['est_total_pnl']:+,.2f} 元), 总资产 {out['total_mv']:,.2f}")
for t, v in tracks_out.items():
    print(f"  {t:8s} mv={v['mv']:>10,.2f} 占比={v['pct_of_total']:>5.2f}% 当日={v['day_pct']:+.2f}% pnl={v['pnl']:+,.2f}")
print(f"医药总敞口: {out['med_pct']:.2f}%")
