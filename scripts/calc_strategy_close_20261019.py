# -*- coding: utf-8 -*-
"""2026-10-19 盘后档策略计算（档型②反向混合档：A股 15:00 收盘 + 港股重阳节翌日休市 + 美股未开盘）
输入：portfolio_close_20261019.json / portfolio_intraday_20261019.json / risk_stats_close_20261019.json
      / event_stats_20261019_close.json / news-2026-10-19.json
输出：portfolio_strategy_close_20261019.json
纪律：赛道级动作区间 [0%, 0%]（本档无已触发且可执行项）；单次调仓 ≤ 5%；单赛道 ≤ 40%
"""
import json, os

BASE = '/Users/jieyang/Documents/WealthHub'
HIST = os.path.join(BASE, 'data/processed/history')
TODAY = '2026-10-19'
TODAYC = '20261019'

pc = json.load(open(os.path.join(HIST, 'portfolio_close_' + TODAYC + '.json'), encoding='utf-8'))
pi = json.load(open(os.path.join(HIST, 'portfolio_intraday_' + TODAYC + '.json'), encoding='utf-8'))
rk = json.load(open(os.path.join(HIST, 'risk_stats_close_' + TODAYC + '.json'), encoding='utf-8'))
es = json.load(open(os.path.join(HIST, 'event_stats_' + TODAYC + '_close.json'), encoding='utf-8'))

T = pc['tracks']
TOTAL = pc['total_mv']
W = {k: round(v['mv'] / TOTAL * 100, 2) for k, v in T.items()}
assert abs(sum(W.values()) - 100) < 0.05, f'权重合计异常 {W}'

MED = pc['med_exposure']
MED_PCT = pc['med_pct']
assert abs(MED_PCT - 38.38) < 0.05, f'医药敞口 {MED_PCT} != 38.38'

# ---------- 1. 赛道级动作（全部 0 元） ----------
def w(t):
    return W[t]


track_actions = [
    {'track': '其他/宽基', 'weight_pct': w('其他/宽基'), 'action_range_pct': [0, 0], 'amount': 0,
     'rationale': ('无防线约束；本档 +815.31 元（+0.882%）但**收益集中于个股**（广联达 +716.80 元 = 87.9%），'
                   '银行创新高属「红利防守」而非主动加仓理由；地产链（投资 −20.6% / 荣丰控股跌停）负向未解'),
     'gates': ['无']},
    {'track': 'A股医药', 'weight_pct': w('A股医药'), 'action_range_pct': [0, 0], 'amount': 0,
     'rationale': ('**反向兑现线闭环判定 = 假破位**（收盘板块代理 +1.1825% > 0%）→ 10/16 第三次触发按 §3.114c '
                   '对称处置回落、10/20 不建减配预案（原 1,851.30 元作废）；中药领涨但属防御属性驱动、非板块反转；'
                   '敞口 38.38% 距 40% 余量 1.62pct、门槛 +7.01%（概率极低）'),
     'gates': ['a_med_reverse_1_5pct: closed_false_break']},
    {'track': '大消费', 'weight_pct': w('大消费'), 'action_range_pct': [0, 0], 'amount': 0,
     'rationale': ('中证消费 12,467.08（−0.18%）连续第 2 日冲高回落、距 12,100 防线 +3.0337%（安全垫收窄）；'
                   '**科技兴商意见属供给侧政策、无量化目标**；本档 +423.42 元几乎全部来自 519915 单只净值超预期'
                   '（+424.79 元），其余 6 券位合计 −1.37 元 → **不外推为消费腿修复**'),
     'gates': ['zz_consume_12100: above_lower_line']},
    {'track': '美股标普医药', 'weight_pct': w('美股标普医药'), 'action_range_pct': [0, 0], 'amount': 0,
     'rationale': ('本档不可定价（US 10/19 未开盘）；**QDII 10/16 净值 0.00% 疑似占位 → US 10/16 挂账未实质核销**；'
                   '传导系数 0.72 仍 pending（5 样本 3 越界）→ **系数未重估前基于该系数的一切仓位决策无效**（§3.118a）'),
     'gates': ['qdii_double_uncertainty: pending']},
    {'track': '恒生科技', 'weight_pct': w('恒生科技'), 'action_range_pct': [0, 0], 'amount': 0,
     'rationale': ('港股 10/19 休市、**无交易时段**；4,250 破位与 4,000 观察线判定**顺延 10/20 收盘**；'
                   '本档 +41.84 元来自 A股 场内溢折价与 164906 净值兑现，方向不一致、不构成判定依据'),
     'gates': ['hstech_4250: deferred_hk_closed', 'hstech_4000: deferred_hk_closed']},
    {'track': '现金', 'weight_pct': w('现金'), 'action_range_pct': [0, 0], 'amount': 0,
     'rationale': '无交易时段；纪律后权重 8.87%（累计减仓 3,786.90 元已成交）', 'gates': ['无']},
]

# ---------- 2. 约束与纪律 ----------
constraints = {
    'single_track_cap_pct': 40,
    'med_exposure': {'mv': MED, 'pct': MED_PCT, 'headroom_pct': round(40 - MED_PCT, 2),
                     'threshold_all_med_pct': pc['threshold_all_med'],
                     'threshold_a_sh_med_pct': pc['threshold_a_sh_med'],
                     'note': ('门槛为解方程值（`A(1+r)/(B+A·r)=0.40`）：全部医药同涨需 +'
                              f'{pc["threshold_all_med"]:.2f}%、仅 A股医药上涨需 +{pc["threshold_a_sh_med"]:.2f}% '
                              '→ **概率均极低，不得把 1.62pct 余量读作「逼近上限」**')},
    'max_single_trade_pct': 5,
    'max_single_trade_used_pct': 0,
    'new_buy': 0, 'active_take_profit': 0,
    'status': 'all_clear',
}

discipline = {
    'cumulative_cut_amount': pc['discipline']['cumulative_amount'],
    'settled': pc['discipline']['settled_on'],
    'today_cut': 0,
    'reason': ('无新增防线触发：恒科两条线本档不可判定（港股休市）；A股医药反向线闭环为假破位 → 不建预案；'
               '中证消费距 12,100 为 +3.0337%，安全'),
    'hk_after_mv': pc['discipline']['hk_after'], 'cash_after_mv': pc['discipline']['cash_after'],
    'weight_after': pc['discipline']['weight_after'],
}

# ---------- 3. 归因与验证 ----------
attrib = []
for k, v in sorted(T.items(), key=lambda kv: -kv[1]['pnl']):
    attrib.append({'track': k, 'mv': round(v['mv'], 2), 'weight_pct': W[k],
                   'pnl': round(v['pnl'], 2), 'day_pct': v['day_pct'],
                   'share_of_total_pnl_pct': round(v['pnl'] / pc['est_total_pnl'] * 100, 1) if pc['est_total_pnl'] else None})

verification = {
    'close_vs_intraday': {'intraday_pnl': pi['total_delta'], 'intraday_pct': pi['est_total_pct'],
                          'close_pnl': pc['est_total_pnl'], 'close_pct': pc['est_total_pct'],
                          'delta_pnl': round(pc['est_total_pnl'] - pi['total_delta'], 2),
                          'note': ('盘中 13:45 估算 +1,665.45 元 → 收盘 +1,793.84 元（+128.39 元）；'
                                   '**增量主因 = 场外真实净值取代代理估算**（519915 +1.805% vs 盘中代理 +0.22%），'
                                   '而非尾盘价格上行（中证消费尾盘反而由 +0.12% 转 −0.18%）')},
    'intraday_assumption_broken': [
        {'assumption': '主动医药基偏离 CRO、跑赢指数（盘中代理 002708 +1.435%）',
         'realized': '002708 真实净值 +0.387%，跑输板块代理 0.80pct',
         'verdict': '❌ 假设被证伪'},
        {'assumption': '消费腿尾盘维持正收益（盘中 +0.12%）',
         'realized': '中证消费收盘 −0.18%，但组合消费腿因 519915 真实净值 +1.805% 仍录得 +423.42 元',
         'verdict': '⚠️ 指数假设证伪 / 组合损益反而改善（口径分裂）'},
        {'assumption': '医药反向线闭环可能成立（盘中代理 +1.03%，需回吐 1.03pct）',
         'realized': '收盘代理 +1.1825%，未回吐反而扩大',
         'verdict': '❌ 闭环不成立（假破位确认）'},
    ],
    'unpriced': {'count': len(pc['unpriced']), 'notional': pc['unpriced_total'],
                 'priceable_pct': pc['priceable_pct'],
                 'codes': [u['code'] for u in pc['unpriced']],
                 'gap_estimate_note': ('4 只未定价券（161616 / 000727 / 100032 / 002742）按基准计 0；'
                                       '若按各自代理（医药 ×2 用 BOARD_MED +1.1825%、红利用 中证金融 +0.83%）粗估，'
                                       '组合损益另有约 +150 元 ~ +210 元的**低估**，**不并入本档主口径**')},
}

# ---------- 4. 明日（10/20）预案 ----------
tomorrow = [
    {'item': '注销 A股医药减配预案', 'detail': '10/16 登记的 0.5% 被动减配（≈1,851.30 元，候选 012323 / 001180）'
                                          '因闭环不成立而作废，须在 10/20 盘前档显式注销，不得静默保留', 'priority': 'P0'},
    {'item': '恒生科技两条防线判定', 'detail': '以 **10/20 收盘价**判定 4,250 破位（10/16 读数 −3.3355%）与 4,000 观察线（+2.7060%）；'
                                          '09:00 LPR 与港股复市同日，开盘 30 分钟价格不具代表性', 'priority': 'P0'},
    {'item': '4 只未定价券兜底复抓', 'detail': '161616 / 000727 / 100032 / 002742（notional 合计 20,084.79 元）；'
                                          '到位即以同日 `_fix` 覆盖并**同步重算 tracks[].pnl**（硬守卫 |Σpnl − est_total_pnl| < 1.5）',
     'priority': 'P1'},
    {'item': 'QDII 10/16 净值占位复核', 'detail': '000369 / 016280 的 10/16 净值是否被事后修订；'
                                          '若修订则重算美股腿并核销 US 10/16 段（预告区间 −206.50 ~ −137.65 元）', 'priority': 'P1'},
    {'item': 'US 10/19 收盘归档', 'detail': '北京 10/20 04:00 成型 → 盘前档仅可登记、不可作结论（§3.120c）', 'priority': 'P2'},
    {'item': '10 月 LPR（09:00）', 'detail': '预期 1Y 3.0% / 5Y+ 3.5% 连续 16 个月不变；意外下调才改变分母端假设', 'priority': 'P2'},
    {'item': '三季报窗口跟踪', 'detail': '10/19-10/31 密集期，重点关注组合医药/消费腿主动基的重仓股业绩预告', 'priority': 'P2'},
]

risk = {
    'chain_cum_pct': rk['chain_cum_pct'], 'chain_days': rk['chain_days'],
    'sharpe': rk.get('sharpe'), 'rf_pct': rk.get('rf_pct', 1.68),
    'mdd_pct': rk.get('max_dd_pct'), 'mdd_peak': rk.get('max_dd_peak'),
    'mdd_trough': rk.get('max_dd_trough'),
    'w43_pct': rk.get('w43_cum_pct'), 'w43_days': rk.get('w43_days'),
    'ret_5d_pct': rk.get('last5_cum_pct'), 'ret_10d_pct': rk.get('last10_cum_pct'),
    'note': 'rf 仍为硬编码 1.68%（10Y 序列自 2026-08-11 未维护）→ 夏普绝对水平不可引用，只看方向',
}

sentiment = {'window_net_nominal': 7.40, 'window_net_weighted': 3.1268,
             'day_net_nominal': 30.40, 'day_net_weighted': 7.9010,
             'annotation_mode': 'rule_table_fallback', 'degraded_items': 17,
             'note': 'DeepSeek HTTP 402 连续第 14 个日历日；本档 17/17 条为规则表标注，跨档比较须标注口径差异'}

out = {
    'date': TODAY, 'as_of': '2026-10-19 收盘（反向混合档：A股 15:00 收盘 + 港股重阳节翌日休市 + 美股未开盘）',
    'session_type': 'reverse_mixed_closed_hk',
    'total_mv': TOTAL, 'est_total_pnl': pc['est_total_pnl'], 'est_total_pct': pc['est_total_pct'],
    'weights': W,
    'track_actions': track_actions,
    'action_range_total_pct': [0, 0], 'action_amount_total': 0,
    'constraints': constraints, 'discipline': discipline,
    'attribution': attrib, 'verification': verification,
    'tomorrow_plan': tomorrow, 'risk': risk, 'sentiment': sentiment,
    'hk_split': {'pure_hk': pc['hk_split']['pure'], 'cn_internet': pc['hk_split']['concept'],
                 'hk_broad': pc['hk_split']['broad'],
                 'total': pc['hk_total'], 'total_pct': pc['hk_total_pct'],
                 'track_layer_pct': pc['track_layer_hk_pct'],
                 'note': '只报赛道层会低估宽基恒生系（§3.108 条款 23）；港股 10/19 休市 → 本档不做待消化测算'},
    'event_lib': {'total_events': es['total_events'], 'session_added': es['session_added'],
                  'session_backfilled_total': es['session_backfilled_total'],
                  'blank': es['blank'],
                  'ref_by_track': es['reference_trading_day_by_track'],
                  'note': ('本档盘后窗口 17 条全部留空（参考日 = 10/20 或 US 10/19），属预期状态；'
                           'A股 类回填 49 条（10/16 与 10/18 档留空条目于本档有真实收盘）')},
    'guards': {
        'sum_tracks_mv_dev': round(abs(sum(v['mv'] for v in T.values()) - TOTAL), 2),
        'sum_tracks_pnl_dev': round(abs(sum(v['pnl'] for v in T.values()) - pc['est_total_pnl']), 2),
        'weights_sum': round(sum(W.values()), 2),
        'med_pct_check': round(abs(MED_PCT - (T['A股医药']['mv'] + T['美股标普医药']['mv']) / TOTAL * 100), 4),
    },
}
assert out['guards']['sum_tracks_mv_dev'] < 1.5
assert out['guards']['sum_tracks_pnl_dev'] < 1.5

json.dump(out, open(os.path.join(HIST, 'portfolio_strategy_close_' + TODAYC + '.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
print('已保存 portfolio_strategy_close_' + TODAYC + '.json')
print('权重:', W)
print('动作区间合计:', out['action_range_total_pct'], '金额', out['action_amount_total'])
print('归因:', [(a['track'], a['pnl']) for a in attrib])
print('守卫:', out['guards'])
print('风险:', {k: risk[k] for k in ('chain_cum_pct', 'sharpe', 'mdd_pct', 'w43_pct')})
