# -*- coding: utf-8 -*-
"""2026-10-22 盘后档策略计算（档型②：正常交易日双收盘）

输入：portfolio_close_20261022.json / risk_stats_close_20261022.json /
      event_stats_20261022_close.json / sentiment_agg_20261022_close.json
输出：portfolio_strategy_close_20261022.json
纪律：赛道级动作区间 [0%, 0%]（无「已触发且当日可执行」项）；
      恒科 3,950 收盘失守 → 新线建案 1,858.66 元（10/23 盘前执行）；
      医药反向线第 4 次触发 → 建案 1,858.66 元但**低置信度、次于恒科、不同时执行**
"""
import json, os

BASE = '/Users/jieyang/Documents/WealthHub'
HIST = os.path.join(BASE, 'data/processed/history')
TODAY, TODAYC = '2026-10-22', '20261022'

pc = json.load(open(os.path.join(HIST, f'portfolio_close_{TODAYC}.json'), encoding='utf-8'))
rk = json.load(open(os.path.join(HIST, f'risk_stats_close_{TODAYC}.json'), encoding='utf-8'))
es = json.load(open(os.path.join(HIST, f'event_stats_{TODAYC}_close.json'), encoding='utf-8'))
sa = json.load(open(os.path.join(HIST, f'sentiment_agg_{TODAYC}_close.json'), encoding='utf-8'))

T, TOTAL = pc['tracks'], pc['total_mv']
W = {k: round(v['mv'] / TOTAL * 100, 2) for k, v in T.items()}
assert abs(sum(W.values()) - 100) < 0.05, f'权重合计异常 {W}'
assert abs(pc['med_pct'] - 39.09) < 0.02, f"医药敞口 {pc['med_pct']} != 39.09"
assert pc['chain_0pct_row_inserted'] is False

D = pc['discipline']
PLAN_4000 = 1863.33
PLAN_3950 = [p for p in D['pending_plans'] if '3,950' in p['trigger']][0]['amount']
PLAN_MED = [p for p in D['pending_plans'] if '医药' in p['trigger']][0]['amount']
assert abs(PLAN_3950 - 1858.66) < 0.02, PLAN_3950
assert abs(PLAN_MED - 1858.66) < 0.02, PLAN_MED

HS = pc['hk_mkt']['HSTECH']
H4200 = round((HS['close'] / 4200 - 1) * 100, 4)
H3700 = round((HS['close'] / 3700 - 1) * 100, 4)
H3600 = round((HS['close'] / 3600 - 1) * 100, 4)

track_actions = [
    {'track': '恒生科技', 'weight_pct': W['恒生科技'], 'mv': T['恒生科技']['mv'],
     'pnl_today': T['恒生科技']['pnl'], 'action_range_pct': [0, 0], 'amount': 0,
     'rationale': (f'**本档第二大拖累腿（{T["恒生科技"]["pnl"]:+,.2f} 元 / {T["恒生科技"]["day_pct"]:+.3f}%）**，'
                   f'收盘 **{HS["close"]:.2f}（{HS["pct"]:+.2f}%）** → **4,000 与 3,950 两线同日收盘失守**、'
                   f'3,800 亦在下方（{round((HS["close"]/3800-1)*100,4):+.4f}%）；'
                   f'**4,000 线预案（{PLAN_4000:,.2f} 元）执行状态仍待用户确认** → 本档按「未确认 = 未计入」处理；'
                   f'**本档动作 0 元**，只按 3,950 线建 −0.5% 预案 **{PLAN_3950:,.2f} 元**（10/23 盘前执行），'
                   f'3,800 破位仅登记（§3.114c 同日不重复触发），下一参考位下移至 3,700（距 {H3700:+.4f}%）；'
                   f'腿内 −1,189.41 元 中 164906 的 10/21 净值 −1.66% 已计入'),
     'gates': ['hstech_4000: breach_widened → plan_awaiting_confirmation',
               'hstech_3950: close_level_breached_today → new_plan_created',
               'hstech_3800: registered_only']},

    {'track': '其他/宽基', 'weight_pct': W['其他/宽基'], 'mv': T['其他/宽基']['mv'],
     'pnl_today': T['其他/宽基']['pnl'], 'action_range_pct': [0, 0], 'amount': 0,
     'rationale': (f'**本档最大拖累腿（{T["其他/宽基"]["pnl"]:+,.2f} 元 / {T["其他/宽基"]["day_pct"]:+.3f}%）**；'
                   '驱动 = 沪深300 −1.84% + 创业板 −4.37% + 中证环保 −1.48%，**单券最大负贡献为广联达 −2.34%（−895.97 元）'
                   '占该腿亏损 48.8%**；结构上该腿**偏大盘、不持银行** → 既未享受「银行创新高」护盘、'
                   '也未享受「小盘抗跌」（本档无小盘抗跌），**弱于上证 −1.48% 属结构必然**；'
                   '**无专项防线、无风格切换证据**（放量下跌 998 亿元属「主动减仓」而非「风格轮动」）→ 动作 0 元'),
     'gates': ['无（该腿无价格防线）']},

    {'track': 'A股医药', 'weight_pct': W['A股医药'], 'mv': T['A股医药']['mv'],
     'pnl_today': T['A股医药']['pnl'], 'action_range_pct': [0, 0], 'amount': 0,
     'rationale': (f'−1,305.52 元（−1.576%），**板块代理 −1.895%（四口径均值）→ 反向兑现线第 4 次触发**；'
                   '**但归因为 β 而非 α**（药财社：10/22 无医药行业新增重大利空，纯跟随风险偏好）；'
                   '**该线本季 4 次触发、前 3 次次日全部转正 → 判别力接近零** → 按剧本 C **只建案 '
                   f'{PLAN_MED:,.2f} 元（0.5%）并标注低置信度**、**10/23 盘前复核后再决定是否执行**、'
                   '**优先级低于恒科 3,950 线、两案不同时执行**；'
                   f'**敞口 {pc["med_pct"]}%、距 40% 仅 {round(40-pc["med_pct"],2)}pct，门槛 +{pc["threshold_all_med"]}%（两腿同涨）/ '
                   f'+{pc["threshold_a_sh_med"]}%（仅 A股医药）→ `new_buy = 0`**；'
                   f'`002708` 双账户 25,217.77 元（6.88%）10/22 净值未出库 → 腿损益属偏低口径'),
     'gates': ['a_med_reverse_1_5pct: triggered_4th_time_low_confidence',
               'med_cap_40pct: headroom_0.91pct']},

    {'track': '大消费', 'weight_pct': W['大消费'], 'mv': T['大消费']['mv'],
     'pnl_today': T['大消费']['pnl'], 'action_range_pct': [0, 0], 'amount': 0,
     'rationale': (f'−579.47 元（−0.774%），**六赛道中表现第二好的权益腿** —— 与 10/21「最大拖累（−1.01%）」**完全反转**；'
                   '中证消费 −0.42% vs 创业板 −4.37%（**差异 3.95pct**）→ **防御属性首次显现**；'
                   '**距 12,100 下沿 +1.2279%（10/21 为 +1.6536%，连续 2 日收窄、累计收窄 0.4257pct）→ 仍在安全区但缓冲变薄**；'
                   '白酒动销下滑 + 三季报强分化出清仍在，**茅台三季报 10/31 是唯一硬验证** → 不加不减'),
     'gates': ['zz_consume_12100: above_lower_line_narrowing', 'maotai_q3: disclosure_2026-10-31']},

    {'track': '美股标普医药', 'weight_pct': W['美股标普医药'], 'mv': T['美股标普医药']['mv'],
     'pnl_today': T['美股标普医药']['pnl'], 'action_range_pct': [0, 0], 'amount': 0,
     'rationale': ('−116.32 元（−0.188%），**本档唯一「亏损小于预告下界」的腿**：13:45 档登记挂账区间 '
                   '−222.85 ~ −148.56 元，实测 −116.32 元 **优于最优端 32.24 元** → 传导系数 0.4657 / 0.4740，'
                   '**低于 0.60 下界（区间法第 7 样本、第 5 例越界，首次为「下跌段实际跌幅小于下界」）** → '
                   '**系数存在方向不对称，单点值不可用**；US 10/22 尚未开盘（北京 20:00 = 美东 08:00）→ '
                   '**只登记新窗口、不给数值**；QDII T+2 确认、T+3 到账 → **净值为盲区时不下单**'),
     'gates': ['qdii_transmission_coef: pending (asymmetric)', 'us_1022: not_closed']},

    {'track': '现金', 'weight_pct': W['现金'], 'mv': T['现金']['mv'],
     'pnl_today': T['现金']['pnl'], 'action_range_pct': [0, 0], 'amount': 0,
     'rationale': (f'无交易；纪律后权重 {D["weight_after"]["现金"]}%（累计已成交减仓 {D["cumulative_amount"]:,.2f} 元）；'
                   f'**若 10/23 执行恒科 3,950 预案 {PLAN_3950:,.2f} 元，现金权重升至 '
                   f'{round((T["现金"]["mv"] + PLAN_3950) / TOTAL * 100, 2)}%**；'
                   f'若 4,000 线预案亦已执行（未确认），现金将再 +{PLAN_4000:,.2f} 元'),
     'gates': [f'pending: 恒科 3,950 → {PLAN_3950:,.2f} 元', f'pending_confirm: 恒科 4,000 → {PLAN_4000:,.2f} 元']},
]

constraints = {
    'single_track_cap_pct': 40, 'max_single_trade_pct': 5, 'max_single_trade_used_pct': 0,
    'new_buy': 0, 'active_take_profit': 0, 'status': 'two_plans_pending_execution',
    'med_exposure': {'mv': pc['med_exposure'], 'pct': pc['med_pct'],
                     'headroom_pct': round(40 - pc['med_pct'], 2),
                     'threshold_all_med_pct': pc['threshold_all_med'],
                     'threshold_a_sh_med_pct': pc['threshold_a_sh_med'],
                     'note': ('门槛 = 解方程 `A(1+r)/(B+A·r)=0.40`；+3.90% 意味着医药需单日普涨 3.90% 才会被动突破上限 '
                              '→ **0.91pct 余量不等于「逼近上限」**（§3.98）')},
    'pending_plan_stack': {
        'hstech_3950': {'amount': PLAN_3950, 'pct': 0.5, 'basis': f'0.5% × {TOTAL:,.2f} 元',
                        'execute_on': '不早于 2026-10-23 盘前档', 'today_executed': 0,
                        'targets_rule': '纯恒科口径（012348 / 513180），不落中概（513050 / 164906）'},
        'a_med_reverse': {'amount': PLAN_MED, 'pct': 0.5, 'basis': f'0.5% × {TOTAL:,.2f} 元',
                          'execute_on': '不早于 2026-10-23 盘前档', 'today_executed': 0,
                          'confidence': 'low_3_of_3_prior_triggers_invalidated',
                          'priority': '低于恒科 3,950 线；两案不同时执行'},
        'hstech_4000_awaiting_confirm': {'amount': PLAN_4000, 'pct': 0.5,
                                         'basis': '0.5% × 372,666.60 元（10/22 盘前建案，不重设分母）',
                                         'status': 'awaiting_user_confirmation'},
        'max_combined_if_all_executed_pct': round((PLAN_3950 + PLAN_MED + PLAN_4000) / TOTAL * 100, 3),
        'note': ('若三案全部执行，合计减仓 '
                 f'{PLAN_3950 + PLAN_MED + PLAN_4000:,.2f} 元 = {round((PLAN_3950+PLAN_MED+PLAN_4000)/TOTAL*100,2)}% 组合，'
                 '**仍低于单次调仓 5% 上限**；但**建议只执行恒科 3,950 一案**（医药案判别力低、4,000 案未确认）'),
    },
}

risk = {
    'chain_cum_pct': rk['chain_cum_pct'], 'chain_days': rk['chain_days'],
    'sharpe': rk['sharpe'], 'sharpe_n': rk['sharpe_n'],
    'max_dd_pct': rk['max_dd_pct'], 'max_dd_peak': rk['max_dd_peak'], 'max_dd_trough': rk['max_dd_trough'],
    'w43_cum_pct': rk['w43_cum_pct'], 'w43_days': rk['w43_days'],
    'last5_cum_pct': rk['last5_cum_pct'], 'last10_cum_pct': rk['last10_cum_pct'],
    'rf_pct': rk['rf_pct'], 'rf_note': rk['rf_note'],
    'max_dd_new_low': True,
    'max_dd_note': f'MDD 由 −7.10% 扩大至 {rk["max_dd_pct"]}%，**谷值刷新至 {rk["max_dd_trough"]}**（原谷值 10/16）',
}

tomorrow = [
    {'priority': 'P0', 'item': f'恒科 3,950 线减配预案执行（{PLAN_3950:,.2f} 元 / 0.5%）',
     'rule': '10/23 盘前档确认后、当日收盘前执行；标的限纯恒科 012348 / 513180；'
             '**纪律优先于择时** —— 若 10/23 盘前恒科反弹站回 4,000 以上，默认仍执行；同日不与 4,000/3,800 线叠加'},
    {'priority': 'P0', 'item': f'4,000 线预案（{PLAN_4000:,.2f} 元）执行状态确认',
     'rule': '**须由用户明确「已执行 / 未执行」**；若已执行 → 累计纪律 5,650.23 元（3 次）、恒科 −1,863.33 元、现金 +1,863.33 元，'
             '并在下一档补登；**不得静默作废**（§3.110）'},
    {'priority': 'P0', 'item': '`002708` 大摩健康产业 10/22 净值兜底复抓',
     'rule': '双账户 25,217.77 元（6.88%）→ 到位即以 10/22 同日 `_fix` 覆盖，**并同步重算 `tracks[].pnl`**'
             '（守卫 |Σpnl − est_total_pnl| < 1.5）'},
    {'priority': 'P0', 'item': '医药反向线第 4 次触发复盘',
     'rule': '10/23 盘前先判「10/22 板块代理 −1.895% 是否被次日反转」；**若连续第 4 次次日转正 → 该线正式注销、'
             '不再建案**（判别力 0/3 → 0/4 即判定失效）'},
    {'priority': 'P1', 'item': 'QDII US 10/22 段挂账',
     'rule': 'US 10/22 收盘成型于北京 10/23 04:00 → 10/23 盘前档按 IYH 实际涨跌给区间（0.45~0.90 弹性，'
             '**因本档实测下跌段系数 0.47 已低于原下界，区间须放宽下界**），不得给点值'},
    {'priority': 'P1', 'item': '恒科 3,700 / 3,600 技术位登记',
     'rule': f'3,700 距 {H3700:+.4f}%、3,600 距 {H3600:+.4f}%；**若 10/23 收盘再破 3,700 → 按新线建案，同日不重复扣减**'},
    {'priority': 'P1', 'item': '中证消费 12,100 逐日复核',
     'rule': '+1.2279%（连续 2 日收窄）→ 缓冲变薄，**若收盘 < 12,150 须在盘前档建减配预案**'},
    {'priority': 'P2', 'item': '`indices.csv` code 口径统一（`sh000933` vs `000933`）',
     'rule': '000933 仅 22 个交易日（vs 399006 的 81）→ distinct 天数系统性偏差，登记长期待办（§3.163b）'},
    {'priority': 'P2', 'item': '历史数据卫生',
     'rule': '两件 `_fix` 不自洽（20260918 / 20260921）、`fund_nav.csv` 历史重复键、`gb_*` 兜底 `prev_date` 未回填'},
]

out = {
    'date': TODAY, 'session_type': 'normal_trading_day_close',
    'total_mv': TOTAL, 'est_total_pnl': pc['est_total_pnl'], 'est_total_pct': pc['est_total_pct_raw'],
    'weights': W, 'track_actions': track_actions, 'constraints': constraints, 'risk': risk,
    'sentiment': {'window_count': sa['count'], 'mean_strength': sa['mean_strength'],
                  'net_nominal': sa['net_nominal'], 'exposure_weighted_net': sa['exposure_weighted_net'],
                  'direction_count': sa['direction_count'], 'by_track': sa['by_track'],
                  'annotation_mode': sa['annotation_mode']},
    'events': {'total': es['total_events'], 'today': es['today_events'], 'added': es['added'],
               'backfilled': es['session_backfilled_total'], 'blank': es['blank'],
               'jaccard_mean': es['jaccard_mean_all']},
    'tomorrow_plan': tomorrow,
    'discipline_total': D['cumulative_amount'],
    'note': ('赛道级动作全部 0 元（区间 [0%, 0%]）；两案为「建案」而非成交（恒科 3,950 = 1,858.66 元、'
             '医药反向 = 1,858.66 元低置信度），4,000 线预案执行状态待用户确认 → 均不计入本档成交；'
             '单次调仓上限 5%、单赛道上限 40% 均未触碰'),
}
json.dump(out, open(os.path.join(HIST, f'portfolio_strategy_close_{TODAYC}.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)

print('权重:', W)
print(f'组合 {pc["est_total_pnl"]:+,.2f} 元 / {pc["est_total_pct_raw"]:+.4f}% → {TOTAL:,.2f} 元')
print(f'恒科 3,950 建案 {PLAN_3950:,.2f} / 医药建案 {PLAN_MED:,.2f} / 4,000 待确认 {PLAN_4000:,.2f}')
print(f'风险：链路 {rk["chain_cum_pct"]}% / 夏普 {rk["sharpe"]} / MDD {rk["max_dd_pct"]}% / W43 {rk["w43_cum_pct"]}%')
print('明日待办', len(tomorrow), '项')
