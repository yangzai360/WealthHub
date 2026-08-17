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

### 3.12 🟡 盘后档情绪全量覆盖 + CSV 判重细节（2026-08-11 实测）

- **盘中档未做 DeepSeek 标注时，sentiment JSON 只有盘前条目**：8/11 盘中 10 条新闻以「中性 50」占位写入 news JSON 但未进 sentiment 文件——盘后脚本必须**全量覆盖当日所有新闻（盘前保留 + 盘中补标 + 盘后新增）**，先追加盘中/盘后条目到 sentiment 文件再同步回 news JSON，避免情绪字段与 news 不一致（已用 fix_sentiment_20260811.py 修复）
- **indices.csv 判重 name 列须严格一致**：同一标的（如 IYH）盘前名「美股医疗ETF(IYH)」vs 盘后名「美股医疗IYH」导致整行判重失败、写入重复行——增量脚本统一维护标的 name 字典，写前检查该 code+date 是否已存在（用 code+date+note 为主键更稳，必要时按 name 归一）
- **XLV 新浪源滞后会在下一交易日盘后补更**：8/11 晚 XLV 已补更至 8/10 收盘（168.44 +1.67%），可用于回填美股医药事件 actual_ret_1d——美股医药事件回填不限于盘前，盘后若 XLV 已补更也可完成
- **`stock_hk_index_daily_sina` 当日收盘滞后**：8/11 盘后该接口仍返回 8/10 数据（恒指 25937/恒科 4919），**当日港股收盘不可用日线接口**；`stock_hk_index_spot_sina` 间歇性空返回（重试 2-3 次即恢复），盘后港股收盘以 spot 重试为主

### 3.13 🟡 fund_nav.csv 增量判重必须用 (code, nav_date) 主键（2026-08-12 盘前实测）

- **现象**：盘前脚本用"整行字符串判重"（date=抓取日 不同 → 同一条净值被重复写入），8/12 盘前发现 fund_nav.csv 有 **37 组 (code, nav_date) 重复**（累计 149 行，其中 8/12 当日误写 7 行），数值一致但数据冗余，且同日多行 name 后缀不一（如「华夏沪深300」「华夏沪深300ETF联接A」「大摩健康产业混合A」）导致判重失败
- **规避**：增量写入**统一按 (code, nav_date) 去重后再 append**（脚本内先读全库建 key 集合）；历史重复已修复（149→109 行，保留 name 最完整行，nav 冲突时保留最新 date 行）
- **教训**：8/11 已记录"增量判重 key 用 (code, nav_date)"（§3.11），但脚本实现仍用整行判重——**脚本与规则必须同步**，新建抓取脚本时直接按 code+nav_date 判重

### 3.14 🟡 且慢 pmdj 接口偶发"HTTP 200 但空 body"（2026-08-12 盘中实测）

- **现象**：`curl`/urllib 调 `qieman.com/pmdj/v2/long-win/plan/adjustments`、`nav-history`、`plan` 三个接口均返回 **HTTP 200 但 0 字节 body**（SIZE:0），绕过代理（`env -u HTTP_PROXY...`）也一样；WebFetch 同样返回空。重试 2 次无效。
- **判定**：非本地代理拦截（此前 8/6-8/11 均正常），疑似且慢服务端临时异常或链路限流。**盘中档若遇此现象，标注「E大调仓数据暂缺」并保留本地最新 adjustments.json 不变，盘后档必须复测**——若恢复则增量补录并提示用户；若持续异常，考虑 qieman 官方 MCP 或换浏览器渲染方案（§9.2）。
- **注意**：空 body 与"连接失败"不同，不要误判为接口废弃，也不要反复重试浪费时长（2 次即可）。
- **补充（2026-08-12 盘后复测）**：**连续第 2 日空 body（8/12 盘前→盘中→盘后均 SIZE:0）**，判定为持续性异常而非瞬时抖动；本地最新调仓仍为 7/30（adj_id 781）。**若 8/13 仍异常，按 §9.2 切换 qieman 官方 MCP（免费申请 API Key）或 playwright 浏览器渲染兜底**，避免 E大调仓信号长期缺失。
- **补充2（2026-08-13 盘中实测：playwright 兜底可行，已成功验证）**：连续第 3 日空 body（8/13 盘前→盘中均 SIZE:0，页面上下文 fetch 同样返回空，判定且慢服务端对 REST `/pmdj/v2/...` 持续限流/异常）。**已实测可行兜底方案（scripts/qieman_pw_fallback.cjs）**：playwright-core + 系统 Chrome headless 打开 `https://qieman.com/longwin`，拦截 response 中 `/adjustments|nav-history|graphql|/plan` 的 JSON 响应即可拿到 `nav-history`（2702 条）与 `plan` 详情（composition/prodSummaries/sharpe 等）。**但注意：REST adjustments 明细（含 comment/orders）浏览器页面也不返回**——调仓判断改用 **`plan` 详情的 `adjustedCount` 字段**与本地 adjustments.json 的 `count` 对比（8/13 均为 261 → 无新调仓，交叉验证通过）；若 adjustedCount 增加则提示需要人工核对该批次调仓内容。**nav-history 增量更新**：数据源日期为 ms 时间戳（`navDate`），需 `/1000` 转换；本地 `long-win-nav.csv` 用日期字符串判重，一次增量写入 8/7-8/12 共 4 行。**plan 详情保存**：写 `reference-portfolios/long-win/composition-YYYY-MM-DD.json`（含 8 大类 composition）+ 更新 `meta.json` 指标（nav/sharpe/maxDrawdown/volatility/adjustedCount）。长期建议仍申请 qieman 官方 MCP 根治。

### 3.15 🟢 港股收盘 spot 失败时的补录方案（2026-08-12 盘后实测）

- **现象**：`stock_hk_index_spot_sina` 8/12 盘后 3 次重试均空返回（此前 8/11 为"间歇性空返回，重试 2-3 次恢复"，本次更严重），`stock_hk_index_daily_sina` 当日收盘滞后（只到前日）。
- **规避（补录路径）**：盘后港股收盘若 spot 全失败，改用 **WebSearch 抓收盘新闻确认收盘点位与涨跌幅**（新华社/财联社港股收评），手动补录 indices.csv（type=index, note='收盘20:00'），并在报告注明「港股收盘为新闻口径补录」。本次恒指 25,440.17(-0.83%)/恒科 4,776.44(-0.99%) 即为此方式补录。

### 3.16 🟡 `stock_hk_index_spot_sina` 列名是「最新价」不是「最新」（2026-08-13 盘前实测）

- **现象**：访问 `df['最新']` 报 KeyError，接口实际列名为 `['代码','名称','最新价','涨跌额','涨跌幅','昨收','今开','最高','最低']`。
- **规避**：读收盘价用 `df['最新价']`、涨跌幅用 `df['涨跌幅']`（数值为百分数如 -0.829，无 % 符号）。
- **补充**：XLV 新浪源 8/13 仍滞后至 8/11（连续第 3 个交易日滞后），美股医疗方向继续用 IYH 代理并标注；DeepSeek 情绪标注脚本解析 JSON 时若模型输出带前缀文字，用 `content[start:end+1]`（find("[")/rfind("]")）截取即可，勿整串 json.loads。

### 3.17 🟡 事件库 track 字段归类规范 + 港股 spot 连续失败升级（2026-08-13 盘后实测）

- **现象（track 归类 bug）**：8/13 盘中事件脚本把 `track` 填成了 category 映射值（宏观/业绩/行业事件/政策），而非赛道名（A股医药/大消费/恒生科技/美股标普医药/宏观/其他宽基）——导致事件库按赛道统计时全部错位。盘后脚本用关键词分类器（标题 regex：创新药|医药|医疗→A股医药；白酒|茅台|消费→大消费；腾讯|联想|港股→恒生科技；CPI|加息|日本→宏观等）重归类修复。
- **规避**：**事件库 track 字段统一用赛道名，禁止用 category 分类名**；新增事件的脚本需在写入时直接按标题关键词归类赛道，而非映射 category；盘后脚本补 id（`N{date}-{seq:03d}`）+ reference 结构（ret_3d/5d/10d/actual_ret_1d 等）+ strength 字段（从 sentiment 文件按标题回填，勿只回填 sentiment 丢 strength）。
- **现象（港股 spot 连续失败）**：`stock_hk_index_spot_sina` 8/13 盘后 3 次重试全部空返回（连续第 2 个交易日失败，8/12 也是），新闻口径补录（§3.15）再次启用——**该接口盘后稳定性持续恶化，盘后档港股收盘默认走 WebSearch 新闻口径补录**，不要反复重试浪费时间。
- **且慢 pmdj 连续第 4 日空 body**：8/13 盘中已用 playwright 浏览器渲染兜底（§3.14 补充2）验证 adjustedCount=261 无新调仓；盘后复测仍 SIZE:0，判定为且慢服务端持续性限流/异常，**本地数据源以 playwright 兜底为准，长期建议申请 qieman 官方 MCP**。

### 3.18 🟡 美股医疗 IYH 新浪源连续滞后 + 事件库 track 归类陷阱（2026-08-14 盘前实测）

- **IYH/XLV 新浪源滞后轮换**：8/11-8/13 为 XLV 滞后（用 IYH 代理），**8/14 盘前反转为 IYH 滞后（仍停在 8/12）、XLV 正常更新至 8/13（168.38 -0.04%）**——两个标的的滞后状态会轮换，**盘前回填美股医药事件先检查两者谁更新，取最新可用者**（本次用 XLV 8/13），不可默认 IYH 优先
- **事件库 track 关键词分类器陷阱**：标题含「美股医疗」会被"医疗"关键词误归 A股医药（本次 N20260814-013「美股医疗8/13基本持平」被误归，需手动修正为美股标普医药）——**关键词分类器须在 A股医药规则前加"美股|XLV|IYH|标普医药"前置规则，或按 (code/标题前缀) 区分 A股/美股医疗**
- **事件库 1 日样本统计须兼容 reference 嵌套**：部分事件 `actual_ret_1d` 在顶层、部分在 `e['reference']['actual_ret_1d']`（历史脚本两处都写过）——统计时 `v = e.get('actual_ret_1d'); if v is None: v = e.get('reference',{}).get('actual_ret_1d')`，否则强负面/强正面样本数会漏算
- **8/14 美股隔夜口径**：标普 7,798.99（+0.65%）再创历史新高、纳指 26,803.03（+0.81%）；7 月 PPI 同比 +4.7%（前 5.5%）回落；QQQ 732.07（+1.16%）领涨（存储芯片闪迪 +13.6%）；中概金龙 -1.84%（京东 -7%）为港股科技拖累项

### 3.19 🟡 盘后档港股 spot 连续失败升级 + 事件库补录注意（2026-08-14 盘后实测）

- **`stock_hk_index_spot_sina` 盘后连续第 3 日空返回**（8/12/8/13/8/14 盘后均失败）——**盘后档港股收盘默认走 WebSearch 新闻口径补录（§3.15），不要反复重试**；本次恒指 25,116.85(-1.10%)/恒科 4,707.62(-1.77%) 用新华社/每经收评补录
- **且慢 pmdj 连续第 6 日空 body**：playwright 兜底（§3.14 补充2）已稳定可用——本次成功拿到 nav-history（2,704 条）+ plan 详情（adjustedCount=261 无新调仓、nav 1.6923）；**meta.json 的 navDate 是 ms 时间戳**，更新时必须 `/1000` 转日期字符串（本次初版把 `str(ms)[:10]` 当日期写坏，已修复）；增量写入 long-win-nav.csv 用日期判重、一次可补多日
- **盘后新增新闻追加事件库后的 sentiment 同步**：sentiment 脚本只把「已存在的标题」同步回 news/events，**盘后新增的新闻/事件需单独按标题从 sentiment 文件回补 sentiment/score/strength 字段**（本次 8 条缺失，已修复）——建议盘后事件追加脚本直接带上 sentiment 文件中的标注
- **事件 track 归类注意**：A股收评类事件（沪指/创业板指标题）不会被「宏观」关键词命中（无 CPI/加息/指数字样），classify 会误归「其他/宽基」——需在宏观规则中加入「收评|沪指|创业板指|深成指」等关键词；中芯国际等港股科技权重个股业绩应归「恒生科技」（南向买入/恒科权重），勿归「其他/宽基」

### 3.20 🟡 盘前档港股 spot 连续失败 + 周一 QDII 净值 T+1 口径（2026-08-17 盘前实测）

- **`stock_hk_index_spot_sina` 盘前也连续失败**：8/17 盘前（07:50）3 次重试全部空返回——该接口自 8/12 盘后起盘前/盘后均不稳定（连续第 5 日），**盘前档港股如需最新价不再重试 spot**，直接用 indices.csv 已归档的 8/14 收盘（恒指 25,116.85/恒科 4,707.62），或 WebSearch 新闻口径补录
- **周一盘前 QDII 净值 T+1 至上周四/周五**：8/17（周一）早间广发全球医疗 A/C 最新净值 8/13、交银海外互联 8/13、华夏恒生 ETF 联接 A 已更新至 8/14——QDII 中部分已出 8/14、部分仍停 8/13（T+1~T+2 混合），属正常；A股类场外基金 8/14 净值周一早间已全量（医药 -0.94%~-1.23%、消费 -1.35%）
- **且慢 pmdj 连续第 8 日空 body**：8/17 盘前复测 `plan` 接口仍 HTTP 200 SIZE:0——持续异常已成常态，盘前/盘中档直接标注「E大调仓数据暂缺」即可，无需每次重试；周度或月度用 playwright 兜底（§3.14 补充2）验证 adjustedCount 变化即可
- **8/17 盘前情绪标注 12 条一次成功**：DeepSeek v4-flash max_tokens=8000 无空响应；事件库 track 直接采用新闻自带的 track 字段（手动归类），避免关键词分类器误归（§3.18 教训）

### 3.21 🟢 港股 spot 盘中恢复 + 且慢净值修正 + playwright 兜底再验证（2026-08-17 盘中实测）

- **`stock_hk_index_spot_sina` 盘中恢复**：8/17 盘中 3 次重试均成功（恒指 25,545.03 +1.71%、恒科 4,812.69 +2.23%）——自 8/12 盘中起的连续失败并非永久失效，**盘中档可正常重试该接口；盘后档仍建议按 §3.15 WebSearch 口径兜底**（盘后稳定性差）
- **且慢 pmdj 连续第 9 日空 body**（HTTP 200 SIZE:0），playwright 兜底（§3.14 补充2）再次成功：nav-history 2,704 条 + plan 详情 `adjustedCount=261` 与本地一致 → **无新调仓**；盘中档沿用「plan adjustedCount 对比」判断即可，无需每次跑 playwright（周度/月度验证即可）
- **且慢组合净值 8/14 出现修正**：playwright 抓到 8/14 nav=1.69029（dailyReturn -0.237%），本地 long-win-nav.csv 8/14 为 1.69233（-0.117%）——**且慢对 8/14 净值做了 -0.12% 修正**（成分基金净值修正传导）。规避：**本地历史净值落库后不回写覆盖**，以首次落库为准并记录差异即可
- **盘中新闻 track 手动归类**：盘中 9 条新闻（无 track 字段）由脚本按标题前缀手动映射赛道（恒生科技/大消费/A股医药/宏观），避免 §3.17 关键词分类器误归——**盘中追加事件脚本需内置手动 TRACK_MAP**，不能依赖自动分类器
- 本次新增脚本：`fetch_intraday_20260817.py` / `build_intraday_news_20260817.py` / `sentiment_intraday_20260817.py` / `append_events_intraday_20260817.py` / `calc_portfolio_intraday_20260817.py`（8/13 同名脚本模板直接改日期复用，增量判重 key 不变）

### 3.22 🟢 港股 spot 连续第 4 日盘后失败 + 且慢净值持续修正（2026-08-17 盘后实测）

- **`stock_hk_index_spot_sina` 盘后连续第 4 日空返回**（8/12/8/13/8/14/8/17 盘后均失败）：**盘后档港股收盘默认走 WebSearch 新闻口径补录**（§3.15），本次恒指 25,453.23(+1.34%)/恒科 4,782.03(+1.58%) 用新华社港股收评补录，与盘中 spot 实测（4,812 高点）对照一致；盘中档该接口正常（§3.21 已记录恢复）
- **且慢 pmdj 连续第 10 日空 body**（HTTP 200 SIZE:0），playwright 兜底再次成功：nav-history 2,705 条（新增 8/16 净值）+ plan 详情 `adjustedCount=261` 与本地一致 → **无新调仓**；8/14 且慢净值再修正至 1.6921（本地 1.69233，差 -0.12%）——**确认且慢近期对 8/12-8/14 净值持续小幅修正（成分基金净值传导），本地历史净值落库后不回写覆盖，以首次落库为准并记录差异**（§3.21 规则延续）
- **场外基金 8/17 当日净值 20:00 时点部分未出**：仅富国消费主题 519915 已更新（1.884 +0.53%），其余 A股基金/医药类 T+1 至明日；QDII（广发全球医疗 A/C 最新 8/13、交银海外互联 8/13）T+1~T+2——**注意富国消费主题 +0.53% 与中证消费 -1.14% 背离（主动基含非白酒权重），组合收益计算须以真实净值为准、勿用指数代理主动基**
- **周末事件回填口径**：8/16（周日）周末 10 条事件 actual_ret_1d 用 8/17（周一，首个交易日）收盘回填，`ret_1d_ref` 标注「8/17收盘(周末事件首个交易日)」——与 8/8-8/9 周末事件 8/10 回填的口径一致
- **DeepSeek 情绪标注 8 条一次成功**（max_tokens=8000 无空响应）；盘后新增 8 条新闻/事件已从 sentiment 文件按标题回补 sentiment/score/strength 字段（§3.19 规则延续）
- 本次新增脚本：`fetch_close_20260817.py` / `append_close_20260817.py` / `append_news_close_20260817.py` / `sentiment_close_20260817.py` / `events_fill_close_20260817.py` / `calc_portfolio_close_20260817.py`（8/14 同名脚本模板直接改日期复用，增量判重 key 不变）

### 3.23 🟢 盘前档港股 spot 失败规律确认 + QDII 净值兑现节奏 + 周二早盘美股可抓（2026-08-18 盘前实测）

- **港股 spot 盘前/盘后失败、盘中恢复的规律确认**：8/18 盘前 3 次重试全部空返回（连续第 6 日盘前失败；8/17 盘中曾恢复）——**盘前档港股直接沿用 indices.csv 已归档收盘（8/17 恒指 25,453.23/恒科 4,782.03），不再重试 spot**（§3.20 规则延续）
- **且慢 pmdj 连续第 11 日空 body**（HTTP 200 SIZE:0）：盘前/盘中档直接标注「E大调仓数据暂缺」，周度/月度 playwright 兜底验证 adjustedCount 即可（§3.21/3.22 规则延续）
- **QDII 净值兑现节奏验证**：广发全球医疗 A/C 的 8/14 净值（-0.73%/-0.74%）在 8/18（周二）盘前已更新——与 8/14 XLV -0.60% 方向一致，**验证 QDII 净值 T+1~T+2 兑现路径：美股 8/14 走势 → 8/18 早盘净值兑现**；8/17 美股（XLV -0.19%）预计 8/19-20 兑现，量级很小
- **周二早盘（08:00）可抓周一美股收盘**：`stock_us_daily`（QQQ/DIA/XLV/IYH）+ `index_us_stock_sina`（.IXIC/.DJI）在周二 08:00 均返回 8/17 收盘数据，本次 6 行全部归档 indices.csv（type=us_index）——盘前档隔夜美股抓取用此组合稳定可靠（§3.10/§2.1 规则延续）
- **场外基金周一净值周二早盘全量可抓**：8/18 盘前 23 只持仓基金 8/17 净值全量拿到（医药普涨 +0.19%~+1.69%、消费 -1.06%、恒科 +1.51%、宽基 +1.54%），仅 QDII 停 8/14（T+1 正常）——与 §3.11 周一规则对称，**周二早盘同样可抓周一全量净值**
- **DeepSeek 情绪标注 18 条一次成功**（max_tokens=8000 无空响应），事件库 track 直接采用手动归类赛道名（§3.17/3.20 规则延续）

*最后更新：2026-08-18（盘前）。环境或接口有变化时，先改本文件再执行任务。*
