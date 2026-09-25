# -*- coding: utf-8 -*-
"""2026-09-25 盘后：「混合档」组合复盘 + 9/28 复市待消化测算
⚠️ 本档 A股休市 → 当日可实现盈亏 = 0.00 元（归因：**全部 A股标的无法定价**，非「市场持平」）
⚠️ 不产出 portfolio_close_*.json（沿用 9/20 周日档先例：非 A股交易日不插入 0% 链式行，避免污染夏普/链路）
⚠️ 待消化测算分母（§3.107）：一律用 `tracks[track].mv`（= Σ(mv0+est_pnl)），禁止用 detail[].mv 求和
"""
import json, os

BASE = '/Users/jieyang/Documents/WealthHub'
HIST = os.path.join(BASE, 'data/processed/history')
TODAY = '2026-09-25'

fix = json.load(open(os.path.join(HIST, 'portfolio_close_20260924_fix.json'), encoding='utf-8'))
tracks = {k: v['mv'] for k, v in fix['tracks'].items()}
TOTAL = sum(tracks.values())
assert abs(TOTAL - fix['total_mv']) < 1.5, f'基准还原失败 {TOTAL} vs {fix["total_mv"]}'
print(f'9/24 修正收盘总资产 = {TOTAL:,.2f} 元（校验通过，§3.107）')

hq = json.load(open(os.path.join(HIST, 'close_hq_20260925.json'), encoding='utf-8'))
HK = hq['indices_hk']
STK = hq['hk_stocks']
HK_PCT = HK['恒生科技']['pct']
HSI_PCT = HK['恒生指数']['pct']
HSTECH_CLOSE = HK['恒生科技']['cur']
HSI_CLOSE = HK['恒生指数']['cur']

# ---- ① 逐券还原 9/24 收盘市值（mv0 + est_pnl，§3.104/§3.107）----
det = []
for x in fix['detail']:
    mv = round(x['mv0'] + x['est_pnl'], 2)
    det.append({**x, 'mv_close': mv})
tot_det = sum(x['mv_close'] for x in det)
print(f'逐券还原合计 = {tot_det:,.2f} 元 | tracks 合计 = {TOTAL:,.2f} | 差 {tot_det - TOTAL:+.2f}')

# ---- ② 港股暴露分解 ----
HK_TRACK = '恒生科技'
hk_tech_rows = [x for x in det if x['track'] == HK_TRACK]
hs_rows = [x for x in det if x['track'] == '其他/宽基'
           and (x['code'] == '000071' or x['code'] == '159920.SZ')]
hk_tech_mv = sum(x['mv_close'] for x in hk_tech_rows)
hs_mv = sum(x['mv_close'] for x in hs_rows)

# 中概/海外互联 vs 纯恒生科技 拆分
PURE_TECH = {'012348', '513180.SH'}          # 天弘恒生科技联接 / 恒指科技（跟踪恒生科技指数）
pure = [x for x in hk_tech_rows if x['code'] in PURE_TECH]
cn_net = [x for x in hk_tech_rows if x['code'] not in PURE_TECH]
pure_mv = sum(x['mv_close'] for x in pure)
cn_mv = sum(x['mv_close'] for x in cn_net)

print(f'\n=== 港股暴露分解（基准 {TOTAL:,.2f} 元） ===')
print(f'恒生科技赛道（tracks.mv）            = {tracks[HK_TRACK]:>12,.2f} 元  ({tracks[HK_TRACK]/TOTAL*100:.2f}%)')
print(f'  其中 纯恒生科技（012348/513180）    = {pure_mv:>12,.2f} 元')
print(f'      中概/海外互联（513050/164906）  = {cn_mv:>12,.2f} 元')
print(f'其他/宽基中的恒生系（000071×2/159920）= {hs_mv:>12,.2f} 元  ({hs_mv/TOTAL*100:.2f}%)')
for x in hs_rows:
    print(f'    {x["name"]:24s} {x["mv_close"]:>10,.2f}')

# 中概互联代理：港股互联网权重股等权
CN_NAMES = ['腾讯控股', '阿里巴巴-W', '美团-W', '京东集团-SW', '百度集团-SW',
            '网易-S', '快手-W', '小米集团-W']
vals = [STK[n]['pct'] for n in CN_NAMES if n in STK]
CN_PCT = round(sum(vals) / len(vals), 4)
print(f'\n中概/海外互联代理（{len(vals)} 只港股互联网权重股等权） = {CN_PCT:+.2f}%')

# ---- ③ 9/28 待消化测算 ----
p_pure = pure_mv * HK_PCT / 100
p_cn = cn_mv * CN_PCT / 100
p_hs = hs_mv * HSI_PCT / 100
pend_mid = p_pure + p_cn + p_hs
# 区间：恒科 −1.00 ~ −1.30%；中概 −0.80 ~ −2.20%；恒指 −0.90 ~ −1.10%
lo = pure_mv * -1.00 / 100 + cn_mv * -0.80 / 100 + hs_mv * -0.90 / 100
hi = pure_mv * -1.30 / 100 + cn_mv * -2.20 / 100 + hs_mv * -1.10 / 100
print(f'\n=== 9/28 复市「港股待消化」测算 ===')
print(f'  纯恒生科技 {pure_mv:>10,.2f} × {HK_PCT:+.2f}%  = {p_pure:>+9,.2f} 元')
print(f'  中概/互联 {cn_mv:>10,.2f} × {CN_PCT:+.2f}%  = {p_cn:>+9,.2f} 元')
print(f'  宽基恒生系 {hs_mv:>10,.2f} × {HSI_PCT:+.2f}%  = {p_hs:>+9,.2f} 元')
print(f'  合计中枢 = {pend_mid:+,.2f} 元（{pend_mid/TOTAL*100:+.3f}% 基准）')
print(f'  区间 = {hi:+,.2f} 元 ~ {lo:+,.2f} 元')

# ---- ④ 美股标普医药 QDII 预告（§3.106：IYH × 0.72）----
import csv
iyh = None
with open(os.path.join(HIST, 'indices.csv'), encoding='utf-8-sig') as fh:
    for row in csv.DictReader(fh):
        if row['code'] == 'IYH' and row['date'] == '2026-09-24':
            iyh = float(row['pct_change'])
print(f'\nIYH 9/24 = {iyh:+.2f}%')
qdii_pct = round(iyh * 0.72, 4)
qdii_mv = sum(x['mv_close'] for x in det if x['track'] == '美股标普医药')
qdii_pnl = qdii_mv * qdii_pct / 100
print(f'美股标普医药赛道市值 = {qdii_mv:,.2f} 元')
print(f'预告（IYH × 0.72）= {qdii_pct:+.4f}% → {qdii_pnl:+,.2f} 元（区间 0 ~ IYH×1.25 → 0 ~ {qdii_mv*iyh*1.25/100:+,.2f} 元）')

# ---- ⑤ 敞口/防线 ----
med_mv = tracks['A股医药'] + tracks['美股标普医药']
med_pct = med_mv / TOTAL * 100
A = tracks['A股医药']
B = tracks['美股标普医药']
# §3.98 方程解法：敞口(r) = [A(1+r) + B(1+r)] / [TOTAL + (A+B)r] = 0.40  →  1 + 0.60r = 0.40·TOTAL/(A+B)
r_all = ((0.40 * TOTAL / (A + B) - 1) / 0.60) * 100          # 两赛道同向上涨所需涨幅
# 仅 A股医药上涨：[A(1+r) + B] / [TOTAL + A·r] = 0.40  →  r = [0.40·TOTAL − (A+B)] / (0.60·A)
r_a = ((0.40 * TOTAL - (A + B)) / (0.60 * A)) * 100          # 仅 A股医药上涨所需涨幅
print(f'\n=== 风险指标 ===')
print(f'医药总敞口 = {med_pct:.2f}%（{med_mv:,.2f} 元），距 40% 上限 {40 - med_pct:.2f}pct')
print(f'  被动触线门槛（§3.98 方程）：两赛道同向 +{r_all:.2f}% / 仅 A股医药 +{r_a:.2f}%')
print(f'现金 = {tracks["现金"]:,.2f} 元（{tracks["现金"]/TOTAL*100:.2f}%）')
print(f'\n防线：')
print(f'  恒生科技 9/25 收 {HSTECH_CLOSE} ({HK_PCT:+.2f}%)，距 4,250 防线 {(HSTECH_CLOSE/4250-1)*100:+.2f}%')
print(f'  中证消费 12,109.54（9/24，A股休市无更新），距 12,100 {(12109.54/12100-1)*100:+.3f}%')

out = {
    'date': TODAY, 'as_of': '2026-09-25 混合档（A股休市 + 港股正常交易）',
    'base_total': round(TOTAL, 2), 'base_note': '9/24 修正收盘口径（portfolio_close_20260924_fix.json）',
    'realized_pnl': 0.0, 'realized_pct': 0.0,
    'realized_note': 'A股全线休市（场外基金无净值发布、场内 ETF 无成交价），持仓 100% 落于 A股市场 → 全部标的无法定价；港股通 9/25-9/27 暂停，QDII 联接无法申赎 → 当日可实现盈亏恒为 0，属「标的无法定价」而非「市场持平」',
    'hk_close': HK, 'hk_stocks': STK,
    'hk_exposure': {
        'track_hktech_mv': round(tracks[HK_TRACK], 2),
        'pure_hstech_mv': round(pure_mv, 2),
        'cn_internet_mv': round(cn_mv, 2),
        'wideindex_hs_mv': round(hs_mv, 2),
        'total_hk_linked_mv': round(tracks[HK_TRACK] + hs_mv, 2),
        'total_hk_linked_pct': round((tracks[HK_TRACK] + hs_mv) / TOTAL * 100, 2),
        'cn_proxy_names': CN_NAMES, 'cn_proxy_pct': CN_PCT,
    },
    'pending_consume': {
        'mid_pnl': round(pend_mid, 2), 'mid_pct': round(pend_mid / TOTAL * 100, 4),
        'low_pnl': round(hi, 2), 'high_pnl': round(lo, 2),
        'components': {'pure_hstech': round(p_pure, 2), 'cn_internet': round(p_cn, 2), 'wide_hs': round(p_hs, 2)},
    },
    'qdii_forecast': {'iyh_pct': iyh, 'coef': 0.72, 'pct': qdii_pct, 'mv': round(qdii_mv, 2),
                      'pnl': round(qdii_pnl, 2), 'range_hi_pnl': round(qdii_mv * iyh * 1.25 / 100, 2)},
    'tracks': {k: round(v, 2) for k, v in tracks.items()},
    'weights': {k: round(v / TOTAL * 100, 2) for k, v in tracks.items()},
    'med_exposure': round(med_mv, 2), 'med_pct': round(med_pct, 2),
    'threshold_all_med': round(r_all, 2), 'threshold_a_sh_med': round(r_a, 2),
    'defense': {'hstech': HSTECH_CLOSE, 'hstech_pct': HK_PCT, 'hstech_gap_to_4250': round((HSTECH_CLOSE / 4250 - 1) * 100, 2),
                'csi_consumer': 12109.54, 'csi_consumer_gap_to_12100': round((12109.54 / 12100 - 1) * 100, 3)},
}
json.dump(out, open(os.path.join(HIST, f'portfolio_pending_{TODAY.replace("-","")}.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
print(f'\n已保存 portfolio_pending_{TODAY.replace("-","")}.json')
