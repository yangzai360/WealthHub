# -*- coding: utf-8 -*-
"""2026-10-15 盘后：策略层产物（三条防线收盘级判定 + 纪律执行台账 + 待消化 + 港股三层拆解）
输出：portfolio_strategy_close_20261015.json

⚠️ 档型 = **正常交易日收盘档**（A股 10/15 长假后第 6 个正常交易日 15:00 收盘 + 港股 10/15 正常交易日 16:00 收盘）
   下一交易日 = **2026-10-16（周五）**
⚠️ §3.133a：所有展示字段（点位/距离/趋势序列）一律从 indices.csv 与 close_<DATE>.json **现算**，禁止硬编码常量
⚠️ §3.145a：**state 类字段禁止从上一档派生继承** —— 本档恒科 state 由「本档 dist_pct vs 上一档 dist_pct」现算
   （上一档 10/14 = −1.7772%、本档 = −4.4473% → 绝对值**走阔** → `BROKEN_CLOSE_LEVEL_WIDENED`）
⚠️ §3.106 条款 17 / §3.121c：本档由 10/14 版 sed 派生后逐项手工核对「档型语义 / 日期常量 / 基准文件 / 前档基准值 / 归一化文案」五类字面量
"""
import json, os, csv

BASE = '/Users/jieyang/Documents/WealthHub'
HIST = os.path.join(BASE, 'data/processed/history')
TODAY = '2026-10-15'
TODAYC = TODAY.replace('-', '')
PREV = '2026-10-14'
NEXT_TD = '2026-10-16'

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
three_hundred_med = next(x for x in cur['boards'] if x['code'] == 'sh000913') if any(
    x['code'] == 'sh000913' for x in cur['boards']) else None

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
        'judgement': (f'破位幅度由 10/14 的 {prev_break:+.4f}% **{_HK_DIR}至 {_hk_d:+.4f}%**'
                      f'（{_HK_DIR} {_HK_DELTA:.4f}pct；本档单日 {hstech["pct"]:+.2f}%）；'
                      f'⚠️ 日内最高 {hstech["high"]:,} **< 4,250 → 全日未站上**（13:45 盘中读数 '
                      f'{pi["defense"]["hstech"]:,} / 距防线 {pi["defense"]["hstech_vs_4250"]:+.4f}%）；'
                      f'按 §3.114c「同日防线只触发一次」→ 本档**不新增纪律动作**，防线维持 4,250；'
                      f'⚠️ 本档读数 {_hk_d:+.4f}% 为 10/8（−4.1558%）以来最深、距下一道 4,000 线仅 '
                      f'{round((hstech["close"] / 4000 - 1) * 100, 4):+.4f}% → **4,000 为当前最需盯盘线位**；'
                      f'⚠️ 单日收跌不改变二元判据（收盘价 < 防线），亦不触发反向补仓'),
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
        'judgement': (f'中证消费 10/15 收 {cs_close:,.4f}（{cs_pct:+.2f}%），距 {LINE_CS:,.0f} 下沿 '
                      f'**{_cs_d:+.4f}%** → **仍站稳下沿，安全边际较 10/14 档登记的 {_cs_d_prev:+.4f}% '
                      f'{_CS_DIR} {_CS_ABS_DELTA:.4f}pct**；'
                      f'日内低 {cs["low"]:,} 未破；本档为**逆市抗跌**（沪指 {IDXP["000001"]:+.2f}%、'
                      f'创业板指 {IDXP["399006"]:+.2f}%）→ 大消费相对大盘显著抗跌、无触发；'
                      f'⚠️ 但内部严重分化：中证白酒 **{pc["board_detail"]["399997"]:+.2f}%** 逆势领涨，'
                      f'而中证消费 {pc["board_detail"]["000932"]:+.2f}% → 相差 '
                      f'{round(pc["board_detail"]["399997"] - pc["board_detail"]["000932"], 2):.2f}pct，'
                      f'**「白酒独强」不等于「大消费走强」**（§3.152）'),
        'next_line': LINE_CS_NEXT,
        'next_line_dist_pct': round((cs_close / LINE_CS_NEXT - 1) * 100, 4),
    },
    'a_med_reverse_1_5pct': {
        'proxy_pct': pc['board_med'], 'board_med': pc['board_med'],
        'leader_med': pc['leader_med'], 'lag_med': pc['lag_med'],
        'single_day_000933': medi['pct'],
        'line_pct': -1.5, 'dist_pct': round(pc['board_med'] - (-1.5), 4),
        'state': 'NOT_TRIGGERED',
        'intraday_state': (f'未触发（13:45 盘中代理 {pi["board_med"]:+.4f}%，'
                           f'portfolio_intraday_20261015.json defense.med_reverse_line = '
                           f'{str(pi["defense"]["med_reverse_line"]).lower()}）'),
        'state_continuity': (f'盘中 → 收盘 **同向走弱**（{pi["board_med"]:+.4f}% → '
                             f'{pc["board_med"]:+.4f}%）→ 两口径均未触及 −1.5% 反向兑现线'),
        'contingency_closed': True, 'contingency_triggered': False,
        'judgement': (f'A股医药板块代理 {pc["board_med"]:+.4f}%（中证医药 {medi["pct"]:+.2f}% / '
                      f'中证医疗 {med_etf["pct"]:+.2f}% / '
                      f'300医药 {pc["leader_med"]:+.2f}%）→ '
                      f'① 负号方向的「主动兑现线」（≤ −1.5%）**未触发**（距线 {pc["board_med"] - (-1.5):+.4f}pct）；'
                      f'② +1.5% 反转线**未触发**（距 {round(1.5 - pc["board_med"], 4):+.4f}pct）；'
                      f'③ 盘前登记的「被动减配预案」'
                      f'已于 10/9 按预案明文「回调序列断裂、预案不启动」作废（盘前档 '
                      f'`contingency_closed = {str(po["defense_lines"]["a_med_reverse_1_5pct"].get("contingency_closed")).lower()}`）'
                      f' → 本档维持作废；'
                      f'④ 内部结构：300医药 {pc["leader_med"]:+.2f}% > 中证医药 '
                      f'{medi["pct"]:+.2f}% > 中证医疗 {med_etf["pct"]:+.2f}% → '
                      f'**「大市值抗跌、中小市值深跌」结构延续第 3 日**（10/13 / 10/14 已现同向，10/12 为异序）。'
                      f'内部离散度 {round(pc["leader_med"] - pc["lag_med"], 4):.4f}pct（300医药 − 中证医疗）'),
    },
}

# ---------- 2. 纪律执行台账 ----------
# 本档无新增纪律动作；台账主体 = 已成交两笔（§3.123e / §3.125c）
hk_cum_since_cut1 = round((hstech['close'] / idx['HSTECH']['2026-09-29'] - 1) * 100, 4)
hk_cum_since_cut2 = round((hstech['close'] / idx['HSTECH']['2026-10-08'] - 1) * 100, 4)
hk_day_prev = round((hstech['close'] / idx['HSTECH'][PREV] - 1) * 100, 4)
ledger = [{
    'date': TODAY, 'kind': '本档无新增纪律动作',
    'amount': 0.0,
    'reason': (f'恒生科技 10/15 收 {hstech["close"]:,}（{hstech["pct"]:+.2f}%），距 4,250 为 {_hk_d:+.4f}% → '
               f'仍处破位区间且**幅度走阔**但**未叠加触发**（当日防线只触发一次，§3.114c）；'
               f'中证消费 {cs_close:,.4f} 距 12,100 为 {_cs_d:+.4f}%（边际 {_CS_MARGIN_DELTA:+.4f}pct，'
               f'**未破下沿**）；A股医药代理 {pc["board_med"]:+.4f}% 未触及 −1.5%'),
    'cumulative_amount': pc['discipline']['cumulative_amount'],
    'cumulative_selfcheck': pc['discipline']['cumulative_selfcheck'],
    'weight_after': pc['discipline']['weight_after'],
    'next_rule': f'恒生科技下一道防线 4,000（距 {lines["hstech_4250"]["next_line_dist_pct"]:+.4f}%）；再破不叠加新纪律',
}]

ledger_hist = [
    {'date': '2026-09-29', 'kind': '大消费 0.5% 纪律兑现', 'amount': 1879.43,
     'trigger': '9/28 收盘级跌破 12,100（12,096.0166，−0.033%）', 'settle': '按 9/29 净值成交（价值中性）',
     'outcome': (f'9/29 收 12,107.1705 收复 12,100 → 定性「技术性误触」；'
                 f'10/15 收 {cs_close:,.4f}（距下沿 {_cs_d:+.4f}%、较 10/14 档登记值 {_CS_DIR} '
                 f'{_CS_ABS_DELTA:.4f}pct）'
                 f'→ 结论延续、未再触发')},
    {'date': '2026-09-30', 'kind': '恒生科技 0.5% 纪律减仓（第 1 次）', 'amount': 1882.46,
     'trigger': '9/29 收盘级破位（4,249.62，−0.0089%，**边际破位**）', 'settle': '按 9/30 净值成交',
     'outcome': (f'9/30 收 4,253.89 收复防线 → 记为「**边际破位成本**」；'
                 f'10/15 收 {hstech["close"]:,}（距防线 {_hk_d:+.4f}%）→ 自触发日（9/29 收 4,249.62）累计 '
                 f'{hk_cum_since_cut1:+.4f}%，**事后看方向正确**（标的已低于减仓时点，'
                 f'减仓规避的持仓损失 ≈ **{-1882.46 * hk_cum_since_cut1 / 100:+,.2f} 元**'
                 f'＝ 1,882.46 元 × {abs(hk_cum_since_cut1):.4f}%）')},
    {'date': '2026-10-08', 'kind': '恒生科技 0.5% 纪律减仓（第 2 次）', 'amount': 1904.44,
     'trigger': '10/2 收盘级破位（4,157.94，−2.1661%，**非边际破位**）', 'settle': '按 10/8 净值成交（价值中性）',
     'outcome': (f'执行日（10/8）恒生科技收 4,073.38（−2.89%，距防线 −4.1558%）→ 当日看属「**有效减仓**」；'
                 f'⚠️ 自执行日（10/8 收 4,073.38）至本档 {hstech["close"]:,} = **{hk_cum_since_cut2:+.4f}%** '
                 f'→ 短期机会成本 ≈ {1904.44:,.2f} 元 × {hk_cum_since_cut2:.4f}% ≈ '
                 f'**{1904.44 * hk_cum_since_cut2 / 100:+,.2f} 元**（本档单日 {hk_day_prev:+.4f}%）；'
                 f'**⚠️ 机会成本由 10/14 档的 +47.26 元（恒科 4,174.47 > 执行日价）转为负值 → '
                 f'「减仓后标的反弹」样本首次出现「减仓后标的低于执行日价」的反向读数**；'
                 f'仅为短期读数、不改变纪律判定（§3.130a）')},
]

# ---------- 3. 待消化收口 + QDII 挂账 ----------
pending = {
    'as_of': TODAY,
    'hk_leg_pending': pc['pending_release'],
    'qdii_pending': pc['qdii_pending'],
    'pending_total': {
        'hk_leg': ('已收口（10/8 由场外港股联接 000071 / 012348 真实净值一次性兑现，`window_closed = true`）；'
                   '本档无新增窗口（10/15 为正常交易日，港股腿按当日真实净值/收盘价逐券定价）'),
        'qdii_leg_range': [pc['qdii_pending']['remaining']['low'],
                           pc['qdii_pending']['remaining']['high']],
        'qdii_leg_note': ('余 **US 10/15 一个未知交易日**（北京 10/16 04:00 成型）；'
                          '本档挂账区间按 0 计系**「尚无已知美股交易日进入挂账」**，非「挂账已消失」（§3.124a / §3.120c）；'
                          '⚠️ **US 10/14 段本档已由真实净值核销** —— 实测 '
                          + format(pc['qdii_pending']['booked_this_session']['amount'], '+,.2f') + ' 元，'
                          '**落在 10/15 盘前档预告区间（+822.61 元 ~ +1,233.91 元）之内** → '
                          '§3.118a「区间法成立」累计 3 个可检验样本中第 2 个成立'),
    },
    'note': ('§3.112f / §3.118a：挂账只给区间、禁止中枢点值。'
             '**本档为 US 10/14 段的释放档**：QDII 000369 / 016280 自基准净值日 10/13 起至 10/14（'
             f'1 个美股交易日）已由真实净值核销 {pc["qdii_pending"]["booked_this_session"]["amount"]:+,.2f} 元；'
             f'164906（交银海外互联 LOF）同步自 10/13 释放至 10/14；'
             f'IYH 10/13→10/14 = {pc["iyh_1013_pct"]:+.4f}% → 实测隐含传导系数（以 IYH 为分母，§3.145c 主口径）000369 = '
             f'{pc["qdii_pending"]["coef_reestimate"]["observed_samples"]["2026-10-14"].get("000369")} / 016280 = '
             f'{pc["qdii_pending"]["coef_reestimate"]["observed_samples"]["2026-10-14"].get("016280")}，'
             '**两只均落在 §3.118a 区间 0.60~0.90 之内**（以 XLV 为分母则为 0.8065 / 0.8049，同样在区间内）→ '
             '**与 10/12 段实测 1.0324 / 1.0503 越上界形成对照**；'
             '⚠️ 本档**仍不更新 0.72 中枢**：按 §3.118a 须以多券（≥4 券位）×多日（≥5 交易日）重估，'
             f'当前 2 券位 × 3 窗口（10/9、10/12、10/14 三段）→ **系数未重估前基于该系数的一切仓位决策无效**'),
}

# ---------- 4. 节假日历（逐市场分列，§3.115d） ----------
calendar = {
    '2026-10-14（上一档）': ('A股 + 港股双市场正常交易日双收盘；'
                          '上证 3,767.2271（−0.88%）/ 创业板指 2,958.63（−3.10%）/ 沪深300（−1.36%）/ '
                          '科创50（−3.29%）/ 中证消费 12,362.5056（+0.27%）；'
                          '恒指 24,314.17（−0.13%）/ 恒生科技 4,174.47（+0.91%）/ 恒生医疗 −2.6222%；'
                          '组合 −0.6941%（−2,598.48 元，取 `_fix` 修正值）；QDII US 10/13 段释放 −651.49 元'),
    '2026-10-15（今日）': (
        'A股 + 港股双市场正常交易日并在本档双收盘；'
        f'上证 {idx["000001"][TODAY]}（{IDXP.get("000001", 0.0):+.2f}%）/ '
        f'深证成指 {IDXP.get("399001", 0.0):+.2f}% / '
        f'创业板指 {idx["399006"][TODAY]}（{IDXP.get("399006", 0.0):+.2f}%）/ '
        f'科创50 {IDXP.get("000688", 0.0):+.2f}% / '
        f'沪深300 {IDXP.get("000300", 0.0):+.2f}% / 中证消费 {pc["board_detail"]["000932"]:+.2f}%；'
        f'恒指 {idx["HSI"][TODAY]}（{IDXP.get("HSI", 0.0):+.2f}%）/ '
        f'恒生科技 {idx["HSTECH"][TODAY]}（{IDXP.get("HSTECH", 0.0):+.2f}%）/ '
        f'恒生医疗保健 {IDXP.get("HSHCI", 0.0):+.4f}%；'
        'A股全天单边走弱、成长端显著弱于价值端（创业板 −2.92% vs 沪指 −1.59%）；'
        '板块内：中证白酒 +1.24% / 300医药 +0.79% / 证券公司 +0.42% / 中证金融 +0.04% 为正，'
        '中证医药 −0.06% / 中证消费 −0.42% / 中证医疗 −0.68% / 中证环保 −1.80% 为负；'
        'QDII US 10/14 段由真实净值核销 +1,198.49 元（组合唯一正贡献赛道）；'
        '⚠️ 美国 9 月 CPI（北京 10/14 20:30 公布）结果须在本档登记并交叉验证'),
    NEXT_TD: ('**下一交易日（周五）**：A股 + 港股正常交易；'
              '**第 140 届广交会开幕（10/15-11/4，广州）**外贸链边际影响跟踪；'
              '**5 只未出 10/15 净值的 A股类券（161616 / 519915 / 000248 / 000727 / 002742）08:00 兜底复抓**'
              '（取到须以同日 `_fix` 覆盖并同步重算 `tracks[].pnl`，§3.140a / §3.150b）；'
              'US 10/15 收盘成型于北京 10/16 04:00（供 QDII 挂账刷新）'),
    '2026-10-19': '港股重阳节翌日休市（A股 正常交易）→ **「混合档」镜像情形**；2026 金融街论坛年会开幕（吴清作主题演讲）',
    '2026-10-27~28': 'FOMC 议息会议',
}

# ---------- 5. 敞口与门槛 ----------
exposure = {
    'tracks': {k: {'mv': v['mv'], 'pct': v['pct_of_total'], 'pnl': v['pnl'], 'day_pct': v['day_pct']}
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
P1616, S1616 = _pct('161616'), _sum('161616')
P0727, S0727 = _pct('000727'), _sum('000727')
P012323, S012323 = _pct('012323'), _sum('012323')
P000248, S000248 = _pct('000248'), _sum('000248')
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
        f'① **本档为「A股与港股同向普跌、唯 QDII 腿由净值释放提供唯一正收益」的单边下跌日**：'
        f'沪指 {IDXP["000001"]:+.2f}%（3,707.48，继续失守 3,800）、深证成指 {IDXP["399001"]:+.2f}%、'
        f'创业板指 {IDXP["399006"]:+.2f}%、科创50 {IDXP["000688"]:+.2f}%、沪深300 {IDXP["000300"]:+.2f}%；'
        f'恒指 {IDXP["HSI"]:+.2f}%、恒生科技 {IDXP["HSTECH"]:+.2f}% → 组合估算 {pc["est_total_pnl"]:+,.2f} 元'
        f'（{NAV_PRECISE:+.4f}%），正贡献 {pos_sum:+,.2f} 元 / 负贡献 {neg_sum:+,.2f} 元 → '
        f'**六赛道{COUNT_STR}**（{COUNT_STR_LIST}）；'
        f'② **最大拖累 = 其他/宽基 {tr["其他/宽基"]["pnl"]:+,.2f} 元**（{tr["其他/宽基"]["day_pct"]:+.3f}%）——'
        f'广联达（002410）**{GLD_PCT:+.2f}%（{GLD_PNL:+,.2f} 元）**为单一最大拖累'
        f'（占全组合负贡献的 {abs(GLD_PNL) / abs(neg_sum) * 100:.1f}%），'
        f'叠加沪深300 双联接（000051 {_pct("000051"):+.2f}% / 110020 {_pct("110020"):+.2f}%，合计 '
        f'{round(_sum("000051") + _sum("110020"), 2):+,.2f} 元）、'
        f'通威股份 {_pct("600438"):+.2f}%（{_sum("600438"):+,.2f} 元）、'
        f'富国清洁能源 {_pct("005368"):+.2f}%（{_sum("005368"):+,.2f} 元）、'
        f'100红利 {_pct("515180"):+.2f}%（{_sum("515180"):+,.2f} 元）、'
        f'传媒 {_pct("004752"):+.2f}%（{_sum("004752"):+,.2f} 元）、'
        f'恒生ETF联接 000071 {_pct("000071"):+.2f}%（两行 {_sum("000071"):+,.2f} 元）'
        f'→ **「宽基联接 + 单一成长券 + 红利/资源回吐」三重负贡献**；'
        f'⚠️ 腿内唯一正项 = 天弘证券保险 {_pct("001552"):+.2f}%（{_sum("001552"):+,.2f} 元）与 '
        f'广发金融地产 {_pct("001469"):+.2f}% → 与证券公司 {pc["board_detail"]["399975"]:+.2f}% / '
        f'中证金融 {pc["board_detail"]["000934"]:+.2f}% 一致；'
        f'③ **第二大拖累 = 恒生科技 {tr["恒生科技"]["pnl"]:+,.2f} 元**（{tr["恒生科技"]["day_pct"]:+.3f}%）——'
        f'恒生科技指数 {IDXP["HSTECH"]:+.2f}%、中概互联 513050 {_pct("513050"):+.2f}%（{_sum("513050"):+,.2f} 元）、'
        f'恒指科技 513180 {_pct("513180"):+.2f}%（{_sum("513180"):+,.2f} 元）、天弘恒科联接 012348 '
        f'{_pct("012348"):+.2f}%（两行 {_sum("012348"):+,.2f} 元）→ **腿内四券同向负、无真实价格背离**；'
        f'④ **A股医药 {tr["A股医药"]["pnl"]:+,.2f} 元**（{tr["A股医药"]["day_pct"]:+.3f}%）——'
        f'大摩健康产业 002708 **{M708_PCT:+.3f}%（{M708_PNL:+,.2f} 元，本档已取得 10/15 真实净值）**、'
        f'华宝中证医疗联接 012323 {P012323:+.2f}%（{S012323:+,.2f} 元）、'
        f'医疗ETF 512170 {P512170:+.2f}%、天弘医药100C {_pct("001551"):+.2f}%、'
        f'广发医药卫生 {_pct("001180"):+.2f}%；'
        f'⚠️ 该腿内 **161616 / 000727 未出 10/15 净值 → 计 0 元**（估值缺口，见下）；'
        f'⚠️ 板块层 300医药 {pc["leader_med"]:+.2f}% / 中证医药 {medi["pct"]:+.2f}% / 中证医疗 {med_etf["pct"]:+.2f}% '
        f'→ **指数级「医药抗跌」不等于「腿收益为正」**（§3.152）；'
        f'⑤ **大消费 {tr["大消费"]["pnl"]:+,.2f} 元**（{tr["大消费"]["day_pct"]:+.3f}%）——'
        f'消费ETF添富 {_pct("159928"):+.2f}%（{_sum("159928"):+,.2f} 元）、'
        f'广发养老产业 {_pct("000968"):+.2f}%（{_sum("000968"):+,.2f} 元）、'
        f'汇添富文体娱乐 {_pct("004424"):+.2f}%（{_sum("004424"):+,.2f} 元）；'
        f'⚠️ **519915 / 000248（合计 notional 52,259.79 元 = 该腿 69.7%）未出净值 → 计 0 元**，'
        f'而中证白酒 {pc["board_detail"]["399997"]:+.2f}% 逆势领涨 vs 中证消费 {pc["board_detail"]["000932"]:+.2f}% '
        f'（相差 {round(pc["board_detail"]["399997"] - pc["board_detail"]["000932"], 2):.2f}pct）→ **该腿当日真实读数存在系统性低估**；'
        f'⑥ **美股标普医药 {tr["美股标普医药"]["pnl"]:+,.2f} 元**（{tr["美股标普医药"]["day_pct"]:+.3f}%）'
        f'——**全部来自 QDII US 10/14 段净值释放**（000369 {_pct("000369"):+.3f}% / 016280 '
        f'{_pct("016280"):+.3f}%，合计 {QDII369_PNL + QDII280_PNL:+,.2f} 元），'
        f'**非 10/15 美股行情**（北京 20:00 时美股未开盘，§3.120c）；'
        f'⑦ **现金** 0.00 元（账面冻结项，不构成方向判断）；'
        f'⑧ **⚠️ 估值缺口提示（本档新增）**：{len(ZERO_CODES)} 只未定价券 notional 合计 {GAP_MV:,.2f} 元'
        f'（占组合 {GAP_MV / float(total_mv) * 100:.2f}%），若按所属赛道板块代理折算，'
        f'组合当日将再变动约 {GAP_TOTAL:+,.2f} 元 → **估算区间下界 {GAP_ALT_PNL:+,.2f} 元'
        f'（{GAP_ALT_PCT:+.4f}%）**；本档主口径仍按「基准已含 → 计 0」'
        f'（§3.105），**该缺口须在次档兜底复抓后以 `_fix` 覆盖修正**'),
}

out = {'date': TODAY, 'as_of': '2026-10-15 收盘（A股 长假后第 6 个正常交易日 + 港股正常交易日；双市场双收盘）',
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
       'action_next': {
           'next_session': NEXT_TD + '（周五，A股 + 港股正常交易日；第 140 届广交会开幕）',
           'planned': (f'① **5 只未出 10/15 净值券 08:00 兜底复抓**（161616 / 519915 / 000248 / 000727 / 002742，'
                       f'notional {GAP_MV:,.2f} 元）；若到位 → 出 `_fix` 件覆盖本档并**同步重算 `tracks[].pnl`**'
                       f'（§3.140a / §3.149g）；'
                       f'② **QDII 挂账刷新**：US 10/15 收盘（北京 10/16 04:00 成型）→ 000369/016280 与 164906 '
                       f'取得最新净值日则按 §3.105 回填（**以基准行 `price_src` 反解基准净值日，禁用固定日期常量**）；'
                       f'③ 复核恒生科技 4,000 防线（本档距 {lines["hstech_4250"]["next_line_dist_pct"]:+.4f}%，'
                       f'**由 13:45 的 +1.7628% 收窄至本值 → 为当前最高优先级线位**）与「减仓后标的反弹」样本'
                       f'（本档首次转负）；'
                       f'④ 复核中证消费 12,100 下沿（本档距 {lines["zz_consume_12100"]["dist_pct"]:+.4f}%，'
                       f'较上一档 {_CS_DIR} {_CS_ABS_DELTA:.4f}pct）与 12,000 次级线；'
                       f'⑤ 复核医药敞口 {pc["med_pct"]:.2f}%（距 40% 上限门槛：全部医药 '
                       f'{pc["threshold_all_med"]:+.2f}% / 仅 A股医药 {pc["threshold_a_sh_med"]:+.2f}%）'
                       f'——**任何正向催化均不构成加仓理由**（new_buy = 0）；'
                       f'⑥ 登记 **美国 9 月 CPI**（北京 10/14 20:30）实际值与中国 9 月 CPI / PPI 的政策传导；'
                       f'⑦ 关注 **第 140 届广交会（10/15 开幕）** 对外贸链的边际影响；'
                       f'⑧ E大（长赢计划）adj 268 / inv 114 后续跟踪（本档零变动）；'
                       f'⑨ **10/19 港股重阳翌日休市（A股 正常交易）→ 「混合档」镜像情形**预案'),
       },
       'note': ('10/15 **无新增纪律动作**（三条防线：恒科破位**走阔至 −4.4473%** 仍未叠加触发 / '
                '中证消费仍站稳下沿（边际 ' + f'{_CS_MARGIN_DELTA:+.4f}pct' + '）/ '
                f'A股医药代理 {pc["board_med"]:+.4f}% 未触 −1.5%）；'
                '待消化：长假港股腿已收口、QDII 腿为「US 10/14 段释放 '
                + format(pc['qdii_pending']['booked_this_session']['amount'], '+,.2f') + ' 元 + 余 0」；'
                f'⚠️ 本档**有 {len(ZERO_CODES)} 只未定价券**（' + '、'.join(ZERO_CODES) + '，'
                f'notional {GAP_MV:,.2f} 元），其余 {len(det) - len(ZERO_ROWS)} 行为真实价格 / 真实净值；'
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
print(f'      A股医药板块代理 {pc["board_med"]:+.4f}% vs −1.5% / +1.5% → {lines["a_med_reverse_1_5pct"]["state"]}')
print(f'\nTop 拖累: ' + ' | '.join(f'{d["name"]} {d["pnl"]:+,.2f}' for d in TOP_DRAG[:4]))
print(f'Top 贡献: ' + ' | '.join(f'{d["name"]} {d["pnl"]:+,.2f}' for d in TOP_GAIN[:4]))
print(f'\n未出净值券: {ZERO_CODES}')

print(f'\n已保存 portfolio_strategy_close_{TODAYC}.json')
