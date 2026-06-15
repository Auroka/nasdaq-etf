# nasdaq-etf 项目规则

## 用途
- 记录 `513100`、`159501`、`159659` 三只纳指 ETF 的交易日收盘后价格、当天涨幅和 T-1 估值溢价率。
- 记录 QQQ 和 NDX 的当前点位/价格、当天涨幅、历史最高收盘点/价和距离最高收盘的回撤。
- 输出文件是 `index.html`、`assets/app.js`、`assets/app.css`、`data/manifest.json` 和 `data/daily-records/YYYY/MM/YYYY-MM-DD.json`；通过本地 HTTP 服务或 GitHub Pages 查看 ETF 溢价表、QQQ/NDX 回撤表和数据源表。

## 文件约定
- `data_sources.json`：项目唯一的数据源和跟踪标的配置入口；新增或调整接口、代码、标的时先改这里。
- `record_nasdaq_etf.py`：采集、补录、去重更新、趋势数据写入和 React 页面壳刷新脚本。
- `data/manifest.json`：页面数据索引；只放生成时间、跟踪标的、数据源和每日文件引用。
- `data/daily-records/YYYY/MM/YYYY-MM-DD.json`：按交易日期和年月目录拆分的每日记录；ETF 使用 `trade_date` 归档，QQQ/NDX 使用 `quote_date` 归档；相同日期和代码/标的重复运行时更新原行。
- `src/`：React + TypeScript 前端源码；表格、tab、回撤摘要和折线图都在这里维护。
- `assets/`：前端构建产物，`index.html` 直接加载这里的 `app.js` 和 `app.css`。
- `index.html`：React 页面壳；从 `data/manifest.json` 加载索引，再按索引读取每日记录并挂载前端应用。
- 不提交缓存、虚拟环境、密钥或本地临时文件。

## 维护规范
- 代码保持简洁、直观，优先沿用现有函数和数据结构；复杂逻辑要写少量说明原因的注释。
- 目录结构必须清晰：配置放根目录，采集脚本放根目录，页面源码放 `src/`，构建产物放 `assets/`，数据索引和每日记录放 `data/`。
- 说明文档保持简洁清晰，只写当前真实可用的命令、路径和数据口径；代码或目录调整后同步更新 `README.md` 和本文件。
- 文件命名要能直接表达用途；多余的缓存、日志、旧数据文件和临时文件要删除，不能因为“也许有用”长期保留。
- 数据文件只保留一种正式入口：`data/manifest.json` 加 `data/daily-records/YYYY/MM/YYYY-MM-DD.json`；旧的单文件数据结构只允许作为脚本兼容读取来源，不再提交。

## 执行约定
- 默认使用 UTF-8。
- 日常自动记录使用 `python record_nasdaq_etf.py`。
- 补录某天使用 `python record_nasdaq_etf.py --backfill-date YYYY-MM-DD`，会同时补录 ETF 和 QQQ/NDX。
- 刷新并补齐已记录 ETF 交易日对应的 QQQ/NDX 使用 `python record_nasdaq_etf.py --refresh-benchmarks`。
- 只补某个美股行情日的 QQQ/NDX 使用 `python record_nasdaq_etf.py --backfill-benchmark-date YYYY-MM-DD`，默认跟踪日期为该行情日后的下一个工作日。
- 补已记录数据中的分钟走势使用 `python record_nasdaq_etf.py --refresh-trends`。
- Python 客户端被 Yahoo Finance 拦截时，历史分钟走势在当前 PowerShell 会话中用 `& .\scripts\refresh_yahoo_intraday_trends.ps1` 兜底补齐。
- 修改脚本后至少运行 `python -m py_compile record_nasdaq_etf.py`。
- 修改前端后运行 `npm run typecheck` 和 `npm run build`。
- 本地查看使用 `python -m http.server 5173`，访问 `http://127.0.0.1:5173/`。
