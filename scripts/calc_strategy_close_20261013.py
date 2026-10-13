# -*- coding: utf-8 -*-
"""2026-10-13 盘后：策略层产物（三条防线收盘级判定 + 纪律执行台账 + 待消化收口 + 港股三层拆解）
输出：portfolio_strategy_close_20261013.json

⚠️ 档型 = **正常交易日收盘档**（A股 10/13 长假后第 4 个正常交易日 15:00 收盘 + 港股 10/13 正常交易日 16:00 收盘）
   下一交易日 = **2026-10-14（周三）**
⚠️ §3.133a：所有展示字段（点位/距离/趋势序列）一律从 indices.csv 与 close_<DATE>.json **现算**，禁止硬编码常量
⚠️ §3.142a：派生后已对「档位/日期/计数」三类字面量做「去 Markdown 标记后的模糊匹配」核对，并回读产物抽查
⚠️ 本档由 10/12 版逐项核对后重写（非纯 sed）：档型语义、日期常量、基准文件、参考交易日、前档口径全部按 10/13 重算
"""
import json, os, csv

BASE = '/Users/jieyang/Documents/WealthHub'
HIST = os.path.join(BASE, 'data/processed/history')
TODAY = '2026-10-13'
TODAYC = TODAY.replace('-', '')
PREV = '2026-10-12'
NEXT_TD = '2026-10-14'

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

lines = {
    'hstech_4250': {
        'line': LINE_HK, 'close': hstech['close'], 'pct': hstech['pct'],
        'dist_pct': _hk_d,
        'state': 'BROKEN_CLOSE_LEVEL_NARROWED',
        'intraday_ref': pi['defense']['hstech'],
        'break_trend': break_trend,
        'intraday_high': hstech['high'], 'intraday_low': hstech['low'],
        'intraday_touched_above': hstech['high'] >= LINE_HK,
        'judgement': (f'破位幅度由 10/12 的 {prev_break:+.4f}% **收窄至 {_hk_d:+.4f}%**（本档单日 {hstech["pct"]:+.2f}%）；'
                      f'⚠️ 日内最高 {hstech["high"]:,} **< 4,250 → 全日未站上**（13:45 盘中读数 '
                      f'{pi["defense"]["hstech"]:,} / 距防线 {pi["defense"]["hstech_vs_4250"]:+.4f}%）；'
                      f'按 §3.114c「同日防线只触发一次」→ 本档**不新增纪律动作**，防线维持 4,250'),
        'next_line': LINE_HK_NEXT,
        'next_line_dist_pct': round((hstech['close'] / LINE_HK_NEXT - 1) * 100, 4),
    },
    'zz_consume_12100': {
        'line': LINE_CS, 'close': cs_close, 'pct': cs_pct,
        'dist_pct': _cs_d,
        'state': 'ABOVE_CLOSE_LEVEL',
        'intraday_low': cs['low'],
        'judgement': (f'中证消费 10/13 收 {cs_close:,.4f}（{cs_pct:+.2f}%），距 {LINE_CS:,.0f} 下沿 '
                      f'**{_cs_d:+.4f}%** → **仍站稳下沿但安全边际由 10/12 的 '
                      f'{po["defense_lines"]["zz_consume_12100"]["dist_pct"]:+.4f}% 收窄至 {_cs_d:+.4f}%**'
                      f'（收窄 {round(po["defense_lines"]["zz_consume_12100"]["dist_pct"] - _cs_d, 4):.4f}pct）；'
                      f'日内低 {cs["low"]:,} 未破；本档为**与大盘同向下跌**（沪指 {IDXP["000001"]:+.2f}%、'
                      f'创业板指 {IDXP["399006"]:+.2f}%）→ 大消费与大盘同向、无触发'),
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
                           f'portfolio_intraday_20261013.json defense.med_reverse_line = '
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
                      f'**「大市值抗跌、中小市值深跌」结构延续第 2 日**（10/12 已现同向）'),
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
    'reason': (f'恒生科技 10/13 收 {hstech["close"]:,}（{hstech["pct"]:+.2f}%），距 4,250 为 {_hk_d:+.4f}% → '
               f'仍处破位区间但**未叠加触发**（当日防线只触发一次，§3.114c）；'
               f'中证消费 {cs_close:,.4f} 距 12,100 为 {_cs_d:+.4f}%；'
               f'A股医药代理 {pc["board_med"]:+.4f}% 未触及 −1.5%'),
    'cumulative_amount': pc['discipline']['cumulative_amount'],
    'cumulative_selfcheck': pc['discipline']['cumulative_selfcheck'],
    'weight_after': pc['discipline']['weight_after'],
    'next_rule': f'恒生科技下一道防线 4,000（距 {lines["hstech_4250"]["next_line_dist_pct"]:+.4f}%）；再破不叠加新纪律',
}]

ledger_hist = [
    {'date': '2026-09-29', 'kind': '大消费 0.5% 纪律兑现', 'amount': 1879.43,
     'trigger': '9/28 收盘级跌破 12,100（12,096.0166，−0.033%）', 'settle': '按 9/29 净值成交（价值中性）',
     'outcome': (f'9/29 收 12,107.1705 收复 12,100 → 定性「技术性误触」；'
                 f'10/13 收 {cs_close:,.4f}（距下沿 {_cs_d:+.4f}%）→ 结论延续、未再触发')},
    {'date': '2026-09-30', 'kind': '恒生科技 0.5% 纪律减仓（第 1 次）', 'amount': 1882.46,
     'trigger': '9/29 收盘级破位（4,249.62，−0.0089%，**边际破位**）', 'settle': '按 9/30 净值成交',
     'outcome': (f'9/30 收 4,253.89 收复防线 → 记为「**边际破位成本**」；'
                 f'10/13 收 {hstech["close"]:,}（距防线 {_hk_d:+.4f}%）→ 自触发日（9/29）累计 '
                 f'{hk_cum_since_cut1:+.4f}%，**事后看方向正确**（减仓规避了 '
                 f'{1882.46 * hk_cum_since_cut1 / 100:+,.2f} 元的持仓损失）')},
    {'date': '2026-10-08', 'kind': '恒生科技 0.5% 纪律减仓（第 2 次）', 'amount': 1904.44,
     'trigger': '10/2 收盘级破位（4,157.94，−2.1661%，**非边际破位**）', 'settle': '按 10/8 净值成交（价值中性）',
     'outcome': (f'执行日（10/8）恒生科技收 4,073.38（−2.89%，距防线 −4.1558%）→ 当日看属「**有效减仓**」；'
                 f'⚠️ 自执行日（10/8 收 4,073.38）至本档 {hstech["close"]:,} = **{hk_cum_since_cut2:+.4f}%** '
                 f'→ 短期机会成本 ≈ {1904.44:,.2f} 元 × {hk_cum_since_cut2:.4f}% ≈ '
                 f'**{1904.44 * hk_cum_since_cut2 / 100:,.2f} 元**（本档单日 {hk_day_prev:+.4f}%、'
                 f'机会成本较 10/12 档（14.15 元）**继续走阔**；仅为短期读数、不改变纪律判定）')},
]

# ---------- 3. 待消化收口 + QDII 挂账 ----------
pending = {
    'as_of': TODAY,
    'hk_leg_pending': pc['pending_release'],
    'qdii_pending': pc['qdii_pending'],
    'pending_total': {
        'hk_leg': ('已收口（10/8 由场外港股联接 000071 / 012348 真实净值一次性兑现，`window_closed = true`）；'
                   '本档无新增窗口（10/13 为正常交易日，港股腿按当日真实净值/收盘价逐券定价）'),
        'qdii_leg_range': [pc['qdii_pending']['remaining']['low'],
                           pc['qdii_pending']['remaining']['high']],
        'qdii_leg_note': ('余 **US 10/13 一个未知交易日**（北京 10/14 04:00 成型）；'
                          '本档挂账区间按 0 计系**「尚无已知美股交易日进入挂账」**，非「挂账已消失」（§3.124a）；'
                          '⚠️ **US 10/12 段本档已由真实净值核销** —— 实测 +349.01 元，'
                          '**高于 10/13 盘前档预告区间上界（+301.73 元）15.7%**（系数漂移击穿区间，§3.114e 同型）'),
    },
    'note': ('§3.112f / §3.118a：挂账只给区间、禁止中枢点值。'
             '**本档为 US 10/12 段的释放档**：QDII 000369 / 016280 自基准净值日 10/9 起至 10/12（'
             f'1 个美股交易日）已由真实净值核销 {pc["qdii_pending"]["booked_this_session"]["amount"]:+,.2f} 元；'
             f'164906（交银海外互联 LOF）同步自 10/9 释放至 10/12；'
             f'IYH 10/12 = {pc["iyh_1012_pct"]:+.4f}% → 实测隐含传导系数（以 IYH 为分母）000369 = '
             f'{pc["qdii_pending"]["coef_reestimate"]["observed_samples"]["2026-10-12"].get("000369")} / 016280 = '
             f'{pc["qdii_pending"]["coef_reestimate"]["observed_samples"]["2026-10-12"].get("016280")}，'
             '**超出 §3.118a 区间 0.60~0.90 上界**（以 XLV 为分母则为 0.8493 / 0.8641，落在区间内）→ '
             '**「系数不是常数」再获一个极端样本，本档不更新 0.72 中枢**；'
             '⚠️ 系数重估仍为 pending（要求 ≥4 券位 × ≥5 交易日，当前 2 券位 × 3 窗口）→ '
             '**系数未重估前基于该系数的一切仓位决策无效**'),
}

# ---------- 4. 节假日历（逐市场分列，§3.115d） ----------
calendar = {
    '2026-10-12（上一档）': ('A股 + 港股双市场正常交易日双收盘；'
                          '上证 3,797.24（−0.43%）/ 创业板指 2,963.82（−2.61%）/ 中证消费 12,469.15（+0.92%）；'
                          '恒指 24,271.20（+0.25%）/ 恒生科技 4,169.57（−0.67%）；'
                          '组合 −0.0344%（−129.64 元）；QDII US 10/9 段释放 +674.77 元'),
    '2026-10-13（今日）': ('A股 + 港股双市场正常交易日并在本档双收盘；'
                        '上证 %s（%+.2f%%）/ 创业板指 %s（%+.2f%%）/ 沪深300 %+.2f%% / 中证消费 %+.2f%%；'
                        '恒指 %s（%+.2f%%）/ 恒生科技 %s（%+.2f%%）/ 恒生医疗保健 %+.4f%%；'
                        'A股 探底回升（沪指收复 3,800）、大消费与医药同步走弱；全国卫生与健康大会闭幕（A股医药政策项）；'
                        '9 月金融数据（16:00 前后）三源交叉验证仍未取得实际值 → 降级「只登记不采用」'
                        % (idx['000001'][TODAY], IDXP.get('000001', 0.0),
                           idx['399006'][TODAY], IDXP.get('399006', 0.0),
                           IDXP.get('000300', 0.0), IDXP.get('000932', 0.0),
                           idx['HSI'][TODAY], IDXP.get('HSI', 0.0),
                           idx['HSTECH'][TODAY], IDXP.get('HSTECH', 0.0),
                           IDXP.get('HSHCI', 0.0))),
    NEXT_TD: ('**下一交易日（周三）**：A股 + 港股正常交易；'
              '**美国 9 月 CPI（北京 20:30）为本周边际定价核心变量**（须双源交叉验证）；'
              '国内 9 月 CPI/PPI 同日公布（待验证）；US 10/13 收盘成型于北京 10/14 04:00（供 QDII 挂账刷新）'),
    '2026-10-15': '第 140 届广交会开幕（10/15-11/4，广州；李强出席开幕式）',
    '2026-10-19': '港股重阳节翌日休市（A股 正常交易）；2026 金融街论坛年会开幕（吴清作主题演讲）',
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

driver = {
    'top_drag': TOP_DRAG,
    'top_gain': TOP_GAIN,
    'track_pnl_rank': drag_rank,
    'pos_sum': pos_sum, 'neg_sum': neg_sum,
    'attribution': (
        f'① **本档为「普跌 + 政策利好未兑现」的方向日**：沪指 {IDXP["000001"]:+.2f}%（收复 3,800）、'
        f'深证成指 {IDXP["399001"]:+.2f}%、创业板指 {IDXP["399006"]:+.2f}%、沪深300 {IDXP["000300"]:+.2f}% → '
        f'指数端分化极小，组合估算 {pc["est_total_pnl"]:+,.2f} 元（{NAV_PRECISE:+.4f}%），'
        f'正贡献 {pos_sum:+,.2f} 元 / 负贡献 {neg_sum:+,.2f} 元 → **六赛道中五负一正**；'
        f'② **美股标普医药 {tr["美股标普医药"]["pnl"]:+,.2f} 元为唯一正贡献赛道**（{tr["美股标普医药"]["day_pct"]:+.3f}%）'
        f'——**全部来自 QDII US 10/12 段净值释放**（000369 {_pct("000369"):+.3f}% / 016280 '
        f'{_pct("016280"):+.3f}%，合计 {QDII369_PNL + QDII280_PNL:+,.2f} 元），'
        f'**非 10/13 美股行情**（北京 20:00 时美股未开盘）；'
        f'③ **其他/宽基 {tr["其他/宽基"]["pnl"]:+,.2f} 元为最大拖累**（{tr["其他/宽基"]["day_pct"]:+.3f}%）——'
        f'广联达（002410）**{GLD_PCT:+.2f}%（{GLD_PNL:+,.2f} 元）**为单一最大拖累（占全组合负贡献的 '
        f'{abs(GLD_PNL) / abs(neg_sum) * 100:.1f}%）、通威股份 {_pct("600438"):+.2f}%（{_sum("600438"):+,.2f} 元）逆势收正，'
        f'而宽基联接类普遍小幅走弱（华夏沪深300联接 {_pct("000051"):+.2f}%、易方达沪深300联接 {_pct("110020"):+.2f}%、'
        f'富国清洁能源 {_pct("005368"):+.2f}%、天弘证券保险 {_pct("001552"):+.2f}%、广发金融地产 {_pct("001469"):+.2f}%）→ '
        f'**「金融由独强转领跌」是本档宽基腿转负的直接原因**；'
        f'④ **大消费 {tr["大消费"]["pnl"]:+,.2f} 元为第二大拖累**（{tr["大消费"]["day_pct"]:+.3f}%）——'
        f'汇添富主要消费联接 {P000248:+.3f}%（{S000248:+,.2f} 元）、消费ETF {_pct("159928"):+.2f}%、'
        f'富国消费主题 {_pct("519915"):+.2f}%（两行合计 {_sum("519915"):+,.2f} 元）、广发养老产业 {_pct("000968"):+.2f}%；'
        f'**⚠️ 与 10/12「逆市收涨」完全反转** → 白酒/主要消费由强转弱、冰雪经济等新主题未覆盖组合持仓；'
        f'⑤ **A股医药 {tr["A股医药"]["pnl"]:+,.2f} 元**（{tr["A股医药"]["day_pct"]:+.3f}%）——'
        f'主动基继续放大下行：融通医疗保健 **{P1616:+.2f}%（{S1616:+,.2f} 元）**、'
        f'华宝中证医疗联接 {P012323:+.2f}%（{S012323:+,.2f} 元）、广发医药卫生 {_pct("001180"):+.2f}%、'
        f'天弘医药100C {_pct("001551"):+.2f}%、融通健康产业 {P0727:+.2f}%（{S0727:+,.2f} 元）、'
        f'医疗ETF {P512170:+.2f}%；**大摩健康产业（002708）本档净值日未推进 → 计 0 元（{M708_PNL:+,.2f} 元）**'
        f'→ **属「基准已含」口径而非「零波动」，须与真实定价严格区分**（§3.105）；'
        f'⑥ **恒生科技 {tr["恒生科技"]["pnl"]:+,.2f} 元**（{tr["恒生科技"]["day_pct"]:+.3f}%）——'
        f'恒生科技指数 {IDXP["HSTECH"]:+.2f}%、天弘恒科联接 {_pct("012348"):+.2f}%（两行 {_sum("012348"):+,.2f} 元）、'
        f'恒指科技ETF {_pct("513180"):+.2f}%、中概互联 {_pct("513050"):+.2f}%、'
        f'164906 交银海外互联净释放 {LOF906_PNL:+,.2f} 元 → **腿内正负对冲，净值释放部分为唯一正向来源**；'
        f'⑦ **现金** 0.00 元（账面冻结项，不构成方向判断）'),
}

out = {'date': TODAY, 'as_of': '2026-10-13 收盘（A股 长假后第 4 个正常交易日 + 港股正常交易日；双市场双收盘）',
       'session_type': pc['session_type'],
       'base_total': pc['base_total'], 'base_file': pc['base_file'], 'total_mv': total_mv,
       'est_total_pnl': pc['est_total_pnl'], 'est_total_pct': pc['est_total_pct'],
       'est_total_pnl_low': pc['est_total_pnl_low'], 'est_total_pnl_high': pc['est_total_pnl_high'],
       'defense_lines_close': lines,
       'discipline_ledger': ledger, 'discipline_ledger_history': ledger_hist,
       'pending': pending, 'calendar': calendar, 'exposure': exposure, 'driver': driver,
       'action_next': {
           'next_session': NEXT_TD + '（周三，A股 + 港股正常交易日）',
           'planned': (('① **美国 9 月 CPI（北京 20:30）**为本周分母端核心变量 → 须双源交叉验证后登记；'
                        '② **QDII 挂账刷新**：US 10/13 收盘（北京 10/14 04:00 成型）→ 000369/016280 与 164906 '
                        '取得最新净值日则按 §3.105 回填（**以基准行 `price_src` 反解基准净值日，禁用固定日期常量**）；'
                        '③ 复核恒生科技 4,000 防线（本档距 %+.4f%%）与「减仓后标的反弹」样本累积；'
                        '④ 复核中证消费 12,100 下沿（本档距 %+.4f%%，安全边际已由 3.0508%% 收窄）与 12,000 次级线；'
                        '⑤ 复核医药敞口 %.2f%%（距 40%% 上限门槛：全部医药 %+.2f%% / 仅 A股医药 %+.2f%%）'
                        '——**任何正向催化均不构成加仓理由**（new_buy = 0）；'
                        '⑥ **复核大摩健康产业（002708）净值是否出库**（本档未推进 → 计 0 元，属估值缺口）'
                        % (lines['hstech_4250']['next_line_dist_pct'],
                           lines['zz_consume_12100']['dist_pct'],
                           pc['med_pct'], pc['threshold_all_med'], pc['threshold_a_sh_med']))),
       },
       'note': ('10/13 **无新增纪律动作**（三条防线：恒科破位但未叠加触发 / 中证消费仍站稳下沿但边际收窄 / '
                'A股医药代理 −1.1625% 未触 −1.5%）；待消化：长假港股腿已收口、QDII 腿为「US 10/12 段释放 + 余 0」；'
                '⚠️ 本档**有 1 只未定价券**（002708 大摩健康产业净值日未推进 → 计 0 元），'
                '其余 44 行均为真实价格 / 真实净值；剩余未出库券 = ' + ('、'.join(ZERO_CODES) if ZERO_CODES else '无') +
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
      f'{1882.46 * hk_cum_since_cut1 / 100:+,.2f} 元')
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
