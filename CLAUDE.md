# nasdaq-etf 项目规则

## 用途
- 记录 `513100`、`159501`、`159659` 三只纳指 ETF 的交易日收盘后价格、当天涨幅和 T-1 估值溢价率。
- 记录 QQQ 和 NDX 的当前点位/价格、当天涨幅、历史最高收盘点/价和距离最高收盘的回撤。
- 输出文件是 `index.html`、`assets/app.js`、`assets/app.css` 和 `nasdaq_etf_daily_data.js`；打开 HTML 即可查看 ETF 溢价表、QQQ/NDX 回撤表和数据源表。

## 文件约定
- `data_sources.json`：项目唯一的数据源和跟踪标的配置入口；新增或调整接口、代码、标的时先改这里。
- `record_nasdaq_etf.py`：采集、补录、去重更新、趋势数据写入和 React 页面壳刷新脚本。
- `nasdaq_etf_daily_data.js`：历史记录数据文件；相同交易日期和代码/标的重复运行时更新原行；新记录可包含 `trend` 分钟走势。
- `src/`：React + TypeScript 前端源码；表格、tab、回撤摘要和折线图都在这里维护。
- `assets/`：前端构建产物，`index.html` 直接加载这里的 `app.js` 和 `app.css`。
- `index.html`：React 页面壳；从 `nasdaq_etf_daily_data.js` 加载数据并挂载前端应用。
- 不提交缓存、虚拟环境、密钥或本地临时文件。

## 执行约定
- 默认使用 UTF-8。
- 日常自动记录使用 `python record_nasdaq_etf.py`。
- 补录某天使用 `python record_nasdaq_etf.py --backfill-date YYYY-MM-DD`，会同时补录 ETF 和 QQQ/NDX。
- 修改脚本后至少运行 `python -m py_compile record_nasdaq_etf.py`。
- 修改前端后运行 `npm run typecheck` 和 `npm run build`。
