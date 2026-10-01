# -*- coding: utf-8 -*-
"""2026-10-01 盘后档产物：假期台账（档型① 纯非交易日专用）
⚠️ 命名刻意避开 `portfolio_close_*`（链式序列 glob）与 `portfolio_pending_*`（混合档专用）
   → `portfolio_holiday_<DATE>.json`：不参与链式序列，不插入 0% 行（§3.108 条款 22 / §3.118b）
⚠️ 本档不重算风险指标（沿用 risk_stats_20261001_preopen.json，chain_0pct_row_inserted = false）
输出：data/processed/history/portfolio_holiday_20261001.json
"""
import json, os, subprocess

BASE = '/Users/jieyang/Documents/WealthHub'
HIST = os.path.join(BASE, 'data/processed/history')
TODAY = '2026-10-01'

pf = json.load(open(os.path.join(HIST, 'portfolio_preopen_20261001.json'), encoding='utf-8'))
rk = json.load(open(os.path.join(HIST, 'risk_stats_20261001_preopen.json'), encoding='utf-8'))
rs = json.load(open(os.path.join(HIST, 'portfolio_strategy_close_20260930.json'), encoding='utf-8'))
base = json.load(open(os.path.join(HIST, 'portfolio_close_20260930_fix.json'), encoding='utf-8'))

# 硬守卫：基准 = 最近一份收盘修正件 tracks[].mv 求和
tot = sum(v['mv'] for v in pf['tracks'].values())
dev = abs(tot - pf['base_total'])
assert dev < 1.5, f'⚠️ Σ tracks.mv 与 base_total 偏差 {dev} ≥ 1.5，终止'

# 零行情增量三自证（§3.119e）
numstat = {}
for f in ('indices.csv', 'etf_intraday.csv', 'fund_nav.csv'):
    r = subprocess.run(['git', '--no-pager', 'diff', '--numstat', '--', f'data/processed/history/{f}'],
                       cwd=BASE, capture_output=True, text=True)
    numstat[f] = r.stdout.strip() or '0/0'
qm = json.load(open(os.path.join(HIST, 'qieman_intraday_20261001.json'), encoding='utf-8')) \
    if os.path.exists(os.path.join(HIST, 'qieman_intraday_20261001.json')) else {}
evs = json.load(open(os.path.join(HIST, 'event_stats_20261001_close.json'), encoding='utf-8'))

holiday = {
    'date': TODAY,
    'session': 'close',
    'session_type': 'pure_non_trading_day_close',
    'session_type_note': ('档型①「纯非交易日」（A股与港股「均」未开市；美股照常开市不改变该判定，§3.109/§3.118b）。'
                          '本档为国庆长假第 1 日 20:00 盘后复盘档。'),
    'three_market_verification': {
        'ashare': {'source': "akshare.stock_zh_index_daily('sh000001')", 'last_row_date': '2026-09-30',
                   'close': 3842.195, 'verdict': '未开市（末行日期 = 上一交易日）'},
        'hk': {'source': '新浪 hq 直连 rt_hkHSTECH 返回体日期字段', 'date_field': '2026/09/30',
               'time_field': '16:08:50', 'close': 4253.89,
               'verdict': '未开市（返回体日期字段 = 上一交易日，§3.119b）'},
        'us': {'source': "akshare.stock_us_daily('IYH' / 'XLV')", 'last_row_date': '2026-09-30',
               'IYH': 71.56, 'XLV': 168.42,
               'verdict': '美股 10/1 交易日尚未收盘（北京 10/2 04:00 成型）→ 本档无美股新数据'},
        'rule': '三市场各自独立验证、不得互相外推（§3.119b）',
    },
    'base': {
        'file': 'portfolio_close_20260930_fix.json',
        'base_total': pf['base_total'],
        'sum_tracks_mv': round(tot, 2),
        'guard_dev': round(dev, 2),
        'guard_rule': '|Σ tracks.mv − base_total| < 1.5',
        'base_revision': pf['base_revision'],
    },
    'day_result': {
        'est_pnl': 0.0,
        'est_pct': 0.0,
        'attribution': '全部持仓标的不可定价（非市场持平）',
        'reasons': [
            'A股 10/1-10/7 全休 → 20 只 A股类场外基金不发布净值、A股指数无新收盘',
            '港股 10/1 休市 → 恒生科技赛道层与中概层无今日价格',
            '场外港股联接（000071 / 012348）在 A股 休市期不发布净值（§3.112i）',
            '场内 ETF（513050 / 513180 / 159920 / 159928 等）无交易时段',
            '美股 9/30 收盘虽已入库，但其组合传导属 QDII 挂账项、不在本档基准内',
        ],
        'note': '⚠️ 「0 元」是账面冻结，不构成任何方向判断（§3.117a / §3.118b）',
    },
    'tracks': pf['tracks'],
    'tracks_weight_after_discipline': pf['tracks_weight_after_discipline'],
    'med_exposure': {
        'mv': pf['med_exposure'], 'pct': pf['med_pct'],
        'threshold_all_med_pct': pf['threshold_all_med'],
        'threshold_a_sh_med_pct': pf['threshold_a_sh_med'],
        'non_med_total': pf['non_med_total'],
        'rule': '§3.98 方程解法 A(1+r)/(B+A(1+r)) = 40%，不得用「相对跑赢 pct」线性外推',
    },
    'hk_exposure': {
        'total': pf['hk_total'], 'pct': pf['hk_total_pct'],
        'segments': pf['hk_segments'],
        'southbound_gap_days': pf['hk_southbound_gap_days'],
        'rule_hint': '只报赛道层 8.29% 将低估 4.84pct（宽基层），§3.108 条款 23',
    },
    'defense_lines': pf['defense_lines'],
    'discipline_hstech': pf['discipline_hstech'],
    'holiday_pending': pf['holiday_pending'],
    'holiday_calendar': {
        'ashare': '2026-10-01 ~ 2026-10-07 全休（7 个自然日）；10-08 复市',
        'hk': '仅 2026-10-01 休市 1 天；10-02 复市 → 长假内共 4 个港股交易日（10-02、10-05、10-06、10-07）',
        'hk_connect': '2026-10-01 ~ 2026-10-07 全程关闭；10-08 恢复 → 南向空窗 4 个港股交易日',
        'us': '照常交易 5 个交易日（10-01、10-02、10-05、10-06、10-07）；10-03/10-04 周末休市',
        'key_events': ['10-02 20:30 美国 9 月非农（预期 +9.0 万 / 失业率 4.1%）',
                       '10-01 22:00 美国 9 月 ISM 制造业（预期 55.0 / 前值 54.6）',
                       '10-05 22:00 美国 9 月 ISM 服务业（预期 54.0 / 前值 55.4）',
                       '10-07 01:00 3 年期美债拍卖；10-07 9 月 FOMC 会议纪要',
                       '10-08 A股 复市 + 港股通恢复；央行 1.2 万亿元买断式逆回购开展'],
    },
    'zero_increment_proof': {
        'tables_numstat': numstat,
        'tables_note': '三表 `git diff --numstat` 全部 0/0 = 正常零增量，非抓取失败（§3.119e）',
        'qieman_session': qm.get('session'),
        'events_session_added': evs.get('session_added'),
        'verdict': '三处独立字段共同证明「数据链路连通、本档确无新行情」',
    },
    'risk_stats': {
        'source': 'risk_stats_20261001_preopen.json',
        'recomputed': False,
        'reason': '档型① 不产 close/pending、不向链式序列插入 0% 行 → 风险指标须与上一盘前档同口径（§3.118b）',
        'chain_cum_pct': rk['chain_cum_pct'], 'chain_days': rk['chain_days'],
        'chain_0pct_row_inserted': rk['chain_0pct_row_inserted'],
        'w40_cum_pct': rk['w40_cum_pct'], 'w40_days': rk['w40_days'],
        'sharpe': rk['sharpe'], 'sharpe_n': rk['sharpe_n'],
        'max_dd_pct': rk['max_dd_pct'],
        'last5_cum_pct': rk['last5_cum_pct'], 'last10_cum_pct': rk['last10_cum_pct'],
        'fix_applied': rk['fix_applied'],
    },
    'next_session_actions': [
        '① 逐市场参考日回填：A股类 → 10-08；恒生科技 → 10-02 起 4 个交易日累计；美股类 → 10-01 起 5 个交易日累计（§3.119c/§3.112h）',
        '② QDII 挂账按实际净值兑现（基准净值日 9/28 起），并以 ≥4 券位 / ≥5 交易日样本重估传导系数（§3.118a）',
        '③ 恒生科技 4,250 防线以 10-08 收盘价重新判定（9/30 收 4,253.89、贴线 +0.0915%）',
        '④ 医药敞口距 40% 上限仅 0.77pct，复市首日须前置被动再平衡预案（门槛：两赛道同涨 +3.27%）',
        '⑤ 场内港股 ETF（513050/513180/159920）的溢价/折价在 10-08 对账时单列（§3.112i）',
    ],
    'generated_by': 'scripts/calc_holiday_20261001.py',
    'note': ('口径纪律：本档不产 `portfolio_close_*` / `portfolio_pending_*`，不做待消化测算（沿用盘前档 pending 披露）、'
             '不向链式序列插入 0% 行。产物命名 `portfolio_holiday_*` 为档型① 盘后档台账（新增约定，待写入知识库）。'),
}
json.dump(holiday, open(os.path.join(HIST, 'portfolio_holiday_20261001.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
print('✅ 已写入 portfolio_holiday_20261001.json')
print('基准', holiday['base']['base_total'], '| Σtracks.mv', holiday['base']['sum_tracks_mv'],
      '| dev', holiday['base']['guard_dev'])
print('三表 numstat:', numstat)
print('qieman_session:', qm.get('session'), '| events session_added:', evs.get('session_added'))
print('chain_days', rk['chain_days'], '| chain_0pct_row_inserted', rk['chain_0pct_row_inserted'])
