# -*- coding: utf-8 -*-
"""2026-10-23 盘后档策略计算（档型②：正常交易日双收盘）

输入：portfolio_close_20261023.json / risk_stats_close_20261023.json /
      event_stats_20261023_close.json / sentiment_agg_20261023_close.json
输出：portfolio_strategy_close_20261023.json

纪律：恒科 3,950 线（10/22 收盘失守建案）→ 10/23 为执行日，本档记 cut3 = 1,858.66 元；
      累计 5,645.56 元（3 笔）；4,000 案连续第 3 日待用户确认（不并入累计）；
      医药反向线 10/23 板块代理 +2.3725% → 第 4 次触发后当日转正 → 正式注销（0/4）。
赛道级动作：全部 0 元（区间 [0%, 0%]）。
"""
import json, os

BASE = '/Users/jieyang/Documents/WealthHub'
HIST = os.path.join(BASE, 'data/processed/history')
TODAY, TODAYC = '2026-10-23', '20261023'

pc = json.load(open(os.path.join(HIST, f'portfolio_close_{TODAYC}.json'), encoding='utf-8'))
rk = json.load(open(os.path.join(HIST, f'risk_stats_close_{TODAYC}.json'), encoding='utf-8'))
es = json.load(open(os.path.join(HIST, f'event_stats_{TODAYC}_close.json'), encoding='utf-8'))
sa = json.load(open(os.path.join(HIST, f'sentiment_agg_{TODAYC}_close.json'), encoding='utf-8'))

T, TOTAL = pc['tracks'], pc['total_mv']
W = {k: round(v['mv'] / TOTAL * 100, 2) for k, v in T.items()}
assert abs(sum(W.values()) - 100) < 0.05, f'权重合计异常 {W}'
assert abs(pc['med_pct'] - 38.98) < 0.02, f"医药敞口 {pc['med_pct']} != 38.98"
assert pc['chain_0pct_row_inserted'] is False
# 守卫：赛道 mv/pnl 与总量自洽（§3.109）
assert abs(sum(v['pnl'] for v in T.values()) - pc['est_total_pnl']) < 1.5, 'Σtracks.pnl 与总量不自洽'
assert abs(sum(v['mv'] for v in T.values()) - TOTAL) < 1.5, 'Σtracks.mv 与 total 不自洽'

D = pc['discipline']
CUM = D['cumulative_amount']
assert abs(CUM - 5645.56) < 0.02, CUM
CUT3 = D['today_action']['discipline_cut_today']
assert abs(CUT3 - 1858.66) < 0.02, CUT3
PLAN_4000 = 1863.33
PLAN_MED = 0.0
assert [p for p in D['pending_plans'] if '医药' in p['trigger']][0]['status'] == 'cancelled_line_deregistered'

HS = pc['hk_mkt']['HSTECH']
H_4000 = round((HS['close'] / 4000 - 1) * 100, 4)
H_3950 = round((HS['close'] / 3950 - 1) * 100, 4)
H_3800 = round((HS['close'] / 3800 - 1) * 100, 4)
H_3700 = round((HS['close'] / 3700 - 1) * 100, 4)
H_3600 = round((HS['close'] / 3600 - 1) * 100, 4)
CONSUME = pc['idx']['sh000932']['close']
C_12100 = round((CONSUME / 12100 - 1) * 100, 4)

# ---- 归因拆解（逐券口径，取自 detail）----
det = pc['detail']


def legs(pred):
    return [d for d in det if pred(d)]


hk_rows = legs(lambda d: d['track'] == '恒生科技')
lof_164906 = sum(d['est_pnl'] for d in hk_rows if '164906' in str(d['code']))
hk_pure = sum(d['est_pnl'] for d in hk_rows if '164906' not in str(d['code']))
assert abs(lof_164906 + hk_pure - T['恒生科技']['pnl']) < 0.05

# 002708 双账户（大消费）未定价 → 腿收益低估口径
unp = {u['code']: u for u in pc['unpriced']}
u2708 = sum(u['mv'] for u in pc['unpriced'] if u['code'] == '002708')
u0248 = sum(u['mv'] for u in pc['unpriced'] if u['code'] == '000248')
shadow_2708 = round(u2708 * pc['board_med'] / 100, 2)

# 恒生科技双层拆解（§3.108）
hks = pc['hk_split']
hk_total_pct = pc['hk_total'] / TOTAL * 100

track_actions = [
    {'track': '其他/宽基', 'weight_pct': W['其他/宽基'], 'mv': T['其他/宽基']['mv'],
     'pnl_today': T['其他/宽基']['pnl'], 'action_range_pct': [0, 0], 'amount': 0,
     'rationale': (f'**本档最大贡献腿（{T["其他/宽基"]["pnl"]:+,.2f} 元 / {T["其他/宽基"]["day_pct"]:+.3f}%）**；'
                   f'驱动 = 创业板 **+4.16%** + 深证成指 +2.79% + 沪深300 +1.71%，成长风格全面回补；'
                   f'单券最大正贡献 广联达 **+3.96%**、通威股份 +2.69%（前日分别为 −2.34% / 下跌）→ '
                   f'**昨日「最大拖累腿」今日「最大贡献腿」，一日反转 2.2pct 级**，属 β 回补而非结构性改善；'
                   f'**无专项防线、无新增动作** → 0 元'),
     'gates': ['无（该腿无价格防线）',
               'style_check: growth_catch_up_confirmed_not_rotation_into_value']},

    {'track': 'A股医药', 'weight_pct': W['A股医药'], 'mv': T['A股医药']['mv'],
     'pnl_today': T['A股医药']['pnl'], 'action_range_pct': [0, 0], 'amount': 0,
     'rationale': (f'{T["A股医药"]["pnl"]:+,.2f} 元（{T["A股医药"]["day_pct"]:+.3f}%）；板块代理 **+2.3725%**'
                   f'（中证医药 +2.35% / 中证医疗 +2.58% / 医疗ETF +2.45%），**第 4 次反向兑现线触发当日即转正 → '
                   f'该线正式注销（0/4）**；'
                   f'**腿收益属偏低口径**：`002708` 双账户 **{u2708:,.2f} 元（{u2708/TOTAL*100:.2f}%）** 10/23 净值未出库 → '
                   f'计 0，按板块代理影子估算应有 **{shadow_2708:+,.2f} 元** 未计入（另有 `000248` {u0248:,.2f} 元同样未定价）；'
                   f'**敞口 {pc["med_pct"]}%、距 40% 余量 {round(40-pc["med_pct"],2)}pct；'
                   f'门槛 +{pc["threshold_all_med"]}%（两腿同涨）/ +{pc["threshold_a_sh_med"]}%（仅 A股医药）→ `new_buy = 0`**'),
     'gates': ['a_med_reverse_1_5pct: deregistered_false_alarm (0/4)',
               'med_cap_40pct: headroom_2.02pct (threshold +4.34% / +7.66%)',
               'unpriced: 002708 + 000248 nav_pending → leg_pnl_understated']},

    {'track': '大消费', 'weight_pct': W['大消费'], 'mv': T['大消费']['mv'],
     'pnl_today': T['大消费']['pnl'], 'action_range_pct': [0, 0], 'amount': 0,
     'rationale': (f'{T["大消费"]["pnl"]:+,.2f} 元（{T["大消费"]["day_pct"]:+.3f}%）；中证消费 +1.44%、'
                   '中证白酒 **+2.70%**、贵州茅台 +1.25%、消费ETF +1.38% → **连续第 2 日跑赢创业板相对强度反转**'
                   '（10/22 消费 −0.42% vs 创业板 −4.37%，10/23 消费 +1.44% vs 创业板 +4.16%，**两日累计跑赢 3.95pct 后回吐 2.72pct**，'
                   '防御属性从「显现」转为「钝化」）；'
                   f'**中证消费 {CONSUME:,.2f} → 距 12,100 下沿 {C_12100:+.4f}pct（10/22 为 +1.2279%，缓冲恢复 1.46pct）** → '
                   '回到安全区中位；**茅台三季报 10/31 仍是唯一硬验证** → 不加不减'),
     'gates': ['zz_consume_12100: above_lower_line_buffer_restored (+2.6880%)',
               'maotai_q3: disclosure_2026-10-31']},

    {'track': '美股标普医药', 'weight_pct': W['美股标普医药'], 'mv': T['美股标普医药']['mv'],
     'pnl_today': T['美股标普医药']['pnl'], 'action_range_pct': [0, 0], 'amount': 0,
     'rationale': (f'{T["美股标普医药"]["pnl"]:+,.2f} 元（{T["美股标普医药"]["day_pct"]:+.3f}%）＝ US 10/22 段真实核销'
                   f'（`000369` +1.531% / `016280` +1.520%，IYH 10/22 **+1.33%**）→ '
                   f'**传导系数 1.151 / 1.143，全部越过 0.90 上界**；'
                   '**与 10/22 下跌段实测 0.47 合并 → 系数呈「上涨段 ≈1.15 / 下跌段 ≈0.47」的方向不对称**，'
                   '**单一区间 0.45~0.90 两头都不覆盖 → 预告模型必须按涨跌方向分档**（本轮第 6 例越界，第 1 例「上涨段上越界」）；'
                   '结构上仍为「QDII T+2 确认、T+3 到账」的净值盲区腿，**不因单日核销转正而加仓**；'
                   'US 10/23 段（北京 10/23 21:30 开盘）本档未开盘 → **只登记、不给数值**'),
     'gates': ['qdii_transmission_coef: asymmetric_confirmed (up 1.15 / down 0.47)',
               'us_1023: not_closed (Beijing 21:30)']},

    {'track': '恒生科技', 'weight_pct': W['恒生科技'], 'mv': T['恒生科技']['mv'],
     'pnl_today': T['恒生科技']['pnl'], 'action_range_pct': [0, 0], 'amount': -CUT3,
     'rationale': (f'{T["恒生科技"]["pnl"]:+,.2f} 元（{T["恒生科技"]["day_pct"]:+.3f}%）—— **名义正收益但显著弱于指数**：'
                   f'HSTECH **+2.05%** 报 {HS["close"]:,.2f}，而腿内 `164906` 双账户（8,848.49 元）'
                   f'的 **10/22 净值 −3.24% 于本档释放，拖累 {lof_164906:+,.2f} 元**，其余 4 券合计 {hk_pure:+,.2f} 元'
                   f'（`012348` +2.02% / `513180` +2.53% / `513050` +2.04%）→ **腿收益 74% 被 LOF 迟滞净值抵消**；'
                   f'**纪律：3,950 线 10/22 收盘失守已建案、10/23 为执行日 → 本档记 cut3 = {CUT3:,.2f} 元**，'
                   f'累计 **{CUM:,.2f} 元（3 笔）**，恒科 {D["hk_after"]:,.2f} 元 / 现金 {D["cash_after"]:,.2f} 元；'
                   f'**3,800 收复（{H_3800:+.4f}%）属「破位解除」，不产生反向加仓**（纪律只单向）；'
                   f'**收盘 {HS["close"]:,.2f} 仍低于 3,950（{H_3950:+.4f}%）与 4,000（{H_4000:+.4f}%）→ 下一参考位 3,700（{H_3700:+.4f}%）**；'
                   f'**南向资金连续第 8 日净卖出 −16.70 亿港元 → 本日 +2.05% 非南向驱动**（外资/本地盘 + 机器人链）'),
     'gates': ['hstech_4000: awaiting_user_confirmation (3rd day)',
               'hstech_3950: executed_this_session (cut3 1,858.66)',
               'hstech_3800: break_lifted_no_reverse_buy',
               'southbound: -16.70 亿港元 net sell (8th consecutive day)']},

    {'track': '现金', 'weight_pct': W['现金'], 'mv': T['现金']['mv'],
     'pnl_today': T['现金']['pnl'], 'action_range_pct': [0, 0], 'amount': 0,
     'rationale': (f'无交易；**纪律后权重 {D["weight_after"]["现金"]}%**（累计已减仓 {CUM:,.2f} 元虚拟计入）；'
                   f'**若 4,000 案经用户确认已执行，累计将升至 {CUM+PLAN_4000:,.2f} 元（4 笔）、'
                   f'现金权重 {round((T["现金"]["mv"]+CUM+PLAN_4000)/TOTAL*100,2)}%**；'
                   '现金 8 月末以来首次回到 9% 以上 → **弹药充足，但本档无任何「主动抄底」授权**（无 PE 分位触发线）'),
     'gates': [f'pending_confirm: 恒科 4,000 → {PLAN_4000:,.2f} 元（连续第 3 日）',
               'cash_ratio: 9.39% post-discipline']},
]

constraints = {
    'single_track_cap_pct': 40, 'max_single_trade_pct': 5, 'max_single_trade_used_pct': 0.5,
    'new_buy': 0, 'active_take_profit': 0, 'status': 'discipline_cut_executed_today',
    'med_exposure': {'mv': pc['med_exposure'], 'pct': pc['med_pct'],
                     'headroom_pct': round(40 - pc['med_pct'], 2),
                     'threshold_all_med_pct': pc['threshold_all_med'],
                     'threshold_a_sh_med_pct': pc['threshold_a_sh_med'],
                     'note': ('门槛 = 解方程 `A(1+r)/(B+A·r)=0.40`；+4.34% 意味着医药需单日普涨 4.34% 才被动突破上限 '
                              '→ 2.02pct 余量在中位偏厚区（§3.98）')},
    'pending_plan_stack': {
        'hstech_4000_awaiting_confirm': {'amount': PLAN_4000, 'pct': 0.5,
                                         'basis': '0.5% × 372,666.60 元（10/22 盘前建案，不重设分母）',
                                         'status': 'awaiting_user_confirmation',
                                         'days_pending': 3},
        'hstech_3950_executed': {'amount': CUT3, 'pct': 0.5,
                                 'basis': '0.5% × 371,732.03 元（10/22 盘后建案）',
                                 'status': 'executed_on_2026-10-23', 'user_confirmed': False,
                                 'execution_assumption': '推定执行（无回执通道），若实际未执行须下一档显式撤销并回退累计至 3,786.90 元'},
        'a_med_reverse': {'amount': PLAN_MED, 'pct': 0.0, 'basis': '作废（不计金额）',
                          'status': 'cancelled_line_deregistered',
                          'confidence': 'deregistered_0_of_4'},
        'max_combined_open_pct': round((PLAN_4000 + CUT3) / TOTAL * 100, 3),
        'note': ('本档实际执行 1 笔（cut3 {0:,.2f} 元 = 0.50% 组合）；仍待确认 1 笔（4,000 案 {1:,.2f} 元）；'
                 '医药反向线已注销（0 元）。合计潜在 {2:,.2f} 元 = {3:.2f}%，'
                 '**仍低于单次调仓 5% 上限**').format(CUT3, PLAN_4000, PLAN_4000 + CUT3,
                                                     round((PLAN_4000 + CUT3) / TOTAL * 100, 2)),
    },
}

risk = {
    'chain_cum_pct': rk['chain_cum_pct'], 'chain_days': rk['chain_days'],
    'sharpe': rk['sharpe'], 'sharpe_n': rk['sharpe_n'],
    'max_dd_pct': rk['max_dd_pct'], 'max_dd_peak': rk['max_dd_peak'], 'max_dd_trough': rk['max_dd_trough'],
    'w43_cum_pct': rk['w43_cum_pct'], 'w43_days': rk['w43_days'],
    'last5_cum_pct': rk['last5_cum_pct'], 'last10_cum_pct': rk['last10_cum_pct'],
    'rf_pct': rk['rf_pct'], 'rf_note': rk['rf_note'],
    'max_dd_new_low': False,
    'mdd_note': (f'MDD 读数 {rk["max_dd_pct"]}%（谷值 {rk["max_dd_trough"]}，峰值 {rk["max_dd_peak"]}）**未改善**：'
                 f'10/22 已刷新谷值（由 −7.10% 扩大至 −8.18%），本档 +1.4853% 只是「自谷值回升」，'
                 f'**不构成回撤修复**（需累计 +8.91% 才回峰值）'),
    'recovery_from_trough': round(pc['est_total_pct_raw'], 4),
}

tomorrow = [
    {'priority': 'P0', 'item': '未定价 4 只 6 行（16.55%）→ 必须以 **10/23 同日 `_fix`** 补齐',
     'rule': ('`000248` 双账户 {0:,.2f} 元 + `002708` 双账户 {1:,.2f} 元 + `000051` {2:,.2f} 元 + `002742` {3:,.2f} 元，'
              '名义合计 **{4:,.2f} 元（16.55%）**；10/23 净值 20:00 未出库（实测 akshare 最新仍为 10/22）→ '
              '**处理必须为「回填进 portfolio_close_20261023_fix.json 并重算 tracks[].pnl」，'
              '严禁把 10/23 的净值变动记入 10/26 的交易档**（跨日错配会使 W43 周收益失真）；'
              '守卫 |Σtracks.pnl − est_total_pnl| < 1.5').format(
                 u0248, u2708, unp['000051']['mv'], unp['002742']['mv'], pc['unpriced_total'])},
    {'priority': 'P0', 'item': '恒科 4,000 案执行状态确认（连续第 3 日）',
     'rule': ('须由用户明确「已执行 / 未执行」；若已执行 → 累计 {0:,.2f} 元（4 笔）、现金 +{1:,.2f} 元，'
              '下一档补登；**不得静默作废**（§3.110）').format(CUM + PLAN_4000, PLAN_4000)},
    {'priority': 'P0', 'item': 'cut3（{0:,.2f} 元）执行回执',
     'rule': ('本档为「推定执行」（无回执通道）。若用户实际未在 10/23 09:30-15:00 执行 → '
              '**下一档须撤销 cut3、累计回退至 3,786.90 元**，并在报告显式披露（§3.125c）').format(CUT3)},
    {'priority': 'P1', 'item': '恒科 3,700 线判定（下一参考位）',
     'rule': '收盘 {0:,.2f}，距 3,700 **{1:+.4f}%**、距 3,600 **{2:+.4f}%**；'
             '**若 10/26 收盘再破 3,700 → 按新线建案 0.5%（分母取 10/23 基准 {3:,.2f} 元），同日不重复扣减**'.format(
                 HS['close'], H_3700, H_3600, TOTAL)},
    {'priority': 'P1', 'item': 'QDII US 10/23 段预告模型改造',
     'rule': ('本档实测上涨段系数 1.151 / 1.143（IYH +1.33%），与下跌段 0.47 形成方向不对称 → '
              '**预告区间须改为「上涨段 1.05~1.20 / 下跌段 0.45~0.60」双档**，'
              '并用 {0:,.2f} 元名义本金重算区间；US 10/23 收盘成型于北京 10/24 04:00，10/26 盘前档可给区间').format(
                 pc['qdii_mv'])},
    {'priority': 'P1', 'item': '中证消费 12,100 逐日复核',
     'rule': '本档 {0:,.2f} → **{1:+.4f}%**（10/22 为 +1.2279%）→ 缓冲恢复至 1.46pct，回到安全区中位；'
             '若下一档 < 12,150 须重新建案'.format(CONSUME, C_12100)},
    {'priority': 'P2', 'item': '恒生科技双层拆解入模',
     'rule': ('本档 港联系总暴露 **{0:,.2f} 元 = {1:.2f}%**（纯恒科 {2:,.2f} / 中概 {3:,.2f} / 宽基恒生系 {4:,.2f}）；'
              '**仅报赛道 {5:.2f}% 会低估 {6:.2f}pct**（§3.108），周报须按三层披露').format(
                 pc['hk_total'], hk_total_pct, hks['pure'], hks['concept'], hks['broad'],
                 W['恒生科技'], hk_total_pct - W['恒生科技'])},
    {'priority': 'P2', 'item': '事件库窗口 n 复核（10/23 收盘档已随伪收盘覆盖回正）',
     'rule': '恒科 3/5/10 日 n = {0} / {1} / {2}；若下一档出现**下降** → 说明伪收盘行未被覆盖，须回查 `indices.csv`'.format(
                 es['window_n']['恒生科技']['3'], es['window_n']['恒生科技']['5'], es['window_n']['恒生科技']['10'])},
    {'priority': 'P2', 'item': '未闭环项（长期）',
     'rule': ('`indices.csv` code 口径（`sh000933` vs `000933`）／`fund_nav.csv` 重复键／两件不自洽 `_fix`'
              '（20260918 / 20260921）／`rf` 硬编码 1.68%（10Y 序列自 8/11 断更）／19 条 legacy 缺 `actual_date`／'
              '`gb_*` 的 `prev_date` 字段／`adjustments.json` 元数据滞后')},
    {'priority': 'P2', 'item': '用户决策（连续第 25 档）',
     'rule': '① 更新持仓快照（当前仍为静态快照，纪律减仓只能虚拟计入）② 且慢 `long-win-nav.csv` 口径统一（第 36 档）'
             '③ 且慢 REST 空 body（117 个交易日）→ 建议申请官方 MCP ④ DeepSeek 端点余额（402 连续第 20 日，情绪分已连续降级为规则表）'},
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
    'discipline_total': CUM,
    'note': ('赛道级动作全部 0 元（区间 [0%, 0%]）；本档唯一执行项 = 恒科 3,950 案 cut3 1,858.66 元（推定执行、待回执），'
             '累计纪律 5,645.56 元（3 笔）；4,000 案连续第 3 日待确认；医药反向线正式注销（0/4）。'
             '单次调仓上限 5%（本档用 0.5%）、单赛道上限 40%（当前 38.98%）均未触碰'),
}
json.dump(out, open(os.path.join(HIST, f'portfolio_strategy_close_{TODAYC}.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)

print('权重:', W)
print(f'组合 {pc["est_total_pnl"]:+,.2f} 元 / {pc["est_total_pct_raw"]:+.4f}% → {TOTAL:,.2f} 元')
print(f'恒科 {HS["close"]:,.2f}（{HS["pct"]:+.2f}%）4,000={H_4000}% 3,950={H_3950}% 3,800={H_3800}% 3,700={H_3700}%')
print(f'中证消费 {CONSUME:,.2f} vs 12,100 = {C_12100}%')
print(f'纪律累计 {CUM:,.2f}（3 笔）+ 待确认 {PLAN_4000:,.2f}；现金权重 {D["weight_after"]["现金"]}%')
print(f'风险：链路 {rk["chain_cum_pct"]}%/{rk["chain_days"]}日 夏普 {rk["sharpe"]}(n={rk["sharpe_n"]}) MDD {rk["max_dd_pct"]}% W43 {rk["w43_cum_pct"]}%/{rk["w43_days"]}日')
print(f'港联系总暴露 {hk_total_pct:.2f}%（纯恒科 {hks["pure"]:,.2f} / 中概 {hks["concept"]:,.2f} / 宽基 {hks["broad"]:,.2f}）')
print('明日待办', len(tomorrow), '项')
