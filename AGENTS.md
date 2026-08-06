# AGENTS.md — WealthHub 代理工作手册

> 本文件是进入本仓库的 agent 的**默认上下文入口**。每次会话开始/任务触发时自动加载。
> 核心原则：**先读知识库，再动手执行**。

---

## 0. 仓库定位

WealthHub = Sean & Jasy 的家庭理财工作台（3 账户：2 支付宝基金 + 1 场内股票）。
数据主权在本地 git 仓库，所有记录可审计、可复现。

## 1. 📖 知识库在哪（必须知道）

| 文件 | 内容 | 何时加载 |
|------|------|----------|
| **`docs/knowledge/technical-notes.md`** | 数据接口实测结论（可用/不可用）、运行时技术坑与规避、环境约定、DeepSeek 调用模板 | **执行任何数据抓取/行情/分析/报告任务前，必读** |
| `README.md` | 账户体系、目录结构、记录规范（快照 CSV 模板、成本法、涨跌配色） | 首次进入仓库时通读 |
| `accounts/*.md` | 各账户档案（持有人、数据约定、历史异常说明） | 涉及具体账户时读取 |

## 2. 🚀 技术执行前强制检查（Checklist）

任何 agent 触发以下动作前，先完成：
1. [ ] 读 `docs/knowledge/technical-notes.md`（接口清单 + 技术坑）
2. [ ] 确认 Python 用 `/Users/jieyang/.workbuddy/binaries/python/envs/default/bin/python`（venv，含 akshare 1.18.81）
3. [ ] 读持仓基准：`holdings/<account>/` 下按日期取最新 `snapshot-*.csv`
4. [ ] 数据写入前校验本地最新日期，**只增量写入**
5. [ ] 报告生成后 `git add -A && git commit -m "<描述>"`，可 `git push origin master`（推送失败不阻塞）

## 3. ⚠️ 速查：最容易踩的 4 个坑

1. **DeepSeek v4-flash 调用 `max_tokens` 必须 8000+**，否则思考占满 token、content 为空（模板见知识库 §3.4）
2. **东财 push2 指数接口被系统代理拦截**（`127.0.0.1:49474`）——直接用新浪源接口（`*_sina()`），别反复重试东财
3. **CSV 一律 `encoding='utf-8-sig'` 打开**，否则 BOM 导致列名读不到
4. **git 命令用 `--no-pager`**，避免分页器卡住管道输出

## 4. 🗂 数据目录速览

```
accounts/     账户档案        holdings/     持仓快照 CSV（单一真相源）
data/raw/     原始截图/导出    data/processed/history/  历史行情（增量 CSV）
data/processed/news/   新闻存档（JSON）   data/processed/events/  事件库（情绪+历史影响）
reports/daily/   日报（每日单文件 YYYY-MM-DD.md，盘前/盘中/盘后为其中章节）
reports/weekly/  周报（按周）  scripts/      自动化脚本
docs/knowledge/  技术知识库
```

## 5. 🔄 定时任务（3 个时段，共用本手册，输出到同一日报文件）

| 时段 | 任务 | 触发 | 产物 |
|------|------|------|------|
| 盘前 | 每日盘前分析 | 08:00 | 创建 `reports/daily/YYYY-MM-DD.md`，写入「一、盘前分析」 |
| 盘中 | 每日盘中调仓建议 | 13:45 | 同一文件追加「二、盘中调仓建议」 |
| 盘后 | 每日盘后复盘 | 20:00 | 同一文件追加「三、盘后复盘」（周日另生成周报 reports/weekly/） |

> **单文件日报约定**：每天只有 1 个日报文件 `reports/daily/YYYY-MM-DD.md`，三时段按章节追加，禁止新建独立文件；文件已存在时仅追加/更新对应章节，禁止覆盖其他章节。

## 5.1 📲 微信通知（每次执行完成后的最后一步）

- 报告写入/更新完成后，**必须通过微信通知用户**：①报告名称与档位（盘前分析/盘中调仓建议/盘后复盘）②核心结论摘要（2-3 句，含组合当日估算收益与关键赛道判断）③报告文件存放路径
- 微信通知失败不阻塞主流程，但仍需完成 git 提交
- 前置条件：用户在 WorkBuddy/Claw 设置中配置了微信客服号绑定（未绑定时通知无法送达，任务仍正常完成报告）

任务执行 = 7 步链路（读持仓→行情→新闻→情绪+历史影响→策略→报告归档+git→**微信通知**），差异化参数在各自任务指令中。

## 6. 📝 知识库维护规则

- 接口可用性、技术坑、环境变化 → 更新 `docs/knowledge/technical-notes.md`
- 本文件（AGENTS.md）只放**索引和速查**，不放细节；细节一律下沉到知识库
- 修改后提交推送：`git add -A && git commit -m "docs: ..." && git push origin master`
