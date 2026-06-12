# nasdaq-etf 项目规则

## 用途
- 记录 `513100`、`159501`、`159659` 三只纳指 ETF 的交易日收盘后价格、当天涨幅和 T-1 估值溢价率。
- 记录 QQQ 和 NDX 的当前点位/价格、当天涨幅、历史最高收盘点/价和距离最高收盘的回撤。
- 输出文件是 `index.html`、`assets/app.js`、`assets/app.css`、`data/manifest.json` 和 `data/daily-records/YYYY-MM-DD.json`；通过本地 HTTP 服务或 GitHub Pages 查看 ETF 溢价表、QQQ/NDX 回撤表和数据源表。

## 文件约定
- `data_sources.json`：项目唯一的数据源和跟踪标的配置入口；新增或调整接口、代码、标的时先改这里。
- `record_nasdaq_etf.py`：采集、补录、去重更新、趋势数据写入和 React 页面壳刷新脚本。
- `data/manifest.json`：页面数据索引；只放生成时间、跟踪标的、数据源和每日文件引用。
- `data/daily-records/YYYY-MM-DD.json`：按交易日期拆分的历史记录；ETF 使用 `trade_date` 归档，QQQ/NDX 使用 `quote_date` 归档；相同日期和代码/标的重复运行时更新原行。
- `src/`：React + TypeScript 前端源码；表格、tab、回撤摘要和折线图都在这里维护。
- `assets/`：前端构建产物，`index.html` 直接加载这里的 `app.js` 和 `app.css`。
- `index.html`：React 页面壳；从 `data/manifest.json` 加载索引，再按索引读取每日记录并挂载前端应用。
- 不提交缓存、虚拟环境、密钥或本地临时文件。

## 执行约定
- 默认使用 UTF-8。
- 日常自动记录使用 `python record_nasdaq_etf.py`。
- 补录某天使用 `python record_nasdaq_etf.py --backfill-date YYYY-MM-DD`，会同时补录 ETF 和 QQQ/NDX。
- 补已记录数据中的分钟走势使用 `python record_nasdaq_etf.py --refresh-trends`。
- 修改脚本后至少运行 `python -m py_compile record_nasdaq_etf.py`。
- 修改前端后运行 `npm run typecheck` 和 `npm run build`。
- 本地查看使用 `python -m http.server 5173`，访问 `http://127.0.0.1:5173/`。
