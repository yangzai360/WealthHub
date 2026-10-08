# -*- coding: utf-8 -*-
"""2026-10-08 盘后：策略层产物（三条防线收盘级判定 + 纪律执行台账 + 待消化收口 + 港股三层拆解）
输出：portfolio_strategy_close_20261008.json
"""
import json, os

BASE = '/Users/jieyang/Documents/WealthHub'
HIST = os.path.join(BASE, 'data/processed/history')
TODAY = '2026-10-08'
TODAYC = TODAY.replace('-', '')

pc = json.load(open(os.path.join(HIST, 'portfolio_close_' + TODAYC + '.json'), encoding='utf-8'))
po = json.load(open(os.path.join(HIST, 'portfolio_preopen_' + TODAYC + '.json'), encoding='utf-8'))
pi = json.load(open(os.path.join(HIST, 'portfolio_intraday_' + TODAYC + '.json'), encoding='utf-8'))
cur = json.load(open(os.path.join(HIST, 'close_' + TODAYC + '.json'), encoding='utf-8'))

total_mv = pc['total_mv']
tr = pc['tracks']
IDXP = pc['idx']
HK = pc['hk_mkt']

# ---------- 1. 三条防线的收盘级判定 ----------
hstech = HK['HSTECH']
cs = next(x for x in cur['indices'] if x['code'] == 'sh000932')
cs_close, cs_pct = cs['close'], cs['pct']
medi = next(x for x in cur['boards'] if x['code'] == 'sh000933')

lines = {
    'hstech_4250': {
        'line': 4250.0, 'close': hstech['close'], 'pct': hstech['pct'],
        'dist_pct': round((hstech['close'] / 4250.0 - 1) * 100, 4),
        'state': 'BROKEN_CLOSE_LEVEL_DEEPENED',
        'intraday_ref': pi['defense']['hstech'],
        'break_trend': {'2026-10-02': -2.1661, '2026-10-05': -1.5605, '2026-10-06': -0.6342,
                        '2026-10-07': -1.3061, '2026-10-08': round((hstech['close'] / 4250.0 - 1) * 100, 4)},
        'judgement': ('破位幅度由 10/7 的 −1.3061% **扩大至 −4.1558%**（10/8 单日 −2.89%），'
                      '长假「破位幅度连续收窄」的反弹假设被彻底否证；'
                      '第 2 次 0.5% 减仓已于本档按 10/8 净值成交（累计 3,786.90 元）；'
                      '按 §3.114c「同日防线只触发一次」→ 本档**不新增纪律动作**；防线维持 4,250'),
        'next_line': 4000.0,
        'next_line_dist_pct': round((hstech['close'] / 4000.0 - 1) * 100, 4),
    },
    'zz_consume_12100': {
        'line': 12100.0, 'close': cs_close, 'pct': cs_pct,
        'dist_pct': round((cs_close / 12100.0 - 1) * 100, 4),
        'state': 'ABOVE_CLOSE_LEVEL',
        'judgement': (f'中证消费 10/8 收 {cs_close:,.4f}（{cs_pct:+.2f}%），距 12,100 下沿 '
                      f'{round((cs_close/12100.0-1)*100,4):+.4f}% → 长假后首个交易日即站稳，无触发'),
        'next_line': 12000.0,
        'next_line_dist_pct': round((cs_close / 12000.0 - 1) * 100, 4),
    },
    'a_med_reverse_1_5pct': {
        'proxy_pct': pc['board_med'], 'board_med': pc['board_med'], 'leader_med': pc['leader_med'],
        'lag_med': pc['lag_med'], 'single_day_000933': medi['pct'],
        'line_pct': -1.5, 'dist_pct': round(pc['board_med'] - (-1.5), 4),
        'state': 'TRIGGERED_CLOSE_LEVEL',
        'intraday_state': 'TRIGGERED（13:45 代理 −2.4025%，portfolio_intraday_20261008.json defense.med_reverse_line = true）',
        'state_continuity': '盘中 → 收盘**同向且更深**（−2.4025% → −2.6475%），状态连续、非推翻',
        'judgement': (f'A股医药板块代理 {pc["board_med"]:+.4f}%（300医药 {pc["leader_med"]:+.2f}% / '
                      f'中证医药 {medi["pct"]:+.2f}% / 中证医疗 {pc["lag_med"]:+.2f}%）≤ −1.5% → '
                      f'**收盘级触发**（距线 {round(pc["board_med"] + 1.5, 4):+.4f}pct）；'
                      f'⚠️ §3.71 语义澄清：本条为「利好兑现后的**回调观察线**」，用于判断「定价是否已兑现」，'
                      f'**不是止损线** → 处置 = 不执行主动减配（active_take_profit = 0 / new_buy = 0）；'
                      f'**闭环要求：若 10/9 形成「连续 2 日回调」，须在 10/9 盘前档建立被动减配预案（候选 012323 / 001180）**；'
                      f'结构为「大市值相对抗跌 + 中小市值/主题跌幅更深」（300医药 −1.86% 优于 中证医药 −2.55% 优于 中证医疗 −2.73%）'),
    },
}

# ---------- 2. 纪律执行台账 ----------
ledger = [{
    'date': TODAY, 'kind': '恒生科技 0.5% 纪律减仓（第 2 次）',
    'amount': 1904.44,
    'trigger': '10/2 收盘级破位（恒生科技 4,157.94 < 4,250，−2.1661%，非边际破位）',
    'decided_at': '2026-10-02 盘后档（收盘级锁定）', 'execute_at': TODAY,
    'settle': '本档按 10/8 净值成交（A股 + 港股通复市首日；价值中性，P&L 口径不变）',
    'target': '012348 天弘恒生科技联接A（纯恒科口径）优先 / 513180 恒指科技（场内 ETF）备选',
    'not_target': '513050 / 164906（中概口径，与触发源不一致）',
    'cumulative_amount': 3786.90,
    'weight_after': pc['discipline']['weight_after'],
    'outcome': ('执行日恒生科技收 4,073.38（−2.89%），距 4,250 为 **−4.1558%** → 破位幅度较判定日（−2.1661%）'
                '进一步扩大，第 2 次减仓属「**有效减仓**」（与 9/30 第 1 次的「边际破位成本」性质相反）；'
                '纪律执行日不同、结果不同，两类样本须分别累积（§3.114c / §3.117b）'),
    'cost_note': ('对照样本：第 1 次（9/29 判定 −0.0089% 边际破位 → 9/30 按净值 1,882.46 元成交）'
                  '成交次日即被收复 4,253.89，属边际破位成本；第 2 次（10/2 判定 −2.1661% 非边际破位）'
                  '执行日进一步下探至 −4.1558%，属有效减仓。同一防线两次触发、结果相反 → '
                  '「二元收盘判据」在非边际区间有效、在贴线区间代价高（样本累积项）。'),
}]
ledger_hist = [
    {'date': '2026-09-29', 'kind': '大消费 0.5% 纪律兑现', 'amount': 1879.43,
     'trigger': '9/28 收盘级跌破 12,100（12,096.0166，−0.033%）', 'settle': '按 9/29 净值成交（价值中性）',
     'outcome': '9/29 收 12,107.1705 收复 12,100 → 定性「技术性误触」；10/8 复市收 12,256.813（+1.296% 距下沿）→ 结论延续'},
    {'date': '2026-09-30', 'kind': '恒生科技 0.5% 纪律减仓（第 1 次）', 'amount': 1882.46,
     'trigger': '9/29 收盘级破位（4,249.62，−0.0089%，边际破位）', 'settle': '按 9/30 净值成交',
     'outcome': '9/30 收 4,253.89 收复防线 → 记为「边际破位成本」；10/8 复市收 4,073.38（−4.1558% 距防线）→ 事后看该笔减仓方向正确但当期被判为成本'},
]

# ---------- 3. 待消化收口 + QDII 挂账 ----------
pending = {
    'as_of': TODAY,
    'hk_leg_pending': pc['pending_release'],
    'qdii_pending': pc['qdii_pending'],
    'pending_total': {
        'hk_leg': '已收口（10/8 由场外港股联接净值一次性兑现）',
        'qdii_leg_range': [pc['qdii_pending']['remaining']['low'],
                           pc['qdii_pending']['remaining']['high']],
        'qdii_leg_note': '余 US 10/1~10/7（5 个可观测交易日）+ US 10/8（未知，北京 10/9 04:00 成型）',
    },
    'note': ('§3.112f：跨档只给区间、禁止中枢点值。10/8 盘前档挂账区间 −1,090.70 元 ~ −816.41 元'
             '（含 component_a 的 US 9/29 段）中，US 9/29 + 9/30 两段已按实际净值回填 −942.55 元；'
             '余下 US 10/1~10/7 复算为 −195.08 元 ~ −130.05 元（IYH 复合 −0.3631%、系数带 0.6~0.9），'
             '叠加 US 10/8 未知段。⚠️ 实际回填（−942.55 元 / 两日）显著劣于前档估算（约 −755 元 / 两日）→ '
             '§3.118a「实测隐含系数 1.25~1.29 远高于标定 0.72」第 3 次被证实，'
             '**系数未重估前基于该系数的一切仓位决策无效**'),
}

# ---------- 4. 节假日历（逐市场分列，§3.115d） ----------
calendar = {
    '2026-10-01': 'A股休市 + 港股休市 + 港股通关闭 + 美股交易',
    '2026-10-02': 'A股休市；港股交易（第 1 个南向空窗日，恒科 4,157.94 / −2.26% **首次收盘级破 4,250**）；美股交易',
    '2026-10-05': 'A股休市；港股交易（南向空窗）；美股交易',
    '2026-10-06': 'A股休市；港股交易（南向空窗）；美股交易',
    '2026-10-07': 'A股休市；港股交易（南向空窗，长假最后一个港股交易日）；美股交易',
    '2026-10-08': 'A股复市（上证 3,811.90 / −0.79%）+ 港股通/南向恢复 + 恒科减仓执行日 + 长假累积净值一次性对账',
    '2026-10-09': 'A股 + 港股正常交易日（本档后首个交易日；09:30 公布 9 月金融数据）',
}

# ---------- 5. 敞口与门槛 ----------
exposure = {
    'tracks': {k: {'mv': v['mv'], 'pct': v['pct_of_total'], 'pnl': v['pnl'], 'day_pct': v['day_pct']}
               for k, v in tr.items()},
    'weight_after_discipline': pc['discipline']['weight_after'],
    'med_exposure': pc['med_exposure'], 'med_pct': pc['med_pct'],
    'threshold_all_med': pc['threshold_all_med'], 'threshold_a_sh_med': pc['threshold_a_sh_med'],
    'hk_split': pc['hk_split'], 'hk_split_pnl': pc['hk_split_pnl'],
    'hk_total': pc['hk_total'], 'hk_total_pct': pc['hk_total_pct'],
    'hk_track_layer_pct': pc['track_layer_hk_pct'],
    'hk_undercount_pct': round(pc['hk_total_pct'] - pc['track_layer_hk_pct'], 2),
    'hk_split_rows': pc['hk_split_rows'],
}

# ---------- 6. 涨跌归因 ----------
driver = {
    'top_drag': [
        {'name': '大摩健康产业混合A', 'track': 'A股医药', 'pct': -3.193, 'pnl': -662.07},
        {'name': '华宝中证医疗联接C', 'track': 'A股医药', 'pct': -2.613, 'pnl': -546.66},
        {'name': '融通医疗保健行业混合A/B', 'track': 'A股医药', 'pct': -3.079, 'pnl': -529.76},
        {'name': '广联达', 'track': '其他/宽基', 'pct': -1.171, 'pnl': -448.02},
        {'name': '天弘恒生科技联接A', 'track': '恒生科技', 'pct': -4.052, 'pnl': -436.84},
        {'name': '恒生ETF联接A', 'track': '其他/宽基', 'pct': -3.170, 'pnl': -374.69},
    ],
    'attribution': ('① **A股医药**为本档最大拖累（−2,576.26 元，占组合总亏损 40.1%）：复市首日板块补跌，'
                    '中证医药 −2.55% / 中证医疗 −2.73% / 300医药 −1.86%，主动药基跌幅更深（−2.40% ~ −3.19%）；'
                    '② **其他/宽基**（−1,379.19 元）中港股系联接（000071 −3.17%）与个股（广联达 −1.17%）同步走弱；'
                    '③ **美股标普医药**（−942.55 元）为 QDII 挂账回填所致，非 10/8 美股行情；'
                    '④ **恒生科技**（−773.68 元）受港股补跌拖累（012348 −4.05% 含跨长假累积）；'
                    '⑤ **大消费**相对抗跌（−750.05 元 / −0.99%），中证消费仅 −0.32%；'
                    '⑥ **现金** 0 元（账面冻结项，不构成方向判断）'),
}

out = {'date': TODAY, 'as_of': '2026-10-08 收盘（A股 长假后复市首日 + 港股正常交易日）',
       'session_type': pc['session_type'],
       'base_total': pc['base_total'], 'total_mv': total_mv,
       'est_total_pnl': pc['est_total_pnl'], 'est_total_pct': pc['est_total_pct'],
       'est_total_pnl_low': pc['est_total_pnl_low'], 'est_total_pnl_high': pc['est_total_pnl_high'],
       'defense_lines_close': lines,
       'discipline_ledger': ledger, 'discipline_ledger_history': ledger_hist,
       'pending': pending, 'calendar': calendar, 'exposure': exposure, 'driver': driver,
       'action_next': {
           'next_session': '2026-10-09（正常交易日）',
           'planned': ('① 复核 000369/016280（QDII，T+2 迟滞）与 164906 的 10/8 净值是否出库 → 出库则回填挂账（§3.105）；'
                       '② 重估 QDII「指数→净值」传导系数（≥4 券位 × ≥5 交易日样本，§3.118a / §3.133a）；'
                       '③ 复核恒生科技 4,000 新防线（本档距 −1.8345%）与 4,250 破位后的减仓累计效果；'
                       '④ 复核中证消费 12,100 下沿与医药 40% 上限（本档 38.96%，门槛 +4.44%）；'
                       '⑤ 09:30 公布 9 月金融数据（M2/社融）→ 登记事件、不预判；'
                       '⑥ A股医药「复市补跌」是否延续（本档主动药基 −2.40~−3.19% vs 板块 −2.65%）须由次日价格证伪'),
       },
       'note': ('10/8 唯一动作 = 恒生科技 0.5% 纪律减仓 1,904.44 元（10/2 收盘级破位判定、本档成交，累计 3,786.90 元）；'
                '其余赛道动作 0。待消化：长假港股腿窗口已收口、QDII 腿余 −195.08 ~ −130.05 元')}

json.dump(out, open(os.path.join(HIST, 'portfolio_strategy_close_' + TODAYC + '.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)

print('✅ 三条防线收盘级判定:')
for k, v in lines.items():
    print(f'  {k}: {json.dumps(v, ensure_ascii=False)[:260]}')
print(f'\n✅ 纪律台账: 第 2 次恒科减仓 {ledger[0]["amount"]:,.2f} 元（累计 {ledger[0]["cumulative_amount"]:,.2f} 元）')
print(f'\n✅ 待消化: 港股腿已收口；QDII 腿余 {pending["pending_total"]["qdii_leg_range"][0]:+,.2f} ~ '
      f'{pending["pending_total"]["qdii_leg_range"][1]:+,.2f} 元；本档回填 {pc["qdii_pending"]["booked_this_session"]["amount"]:+,.2f} 元')
print(f'\n✅ 敞口：医药 {pc["med_pct"]:.2f}%（门槛全部 {pc["threshold_all_med"]:+.2f}% / 仅A股医药 {pc["threshold_a_sh_med"]:+.2f}%）'
      f'｜港联系 {pc["hk_total_pct"]:.2f}%（赛道层 {pc["track_layer_hk_pct"]:.2f}% + 宽基 {exposure["hk_undercount_pct"]:.2f}pct）')
print(f'\n✅ 减仓后权重: ' + ' / '.join(f'{k} {v:.2f}%' for k, v in pc['discipline']['weight_after'].items()))
print(f'\n防线：恒生科技 {hstech["close"]} ({hstech["pct"]:+.2f}%) vs 4250 → {lines["hstech_4250"]["state"]}（{lines["hstech_4250"]["dist_pct"]:+.4f}%）')
print(f'      中证消费 {cs_close} ({cs_pct:+.2f}%) vs 12100 → {lines["zz_consume_12100"]["state"]}（{lines["zz_consume_12100"]["dist_pct"]:+.4f}%）')
print(f'      A股医药板块代理 {pc["board_med"]:+.4f}% vs +1.5% → {lines["a_med_reverse_1_5pct"]["state"]}')
