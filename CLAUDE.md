# nasdaq-etf 项目规则

## 用途
- 记录 `513100`、`159501`、`159659` 三只纳指 ETF 的交易日收盘后价格、当天涨幅和溢价率。
- 记录 QQQ 和 NDX 的当前点位/价格、当天涨幅、历史最高收盘点/价和距离最高收盘的回撤。
- 输出文件是 `index.html`、`assets/app.js`、`assets/app.css`、`data/manifest.json` 和 `data/daily-records/YYYY/MM/YYYY-MM-DD.json`；通过本地 HTTP 服务或 GitHub Pages 查看 ETF 溢价表、QQQ/NDX 回撤表和数据源表。

## 走势图已下线（2026-09-08 用户决定）
- 页面不再渲染「走势」列（分时迷你图），采集与回填流程**不再抓取任何分时/分钟数据（trend）**。
- 历史每日 JSON 中已存在的 `trend` 字段原样保留（数据无损、不主动清理），但不再校验、不再使用。
- `python record_nasdaq_etf.py --refresh-trends` 已弃用为 no-op（仅保留参数兼容）；新写入的记录 `trend` 均为 `null`。
- 早盘停牌导致的分时缺口等知识不再作为数据操作依据。

## 文件约定
- `data_sources.json`：项目唯一的数据源和跟踪标的配置入口；新增或调整接口、代码、标的时先改这里。
- `record_nasdaq_etf.py`：采集、补录、去重更新和 React 页面壳刷新脚本。
- `data/manifest.json`：页面数据索引；只放生成时间、跟踪标的、数据源和每日文件引用。
- `data/daily-records/YYYY/MM/YYYY-MM-DD.json`：按交易日期和年月目录拆分的每日记录；ETF 使用 `trade_date` 归档，QQQ/NDX 使用 `quote_date` 归档；相同日期和代码/标的重复运行时更新原行。
- `src/`：React + TypeScript 前端源码；表格、tab、回撤摘要都在这里维护。
- `assets/`：前端构建产物，`index.html` 直接加载这里的 `app.js` 和 `app.css`。
- `index.html`：React 页面壳；从 `data/manifest.json` 加载索引，再按索引读取每日记录并挂载前端应用。
- `docs/HANDOFF.md`：完整项目交接文档；架构、数据口径、更新流程、自动任务和故障处理以这里的当前内容为准。
- 不提交缓存、虚拟环境、密钥或本地临时文件。

## 维护规范
- 代码保持简洁、直观，优先沿用现有函数和数据结构；复杂逻辑要写少量说明原因的注释。
- 目录结构必须清晰：配置放根目录，采集脚本放根目录，页面源码放 `src/`，构建产物放 `assets/`，数据索引和每日记录放 `data/`。
- 说明文档保持简洁清晰，只写当前真实可用的命令、路径和数据口径；代码、目录、数据源、自动任务或操作流程调整后同步更新 `README.md`、本文件和 `docs/HANDOFF.md`。
- 文件命名要能直接表达用途；多余的缓存、日志、旧数据文件和临时文件要删除，不能因为"也许有用"长期保留。
- 数据文件只保留一种正式入口：`data/manifest.json` 加 `data/daily-records/YYYY/MM/YYYY-MM-DD.json`；旧的单文件数据结构只允许作为脚本兼容读取来源，不再提交。

## 数据获取规则（最高优先，2026-09-03 用户强制约定）

**所有行情数据一律通过腾讯自选股连接器（westock MCP）获取，不再从 HTTP 网站抓取。**

适用场景：日常收盘采集、`--backfill-date` 回填、查 IOPV/估值、QQQ/NDX 行情等一切取数操作。
westock 实测可覆盖本项目全部数据需求（ETF 三只 + QQQ/NDX 的收盘价、涨幅、估值、历史最高），不再需要 HTTP 兜底源。
走势图下线后无需取分时（`data_minute` 不再使用）。

| 数据 | westock 工具 | 代码格式 |
| --- | --- | --- |
| ETF 实时/历史收盘、涨幅 | `data_quote`（支持 `date=YYYY-MM-DD` 历史快照） | `sh513100` / `sz159501` / `sz159659` |
| ETF 估值/净值（estimate） | `data_etf`（nav 字段）或 `data_quote` 返回的估值字段 | 同上 |
| ETF 历史日 K（回填补录） | `data_kline`（period=day, start/end） | 同上 |
| QQQ 收盘/涨幅 | `data_quote`（date 指定美股行情日） | `usQQQ.OQ` |
| NDX 收盘/涨幅 | `data_quote` | `usNDX`（勿用裸 NDX） |
| QQQ/NDX 历史日 K | `data_kline`（长区间取 history_high / 回撤） | `usQQQ.OQ` / `usNDX` |
| 代码/名称搜索 | `data_search` | — |

规则要点：
- 查询行情一律先走 westock MCP，只有 westock 完全不可用时才允许回退 HTTP 接口（东财/新浪/腾讯），且要把失败原因记入日志，不要静默切换。
- 溢价率 = `price / estimate - 1`，必须复算校验与 premium 字段一致。
- `record_nasdaq_etf.py` 内置 HTTP 源作为最后兜底保留，但日常取数不再主动访问 HTTP 行情站。

### 历史补录与回填
| 数据 | westock 顺序 |
| --- | --- |
| 历史收盘和涨幅 | `data_kline` / `data_quote`(date) |
| 估值（净值） | `data_etf`，记录写入时刻的最新可用净值 |

### QQQ/NDX 日线与回撤
```text
data_quote / data_kline (腾讯自选股)
```
历史最高收盘由项目已有记录中出现的最高收盘价决定：每次记录时将当前 `value` 与已有记录中的 `history_high` 比较，取较大值。

## 执行约定
- 默认使用 UTF-8。
- **取数主路径（会话/自动化执行时）**：用 westock MCP 工具（`data_quote`/`data_etf`/`data_kline`/`data_search`）取数，然后直接写入每日 JSON 或调用 `write_page_and_data` 重建页面；不要先跑到 HTTP 行情站逐站探测。
- 日常自动记录使用 `python record_nasdaq_etf.py`（脚本本身是纯 HTTP 实现，其取数链仅在无 westock 会话或连接器不可用时作为兜底，不允许作为默认取数路径）。
- 补录某天使用 `python record_nasdaq_etf.py --backfill-date YYYY-MM-DD`，会同时补录 ETF 和 QQQ/NDX；会话中优先用 westock 取数后回填。
- 历史 ETF 价格和涨幅优先使用腾讯自选股历史 K 线/行情，HTTP 源（东方财富、新浪）仅兜底。
- ETF 当前净值使用腾讯自选股 ETF 详情的 `nav` 字段。溢价率直接按 `price / nav - 1` 计算，不依赖外部估值服务。
- 刷新并补齐已记录 ETF 交易日对应的 QQQ/NDX 使用 `python record_nasdaq_etf.py --refresh-benchmarks`。
- 只补某个美股行情日的 QQQ/NDX 使用 `python record_nasdaq_etf.py --backfill-benchmark-date YYYY-MM-DD`，默认跟踪日期为该行情日后的下一个工作日。
- 修改脚本后至少运行 `python -m py_compile record_nasdaq_etf.py`。
- 修改前端后运行 `npm run typecheck` 和 `npm run build`。
- 本地查看使用 `python -m http.server 5173`，访问 `http://127.0.0.1:5173/`。
