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
| `ak.stock_zh_index_daily(symbol="sh000932")` | 指数日线（新浪源） | 中证消费日线；**兼作 spot 缺失兜底**（见 §3.9） |
| `ak.stock_us_daily(symbol="XLV")` | 美股 ETF 日线（新浪源，2026-08-07 盘前实测） | XLV（医疗保健精选）/IYH（医疗）/QQQ（纳指100）/DIA（道指）均可用，更新到隔夜收盘；**盘前档美股医疗代理首选 XLV/IYH** |
| `ak.stock_us_daily(symbol="IYH")` | 美股医疗 ETF 日线（新浪源，2026-08-11 盘前实测） | **IYH 数据更新及时，XLV 偶发滞后 1-2 个交易日**（8/11 盘前 XLV 只到 8/7、IYH 已到 8/10 收盘 +1.63%）——**美股医疗方向优先用 IYH，XLV 滞后时作代理并标注** |
| `ak.index_us_stock_sina(symbol=".IXIC")` | 美股指数日线（新浪源，2026-08-07 实测） | .IXIC/.DJI 可用但**间歇 IndexError**（重试 2 次仍失败则用 QQQ/DIA 代理）；**.INX/SPY 滞后一天**（盘前只到前日，勿用其判断隔夜方向） |

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

### 3.9 🟡 新浪源指数代码带 sh/sz 前缀（2026-08-06 盘中实测）

**现象**：`stock_zh_index_spot_sina()` 返回的「代码」列是 `sh000001`/`sz399006` 格式，直接 `.zfill(6)` 匹配 `000001` 会失败，导致 A股指数盘中抓取静默漏数据。
**规避**：用 `re.sub(r"\D", "", code)` 剥离字母前缀后再匹配 6 位代码。
**补充**：`fund_open_fund_info_em()` 场外净值存在 **T+1 延迟**——盘中档（13:45）只能拿到前一日或前两日净值（如 8/6 盘中仅到 8/4-8/5），当日净值需收盘后更新，属正常现象，报告中注明「净值 T+1 更新」即可，勿误判为接口故障。
**补充2（2026-08-06 盘后实测）**：`stock_zh_index_spot_sina()` 存在**间歇性数据缺失**——同一天多次调用可能某次缺上证指数（000001）等条目，`df[df["code6"]==code]` 匹配为空即静默漏数据。**规避**：盘后/收盘数据不要依赖 spot，直接用 `stock_zh_index_daily(symbol="sh000001"/"sz399006"/"sh000932")` 取日线最后一行收盘价 + 与前一交易日算涨跌幅（一次调用拿全，稳定可靠）。
**补充3（CSV 写入）**：`indices.csv` 表头为 `type,date,name,code,close,pct_change,note`（首列 `type` 固定 `index`；美股行用 `type=us_index` 区分）；`etf_intraday.csv` 表头 `date,code,name,price,pct,amount_wan,note`；`fund_nav.csv` 表头 `date,code,name,nav_date,nav,pct`。增量写入 key 必须**包含 note 字段**（如 `(date,code,note)`），否则盘中行与收盘行互相误判已存在而漏写。脚本写入行元素须全部 `str()` 转换，否则 `",".join` 对 float 报 TypeError。
**补充4（fund_nav.csv name 列，2026-08-07 踩坑）**：增量追加 fund_nav.csv 时第 3 列 `name` 是基金中文名，**不要用 code 占位**（会污染历史库，需事后修复）。名称映射建议维护在脚本内字典；QDII 基金净值存在 T+1~T+2（如广发全球医疗 000369/016280 在 8/7 早盘仅更新到 8/5），属正常现象。
**补充5（盘前档美股口径）**：北京时间早盘抓美股，判断隔夜方向优先用 `stock_us_daily` 的 ETF 代理（QQQ 纳指 / DIA 道指 / XLV 医疗），`.INX` 滞后一天不可用；涨跌幅由日线最后两行收盘价自行计算（接口不返回 pct）。
**补充6（个股盘中实时，2026-08-07 盘中实测）**：A股个股**盘中实时价暂无可靠接口**——`stock_zh_a_spot()`（新浪全市场）返回 HTML 被代理污染（JSONDecodeError），`stock_zh_a_daily(symbol="sz002410")` 盘中最后一行只到**前一交易日**（无当日 bar）。盘中档对个股（广联达/通威）用指数近似估算并在报告标注：广联达(软件)→创业板指、通威(光伏)→上证指数保守口径。盘后收盘价仍可用 `stock_zh_a_daily` 更新。
**补充7（盘后档收盘口径，2026-08-07 盘后实测）**：
- A股指数收盘**统一用 `stock_zh_index_daily(symbol=...)` 日线**（sh000001/sz399006/sh000932 前缀），末行收盘价 + 与前一交易日算涨跌幅，一次调用拿全、稳定可靠；港股仍用 `stock_hk_index_spot_sina`（收盘后即收盘值）
- 个股收盘用 `stock_zh_a_daily(symbol, adjust="qfq")`，同样末两行算涨跌幅——**盘中指数近似法误差可能很大**（实测 8/7 广联达近似 +2.69% vs 实际 **-2.19%**、通威近似 +0.77% vs 实际 **+6.26%**），盘后复盘必须用真实个股数据重算并修正盘中估算
- CSV 增量判重 key **用整行（全部列）**最稳妥（含 note 字段区分盘中/收盘），盘中脚本若用前 N 列会互判已存在而漏写收盘行
- 场外基金 8/7 收盘后当日净值仅部分更新（医药/恒科类通常 20:00 前出，QDII T+1~T+2），盘中档基金净值多为 T+1，属正常

---

## 4. 定时任务运行约定（3 个时段共用，单文件日报）

| 时段 | 任务 | 触发 | 产物 |
|------|------|------|------|
| 盘前 | WealthHub-每日盘前分析 | 每日 08:00 | 创建 `reports/daily/YYYY-MM-DD.md`，写入「一、盘前分析」章节 |
| 盘中 | WealthHub-每日盘中调仓建议 | 每日 13:45 | 同一文件追加「二、盘中调仓建议」章节 |
| 盘后 | WealthHub-每日盘后复盘 | 每日 20:00 | 同一文件追加「三、盘后复盘」章节；**周日额外生成周报** `reports/weekly/YYYY-Www-周报.md` |

> **单文件日报约定**：每天只有 1 个日报文件 `reports/daily/YYYY-MM-DD.md`（如 2026-08-06.md），三个时段按章节追加，**不得新建独立文件**；文件已存在时仅追加/更新对应章节，禁止覆盖其他章节。账户快照分析（如 sean/jasy/stock 三账户）归入当日文件「附录」章节。

- 统一 7 步链路：读持仓 → 行情更新 → 新闻抓取 → 情绪+历史影响 → 策略计算 → 报告归档+git 提交 → **微信通知**（含报告名称/档位 + 核心结论摘要 + 文件路径；通知失败不阻塞主流程）
- 非交易日（周末/节假日）：跳过行情与调仓，仅整理新闻，在当日文件输出简版章节并注明「非交易日」
- 数据目录：行情 `data/processed/history/`（增量 CSV）、事件 `data/processed/events/`（JSON）、新闻 `data/processed/news/`
- **新闻 schema（2026-08-06 起）**：每条新闻必须含 `source_url` 字段（来源链接，抓取不到留空字符串）；报告「新闻与情绪分析」章节中关键新闻（情绪强度≥60 或影响方向明确）用 markdown 超链接 `[标题](source_url)` 输出，可直接点击跳转原文，无链接保持纯文本
- **脱敏保护**：build_site.py 已对 markdown 超链接 URL 做保护（脱敏前暂存 → 处理完还原），URL 不会被金额规则误伤；站点上新闻链接可正常点击跳转
- 事件库积累：盘后任务把「当日事件 ↔ 当日实际走势」回填事件库，逐步形成「事件→赛道 3/5/10 日走势」样本库

---

## 5. 目录自适应评估原则（每次执行第一步执行）

扫描仓库结构，按「数据与代码分离、报告按时间归档、历史资产可追溯」三原则评估：
- 合理 → 直接沿用，不做无意义重构
- 不合理 → 先输出「目录调整方案」再迁移，禁止文件散落根目录
- 持仓基准 / 历史行情 / 脚本 / 报告必须物理分目录

---

## 6. ⚠️ 站点隐私坑（VuePress 公开站必须遵守）

**问题**：VuePress 内置 git 插件会无条件把提交信息注入每个页面的 JS 数据（contributors/changelog），即使 `repo` 未配置、`lastUpdated/contributors` 关闭也无法阻止（rc.30 实测）。注入内容包括：
- contributor 主页链接 `https://github.com/yangzai`（点击即进用户 GitHub 主页 → 公开仓库 → 未脱敏数据）
- 提交邮箱 `yangzai360@icloud.com`、用户名、commit message/hash
- `themePlugins.git:false` 在 rc.30 有 bug（SSR 加载 GitChangelog css 报 `ERR_UNKNOWN_FILE_EXTENSION`）

**解法（已落地）**：`scripts/clean_dist.py` 在 `vuepress build` 后运行（deploy.yml 已接入），把仓库 URL/主页链接/用户名/邮箱全部替换为不可达占位。**任何新页面/新组件上线后必须跑 `python3 scripts/clean_dist.py` 并验证 `grep -r github.com/yangzai docs/.vuepress/dist/` 无结果**。
- 不要在 config.ts 配 `repo`（导航栏会出现 GitHub 图标链接）
- 修改站点后验证清单：①页面 200 ②dist 无 `github.com/yangzai` / 个人邮箱 ③node --check 页面 JS 语法完整

---

## 7. ⚠️ VuePress 2 组件注册坑（图表不显示）

**问题**：Markdown 里写了 `<DashboardCharts />` 但页面空白无图表。根因：**VuePress 2 不会自动注册 `.vuepress/components/` 下的组件**（那是 VuePress 1 的旧特性），组件从未被打包渲染——构建产物中无任何组件代码可验证（`grep 赛道配置分布 dist/assets/*.js` 为空）。

**解法（已落地）**：新建 `docs/.vuepress/client.ts`，用 `defineClientConfig + enhance({ app }) { app.component('DashboardCharts', DashboardCharts) }` 手动注册全局组件。

**验证方法**：
- 构建后 `grep -c "图表加载中" docs/.vuepress/dist/index.html` ≥ 1（组件 SSR 占位出现）
- `grep -c "赛道配置分布" docs/.vuepress/dist/assets/app-*.js` ≥ 1（组件代码进包）
- app.js 含 echarts（大小 ~1.2MB）
- ⚠️ 线上验证用 `git clone -b gh-pages` 拉分支检查最可靠，curl 可能被本地代理污染（大小/内容对不上、502）

---

## 8. 专有名词速查

### 乖离率（BIAS, Bias Ratio）
- **定义**：衡量价格（或指数）偏离其 N 日移动平均线的相对程度
- **公式**：`BIAS(N) = (当日收盘价 − N日移动均线) ÷ N日移动均线 × 100%`
- **含义**：正值=价格在均线上方（正乖离，短期涨多）；负值=在下方（负乖离，短期跌多）
- **用法**：乖离过大 → 价格"跑太快"，有回归均线的引力。正乖离过高（超买）警惕回调；负乖离过大（超卖）可能反弹
- **常用参数**：6 日 / 12 日 / 24 日；震荡市效果较好，强趋势市中乖离会持续偏大，须结合趋势与成交量判断
- **配套**：常与 KDJ / MACD 组合用于短线择时；可应用于个股、指数、板块、ETF

### 夏普比率（Sharpe Ratio）
- **定义**：衡量"每承担 1 单位风险能换来多少超额收益"的风险调整后收益指标
- **公式**：`(组合收益率 − 无风险收益率) ÷ 组合收益率标准差`
- **用法**：越高越好（>1 可接受，>2 优秀）；本仓库默认无风险基准 = 十年国债收益率

### 赛道集中度
- **定义**：单一赛道持仓市值占组合总资产的比例
- **约束**：单赛道上限默认 40%；超过即提示集中度风险

### 最大回撤（Max Drawdown）
- **定义**：历史区间内，从任一峰值到后续最低点的最大跌幅百分比
- **用法**：衡量组合最坏情况下的亏损幅度，用于风险预算与仓位控制

### 无风险基准利率（Risk-free Rate）
- **定义**：理论上无违约风险的收益率，常用作超额收益的基准
- **本仓库取值**：中国 10 年期国债收益率（如 2026-08-05 为 1.70%）

---

## 9. 且慢（qieman.com）数据接口与参考组合

**背景**：用户的 LONG_WIN（长赢指数投资计划-150份，主理人 ETF拯救世界）是主要操作参考来源，与用户持仓高度重合（15 只基金重合，市值约 21.6 万）。数据已落库 `reference-portfolios/long-win/`。

### 9.1 可用接口（2026-08-07 实测，公开可访问，无需登录）

| 接口 | 说明 |
|------|------|
| `GET https://qieman.com/pmdj/v2/long-win/plan?prodCode=LONG_WIN` | 组合详情（指标/大类 composition/38 个成分基金 prodSummaries） |
| `GET https://qieman.com/pmdj/v2/long-win/plan/adjustments?desc=true&prodCode=LONG_WIN` | **全部调仓记录**（261 条，含 fundCode/份数/调仓日期/说明文章 url） |
| `GET https://qieman.com/pmdj/v2/long-win/plan/nav-history?prodCode=LONG_WIN` | 净值历史（2698 条，2015-07 起，字段 navDate/nav/dailyReturn） |
| `GET https://qieman.com/pmdj/v2/long-win/plan/clz-distribution` | 大类资产分布历史（541KB，各时段配置比例） |
| `GET https://qieman.com/pmdj/v1/utils/index/000905.SH/history?start=2015-07-01&end=2026-08-06` | **指数历史数据**（中证500；hs300 同理）——"基金/指数历史数据"可从此拿 |
| `POST https://qieman.com/alfa/v1/graphql` | GraphQL（operationName: Longwin / LongWinNavHistory / LongWinAcrHistory 等，需带浏览器同源 header） |

### 9.2 抓取方式（重要经验）
- **页面是 Taro/SSR SPA**：`curl` 只能拿到 detail 页的部分 SSR 数据（大类配置），**基金级持仓/调仓记录必须浏览器渲染或直接调 REST API**
- **最可靠方式**：直接 curl REST API（`/pmdj/v2/...`），返回纯 JSON，无需登录，Referer 加 `https://qieman.com/` 即可
- GraphQL introspection 被禁用；GraphQL 需正确 operationName + variables（可从浏览器 DevTools 抓）
- **浏览器渲染**：系统 Chrome headless + playwright-core（`/Users/jieyang/.workbuddy/binaries/node/workspace/node_modules/playwright-core`），`executablePath: /Applications/Google Chrome.app/...`，拦截 response 保存 graphql/pmdj 响应
- ⚠️ 且慢官方还有 **Qieman MCP**（qieman.com/mcp 免费申请 API Key，72 个工具含基金历史净值/组合穿透）——若需批量基金历史数据可申请接入

### 9.3 落库约定（reference-portfolios/）
- `reference-portfolios/<poCode>/meta.json` — 组合元数据与最新指标（快照式）
- `reference-portfolios/<poCode>/composition-YYYY-MM-DD.json` — 持仓快照（按日期归档，含大类+成分基金代码/份数/占比/累计收益）
- `reference-portfolios/<poCode>/adjustments.json` — 调仓记录全量（事件型，按 adjustmentId 增量追加）
- `data/processed/reference/<poCode>-nav.csv` — 净值历史（时间序列，按日期增量 append）
- 更新频率建议：**盘后档（20:00）每日增量拉取** nav-history 与 adjustments（`desc=true` 取最新 adjustmentId 对比），LONG_WIN 有新调仓时在日报「参考信号」提示用户

### 9.4 ⚠️ 调仓方向判定（重要教训，2026-08-07 修正）
- **REST `/adjustments` 的 `orders[].tradeUnit` 恒为正数**，只表示份数，**不区分买卖**！方向在：
  1. **`adjustments[].comment` 字段**（权威）：中文描述如「卖出1份建信500，买入1份易方达1-3年国开债」，按 `(买入|卖出)(\d*)份?(名称)` 正则解析
  2. **GraphQL `latestAdjustment.redeemOrders`（卖出）/ `buyOrders`（买入）** 分类，与 comment 一致
- **此前错误**：曾用 `buyAdjustmentId != 自身批次 = 卖出` 判定，仅识别出 10 次网格卖出，漏判 159-10=149 份卖出（把大量卖出当买入）——**必须用 comment 解析**
- 正确统计（全历史 261 批）：**买入 268 份 / 卖出 159 份 / 132 批含卖出**；2026 年 21 批含卖出
- 正则解析 comment 后建议与 orders 的 variety 匹配回填 fund_code（名称含 `-` 如「易方达1-3年国开债」需在正则字符集加 `\-`）

---

### 3.10 🟢 非交易日（周末）盘前档执行口径（2026-08-08 实测）

- 周末 A股/港股/场外基金无新行情，**跳过行情增量更新与调仓建议**，仅整理新闻与事件，输出简版章节并注明「非交易日」
- 隔夜美股**仍可抓取并归档**：`stock_us_daily(symbol="XLV"/"QQQ"/"DIA")` 在周六早间能拿到周五收盘数据（XLV 165.68 +0.75% 等），写入 indices.csv（type=us_index，note 标注「美股收盘(非交易日参考)」）——规则"跳过行情更新"指 A股/港股/基金，美股隔夜收盘属盘前档明确数据范围
- 周末新闻窗口为周五 18:00 - 周六 07:30，重点覆盖：①隔夜美股宏观（非农/CPI/加息预期）②五粮液批价等消费边际 ③医药 BD/审批/集采 ④港股周五收盘异动；情绪标注流程与交易日一致（DeepSeek v4-flash max_tokens=8000）

### 3.11 🟢 周一场外基金净值盘前抓取口径 + DeepSeek 偶发空响应（2026-08-10 实测）

- **周一盘前（08:00）场外基金净值已更新至上周五收盘**：`fund_open_fund_info_em` 早间可拿到上周五（如 8/7）全量净值，医药/宽基类当日 20:00 前已出（大摩健康 8/7 +9.22%、融通医疗 +7.34%），QDII（广发全球医疗 A/C、交银海外互联）停在上上周五/上周四（T+1~T+2，属正常）；上周五已归档的部分基金净值（如恒生科技/华宝医疗 C）注意去重，增量判重 key 用 `(code, nav_date)`
- **fund_nav.csv 增量写入必须 6 列全含**：`date(抓取日),code,name,nav_date,nav,pct`——曾踩坑漏写首列 date 导致列错位（历史 45 行被污染），写入时统一用完整 6 列、全部 str() 转换
- **DeepSeek v4-flash 偶发 content 为空（非必现）**：max_tokens=8000 时偶尔返回空 content（非 reasoning 占满，usage 正常），**重试一次即恢复**；情绪分析脚本需内置"content 为空则重试"逻辑，避免误判为接口故障

*最后更新：2026-08-11。环境或接口有变化时，先改本文件再执行任务。*
