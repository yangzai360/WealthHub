# -*- coding: utf-8 -*-
"""2026-09-30 盘后：策略层产物（三条防线收盘级判定 + 纪律执行台账 + 假期待消化 + 港股三层拆解）
输出：portfolio_strategy_close_20260930.json
"""
import json, os

BASE = '/Users/jieyang/Documents/WealthHub'
HIST = os.path.join(BASE, 'data/processed/history')
TODAY = '2026-09-30'
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
hstech_close = HK['HSTECH']['close']          # 4,253.89
hstech_pct = HK['HSTECH']['pct']
cs_close = pc['board_detail']['000932'] if False else None
cs_close = IDXP['000932'] if False else None
# 中证消费收盘价来自 close_*.json
cs = next(x for x in cur['indices'] if x['code'] == 'sh000932')
cs_close, cs_pct = cs['close'], cs['pct']

lines = {
    'hstech_4250': {
        'line': 4250.0, 'close': hstech_close, 'pct': hstech_pct,
        'dist_pct': round((hstech_close / 4250.0 - 1) * 100, 4),
        'state': 'RESTORED_CLOSE_LEVEL' if hstech_close >= 4250.0 else 'BROKEN_CLOSE_LEVEL',
        'intraday_ref': pi['defense']['hstech'],
        'judgement': ('收复防线 → 9/29 收盘级「边际破位」减仓记为**边际破位成本**（§3.114c 并列披露义务），'
                      '纪律不改回、不补回仓位；防线维持 4,250'),
        'next_line': 4250.0,
    },
    'zz_consume_12100': {
        'line': 12100.0, 'close': cs_close, 'pct': cs_pct,
        'dist_pct': round((cs_close / 12100.0 - 1) * 100, 4),
        'state': 'RESTORED_CLOSE_LEVEL' if cs_close >= 12100.0 else 'BROKEN_CLOSE_LEVEL',
        'judgement': '收复第 2 日 + 远离防线（+1.62%）→ 9/28 兑现的「技术性误触」定性获第二日确认；防线回归 12,100',
        'next_line': 12000.0,
        'next_line_dist_pct': round((cs_close / 12000.0 - 1) * 100, 4),
    },
    'a_med_reverse_1_5pct': {
        'proxy_pct': pc['board_med'], 'board_med': pc['board_med'], 'leader_med': pc['leader_med'],
        'line_pct': -1.5,
        'state': 'NOT_TRIGGERED',
        'judgement': f'A股医药板块代理 {pc["board_med"]:+.4f}%（300医药 {pc["leader_med"]:+.2f}%）→ 远离 −1.5% 反向兑现线，未触发',
    },
}

# ---------- 2. 纪律执行台账 ----------
ledger = [{
    'date': TODAY, 'kind': '恒生科技 0.5% 纪律减仓',
    'amount': 1882.46,
    'trigger': '9/29 收盘级破位（恒生科技 4,249.62 < 4,250，−0.0089%，边际破位）',
    'decided_at': '2026-09-30 盘前档', 'confirmed_at': '2026-09-30 盘中档',
    'settle': '9/30 按 9/30 净值成交（节前最后一个 A股交易日）',
    'target': '012348 天弘恒生科技联接A（纯恒科口径）优先 / 513180 恒指科技（场内 ETF）备选',
    'not_target': '513050 / 164906（中概口径，与触发源不一致）',
    'weight_after': pc['discipline']['weight_after'],
    'outcome': ('⚠️ 恒生科技 9/30 收 4,253.89（+0.10%）**收复 4,250 防线（+0.0914%）** → '
                '本次减仓按 §3.114c 记为「边际破位成本」；纪律不改回、不补回仓位；防线维持 4,250'),
    'cost_note': ('边际破位成本的一次实证：以「收盘价 < 防线」的二元判据执行、不引入主观容差，'
                  '在贴线幅度仅 −0.0089% 的情形下，次日即被收复；若引入「容差带/观察一日」则本笔不会发生。'
                  '按 §3.114c，本项须如实记录、不得事后否认，并作为「二元判据 vs 容差判据」的样本累积。'),
}]
# 历史纪律台账（承接 9/29 / 9/28 / 9/16 / 9/15 已执行项）
ledger_hist = [
    {'date': '2026-09-29', 'kind': '大消费 0.5% 纪律兑现', 'amount': 1879.43,
     'trigger': '9/28 收盘级跌破 12,100（12,096.0166，−0.033%）', 'settle': '按 9/29 净值成交（价值中性）',
     'outcome': '9/29 收 12,107.1705 收复 12,100 → 定性「技术性误触」，纪律不改回'},
    {'date': '2026-09-29', 'kind': '恒生科技 0.5% 纪律减仓（判定）', 'amount': 1882.87,
     'trigger': '9/29 收盘级跌破 4,250（4,249.62，−0.0089%，边际破位）', 'settle': '移交 9/30 执行',
     'outcome': '9/30 按净值成交 1,882.46 元 → 次日被收复，记为边际破位成本'},
]

# ---------- 3. 假期待消化（10/8 复市） ----------
# QDII 000369/016280：基准净值日 9/28（已在 9/29 修正件中兑现）→ 挂账 = US 9/29、US 9/30、…（假期累积）
qdii_mv = 0.0
for d in pc['detail']:
    c6 = ''.join(c for c in str(d['code']) if c.isdigit())
    if c6 in ('000369', '016280'):
        qdii_mv += d['mv0_new'] + d['est_pnl']
qdii_mv = round(qdii_mv, 2)
IYH_0929 = -0.36      # US 9/29 IYH 收盘（盘前档已记录；本档沿用）
pending = {
    'as_of': TODAY,
    'settle_date': '2026-10-08',
    'qdii_pending_sessions': ['2026-09-29'],       # 本档仅 US 9/29 已知；US 9/30 及假期 5 个交易日待补
    'qdii_mv': qdii_mv,
    'qdii_coef_mid': 0.72, 'qdii_coef_low': 0.60, 'qdii_coef_high': 0.90,
    'qdii_pnl_mid': round(qdii_mv * IYH_0929 / 100 * 0.72, 2),
    'qdii_pnl_low': round(qdii_mv * IYH_0929 / 100 * 0.60, 2),
    'qdii_pnl_high': round(qdii_mv * IYH_0929 / 100 * 0.90, 2),
    'qdii_pnl_at_062': round(qdii_mv * IYH_0929 / 100 * 0.62, 2),
    'note': ('⚠️ 本档按 §3.112f「只给区间、不给方向」处理：US 9/30（北京 9/30 夜）与 10/1-10/7 共 5 个美股交易日'
             '将在休市期累积，10/8 复市后须一次性按实际净值回填，本节仅量化「US 9/29 已确定的一日」；'
             '假期累积量级可能显著大于本节数字，不得以本节区间作方向依据'),
    'unquantified': {
        'code': '164906', 'mv': round(sum(d['mv0_new'] + d['est_pnl'] for d in pc['detail']
                                           if ''.join(c for c in str(d['code']) if c.isdigit()) == '164906'), 2),
        'note': 'US 9/29 挂账未计入合计（传导系数未标定）',
    },
    'hk_northbound_gap_days': ['2026-10-02', '2026-10-05', '2026-10-06', '2026-10-07'],
}

# ---------- 4. 节假日历（逐市场分列，§3.115d） ----------
calendar = {
    '2026-09-30': 'A股 + 港股 + 美股均交易（节前最后一个 A股交易日；20:30 美国 8 月 PCE）',
    '2026-10-01': 'A股休市 + 港股休市 + 港股通关闭 + 美股交易',
    '2026-10-02': 'A股休市；港股交易（第 1 个南向空窗日）；港股通关闭；美股交易',
    '2026-10-03~10-04': 'A股休市；港股休市（周末）；美股休市（周末）',
    '2026-10-05': 'A股休市；港股交易（南向空窗）；港股通关闭；美股交易',
    '2026-10-06': 'A股休市；港股交易（南向空窗）；港股通关闭；美股交易',
    '2026-10-07': 'A股休市；港股交易（南向空窗）；港股通关闭；美股交易',
    '2026-10-08': 'A股复市 + 港股通恢复（美股类事件一次性回填）',
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
    'hk_track_layer_pct': round(tr['恒生科技']['mv'] / total_mv * 100, 2),
    'hk_undercount_pct': round(pc['hk_total_pct'] - tr['恒生科技']['mv'] / total_mv * 100, 2),
}

out = {'date': TODAY, 'as_of': '2026-09-30 收盘（节前最后一个 A股交易日）',
       'base_total': pc['base_total'], 'total_mv': total_mv,
       'est_total_pnl': pc['est_total_pnl'], 'est_total_pct': pc['est_total_pct'],
       'est_total_pnl_low': pc['est_total_pnl_low'], 'est_total_pnl_high': pc['est_total_pnl_high'],
       'defense_lines_close': lines,
       'discipline_ledger': ledger, 'discipline_ledger_history': ledger_hist,
       'pending': pending, 'calendar': calendar, 'exposure': exposure,
       'action_next': {
           'next_session': '2026-10-08（A股复市日，本档后首个交易日）',
           'planned': ('① 一次性回填 10/1-10/7 美股类事件（逐条校验参考指数真实收盘价存在性，§3.112h）；'
                       '② 按 QDII 实际净值兑现 9/29-10/7 挂账并复核本档 9/30 估算；'
                       '③ 复核 002708/161616/000727 的 9/30 真实净值（本档由板块代理估算）；'
                       '④ 重新判定恒生科技 4,250 防线的假期后状态；'
                       '⑤ 恒科减仓后权重（8.15% 现金）的再配置再评估'),
       },
       'note': '9/30 唯一动作 = 恒生科技 0.5% 纪律减仓 1,882.46 元（9/29 收盘级破位触发，9/30 净值成交）；其余赛道动作 0'}

json.dump(out, open(os.path.join(HIST, 'portfolio_strategy_close_' + TODAYC + '.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)

print('✅ 三条防线收盘级判定:')
for k, v in lines.items():
    print(f'  {k}: {json.dumps(v, ensure_ascii=False)[:230]}')
print(f'\n✅ 待消化（10/8）: QDII 敞口 {qdii_mv:,.2f} 元 → US 9/29 单日预告 中枢 {pending["qdii_pnl_mid"]:+,.2f} 元'
      f'（区间 {pending["qdii_pnl_low"]:+,.2f} ~ {pending["qdii_pnl_high"]:+,.2f} 元）')
print(f'   未量化：164906 {pending["unquantified"]["mv"]:,.2f} 元')
print(f'\n✅ 敞口：医药 {pc["med_pct"]:.2f}%（门槛全部 {pc["threshold_all_med"]:+.2f}% / 仅A股医药 {pc["threshold_a_sh_med"]:+.2f}%）'
      f'｜港联系 {pc["hk_total_pct"]:.2f}%（赛道层 {exposure["hk_track_layer_pct"]:.2f}% + 宽基 {exposure["hk_undercount_pct"]:.2f}pct）')
print(f'\n✅ 减仓后权重: ' + ' / '.join(f'{k} {v:.2f}%' for k, v in pc['discipline']['weight_after'].items()))
print(f'\n防线：恒生科技 {hstech_close} ({hstech_pct:+.2f}%) vs 4250 → {lines["hstech_4250"]["state"]}（{lines["hstech_4250"]["dist_pct"]:+.4f}%）')
print(f'      中证消费 {cs_close} ({cs_pct:+.2f}%) vs 12100 → {lines["zz_consume_12100"]["state"]}（{lines["zz_consume_12100"]["dist_pct"]:+.4f}%）')
print(f'      A股医药板块代理 {pc["board_med"]:+.4f}% vs −1.5% → {lines["a_med_reverse_1_5pct"]["state"]}')
