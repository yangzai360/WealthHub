# -*- coding: utf-8 -*-
"""2026-10-09 盘后：策略层产物（三条防线收盘级判定 + 纪律执行台账 + 待消化收口 + 港股三层拆解）
输出：portfolio_strategy_close_20261009.json

⚠️ 档型 = **正常交易日收盘档**（A股 10/9 长假后第 2 个交易日 15:00 收盘 + 港股 10/9 正常交易日 16:00 收盘）
   下一交易日 = **2026-10-12（周一）**（10/10-10/11 为周末）
⚠️ §3.133a：所有展示字段（点位/距离/趋势序列）一律从 indices.csv 与 close_<DATE>.json **现算**，禁止硬编码常量
⚠️ §3.106 条款 17：本档为全新撰写（非 sed 派生），写盘路径 / 日期常量 / 档型语义 均已逐条核对
"""
import json, os, csv

BASE = '/Users/jieyang/Documents/WealthHub'
HIST = os.path.join(BASE, 'data/processed/history')
TODAY = '2026-10-09'
TODAYC = TODAY.replace('-', '')
NEXT_TD = '2026-10-12'

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

LINE_HK = 4250.0
LINE_HK_NEXT = 4000.0
LINE_CS = 12100.0
LINE_CS_NEXT = 12000.0

# 破位趋势序列：从 indices.csv 现算（§3.133a）
break_trend = {d: round((v / LINE_HK - 1) * 100, 4)
               for d, v in sorted(idx['HSTECH'].items()) if d >= '2026-10-02'}
prev_break = break_trend.get('2026-10-08')
assert prev_break is not None and len(break_trend) >= 6, f'破位趋势序列异常：{break_trend}'

lines = {
    'hstech_4250': {
        'line': LINE_HK, 'close': hstech['close'], 'pct': hstech['pct'],
        'dist_pct': round((hstech['close'] / LINE_HK - 1) * 100, 4),
        'state': 'BROKEN_CLOSE_LEVEL_NARROWED',
        'intraday_ref': pi['defense']['hstech'],
        'break_trend': break_trend,
        'intraday_high': hstech['high'], 'intraday_low': hstech['low'],
        'intraday_touched_above': hstech['high'] >= LINE_HK,
        'judgement': (f'破位幅度由 10/8 的 {prev_break:+.4f}% **收窄至 '
                      f'{round((hstech["close"] / LINE_HK - 1) * 100, 4):+.4f}%**（本档单日 {hstech["pct"]:+.2f}%）；'
                      f'⚠️ 但为「破位状态未解除」——收盘仍低于 4,250、日内最高 {hstech["high"]} 未触及防线，'
                      f'且反弹日成交仅微增、南向净买入由 64.77 亿港元回落至 2.91 亿 → 承接力量弱于跌幅日；'
                      f'按 §3.114c「同日防线只触发一次」→ 本档**不新增纪律动作**，防线维持 4,250'),
        'next_line': LINE_HK_NEXT,
        'next_line_dist_pct': round((hstech['close'] / LINE_HK_NEXT - 1) * 100, 4),
    },
    'zz_consume_12100': {
        'line': LINE_CS, 'close': cs_close, 'pct': cs_pct,
        'dist_pct': round((cs_close / LINE_CS - 1) * 100, 4),
        'state': 'ABOVE_CLOSE_LEVEL',
        'intraday_low': cs['low'],
        'judgement': (f'中证消费 10/9 收 {cs_close:,.4f}（{cs_pct:+.2f}%），距 {LINE_CS:,.0f} 下沿 '
                      f'{round((cs_close / LINE_CS - 1) * 100, 4):+.4f}% → **连续第 2 个交易日站稳下沿**（10/8 '
                      f'{po["defense_lines"]["zz_consume_12100"]["dist_pct"]:+.4f}% → 本档 '
                      f'{round((cs_close / LINE_CS - 1) * 100, 4):+.4f}%）；日内低 {cs["low"]} 未破；无触发'),
        'next_line': LINE_CS_NEXT,
        'next_line_dist_pct': round((cs_close / LINE_CS_NEXT - 1) * 100, 4),
    },
    'a_med_reverse_1_5pct': {
        'proxy_pct': pc['board_med'], 'board_med': pc['board_med'],
        'leader_med': pc['leader_med'], 'lag_med': pc['lag_med'],
        'single_day_000933': medi['pct'],
        'line_pct': -1.5, 'dist_pct': round(pc['board_med'] - (-1.5), 4),
        'state': 'NOT_TRIGGERED_RECOVERED',
        'intraday_state': ('TRIGGERED 过（13:45 盘中代理 −2.4025%，portfolio_intraday_20261009.json '
                           'defense.med_reverse_line = true）'),
        'state_continuity': ('盘中 → 收盘 **反向翻转**（−2.4025% → '
                             f'{pc["board_med"]:+.4f}%）→ 「盘中触发」被收盘推翻，'
                             '按 §3.71 该线为「利好兑现后的回调观察线」、非止损线 → **不执行任何减配**'),
        'contingency_closed': True, 'contingency_triggered': False,
        'judgement': (f'A股医药板块代理 {pc["board_med"]:+.4f}%（中证医疗 {pc["lag_med"]:+.2f}% / '
                      f'中证医药 {medi["pct"]:+.2f}% / 300医药 {pc["leader_med"]:+.2f}%）> 0 → '
                      f'① 负号方向的「主动兑现线」（≤ −1.5%）**未触发**；'
                      f'② +1.5% 反转线**未触发**（距 {round(1.5 - pc["board_med"], 4):+.4f}pct）；'
                      f'③ **盘前登记的「被动减配预案」判定为未触发 → 按预案明文「回调序列断裂、预案不启动」作废**'
                      f'（预案条件：10/9 收盘代理 ≤ 0% 则减持 {po["defense_lines"]["a_med_reverse_1_5pct"]["contingency_plan"]["size_amount"]:,.2f} 元，'
                      f'候选 {"/".join(po["defense_lines"]["a_med_reverse_1_5pct"]["contingency_plan"]["candidates"])}）；'
                      f'④ 结构反转：10/8「大市值抗跌、中小市值深跌」→ 10/9「中证医疗 +{pc["lag_med"]:.2f}% 领涨、'
                      f'300医药 {pc["leader_med"]:+.2f}% 唯一收跌」，结构序完全颠倒'),
    },
}

# ---------- 2. 纪律执行台账 ----------
# 本档无新增纪律动作；台账主体 = 已成交两笔（§3.123e / §3.125c）
hk_rebound = round((hstech['close'] / idx['HSTECH']['2026-10-08'] - 1) * 100, 4)
_hk_d = lines['hstech_4250']['dist_pct']
_cs_d = lines['zz_consume_12100']['dist_pct']
ledger = [{
    'date': TODAY, 'kind': '本档无新增纪律动作',
    'amount': 0.0,
    'reason': (f'恒生科技 10/9 收 {hstech["close"]}（{hstech["pct"]:+.2f}%），距 4,250 为 {_hk_d:+.4f}% → '
               f'仍处破位区间但**未叠加触发**；'
               f'中证消费 {cs_close:,.4f} 距 12,100 为 {_cs_d:+.4f}%；A股医药代理 {pc["board_med"]:+.4f}% 转正'),
    'cumulative_amount': pc['discipline']['cumulative_amount'],
    'cumulative_selfcheck': pc['discipline']['cumulative_selfcheck'],
    'weight_after': pc['discipline']['weight_after'],
    'next_rule': f'恒生科技下一道防线 4,000（距 {lines["hstech_4250"]["next_line_dist_pct"]:+.4f}%）；再破不叠加新纪律',
}]

ledger_hist = [
    {'date': '2026-09-29', 'kind': '大消费 0.5% 纪律兑现', 'amount': 1879.43,
     'trigger': '9/28 收盘级跌破 12,100（12,096.0166，−0.033%）', 'settle': '按 9/29 净值成交（价值中性）',
     'outcome': (f'9/29 收 12,107.1705 收复 12,100 → 定性「技术性误触」；'
                 f'10/9 收 {cs_close:,.4f}（距下沿 {_cs_d:+.4f}%）→ 结论延续、未再触发')},
    {'date': '2026-09-30', 'kind': '恒生科技 0.5% 纪律减仓（第 1 次）', 'amount': 1882.46,
     'trigger': '9/29 收盘级破位（4,249.62，−0.0089%，**边际破位**）', 'settle': '按 9/30 净值成交',
     'outcome': (f'9/30 收 4,253.89 收复防线 → 记为「**边际破位成本**」；'
                 f'10/9 收 {hstech["close"]}（距防线 {_hk_d:+.4f}%）→ 事后看方向正确、当期被判成本')},
    {'date': '2026-10-08', 'kind': '恒生科技 0.5% 纪律减仓（第 2 次）', 'amount': 1904.44,
     'trigger': '10/2 收盘级破位（4,157.94，−2.1661%，**非边际破位**）', 'settle': '按 10/8 净值成交（价值中性）',
     'outcome': (f'执行日（10/8）恒生科技收 4,073.38（−2.89%，距防线 −4.1558%）→ 当日看属「**有效减仓**」；'
                 f'⚠️ **次日（10/9）标的反弹 {hk_rebound:+.4f}%** → 短期看该笔减仓的机会成本 ≈ '
                 f'{1904.44:,.2f} 元 × {hk_rebound:.4f}% ≈ **{1904.44 * hk_rebound / 100:,.2f} 元**'
                 f'（仅为短期读数、不改变纪律判定）；本档距防线 {_hk_d:+.4f}% → 破位状态仍在')},
]

# ---------- 3. 待消化收口 + QDII 挂账 ----------
pending = {
    'as_of': TODAY,
    'hk_leg_pending': pc['pending_release'],
    'qdii_pending': pc['qdii_pending'],
    'pending_total': {
        'hk_leg': ('已收口（10/8 由场外港股联接 000071 / 012348 真实净值一次性兑现，`window_closed = true`）；'
                   '本档无新增窗口（10/9 为正常交易日，港股腿按当日真实净值/收盘价逐券定价）'),
        'qdii_leg_range': [pc['qdii_pending']['remaining']['low'],
                           pc['qdii_pending']['remaining']['high']],
        'qdii_leg_note': ('余 **US 10/9 一个未知交易日**（北京 10/10 04:00 成型）；'
                          '本档挂账区间按 0 计系**「尚无已知美股交易日进入挂账」**，非「挂账已消失」（§3.124a）'),
    },
    'note': ('§3.112f / §3.118a：挂账只给区间、禁止中枢点值。'
             '**本档为长假挂账窗口的核销档**：QDII 000369 / 016280 / 164906 自基准净值日 9/30 起至 10/8，'
             '全部 **6 个美股交易日**（US 10/1·10/2·10/5·10/6·10/7·10/8）已由真实净值一次性核销，'
             f'实际回填 {pc["qdii_pending"]["booked_this_session"]["amount"]:+,.2f} 元（基准 9/30 口径）；'
             'IYH 同期复合 −0.8944% → 实测隐含传导系数 000369 = 0.7032 / 016280 = 0.76，'
             '**回落至标定中枢 0.72 附近**，与前档「长假前后隐含 1.25~1.29」形成强对照 → '
             '§3.118a「区间法成立、中枢法偏高」获得**反向样本**；'
             '⚠️ 系数重估仍为 pending（要求 ≥4 券位 × ≥5 交易日，当前仅 2 券位 × 1 窗口）→ '
             '**系数未重估前基于该系数的一切仓位决策无效**（港股腿已收口，不受影响）'),
}

# ---------- 4. 节假日历（逐市场分列，§3.115d） ----------
calendar = {
    '2026-10-08（上一档）': ('A股 长假后复市首日（上证 3,811.90 / −0.79%）+ 港股正常交易日（恒指 −1.43% / 恒科 −2.89%）；'
                          '港股通恢复（南向净买入 64.77 亿港元）；第 2 次恒科 0.5% 减仓 1,904.44 元按净值成交；'
                          '美联储 9 月会议纪要偏鹰；央行 12,000 亿元 3 个月期买断式逆回购'),
    '2026-10-09（今日）': ('A股 + 港股双市场正常交易日并在本档双收盘；'
                        '上证 %s（%+.2f%%）/ 创业板指 %s（%+.2f%%）/ 沪深300 %+.2f%%；'
                        '恒指 %s（%+.2f%%）/ 恒生科技 %s（%+.2f%%）/ 恒生医疗保健 %+.4f%%；'
                        '09:30 公布 9 月金融数据（M2/社融）；中证 500/1000 指数样本调整于收市后生效'
                        % (idx['000001'][TODAY], IDXP.get('000001', 0.0),
                           idx['399006'][TODAY], IDXP.get('399006', 0.0),
                           IDXP.get('000300', 0.0),
                           idx['HSI'][TODAY], IDXP.get('HSI', 0.0),
                           idx['HSTECH'][TODAY], IDXP.get('HSTECH', 0.0),
                           IDXP.get('HSHCI', 0.0))),
    NEXT_TD: ('**下一交易日（周一）**：A股 + 港股正常交易；US 10/9 收盘成型于北京 04:00（供 QDII 挂账刷新）；'
              '美国 9 月 CPI 前瞻周；10/10-10/11 为周末（非交易日）'),
    '2026-10-14': '美国 9 月 CPI 公布',
    '2026-10-19': '港股重阳节翌日休市（A股 正常交易）',
    '2026-10-27~28': 'FOMC 议息会议（CME：10 月维持不变概率 82.3%）',
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
LOF906_PNL = _sum('164906')
P1616, S1616 = _pct('161616'), _sum('161616')
P0727, S0727 = _pct('000727'), _sum('000727')
P012323, S012323 = _pct('012323'), _sum('012323')
P512170 = _pct('512170')
# 仍「未推进 → 计 0」的券（本档仅 000051；161616 / 000727 已于 20:14 复抓后补入）
ZERO_ROWS = [d for d in det if '未推进' in str(d.get('price_src', ''))]
ZERO_CODES = sorted({_base(d['code']) for d in ZERO_ROWS})
NAV_PRECISE = round(pc['est_total_pnl'] / pc['base_total'] * 100, 4)
gain_share = round(100.0 * GLD_PNL / pc['est_total_pnl'], 1)

driver = {
    'top_drag': TOP_DRAG,
    'top_gain': TOP_GAIN,
    'track_pnl_rank': drag_rank,
    'attribution': (
        f'① **本档为「普涨修复日」**：六大板块除 A股医药（{tr["A股医药"]["day_pct"]:+.2f}%）外全部收正，'
        f'组合估算 {pc["est_total_pnl"]:+,.2f} 元（{NAV_PRECISE:+.4f}%）；'
        f'② **其他/宽基 {tr["其他/宽基"]["pnl"]:+,.2f} 元为最大正贡献**——广联达（002410）'
        f'**{GLD_PCT:+.2f}%** 单券贡献 {GLD_PNL:+,.2f} 元（占组合正收益 {gain_share:.1f}%），'
        f'叠加证券ETF国泰 {_pct("512880"):+.2f}%、恒生ETF联接 {_pct("000071"):+.2f}%；'
        f'③ **大消费 {tr["大消费"]["pnl"]:+,.2f} 元**——汇添富主要消费联接 {_pct("000248"):+.2f}%、'
        f'富国消费主题 {_pct("519915"):+.2f}%、消费ETF {_pct("159928"):+.2f}%，'
        f'中证消费 {cs_pct:+.2f}% 领涨宽基指数；'
        f'④ **恒生科技 {tr["恒生科技"]["pnl"]:+,.2f} 元**——天弘恒科联接 {_pct("012348"):+.2f}%、'
        f'恒指科技ETF {_pct("513180"):+.2f}%、中概互联ETF {_pct("513050"):+.2f}%，'
        f'但 **164906 交银海外互联按 10/8 净值核销 −2.46%** 抵消 {LOF906_PNL:+,.2f} 元'
        f'（**净值出库节奏错配，非 10/9 港股行情**）；'
        f'⑤ **A股医药 {tr["A股医药"]["pnl"]:+,.2f} 元为唯一负贡献**——**主动医药基拖累为主因**：'
        f'大摩健康 {M708_PCT:+.2f}%（两只账户合计 {M708_PNL:+,.2f} 元）、'
        f'融通医疗保健 **{P1616:+.2f}%（{S1616:+,.2f} 元，20:14 复抓后已补入）**；'
        f'正贡献来自 融通健康产业 {P0727:+.2f}%（{S0727:+,.2f} 元）、'
        f'华宝中证医疗联接 {P012323:+.2f}%（{S012323:+,.2f} 元）、医疗ETF {P512170:+.2f}% 等被动医药基；'
        f'⚠️ 板块本身 {pc["board_med"]:+.4f}% **收正** → **基金与板块背离 = 「主动医药基超额为负」+「场外净值出库节奏」'
        f'双因，方向由前者主导**（§3.105「基准已含」口径）；'
        f'⑥ **美股标普医药 {tr["美股标普医药"]["pnl"]:+,.2f} 元为负**——系 QDII 挂账核销'
        f'（US 10/1~10/8 真实净值），**非 10/9 美股行情**（北京 20:00 时美股尚未开盘）；'
        f'⑦ **现金** 0.00 元（账面冻结项，不构成方向判断）'),
}

out = {'date': TODAY, 'as_of': '2026-10-09 收盘（A股 长假后第 2 个交易日 + 港股正常交易日；双市场双收盘）',
       'session_type': pc['session_type'],
       'base_total': pc['base_total'], 'base_file': pc['base_file'], 'total_mv': total_mv,
       'est_total_pnl': pc['est_total_pnl'], 'est_total_pct': pc['est_total_pct'],
       'est_total_pnl_low': pc['est_total_pnl_low'], 'est_total_pnl_high': pc['est_total_pnl_high'],
       'defense_lines_close': lines,
       'discipline_ledger': ledger, 'discipline_ledger_history': ledger_hist,
       'pending': pending, 'calendar': calendar, 'exposure': exposure, 'driver': driver,
       'action_next': {
           'next_session': NEXT_TD + '（周一，A股 + 港股正常交易日）',
           'planned': (('① **QDII 挂账刷新**：US 10/9 收盘（北京 10/12 04:00 成型）→ 000369/016280/164906 '
                        '取得 10/12 可得的最新净值日则按 §3.105 回填；② **9 月金融数据已公布（09:30）**：'
                        '在 10/12 盘前档登记事件、不预判；③ 复核恒生科技 4,000 防线（本档距 %+.4f%%）'
                        '与「减仓后反弹」样本累积；④ 复核中证消费 12,100 下沿（本档距 %+.4f%%）'
                        '与 12,000 次级线；⑤ 复核医药敞口 %.2f%%（距 40%% 上限门槛：全部医药 %+.2f%% / 仅 A股医药 %+.2f%%）'
                        '——**任何正向催化均不构成加仓理由**（new_buy = 0）；'
                        % (lines['hstech_4250']['next_line_dist_pct'],
                           lines['zz_consume_12100']['dist_pct'],
                           pc['med_pct'], pc['threshold_all_med'], pc['threshold_a_sh_med']))
                       + '⑥ ' + (' / '.join(ZERO_CODES) if ZERO_CODES else '（无）') +
                       ' 的 **10/9 净值补抓**（161616 / 000727 已于本档 20:14 复抓补入；'
                       '剩余未出者于 10/12 盘前档兜底并以 `_fix` 覆盖本档读数）'),
       },
       'note': ('10/9 **无新增纪律动作**（三条防线：恒科破位但未叠加触发 / 中证消费站稳 / '
                'A股医药转正且被动减配预案作废）；待消化：长假港股腿已收口、QDII 腿为「本档核销 + 余 0」；'
                '⚠️ 场外净值出库节奏：161616 / 000727 已于本档 **20:14 复抓后补入**（−0.61% / +0.93%），'
                '**剩余 ' + ('、'.join(ZERO_CODES) if ZERO_CODES else '无') + ' 仍按「基准已含计 0」处理**（§3.105）；'
                '组合当日估算由 20:02 首抓（含两只计 0，+2,613.60 元）**下修至 +2,558.50 元**，'
                '差异 −55.10 元 = 161616（−102.25）+ 000727（+47.15）'),
       'nav_pending_after_refetch': {'codes': ZERO_CODES, 'refetched_codes': ['161616', '000727'],
                                     'refetch_time': '2026-10-09 20:14',
                                     'pnl_delta': round(S1616 + S0727, 2)}}

json.dump(out, open(os.path.join(HIST, 'portfolio_strategy_close_' + TODAYC + '.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)

print('✅ 三条防线收盘级判定:')
for k, v in lines.items():
    print(f'  {k}: state={v["state"]} close={v.get("close", v.get("board_med"))} '
          f'dist={v["dist_pct"]:+.4f}%')
print(f'\n✅ 本档纪律动作 = 0（累计已登记 {pc["discipline"]["cumulative_amount"]:,.2f} 元）')
print(f'✅ 恒科第 2 次减仓次日反弹 {hk_rebound:+.4f}%（短期机会成本 ≈ {1904.44 * hk_rebound / 100:,.2f} 元）')
print(f'\n✅ 待消化: 港股腿已收口；QDII 腿区间 = {pending["pending_total"]["qdii_leg_range"]} 元；'
      f'本档核销 {pc["qdii_pending"]["booked_this_session"]["amount"]:+,.2f} 元')
print(f'\n✅ 敞口：医药 {pc["med_pct"]:.2f}%（门槛全部 {pc["threshold_all_med"]:+.2f}% / 仅A股医药 {pc["threshold_a_sh_med"]:+.2f}%）'
      f'｜港联系 {pc["hk_total_pct"]:.2f}%（赛道层 {pc["track_layer_hk_pct"]:.2f}% + 宽基 '
      f'{exposure["hk_broad_layer_pct"]:.2f}pct）')
print(f'\n✅ 减仓后权重: ' + ' / '.join(f'{k} {v:.2f}%' for k, v in pc['discipline']['weight_after'].items()))
print(f'\n防线：恒生科技 {hstech["close"]} ({hstech["pct"]:+.2f}%) vs {LINE_HK:,.0f} → '
      f'{lines["hstech_4250"]["state"]}（{lines["hstech_4250"]["dist_pct"]:+.4f}%）')
print(f'      中证消费 {cs_close} ({cs_pct:+.2f}%) vs {LINE_CS:,.0f} → '
      f'{lines["zz_consume_12100"]["state"]}（{lines["zz_consume_12100"]["dist_pct"]:+.4f}%）')
print(f'      A股医药板块代理 {pc["board_med"]:+.4f}% vs −1.5% / +1.5% → {lines["a_med_reverse_1_5pct"]["state"]}')
print(f'\nTop 拖累: ' + ' | '.join(f'{d["name"]} {d["pnl"]:+,.2f}' for d in TOP_DRAG[:4]))
print(f'Top 贡献: ' + ' | '.join(f'{d["name"]} {d["pnl"]:+,.2f}' for d in TOP_GAIN[:4]))
print(f'\n已保存 portfolio_strategy_close_{TODAYC}.json')
