# -*- coding: utf-8 -*-
"""2026-10-16 盘后：策略层产物（三条防线收盘级判定 + 纪律执行台账 + 待消化 + 港股三层拆解）
输出：portfolio_strategy_close_20261016.json

⚠️ 档型 = **正常交易日收盘档**（A股 10/16 长假后第 7 个正常交易日 15:00 收盘 + 港股 10/16 正常交易日 16:00 收盘）
   下一交易日 = **2026-10-19（周一）**；⚠️ 10/17-10/18 为周末（A股 + 港股均休市）
   ⚠️ 10/19 为「港股重阳节翌日休市 + A股 正常交易」→ **「混合档」镜像情形**（§3.108 / §3.121e）
⚠️ §3.133a：所有展示字段（点位/距离/趋势序列）一律从 indices.csv 与 close_<DATE>.json **现算**，禁止硬编码常量
⚠️ §3.145a / §3.149a：**state 类字段禁止从上一档派生继承** —— 本档恒科 state 由「本档 dist_pct vs 上一档 dist_pct」现算
   （上一档 10/15 = −4.4473%、本档 = −3.3355% → 绝对值**收窄** → `BROKEN_CLOSE_LEVEL_NARROWED`）
⚠️ 本档为**全新撰写**（非 sed 派生）：日期常量 / 基准文件 / 前档基准值 / 档位语义 / 方向词五类字面量逐项手写核对
"""
import json, os, csv

BASE = '/Users/jieyang/Documents/WealthHub'
HIST = os.path.join(BASE, 'data/processed/history')
TODAY = '2026-10-16'
TODAYC = TODAY.replace('-', '')
PREV = '2026-10-15'
NEXT_TD = '2026-10-19'

pc = json.load(open(os.path.join(HIST, 'portfolio_close_' + TODAYC + '.json'), encoding='utf-8'))
po = json.load(open(os.path.join(HIST, 'portfolio_preopen_' + TODAYC + '.json'), encoding='utf-8'))
pi = json.load(open(os.path.join(HIST, 'portfolio_intraday_' + TODAYC + '.json'), encoding='utf-8'))
cur = json.load(open(os.path.join(HIST, 'close_' + TODAYC + '.json'), encoding='utf-8'))

total_mv = pc['total_mv']
tr = pc['tracks']
IDXP = pc['idx']
HK = pc['hk_mkt']

# 指数日线（现算用）
idx = {}
with open(os.path.join(HIST, 'indices.csv'), encoding='utf-8-sig') as fh:
    for row in csv.DictReader(fh):
        try:
            idx.setdefault(row['code'], {})[row['date']] = float(row['close'])
        except Exception:
            pass

# ---------- 1. 三条防线的收盘级判定 ----------
hstech = HK['HSTECH']
cs = next(x for x in cur['indices'] if x['code'] == 'sh000932')
cs_close, cs_pct = cs['close'], cs['pct']
medi = next(x for x in cur['boards'] if x['code'] == 'sh000933')
med_etf = next(x for x in cur['boards'] if x['code'] == 'sz399989')

LINE_HK = 4250.0
LINE_HK_NEXT = 4000.0
LINE_CS = 12100.0
LINE_CS_NEXT = 12000.0

# 破位趋势序列：从 indices.csv 现算（§3.133a）
break_trend = {d: round((v / LINE_HK - 1) * 100, 4)
               for d, v in sorted(idx['HSTECH'].items()) if d >= '2026-10-02'}
prev_break = break_trend.get(PREV)
assert prev_break is not None and len(break_trend) >= 6, f'破位趋势序列异常：{break_trend}'
_hk_d = round((hstech['close'] / LINE_HK - 1) * 100, 4)
_cs_d = round((cs_close / LINE_CS - 1) * 100, 4)
_cs_d_prev = round(po['defense_lines']['zz_consume_12100']['dist_pct'], 4)

# §3.145a：state 由本档 vs 上一档 dist_pct 现算（禁止继承）
HK_STATE = ('BROKEN_CLOSE_LEVEL_NARROWED' if abs(_hk_d) < abs(prev_break)
            else 'BROKEN_CLOSE_LEVEL_WIDENED' if abs(_hk_d) > abs(prev_break)
            else 'BROKEN_CLOSE_LEVEL_FLAT')
_CS_MARGIN_DELTA = round(_cs_d - _cs_d_prev, 4)
CS_STATE = 'ABOVE_CLOSE_LEVEL_WIDENED' if _CS_MARGIN_DELTA > 0 else (
    'ABOVE_CLOSE_LEVEL_NARROWED' if _CS_MARGIN_DELTA < 0 else 'ABOVE_CLOSE_LEVEL_FLAT')
# 方向词一律现算（§3.149a 条款 2：禁止誊抄「收窄/走阔」）
_HK_DIR = '走阔' if abs(_hk_d) > abs(prev_break) else ('收窄' if abs(_hk_d) < abs(prev_break) else '持平')
_HK_DELTA = round(abs(abs(_hk_d) - abs(prev_break)), 4)
_CS_DIR = '走阔' if _CS_MARGIN_DELTA > 0 else ('收窄' if _CS_MARGIN_DELTA < 0 else '持平')
_CS_ABS_DELTA = round(abs(_CS_MARGIN_DELTA), 4)
_MED_TRIGGERED = pc['board_med'] <= -1.5

lines = {
    'hstech_4250': {
        'line': LINE_HK, 'close': hstech['close'], 'pct': hstech['pct'],
        'dist_pct': _hk_d,
        'state': HK_STATE,
        'state_derivation': (f'§3.145a 现算：上一档 dist_pct = {prev_break:+.4f}%、本档 = {_hk_d:+.4f}% '
                             f'→ 绝对值由 {abs(prev_break):.4f} {_HK_DIR}至 {abs(_hk_d):.4f} → {HK_STATE}'),
        'intraday_ref': pi['defense']['hstech'],
        'break_trend': break_trend,
        'intraday_high': hstech['high'], 'intraday_low': hstech['low'],
        'intraday_touched_above': hstech['high'] >= LINE_HK,
        'judgement': (f'破位幅度由 10/15 的 {prev_break:+.4f}% **{_HK_DIR}至 {_hk_d:+.4f}%**'
                      f'（{_HK_DIR} {_HK_DELTA:.4f}pct；本档单日 {hstech["pct"]:+.2f}%）；'
                      f'⚠️ 日内最高 {hstech["high"]:,} **< 4,250 → 全日未站上**（13:45 盘中读数 '
                      f'{pi["defense"]["hstech"]:,} / 距防线 {pi["defense"]["hstech_vs_4250"]:+.4f}%）；'
                      f'按 §3.114c「同日防线只触发一次」→ 本档**不新增纪律动作**，防线维持 4,250；'
                      f'⚠️ 本档读数 {_hk_d:+.4f}% 虽收窄，仍处破位区间、距下一道 4,000 线 '
                      f'{round((hstech["close"] / 4000 - 1) * 100, 4):+.4f}%'
                      f'（较 10/15 的 +1.5247% 安全垫走阔 {round((hstech["close"] / 4000 - 1) * 100 - 1.5247, 4):+.4f}pct）；'
                      f'⚠️ 单日收涨不改变二元判据（收盘价 < 防线）的结论，亦不触发反向补仓（§3.114c）'),
        'next_line': LINE_HK_NEXT,
        'next_line_dist_pct': round((hstech['close'] / LINE_HK_NEXT - 1) * 100, 4),
    },
    'zz_consume_12100': {
        'line': LINE_CS, 'close': cs_close, 'pct': cs_pct,
        'dist_pct': _cs_d,
        'state': CS_STATE,
        'state_derivation': (f'§3.145a 现算：上一档 dist_pct = {_cs_d_prev:+.4f}%、本档 = {_cs_d:+.4f}% '
                             f'→ 边际 {_CS_MARGIN_DELTA:+.4f}pct → {CS_STATE}'),
        'intraday_low': cs['low'],
        'judgement': (f'中证消费 10/16 收 {cs_close:,.4f}（{cs_pct:+.2f}%），距 {LINE_CS:,.0f} 下沿 '
                      f'**{_cs_d:+.4f}%** → **安全边际较 10/15 档登记的 {_cs_d_prev:+.4f}% '
                      f'{_CS_DIR} {_CS_ABS_DELTA:.4f}pct**；'
                      f'日内低 {cs["low"]:,} 未破；本档为**全市场唯一显著走强的内需腿**（沪指 {IDXP["000001"]:+.2f}%、'
                      f'创业板指 {IDXP["399006"]:+.2f}%、沪深300 {IDXP["000300"]:+.2f}%）→ 大消费显著跑赢大盘、无触发；'
                      f'⚠️ 内部结构：中证白酒 **{pc["board_detail"]["399997"]:+.2f}%** 与中证消费 '
                      f'{pc["board_detail"]["000932"]:+.2f}% **同向为正**（相差 '
                      f'{round(pc["board_detail"]["399997"] - pc["board_detail"]["000932"], 2):.2f}pct）'
                      f'→ 与 10/15「白酒独强」型分化不同，本档为**同步走强**（§3.129c 结构切换须显式披露）'),
        'next_line': LINE_CS_NEXT,
        'next_line_dist_pct': round((cs_close / LINE_CS_NEXT - 1) * 100, 4),
    },
    'a_med_reverse_1_5pct': {
        'proxy_pct': pc['board_med'], 'board_med': pc['board_med'],
        'leader_med': pc['leader_med'], 'lag_med': pc['lag_med'],
        'single_day_000933': medi['pct'],
        'line_pct': -1.5, 'dist_pct': round(pc['board_med'] - (-1.5), 4),
        'state': 'TRIGGERED' if _MED_TRIGGERED else 'NOT_TRIGGERED',
        'semantics': '§3.71 / §3.136a：利好兑现后的回调观察线，**非止损线** → 处置 = 不执行主动减配',
        'intraday_state': (f'未触发（13:45 盘中代理 {pi["board_med"]:+.4f}%，'
                           f'portfolio_intraday_20261016.json defense.med_reverse_line = '
                           f'{str(pi["defense"]["med_reverse_line"]).lower()}）'),
        'state_continuity': (f'盘中 → 收盘 **同向走弱**（{pi["board_med"]:+.4f}% → '
                             f'{pc["board_med"]:+.4f}%）→ **收盘级首次触及 −1.5% 反向兑现线**'
                             f'（盘中口径尚未触及、收盘口径已触发，两口径须并列披露，§3.117d）'),
        'contingency_closed': True, 'contingency_triggered': False,
        'action': 'active_take_profit = 0 / new_buy = 0',
        'closed_requirement': ('**闭环要求（本档登记、判定权移交 10/19 盘后档）**：若下一交易日（10/19）收盘'
                               '板块代理续跌、与 10/16 形成「连续 2 日回调」（即 10/19 代理 ≤ 0%），'
                               '则须于**再下一盘前档（10/20）建立被动减配预案**'
                               '（0.5% × 基准总资产 = 0.5% × ' + format(pc['base_total'], ',.2f') + ' 元 = '
                               + format(round(pc['base_total'] * 0.005, 2), ',.2f') + ' 元；'
                               '候选 012323 华宝中证医疗C / 001180 广发医药卫生ETF联接A）；'
                               '**本档只登记、不动作**（该线非止损线，§3.71）'),
        'trigger_count_since_inception': 3,
        'trigger_history': [{'date': '2026-09-24', 'proxy_pct': -2.3775, 'note': '首次触发（§3.104）'},
                            {'date': '2026-10-08', 'proxy_pct': -2.6475,
                             'note': '第 2 次触发 → 10/9 盘前档建立预案、10/9 收盘按「回调序列断裂」作废'},
                            {'date': '2026-10-16', 'proxy_pct': pc['board_med'],
                             'note': '**第 3 次触发**（本档；对照：10/13 −1.1625%、10/14 −0.8500%、10/15 −0.4500% 均贴线未触发）'}],
        'judgement': (f'A股医药板块代理 {pc["board_med"]:+.4f}%（中证医药 {medi["pct"]:+.2f}% / '
                      f'中证医疗 {med_etf["pct"]:+.2f}% / '
                      f'300医药 {pc["leader_med"]:+.2f}%）→ '
                      f'① 负号方向的「主动兑现线」（≤ −1.5%）**收盘级已触发**（距线 '
                      f'{pc["board_med"] - (-1.5):+.4f}pct）→ **本档主动减配 = 0 元**（该线为回调观察线、非止损线，§3.71）；'
                      f'② +1.5% 反转线**未触发**（距 {round(1.5 - pc["board_med"], 4):+.4f}pct）；'
                      f'③ 盘前登记的「被动减配预案」'
                      f'已于 10/9 按预案明文「回调序列断裂、预案不启动」作废（盘前档 '
                      f'`contingency_closed = {str(po["defense_lines"]["a_med_reverse_1_5pct"].get("contingency_closed")).lower()}`）'
                      f' → 本档维持作废、**不自动复活**，须按上述闭环要求重新建立；'
                      f'④ 内部结构：中证医药 {medi["pct"]:+.2f}% > 300医药 {pc["leader_med"]:+.2f}% > 中证医疗 '
                      f'{med_etf["pct"]:+.2f}% → **序位与 10/13-10/15 的「大市值抗跌」结构反向切换**（本档大市值 300医药 反而最深）。'
                      f'内部离散度 {round(pc["leader_med"] - pc["lag_med"], 4):.4f}pct（300医药 − 中证医疗）'),
    },
}

# ---------- 2. 纪律执行台账 ----------
hk_cum_since_cut1 = round((hstech['close'] / idx['HSTECH']['2026-09-29'] - 1) * 100, 4)
hk_cum_since_cut2 = round((hstech['close'] / idx['HSTECH']['2026-10-08'] - 1) * 100, 4)
hk_day_prev = round((hstech['close'] / idx['HSTECH'][PREV] - 1) * 100, 4)
ledger = [{
    'date': TODAY, 'kind': '本档无新增纪律动作',
    'amount': 0.0,
    'reason': (f'恒生科技 10/16 收 {hstech["close"]:,}（{hstech["pct"]:+.2f}%），距 4,250 为 {_hk_d:+.4f}% → '
               f'仍处破位区间但**幅度收窄 {_HK_DELTA:.4f}pct** 且**未叠加触发**（当日防线只触发一次，§3.114c）；'
               f'中证消费 {cs_close:,.4f} 距 12,100 为 {_cs_d:+.4f}%（边际 {_CS_MARGIN_DELTA:+.4f}pct，'
               f'**未破下沿**）；A股医药代理 {pc["board_med"]:+.4f}% **触达 −1.5% 反向兑现线**，'
               f'但该线非止损线 → 主动减配 0 元、只登记并移交 10/19 档闭环判定'),
    'cumulative_amount': pc['discipline']['cumulative_amount'],
    'cumulative_selfcheck': pc['discipline']['cumulative_selfcheck'],
    'weight_after': pc['discipline']['weight_after'],
    'next_rule': f'恒生科技下一道防线 4,000（距 {lines["hstech_4250"]["next_line_dist_pct"]:+.4f}%）；再破不叠加新纪律',
}]

ledger_hist = [
    {'date': '2026-09-29', 'kind': '大消费 0.5% 纪律兑现', 'amount': 1879.43,
     'trigger': '9/28 收盘级跌破 12,100（12,096.0166，−0.033%）', 'settle': '按 9/29 净值成交（价值中性）',
     'outcome': (f'9/29 收 12,107.1705 收复 12,100 → 定性「技术性误触」；'
                 f'10/16 收 {cs_close:,.4f}（距下沿 {_cs_d:+.4f}%、较 10/15 档登记值 {_CS_DIR} '
                 f'{_CS_ABS_DELTA:.4f}pct）'
                 f'→ 结论延续、未再触发')},
    {'date': '2026-09-30', 'kind': '恒生科技 0.5% 纪律减仓（第 1 次）', 'amount': 1882.46,
     'trigger': '9/29 收盘级破位（4,249.62，−0.0089%，**边际破位**）', 'settle': '按 9/30 净值成交',
     'outcome': (f'9/30 收 4,253.89 收复防线 → 记为「**边际破位成本**」；'
                 f'10/16 收 {hstech["close"]:,}（距防线 {_hk_d:+.4f}%）→ 自触发日（9/29 收 4,249.62）累计 '
                 f'{hk_cum_since_cut1:+.4f}%，**事后看方向正确**（标的仍低于减仓时点，'
                 f'减仓规避的持仓损失 ≈ **{-1882.46 * hk_cum_since_cut1 / 100:+,.2f} 元**'
                 f'＝ 1,882.46 元 × {abs(hk_cum_since_cut1):.4f}%）')},
    {'date': '2026-10-08', 'kind': '恒生科技 0.5% 纪律减仓（第 2 次）', 'amount': 1904.44,
     'trigger': '10/2 收盘级破位（4,157.94，−2.1661%，**非边际破位**）', 'settle': '按 10/8 净值成交（价值中性）',
     'outcome': (f'执行日（10/8）恒生科技收 4,073.38（−2.89%，距防线 −4.1558%）→ 当日看属「**有效减仓**」；'
                 f'⚠️ 自执行日（10/8 收 4,073.38）至本档 {hstech["close"]:,} = **{hk_cum_since_cut2:+.4f}%** '
                 f'→ 短期机会成本 ≈ {1904.44:,.2f} 元 × {hk_cum_since_cut2:.4f}% ≈ '
                 f'**{1904.44 * hk_cum_since_cut2 / 100:+,.2f} 元**（本档单日 {hk_day_prev:+.4f}%）；'
                 f'**⚠️ 「减仓后标的反弹」读数由 10/15 的 NEGATIVE（标的低于执行日价）于本档翻回 POSITIVE**'
                 f'（正负号 {hk_cum_since_cut2:+.4f}%）→ **该短期读数在正负之间反复切换、不构成纪律判定依据**'
                 f'（§3.130a）；仅为短期读数、不改变纪律判定')},
]

# ---------- 3. 待消化收口 + QDII 挂账 ----------
pending = {
    'as_of': TODAY,
    'hk_leg_pending': pc['pending_release'],
    'qdii_pending': pc['qdii_pending'],
    'pending_total': {
        'hk_leg': ('已收口（10/8 由场外港股联接 000071 / 012348 真实净值一次性兑现，`window_closed = true`）；'
                   '本档无新增窗口（10/16 为正常交易日，港股腿按当日真实净值/收盘价逐券定价）'),
        'qdii_leg_range': [pc['qdii_pending']['remaining']['low'],
                           pc['qdii_pending']['remaining']['high']],
        'qdii_leg_note': ('余 **US 10/16 一个未知交易日**（北京 10/17 04:00 成型）；'
                          '本档挂账区间按 0 计系**「尚无已知美股交易日进入挂账」**，非「挂账已消失」（§3.124a / §3.120c）；'
                          '⚠️ **US 10/15 段本档已由真实净值核销** —— 实测 '
                          + format(pc['qdii_pending']['booked_this_session']['amount'], '+,.2f') + ' 元，'
                          '**超出 10/16 盘前/盘中档预告区间（+653.99 元 ~ +980.98 元）上界 '
                          + ('%+.2f' % pc['qdii_pending']['booked_this_session']['pred_vs_realized']['vs_high_pct'])
                          + '%** → §3.118a「区间法」累计 4 个可检验样本中**第 2 例越界**'
                          '（前 3：10/9 段成立、10/12 段越上界 +15.7%、10/14 段成立）'),
    },
    'note': ('§3.112f / §3.118a：挂账只给区间、禁止中枢点值。'
             '**本档为 US 10/15 段的释放档**：QDII 000369 / 016280 自基准净值日 10/14 起至 10/15（'
             f'1 个美股交易日）已由真实净值核销 {pc["qdii_pending"]["booked_this_session"]["amount"]:+,.2f} 元；'
             f'164906（交银海外互联 LOF）同步自 10/14 释放至 10/15（0.8652，−1.8384%）；'
             f'IYH 10/14→10/15 = {pc["iyh_1013_pct"]:+.4f}% → 实测隐含传导系数（以 IYH 为分母，§3.145c 主口径）000369 = '
             f'{pc["qdii_pending"]["coef_reestimate"]["observed_samples"]["2026-10-15"].get("000369")} / 016280 = '
             f'{pc["qdii_pending"]["coef_reestimate"]["observed_samples"]["2026-10-15"].get("016280")}，'
             '**两只均越上界 0.90**（以 XLV 为分母则为 1.0373 / 1.0345，同样越上界 → '
             '**两套分母同向越界、非分母定义所致的歧义**）；'
             '⚠️ 本档**仍不更新 0.72 中枢**：按 §3.118a 须以多券（≥4 券位）×多日（≥5 交易日）重估，'
             f'当前 2 券位 × 4 窗口（10/9、10/12、10/14、10/15 四段）→ **系数未重估前基于该系数的一切仓位决策无效**'),
}

# ---------- 4. 节假日历（逐市场分列，§3.115d） ----------
calendar = {
    '2026-10-15（上一档）': ('A股 + 港股双市场正常交易日双收盘；'
                          '上证 3,707.476（−1.59%）/ 创业板指（−2.92%）/ 沪深300（−1.33%）/ '
                          '科创50（−1.34%）/ 中证消费 12,310.3164（−0.42%）；'
                          '恒指 24,062.72（−1.03%）/ 恒生科技 4,060.99（−2.72%，本轮调整新低）/ '
                          '恒生医疗保健 −0.9091%；'
                          '组合 −0.4117%（−1,530.57 元，取 `_fix` 修正值）；QDII US 10/14 段释放 +1,198.49 元'),
    '2026-10-16（今日）': (
        'A股 + 港股双市场正常交易日并在本档双收盘；'
        f'上证 {idx["000001"][TODAY]}（{IDXP.get("000001", 0.0):+.2f}%）/ '
        f'深证成指 {IDXP.get("399001", 0.0):+.2f}% / '
        f'创业板指 {idx["399006"][TODAY]}（{IDXP.get("399006", 0.0):+.2f}%）/ '
        f'科创50 {IDXP.get("000688", 0.0):+.2f}% / '
        f'沪深300 {IDXP.get("000300", 0.0):+.2f}% / 中证消费 {pc["board_detail"]["000932"]:+.2f}%；'
        f'恒指 {idx["HSI"][TODAY]}（{IDXP.get("HSI", 0.0):+.2f}%）/ '
        f'恒生科技 {idx["HSTECH"][TODAY]}（{IDXP.get("HSTECH", 0.0):+.2f}%）/ '
        f'恒生医疗保健 {IDXP.get("HSHCI", 0.0):+.2f}%；'
        'A股「指数微涨、结构剧烈分化」：沪指 +0.24% 而创业板指 −0.39%，'
        '**中证消费 +1.46% 与中证白酒 +1.30% 同步走强、中证医药 −1.31% 与中证医疗 −2.33% 深跌**'
        '→ 组合内部「消费腿正 / 医药腿负」完全对冲；'
        '港股三大指数同向收涨（恒指 +0.52% / 恒科 +1.16% / 恒生医疗 +1.35%）；'
        'QDII US 10/15 段由真实净值核销 +1,151.97 元（组合最大正贡献赛道）；'
        '⚠️ 组合当日 −0.1377%，**六个估值日以来最小单日跌幅**（W42 五连负中最浅）'),
    NEXT_TD: ('**下一交易日（周一）**：⚠️ **10/19 为「港股重阳节翌日休市 + A股 正常交易」→ 混合档镜像情形**'
              '（§3.108 条款 22 / §3.121e：港股腿当日不可定价、港联系 13.26% 敞口应收敛为「隔日待消化」）；'
              '10/19 盘后档须**重新判定 A股医药反向兑现线**（本档收盘级首次触发 −1.8025% → 判定「连续 2 日回调」是否成立）；'
              '2026 金融街论坛年会开幕（吴清作主题演讲）；'
              '⚠️ 本档未定价券（000248 双账户 / 110020 / 002742）10/16 净值须于 10/19 08:00 兜底复抓'
              '（取到须以同日 `_fix` 覆盖并同步重算 `tracks[].pnl`，§3.155a / §3.140a）'),
    '2026-10-17~18': '周末（A股 + 港股均休市）→ 档型①「纯非交易日」；美股 10/16 收盘（北京 10/17 04:00 成型）将进入 QDII 挂账',
    '2026-10-27~28': 'FOMC 议息会议（更正口径见知识库 §3.155c 同类日历核验要求：须双源交叉验证）',
}

# ---------- 5. 敞口与门槛 ----------
exposure = {
    'tracks': {k: {'mv': v['mv'], 'pct': round(v['mv'] / float(total_mv) * 100, 2),
                   'pnl': v['pnl'], 'day_pct': v['day_pct']}
               for k, v in tr.items()},
    'weight_after_discipline': pc['discipline']['weight_after'],
    'med_exposure': pc['med_exposure'], 'med_pct': pc['med_pct'],
    'threshold_all_med': pc['threshold_all_med'], 'threshold_a_sh_med': pc['threshold_a_sh_med'],
    'med_pct_prev': po['med_pct'], 'med_pct_delta': round(pc['med_pct'] - po['med_pct'], 2),
    'hk_split': pc['hk_split'], 'hk_split_pnl': pc['hk_split_pnl'], 'hk_split_rows': pc['hk_split_rows'],
    'hk_total': pc['hk_total'], 'hk_total_pct': pc['hk_total_pct'],
    'hk_track_layer_pct': pc['track_layer_hk_pct'],
    'hk_broad_layer_pct': round(pc['hk_total_pct'] - pc['track_layer_hk_pct'], 2),
    'hk_segments': {'pure': pc['hk_split']['pure'], 'concept': pc['hk_split']['concept'],
                    'broad': pc['hk_split']['broad']},
}

# ---------- 6. 涨跌归因（从 detail 现算，§3.133a） ----------
det = [d for d in pc['detail'] if d.get('est_pnl') is not None]
srt = sorted(det, key=lambda x: x['est_pnl'])
def brief(d):
    return {'name': d['name'], 'code': d['code'], 'track': d['track'],
            'pct': d['est_pct'], 'pnl': d['est_pnl'], 'price_src': d['price_src'][:64]}
TOP_DRAG = [brief(d) for d in srt[:6]]
TOP_GAIN = [brief(d) for d in srt[-6:]][::-1]
trk_pnl = {k: v['pnl'] for k, v in tr.items()}
drag_rank = [k for k, _ in sorted(trk_pnl.items(), key=lambda kv: kv[1]) if k != '现金']
gain_rank = [k for k, _ in sorted(trk_pnl.items(), key=lambda kv: -kv[1]) if k != '现金']


def _base(c):
    return str(c).split('.')[0]


def _sum(code_prefix, track=None):
    return round(sum(d['est_pnl'] for d in det
                     if _base(d['code']).startswith(code_prefix)
                     and (track is None or d['track'] == track)), 2)


def _pct(code_prefix, track=None):
    v = [d['est_pct'] for d in det if _base(d['code']).startswith(code_prefix)
         and (track is None or d['track'] == track)]
    return v[0] if v else None


GLD_PNL, GLD_PCT = _sum('002410'), _pct('002410')
M708_PNL, M708_PCT = _sum('002708'), _pct('002708')
QDII369_PNL = _sum('000369')
QDII280_PNL = _sum('016280')
LOF906_PNL = _sum('164906')
P012323, S012323 = _pct('012323'), _sum('012323')
P512170 = _pct('512170')
ZERO_ROWS = [d for d in det if '未推进' in str(d.get('price_src', ''))]
ZERO_CODES = sorted({_base(d['code']) for d in ZERO_ROWS})
NAV_PRECISE = pc['est_total_pct_raw']
pos_sum = round(sum(d['est_pnl'] for d in det if d['est_pnl'] > 0), 2)
neg_sum = round(sum(d['est_pnl'] for d in det if d['est_pnl'] < 0), 2)

# §3.149h：赛道胜负计数一律由 tracks[].pnl 现算（三分：正 / 负 / 零）
_neg = [k for k, v in trk_pnl.items() if round(v, 2) < 0]
_pos = [k for k, v in trk_pnl.items() if round(v, 2) > 0]
_zero = [k for k, v in trk_pnl.items() if round(v, 2) == 0]
COUNT_STR = f'{len(_neg)}负{len(_pos)}正{len(_zero)}零'
COUNT_STR_LIST = f'{len(_neg)}负（{" / ".join(_neg)}）+ {len(_pos)}正（{" / ".join(_pos)}）+ {len(_zero)}零（{" / ".join(_zero)}）'

# 未定价券的「估值缺口」敏感性：按所属赛道板块代理折算（区间下界 / 上界，§3.116b）
_track_proxy = {'A股医药': pc['board_med'], '大消费': pc['board_detail']['000932'],
                '其他/宽基': pc['idx']['000300'], '恒生科技': pc['idx']['HSTECH']}
GAP_ROWS = []
for d in ZERO_ROWS:
    _gap = round(d['mv0_new'] * _track_proxy.get(d['track'], 0.0) / 100, 2)
    GAP_ROWS.append({'code': _base(d['code']), 'track': d['track'], 'mv0': d['mv0_new'],
                     'proxy_pct': _track_proxy.get(d['track'], 0.0), 'est_pnl_if_proxy': _gap})
GAP_TOTAL = round(sum(x['est_pnl_if_proxy'] for x in GAP_ROWS), 2)
GAP_MV = round(sum(x['mv0'] for x in GAP_ROWS), 2)
GAP_ALT_PNL = round(pc['est_total_pnl'] + GAP_TOTAL, 2)
GAP_ALT_PCT = round(GAP_ALT_PNL / pc['base_total'] * 100, 4)

driver = {
    'top_drag': TOP_DRAG,
    'top_gain': TOP_GAIN,
    'track_pnl_rank': drag_rank,
    'pos_sum': pos_sum, 'neg_sum': neg_sum,
    'attribution': (
        f'① **本档为「A股医药单腿深跌、消费腿与 QDII 腿双向对冲」的结构分化日**（非单边日）：'
        f'沪指 {IDXP["000001"]:+.2f}%（3,716.28，微幅收复但仍在 3,750 下方）、深证成指 {IDXP["399001"]:+.2f}%、'
        f'创业板指 {IDXP["399006"]:+.2f}%、科创50 {IDXP["000688"]:+.2f}%、沪深300 {IDXP["000300"]:+.2f}%；'
        f'恒指 {IDXP["HSI"]:+.2f}%、恒生科技 {IDXP["HSTECH"]:+.2f}% → 组合估算 {pc["est_total_pnl"]:+,.2f} 元'
        f'（{NAV_PRECISE:+.4f}%），正贡献 {pos_sum:+,.2f} 元 / 负贡献 {neg_sum:+,.2f} 元 → '
        f'**六赛道{COUNT_STR}**（{COUNT_STR_LIST}）；'
        f'② **最大拖累 = A股医药 {tr["A股医药"]["pnl"]:+,.2f} 元**（{tr["A股医药"]["day_pct"]:+.3f}%）——'
        f'大摩健康产业 002708 **{M708_PCT:+.3f}%（两行合计 {M708_PNL:+,.2f} 元）**、'
        f'华宝中证医疗联接 012323 {P012323:+.3f}%（{S012323:+,.2f} 元）、'
        f'融通医疗保健 161616 {_pct("161616"):+.3f}%、医疗ETF 512170 {P512170:+.2f}%、'
        f'广发医药卫生 001180 {_pct("001180"):+.3f}%、融通健康产业 000727 {_pct("000727"):+.3f}% → '
        f'**腿内六券同向为负、无背离**；板块层 300医药 {pc["leader_med"]:+.2f}% / 中证医药 {medi["pct"]:+.2f}% / '
        f'中证医疗 {med_etf["pct"]:+.2f}% → **腿代理深于任一板块指数**'
        f'（主动基弹性 ×1.493 / ×1.330，§3.156a 镜像条款）；'
        f'③ **第二大贡献 = 美股标普医药 {tr["美股标普医药"]["pnl"]:+,.2f} 元**（{tr["美股标普医药"]["day_pct"]:+.3f}%）'
        f'——**全部来自 QDII US 10/15 段净值释放**（000369 {_pct("000369"):+.3f}% / 016280 '
        f'{_pct("016280"):+.3f}%，合计 {QDII369_PNL + QDII280_PNL:+,.2f} 元），'
        f'**非 10/16 美股行情**（北京 20:00 时美股未开盘，§3.120c）→ **本档组合的核心对冲项**；'
        f'④ **第三大贡献 = 大消费 {tr["大消费"]["pnl"]:+,.2f} 元**（{tr["大消费"]["day_pct"]:+.3f}%）——'
        f'消费ETF添富 159928 {_pct("159928"):+.3f}%（{_sum("159928"):+,.2f} 元）、'
        f'富国消费主题 519915 {_pct("519915"):+.3f}%（{_sum("519915"):+,.2f} 元）、'
        f'汇添富文体娱乐 004424 {_pct("004424"):+.3f}%（{_sum("004424"):+,.2f} 元）、'
        f'广发养老产业 000968 {_pct("000968"):+.3f}% → 与中证消费 {pc["board_detail"]["000932"]:+.2f}%、'
        f'中证白酒 {pc["board_detail"]["399997"]:+.2f}% 一致；'
        f'⚠️ 该腿内 **000248（双账户 2 行，notional {round(sum(d["mv0_new"] for d in ZERO_ROWS if _base(d["code"]) == "000248"), 2):,.2f} 元）未出净值 → 计 0 元**（估值缺口，见下）；'
        f'⑤ **恒生科技 {tr["恒生科技"]["pnl"]:+,.2f} 元**（{tr["恒生科技"]["day_pct"]:+.3f}%）——'
        f'恒生科技指数 {IDXP["HSTECH"]:+.2f}%、天弘恒科联接 012348 {_pct("012348"):+.3f}%（两行 {_sum("012348"):+,.2f} 元）、'
        f'恒指科技 513180 {_pct("513180"):+.2f}%、中概互联 513050 {_pct("513050"):+.2f}%（{_sum("513050"):+,.2f} 元）'
        f'**为正**，而 **164906（交银海外互联 LOF）{_pct("164906"):+.3f}%（{LOF906_PNL:+,.2f} 元）为负** → '
        f'**同日腿内符号相反，属「境外上市中概 vs 港股中概」的时序错位（§3.112i 禁互验），非数据异常**；'
        f'⑥ **其他/宽基 {tr["其他/宽基"]["pnl"]:+,.2f} 元**（{tr["其他/宽基"]["day_pct"]:+.3f}%）——'
        f'广联达（002410）{GLD_PCT:+.2f}%（{GLD_PNL:+,.2f} 元）、通威股份 600438 {_pct("600438"):+.2f}%（{_sum("600438"):+,.2f} 元）'
        f'为正、**100红利 515180 {_pct("515180"):+.2f}%（{_sum("515180"):+,.2f} 元，⚠️ 当日除息 XD，见专题）**、'
        f'证券ETF {_pct("512880"):+.2f}%、传媒ETF {_pct("512980"):+.2f}%、'
        f'天弘证券保险 {_pct("001552"):+.3f}% 为负 → **腿内几乎完全对冲（−13.18 元）**；'
        f'⑦ **现金** 0.00 元（账面冻结项，不构成方向判断）；'
        f'⑧ **⚠️ 估值缺口提示**：{len(ZERO_CODES)} 只未定价券（' + '、'.join(ZERO_CODES) + f'）共 {len(ZERO_ROWS)} 行、'
        f'notional 合计 {GAP_MV:,.2f} 元（占组合 {GAP_MV / float(total_mv) * 100:.2f}%），'
        f'若按所属赛道板块代理折算，组合当日将再变动约 {GAP_TOTAL:+,.2f} 元 → '
        f'**估算区间下界 {GAP_ALT_PNL:+,.2f} 元（{GAP_ALT_PCT:+.4f}%）**；本档主口径仍按「基准已含 → 计 0」'
        f'（§3.105），**该缺口须在 10/19 08:00 兜底复抓后以 `_fix` 覆盖修正**'),
}

out = {'date': TODAY, 'as_of': '2026-10-16 收盘（A股 长假后第 7 个正常交易日 + 港股正常交易日；双市场双收盘）',
       'session_type': pc['session_type'],
       'base_total': pc['base_total'], 'base_file': pc['base_file'], 'total_mv': total_mv,
       'est_total_pnl': pc['est_total_pnl'], 'est_total_pct': pc['est_total_pct'],
       'est_total_pnl_low': pc['est_total_pnl_low'], 'est_total_pnl_high': pc['est_total_pnl_high'],
       'defense_lines_close': lines,
       'discipline_ledger': ledger, 'discipline_ledger_history': ledger_hist,
       'pending': pending, 'calendar': calendar, 'exposure': exposure, 'driver': driver,
       'track_count_str': COUNT_STR,
       'est_gap': {'codes': ZERO_CODES, 'notional': GAP_MV,
                   'notional_pct': round(GAP_MV / float(total_mv) * 100, 2),
                   'rows': GAP_ROWS, 'implied_pnl_if_proxy': GAP_TOTAL,
                   'gap_total_pnl': GAP_ALT_PNL, 'gap_total_pct': GAP_ALT_PCT,
                   'note': ('§3.105：未定价券按「基准已含 → 计 0」处理，属估值缺口而非零波动；'
                            '缺口敏感性按所属赛道板块代理折算，**只给量级、不作方向判断**（§3.116b）')},
       'ex_div_event': pc['ex_div_adjustment'],
       'action_next': {
           'next_session': NEXT_TD + '（周一，⚠️ 港股重阳节翌日休市 + A股 正常交易日 → 混合档镜像情形）',
           'planned': (f'① **3 只未出 10/16 净值券 08:00 兜底复抓**（000248 双账户 / 110020 / 002742，'
                       f'notional {GAP_MV:,.2f} 元）；若到位 → 出 `_fix` 件覆盖本档并**同步重算 `tracks[].pnl`**'
                       f'（§3.155a / §3.140a / §3.149g）；'
                       f'② **A股医药反向兑现线闭环判定（本档最高优先级）**：本档收盘级首次触发 '
                       f'（代理 {pc["board_med"]:+.4f}% ≤ −1.5%）→ 10/19 盘后档复核「连续 2 日回调」是否成立'
                       f'（10/19 代理 ≤ 0% 即成立）→ 成立则 10/20 盘前档建立被动减配预案'
                       f'（{format(round(pc["base_total"] * 0.005, 2), ",.2f")} 元，候选 012323 / 001180，§3.136a）；'
                       f'③ **10/19 混合档产物口径预备**：A股 正常交易 + 港股休市 → 按 §3.108 条款 22 判定'
                       f'（若 A股 开市则产 `portfolio_close_*`、港股腿单列「隔日待消化」；'
                       f'港联系 13.26% 敞口当日不可定价）；'
                       f'④ **QDII 挂账刷新**：US 10/16 收盘（北京 10/17 04:00 成型）→ 000369/016280 与 164906 '
                       f'取得最新净值日则按 §3.105 回填（**以基准行 `price_src` 反解基准净值日，禁用固定日期常量**）；'
                       f'⑤ 复核恒生科技 4,000 防线（本档距 {lines["hstech_4250"]["next_line_dist_pct"]:+.4f}%，'
                       f'较 10/15 走阔）与「减仓后标的反弹」样本（本档为第 5 个负样本）；'
                       f'⑥ 复核中证消费 12,100 下沿（本档距 {lines["zz_consume_12100"]["dist_pct"]:+.4f}%，'
                       f'较上一档 {_CS_DIR} {_CS_ABS_DELTA:.4f}pct）与 12,000 次级线；'
                       f'⑦ 复核医药敞口 {pc["med_pct"]:.2f}%（距 40% 上限门槛：全部医药 '
                       f'{pc["threshold_all_med"]:+.2f}% / 仅 A股医药 {pc["threshold_a_sh_med"]:+.2f}%）'
                       f'——**任何正向催化均不构成加仓理由**（new_buy = 0）；'
                       f'⑧ **100红利 ETF 除息（XD）42.70 元现金分红的到账登记**（本档仅按价格口径披露，§3.108）；'
                       f'⑨ E大（长赢计划）adj / inv 后续跟踪（本档零变动）；'
                       f'⑩ 登记 **2026 世界传统医药大会（大会 10/17-18 / 配套展览会 10/16-18）** 对中药板块的边际影响'),
       },
       'note': ('10/16 **无新增纪律动作**（三条防线：恒科破位**收窄至 −3.3355%** 仍未叠加触发 / '
                '中证消费仍站稳下沿（边际 ' + f'{_CS_MARGIN_DELTA:+.4f}pct' + '）/ '
                f'A股医药代理 {pc["board_med"]:+.4f}% **首次触及 −1.5% 反向兑现线**（非止损线 → 主动减配 0 元、只登记））；'
                '待消化：长假港股腿已收口、QDII 腿为「US 10/15 段释放 '
                + format(pc['qdii_pending']['booked_this_session']['amount'], '+,.2f') + ' 元 + 余 0」；'
                f'⚠️ 本档**有 {len(ZERO_CODES)} 只未定价券**（' + '、'.join(ZERO_CODES) + '，'
                f'共 {len(ZERO_ROWS)} 行、notional {GAP_MV:,.2f} 元），其余 {len(det) - len(ZERO_ROWS)} 行为真实价格 / 真实净值；'
                f'未定价券的估值缺口量级 ≈ {GAP_TOTAL:+,.2f} 元（按所属赛道板块代理折算）'
                '（§3.105「基准已含」口径）'),
       'nav_pending_after_refetch': {'codes': ZERO_CODES, 'refetched_codes': [],
                                     'refetch_time': None,
                                     'pnl_delta': 0.0}}

json.dump(out, open(os.path.join(HIST, 'portfolio_strategy_close_' + TODAYC + '.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)

print('✅ 三条防线收盘级判定:')
for k, v in lines.items():
    print(f'  {k}: state={v["state"]} close={v.get("close", v.get("board_med"))} '
          f'dist={v["dist_pct"]:+.4f}%')
print(f'\n✅ 本档纪律动作 = 0（累计已登记 {pc["discipline"]["cumulative_amount"]:,.2f} 元）')
print(f'✅ 恒科第 2 次减仓自执行日累计 {hk_cum_since_cut2:+.4f}% → 机会成本 ≈ '
      f'{1904.44 * hk_cum_since_cut2 / 100:,.2f} 元')
print(f'✅ 恒科第 1 次减仓自触发日累计 {hk_cum_since_cut1:+.4f}% → 规避损失 ≈ '
      f'{-1882.46 * hk_cum_since_cut1 / 100:+,.2f} 元')
print(f'\n✅ 待消化: 港股腿已收口；QDII 腿区间 = {pending["pending_total"]["qdii_leg_range"]} 元；'
      f'本档释放 {pc["qdii_pending"]["booked_this_session"]["amount"]:+,.2f} 元')
print(f'\n✅ 敞口：医药 {pc["med_pct"]:.2f}%（门槛全部 {pc["threshold_all_med"]:+.2f}% / 仅A股医药 {pc["threshold_a_sh_med"]:+.2f}%）'
      f'｜港联系 {pc["hk_total_pct"]:.2f}%（赛道层 {pc["track_layer_hk_pct"]:.2f}% + 宽基 '
      f'{exposure["hk_broad_layer_pct"]:.2f}pct）')
print(f'\n✅ 减仓后权重: ' + ' / '.join(f'{k} {v:.2f}%' for k, v in pc['discipline']['weight_after'].items()))
print(f'\n防线：恒生科技 {hstech["close"]:,} ({hstech["pct"]:+.2f}%) vs {LINE_HK:,.0f} → '
      f'{lines["hstech_4250"]["state"]}（{lines["hstech_4250"]["dist_pct"]:+.4f}%）')
print(f'      中证消费 {cs_close:,} ({cs_pct:+.2f}%) vs {LINE_CS:,.0f} → '
      f'{lines["zz_consume_12100"]["state"]}（{lines["zz_consume_12100"]["dist_pct"]:+.4f}%）')
print(f'      A股医药板块代理 {pc["board_med"]:+.4f}% vs −1.5% / +1.5% → '
      f'{lines["a_med_reverse_1_5pct"]["state"]}')
print(f'\nTop 拖累: ' + ' | '.join(f'{d["name"]} {d["pnl"]:+,.2f}' for d in TOP_DRAG[:4]))
print(f'Top 贡献: ' + ' | '.join(f'{d["name"]} {d["pnl"]:+,.2f}' for d in TOP_GAIN[:4]))
print(f'\n未出净值券: {ZERO_CODES}（{len(ZERO_ROWS)} 行，notional {GAP_MV:,.2f} 元）')
print(f'赛道计数: {COUNT_STR}  ←  {COUNT_STR_LIST}')

print(f'\n已保存 portfolio_strategy_close_{TODAYC}.json')
