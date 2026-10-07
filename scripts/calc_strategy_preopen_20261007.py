# -*- coding: utf-8 -*-
"""2026-10-07（周三 · 国庆长假第 7 日 · **混合档**：A股休市 + 港股续市第 4 日）盘前档：组合策略计算
SESSION_TYPE = 'mixed_day_preopen'（档型②：A股休市 + 港股开市 → §3.108 条款 22 / AGENTS #22 / §3.121b）
基准 = 9/30 修正收盘（portfolio_close_20260930_fix.json）= 380,888.29 元
输出：
  - portfolio_preopen_20261007.json —— 敞口、门槛方程、港联系三层拆解、**待消化（mixed-day）**、防线台账、日历
  - portfolio_pending_20261007.json —— 混合档台账（**state = preopen_estimate / finalized = false**，
    港股 10/7 收盘价 16:00 后成型 → 由 10/7 20:00 盘后档覆盖为正式版）
★★★ 本档与 10/6 盘前档的**四项结构差异（派生后必检）** ★★★
  ① **美股腿新增 1 个真实交易日（US 10/6，负收益）**：IYH 70.91 → 70.67（**−0.34%**）→ 待消化 B 段
     由「9/30 × 10/1 × 10/2 × 10/5」扩展为「9/30 × 10/1 × 10/2 × 10/5 × 10/6」；
  ② **港股腿已定价段由 2 日（10/2+10/5）扩为 3 日（10/2 + 10/5 + 10/6）**：10/6 段 HSTECH +0.9418%、
     恒生指数 +1.0000%
     → 累积段读数据 `portfolio_pending_20261006.json.hk_pending_digest`（**几何复合，§3.126c**）；
  ③ **恒生科技防线基准价由 10/5 的 4,183.68 更新为 10/6 的 4,223.08**（仍在 4,250 下方、幅度收窄至 −0.6344%）；
  ④ **夜盘读数须分列且本档未采集**（10/6 夜盘读数未入库 → 本档**显式标注不可用**，不沿用 10/5 夜盘旧值）。
    —— **夜盘不参与防线判定**（§3.114c）。
⚠️ 档型②（混合档：A股休市 + 港股开市）→ **必做待消化测算**（§3.108 条款 22）。
   ⚠️ 时段归属澄清：08:00 盘前时刻港股尚未开盘 → 本档 pending 仅含
      「美股/QDII 腿」（已定价至 US 10/6）与「港股腿（10/2+10/5+10/6 已定价 / 10/7 未定价）」两段。
⚠️ §3.107：QDII/LOF 券「基准已含哪一日净值」从 price_src 字符串解析，不得用固定日期常量。
⚠️ §3.118a：跨长假 QDII 挂账预告**禁止给中枢点值**，只给区间（系数 0.60~0.90）并显式标注「系数不稳定」。
⚠️ §3.123e 纪律累计口径：第 1 次 1,882.46 元（9/29 触发、9/30 成交）+ 第 2 次 1,904.44 元
   （10/2 触发、执行待 10/8）= 累计 3,786.90 元 → 恒生科技 27,785.94 元（7.30%）/ 现金 32,999.87 元（8.66%）。
"""
import json, os

BASE = '/Users/jieyang/Documents/WealthHub'
HIST = os.path.join(BASE, 'data/processed/history')
TODAY = '2026-10-07'
SESSION_TYPE = 'mixed_day_preopen'
BASEFILE = 'portfolio_close_20260930_fix.json'
fix = json.load(open(os.path.join(HIST, BASEFILE), encoding='utf-8'))

TOTAL = fix['total_mv']
tracks = fix['tracks']
print(f'基准（9/30 修正收盘）= {TOTAL:,.2f} 元  ← {BASEFILE}')
print('  ⚠️ 档型②「混合档」（A股 10/1-10/7 休市 + 港股 10/7 续市第 4 日）'
      '→ 产 pending 台账、**必做待消化**（§3.108 条款 22 / §3.121b）')
dev = abs(sum(v['mv'] for v in tracks.values()) - TOTAL)
print(f'  硬守卫 |Σ tracks.mv − total_mv| = {dev:.4f} 元  {"✅" if dev < 1.5 else "❌ 终止"}')
assert dev < 1.5, 'Σ tracks.mv 与 total_mv 不一致，终止本档计算（§3.104）'

for k, v in sorted(tracks.items(), key=lambda kv: -kv[1]['mv']):
    print(f"  {k:10s} mv={v['mv']:>11,.2f}  w={v['pct_of_total']:>6.2f}%  day={v['day_pct']:+.3f}%")

# ---------- 医药敞口与门槛方程（§3.98 / §3.112）----------
med = round(tracks['A股医药']['mv'] + tracks['美股标普医药']['mv'], 2)
B_nm = TOTAL - med
A_sh = tracks['A股医药']['mv']
th_all = ((0.40 / 0.60) * B_nm / med - 1) * 100
th_sh = (((0.40 / 0.60) * B_nm - (med - A_sh)) / A_sh - 1) * 100
print(f'\n医药敞口 {med:,.2f} 元 = {med/TOTAL*100:.2f}%  距 40% 上限 {40-med/TOTAL*100:.2f}pct')
print(f'  门槛：两医药赛道同涨 {th_all:+.2f}%  /  仅 A股医药 {th_sh:+.2f}%')
print(f'  非医药对手盘 {B_nm:,.2f} 元')
print('  ⚠️ 本档两医药赛道（A股 + 美股）中：A股 休市无定价（场外无净值、场内无成交价）；'
      '美股 10/6 已定价（**XLV −0.17%，为标普 11 板块唯一下跌**；IYH −0.34%）'
      '→ 门槛口径沿用（基准未变）；**美股医药微跌不改变 39.23% 的当日权重口径**（权重按 9/30 修正收盘计）')

# ---------- 港股暴露三层拆解（§3.108 条款 23/24）----------
HK_TECH_CODES = {'012348', '513180'}          # 纯恒生科技系
CPO_CODES = {'513050', '164906'}              # 中概/海外互联系
BROAD_HK_CODES = {'000071', '159920'}         # 宽基中的恒生系
pure = cpo = broad = 0.0
seg_detail = []
for d in fix['detail']:
    code6 = ''.join(c for c in str(d['code']) if c.isdigit())[-6:] if any(c.isdigit() for c in str(d['code'])) else ''
    mv = float(d['mv0_new']) + float(d['est_pnl'])
    if code6 in HK_TECH_CODES:
        pure += mv; seg_detail.append(('纯恒生科技系', code6, d['name'], round(mv, 2)))
    elif code6 in CPO_CODES:
        cpo += mv; seg_detail.append(('中概·海外互联系', code6, d['name'], round(mv, 2)))
    elif code6 in BROAD_HK_CODES:
        broad += mv; seg_detail.append(('宽基恒生系', code6, d['name'], round(mv, 2)))
hk_total = tracks['恒生科技']['mv'] + broad
print(f'\n港股暴露（三层拆解）：总 {hk_total:,.2f} 元 = {hk_total/TOTAL*100:.2f}%')
print(f'  赛道层「恒生科技」{tracks["恒生科技"]["mv"]:,.2f} 元 = {tracks["恒生科技"]["pct_of_total"]:.2f}%'
      f'  +  宽基层「恒生系」{broad:,.2f} 元 = {broad/TOTAL*100:.2f}%'
      f'  → 只报赛道层将低估 {broad/TOTAL*100:.2f}pct')
print(f'  三段法：纯恒生科技系 {pure:,.2f}（{pure/TOTAL*100:.2f}%）/ 中概·海外互联系 {cpo:,.2f}（{cpo/TOTAL*100:.2f}%）'
      f'/ 宽基恒生系 {broad:,.2f}（{broad/TOTAL*100:.2f}%） = {pure+cpo+broad:,.2f} 元 '
      f'（和校验 {round(pure+cpo+broad, 2) == round(hk_total, 2)}）')
for r in seg_detail:
    print(f'    {r[0]} {r[1]} {r[2][:22]:24s} {r[3]:>10,.2f}')
print('  ⚠️ 港联系「南向空窗」= 10/2、10/5、10/6、10/7 共 4 个港股交易日（港股通 10/1-10/7 关闭）'
      '→ 本档进入**第 4 个**空窗交易日，波动率须按「外资主导」建模（§3.113a/§3.115d/§3.121e）；'
      '10/5 成交 981.02 亿港元（较 10/2 的 1,458.04 亿缩量 32.7%）、10/6 量能连续第 2 日低于千亿'
      ' → 承接力量持续偏薄（**10/6 全天成交额为「数据暂缺」，未采集入库，不得由 10/5 值外推**）')

# ---------- 恒生科技 0.5% 纪律减仓（累计口径，§3.123e）----------
cut1 = fix.get('discipline', {})
cut1_amt = cut1.get('amount', 1882.46)          # 第 1 次：9/29 破位触发 → 9/30 成交
cut2_amt = round(TOTAL * 0.005, 2)               # 第 2 次：10/2 破位触发 → 执行待 10/8
cut_cum = round(cut1_amt + cut2_amt, 2)
hk_after = tracks['恒生科技']['mv'] - cut_cum
cash_after = tracks['现金']['mv'] + cut_cum
print(f'\n恒生科技 0.5% 纪律减仓（**累计口径**）：{cut_cum:,.2f} 元')
print(f'  第 1 次 {cut1_amt:,.2f} 元（9/29 收盘级破位触发 → 9/30 按净值成交，已结算）')
print(f'  第 2 次 {cut2_amt:,.2f} 元（10/2 收盘级破位触发 → 判定已成立，**执行待 10/8**）')
print(f'  恒生科技 {tracks["恒生科技"]["mv"]:,.2f} → {hk_after:,.2f}'
      f'（{tracks["恒生科技"]["pct_of_total"]:.2f}% → {hk_after/TOTAL*100:.2f}%）')
print(f'  现金     {tracks["现金"]["mv"]:,.2f} → {cash_after:,.2f}'
      f'（{tracks["现金"]["pct_of_total"]:.2f}% → {cash_after/TOTAL*100:.2f}%）')
print('  ⚠️ 口径更正：10/4 档曾记「纪律后 29,668.40 元 = 7.79% / 现金 31,117.41 元 = 8.17%」，'
      '该值 = 31,572.84 − 1,904.44（**只扣第 2 次、漏扣第 1 次已成交**）→ 本档统一为累计扣除并一并披露两个口径')

# ---------- 待消化（混合档核心；§3.112f / §3.123b 只给区间、不给方向）----------
med_us = tracks['美股标普医药']['mv']
IYH_0930, IYH_1001, IYH_1002, IYH_1005, IYH_1006 = -1.17, -1.62, 0.00, 0.7244, -0.34
comp_b = ((1 + IYH_0930 / 100) * (1 + IYH_1001 / 100) * (1 + IYH_1002 / 100)
          * (1 + IYH_1005 / 100) * (1 + IYH_1006 / 100) - 1)
# 自 US 9/30 起（A 已覆盖 9/29）；10/6 为本档新增段（IYH 70.91 → 70.67，−0.34%，负收益）
qdii_out = fix.get('pending', {}).get('qdii_observable_amount', -267.82)   # component A
notional_b = med_us * comp_b
print('\n待消化 / 挂账（混合档 = 必做；§3.112f / §3.118a：只给区间、禁止中枢点值）')
print(f'  A) QDII 000369/016280 的 9/29 净值已出库但按既定口径挂账：{qdii_out:+,.2f} 元'
      f'（基准净值日 9/28 → 已覆盖 US 9/29，不得在 B 中重复计入）')
print(f'  B) 自 US 9/30 起未可观测段：IYH 9/30 {IYH_0930:+.2f}% × 10/1 {IYH_1001:+.2f}% × 10/2 {IYH_1002:+.2f}%'
      f' × 10/5 {IYH_1005:+.4f}%（IYH 70.40→70.91） × **10/6 {IYH_1006:+.2f}%（本档新增，IYH 70.91→70.67）**'
      f' → 复合 {comp_b*100:+.4f}%')
print(f'     标的市值 {med_us:,.2f} 元 → 未打折损益 {notional_b:+,.2f} 元')
coefs = (0.60, 0.72, 0.90)
vals_b = sorted(round(notional_b * k, 2) for k in coefs)          # 负值：系数越大越负
b_high, b_mid, b_low = max(vals_b), (notional_b * 0.72), min(vals_b)
print(f'     系数 0.60 / 0.72 / 0.90 → {notional_b*0.60:+,.2f} / {b_mid:+,.2f} / {notional_b*0.90:+,.2f} 元')
tot_high, tot_mid, tot_low = qdii_out + b_high, qdii_out + b_mid, qdii_out + b_low
print(f'  → A+B 合计区间 {tot_high:+,.2f} 元 ~ {tot_low:+,.2f} 元（中枢 {tot_mid:+,.2f} 元 = 组合 {tot_mid/TOTAL*100:+.4f}%）')
print('  ⚠️ 传导系数不稳定：长假前后实测隐含系数 1.25~1.29（§3.118a），远超标定 0.72 / 实测 0.62'
      ' → 若按 1.25 折算，B = {:+,.2f} 元、A+B 合计 {:+,.2f} 元，**区间上/下界均可能被击穿**'
      .format(notional_b * 1.25, qdii_out + notional_b * 1.25))
print('  ⚠️ 仍未量化：US 10/7 共 1 个美股交易日未知（US 10/5 +0.7244% 与 US 10/6 −0.34% 均已计入）')
print('  ⚠️ 港股腿（港联系 {:.2f} 元 = {:.2f}%）已定价段 = 10/2 + 10/5 + 10/6（3 日）；'
      '未定价段 = 10/7 共 1 个交易日（本档 08:00 港股尚未开盘）'
      .format(hk_total, hk_total / TOTAL * 100))

# ---------- 港股腿「已定价段」= 10/2 + 10/5 + 10/6 三段（累积窗口第 3 日 / 共 4 日）----------
# §3.126c：跨档累积一律**几何复合**；§3.123b：low/high 取「合计结果值」的 min/max
PEND06 = json.load(open(os.path.join(HIST, 'portfolio_pending_20261006.json'), encoding='utf-8'))
HD = PEND06['hk_pending_digest']['segments']
SEG = {
    'pure_hstech':     {'mv': HD['pure_hstech']['mv'],     'cum': HD['pure_hstech']['cum_pct']},
    'china_internet':  {'mv': HD['china_internet']['mv'],  'cum': HD['china_internet']['cum_pct']},
    'broad_hk':        {'mv': HD['broad_hk']['mv'],        'cum': HD['broad_hk']['cum_pct']},
}
import itertools
outs_all = []
for a in SEG['pure_hstech']['cum']:
    for b in SEG['china_internet']['cum']:
        for c in SEG['broad_hk']['cum']:
            outs_all.append(round(SEG['pure_hstech']['mv'] * a / 100
                                  + SEG['china_internet']['mv'] * b / 100
                                  + SEG['broad_hk']['mv'] * c / 100, 2))
hk_low, hk_high = min(outs_all), max(outs_all)
hk_mid = round(sum(outs_all) / len(outs_all), 2)
assert hk_low <= hk_mid <= hk_high, '§3.123b 区间端点语义错误'
track_only = [round(SEG['pure_hstech']['mv'] * a / 100 + SEG['china_internet']['mv'] * b / 100, 2)
              for a in SEG['pure_hstech']['cum'] for b in SEG['china_internet']['cum']]
print(f'\n港股腿「已定价段」= 10/2 + 10/5 + 10/6（累积窗口第 3 日 / 共 4 日）：{hk_low:+,.2f} 元 ~ {hk_high:+,.2f} 元'
      f'（代理均值中枢 {hk_mid:+,.2f} 元，共 {len(outs_all)} 组笛卡尔积）')
print(f'  纯恒科 {SEG["pure_hstech"]["mv"]:,.2f} × 累积 {SEG["pure_hstech"]["cum"][0]:+.4f}%'
      f' = {SEG["pure_hstech"]["mv"]*SEG["pure_hstech"]["cum"][0]/100:+,.2f} 元')
print(f'  中概   {SEG["china_internet"]["mv"]:,.2f} × 累积 [{min(SEG["china_internet"]["cum"]):+.4f}%, '
      f'{max(SEG["china_internet"]["cum"]):+.4f}%]')
print(f'  宽基   {SEG["broad_hk"]["mv"]:,.2f} × 累积 [{min(SEG["broad_hk"]["cum"]):+.4f}%, '
      f'{max(SEG["broad_hk"]["cum"]):+.4f}%]')
print(f'  （仅赛道层 纯恒科+中概）区间 {min(track_only):+,.2f} 元 ~ {max(track_only):+,.2f} 元')
print('  ⚠️ 10/7 段（第 4 日）08:00 尚无收盘价 → **不可测算**，待 20:00 盘后档；'
      '累积区间 = 上述已定价段 + 1 个未知交易日（禁止作方向判断，§3.108 条款 24）')
print('  ⚠️ 口径对齐：本档 10/6 段读数据 `portfolio_pending_20261006.json#hk_pending_digest`（该文件由 10/6 20:00 盘后档'
      '以真实收盘价重算并覆盖，§3.121b）；HSTECH 10/6 收盘 4,223.08 / +0.9418%')

# ---------- 三条防线（恒科取 10/6 收盘口径；A股 两项待 10/8）----------
HS, ZZ, SH, HS_PREV = 4223.08, 12295.9591, 3842.1946, 4183.68
HS_NIGHT, HSI_NIGHT = None, None          # 10/6 夜盘读数本档未采集 → 显式不可用，不沿用 10/5 旧值
MED933_1D = (8009.6669 / 7786.2255 - 1) * 100
print('\n三条防线（恒科 = 10/6 收盘口径；本档可验证项分列）：')
print(f'  ① 恒生科技 4,250：10/6 收 {HS:,.2f}（前收 {HS_PREV:,.2f} / {(HS/HS_PREV-1)*100:+.4f}%）'
      f' → 距防线 {HS-4250:+,.2f} 点 / {(HS/4250-1)*100:+.4f}%'
      f'【**非边际破位、幅度持续收窄**（10/2 −2.1661% → 10/5 −1.5605% → 10/6 −0.6344%）】'
      f'→ 第 2 次 0.5% 减仓（{cut2_amt:,.2f} 元）**判定已成立、执行待 10/8**；**本档不重复判定**')
print('      ⚠️ **夜盘读数本档不可用**（10/6 港股夜盘读数未采集入库）→ 按「数据暂缺」处理，'
      '**不得沿用 10/5 夜盘旧值（4,245 / 24,266）冒充本档读数**')
print(f'      ⚠️ 判据纪律：**夜盘 ≠ 现货收盘价** → 即便 10/7 现货收盘站上 4,250，'
      f'按「同日防线只触发一次、已登记减仓不撤销」亦须于 10/8 执行')
print(f'  ② 中证消费 12,100 下沿：9/30 收 {ZZ:,.4f} → {(ZZ/12100-1)*100:+.4f}%'
      f'（下一线 12,000 距 {(ZZ/12000-1)*100:+.2f}%）→ **A股休市，10/7 不可验证，待 10/8**')
print(f'  ③ A股医药反向兑现线（板块代理单日 ≥1.5% 跌幅）：9/30 板块代理 {MED933_1D:+.4f}% → 未触发'
      f'（方向相反）；**A股休市，10/7 不可验证**')
print(f'  附：上证 9/30 收 {SH:,.4f}；恒指 10/6 收 24,280.561（+1.0000%）')

# ---------- 产物 ----------
out = {
    'date': TODAY, 'session': 'preopen', 'session_type': SESSION_TYPE,
    'session_type_note': ('档型②「混合档」**第 4 日** = A股休市（10/1-10/7）+ 港股开市（10/7 周三续市）；'
                          '美股 10/6（周二）收盘已于北京 10/7 04:00 成型（XLV −0.17% / IYH −0.34%，医药为 11 板块唯一下跌）；'
                          '08:00 盘前时刻港股尚未开盘（09:30 开）→ 本档 pending 台账中「美股/QDII 腿」已定价、'
                          '「港股腿」10/2+10/5+10/6 三段已定价 / 10/7 未定价，16:00 收盘后由 20:00 盘后档覆盖为正式版'),
    'calendar_verification': {
        'A股': 'stock_zh_index_daily(sh000001) 末行 = 2026-09-30（收 3,842.195）→ 国庆长假休市（第 7 日）',
        '港股': '新浪 hq rt_hkHSTECH 返回体日期字段 = 2026/10/06 16:08 → 10/6 已收盘（4,223.08 / +0.9418%）、10/7 今日待开 09:30（非休市）',
        '美股': 'stock_us_daily(IYH/XLV) 末行 = **2026-10-06**（XLV 167.09 / IYH 70.67）→ 10/6（周二）收盘已于北京 10/7 04:00 成型，**本档新增 8 行**',
        'rule': '三市场各自独立验证、不得互相外推（§3.107 / §3.119b / §3.122b）'},
    'base_total': TOTAL, 'base_file': BASEFILE,
    'base_revision': {'prev_total': None, 'delta': 0.0,
                      'reason': '本档交易日三验：A股 末行 = 2026-09-30（3,842.1946）仍休市、HSTECH 末行 = 2026-10-06（4,223.08）、'
                                'XLV 末行 = 2026-10-06（167.09）→ A股仍在长假、场外基金无净值发布 → '
                                '组合账面基准仍冻结于 9/30 修正收盘，**本档无修正**'},
    'tracks': {k: {'mv': v['mv'], 'pct_of_total': v['pct_of_total'], 'day_pct': v['day_pct']}
               for k, v in tracks.items()},
    'discipline_hstech_cumulative': {
        'cut1': {'pct': 0.5, 'amount': cut1_amt, 'triggered_on': '2026-09-29', 'settled_on': '2026-09-30',
                 'note': '9/29 收盘 4,249.62（−0.0089%）边际破位触发 → 9/30 按净值成交'},
        'cut2': {'pct': 0.5, 'amount': cut2_amt, 'triggered_on': '2026-10-02', 'settled_on': None,
                 'execute_at': '2026-10-08', 'execution_pending': True,
                 'basis': f'基准总资产 {TOTAL:,.2f} 元 × 0.5%（§3.114c / §3.123e 确定性口径）',
                 'targets': ['012348（天弘恒生科技联接A）', '513180（恒生科技ETF华夏）'],
                 'target_rule': '标的限「纯恒科」口径，不落在中概（513050 / 164906）'},
        'cumulative_amount': cut_cum,
        'hk_after': round(hk_after, 2), 'cash_after': round(cash_after, 2),
        'weight_after_pct': {'恒生科技': round(hk_after / TOTAL * 100, 2),
                             '现金': round(cash_after / TOTAL * 100, 2)},
        'prior_档口径': {'source': 'reports/daily/2026-10-04.md',
                        'hk_after': 29668.40, 'cash_after': 31117.41,
                        'weight_after_pct': {'恒生科技': 7.79, '现金': 8.17},
                        'correction_note': '该口径 = 31,572.84 − 1,904.44（只扣第 2 次减仓），'
                                           '未扣除第 1 次已成交的 1,882.46 元 → 本档统一为「累计扣除」'
                                           '（31,572.84 − 3,786.90 = 27,785.94 元 = 7.30%）；'
                                           '两口径并列披露、以累计口径为准（§3.123e）'},
        'note': '**本档不重复计入任何一次减仓**；第 2 次的判定权已于 10/2 收盘级锁定、执行权归 10/8'},
    'med_exposure': med, 'med_pct': round(med / TOTAL * 100, 2),
    'threshold_all_med': round(th_all, 2), 'threshold_a_sh_med': round(th_sh, 2),
    'non_med_total': round(B_nm, 2),
    'hk_total': round(hk_total, 2), 'hk_total_pct': round(hk_total / TOTAL * 100, 2),
    'hk_segments': {'pure_hstech': round(pure, 2), 'china_internet': round(cpo, 2),
                    'broad_hk': round(broad, 2)},
    'hk_southbound_gap_days': ['2026-10-02', '2026-10-05', '2026-10-06', '2026-10-07'],
    'hk_gap_day_index_today': 3,
    'hk_leg_pending': {
        'window_days': ['2026-10-02', '2026-10-05', '2026-10-06', '2026-10-07'],
        'priced_days': ['2026-10-02', '2026-10-05', '2026-10-06'], 'unpriced_days_today': ['2026-10-07'],
        'priced_segment_cum': {
            'low': hk_low, 'mid': hk_mid, 'high': hk_high,
            'method': (f'三段法笛卡尔积（纯恒科 {len(SEG["pure_hstech"]["cum"])} 值 × 中概 '
                       f'{len(SEG["china_internet"]["cum"])} 值 × 宽基 {len(SEG["broad_hk"]["cum"])} 值 = '
                       f'{len(outs_all)} 组）后对**合计值**取 min/max（§3.123b）；'
                       '10/2 + 10/5 + 10/6 三段按**几何复合**累积（§3.126c）；'
                       '§3.129a：跨档累积**禁止用前档区间端点当输入**，取前档 segments[].cum_pct 值列表做完整笛卡尔积'),
            'segments': {
                'pure_hstech': {'exposure': round(pure, 2), 'ret_pct_cum': SEG['pure_hstech']['cum']},
                'china_internet': {'exposure': round(cpo, 2),
                                   'ret_range_pct_cum': list(SEG['china_internet']['cum'])},
                'broad_hk': {'exposure': round(broad, 2),
                             'ret_range_pct_cum': list(SEG['broad_hk']['cum'])}},
            'source_file': 'data/processed/history/portfolio_pending_20261006.json#hk_pending_digest',
            'source_note': '10/6 盘后档以真实收盘价重算并覆盖同文件名（§3.121b）；HSTECH 10/6 收 4,223.08 / +0.9418%'},
        'unpriced_note': ('10/7（南向空窗第 4 日）08:00 尚无收盘价 → **不可测算**；'
                          '累积区间 = 10/2+10/5+10/6 已定价段 + 10/7 一个未知交易日；'
                          '**静态测算只可给区间上下界、不得作方向判断**（§3.108 条款 24）'),
        'priced': False, 'priced_partial': True, 'priced_for_today': False},
    'pending': {
        'as_of': '2026-10-07 08:00', 'state': 'preopen_estimate', 'finalized': False,
        'finalize_at': '2026-10-07 20:00（港股收盘后）',
        'settle_date': '2026-10-08',
        'component_a': {'desc': 'QDII 000369/016280 的 9/29 净值（基准净值日 9/28）→ 已覆盖 US 9/29',
                        'amount': qdii_out, 'trade_date_covered': '2026-09-29'},
        'component_b': {'desc': f'自 US 9/30 起未可观测段：IYH 9/30 {IYH_0930:+.2f}% × 10/1 {IYH_1001:+.2f}%'
                                f' × 10/2 {IYH_1002:+.2f}% × 10/5 {IYH_1005:+.4f}%'
                                f' × **10/6 {IYH_1006:+.2f}%（本档新增，IYH 70.91→70.67）**'
                                f' 复合 {comp_b*100:+.4f}%',
                        'trade_dates_covered': ['2026-09-30', '2026-10-01', '2026-10-02', '2026-10-05', '2026-10-06'],
                        'notional': round(notional_b, 2),
                        'low': round(b_low, 2), 'mid': round(b_mid, 2), 'high': round(b_high, 2),
                        'coef_range': [0.60, 0.90], 'coef_unstable': True,
                        'coef_note': '长假前后实测隐含系数 1.25~1.29（§3.118a），远超标定 0.72 / 实测 0.62'},
        'total_low': round(tot_low, 2), 'total_mid': round(tot_mid, 2), 'total_high': round(tot_high, 2),
        'unknown_sessions': ['2026-10-07'],
        'hk_leg': {'exposure': round(hk_total, 2), 'pct': round(hk_total / TOTAL * 100, 2),
                   'priced': False, 'priced_partial': True,
                   'priced_days': ['2026-10-02', '2026-10-05', '2026-10-06'], 'unpriced_days': ['2026-10-07'],
                   'reason': '港股 10/7 09:30 开盘、16:00 收盘 → 本档 08:00 无当日价格；10/2、10/5 与 10/6 已按真实收盘累积定价',
                   'priced_segment_ref': 'hk_leg_pending.priced_segment_cum',
                   'note': '南向空窗（10/2/10/5/10/6/10/7，本档为第 4 日）；静态测算只可给区间上下界、不得作方向判断（§3.108 条款 24）'},
        'unquantified': {'code': None, 'mv': 0.0, 'stale': False,
                         'note': '164906 最新净值日 = 9/29 且已真实兑现计入「恒生科技」赛道 → 无挂账项；'
                                 'pending_codes ∩ applied_codes = ∅'},
        'note': ('§3.112f / §3.118a：跨长假只给区间、禁止中枢点值。A 覆盖 US 9/29（不得在 B 重复）；'
                 'B 自 US 9/30 起（含 10/2 的 0.00%、US 10/5 的 +0.7244%、**US 10/6 的 −0.34%**）。'
                 '港股腿 10/2+10/5+10/6 三段已定价、10/7 未定价；'
                 'US 10/7 共 1 个交易日完全未知。')},
    'pending_consume': {
        'hold_decision': 'no_action',
        'reason': ('混合档必做待消化，但 08:00 时点可定价部分仅美股/QDII 腿（已在挂账口径内）与'
                   '港股腿 10/2+10/5+10/6 三段；港股 10/7 未定价；且组合唯一可执行的交易窗口 = 10/8'
                   '（A股 + 南向 + 港股通同时恢复）→ 本档不做任何赛道级调整'),
        'estimated_combo_return_pct': 0.0,
        'estimated_combo_pnl': 0.0,
        'attribution': 'A股 10/1-10/7 休市 → 场外基金无净值、场内无成交价；港股 10/7 尚未开盘 → '
                       '**当日可实现盈亏恒为 0，归因「标的不可定价」而非「市场持平」**（§3.107 / §3.121d）'},
    'defense_lines': {
        'hstech_4250': {'last': HS, 'prev_close': HS_PREV, 'state': 'close_level_break_confirmed',
                        'dist_pct': round((HS / 4250 - 1) * 100, 4), 'dist_pts': round(HS - 4250, 2),
                        'break_type': '非边际破位（10/2 收盘级首次触发，10/6 距防线 −0.6344%，幅度连续第 3 档收窄）',
                        'action_reserved': f'第 2 次 0.5% 纪律减仓 {cut2_amt:,.2f} 元（执行待 10/8）',
                        'verify_at': '2026-10-07 16:00（港股续市第 4 日，收盘价验证）',
                        'night_session': {'available': False,
                                          'note': '10/6 港股夜盘读数本档未采集入库 → 「数据暂缺」，'
                                                  '不得沿用 10/5 夜盘旧值（恒科 4,245 / 恒指 24,266）'},
                        'next_rule': '再破不叠加新纪律（同日防线只触发一次）；若回升站上 4,250 亦**不撤销**已登记减仓（§3.114c）'},
        'zz_consume_12100': {'last': ZZ, 'state': 'abv_line_last_known',
                             'dist_pct': round((ZZ / 12100 - 1) * 100, 4),
                             'next_line': 12000, 'next_line_dist_pct': round((ZZ / 12000 - 1) * 100, 2),
                             'verify_at': '2026-10-08（A股 复市）'},
        'a_med_reverse_1_5pct': {'proxy_pct': round(MED933_1D, 4), 'state': 'not_triggered',
                                 'verify_at': '2026-10-08（A股 复市）'},
        'sh_comp': {'last': SH}},
    'scenario': {
        'upside': ('港股 10/6 现货收盘 4,223.08（+0.9418%）已连续第 2 日修复、距 4,250 防线仅 −0.6344%，'
                   '且美股 10/6 三大指数续涨（道指 +0.49% / 标普 +0.58% / 纳指 +0.45%，标普与纳指双创收盘新高）'
                   '→ 恒生科技 10/7 仍有收复 4,250 的动能；**但已登记的第 2 次减仓 {:.2f} 元仍须于 10/8 执行**'
                   '（纪律不可撤销，§3.114c）'.format(cut2_amt)),
        'base': ('混合档第 4 日盘前：A股休市、港股 09:30 待开。组合账面基准冻结在 9/30 修正收盘 {:.2f} 元；'
                 '已定价增量 = 「美股/QDII 腿」（挂账区间 {:.2f} 元 ~ {:.2f} 元）'
                 '＋「港股腿 10/2+10/5+10/6 三段」（{:.2f} 元 ~ {:.2f} 元）；'
                 '港股 10/7 与 A股腿待 10/8')
                .format(TOTAL, tot_low, tot_high, hk_low, hk_high),
        'downside': ('① **美股医疗（XLV）10/6 −0.17%，为标普 11 大板块中唯一下跌**，与「三大指数创新高」'
                     '构成显著背离 → 组合美股标普医药腿（15.66%）相对收益走弱；'
                     '② **美债长端 10/6 仍高位（10Y 5.279%，仅 −2.32bp）** → 分母端压制恒科与医药估值，'
                     '且与「美股齐涨」构成方向背离，须并列；'
                     '③ **中东地缘二次升级（曼德海峡控制权争夺 + 油债相关性 35 年最高）** → '
                     '油价与运费二次冲高风险 → 通胀与长端利率反向传导；'
                     '④ **南向空窗第 4 日（港股通 10/1-10/7 全程关闭）** + 港股 10/5 成交缩量 32.7%（981.02 亿港元）、'
                     '10/6 量能连续第 2 日低于千亿 → 承接力量最薄，修复易被打断；'
                     '⑤ **日本央行 12 月加息概率升至 80%** + 美元回落至 102 下方 → 套息交易平仓风险，'
                     '对港股与新兴市场资金面构成尾部冲击；'
                     '⑥ US 10/7 一个交易日未知，QDII 挂账区间可能被系数漂移击穿（实测隐含系数 1.25~1.29）'),
    },
    'action': {'new_buy': 0, 'active_take_profit': 0, 'discipline_cut_today': 0,
               'discipline_cut_cumulative_registered': cut_cum,
               'note': ('混合档第 4 日 + 盘前：A股 休市、港股未开盘 → 赛道级动作全部为 0；'
                        '恒生科技 0.5% 纪律减仓累计 3,786.90 元已登记（第 1 次 9/30 已成交、第 2 次执行待 10/8），'
                        '**本档不重复计入**（10/5 +0.6191% 与 10/6 +0.9418% 的连续修复**不改变**已登记减仓的执行义务，§3.114c）；'
                        '医药敞口 39.23% 距 40% 上限 0.77pct，其中 A股腿仍无新增定价、美股腿随 US 10/6 微跌（XLV −0.17%）基本持平'
                        ' → 门槛方向不变；现金 7.67%（累计纪律后 8.66%）维持长假缓冲；'
                        '**唯一可执行窗口 = 10/8**（A股 + 南向 + 港股通同时恢复）')},
    'calendar': {'2026-10-01': 'A股休市 + 港股休市（国庆日）+ 港股通关闭；美股照常交易',
                 '2026-10-02': 'A股休市；**港股复市（周五，收 4,157.94 / −2.2556%）**；港股通关闭；美股照常；**美国 9 月非农**',
                 '2026-10-03~10-04': 'A股/港股/美股均休（周末）',
                 '2026-10-05': 'A股休市；**港股续市（周一，收 4,183.68 / +0.6191%）**；港股通关闭；'
                               '**美股 10/5 交易日（道指 +0.13% / 标普 +0.34% / 纳指 +0.61%，收盘成型于北京 10/6 04:00）**',
                 '2026-10-06': 'A股休市；**港股续市第 3 日（周二，收 4,223.08 / +0.9418%）**；港股通关闭；'
                               '**美股 10/6 交易日（道指 +0.49% / 标普 +0.58% / 纳指 +0.45%，标普与纳指双创收盘新高；'
                               'XLV −0.17% 为 11 板块唯一下跌，收盘成型于北京 10/7 04:00）**',
                 '2026-10-07（今日）': 'A股休市；**港股续市第 4 日（周三，09:30 开 / 16:00 收）**；港股通关闭；'
                                     '美股 10/7 交易日（收盘将于北京 10/8 04:00 成型）；'
                                     '今晚 21:45 美国 9 月标普全球服务业 PMI 终值 / 22:00 美国 9 月 ISM 非制造业 PMI',
                 '2026-10-08': 'A股复市 + 港股通恢复 → 挂账一次性释放与对账（唯一可执行窗口）；'
                               '第 2 次恒科 0.5% 纪律减仓 {:.2f} 元执行日；'
                               '央行 12,000 亿元 3 个月期买断式逆回购投放；**美联储 9 月会议纪要（10/8）**'.format(cut2_amt)},
    'calendar_by_market': {
        'A股': '10/1-10/7 休市 → 10/8 复市（10/10 周六休）',
        '港股': '10/1 休市 1 天 → 10/2 复市 → 10/3-4 周末 → **10/5-10/7 正常交易**（10/19 重阳节翌日休）',
        '港股通(南向)': '10/1-10/7 全程暂停 → 10/8 恢复',
        '美股': '10/1-10/7 照常交易（5 个交易日）；10/2、10/5、10/6 三个收盘已分别于 10/4、10/6、10/7 档归档'},
}

json.dump(out, open(os.path.join(HIST, f'portfolio_preopen_{TODAY.replace("-", "")}.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
print(f'\n已保存 portfolio_preopen_{TODAY.replace("-", "")}.json')

pend = {
    'date': TODAY,
    'as_of': '2026-10-07 08:00（盘前）',
    'state': 'preopen_estimate',
    'finalized': False,
    'finalize_at': '2026-10-07 20:00（港股 10/7 收盘价 16:00 后成型）',
    'finalized_note': ('§3.121b：混合档 `portfolio_pending_<DATE>.json` 的正式版归属当日 20:00 盘后档，'
                       '以港股 10/7 收盘价重算并覆盖同文件名；本档为 08:00 预登记版（state=preopen_estimate），'
                       '**港股腿 10/7 未经收盘价定价**（10/2、10/5、10/6 三段已按真实收盘累积定价）'),
    'session_type': '混合档第 4 日（A股休市 + 港股续市）',
    'base_total': TOTAL, 'base_file': BASEFILE,
    'base_guard_dev': round(dev, 4), 'base_guard_rule': '|Σ tracks.mv − total_mv| < 1.5',
    'base_note': '9/30 修正收盘口径（tracks[].mv 求和校验通过）',
    'realized_pnl': 0.0, 'realized_pct': 0.0,
    'realized_note': ('A股 10/1-10/7 休市（场外基金无净值发布、场内 ETF 无成交价）；'
                      '港股 10/7 09:30 开盘，08:00 尚无当日价格 → 本档账面可实现盈亏恒为 0，'
                      '属「标的不可定价」而非「市场持平」（§3.107 / §3.121d）'),
    'hk_close': {'index': 'HSTECH', 'date': '2026-10-06', 'close': HS, 'prev_close': HS_PREV,
                 'pct': round((HS / HS_PREV - 1) * 100, 4),
                 'priced_for_today': False,
                 'note': ('10/6 为港股上一交易日（收 4,223.08 / +0.9418%）；本档 08:00 时点 10/7 尚未开盘 '
                          '→ 引用 10/6 收盘作基准，**不得当作 10/7 价格**；10/6 收盘已计入 '
                          'hk_leg priced_segment_cum 的累积段')},
    'hk_leg': {'exposure': round(hk_total, 2), 'pct': round(hk_total / TOTAL * 100, 2),
               'priced': False, 'priced_partial': True, 'segments': out['hk_segments'],
               'priced_days': ['2026-10-02', '2026-10-05', '2026-10-06'], 'unpriced_days': ['2026-10-07'],
               'priced_segment_cum': out['hk_leg_pending']['priced_segment_cum']},
    'pending_consume': out['pending_consume'],
    'qdii_forecast': {'component_a': out['pending']['component_a'],
                      'component_b': out['pending']['component_b'],
                      'total_low': out['pending']['total_low'], 'total_mid': out['pending']['total_mid'],
                      'total_high': out['pending']['total_high'],
                      'unknown_sessions': out['pending']['unknown_sessions'],
                      'coef_note': out['pending']['component_b']['coef_note']},
    'tracks': out['tracks'],
    'weights': {k: v['pct_of_total'] for k, v in out['tracks'].items()},
    'tracks_weight_after_cumulative_discipline': out['discipline_hstech_cumulative']['weight_after_pct'],
    'discipline_hstech_cumulative': out['discipline_hstech_cumulative'],
    'med_exposure': med, 'med_pct': out['med_pct'],
    'threshold_all_med': out['threshold_all_med'], 'threshold_a_sh_med': out['threshold_a_sh_med'],
    'defense': out['defense_lines'],
    'chain_0pct_row_inserted': False,
    'note': ('混合档第 4 日盘前台账（**非正式版**）：「美股/QDII 腿」已定价至 US 10/6、「港股腿」10/2+10/5+10/6 三段'
             '已按真实收盘累积定价 / 10/7 未定价、「A股腿」未定价；'
             '20:00 盘后档将以港股 10/7 收盘价重算并覆盖本文件（§3.121b / AGENTS #80）；'
             '未向链式序列插入 0% 行（`chain_0pct_row_inserted: false`，§3.108 条款 22）'),
}
json.dump(pend, open(os.path.join(HIST, f'portfolio_pending_{TODAY.replace("-", "")}.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
print(f'已保存 portfolio_pending_{TODAY.replace("-", "")}.json（state=preopen_estimate, finalized=false）')
