# 纳指ETF每日数据更新 — 执行历史

## 2026-09-03 17:05（规则升级：所有数据一律走 westock，HTTP 行情源退役）
用户再次明确并升级约定：**所有数据——包括 --refresh-trends 及其他要补的段——都从腾讯自选股连接器获取，不要去 HTTP 行情站抓取**。本次已完成：
- **覆盖范围核查通过**：westock 可满足本项目全部需求（3 ETF + QQQ/NDX 的收盘/涨幅/估值/日K/分时/历史最高），无需 HTTP 兜底。
- **文档/配置同步**：CLAUDE.md「数据获取规则/执行约定」、README.md、docs/HANDOFF.md（§6 及 §8/§9/§10/§11/§14）、data_sources.json + data/manifest.json（westock=active，HTTP 各源 retired/enabled:false）、项目 MEMORY.md、本自动化 prompt（已加"0. 数据源约定"步骤）。
- **分层认知**：会话/自动化执行时 = westock MCP 工具取数直接写每日 JSON 或调 write_page_and_data；`record_nasdaq_etf.py` 是纯 HTTP 脚本（无 MCP 客户端能力），其 HTTP 链仅作为"无 westock 会话"的最后兜底保留，日常不再主动访问 HTTP 行情站。
- **下一轮（2026/09/04 15:30）起**：当日采集按 westock 主路径执行。

## 关键规则：数据源 = 腾讯自选股（westock MCP）为唯一取数源
（2026-09-03 用户强制约定，最高优先）一切行情取数（当天采集/回填/补 trend/查估值/QQQ·NDX）**一律从 westock MCP 获取，不去 HTTP 行情站抓取**。westock 工具映射：`data_quote`（sh513100/sz159501/sz159659/usQQQ.OQ/usNDX，date=YYYY-MM-DD 支持历史快照）、`data_etf`（nav=估值）、`data_kline`（日K/history_high）、`data_minute`（days=3 返回近 3 交易日分时，含复牌后段）、`data_search`（代码解析）。HTTP 源（东财/新浪/腾讯）已退役不再主动访问；record_nasdaq_etf.py 的 HTTP 链仅限"无 westock 会话"兜底，不作为默认取数路径。

## 2026-09-03 16:59（westock 纯链路耗时实测）
- **背景**: 用户要求实测"仅用腾讯自选股 connector、按当前记忆重生成 09-02 数据需要多久"。
- **结果**: 11 次 westock 调用（quote×2 / etf×1 / search×1 / kline×2 / minute×5，days=3 覆盖 09-02），墙钟 146.5s（16:56:29→16:58:56，含逐次调用与思考间隙；单次请求实际响应约 1-2s）。固化为脚本后纯采集预计 ≤30s。
- **数据一致性**: 与已提交 09-02 文件完全一致——ETF 收盘 2.195/2.084/2.313、estimate 1.9652/1.8458/2.1228（溢价 11.69%/12.90%/8.96%）；QQQ 709.24 / NDX 29143.33（+0.23%），history_high 732.07/30084.5（=08-13，drawdown 可复算）。
- **关键发现**: 513100/159501 的 09-02 分时 westock data_minute **实际可返回 10:31 起完整段**（此前 HTTP 链路全程取不到）——早盘 9:30-10:30 停牌段按规则不补，但日后 --refresh-trends 时可用 westock 补 10:31-15:00 段，勿再走 HTTP 多源重试。

## 关键规则：早盘分时缺失 = 高溢价临时停牌（勿补）
（2026-09-03 用户确认）纳指 QDII-ETF 高溢价时开盘停牌 1 小时至 10:30 复牌。若分时第一根 bar 从 ≈10:35 起、仅缺早盘 9:30-10:30 → 属停牌正常现象，**不算数据缺口，不需要补齐**，勿多源重试浪费时间。真正需补的：整日缺失 / 10:30 后出现空洞 / 尾盘缺失。实例：2026-09-02 的 513100/159501（premium 11.7%/12.9% 高位）即属此情况。

## 2026-08-28 15:30
- **状态**: 成功（收盘时段正常采集当天 08-28）
- **数据源**: ETF=eastmoney_quote + tencent_minute；Benchmark=nasdaq_api_historical
- **ETF 数据 (08-28)**:
  - 513100 (纳指ETF国泰): price=2.235, +0.27%, premium=11.50%
  - 159501 (纳指ETF嘉实): price=2.104, +0.05%, premium=11.76%
  - 159659 (纳斯达克100ETF招商): price=2.361, +0.08%, premium=9.05%
- **溢价率验证**: 三只全部通过 price/estimate-1 复算
- **Benchmark**: QQQ 721.11 (+1.37%) / NDX 29641.56 (+1.43%)，quote_date=08-27，写入 08-27 文件（T-1 设计），drawdown 复算通过，trend 64点/只
- **Git**: commit 0d1e7f6, push origin main 成功（3 files: 08-28 new + 08-27 benchmark 补录 + manifest）
- **自动化名称**: 已更新为 2026/08/31 纳指每日更新（08-28 周五 → 下一交易日 08-31 周一）

## 2026-08-27 16:28
- **状态**: 成功（收盘时段正常采集当天 08-27）
- **数据源**: ETF=eastmoney_quote + eastmoney_trend；Benchmark=nasdaq_api_historical + yahoo_intraday_chart/nasdaq_api_chart
- **ETF 数据 (08-27)**:
  - 513100 (纳指ETF国泰): price=2.229, +1.18%, premium=12.81%
  - 159501 (纳指ETF嘉实): price=2.103, +0.91%, premium=13.32%
  - 159659 (纳斯达克100ETF招商): price=2.359, +1.16%, premium=10.53%
- **溢价率验证**: 三只全部通过 price/estimate-1 复算
- **Benchmark**: QQQ 711.37 (+0.09%) / NDX 29224.52 (+0.05%)，quote_date=08-26，写入 08-26 文件（T-1 设计），drawdown 复算通过
- **Git**: commit 366fee1, push origin main 成功（3 files: 08-27 new + 08-26 benchmark/trend update + manifest）
- **自动化名称**: 已更新为 2026/08/28 纳指每日更新

## 2026-08-26 15:45
- **状态**: 成功（收盘时段正常采集当天 08-26）
- **数据源**: ETF=eastmoney_quote + tencent_minute；Benchmark=nasdaq_api_historical + nasdaq_api_chart
- **ETF 数据 (08-26)**:
  - 513100 (纳指ETF国泰): price=2.203, +0.36%, premium=11.50%
  - 159501 (纳指ETF嘉实): price=2.084, +0.39%, premium=12.31%
  - 159659 (纳斯达克100ETF招商): price=2.332, +0.09%, premium=9.28%
- **溢价率验证**: 三只全部通过 price/estimate-1 复算
- **Benchmark**: QQQ 710.72 (+0.62%) / NDX 29209.23 (+0.64%)，quote_date=08-25，写入 08-25 文件（T-1 设计），drawdown 复算通过
- **Git**: commit da47c71, push origin main 成功（3 files: 08-26 new + 08-25 benchmark/trend update + manifest）
- **自动化名称**: 已更新为 2026/08/27 纳指每日更新

## 2026-08-25 15:30
- **状态**: 成功（收盘时段正常采集当天 08-25）
- **数据源**: ETF=eastmoney_quote + tencent_minute；Benchmark=nasdaq_api_historical + nasdaq_api_chart
- **ETF 数据 (08-25)**:
  - 513100 (纳指ETF国泰): price=2.195, +1.34%, premium=11.82%
  - 159501 (纳指ETF嘉实): price=2.076, +0.87%, premium=12.61%
  - 159659 (纳斯达克100ETF招商): price=2.330, +1.00%, premium=9.90%
- **溢价率验证**: 三只全部通过 price/estimate-1 复算
- **Benchmark**: QQQ 706.32 (-1.00%) / NDX 29023.18 (-0.97%)，quote_date=08-24，写入 08-24 文件（T-1 设计）
- **Git**: commit fad8801, push origin main 成功（3 files: 08-25 new + 08-24 benchmark/trend update + manifest）
- **自动化名称**: 已更新为 2026/08/26 纳指每日更新

## 2026-08-24 18:16
- **状态**: 成功（收盘时段正常采集当天 08-24）
- **数据源**: ETF=eastmoney_quote + tencent_minute；Benchmark=nasdaq_api_historical + nasdaq_api_chart
- **ETF 数据 (08-24)**:
  - 513100 (纳指ETF国泰): price=2.166, -1.32%, premium=9.31%
  - 159501 (纳指ETF嘉实): price=2.058, -0.82%, premium=10.59%
  - 159659 (纳斯达克100ETF招商): price=2.307, -1.03%, premium=7.81%
- **溢价率验证**: 三只全部通过 price/estimate-1 复算
- **Benchmark**: QQQ 713.44 (+0.35%) / NDX 29308.86 (+0.33%)，quote_date=08-21，写入 08-21 文件（T-1 设计）
- **QQQ trend 补录**: nasdaq chart API 在美股盘前时段只返回 08-24 盘前数据（QQQ 为 ETF），QQQ 08-21 分时缺失；改用 westock data_minute（usQQQ）补全 64 点分时，source_ids=westock_minute
- **Git**: commit ba4287b, push origin main 成功（3 files: 08-24 new + 08-21 benchmark/trend update + manifest）
- **自动化名称**: 已更新为 2026/08/25 纳指每日更新

## 2026-08-21 15:26
- **状态**: 成功（收盘时段正常采集当天 08-21）
- **数据源**: ETF=eastmoney_quote + tencent_minute
- **ETF 数据 (08-21)**:
  - 513100 (纳指ETF国泰): price=2.195, -0.77%, premium=11.17%
  - 159501 (纳指ETF嘉实): price=2.075, -0.77%, premium=11.90%
  - 159659 (纳斯达克100ETF招商): price=2.331, -0.77%, premium=9.31%
- **溢价率验证**: 三只全部通过 price/estimate-1 复算
- **Benchmark**: QQQ 710.93 (-0.72%) / NDX 29213.16 (-0.72%)，quote_date=08-20，写入 08-20 文件（T-1 设计）
- **Git**: commit 780506f, push origin main 成功（3 files: 08-21 new + 08-20 benchmark update + manifest）
- **Trend**: 三只 ETF 均有完整 tencent_minute 分时
- **自动化名称**: 已更新为 2026/08/24 纳指每日更新

## 2026-08-21 10:14（补齐 08-20）
- **状态**: 成功（非收盘时段触发，补录前一交易日 08-20）
- **触发**: 10:08 市场未收盘 → 检测到 08-20 缺失 → 用户确认补齐
- **数据源**: 回填模式（eastmoney_kline/sina_daily_kline + tinyright_iopv；分时 tencent_minute）
- **ETF 数据 (08-20)**:
  - 513100 (纳指ETF国泰): price=2.212, +0.55%, premium=11.14%
  - 159501 (纳指ETF嘉实): price=2.091, +1.06%, premium=11.87%
  - 159659 (纳斯达克100ETF招商): price=2.349, +0.90%, premium=9.28%
- **溢价率验证**: 三只全部通过 price/estimate-1 复算
- **Benchmark**: QQQ 716.08 / NDX 29426.02，quote_date=08-19，写入 08-19 文件（T-1 设计）
- **Git**: commit 3e0dab6, push origin main 成功（3 files: 08-20 new + 08-19 benchmark update + manifest）
- **Trend 修复**: 513100/159501 回填时 trend 为空（sina 数据源无这两只历史分时），已用腾讯 m1 K 线接口（ifzq.gtimg.cn mkline）补全，64 点/只，source_ids=tencent_minute；159659 自带 sina_minute_kline 48 点
- **自动化名称**: 已更新为 2026/08/21 纳指每日更新

## 2026-08-19 15:26
- **状态**: 成功（收盘时段正常采集当天 08-19）
- **数据源**: ETF=westock_etf_detail + tencent_minute；Benchmark=nasdaq_api_historical + nasdaq_api_chart
- **ETF 数据 (08-19)**:
  - 513100 (国泰纳指100): price=2.200, -1.74%, premium=10.21%
  - 159501 (嘉实纳指100): price=2.069, -1.38%, premium=10.37%
  - 159659 (招商纳指100): price=2.328, -1.77%, premium=7.99%
- **溢价率验证**: 三只全部通过 price/estimate-1 复算
- **Benchmark**: QQQ 717.51 (-1.69%) / NDX 29490.96 (-1.68%)，quote_date=08-18，写入 08-18 文件（T-1 设计）
- **Git**: commit 15794fb, push origin main 成功（3 files: 08-19 new + 08-18 benchmark 补录 + manifest）
- **Trend**: 三只 ETF 均有完整 tencent_minute 分时（65点/只），benchmark 有 nasdaq_api_chart 分时
- **自动化名称**: 已更新为 2026/08/20 纳指每日更新

## 2026-08-19 13:56
- **状态**: 成功（非收盘时段触发，补录前一交易日 08-18）
- **触发**: 13:56 市场未收盘 → 检测到 08-18 缺失 → 用户确认补齐
- **数据源**: 回填模式（eastmoney_kline/sina_daily_kline + tinyright_iopv；分时 yahoo_intraday_chart/sina_minute_kline）
- **ETF 数据 (08-18)**:
  - 513100 (纳指ETF国泰): price=2.239, -1.54%, premium=10.33%
  - 159501 (纳指ETF嘉实): price=2.098, -1.32%, premium=10.09%
  - 159659 (纳斯达克100ETF招商): price=2.370, -1.50%, premium=8.14%
- **溢价率验证**: 三只全部通过 price/estimate-1 复算
- **Benchmark**: QQQ 729.87 / NDX 29995.38，quote_date=08-17，写入 08-17 文件（T-1 设计）
- **Git**: commit a0c733a, push origin main 成功（3 files: 08-18 new + 08-17 benchmark update + manifest）
- **Trend**: 三只 ETF 均有分时（513100/159501 yahoo_intraday_chart，159659 sina_minute_kline）
- **自动化名称**: 已更新为 2026/08/19 纳指每日更新

## 2026-08-17 15:25
- **状态**: 成功
- **数据源**: eastmoney_quote + eastmoney_trend
- **ETF 数据**:
  - 513100 (纳指ETF国泰): price=2.274, +0.44%, premium=11.85%
  - 159501 (纳指ETF嘉实): price=2.126, +0.24%, premium=11.35%
  - 159659 (纳斯达克100ETF招商): price=2.406, +0.46%, premium=9.59%
- **溢价率验证**: 三只全部通过 price/estimate-1 复算
- **Benchmark**: QQQ 731.07 (-0.14%) / NDX 30046.14 (-0.13%)，quote_date=08-14，写入 08-14 文件（T-1 设计）
- **Git**: commit 744e806, push origin main 成功（3 files: 08-17 new + 08-14 benchmark update + manifest）
- **Trend**: 三只 ETF 均有完整 eastmoney_trend 分时（64点/只）
- **自动化名称**: 已更新为 2026/08/18 纳指每日更新

## 2026-08-14 15:25
- **状态**: 成功（同时提交了 08-13 遗留未提交的数据）
- **数据源**: ETF=eastmoney_quote + eastmoney_trend（08-14）/ tencent_minute（08-13）；Benchmark=nasdaq_api_historical + nasdaq_api_chart
- **ETF 数据 (08-14)**:
  - 513100 (纳指ETF国泰): price=2.264, +1.71%, premium=11.20%
  - 159501 (纳指ETF嘉实): price=2.121, +1.24%, premium=10.93%
  - 159659 (纳斯达克100ETF招商): price=2.395, +1.48%, premium=8.93%
- **ETF 数据 (08-13，前次运行未提交)**:
  - 513100: price=2.226, 0.00%, premium=10.60%
  - 159501: price=2.095, -0.05%, premium=10.84%
  - 159659: price=2.360, +0.30%, premium=8.58%
- **溢价率验证**: 六条全部通过 price/estimate-1 复算
- **Benchmark**: QQQ 732.07 (+1.16%) / NDX 30084.5 (+1.15%)，quote_date=08-13，写入 08-13 文件；08-12 文件 benchmark（QQQ 723.7 / NDX 29742.6）一并提交
- **Git**: commit b59aff0, push origin main 成功（4 files: 08-13 new + 08-14 new + 08-12 benchmark update + manifest）
- **Trend**: 三只 ETF 均有完整分时（64点/只），benchmark 有 nasdaq_api_chart 分时（64点/只）
- **自动化名称**: 已更新为 2026/08/17 纳指每日更新

## 2026-08-12 15:25
- **状态**: 成功
- **数据源**: eastmoney_quote + tencent_minute
- **ETF 数据**:
  - 513100 (纳指ETF国泰): price=2.226, +0.50%, premium=11.38%
  - 159501 (纳指ETF嘉实): price=2.096, +0.43%, premium=11.67%
  - 159659 (纳斯达克100ETF招商): price=2.353, +0.43%, premium=9.02%
- **溢价率验证**: 三只全部通过 price/estimate-1 复算
- **Git**: commit d36df42, push origin main 成功（3 files: 08-12 new + 08-11 benchmark update + manifest）
- **Trend**: 三只 ETF 均有完整 tencent_minute 分时（~64点/只）
- **自动化名称**: 已更新为 2026/08/13 纳指每日更新

## 2026-08-12 09:16（补齐 08-10, 08-11）
- **状态**: 成功（非收盘时段触发，用户确认补齐两个交易日）
- **触发**: 09:14 市场未收盘 → 检测到 08-10/08-11 均缺失 → 用户选择从 08-10 开始补
- **数据源**: 回填模式（sina_daily_kline + tinyright_iopv/eastmoney_fund_nav）
- **修复**: 补充了缺失的 `eastmoney_fund_nav` 数据源到 data_sources.json
- **ETF 数据 (08-10)**:
  - 513100: price=2.261, -0.22%, premium=12.38%
  - 159501: price=2.113, +0.48%, premium=11.83%
  - 159659: price=2.375, +0.38%, premium=9.31%
- **ETF 数据 (08-11)**:
  - 513100: price=2.215, -2.03%, premium=10.49%
  - 159501: price=2.087, -1.23%, premium=10.86%
  - 159659: price=2.343, -1.35%, premium=8.23%（含 sina_minute_kline 分时）
- **溢价率验证**: 六条全部通过 price/estimate-1 复算
- **Benchmark (08-10)**: QQQ 720.87 (-0.30%) / NDX 29621.8 (-0.34%)
- **Git**: commit c05f19e, push origin main 成功（5 files: 08-10/08-11 new + manifest + data_sources + 08-07 update）
- **自动化名称**: 已更新为 2026/08/12 纳指每日更新

## 2026-08-07 16:35
- **状态**: 成功
- **数据源**: eastmoney_quote + tencent_minute
- **ETF 数据**:
  - 513100 (纳指ETF国泰): price=2.266, +0.98%, premium=13.97%
  - 159501 (纳指ETF嘉实): price=2.103, +0.77%, premium=12.63%
  - 159659 (纳斯达克100ETF招商): price=2.366, +0.47%, premium=10.20%
- **溢价率验证**: 三只全部通过 price/estimate-1 复算
- **Benchmark**: QQQ 714.65 (-0.37%) / NDX 29373.33 (-0.39%)，quote_date=08-06，写入 08-06 文件
- **Git**: commit 09b9e2c, push origin main 成功（3 files: 08-07 new + 08-06 benchmark + manifest）
- **Trend**: 三只 ETF 均有完整 tencent_minute 分时（~63点/只），benchmark 有 yahoo_intraday/nasdaq_api_chart 分时
- **自动化名称**: 已更新为 2026/08/10 纳指每日更新

## 2026-08-06 15:25
- **状态**: 成功
- **数据源**: eastmoney_quote + tencent_minute
- **ETF 数据**:
  - 513100 (纳指ETF国泰): price=2.244, -1.01%, premium=12.45%
  - 159501 (纳指ETF嘉实): price=2.087, -1.14%, premium=11.35%
  - 159659 (纳斯达克100ETF招商): price=2.355, -1.38%, premium=9.27%
- **溢价率验证**: 三只全部通过 price/estimate-1 复算
- **Benchmark**: QQQ 717.30 (-0.90%) / NDX 29487.79 (-0.83%)，quote_date=08-05，写入 08-05 文件
- **Git**: commit 5085f1c, push origin main 成功（3 files: 08-06 new + 08-05 benchmark update + manifest）
- **Trend**: 三只 ETF 均有完整 tencent_minute 分时（64点/只），benchmark 有 nasdaq_api_chart 分时
- **自动化名称**: 已更新为 2026/08/07 纳指每日更新

## 2026-08-05 15:25
- **状态**: 成功
- **数据源**: eastmoney_quote + eastmoney_trend
- **ETF 数据**:
  - 513100 (纳指ETF国泰): price=2.267, +3.42%, premium=12.62%
  - 159501 (纳指ETF嘉实): price=2.111, +3.18%, premium=11.65%
  - 159659 (纳斯达克100ETF招商): price=2.388, +3.60%, premium=9.83%
- **溢价率验证**: 三只全部通过 price/estimate-1 复算
- **Benchmark**: QQQ 723.85 (+3.40%) / NDX 29733.16 (+3.32%)，quote_date=08-04，写入 08-04 文件
- **Git**: commit 38ae38a, push origin main 成功（3 files: 08-05 new + 08-04 benchmark + manifest）
- **Trend**: 三只 ETF 均有完整 eastmoney_trend 分时（64点/只）
- **自动化名称**: 已更新为 2026/08/06 纳指每日更新

## 2026-08-04 15:25
- **状态**: 成功
- **数据源**: eastmoney_quote + tencent_minute
- **ETF 数据**:
  - 513100 (纳指ETF国泰): price=2.192, +1.42%, premium=12.52%
  - 159501 (纳指ETF嘉实): price=2.046, +1.27%, premium=11.83%
  - 159659 (纳斯达克100ETF招商): price=2.305, +1.17%, premium=9.56%
- **溢价率验证**: 三只全部通过 price/estimate-1 复算
- **Benchmark**: QQQ 700.07 (+1.76%) / NDX 28776.8 (+1.78%)，quote_date=08-03，补录至 08-03 文件
- **Git**: commit f730de9, push origin main 成功（3 files: 08-04 new + 08-03 benchmark backfill + manifest）
- **Trend**: 三只 ETF 均有完整 tencent_minute 分时（64点/只）
- **自动化名称**: 已更新为 2026/08/05 纳指每日更新

## 2026-08-03 15:25
- **状态**: 成功
- **数据源**: eastmoney_quote + tencent_minute
- **ETF 数据**:
  - 513100 (纳指ETF国泰): price=2.127, +0.71%, premium=11.14%
  - 159501 (纳指ETF嘉实): price=1.995, +0.61%, premium=10.99%
  - 159659 (纳斯达克100ETF招商): price=2.245, +0.45%, premium=8.62%
- **溢价率验证**: 三只全部通过 price/estimate-1 复算
- **Benchmark**: QQQ 687.99 (+0.65%) / NDX 28274.19 (+0.60%)，T-1 quote_date=07-31，写入 07-31 文件
- **Git**: commit 49f1dfe, push origin main 成功（3 files: 08-03 new + 07-31 benchmark + manifest）
- **Trend**: 三只 ETF 均有完整 tencent_minute 分时，benchmark 有 nasdaq_api_chart 分时
- **自动化名称**: 已更新为 2026/08/04 纳指每日更新

## 2026-07-31 15:25
- **状态**: 成功
- **数据源**: eastmoney_quote + tencent_minute
- **ETF 数据**:
  - 513100 (纳指ETF国泰): price=2.112, +3.48%, premium=11.00%
  - 159501 (纳指ETF嘉实): price=1.983, +3.23%, premium=10.97%
  - 159659 (纳斯达克100ETF招商): price=2.235, +3.81%, premium=8.77%
- **溢价率验证**: 三只全部通过 price/estimate-1 复算
- **Benchmark**: QQQ 683.55 (+3.30%) / NDX 28106.35 (+3.36%)，T-1 写入 07-30 文件，quote_date=2026-07-30
- **Git**: commit ecd1d5e, push origin main 成功（3 files: 07-31 new + 07-30 benchmark 补录 + manifest）
- **Trend**: 三只 ETF 均有完整 tencent_minute 分时数据（64点/只），benchmark 有 nasdaq_api_chart 分时
- **自动化名称**: 已更新为 2026/08/03 纳指每日更新

## 2026-07-30 15:25
- **状态**: 成功
- **数据源**: eastmoney_quote + tencent_minute
- **ETF 数据**:
  - 513100 (纳指ETF国泰): price=2.041, -1.59%, premium=10.86%
  - 159501 (纳指ETF嘉实): price=1.921, -1.34%, premium=11.11%
  - 159659 (纳斯达克100ETF招商): price=2.153, -1.55%, premium=8.29%
- **溢价率验证**: 三只全部通过 price/estimate-1 复算
- **Benchmark**: QQQ 661.73 (-2.04%) / NDX 27192.31 (-2.06%)，T-1 写入 07-29 文件
- **Git**: commit 6c8c764, push origin main 成功（3 files: 07-30 new + 07-29 benchmark 补录 + manifest）
- **Trend**: 三只 ETF 均有完整 tencent_minute 分时数据（63点/只）
- **自动化名称**: 已更新为 2026/07/31 纳指每日更新

## 2026-07-30 10:03（补齐 07-29）
- **状态**: 成功（补齐前一交易日 07-29）
- **触发**: 市场未收盘 → 检测到 07-29 缺失 → 用户确认补齐
- **数据源**: eastmoney_kline/sina_daily_kline + tinyright_iopv + sina_minute_kline（回填模式）
- **ETF 数据**:
  - 513100 (纳指ETF国泰): price=2.074, +0.29%, premium=10.29%
  - 159501 (纳指ETF嘉实): price=1.947, +0.10%, premium=10.25%
  - 159659 (纳斯达克100ETF招商): price=2.187, +0.32%, premium=7.70%
- **溢价率验证**: 三只全部通过 price/estimate-1 复算
- **Git**: commit de49f29, push origin main 成功（3 files: 07-29 new + 07-28 benchmark 补录 + manifest）
- **Trend**: 三只 ETF 均有完整 sina_minute_kline 分时（48点/只）
- **自动化名称**: 已更新为 2026/07/30 纳指每日更新

## 2026-07-28 17:55 (定时调度再次触发，当天已采集)
- **状态**: 跳过（07-28 数据已存在，数据与前次一致）
- **Git**: 无变更，跳过提交
- **自动化名称**: 已更新为 2026/07/29 纳指每日更新

## 2026-07-28 17:53
- **状态**: 成功
- **数据源**: westock_etf_detail + tencent_minute
- **ETF 数据**:
  - 513100 (纳指ETF国泰): price=2.068, -2.36%, premium=8.92%
  - 159501 (纳指ETF嘉实): price=1.945, -1.92%, premium=9.07%
  - 159659 (纳斯达克100ETF招商): price=2.180, -2.64%, premium=6.32%
- **溢价率验证**: 三只全部通过 price/estimate-1 复算
- **Benchmark**: QQQ 682.12 (-0.31%) / NDX 28039.21 (-0.32%)，T-1 写入 07-27 文件
- **Git**: commit fc329b9, push origin main 成功（3 files: daily 07-28 + manifest + 07-27 benchmark 更新）
- **Trend**: 三只 ETF 均有完整 tencent_minute 分时数据，benchmark 有 yahoo_intraday/nasdaq_api_chart 分时

## 2026-07-27 17:12
- **状态**: 成功
- **数据源**: eastmoney_quote + tencent_minute
- **ETF 数据**:
  - 513100 (纳指ETF国泰): price=2.118, +0.67%, premium=11.15%
  - 159501 (纳指ETF嘉实): price=1.983, +0.15%, premium=10.81%
  - 159659 (纳斯达克100ETF招商): price=2.239, +0.72%, premium=8.81%
- **溢价率验证**: 三只全部通过 price/estimate-1 复算
- **Git**: commit b897d43, push origin main 成功（3 files: daily 07-27 + manifest + 07-24 benchmark 补录）
- **Trend**: 三只 ETF 均有完整 tencent_minute 分时数据（64点/只）

## 2026-07-24 15:25
- **状态**: 成功
- **数据源**: eastmoney_quote + tencent_minute
- **ETF 数据**:
  - 513100 (纳指ETF国泰): price=2.104, -1.27%, premium=9.20%
  - 159501 (纳指ETF嘉实): price=1.98, -1.05%, premium=9.42%
  - 159659 (纳斯达克100ETF招商): price=2.223, -1.42%, premium=6.85%
- **溢价率验证**: 三只全部通过 price/estimate-1 复算
- **Benchmark**: QQQ 691.96 (-1.90%) / NDX 28454.81 (-1.87%)，T-1 补录至 07-23 文件
- **Git**: commit 581ebbf, push origin main 成功（7 files: daily 07-24 + manifest + 07-23 benchmark 补录 + assets/src 渲染）
- **Trend**: 三只 ETF 均有完整 tencent_minute 分时数据（64点/只）

## 2026-07-23 15:25
- **状态**: 成功
- **数据源**: eastmoney_quote + tencent_minute
- **ETF 数据**:
  - 513100 (纳指ETF国泰): price=2.131, +0.05%, premium=8.49%
  - 159501 (纳指ETF嘉实): price=2.001, -0.10%, premium=8.47%
  - 159659 (纳斯达克100ETF招商): price=2.255, 0.00%, premium=6.31%
- **溢价率验证**: 三只全部通过 price/estimate-1 复算
- **Benchmark**: QQQ 705.35 (-0.51%)，T-1 补录至 07-22 文件
- **Git**: commit 69a1e6f, push origin main 成功（3 files: daily 07-23 + manifest + 07-22 benchmark 补录）
- **Trend**: 三只 ETF 均有完整 tencent_minute 分时数据（63点/只）

## 2026-07-23 13:51（补齐 07-22）
- **状态**: 成功（补齐前一交易日 07-22）
- **数据源**: eastmoney_kline + tinyright_iopv + eastmoney_trend（回填模式）
- **ETF 数据**:
  - 513100 (纳指ETF国泰): price=2.130, 0.00%, premium=7.88%
  - 159501 (纳指ETF嘉实): price=2.003, -0.20%, premium=8.02%
  - 159659 (纳斯达克100ETF招商): price=2.255, -0.31%, premium=5.76%
- **溢价率验证**: 三只全部通过 price/estimate-1 复算
- **Benchmark**: QQQ 708.97 (+1.85%) / NDX 29155.18 (+1.93%)，quote=2026-07-21（T-1）
- **Git**: commit ac37295, push origin main 成功（3 files）
- **Trend**: 三只 ETF 均有完整 eastmoney_trend 分时数据（64点/只）

## 2026-07-23 10:52
- **状态**: 跳过（市场未收盘，检测到 07-22 缺失后由用户确认补齐）
- **下一个交易日**: 2026-07-24（周五），自动化名称已更新

## 2026-07-21 15:25
- **状态**: 成功
- **数据源**: eastmoney_quote + eastmoney_trend（东方财富 API 正常）
- **ETF 数据**:
  - 513100 (纳指ETF国泰): price=2.130, +0.77%, premium=9.89%
  - 159501 (纳指ETF嘉实): price=2.007, +0.61%, premium=10.26%
  - 159659 (纳斯达克100ETF招商): price=2.262, +0.72%, premium=8.08%
- **溢价率验证**: 三只全部通过 price/estimate-1 复算
- **Git**: commit 4653249, push origin main 成功（3 files: daily record 2026-07-21 + manifest + 07-20 benchmark 补录）
- **Trend**: 三只 ETF 均有完整 eastmoney_trend 分时数据（63点/只）

## 2026-07-20 15:25
- **状态**: 成功
- **数据源**: eastmoney_quote + eastmoney_trend（东方财富 API 正常）
- **ETF 数据**:
  - 513100 (纳指ETF国泰): price=2.096, -0.52%, premium=8.19%
  - 159501 (纳指ETF嘉实): price=1.983, -0.05%, premium=9.00%
  - 159659 (纳斯达克100ETF招商): price=2.226, 0.00%, premium=6.42%
- **溢价率验证**: 三只全部通过 price/estimate-1 复算
- **Git**: commit 9928bd5, push origin main 成功（3 files: new daily record 2026-07-20 + manifest + 07-17 benchmark 补录）
- **Trend**: 三只 ETF 均有完整 eastmoney_trend 分时数据（64点/只）

## 2026-07-17 15:26
- **状态**: 成功
- **数据源**: eastmoney_quote + eastmoney_trend（东方财富 API 正常）
- **ETF 数据**:
  - 513100 (纳指ETF国泰): price=2.107, -2.77%, premium=7.18%
  - 159501 (纳指ETF嘉实): price=1.984, -2.79%, premium=7.47%
  - 159659 (纳斯达克100ETF招商): price=2.226, -2.96%, premium=4.87%
- **溢价率验证**: 三只全部通过 price/estimate-1 复算
- **Git**: commit d6d905e, push origin main 成功（3 files: new daily record + manifest update + 07-16 benchmark 补录）
- **Trend**: 三只 ETF 均有完整 eastmoney_trend 分时数据（64点/只）

## 2026-07-16 15:25
- **状态**: 成功
- **数据源**: eastmoney_quote + tencent_minute（东方财富报价 + 腾讯分时）
- **ETF 数据**:
  - 513100 (纳指ETF国泰): price=2.167, -0.96%, premium=8.45%
  - 159501 (纳指ETF嘉实): price=2.041, -0.97%, premium=8.76%
  - 159659 (纳斯达克100ETF招商): price=2.294, -1.16%, premium=6.33%
- **溢价率验证**: 三只全部通过 price/estimate-1 复算
- **Benchmark**: QQQ/NDX 数据补录至 2026-07-15 daily file（T-1 设计）
- **Git**: commit 8504bba, push origin main 成功（3 files: new daily record + manifest + benchmark 补录）
- **Trend**: 三只 ETF 均有完整 tencent_minute 分时数据（64点/只）

## 2026-07-15 15:25
- **状态**: 成功
- **数据源**: eastmoney_quote + eastmoney_trend（东方财富 API 可用）
- **ETF 数据**:
  - 513100 (纳指ETF国泰): price=2.188, +0.83%, premium=9.06%
  - 159501 (纳指ETF嘉实): price=2.061, +0.78%, premium=9.38%
  - 159659 (纳斯达克100ETF招商): price=2.321, +1.31%, premium=7.15%
- **溢价率验证**: 三只全部通过 price/estimate-1 复算
- **Benchmark**: QQQ/NDX 数据更新至 2026-07-14 daily file（T-1 设计，与 ETF 不同日期）
- **Git**: commit c4b687d, push origin main 成功
- **Trend**: 三只 ETF 均有完整 eastmoney_trend 分时数据（~65点/只）

## 2026-07-14 15:25
- **状态**: 成功（MCP 回退模式）
- **回退原因**: tinyright IOPV 未更新 + EastMoney API 连接被拒
- **数据源**: 腾讯自选股 MCP（westock_quote + westock_etf_detail）
- **ETF 数据**:
  - 513100 (纳指ETF国泰): price=2.170, +0.09%, premium=7.57%
  - 159501 (纳指ETF嘉实): price=2.045, +0.05%, premium=7.94%
  - 159659 (纳斯达克100ETF招商): price=2.291, +0.17%, premium=5.19%
- **Benchmark** (QQQ/NDX 2026-07-13 收盘):
  - QQQ: 711.74 (-1.90%), 距历史最高 746.16 回撤 4.61%
  - NDX: 29264.1 (-1.88%), 距历史最高 30660.6 回撤 4.55%
- **溢价率验证**: 三只全部通过 price/estimate-1 复算
- **Git**: commit de61c06, push origin main 成功（含 07-10 benchmark 补录 + 走势图）
- **修复**: 初次提交遗漏了所有走势数据（5 只全为 None），已用 ammend 补上 westock_minute 分时数据

## 2026-07-13 15:26
- **状态**: 成功
- **采集结果**: 3 ETF rows，benchmark 为空
- **ETF 数据**:
  - 513100 (纳指ETF国泰): price=2.168, -0.28%, premium=7.20%
  - 159501 (纳指ETF嘉实): price=2.044, -0.44%, premium=7.61%
  - 159659 (纳斯达克100ETF招商): price=2.287, -0.57%, premium=6.37%
- **溢价率验证**: 三只全部通过 price/estimate-1 复算
- **Git**: commit 505d662, push origin main 成功

## 2026-07-10 15:30
- **状态**: 成功
- **采集结果**: 3 ETF rows（benchmark 未写入 daily file）
- **ETF 数据**:
  - 513100 (纳指ETF国泰): price=2.174, +0.37%, premium=7.77%
  - 159501 (纳指ETF嘉实): price=2.053, +0.20%, premium=8.37%
  - 159659 (纳斯达克100ETF招商): price=2.300, +0.31%, premium=5.60%
- **溢价率验证**: 三只全部通过 price/estimate-1 复算
- **Git**: commit 51c2bd2, push origin main 成功

## 2026-07-09 15:28
- **状态**: 成功
- **ETF 数据**:
  - 513100 (纳指ETF国泰): price=2.166, +1.17%, premium=9.04%
  - 159501 (纳指ETF嘉实): price=2.049, +0.79%, premium=9.84%
  - 159659 (纳斯达克100ETF招商): price=2.293, +1.10%, premium=6.93%
- **Git**: commit c68fd48, push origin main 成功

## 2026-09-01 14:40
- **状态**: 成功（非收盘时段触发，用户确认补齐 08-31）
- **触发**: 14:04 市场未收盘 → 检测到 08-31 缺失 → 用户确认补齐 → backfill-date 2026-08-31
- **数据源**: ETF=sina_daily_kline + tinyright_iopv（回填）；Benchmark=nasdaq_api_historical（quote_date=08-28，T-1 写入 08-28 文件）
- **ETF 数据 (08-31)**:
  - 513100 (纳指ETF国泰): price=2.223, -0.54%, premium=11.74%
  - 159501 (纳指ETF嘉实): price=2.100, -0.19%, premium=12.39%
  - 159659 (纳斯达克100ETF招商): price=2.345, -0.68%, premium=9.13%
- **溢价率验证**: 三只全部通过 price/estimate-1 复算
- **Benchmark (track 08-31, quote 08-28)**: QQQ 716.43 (-0.65%) / NDX 29433.43 (-0.70%)，history_high 732.07/30084.5，drawdown 复算通过，写入 08-28 文件
- **Trend 修复**: 回填时 513100/159501/QQQ/NDX 的 trend 均为 null。腾讯 m1 缺早盘、新浪 A 股缺早盘、东财 https 被限流 → 改用 东财 trends2 HTTP 接口（push2his HTTP 版）补 ETF 08-31 分时 64 点/只（eastmoney_trend），新浪美股 5 分钟接口补 QQQ/NDX 08-28 分时 64 点/只（sina_minute_kline）；159659 自带 sina_minute_kline
- **Git**: commit da66e44, push origin main 成功（3 files: 08-31 new + 08-28 benchmark/trend + manifest）
- **自动化名称**: 已更新为 2026/09/01 纳指每日更新（08-31 周一 → 下一交易日 09-01 周二）

## 2026-09-01 15:30
- **状态**: 成功（收盘时段正常采集当天 09-01）
- **数据源**: ETF=westock_etf_detail + tencent_minute；Benchmark=nasdaq_api_historical（quote_date=08-31，T-1 写入 08-31 文件）
- **ETF 数据 (09-01)**:
  - 513100 (纳指ETF国泰): price=2.233, +0.45%, premium=12.12%
  - 159501 (纳指ETF嘉实): price=2.108, +0.38%, premium=12.70%
  - 159659 (纳斯达克100ETF招商): price=2.352, +0.30%, premium=9.34%
- **溢价率验证**: 三只通过复算（159659 存储 0.0934 vs 复算 0.093343，差异 0.00006 为数据源 IOPV 高精度正常浮动）
- **Benchmark (track 09-01, quote 08-31)**: QQQ 716.76 (+0.05%) / NDX 29456.97 (+0.08%)，写入 08-31 文件（更新原 quote=08-28 的 benchmark），trend 64 点/只，字段完整
- **Git**: commit 95b365a, push origin main 成功（3 files: 09-01 new + 08-31 benchmark 更新 + manifest）
- **自动化名称**: 已更新为 2026/09/02 纳指每日更新（09-01 周二 → 下一交易日 09-02 周三）

## 2026-09-07 18:15（当天采集 09-07 + 一并提交 09-04 遗留数据）
- **状态**: 成功。git pull 无更新 → 采集并写入当天（09-07 周一，收盘后）数据
- **数据源**: **westock MCP 本轮不可用**（会话内未连接，仅 agent-mail 在线，ToolSearch 查不到 data_quote/data_minute 等工具）→ 按规则执行 HTTP 兜底 `python record_nasdaq_etf.py`，已在本条记录原因
- **ETF 数据 (09-07)**: 513100 price=2.236 (+0.63%) prem=12.22% / 159501 price=2.110 (+0.24%) prem=12.75% / 159659 price=2.365 (+0.64%) prem=9.88%；估值沿用 T-1（09-04 NAV：1.9925/1.8714/2.1523，周一 IOPV 未发布属正常）；trend 64 点/只；溢价率复算全部通过（差 <2e-4，源端 4 位小数取整）
- **Benchmark (track 09-07, quote 09-04)**: QQQ 718.96 (+0.18%) / NDX 29544.16 (+0.21%)，history_high 732.07/30084.5（=08-13），drawdown 复算一致，写入 09-04 文件（T-1 设计：周一 track 引用上周五美股收盘），trend 64 点/只
- **一并提交 09-04 遗留**: 09-04 晚 18:31 曾生成 09-04.json（ETF 3 条 + 09-03 文件 benchmark track 09-04）但未提交——本轮已含；并补全 09-03 文件 QQQ benchmark（track 09-04, quote 09-03）缺失的 trend（64 点，此前 QQQ trend=null）
- **Git**: commit 311e08e, push origin main 成功（4 files: 09-04 new + 09-07 new + 09-03 benchmark/trend + manifest）；index.html 为壳文件无 diff
- **自动化名称**: 已更新为 2026/09/08 纳指每日更新（09-07 周一 → 下一交易日 09-08 周二）
- **遗留未提交（属文档升级，非数据）**: CLAUDE.md / README.md / docs/HANDOFF.md / data_sources.json 的 09-03 westock 规则升级改动仍未纳入 commit（按指令仅 add index.html/manifest/daily-records）

## 2026-09-03 16:20（当天采集 09-03 + 一并提交 09-02 补录）
- **状态**: 成功（git pull 无更新 → 脚本正常记录当天数据）
- **背景**: 09-02 无提交记录（此前自动运行缺失），工作区已存在当天 15:28 生成的 09-02 补录数据（ETF trade 09-02 用 eastmoney_kline/sina_daily_kline + tinyright_iopv 回填，recorded_at=09-03 15:28），本次一并提交
- **ETF 数据 (09-03)**: 513100 price=2.196 (+0.05%) premium=11.46% / 159501 price=2.092 (+0.38%) premium=13.05% / 159659 price=2.316 (+0.13%) premium=8.82%；trend 64 点/只（eastmoney_quote/tencent 当天下行，实际来自 tinyright+新浪分时，source_ids 记 westock_etf_detail 沿用既有约定）
- **ETF 数据 (09-02 补录)**: 513100 2.195 premium=11.69% / 159501 2.084 premium=12.90% / 159659 2.313 premium=8.96%
- **Benchmark (track 09-03, quote 09-02)**: QQQ 709.24 (+0.23%) / NDX 29143.33 (+0.23%)，写入 09-02 文件；drawdown 复核一致
- **溢价率验证**: 六条全部通过 price/estimate-1 复算（差 <1e-4）
- **Trend 缺口（遗留待补）**: 09-02 的 513100/159501 ETF 分时缺失 —— 当天东财 push2his trends2 全程 RemoteDisconnected、腾讯 ifzq DNS 不可达、新浪该两只 09-02 缺早盘（10:35 起）；QQQ 09-02 分时已用新浪美股 5 分钟接口补全 64 点（sina_minute_kline）。后续可待东财/腾讯恢复后 --refresh-trends 或 westock data_minute 补齐
- **Git**: commit 6d13a80, push origin main 成功（4 files: 09-01 benchmark 补录 + 09-02 new + 09-03 new + manifest）
- **自动化名称**: 已更新为 2026/09/04 纳指每日更新（09-03 周四 → 下一交易日 09-04 周五）

## 2026-09-08 16:25（当天采集 09-08）
- **状态**: 成功。git pull 无更新 → 16:22 触发（A股已收盘）采集当天（09-08 周二）数据
- **数据源**: **westock MCP 本轮不可用**（会话内仅 agent-mail 在线，ToolSearch 查不到 data_quote/data_minute 等工具）→ 按规则执行 HTTP 兜底 `python record_nasdaq_etf.py`（27s，3 ETF + 2 benchmark），已记录原因
- **ETF 数据 (09-08)**: 513100 price=2.233 (-0.13%) prem=11.66% / 159501 price=2.108 (-0.09%) prem=12.22% / 159659 price=2.359 (-0.25%) prem=9.19%；estimate=1.9998/1.8784/2.1604（较周一微升，tinyright 实时值）；source_ids=eastmoney_quote；trend 64 点/只、09:30 起完整无停牌缺口；溢价率复算全部通过（差 <4e-5）
- **Benchmark (track 09-08, quote 09-04)**: QQQ 718.96 / NDX 29544.16——周一（09-07）美股 Labor Day 休市、周二美股未收盘，中国交易日 09-08 引用的最新美股收盘仍为 09-04（周五），故本次仅将 09-04 文件内 BM 行 track_date 09-07→09-08、recorded_at 刷新，数值不变
- **⚠️ 数据修复**: 本次脚本 upsert 时 QQQ 分时抓取失败，导致 09-04.json 的 QQQ BM trend 被空值覆盖（NDX 正常 64 点）；因分时是历史数据不会变化，已用 `git show HEAD` 取回原 64 点 trend 恢复，diff 收敛为仅 track_date/recorded_at（8 行变更）
- **Git**: commit e5ad128, push origin main 成功（3 files: 09-08 new + 09-04.json BM track 更新 + manifest）
- **自动化名称**: 已更新为 2026/09/09 纳指每日更新（09-08 周二 → 下一交易日 09-09 周三）

## 2026-09-08 补充（用户确认后）
- 走势图下线已随 commit a95b973 推送（页面删走势列、脚本停采分时、--refresh-trends no-op、文档同步）。
- 会话卡片标题规则：客户端 sessions 存于 ~/.workbuddy/workbuddy.db，显示 custom_title ?? title；近两轮因 title 为整段 prompt 导致左侧卡片显示原文。已直接改 DB：本轮 1a09dd88 → 2026/09/09 纳指每日更新、上轮 e573a055 → 2026/09/08 纳指每日更新（改前已备份 automation-backups/workbuddy.db.bak-20260908-1705.sqlite）。prompt 已新增第 10 步：每次跑完用 CODEBUDDY_SESSION_ID 自动把本会话 title/custom_title 更新为自动化名称。

## 2026-09-09 16:51（当天采集 09-09）
- **状态**: 成功。git pull 无更新 → 16:51 触发（A股已收盘）采集当天（09-09 周三）数据
- **数据源**: **westock MCP 本轮不可用**（ToolSearch 查不到 data_quote/data_etf/data_kline，会话内仅 agent-mail 在线，与 09-08 轮相同）→ 按规则执行 HTTP 兜底 `python record_nasdaq_etf.py`（约 5s），已记录原因
- **ETF 数据 (09-09)**: 513100 price=2.234 (+0.04%) prem=12.02% / 159501 price=2.103 (-0.24%) prem=12.27% / 159659 price=2.361 (+0.08%) prem=9.60%；estimate=1.9942/1.8731/2.1542；source_ids=westock_etf_detail（tinyright 实时估值链回退）；trend=null（走势图下线约定）；溢价率复算全部通过（差 <1e-3）
- **Benchmark (track 09-09, quote 09-08)**: QQQ 718.36 (-0.083%) / NDX 29507.7 (-0.123%)——美股周二（09-08）已于北京时间 09-09 凌晨收盘，本次新增写入 quote_date=09-08 的两条 BM 到 09-08.json（脚本 split_daily_records 按 quote_date 归档约定），track_date=09-09 供 09-09 中国交易日引用；history_high 732.07/30084.5 @08-13；drawdown -1.87%/-1.92%；source_ids=nasdaq_api_historical
- **Git**: commit 66c6c0c, push origin main 成功（3 files: 09-09.json new + 09-08.json BM 增补 + manifest）；index.html 仅行尾差异已 add 无实质变更
- **自动化名称**: 已更新为 2026/09/10 纳指每日更新（09-09 周三 → 下一交易日 09-10 周四）
- **会话卡片标题**: 已更新（workbuddy.db 备份 automation-backups/workbuddy.db.bak-20260909-165635.sqlite；sessions 61c33da7 title+custom_title → 2026/09/10 纳指每日更新，只读复查通过）

## ⚠️ 约定修正 2026-09-09 17:06（用户纠正）
- **自动化 name 与会话卡片标题含义不同**：
  - 自动化 name = 指向"下一个待采集交易日"（2026/09/10 纳指每日更新）→ 用 automation_update 更新，保持 09/10 不变
  - **会话卡片标题 = 本次运行实际执行采集的交易日**（本会话采集 09-09 数据 → 标题应为「2026/09/09 纳指每日更新」，而非自动化 name）
- 上一轮我错误地把卡片标题设成了自动化 name（09/10），用户指出后已改回 09/09（sessions 61c33da7 title+custom_title → 2026/09/09，备份 automation-backups/workbuddy.db.bak-20260909-170625.sqlite）
- **后续执行规则**：第 9 步 automation_update 的 name 用"下一交易日"；第 10 步会话卡片标题用**本次采集数据的 trade_date**（当天中国交易日），二者日期不同，勿再混用

## 2026-09-11 15:30（当天采集 09-11）
- **状态**: 成功。git pull 无更新 → 15:30 触发（A股已收盘）采集当天（09-11 周五）数据
- **数据源**: **westock MCP 本轮仍不可用**（ToolSearch 查 data_quote/data_etf/data_kline 及关键词均无结果，会话内仅 agent-mail 在线，与 09-07~09-10 轮一致）→ 按规则执行 HTTP 兜底 `python record_nasdaq_etf.py`（数秒完成），已记录原因
- **ETF 数据 (09-11)**: 513100 price=2.201 (-0.81%) prem=11.97% / 159501 price=2.092 (-0.33%) prem=13.30% / 159659 price=2.332 (-0.55%) prem=9.82%；estimate=1.9657/1.8464/2.1235；source_ids=westock_etf_detail（tinyright 估值链）；trend=null；溢价率复算全部通过（差 <1e-4）
- **Benchmark (track 09-11, quote 09-10)**: QQQ 708.69 (-1.064%) / NDX 29103.51 (-1.081%)——美股周四（09-10）已于北京时间 09-11 凌晨收盘，写入 quote_date=09-10 的两条 BM 到 09-10.json；history_high 732.07/30084.5 @08-13；drawdown -3.19%/-3.26%（复算一致）；source_ids=nasdaq_api_historical
- **Git**: commit 99f74f2, push origin main 成功（3 files: 09-11.json new + 09-10.json BM 增补 + manifest）；index.html 壳文件无 diff
- **自动化名称**: 已更新为 2026/09/14 纳指每日更新（09-11 周五 → 下一交易日 09-14 周一）
- **会话卡片标题**: 已更新（workbuddy.db 备份 automation-backups/workbuddy.db.bak-20260911-153124.sqlite；sessions 5d9ecdb9 title+custom_title → 2026/09/11 纳指每日更新，只读复查通过；更新前 title 已是该值，custom_title 本次补齐）

## 2026-09-10 15:31（当天采集 09-10）
- **状态**: 成功。git pull 无更新 → 15:31 触发（A股已收盘）采集当天（09-10 周四）数据
- **数据源**: **westock MCP 本轮不可用**（ToolSearch 查不到 data_quote/data_etf/data_kline，会话内仅 agent-mail 在线，与 09-07~09-09 轮相同）→ 按规则执行 HTTP 兜底 `python record_nasdaq_etf.py`（数秒完成），已记录原因
- **ETF 数据 (09-10)**: 513100 price=2.219 (-0.67%) prem=11.66% / 159501 price=2.099 (-0.19%) prem=12.45% / 159659 price=2.345 (-0.68%) prem=9.23%；estimate=1.9874/1.8667/2.1468；source_ids=westock_etf_detail（tinyright 估值链）；trend=null；溢价率复算全部通过（差 <1e-4）
- **Benchmark (track 09-10, quote 09-09)**: QQQ 716.31 (-0.285%) / NDX 29421.55 (-0.292%)——美股周三（09-09）已于北京时间 09-10 凌晨收盘，新增写入 quote_date=09-09 的两条 BM 到 09-09.json；history_high 732.07/30084.5 @08-13；drawdown -2.15%/-2.20%；source_ids=nasdaq_api_historical
- **Git**: commit 6e97c64, push origin main 成功（3 files: 09-10.json new + 09-09.json BM 增补 + manifest）；index.html 壳文件无 diff
- **自动化名称**: 已更新为 2026/09/11 纳指每日更新（09-10 周四 → 下一交易日 09-11 周五）
- **会话卡片标题**: 已更新（workbuddy.db 备份 automation-backups/workbuddy.db.bak-20260910-153144.sqlite；sessions f38eb6d6 title+custom_title → 2026/09/10 纳指每日更新，只读复查通过）


## 2026-09-15 09:16（本次为**补录**，补 09-14 周一）
- **状态**: 成功（补录）。09:16 触发（A股未收盘，早于常规 15:30）→ 走第 4 步：上一中国交易日 **2026-09-14 缺失**（最新记录原为 09-11 周五）→ 无人值守默认「补齐」→ D=2026-09-14
- **数据源**: **westock MCP 本轮仍不可用**（ToolSearch 查 data_quote/data_etf/data_kline 及关键词均无结果；会话内仅 agent-mail 在线，与 09-07~09-11 各轮一致）→ 按规则执行 HTTP 兜底 `python record_nasdaq_etf.py --backfill-date 2026-09-14`，已记录原因
- **ETF 数据 (09-14)**: 513100 price=2.191 (-0.454%) prem=10.48% / 159501 price=2.083 (-0.430%) prem=11.83% / 159659 price=2.317 (-0.643%) prem=8.15%；estimate=1.9831/1.8627/2.1423（tinyright_iopv@09-11）；source_ids=sina_daily_kline+tinyright_iopv；trend=null；溢价率复算全部通过
- **Benchmark (track 09-14, quote 09-11)**: QQQ 714.88 (+0.873%) / NDX 29368.44 (+0.910%)——美股周五（09-11）收盘，写入 quote_date=09-11 的两条 BM 到 **09-11.json**（该文件此前 benchmark_records 为空，本次补上）；history_high 732.07/30084.5 @08-13；drawdown -2.35%/-2.38%；source_ids=nasdaq_api_historical
- **交叉校验**（本轮额外做，因走 HTTP 兜底）: 新浪日K独立复核 3 只 ETF 09-14 收盘价完全一致；Nasdaq 官方 API 独立复核 QQQ/NDX 09-11 收盘价及历史序列完全一致
- **Git**: commit **fe88345** `Record Nasdaq tracking 2026-09-14`, push origin main 成功（3 files: 09-14.json new + 09-11.json BM 增补 + manifest）；index.html 壳文件无 diff
- **自动化名称**: 已更新为 **2026/09/15 纳指每日更新**（最新记录 09-14 周一 → 下一交易日 09-15 周二）
- **会话卡片标题**: 已更新（workbuddy.db 备份 automation-backups/workbuddy.db.bak-20260915-091600.sqlite；sessions 6df22f75 title+custom_title → 2026/09/14 纳指每日更新，只读复查通过；更新前 title 已为该值，custom_title 本次补齐）
- **注意**: 09-14 09:00-15:00 期间 A股正常交易但当时无自动化运行记录 → 09-14 整日缺口系漏采（非停牌）；下次如再遇早于 15:30 触发且前一交易日缺失，同样按补录处理

## 2026-09-16 15:30（当天采集 09-16）
- **状态**: 成功。git pull 无更新（Already up to date）→ 15:30 触发（A股已收盘）采集当天（09-16 周三）数据
- **数据源**: **westock MCP 本轮仍不可用**（ToolSearch 精确名 data_quote/data_etf/data_kline + 关键词"自选股 行情"均无结果，会话内仅 agent-mail 在线，与 09-07~09-15 各轮一致）→ 按规则执行 HTTP 兜底 `python record_nasdaq_etf.py`（数秒完成），已记录原因
- **ETF 数据 (09-16)**: 513100 price=2.218 (+1.00%) prem=13.63% / 159501 price=2.094 (+0.48%) prem=14.21% / 159659 price=2.320 (+0.30%) prem=10.03%；estimate=1.9519/1.8334/2.1085；source_ids=eastmoney_quote；trend=null；溢价率复算全部通过（差 <1e-4）
- **Benchmark (track 09-16, quote 09-15)**: QQQ 704.54 (-0.654%) / NDX 28937.84 (-0.650%)——写入 quote_date=09-15 的两条 BM 到 **09-15.json**；history_high 732.07/30084.5 @08-13；drawdown -3.76%/-3.81%（复算一致）；source_ids=nasdaq_api_historical
- **交叉校验**（HTTP 兜底轮次惯例）: 新浪日K独立复核 3 只 ETF 09-16 收盘价完全一致（2.218/2.094/2.320）；Nasdaq 官方 API 独立复核 QQQ/NDX 09-15 收盘价完全一致（704.54/28937.84）。**注意 Nasdaq API 必须带 fromdate 参数**，否则返回 rCode 400 "The fromdate field is required."
- **index.html**: 先备份再跑脚本（防抹用户侧改动）→ 比对发现脚本产物与 HEAD 版本**无差异**（09-15 的 `data-page-node-id` 用户改动已于 commit 14b95b8 提交），index.html 本轮无 diff 未纳入提交
- **Git**: commit **c552de4** `Record Nasdaq tracking 2026-09-16`, push origin main 成功（3 files: 09-16.json new + 09-15.json BM 增补 + manifest）
- **自动化名称**: 已更新为 **2026/09/17 纳指每日更新**（最新记录 09-16 周三 → 下一交易日 09-17 周四）
- **会话卡片标题**: 已更新（workbuddy.db 备份 automation-backups/workbuddy.db.bak-20260916-153200.sqlite；sessions 611284c6 title+custom_title → 2026/09/16 纳指每日更新，只读复查通过；更新前 title 已为该值，custom_title 本轮补齐）

## 2026-09-15 15:30（当天采集 09-15）
- **状态**: 成功。git pull 无更新 → 15:30 触发（A股已收盘）采集当天（09-15 周二）数据
- **数据源**: **westock MCP 本轮仍不可用**（ToolSearch 精确名 data_quote/data_etf/data_kline + 关键词"自选股 行情"均无结果，会话内仅 agent-mail 在线，与 09-07~09-14 各轮一致）→ 按规则执行 HTTP 兜底 `python record_nasdaq_etf.py`（数秒完成），已记录原因
- **ETF 数据 (09-15)**: 513100 price=2.196 (+0.23%) prem=11.73% / 159501 price=2.084 (+0.05%) prem=12.88% / 159659 price=2.313 (-0.17%) prem=8.93%；estimate=1.9655/1.8462/2.1233；source_ids=eastmoney_quote（本轮兜底命中东财报价而非新浪日K）；trend=null；溢价率复算全部通过（差 <1e-4）
- **Benchmark (track 09-15, quote 09-14)**: QQQ 709.18 (-0.797%) / NDX 29127.16 (-0.822%)——写入 quote_date=09-14 的两条 BM 到 **09-14.json**（此前 benchmark_records 为空，本轮补上）；history_high 732.07/30084.5 @08-13；drawdown -3.13%/-3.18%；source_ids=nasdaq_api_historical
- **交叉校验**（HTTP 兜底轮次惯例）: 新浪日K独立复核 3 只 ETF 09-15 收盘价完全一致（2.196/2.084/2.313）；Nasdaq 官方 API 独立复核 QQQ/NDX 09-14 收盘价完全一致（709.18/29127.16）
- **index.html 特殊处理**: 发现 index.html 有用户侧未提交改动（09:18 由智能页面工具写入 `data-page-node-id` 属性，7 行）。脚本 write_page_and_data 会整文件重写 index.html 从而抹掉这些属性 → 本轮先备份 index.html 再跑脚本，跑完用备份覆盖回用户版本（已确认脚本产物与用户版本的**唯一差异**就是这些 node-id 属性），最终把用户版本一并提交
- **Git**: commit **14b95b8** `Record Nasdaq tracking 2026-09-15`, push origin main 成功（4 files: 09-15.json new + 09-14.json BM 增补 + manifest + index.html）；data/ 与 index.html 工作区已干净
- **自动化名称**: 已更新为 **2026/09/16 纳指每日更新**（最新记录 09-15 周二 → 下一交易日 09-16 周三）
- **会话卡片标题**: 已更新（workbuddy.db 备份 automation-backups/workbuddy.db.bak-20260915-153245.sqlite；sessions 9ed13610 title+custom_title → 2026/09/15 纳指每日更新，只读复查通过；更新前 title 已为该值，custom_title 本轮补齐）

## 2026-09-23 10:19（本轮为**补录**，一次性补 09-17 / 09-18 / 09-21 / 09-22 共 4 个交易日）
- **状态**: 成功（补录）。10:19 触发（A股未收盘，早于常规 15:30）→ 检查最新记录为 09-16，缺口 09-17(四)/09-18(五)/09-21(一)/09-22(二) 共 4 个交易日 → 无人值守默认「全部补齐」（不止补前一日，避免留下 3 天空洞）
- **数据源**: **westock MCP 本轮仍不可用**（ToolSearch 精确名 data_quote/data_etf/data_kline + 关键词"自选股 行情"均无结果；会话内仅 agent-mail 在线，与 09-07~09-16 各轮一致）→ 按规则走 HTTP 兜底 `python record_nasdaq_etf.py --backfill-date <D>`，逐日跑 4 次（每次约 1~2 min）
- **ETF 数据**（均 trend=null，溢价率复算全部通过，差 <1e-6）:
  - 09-17: 513100 price=2.220 prem=13.77% / 159501 2.095 prem=14.31% / 159659 2.328 prem=10.44%；est=1.9513/1.8328/2.1079（eastmoney_kline+eastmoney_fund_nav）
  - 09-18: 513100 2.269 prem=14.39% / 159501 2.129 prem=14.27% / 159659 2.368 prem=10.51%；est=1.9836/1.8632/2.1428（sina_daily_kline+eastmoney_fund_nav）
  - 09-21: 513100 2.283 prem=14.44% / 159501 2.156 prem=15.05% / 159659 2.383 prem=10.57%；est=1.9949/1.8739/2.1552
  - 09-22: 513100 2.316 prem=12.96% / 159501 2.193 prem=13.86% / 159659 2.432 prem=9.77%；est=2.0503/1.926/2.2155（sina_daily_kline/eastmoney_kline + tinyright_iopv）
- **Benchmark**（按 T-1 归档到 quote_date 所在文件）: quote 09-16 → QQQ 704.72 / NDX 28945.06（写入 09-16.json）；quote 09-17 → 716.92 / 29446.98（09-17.json）；quote 09-18 → 721.45 / 29644.17（09-18.json）；quote 09-21 → **741.47 / 30482.35（双双创历史新高）**，history_high 732.07→741.47、30084.5→30482.35 @09-21，drawdown=0（写入 09-21.json）。09-22.json 暂无 BM（其 BM 属 quote 09-22 / track 09-23，留待下轮）
- **交叉校验**（HTTP 兜底轮次惯例）: 新浪日K独立复核 4 日 ×3 只 ETF 收盘价完全一致（2.220/2.095/2.328、2.269/2.129/2.368、2.283/2.156/2.383、2.316/2.193/2.432）；Nasdaq 官方 API 独立复核 QQQ/NDX 09-16~09-21 收盘价完全一致（含 fromdate 参数）
- **09-17 首次失败**: tinyright SSL handshake timeout（`<urlopen error _ssl.c:1015: The handshake operation timed out>`）→ 重试一次即成功；其余三日一次通过
- **index.html 处理**: 脚本 write_page_and_data 重写 index.html 时抹掉了用户侧 `data-page-node-id` 属性（14b95b8 提交的）→ 用运行前备份覆盖回用户版本，最终 index.html 与 HEAD 无 diff，未纳入提交
- **Git**: commit **0603abc** `Record Nasdaq tracking 2026-09-22`, push origin main 成功（6 files: 09-17/18/21/22.json 新增 + 09-16.json BM 增补 + manifest.json）；工作区 data/ 干净
- **自动化名称**: 已更新为 **2026/09/23 纳指每日更新**（最新记录 09-22 周二 → 下一交易日 09-23 周三）
- **会话卡片标题**: 已更新（workbuddy.db 备份 automation-backups/workbuddy.db.bak-20260923-102752.sqlite；sessions 2a501122-66cf-48cd-b64f-1ae108484a54 title+custom_title → 2026/09/22 纳指每日更新，只读复查通过）。**更新前 title 为「2026/09/17 纳指每日更新」→ 印证自动化自 09-16 15:30 后至 09-22 未运行，缺口系漏采**
- **教训/建议**: 若客户端长时间未运行自动化，单轮可能面对多日缺口；按「补齐所有缺失交易日」处理（而非只补前一日）更符合项目完整日序列的目标


## 2026-09-24 16:32（正常采集 + 补前一日缺口）
- **状态**: 成功。最新记录为 09-22 → 缺口 09-23(三) + 09-24(四, 当天已收盘) → 一并处理
- **数据源**: westock MCP 仍不可用（ToolSearch 精确名 + 关键词"自选股 行情"/"ETF 估值 IOPV" 均无结果）→ HTTP 兜底
  - 09-23 用 `python record_nasdaq_etf.py --backfill-date 2026-09-23`
  - 09-24 用 `python record_nasdaq_etf.py`（正常收盘路径）
- **ETF 数据**（trend=null，溢价率复算全部精确通过）:
  - 09-23: 513100 2.334(+0.78%,est 2.066,prem 12.97%) / 159501 2.219(+1.19%,1.9409,14.33%) / 159659 2.456(+0.99%,2.2323,10.02%)，src=sina_daily_kline+tinyright_iopv
  - 09-24: 513100 2.312(-0.94%,est 2.0487,prem 12.85%) / 159501 2.212(-0.32%,1.9246,14.93%) / 159659 2.423(-1.34%,2.2136,9.46%)
- **Benchmark**: quote 09-22 → QQQ 747.46 / NDX 30732.40（写入 09-22.json，双创新高，history_high 741.47→747.46 / 30084.5→30732.4 @09-22）；quote 09-23 → QQQ 741.21(-0.84%) / NDX 30470.29(-0.85%)（写入 09-23.json，drawdown -0.84%/-0.85%）
- **交叉校验**: 新浪日K 3只ETF 09-23/09-24 收盘完全一致；Nasdaq 官方 API QQQ 741.21/747.46、NDX 30470.29/30732.40 完全一致
- **新发现/已处理的问题**:
  1. **eastmoney_quote 本次不可用**（push2.eastmoney.com `RemoteDisconnected`，连试 5 次均失败），脚本 `build_etf_rows` 回退到 tinyright，导致 (a) `source_ids` 被硬编码写成 `["westock_etf_detail"]`（**虚假标记**，westock 并未使用），(b) `name` 变成 tinyright 的"国泰纳指100"而非配置规范名"纳指ETF国泰"，(c) `premium` 取的是 tinyright 的 4 位小数四舍五入值而非精确 price/estimate-1
     → 已手动规范化 09-24 记录：name 用 data_sources.json 配置名、source_ids 改为如实 `["tinyright_quote","tinyright_t1"]`、premium 精确 = price/estimate-1，然后用模块函数 `read_records` + `write_page_and_data` 重建页面（未重新取数）
     → **历史同类问题**：`('westock_etf_detail',)` 组合在库中已出现 27 条（约 9 个交易日）、非规范名 11 条，即该误标已长期存在。**建议后续把 record_nasdaq_etf.py:915 的 fallback 标签改为如实的 tinyright_* 并优先用配置名**（本轮未改脚本，避免无人值守时变更行为）
  2. index.html 又被脚本重写抹掉用户侧 `data-page-node-id`（7 行）→ 用运行前备份 `automation-backups/index.html.bak-20260924-163257` 恢复，恢复后与 HEAD 无 diff，故未纳入提交
- **Git**: commit **e56af55** `Record Nasdaq tracking 2026-09-24`，push origin main 成功（4 files: 09-23/09-24.json 新增 + 09-22.json BM 增补 + manifest.json）
- **自动化名称**: → **2026/09/25 纳指每日更新**（最新记录 09-24 周四 → 下一交易日 09-25 周五）
- **会话卡片标题**: → **2026/09/24 纳指每日更新**（workbuddy.db 备份 automation-backups/workbuddy.db.bak-20260924-163736.sqlite；sessions b453e92b title+custom_title 均已写入，只读复查通过；更新前 title 为「2026/09/23」= 上轮自动化名）

## 2026-10-09 10:04（本轮为**多日补录**，补 09-28 / 09-29 / 09-30 / 10-08）
- **状态**: 成功。10:04 触发（A股未收盘）→ 最新记录原为 09-24 → 依 2026 中秋(09-25~09-27)/国庆(10-01~10-07)休市安排，实际缺口 = **09-28、09-29、09-30、10-08** 共 4 个中国交易日
- **数据源**: **westock MCP 仍不可用**（ToolSearch 精确名 data_quote/data_etf/data_kline 无结果，仅 agent-mail 在线，与 09-07~09-24 各轮一致）→ HTTP 兜底
- **ETF 数据**（trend=null，溢价率精确复算通过）:
  - 09-28: 513100 2.304(-0.35%) prem=12.40% / 159501 2.214(+0.09%) 14.97% / 159659 2.412(-0.45%) 8.86%；est=NAV(09-24)=2.0498/1.9257/2.2156
  - 09-29: 2.324(+0.87%)/2.236(+0.99%)/2.423(+0.46%)；est=NAV(09-28)=2.0335/1.9104/2.1984；src=sina_daily_kline+eastmoney_fund_nav
  - 09-30: 2.352(+1.20%)/2.205(-1.39%)/2.455(+1.32%)；est=NAV(09-29)=2.0379/1.9146/2.2028
  - 10-08: 2.374(+0.94%)/2.205(0.00%)/2.478(+0.94%)；est=NAV(09-30)=2.0409/1.9171/2.2058
- **Benchmark**（按 quote_date 归档）: track 09-28→q 09-25 QQQ 744.50 / NDX 30608.13（写入 09-25.json）；track 09-29→q 09-28 736.53/30276.81（09-28.json）；track 09-30→q 09-29 737.93/30339.33（09-29.json）；track 10-08→q 10-07 757.73/31160.08，**history_high 更新 747.46→759.66@10-06**（写入 10-07.json）
- **⚠️ 脚本回填节后首日失败（新坑，后续节假日会复现）**: `--backfill-date` 对 09-29/09-30 成功，对 **09-28/10-08 报 `valuation date mismatch`** —— 脚本要求 `NAV(quote_date)`，而节后首日的 quote_date 落在**中国节假日**（09-25/10-07）当日无基金净值 → 抛错。**已手工补齐**（importlib 载入脚本：parse_historical_etf_quote 取价 + parse_eastmoney_fund_nav(前一中国交易日) 取估值 + build_benchmark_rows + write_rows，未改脚本）。口径已用 06-22 端午先例验证：`estimate(track D)=最近中国交易日 NAV`，`BM.quote_date=最近美股交易日≤D-1`
- **⚠️ HTTP 兜底本轮两个瞬时故障**: (1) `n.tinyright.com` 首次连续 4 次 SSL handshake/read timeout（重试后恢复；该域名要求浏览器 UA，默认 urllib UA 会 403）；(2) `api.nasdaq.com` 在 lookback=11000 天时易 `SSL UNEXPECTED_EOF`，加 4~6 次重试可成功
- **BM-only 文件**: 节后首日 quote_date 落节假日 → 自然产生 `2026-09-25.json` / `2026-10-07.json`（仅 benchmark）。前端按 quote_date 分组可正常渲染，属 T-1 设计必然结果
- **交叉校验**: ETF 收盘 vs 新浪日K 完全一致；QQQ/NDX vs Nasdaq 官方 API 完全一致
- **index.html**: 脚本重写抹掉用户侧 `data-page-node-id`（7 行）→ 用运行前备份 `automation-backups/index.html.bak-20261009-100434` 恢复，与 HEAD 无 diff，未纳入提交
- **Git**: commit **3c18570** `Record Nasdaq tracking 2026-10-08`，push origin main 成功（7 files: 09-25/09-28/09-29/09-30/10-07/10-08.json 新增 + manifest）
- **自动化名称**: → **2026/10/09 纳指每日更新**（最新记录 10-08 周四 → 下一交易日 10-09 周五）
- **会话卡片标题**: → **2026/10/08 纳指每日更新**（db 备份 automation-backups/workbuddy.db.bak-20261009-103435.sqlite；sessions 621ae4a1 title+custom_title 均写入，只读复查通过；**改前 title 为「2026/09/25」= 上轮自动化名 → 说明 09-25 之后自动化一直未成功运行**）
- **待办建议（未改脚本，需用户确认）**: 回填估值在 `NAV(quote_date)` 缺失时回退到「最近中国交易日 NAV」，可免节后首日手工；另 `record_nasdaq_etf.py:915` 兜底 source_ids 误标 + 名称非规范化（见项目 MEMORY.md 2026-09-24 条）

## 2026-10-09 15:30（当天采集 10-09，本轮为**当日正常采集**）
- **状态**: 成功。git pull 无更新 → 15:30 触发（A股已收盘）采集当天（10-09 周五）数据
- **数据源**: **westock MCP 仍不可用**（ToolSearch 精确名 data_quote/data_etf/data_kline + 关键词均无结果，仅 agent-mail 在线）→ HTTP 兜底 `python record_nasdaq_etf.py`（3 ETF + 2 BM，数秒完成）
- **ETF 数据 (10-09)**: 513100 price=2.398 (+1.01%) prem=19.13% / 159501 2.220 (+0.68%) prem=17.41% / 159659 2.503 (+1.01%) prem=15.05%；est=2.0129/1.8908/2.1756（tinyright「T-1估值」，T-1估值日=10-08）；trend=null；溢价率复算通过（差 ~1e-5，源端 4 位取整）
- **Benchmark (track 10-09, quote 10-08)**: QQQ 747.58 (-1.34%) / NDX 30725.81 (-1.39%)，history_high 759.66/31224.69 @10-06，drawdown -1.59%/-1.60%，写入 **10-08.json**
- **交叉校验**: 新浪日K 复核 3 只 ETF 10-09 收盘完全一致（2.398/2.220/2.503）；Nasdaq 官方 API 复核 QQQ/NDX 10-08 收盘完全一致（含 fromdate）
- **⚠️ 新发现（估值源在长假后失真，重要）**: tinyright 的「T-1估值」在长假后系统性偏低约 2.4%。其公式 = `最近已公布官方NAV × 最近一个美股交易日涨跌`，即只套用**单日**变动；长假期间跨越多个美股交易日（09-30→10-07 共 5 个）的累计涨幅被漏掉。实证：t1(10-08)=2.0129 = NAV(09-30)2.0409 × (NDX10-08/NDX10-07)，而按 `NAV(d)∝NDX(d)` 模型（9 月 12 个交易日残差仅 0.03~0.12%）推得 NAV(10-08)≈2.058~2.062。**本轮按既有约定（MEMORY.md 明示 estimate=tinyright T-1 语义）如实记录源值，未擅自替换**；建议用户决定是否加长假修正。详见项目 MEMORY.md 2026-10-09 条
- **附带发现**: 官方 NAV 最新只到 09-30（QDII T+1/T+2 滞后，10-08 净值尚未公布）；本脚本正常路径未把 tinyright_t1 记入 source_ids（仅 `["eastmoney_quote"]`），而 6 月记录曾记 `["eastmoney_quote","tinyright_t1"]`，属元数据遗漏（同 09-24 待办）
- **index.html**: 脚本重写会重新生成 `data-page-node-id`（与 HEAD 的 7 行值不同）→ 用运行前备份 `automation-backups/index.html.bak-20261009-153107` 恢复，恢复后与 HEAD 无 diff，未纳入提交
- **Git**: commit **2d544f2** `Record Nasdaq tracking 2026-10-09`，push origin main 成功（3 files: 10-09.json 新增 + 10-08.json BM 增补 + manifest）
- **自动化名称**: → **2026/10/12 纳指每日更新**（最新记录 10-09 周五 → 下一中国交易日 10-12 周一）
- **会话卡片标题**: → **2026/10/09 纳指每日更新**（db 备份 automation-backups/workbuddy.db.bak-20261009-153632.sqlite；sessions 01fea331 title+custom_title 均写入，只读复查通过；改前 title 已是该值、custom_title 为 None）

## 2026-10-12 15:39（当天采集 10-12）
- **状态**: 成功。git pull 无更新（Already up to date）→ 15:39 触发（A股已收盘）采集当天（10-12 周一）数据
- **数据源**: **westock MCP 仍不可用**（ToolSearch 精确名 data_quote/data_etf/data_kline + 关键词均无结果，仅 agent-mail 在线，与 09-07 起各轮一致）→ HTTP 兜底 `python record_nasdaq_etf.py`（数秒完成）
- **ETF 数据 (10-12)**: 513100 price=2.400 (+0.08%) prem=15.85% / 159501 2.238 (+0.81%) prem=15.00% / 159659 2.529 (+1.04%) prem=12.94%；est=2.0716/1.9462/2.2392（tinyright t1，t1_date=10-09）；source_ids=eastmoney_quote；trend=null；溢价率复算通过（差 <7e-5，源端 4 位取整）
- **Benchmark (track 10-12, quote 10-09)**: QQQ 751.27 (+0.494%) / NDX 30883.15 (+0.512%)，history_high 759.66/31224.69 @10-06，drawdown -1.10%/-1.09%，写入 **10-09.json**；source_ids=nasdaq_api_historical
- **交叉校验**: 新浪日K 复核 3 只 ETF 10-12 收盘完全一致（2.400/2.238/2.529）；Nasdaq 官方 API 复核 QQQ/NDX 10-09 收盘完全一致（751.27/30883.15）。**注意 NDX 需 assetclass=index**（用 etf 会返回 rCode 400 "Symbol not exists."）
- **✅ 估值失真已自愈（重要正面发现）**: tinyright 官方 NAV 已补到 **10-08**（iopvData date=10-08，2.0622/1.9373/2.2290），故「长假后 T-1 估值失真」（10-09 记录的问题）本轮消失。用 `NAV(d)∝NDX(d)` 模型复核：NAV(10-08) 模型值 vs 官方 IOPV 差仅 0.01%；t1(10-09) vs 「NAV(10-08)×当日NDX变动」差 **-0.055%（三只完全一致）**，属系统性残差（已知区间 0.03~0.12%）。→ **本轮 estimate 准确，未做任何修正**；溢价率下降（19.13%→15.85% 等）系 NAV 长假累计涨幅回补所致，非异常
- **index.html**: 先备份 `automation-backups/index.html.bak-20261012-153912` → 跑脚本后用备份恢复（脚本重写会改 `data-page-node-id`），恢复后与 HEAD **无 diff**，未纳入提交
- **Git**: commit **982b30b** `Record Nasdaq tracking 2026-10-12`，push origin main 成功（3 files: 10-12.json 新增 + 10-09.json BM 增补 + manifest）
- **自动化名称**: → **2026/10/13 纳指每日更新**（最新记录 10-12 周一 → 下一交易日 10-13 周二）
- **会话卡片标题**: → **2026/10/12 纳指每日更新**（db 备份 automation-backups/workbuddy.db.bak-20261012-154000.sqlite；sessions 46f154d3 title+custom_title 均写入，只读复查通过；改前 title 已是该值、custom_title 为 None）

## 2026-10-15 14:09（本轮为**多日补录**，补 10-13 / 10-14）
- **状态**: 成功。14:09 触发（A股未收盘，早于常规 15:30）→ 最新记录原为 10-12 周一 → 缺口 10-13(二) + 10-14(三) 共 2 个中国交易日 → 无人值守默认「全部补齐」
- **数据源**: **westock MCP 仍不可用**（ToolSearch 精确名 data_quote/data_etf/data_kline + 关键词"自选股 行情"/"ETF 估值 IOPV" 均无结果，仅 agent-mail 在线，与 09-07 起各轮一致）→ HTTP 兜底 `python record_nasdaq_etf.py --backfill-date <D>`，逐日两次
- **ETF 数据**（trend=null，溢价率精确复算通过，差 = 0）:
  - 10-13: 513100 2.375(-1.04%,est 2.0563,prem 15.499%) / 159501 2.221(-0.76%,1.9317,14.976%) / 159659 2.506(-0.91%,2.2224,12.761%)，src=eastmoney_kline+eastmoney_fund_nav
  - 10-14: 513100 2.399(+1.01%,est 2.0494,prem 17.059%) / 159501 2.229(+0.36%,1.9252,15.780%) / 159659 2.517(+0.44%,2.215,13.634%)，src=eastmoney_kline+tinyright_iopv
- **Benchmark**（按 quote_date 归档）: track 10-13 → quote 10-12 QQQ 746.04(-0.696%) / NDX 30664.70(-0.707%)（写入 **10-12.json**，该文件此前 BM 为空，本轮补上）；track 10-14 → quote 10-13 QQQ 743.57(-0.331%) / NDX 30569.48(-0.311%)（写入 10-13.json）。history_high 759.66 / 31224.69 @10-06 维持不变（10-12~10-13 均低于 10-06 高点），drawdown -2.12%/-2.10%
- **10-14.json 无 BM**：其 BM 属 quote 10-14 / track 10-15，留待下轮（下一轮将记录 QQQ 728.95 / NDX 29950.82，10-14 美股大幅回落约 -2%）
- **交叉校验**（HTTP 兜底轮次惯例）: 新浪日K独立复核 3 只 ETF 10-13/10-14 收盘完全一致（2.375/2.221/2.506、2.399/2.229/2.517）；Nasdaq 官方 API 独立复核 QQQ/NDX 10-12/10-13 收盘完全一致（746.04/30664.70、743.57/30569.48）。注意 NDX 需 `assetclass=index`、接口必须带 `fromdate`
- **估值口径核验**（NAV∝NDX 模型）: NAV(10-12)/NAV(10-09)=0.99261 vs NDX 比值 0.99294；NAV(10-13)/NAV(10-12)=0.99664 vs 0.99689 → 残差 0.02~0.03%，属已知系统性残差。**长假后 T-1 估值失真问题未复现，本轮 estimate 准确，无需修正**
- **瞬时故障**: 10-14 首次回填报 `n.tinyright.com read timeout` → **重试一次即成功**（与既有经验一致，勿立即换源）
- **index.html**: 先备份 `automation-backups/index.html.bak-20261015-140900` → 跑脚本后用备份恢复（脚本重写会改 `data-page-node-id`），恢复后与 HEAD **无 diff**，未纳入提交
- **Git**: commit **d3b924e** `Record Nasdaq tracking 2026-10-14`，push origin main 成功（4 files: 10-13.json new + 10-14.json new + 10-12.json BM 增补 + manifest）
- **自动化名称**: → **2026/10/15 纳指每日更新**（最新记录 10-14 周三 → 下一交易日 10-15 周四 = 今天，尚未采集）
- **会话卡片标题**: → **2026/10/14 纳指每日更新**（db 备份 automation-backups/workbuddy.db.bak-20261015-141500.sqlite；sessions 36053684 title+custom_title 均写入，只读复查通过；改前 title 为「2026/10/13」= 上轮自动化名 → 印证 10-13/10-14 自动化未运行，缺口系漏采）

## 2026-10-15 14:15（**空跑 no-op**：客户端二次触发，无缺口）
- **状态**: 跳过（无采集、无提交）。14:09 那次（session 36053684）已于 **14:14:08** 结束并补齐 10-13/10-14；**14:14:47** 客户端又起了一个会话（session 00e8a6ec，即本轮）。推测客户端把两次漏跑（10-13 15:30、10-14 15:30）都排入队列，第一条已一并覆盖两日 → 第二条无缺口
- **判定依据**: 14:14 早于 A 股 15:00 收盘（非收盘时段）→ 走第 4 步检查前一中国交易日 **10-14 已存在**（10-01~10-07 国庆休市后 10-08/09/12/13/14 连续无缺口）→ 无需补录
- **数据源**: westock MCP 仍不可用（ToolSearch 精确名 data_quote/data_etf/data_kline 无结果，仅 agent-mail 在线）→ 因无需取数，未走 HTTP 兜底
- **数据核验（对最新 10-14.json）**: 3 条 ETF 代码 513100/159501/159659 正确；premium 与 price/estimate-1 复算**差=0**（17.0587%/15.7802%/13.6343%）；trend=null；benchmark_records 为空（其 BM 属 quote 10-14/track 10-15，下轮写入）
- **Git**: 无数据变更 → 跳过提交（工作区仅 .workbuddy/ 文件变动，不属第 6 步提交范围）
- **自动化名称**: 保持 **2026/10/15 纳指每日更新**（最新记录 10-14 周三 → 下一中国交易日 10-15 周四 = 今天，仍未采集）
- **会话卡片标题**: → **2026/10/15 纳指每日更新**（db 备份 automation-backups/workbuddy.db.bak-20261015-141557.sqlite；sessions 00e8a6ec title+custom_title 均写入，只读复查通过）。**说明**：本轮无"实际采集交易日"，故沿用客户端按自动化 name 生成的默认标题（10/15 = 待采集交易日）；改前 title 已是该值、custom_title 为 None
- **经验**: 客户端在长期间断后可能一次排队多个漏跑实例；同一天内可能出现「前一条补完缺口、后一条空跑」的连续会话，此时按「无缺口 → 跳过」处理即可，勿重复采集

## 2026-10-15 15:30（当天采集 10-15）
- **状态**: 成功。git pull 无更新（Already up to date）→ 15:30 触发（A股已收盘）采集当天（10-15 周四）数据，D=2026-10-15
- **数据源**: **westock MCP 仍不可用**（ToolSearch 精确名 data_quote/data_etf/data_kline + 关键词均无结果，仅 agent-mail 在线，与 09-07 起各轮一致）→ HTTP 兜底 `python record_nasdaq_etf.py`（数秒完成）
- **ETF 数据 (10-15)**: 513100 price=2.321 (-3.25%) prem=15.68% / 159501 2.170 (-2.65%) prem=15.13% / 159659 2.430 (-3.46%) prem=12.05%；est=2.0065/1.8849/2.1686（=NAV(10-14)）；source_ids=eastmoney_quote（**本轮东财报价链正常**，名称用配置规范名、非 tinyright 回退，与 09-24 记录的误标情形不同）；trend=null；溢价率复算差 <1e-4（源端 4 位取整）
- **Benchmark (track 10-15, quote 10-14)**: QQQ 728.95 (-1.97%) / NDX 29950.82 (-2.02%)——写入 quote_date=10-14 的两条 BM 到 **10-14.json**（该文件此前 BM 为空，本轮补上，与上轮预告一致）；history_high 759.66/31224.69 @10-06，drawdown -4.04%/-4.08%；source_ids=nasdaq_api_historical
- **交叉校验**（HTTP 兜底轮次惯例）: 新浪日K独立复核 3 只 ETF 10-15 收盘完全一致（2.321/2.170/2.430）；Nasdaq 官方 API 独立复核 QQQ/NDX 10-14 收盘完全一致（728.95/29950.82）。注意 NDX 需 `assetclass=index`、接口必须带 `fromdate`
- **估值口径核验**: NAV(10-14)/NAV(10-13)=0.979067 vs NDX(10-14)/NDX(10-13)=0.979758 → 残差 0.07%，属已知系统性残差（0.03~0.12%）。长假后 T-1 估值失真未复现，estimate 准确，无需修正
- **index.html**: 先备份 `automation-backups/index.html.bak-20261015-153100` → 跑脚本后用备份恢复（脚本重写会抹掉用户侧 `data-page-node-id` 7 行），恢复后与 HEAD **无 diff**，未纳入提交
- **Git**: commit **833684c** `Record Nasdaq tracking 2026-10-15`，push origin main 成功（3 files: 10-15.json new + 10-14.json BM 增补 + manifest）
- **自动化名称**: → **2026/10/16 纳指每日更新**（最新记录 10-15 周四 → 下一交易日 10-16 周五）
- **会话卡片标题**: → **2026/10/15 纳指每日更新**（db 备份 automation-backups/workbuddy.db.bak-20261015-153300.sqlite；sessions 226a6d11 title+custom_title 均写入，只读复查通过；改前 title 已是该值、custom_title 为 None）

## 2026-10-16 16:02（当天采集 10-16）
- **状态**: 成功。git pull 无更新（Already up to date）→ 16:02 触发（A股已收盘）采集当天（10-16 周五）数据，D=2026-10-16。无缺口（最新记录原为 10-15）
- **数据源**: **westock MCP 仍不可用**（ToolSearch 精确名 data_quote/data_etf/data_kline + 关键词"自选股 行情"/"ETF IOPV 日K" 均无结果，仅 agent-mail 在线，与 09-07 起各轮一致）→ HTTP 兜底 `python record_nasdaq_etf.py`（数秒完成）
- **ETF 数据 (10-16)**: 513100 price=2.356 (+1.51%) prem=17.46% / 159501 2.207 (+1.71%) prem=17.13% / 159659 2.471 (+1.69%) prem=13.99%；est=2.0058/1.8842/2.1677（=NAV(10-15)）；source_ids=eastmoney_quote（**东财报价链正常**，名称用配置规范名，无 tinyright 回退误标）；trend=null；溢价率复算差 <2e-5（源端 4 位取整）
- **Benchmark (track 10-16, quote 10-15)**: QQQ 728.00 (-0.130%) / NDX 29935.59 (-0.051%)——写入 quote_date=10-15 的两条 BM 到 **10-15.json**（该文件此前 BM 为空，本轮补上）；history_high 759.66/31224.69 @10-06；drawdown -4.17%/-4.13%；source_ids=nasdaq_api_historical
- **交叉校验**（HTTP 兜底轮次惯例）: 新浪日K独立复核 3 只 ETF 10-16 收盘完全一致（2.356/2.207/2.471）；Nasdaq 官方 API 独立复核 QQQ/NDX 10-15 收盘完全一致（728.00/29935.59）。注意 NDX 需 `assetclass=index`、接口必须带 `fromdate`
- **估值口径核验**: est(10-16) 2.0058/1.8842/2.1677 较 10-15 的 2.0065/1.8849/2.1686 微降，与 NDX(10-15) -0.05% 方向一致；长假后 T-1 估值失真未复现，estimate 准确，无需修正
- **index.html**: 先备份 `automation-backups/index.html.bak-20261016-160200` → 跑脚本后用备份恢复（脚本重写会改 `data-page-node-id`），恢复后与 HEAD **无 diff**，未纳入提交
- **Git**: commit **998e5f2** `Record Nasdaq tracking 2026-10-16`，push origin main 成功（3 files: 10-16.json new + 10-15.json BM 增补 + manifest）
- **自动化名称**: **未改动** —— 检查发现当前 name 已是通用名「纳指每日更新」（无日期前缀），与上轮设的「2026/10/16 纳指每日更新」不同，疑为用户近期手动改名；且本轮 prompt 未包含改名步骤 → 保守起见保留现状，未写日期
- **会话卡片标题**: → **2026/10/16 纳指每日更新**（db 备份 automation-backups/workbuddy.db.bak-20261016-160600.sqlite；sessions 8c40de85 title+custom_title 均写入，只读复查通过；改前 title 为自动化名「纳指每日更新」、custom_title 为 None）
