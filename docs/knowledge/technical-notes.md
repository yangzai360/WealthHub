# WealthHub 技术知识库

> 本文件是仓库的**技术执行手册**。任何 agent（或人）在 WealthHub 内执行数据抓取、行情更新、情绪分析、报告生成等任务前，**必须先读本文件**。
> 记录内容 = 接口实测结论 + 运行时技术坑 + 环境约定。来源均为 2026-08-06 实测，有环境变化需同步更新。

---

## 1. 运行环境（固定约定）

| 项 | 值 | 说明 |
|----|----|------|
| Python 解释器 | `/Users/jieyang/.workbuddy/binaries/python/envs/default/bin/python` | venv，已装 akshare 1.18.81 |
| 兜底解释器 | `/Users/jieyang/.workbuddy/binaries/python/versions/3.13.12/bin/python3` | venv 失效时使用，无 akshare |
| akshare 版本 | 1.18.81 | 首次安装耗时约 18 分钟（依赖编译），勿频繁重建 venv |
| DeepSeek Key | `~/.pi/agent/auth.json` → `deepseek.key` | API base: `https://api.deepseek.com` |
| DeepSeek 模型 | `deepseek-v4-flash`（快速+深度思考） | 需要更强推理时用 `deepseek-v4-pro` |
| Git | 仓库根目录执行 `git add -A && git commit`，可 `git push origin master` | 推送失败不阻塞主流程 |
| 系统代理 | `127.0.0.1:49474`（WorkBuddy 注入） | **拦截东方财富 push2 域名**，见 §3 |

---

## 2. 数据接口实测结论（2026-08-06 验证）

### 2.1 ✅ 可用接口（优先使用）

| 接口 | 用途 | 实测数据 |
|------|------|----------|
| `ak.fund_etf_spot_em()` | 场内 ETF 实时行情 | 持仓 513050/159928/159938/512170/513180 全部抓到 |
| `ak.fund_open_fund_info_em(symbol, indicator="单位净值走势")` | 场外基金净值（天天基金源） | 支付宝账户核心数据源，000369 拿到净值 |
| `ak.stock_zh_index_spot_sina()` | A股指数实时（新浪源） | 上证 3872.19 / 中证消费 000932 |
| `ak.stock_hk_index_spot_sina()` | 港股指数实时（新浪源） | 恒生科技 HSTECH 4846.59 |
| `ak.stock_zh_a_daily(symbol="sz002410", adjust="qfq")` | A股个股日线（新浪源） | 广联达；深市 `sz` 前缀 / 沪市 `sh` 前缀 |
| `ak.stock_zh_index_daily(symbol="sh000932")` | 指数日线（新浪源） | 中证消费日线 |

### 2.2 ❌ 不可用接口（被本地代理拦截）

| 接口 | 原因 | 替代方案 |
|------|------|----------|
| `ak.stock_zh_index_spot_em()` | 东财 push2 域名被代理拦截，绕过代理直连也被服务器拒绝 | 用 `stock_zh_index_spot_sina()` |
| `ak.stock_hk_index_spot_em()` | 同上 | 用 `stock_hk_index_spot_sina()` |
| `ak.stock_zh_a_spot_em()` | 同上 | 用 `stock_zh_a_daily()` 或 `fund_etf_spot_em()` |

> **规则**：接口失败自动重试 2 次；仍失败在报告中标注「数据暂缺」，**不中断主流程**。

---

## 3. 已知技术坑与规避（按严重度排序）

### 3.1 🔴 DeepSeek v4-flash 深度思考占满输出 token

**现象**：调 `deepseek-v4-flash` 时若 `max_tokens` 设小（如 100/300），深度思考（reasoning_content）会先占满输出预算，导致 `content` 为空 → 情绪分析等任务拿不到结果。

**规避**：**`max_tokens` 必须设 8000+**（模型配置上限 8192），temperature 建议 0.3。
**验证方式**：API 响应检查 `choices[0].message.content` 非空；`reasoning_content` 字段存在即表示模型在深度思考（属正常）。

### 3.2 🔴 东方财富 push2 域名被系统代理拦截

**现象**：`stock_zh_index_spot_em()` 等东财指数/全市场接口返回代理错误；`env -u HTTP_PROXY ...` 绕过代理直连仍被服务器拒绝（非代理问题，是域名策略）。

**规避**：不要浪费时间重试东财指数接口，**直接用新浪源**（见 §2.1）。

### 3.3 🟡 系统代理影响所有外部调用

**说明**：WorkBuddy 注入 `HTTP_PROXY/HTTPS_PROXY=127.0.0.1:49474`，绝大多数接口正常，仅东财 push2 被拦截。GitHub clone 走代理会 502（`git:` 方式安装扩展会卡死，改用 npm 源）。

### 3.4 🟡 DeepSeek 调用代码模板（可直接复用）

```python
import json, urllib.request
with open('/Users/jieyang/.pi/agent/auth.json') as f:
    key = json.load(f)['deepseek']['key']
data = {
    "model": "deepseek-v4-flash",
    "messages": [{"role": "user", "content": prompt}],
    "max_tokens": 8000,        # 关键!思考会占 token
    "temperature": 0.3,
}
req = urllib.request.Request("https://api.deepseek.com/chat/completions",
    data=json.dumps(data).encode(),
    headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
with urllib.request.urlopen(req, timeout=120) as resp:
    result = json.load(resp)
content = result['choices'][0]['message']['content']
```

### 3.5 🟡 CSV 编码 BOM 坑

**现象**：Excel/部分工具导出的 CSV 带 UTF-8 BOM，`csv.DictReader` 读不到列名（第一列名带 `\ufeff`）。
**规避**：一律 `open(path, encoding='utf-8-sig')`。

### 3.6 🟡 git 分页器卡住管道输出

**现象**：`git log` / `git show` 在非交互 shell 里打开分页器，管道命令卡死。
**规避**：一律用 `git --no-pager log` / `git --no-pager show`。

### 3.7 🟢 macOS 没有 `timeout` 命令

**现象**：Linux 的 `timeout 60 cmd` 在 macOS 不存在。
**规避**：长命令用后台执行（WorkBuddy run_in_background）或 `gtimeout`（需 coreutils）。

### 3.8 🟢 NODE_OPTIONS 干扰系统 node/npm（仅 pi 相关）

**现象**：WorkBuddy 注入的 `NODE_OPTIONS` 让系统 node 报错，导致 `/usr/local/bin/pi` 等工具异常。
**规避**：执行 pi 相关命令前 `env -u NODE_OPTIONS ...`。

---

## 4. 定时任务运行约定（3 个时段共用，单文件日报）

| 时段 | 任务 | 触发 | 产物 |
|------|------|------|------|
| 盘前 | WealthHub-每日盘前分析 | 每日 08:00 | 创建 `reports/daily/YYYY-MM-DD.md`，写入「一、盘前分析」章节 |
| 盘中 | WealthHub-每日盘中调仓建议 | 每日 14:15 | 同一文件追加「二、盘中调仓建议」章节 |
| 盘后 | WealthHub-每日盘后复盘 | 每日 20:00 | 同一文件追加「三、盘后复盘」章节；**周日额外生成周报** `reports/weekly/YYYY-Www-周报.md` |

> **单文件日报约定**：每天只有 1 个日报文件 `reports/daily/YYYY-MM-DD.md`（如 2026-08-06.md），三个时段按章节追加，**不得新建独立文件**；文件已存在时仅追加/更新对应章节，禁止覆盖其他章节。账户快照分析（如 sean/jasy/stock 三账户）归入当日文件「附录」章节。

- 统一 6 步链路：读持仓 → 行情更新 → 新闻抓取 → 情绪+历史影响 → 策略计算 → 报告归档+git 提交
- 非交易日（周末/节假日）：跳过行情与调仓，仅整理新闻，在当日文件输出简版章节并注明「非交易日」
- 数据目录：行情 `data/processed/history/`（增量 CSV）、事件 `data/processed/events/`（JSON）、新闻 `data/processed/news/`
- 事件库积累：盘后任务把「当日事件 ↔ 当日实际走势」回填事件库，逐步形成「事件→赛道 3/5/10 日走势」样本库

---

## 5. 目录自适应评估原则（每次执行第一步执行）

扫描仓库结构，按「数据与代码分离、报告按时间归档、历史资产可追溯」三原则评估：
- 合理 → 直接沿用，不做无意义重构
- 不合理 → 先输出「目录调整方案」再迁移，禁止文件散落根目录
- 持仓基准 / 历史行情 / 脚本 / 报告必须物理分目录

---

*最后更新：2026-08-06。环境或接口有变化时，先改本文件再执行任务。*
