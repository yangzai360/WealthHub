# 长赢指数投资计划-150份 (LONG_WIN)

> 外部参考组合（且慢平台，盈米基金提供）。用户操作参考来源之一，与 WealthHub 用户持仓高度重合。

## 组合信息
- **主理人**: ETF拯救世界  |  **风险等级**: 中高风险  |  **成立**: 2015-07-01
- **当前净值**: 1.6803 (2026-08-06)  |  累计收益: 68.03%
- **已投**: 109/150 份  |  最大回撤: 19.79%  |  夏普: 0.2952
- **关注人数**: 444,808 人开启, 128,975 人在投

## 数据文件
| 文件 | 说明 |
|------|------|
| `meta.json` | 组合元数据与最新指标 |
| `composition-2026-08-06.json` | 持仓快照（大类 + 成分基金，按日期归档） |
| `adjustments.json` | 全部 261 条调仓记录（2015-08 至今） |
| `data/processed/reference/long-win-nav.csv` | 净值历史（2698 条，增量追加） |

## 数据接口（抓取方式，见 knowledge/technical-notes.md 第 9 节）
- 组合详情: `https://qieman.com/pmdj/v2/long-win/plan?prodCode=LONG_WIN`
- 调仓记录: `https://qieman.com/pmdj/v2/long-win/plan/adjustments?desc=true&prodCode=LONG_WIN`
- 净值历史: `https://qieman.com/pmdj/v2/long-win/plan/nav-history?prodCode=LONG_WIN`
- 资产分布: `https://qieman.com/pmdj/v2/long-win/plan/clz-distribution`
- 指数历史: `https://qieman.com/pmdj/v1/utils/index/000905.SH/history?start=YYYY-MM-DD&end=YYYY-MM-DD`

*快照日期: 2026-08-06 | 由 agent 抓取归档*
