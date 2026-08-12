# -*- coding: utf-8 -*-
"""盘后档 2026-08-12 组合收益计算：基于最新快照(含用户3笔卖出) + 当日涨跌"""
import json, os, csv

BASE = '/Users/jieyang/Documents/WealthHub'

# ---------- 读取 3 账户快照 ----------
def load_snapshot(path):
    rows = []
    with open(path, encoding='utf-8-sig') as f:
        for r in csv.DictReader(f):
            rows.append(r)
    return rows

snap_stock = load_snapshot(os.path.join(BASE, 'holdings/stock-brokerage/snapshot-2026-08-12.csv'))
snap_jasy = load_snapshot(os.path.join(BASE, 'holdings/jasy-alipay-fund/snapshot-2026-08-12.csv'))
snap_sean = load_snapshot(os.path.join(BASE, 'holdings/sean-alipay-fund/snapshot-2026-08-05.csv'))

# ---------- 当日涨跌映射（%），真实净值/收盘优先 ----------
pct_map = {
    # 个股真实收盘
    '002410': -0.95, '600438': 5.06,
    # 场内 ETF 收盘
    '513050': -2.16, '159928': 0.29, '512170': -0.28, '513180': -0.98,
    '515180': 0.21, '159920': -0.99, '512880': 0.37, '512980': 0.69,
    # 场外 8/12 真实净值
    '000968': 0.23, '001180': -0.52, '000071': -0.84, '012348': -0.97,
    # 场外未更新 → 赛道近似（8/12 涨跌）
    '002708': -0.29, '001469': 0.32, '000369': 0.0, '001552': 0.37,
    '000248': 0.25, '012323': -0.28, '000727': -0.29, '004424': 0.25,
    '164906': -2.16, '016280': 0.0, '519915': 0.25, '002742': 0.0,
    '004752': 0.69, '005368': 0.32, '110020': 0.32, '100032': 0.21,
    '161616': -0.29, '000051': 0.32, '001551': -0.29, '000369b': 0.0,
}
# 注意：000369/016280 QDII 净值停在 8/10（T+1~T+2），今日贡献按 0 计，报告中注明 8/11 XLV -0.26% 待净值反映

# ---------- 赛道映射 ----------
track_map = {
    '002410': '其他/宽基', '600438': '其他/宽基', '513050': '恒生科技', '159928': '大消费',
    '512170': 'A股医药', '513180': '恒生科技', '515180': '其他/宽基', '159920': '其他/宽基',
    '512880': '其他/宽基', '512980': '其他/宽基',
    '002708': 'A股医药', '001469': '其他/宽基', '000071': '其他/宽基', '000369': '美股标普医药',
    '001552': '其他/宽基', '000248': '大消费', '012323': 'A股医药', '000727': 'A股医药',
    '012348': '恒生科技', '004424': '大消费', '164906': '恒生科技', '016280': '美股标普医药',
    '519915': '大消费', '000968': '大消费', '002742': '其他/宽基', '004752': '其他/宽基',
    '005368': '其他/宽基', '110020': '其他/宽基', '100032': '其他/宽基', '001180': 'A股医药',
    '161616': 'A股医药', '000051': '其他/宽基', '001551': 'A股医药',
}

# ---------- 计算 ----------
detail = []
total = 0.0
tracks = {}
for snap, acc in [(snap_stock, 'stock-brokerage'), (snap_jasy, 'jasy-alipay-fund'), (snap_sean, 'sean-alipay-fund')]:
    for r in snap:
        name = r['name']
        code = r['code']
        try:
            amount = float(r['amount']) if r['amount'].strip() else 0.0
        except ValueError:
            amount = 0.0
        total += amount
        # 现金
        if code == '' or '货币' in r.get('type', ''):
            track = '现金'
            pct = 0.0
        else:
            code6 = code.split('.')[0]
            track = track_map.get(code6, '其他/宽基')
            pct = pct_map.get(code6, 0.0)
        pnl = amount * pct / 100
        detail.append({'account': acc, 'name': name, 'code': code, 'track': track,
                       'amount': round(amount, 2), 'est_pct': pct, 'est_pnl': round(pnl, 2)})
        tracks.setdefault(track, {'amount': 0.0, 'pnl': 0.0})
        tracks[track]['amount'] += amount
        tracks[track]['pnl'] += pnl

# 赛道占比与贡献
track_out = {}
for t, v in tracks.items():
    track_out[t] = {
        'amount': round(v['amount'], 2),
        'pct': round(v['amount'] / total * 100, 2) if total else 0,
        'pnl': round(v['pnl'], 2),
        'pct_contrib': round(v['pnl'] / total * 100, 2) if total else 0,
    }

est_total_pct = round(sum(v['pnl'] for v in tracks.values()) / total * 100, 2)
est_total_pnl = round(sum(v['pnl'] for v in tracks.values()), 2)

out = {
    'date': '2026-08-12',
    'total': round(total, 2),
    'tracks': track_out,
    'est_total_pct': est_total_pct,
    'est_total_pnl': est_total_pnl,
    'detail': detail,
}
with open(os.path.join(BASE, 'data/processed/history/portfolio_close_20260812.json'), 'w', encoding='utf-8') as f:
    json.dump(out, f, ensure_ascii=False, indent=1)

print(f'总资产: {total:,.2f}')
print(f'组合当日估算: {est_total_pct:+.2f}% ({est_total_pnl:+,.2f} 元)')
print('\n赛道分布:')
for t, v in sorted(track_out.items(), key=lambda x: -x[1]['amount']):
    print(f'  {t}: {v["pct"]:.2f}% | 贡献 {v["pct_contrib"]:+.2f}pct | 金额 {v["amount"]:,.2f} | 盈亏 {v["pnl"]:+,.2f}')
print('\nDONE -> portfolio_close_20260812.json')
