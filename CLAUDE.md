# nasdaq-etf 项目规则

## 用途
- 记录 `513100`、`159501`、`159659` 三只纳指 ETF 的交易日收盘后价格、当天涨幅和 T-1 估值溢价率。
- 输出文件是 `nasdaq_etf_daily_record.html`，打开即可查看记录表。

## 文件约定
- `record_nasdaq_etf.py`：采集、补录、去重更新和 HTML 渲染脚本。
- `nasdaq_etf_daily_record.html`：历史记录页面；相同交易日期和代码重复运行时更新原行。
- 不提交缓存、虚拟环境、密钥或本地临时文件。

## 执行约定
- 默认使用 UTF-8。
- 日常自动记录使用 `python record_nasdaq_etf.py`。
- 补录某天使用 `python record_nasdaq_etf.py --backfill-date YYYY-MM-DD`。
- 修改脚本后至少运行 `python -m py_compile record_nasdaq_etf.py`。
