# -*- coding: utf-8 -*-
"""2026-09-24 盘前：基准口径与当日预判参数计算
base = portfolio_close_20260923_fix.json（9/23 收盘真实净值兜底修正口径）
输出：portfolio_preopen_20260924.json
"""
import json, os

BASE = '/Users/jieyang/Documents/WealthHub'
HIST = os.path.join(BASE, 'data/processed/history')
TODAY = '2026-09-24'

b = json.load(open(os.path.join(HIST, 'portfolio_close_20260923_fix.json'), encoding='utf-8'))
base_total = b['total_mv']
tracks = b['tracks']

# ---- 隔夜美股（9/23 收盘）----
US = {'XLV': -0.64, 'IYH': -0.75, 'QQQ': -0.84, 'DIA': -0.71, 'SPY': -0.72,
      '.IXIC': -1.13, '.DJI': -0.68, '.INX': -0.75}
QDII_TRANS = 0.75          # §3.102 首次量化：指数 → QDII 净值传导系数
mv_us = tracks['美股标普医药']['mv']
qdii_pred_pct = round(US['XLV'] * QDII_TRANS, 4)
qdii_pred_pnl = round(mv_us * qdii_pred_pct / 100, 2)
qdii_lo = round(mv_us * (US['XLV'] * 0.748) / 100, 2)
qdii_hi = round(mv_us * (US['XLV'] * 0.762) / 100, 2)

# ---- 医药敞口与门槛（§3.98 方程解法）----
med = round(tracks['A股医药']['mv'] + tracks['美股标普医药']['mv'], 2)
A, Bn = med, base_total - med
threshold_all = round(((0.40 / 0.60) * Bn / A - 1) * 100, 2)
A_sh = tracks['A股医药']['mv']
threshold_sh = round((((0.40 / 0.60) * Bn - (med - A_sh)) / A_sh - 1) * 100, 2)

# ---- 三条防线距离（口径必须标注）----
LINES = {
    '中证消费 12,100 下沿': (12288.7946, 12100.0, 'down'),
    '中证消费 12,400 上沿观察位': (12288.7946, 12400.0, 'up'),
    '恒生科技 4,250 防线': (4379.07, 4250.0, 'down'),
    '中证医药单日 -1.5% 反向兑现线': (None, -1.5, 'pct'),
}
lines_out = {}
for k, (cur, tgt, kind) in LINES.items():
    if kind == 'down':
        lines_out[k] = {'current': cur, 'target': tgt,
                        'dist_pct': round((cur - tgt) / tgt * 100, 3),
                        'formula': '(收盘−防线)/防线'}
    elif kind == 'up':
        lines_out[k] = {'current': cur, 'target': tgt,
                        'dist_pct': round((tgt - cur) / cur * 100, 3),
                        'formula': '(目标−收盘)/收盘'}
    else:
        lines_out[k] = {'current': '9/23 A股医药赛道 +0.936%', 'target': -1.5,
                        'dist_pct': '未触发', 'formula': '单日赛道跌幅阈值'}

out = {
    'date': TODAY, 'as_of': '2026-09-24 盘前(08:00)',
    'base_total': base_total, 'base_date': '2026-09-23收盘(净值补更修正)',
    'base_pnl_prev_day': b['est_total_pnl'], 'base_pct_prev_day': b['est_total_pct_raw'],
    'tracks': {k: {'mv': v['mv'], 'w': round(v['mv'] / base_total * 100, 2),
                   'prev_day_pct': v['day_pct'], 'prev_day_pnl': v['pnl']} for k, v in tracks.items()},
    'med_exposure': med, 'med_pct': round(med / base_total * 100, 2),
    'threshold_all_med': threshold_all, 'threshold_a_sh_med': threshold_sh,
    'us_overnight': US, 'qdii_trans_coef': QDII_TRANS,
    'us_track_pred_pct': qdii_pred_pct, 'us_track_pred_pnl': qdii_pred_pnl,
    'us_track_pred_pnl_range': [qdii_lo, qdii_hi],
    'defense_lines': lines_out,
}
json.dump(out, open(os.path.join(HIST, 'portfolio_preopen_20260924.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)

print(f'★ 基准：9/23 收盘（真实净值兜底修正）{base_total:,.2f} 元'
      f'（前一日 {b["est_total_pct_raw"]:+.4f}% / {b["est_total_pnl"]:+,.2f} 元）')
print('\n赛道权重（9/23 修正后）:')
for k, v in sorted(out['tracks'].items(), key=lambda kv: -kv[1]['mv']):
    print(f"  {k:10s} mv={v['mv']:>11,.2f} w={v['w']:>6.2f}%  9/23={v['prev_day_pct']:+.3f}% ({v['prev_day_pnl']:+,.2f})")
print(f"\n医药敞口 {out['med_pct']:.2f}%（{med:,.2f} 元）")
print(f'  被动触及 40% 门槛：医药两赛道同涨 {threshold_all:+.2f}% / 仅A股医药 {threshold_sh:+.2f}%')
print(f"\n隔夜美股：XLV {US['XLV']:+.2f}%（传导系数 {QDII_TRANS} → 预告 {qdii_pred_pct:+.2f}%）")
print(f'  美股标普医药 mv={mv_us:,.2f} → 预告 {qdii_pred_pnl:+,.2f} 元（区间 {qdii_lo:+,.2f} ~ {qdii_hi:+,.2f}）')
print('\n防线距离:')
for k, v in lines_out.items():
    print(f"  {k}: {v['dist_pct']}%（口径 {v['formula']}）")
