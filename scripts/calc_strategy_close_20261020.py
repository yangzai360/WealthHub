# -*- coding: utf-8 -*-
"""2026-10-20 盘后档策略计算（档型：正常交易日收盘 —— A股 15:00 收盘 + 港股复市 16:00 收盘 + 美股未开盘）
输入：portfolio_close_20261020.json / portfolio_intraday_20261020.json / risk_stats_close_20261020.json
      / event_stats_20261020_close.json
输出：portfolio_strategy_close_20261020.json
纪律：赛道级动作区间 [0%, 0%]（本档无已触发且可执行项）；单次调仓 ≤ 5%；单赛道 ≤ 40%
"""
import json, os

BASE = '/Users/jieyang/Documents/WealthHub'
HIST = os.path.join(BASE, 'data/processed/history')
TODAY = '2026-10-20'
TODAYC = '20261020'

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
assert abs(MED_PCT - 38.59) < 0.05, f'医药敞口 {MED_PCT} != 38.59'

# ---------- 1. 赛道级动作（全部 0 元） ----------
track_actions = [
    {'track': '其他/宽基', 'weight_pct': W['其他/宽基'], 'action_range_pct': [0, 0], 'amount': 0,
     'rationale': ('无防线约束；本档 +39.49 元（+0.042%）**几乎全部来自广联达 +1.66% 与传媒ETF +0.76%**，'
                   '而券商（001552 −1.56%）与金融地产（001469 −1.09%）为负拖累 → **腿内方向相反、净额近零**；'
                   '10/20 红利资产集体休整（中证金融 −1.21%）与 10/19「银行创新高」构成单日镜像 → 风格无连续趋势；'
                   '**未定价缺口 000051（9,061 元量级）按沪深300 −0.54% 影子估算约 −48 元** → 该腿实质约 −9 元'),
     'gates': ['无']},
    {'track': 'A股医药', 'weight_pct': W['A股医药'], 'action_range_pct': [0, 0], 'amount': 0,
     'rationale': ('**本档唯一强正贡献腿（+1,256.96 元 / +1.54%）**，驱动 = 发改委「前三季度创新药对外授权约 1,300 亿美元」'
                   '（硬政策数据）+ 器械/服务强于药品（中证医疗 +2.21% / 300医药 +1.25% / 中证医药 +0.89%）；'
                   '**但敞口 38.59%、距 40% 上限仅 1.41pct，门槛收益率 +6.11%（全部医药同涨）/ +10.56%（仅 A股医药）** → '
                   '**加仓空间被硬约束封死**（§3.98）；反向兑现线新基线首日 +1.5925%，未触发'),
     'gates': ['a_med_reverse_1_5pct: not_triggered', 'med_cap_40pct: headroom_1.41pct']},
    {'track': '大消费', 'weight_pct': W['大消费'], 'action_range_pct': [0, 0], 'amount': 0,
     'rationale': ('中证消费 12,422.96（−0.35%）**连续第 3 日冲高回落**、白酒 −0.60% 弱于指数；'
                   '**Q3 业绩前瞻「强分化 + 出清为主基调」**（浙商）与价格端首次同向为负；'
                   '**519915 10/20 净值 1.8050 / 0.00% 疑为占位**（10/19 为 +1.805%）→ 该腿 −120.27 元 的可信度待复核；'
                   '距 12,100 防线 +2.67%（两日收窄 0.36pct），仍在安全区 → 不动作'),
     'gates': ['zz_consume_12100: above_lower_line', 'nav_519915_placeholder: suspect']},
    {'track': '美股标普医药', 'weight_pct': W['美股标普医药'], 'action_range_pct': [0, 0], 'amount': 0,
     'rationale': ('**本档最大负贡献腿（−349.01 元 / −0.57%）**= QDII 10/19 净值真实兑现（挂账段核销）；'
                   '**隐含传导系数 0.99 / 1.01（映射 US 10/19）或 1.49 / 1.52（映射 US 10/16）→ 两种映射均越 0.60~0.90 区间**；'
                   '**系数未重估前基于该系数的一切前瞻仓位决策无效**（§3.118a）；'
                   '**US 10/20 尚未开盘（北京 20:00 = 美东 08:00）→ 本档无确认权、只登记挂账**（§3.120c）'),
     'gates': ['qdii_transmission_coef: pending']},
    {'track': '恒生科技', 'weight_pct': W['恒生科技'], 'action_range_pct': [0, 0], 'amount': 0,
     'rationale': ('**4,250 破位扩大至 −4.8021%**（收盘 4,045.91 / −1.52%，放量下跌至 1,904.55 亿港元）、'
                   '**4,000 观察线距 +1.1478%（日内低 4,026.90）→ 未破**；'
                   '**同一防线本季已触发 2 次（9/29、10/2）、同日只触发一次 → 本档不重复减仓**（§3.114c）；'
                   '本档仅 −71.12 元，因 012348（13,945.72 元 = 45.2%）净值未出库计 0 → **影子估算另约 −180 元**'),
     'gates': ['hstech_4250: break_widened_no_new_cut', 'hstech_4000: above_1.15pct']},
    {'track': '现金', 'weight_pct': W['现金'], 'action_range_pct': [0, 0], 'amount': 0,
     'rationale': '无交易；纪律后权重 8.85%（累计减仓 3,786.90 元已成交）', 'gates': ['无']},
]

# ---------- 2. 约束与纪律 ----------
constraints = {
    'single_track_cap_pct': 40,
    'med_exposure': {'mv': MED, 'pct': MED_PCT, 'headroom_pct': round(40 - MED_PCT, 2),
                     'threshold_all_med_pct': pc['threshold_all_med'],
                     'threshold_a_sh_med_pct': pc['threshold_a_sh_med'],
                     'note': ('门槛为解方程值（`A(1+r)/(B+A·r)=0.40`）：全部医药同涨需 +'
                              f'{pc["threshold_all_med"]:.2f}%、仅 A股医药上涨需 +{pc["threshold_a_sh_med"]:.2f}% '
                              '→ **概率均极低，不得把 1.41pct 余量读作「逼近上限」**')},
    'max_single_trade_pct': 5,
    'max_single_trade_used_pct': 0,
    'new_buy': 0, 'active_take_profit': 0,
    'status': 'all_clear',
}

discipline = {
    'cumulative_cut_amount': pc['discipline']['cumulative_amount'],
    'settled': pc['discipline']['settled_on'],
    'today_cut': 0,
    'reason': ('无新增防线触发：恒科 4,250 已在案、同日不重复（§3.114c）；4,000 未破（+1.1478%）；'
               '中证消费距 12,100 为 +2.67%；A股医药反向线新基线首日 +1.5925% 未触发'),
    'hk_after_mv': pc['discipline']['hk_after'], 'cash_after_mv': pc['discipline']['cash_after'],
    'weight_after': pc['discipline']['weight_after'],
    'next_trigger': {'line': 4000, 'hstech_close': 4045.91, 'gap_pct': 1.1478,
                     'amount_if_triggered': round(TOTAL * 0.005, 2),
                     'targets': ['012348（天弘恒生科技联接A）', '513180（恒生科技ETF华夏）'],
                     'note': '4,000 为本季新设观察线，首次收盘价跌破即 0.5% 纪律减仓（分母 = 本档总资产 372,920.01 元）'},
}

# ---------- 3. 归因与验证 ----------
attrib = []
for k, v in sorted(T.items(), key=lambda kv: -kv[1]['pnl']):
    attrib.append({'track': k, 'mv': round(v['mv'], 2), 'weight_pct': W[k],
                   'pnl': round(v['pnl'], 2), 'day_pct': v['day_pct'],
                   'share_of_total_pnl_pct': round(v['pnl'] / pc['est_total_pnl'] * 100, 1) if pc['est_total_pnl'] else None})

verification = {
    'close_vs_intraday': {'intraday_pnl': pi['total_delta'], 'intraday_pct': pi['est_total_pct'],
                          'close_pnl': pc['est_total_pnl'], 'close_pct': pc['est_total_pct_raw'],
                          'delta_pnl': round(pc['est_total_pnl'] - pi['total_delta'], 2),
                          'note': ('盘中 13:45 估算 −370.62 元 → 收盘 +756.05 元（**Δ +1,126.67 元**）；'
                                   '**四条归因（按量级）**：① 场外基金由「10/19 净值 + 板块代理」切换为 **10/20 真实净值**'
                                   '（A股医药 +346 元 / 大消费 +411 元）；② 场内 A股 收盘价替换 13:45 盘中价（其他/宽基 +460 元）；'
                                   '③ 港股收盘定档（恒生科技 +258 元，因 012348 未定价、跌幅未全额传导）；'
                                   '④ **QDII 10/19 净值在收盘档兑现 −349 元，盘中档为 0** → 该项为唯一负向修正')},
    'intraday_assumption_broken': [
        {'assumption': '盘中档推断「A股医药为唯一正贡献腿、其余四腿皆负」',
         'realized': '收盘 A股医药 +1,256.96 元、其他/宽基转正 +39.49 元、大消费收窄至 −120.27 元、恒生科技收窄至 −71.12 元',
         'verdict': '⚠️ 方向大体成立，但**幅度系统性低估**（盘中用 10/19 净值作锚，滞后一日）'},
        {'assumption': '盘中档记「恒生科技复市首日补跌 −1.65%，组合腿 −328.96 元」',
         'realized': '收盘恒科 −1.52%、组合腿仅 −71.12 元',
         'verdict': '❌ 组合腿损益被高估 4.6 倍：**012348 净值未出库 → 45.2% 的敞口未定价**（影子 −180 元）'},
        {'assumption': '盘中档未计入 QDII 兑现（美股腿 0 元）',
         'realized': '收盘美股腿 −349.01 元（10/19 净值 −0.567% / −0.580%）',
         'verdict': '✅ 收盘档修正到位；但**净值日映射存疑（0.99 vs 1.49 两解）**'},
    ],
    'unpriced': {'count': len(pc['unpriced']), 'notional': pc['unpriced_total'],
                 'priceable_pct': pc['priceable_pct'],
                 'codes': [u['code'] for u in pc['unpriced']],
                 'gap_estimate_note': (f"3 行未定价（012348 双账户 13,945.72 元 + 000051 9,061 元量级）按基准计 0；"
                                       f"影子估算合计 **{pc['unpriced_shadow']['total_est_pnl']:+,.2f} 元**"
                                       "（012348 按恒生科技 −1.52%×0.85、000051 按沪深300 −0.54%×0.98），**不并入主口径**；"
                                       "两券 10/20 净值若于 10/21 出库，须以 `_fix` 覆盖并同步重算 tracks[].pnl（§3.109 条款 26）")},
}

# ---------- 4. 明日（10/21）预案 ----------
tomorrow = [
    {'item': '未定价券兜底复抓', 'detail': '012348（恒生科技联接）/ 000051（沪深300联接）10/20 净值 → 到位即以 `_fix` 覆盖，'
                                          '硬守卫 `|Σ tracks.mv − total_mv| < 1.5` + `|Σ tracks.pnl − est_total_pnl| < 1.5`', 'priority': 'P0'},
    {'item': '519915 净值占位复核', 'detail': '10/20 净值 1.8050 / 日增长 0.00%（10/19 为 +1.805%、中证消费 −0.35%）→ 疑占位；'
                                             '若确认为占位，大消费腿 −120.27 元 需按真实净值重算（量级 ±300 元）', 'priority': 'P0'},
    {'item': '恒生科技 4,000 观察线', 'detail': '当前 +1.1478%（日内低 4,026.90）；**收盘价跌破即触发本季新设防线的首次 0.5% 减仓 1,864.60 元**'
                                          '（= 372,920.01 × 0.5%），标的限纯恒科 012348 / 513180', 'priority': 'P0'},
    {'item': 'QDII US 10/20 段挂账', 'detail': 'US 10/20 收盘成型于北京 10/21 04:00 → 10/21 盘前档可登记、10/21 盘后档按净值兑现；'
                                            '**系数未重估前只给区间、不给中枢点值**（§3.118a）', 'priority': 'P1'},
    {'item': '三季报窗口跟踪（10/21-10/31）', 'detail': '关注组合医药腿主动基（002708 / 161616 / 000727）与大消费腿（519915）重仓股的业绩预告/快报', 'priority': 'P1'},
    {'item': 'ESMO 大会（10/23-27）', 'detail': '创新药临床数据集中披露 → 医药腿情绪催化；**会前抢跑、会后回落是常见形态**，不据此加仓', 'priority': 'P2'},
    {'item': '中东尾部风险触发器', 'detail': '布伦特 > 115 美元 / 霍尔木兹实际通行中断 / 苏伊士航线改道 → 任一成立即上调全组合风险等级', 'priority': 'P2'},
]

risk = {
    'chain_cum_pct': rk['chain_cum_pct'], 'chain_days': rk['chain_days'],
    'sharpe': rk.get('sharpe'), 'rf_pct': rk.get('rf_pct', 1.68),
    'mdd_pct': rk.get('max_dd_pct'), 'mdd_peak': rk.get('max_dd_peak'),
    'mdd_trough': rk.get('max_dd_trough'),
    'w43_pct': rk.get('w43_cum_pct'), 'w43_days': rk.get('w43_days'),
    'ret_5d_pct': rk.get('last5_cum_pct'), 'ret_10d_pct': rk.get('last10_cum_pct'),
    'note': 'rf 仍为硬编码 1.68%（10Y 序列自 2026-08-11 未维护）→ 夏普绝对水平不可引用，只看方向与相对变化',
}

sentiment = {'window_net_nominal': es['track_net_sentiment_close'] and round(sum(es['track_net_sentiment_close'].values()), 2),
             'window_net_weighted': es['exposure_weighted_net_sentiment_close'],
             'day_net_nominal': round(sum(es['track_net_sentiment_day_all'].values()), 2),
             'day_net_weighted': es['exposure_weighted_net_sentiment_day_all'],
             'annotation_mode': 'rule_table_fallback', 'degraded_items': 22,
             'note': 'DeepSeek HTTP 402 连续第 15 个日历日；本档 22/22 条为规则表标注，跨档比较须标注口径差异'}

out = {
    'date': TODAY, 'as_of': '2026-10-20 收盘（正常交易日：A股 15:00 收盘 + 港股复市 16:00 收盘 + 美股未开盘）',
    'session_type': 'normal_trading_day_close',
    'total_mv': TOTAL, 'est_total_pnl': pc['est_total_pnl'], 'est_total_pct': pc['est_total_pct_raw'],
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
                 'note': '只报赛道层 8.28% 会低估宽基恒生系 4.79pct（§3.108 条款 23）'},
    'event_lib': {'total_events': es['total_events'], 'session_added': es['session_added'],
                  'session_backfilled_total': es['session_backfilled_total'],
                  'session_prior_filled': es['session_prior_filled'],
                  'blank': es['blank'],
                  'ref_by_track': es['reference_trading_day_by_track'],
                  'note': ('本档盘后窗口 22 条全部留空（参考日 = 10/21 或 US 10/20），属预期状态；'
                           '本档回填 71 条（含 10/19 恒科类 ref=10/20 的条目，港股复市后可回填）')},
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
print('情绪:', sentiment)
