# -*- coding: utf-8 -*-
"""2026-10-21 盘后档策略计算（档型②：正常交易日双收盘）

输入：portfolio_close_20261021.json / portfolio_intraday_20261021.json /
      risk_stats_close_20261021.json / event_stats_20261021_close.json /
      sentiment_agg_20261021_close.json
输出：portfolio_strategy_close_20261021.json
纪律：赛道级动作区间 [0%, 0%]（无「已触发且当日可执行」项）；
      恒科 4,000 破位 → 预案 1,863.33 元，**10/22 盘前建案、本档不执行**
"""
import json, os

BASE = '/Users/jieyang/Documents/WealthHub'
HIST = os.path.join(BASE, 'data/processed/history')
TODAY, TODAYC = '2026-10-21', '20261021'

pc = json.load(open(os.path.join(HIST, f'portfolio_close_{TODAYC}.json'), encoding='utf-8'))
pi = json.load(open(os.path.join(HIST, f'portfolio_intraday_{TODAYC}.json'), encoding='utf-8'))
rk = json.load(open(os.path.join(HIST, f'risk_stats_close_{TODAYC}.json'), encoding='utf-8'))
es = json.load(open(os.path.join(HIST, f'event_stats_{TODAYC}_close.json'), encoding='utf-8'))
sa = json.load(open(os.path.join(HIST, f'sentiment_agg_{TODAYC}_close.json'), encoding='utf-8'))

T, TOTAL = pc['tracks'], pc['total_mv']
W = {k: round(v['mv'] / TOTAL * 100, 2) for k, v in T.items()}
assert abs(sum(W.values()) - 100) < 0.05, f'权重合计异常 {W}'
assert abs(pc['med_pct'] - 38.96) < 0.02, f"医药敞口 {pc['med_pct']} != 38.96"
assert pc['chain_0pct_row_inserted'] is False

D = pc['discipline']
PLAN = D['pending_plan']['amount']
assert abs(PLAN - 1863.33) < 0.02, PLAN

track_actions = [
    {'track': '恒生科技', 'weight_pct': W['恒生科技'], 'mv': T['恒生科技']['mv'],
     'pnl_today': T['恒生科技']['pnl'], 'action_range_pct': [0, 0], 'amount': 0,
     'rationale': ('**唯一触发纪律的一条腿，但按预案本档不执行。** 收盘 3,994.77 首次收盘失守 4,000（−0.1308%），'
                   '距 4,250 −6.0054%（10/20 −4.8021%，再走阔 1.2033pct）；'
                   '**4,250 线本季已用 2 次 → 同日/同季不重复叠加（§3.114c）**；'
                   '13:45 档 P0 预案明确「收盘 <4,000 → 观察线升级为防线、10/22 盘前建 −0.5% 减配预案、当日不执行」→ '
                   f'**今日动作 0 元、明日预案 {PLAN:,.2f} 元**（纯恒科 012348/513180，不落中概）；'
                   '本档腿内 −395.00 元（−1.288%）已含 164906 的 10/20 净值 −1.13%'),
     'gates': ['hstech_4000: close_level_breached → plan_next_preopen', 'hstech_4250: break_widened_no_new_cut']},

    {'track': '大消费', 'weight_pct': W['大消费'], 'mv': T['大消费']['mv'],
     'pnl_today': T['大消费']['pnl'], 'action_range_pct': [0, 0], 'amount': 0,
     'rationale': ('**本档最大拖累腿（−763.88 元 / −1.010%）**，驱动 = 中证白酒 −2.46% + 茅台 −1.67% + 价盘走弱；'
                   '**距 12,100 防线 +1.6536%（两日收窄 1.0155pct）→ 仍在安全区、未触线**；'
                   '**茅台三季报预约披露日 = 10/31（本档已更正 13:45 档的错误前提）** → '
                   '**原「净利增速 <10% 即建减配预案」的条件动作作废**，改为 10/31 前跟踪；'
                   '**权重 20.14% 已足、卖方共识仅为「出清中」非「反转」→ 不加仓**'),
     'gates': ['zz_consume_12100: above_lower_line', 'maotai_q3: disclosure_2026-10-31']},

    {'track': '其他/宽基', 'weight_pct': W['其他/宽基'], 'mv': T['其他/宽基']['mv'],
     'pnl_today': T['其他/宽基']['pnl'], 'action_range_pct': [0, 0], 'amount': 0,
     'rationale': ('−632.76 元（−0.679%），**主因是权重股而非全市场**：沪深300 −0.97%、中证金融 −0.70%、'
                   '中证环保 −2.62%、证券公司 −1.07%；**同期中证1000 +0.20%、数据要素/AI 漫剧走强 → '
                   '组合宽基腿偏大盘、不享受小盘与主题红利**；'
                   '广联达 −0.47%（−179.22 元，腿内最大单券拖累）；无专项防线、无风格切换证据（成交缩量 268 亿）→ 动作 0'),
     'gates': ['无']},

    {'track': 'A股医药', 'weight_pct': W['A股医药'], 'mv': T['A股医药']['mv'],
     'pnl_today': T['A股医药']['pnl'], 'action_range_pct': [0, 0], 'amount': 0,
     'rationale': ('−228.75 元（−0.275%），**跌幅显著小于沪深300，符合「医药结构性抗跌」**；'
                   '**ESMO 10/23-27 是关键催化剂但尚未兑现，会前阵容≠临床结果 → 不提前定价**；'
                   '**敞口 38.96%、距 40% 仅 1.04pct，门槛收益率 +4.45%（两腿同涨）/ +7.76%（仅 A股医药）** → '
                   '**加仓空间被硬约束封死、`new_buy = 0`**；反向兑现线代理 −0.3825% 未触发（距 −1.5% 尚 +1.1175pct）；'
                   '`002708`（22,246.77 元）10/21 净值未出库 → 腿损益属偏低口径'),
     'gates': ['med_cap_40pct: headroom_1.04pct', 'a_med_reverse_1_5pct: not_triggered']},

    {'track': '美股标普医药', 'weight_pct': W['美股标普医药'], 'mv': T['美股标普医药']['mv'],
     'pnl_today': T['美股标普医药']['pnl'], 'action_range_pct': [0, 0], 'amount': 0,
     'rationale': ('**唯一正贡献腿 +1,209.91 元（+1.994%）** = QDII US 10/20 段按真实净值核销；'
                   '隐含系数 0.8447 / 0.8597（分母 IYH +2.34%），**落 0.60~0.90 区间内（区间法第 6 样本、第 4 例成立）**；'
                   '**但净值日 ↔ 美股交易日映射仍未确定 → 系数为「区间可用、点值 pending」**；'
                   'US 10/21 尚未开盘（北京 20:00 = 美东 08:00）→ **本档无新增确认权、只建新挂账段**；'
                   'QDII 申赎 T+2 → 任何基于当日读数的动作都不可执行'),
     'gates': ['qdii_transmission_coef: pending', 'us_1021: not_closed']},

    {'track': '现金', 'weight_pct': W['现金'], 'mv': T['现金']['mv'],
     'pnl_today': T['现金']['pnl'], 'action_range_pct': [0, 0], 'amount': 0,
     'rationale': (f'无交易；纪律后权重 {D["weight_after"]["现金"]}%（累计减仓 {D["cumulative_amount"]:,.2f} 元已成交）；'
                   f'**明日预案若执行，现金权重将升至 {round((T["现金"]["mv"] + PLAN) / TOTAL * 100, 2)}%**'),
     'gates': [f'pending_plan: {PLAN:,.2f} 元 @ 10/22 盘前']},
]

constraints = {
    'single_track_cap_pct': 40, 'max_single_trade_pct': 5, 'max_single_trade_used_pct': 0,
    'new_buy': 0, 'active_take_profit': 0, 'status': 'plan_pending_execution',
    'med_exposure': {'mv': pc['med_exposure'], 'pct': pc['med_pct'],
                     'headroom_pct': round(40 - pc['med_pct'], 2),
                     'threshold_all_med_pct': pc['threshold_all_med'],
                     'threshold_a_sh_med_pct': pc['threshold_a_sh_med'],
                     'note': ('门槛 = 解方程 `A(1+r)/(B+A·r)=0.40`；+4.45% 意味着医药需单日普涨 4.45% 才会被动突破上限 '
                              '→ **不得把 1.04pct 余量读作「逼近上限」**（§3.98）')},
    'hstech_plan': {'amount': PLAN, 'pct': 0.5, 'basis': f'0.5% × {TOTAL:,.2f} 元',
                    'execute_on': '不早于 2026-10-22 盘前档', 'today_executed': 0,
                    'targets_rule': '纯恒科口径（012348 / 513180），不落中概（513050 / 164906）'},
}

risk = {
    'chain_cum_pct': rk['chain_cum_pct'], 'chain_days': rk['chain_days'],
    'sharpe': rk['sharpe'], 'sharpe_n': rk['sharpe_n'],
    'max_dd_pct': rk['max_dd_pct'], 'max_dd_peak': rk['max_dd_peak'], 'max_dd_trough': rk['max_dd_trough'],
    'w43_cum_pct': rk['w43_cum_pct'], 'w43_days': rk['w43_days'],
    'last5_cum_pct': rk['last5_cum_pct'], 'last10_cum_pct': rk['last10_cum_pct'],
    'rf_pct': rk['rf_pct'], 'rf_note': rk['rf_note'],
}

tomorrow = [
    {'priority': 'P0', 'item': f'恒科 4,000 破位减配预案建案（{PLAN:,.2f} 元 / 0.5%）',
     'rule': '10/22 盘前档建立、**当日收盘前执行**；标的限纯恒科 012348 / 513180；若 10/22 盘前恒科已反弹站回 4,050 以上，'
             '是否仍执行须在本档口径内明示（默认执行，纪律优先于择时）'},
    {'priority': 'P0', 'item': '`002708` 大摩健康产业 10/21 净值兜底复抓',
     'rule': '22,246.77 元（6.0% 组合）未定价 → 到位即以 10/21 同日 `_fix` 覆盖，并同步重算 `tracks[].pnl`（守卫 |Σpnl−total|<1.5）'},
    {'priority': 'P0', 'item': '茅台三季报披露日更正后的跟踪落地',
     'rule': '**10/31 前不做任何三季报驱动的动作**；三季报密集期（10/19-10/31）内逐日核对交易所预约披露表'},
    {'priority': 'P1', 'item': 'QDII US 10/21 段挂账',
     'rule': 'US 10/21 收盘成型于北京 10/22 04:00 → 10/22 盘前档按 IYH 实际涨跌给出区间（0.60~0.90 弹性），'
             '不得给点值；`000369`/`016280` 10/21 净值最早 10/22 出库'},
    {'priority': 'P1', 'item': 'ESMO 10/23 开幕前观察',
     'rule': '会前阵容不等于临床数据；10/23-27 逐日登记 ORR/PFS 读数，仅在实际读出后调整医药腿判断'},
    {'priority': 'P1', 'item': '恒生科技 4,000 之后的技术位',
     'rule': '下一观察位 3,950（卖方参考位，非本档防线）；若 10/22 收盘再破 3,950 → 按新的 −0.5% 建案，**同日不重复扣减**'},
    {'priority': 'P2', 'item': '`indices.csv` code 口径统一（`sh000933` vs `000933`）',
     'rule': '000933 仅 21 个交易日（vs 399006 的 80）→ distinct 天数系统性偏差，登记长期待办（§3.163b）'},
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
    'note': ('赛道级动作全部 0 元（区间 [0%, 0%]）；恒科 4,000 破位属「已触发但按预案顺延至 10/22 盘前建案」，'
             '不计入本档成交；单次调仓上限 5%、单赛道上限 40% 均未触碰'),
}
json.dump(out, open(os.path.join(HIST, f'portfolio_strategy_close_{TODAYC}.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)

print('权重:', W)
print(f'组合 {pc["est_total_pnl"]:+,.2f} 元 / {pc["est_total_pct_raw"]:+.4f}% → {TOTAL:,.2f} 元')
print(f'恒科预案 {PLAN:,.2f} 元（本档执行 0）')
print(f'风险：链路 {rk["chain_cum_pct"]}% / 夏普 {rk["sharpe"]} / MDD {rk["max_dd_pct"]}% / W43 {rk["w43_cum_pct"]}%')
print('明日待办', len(tomorrow), '项')
