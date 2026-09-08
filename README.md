# Nasdaq Tracking Daily Record

纳斯达克 100 指数跟踪工具。记录三只 A 股纳指 ETF 的交易日收盘后数据，同时跟踪 QQQ 和 NDX 距离历史最高收盘点/价的回撤，并生成一个可通过本地 HTTP 服务或 GitHub Pages 查看的 HTML 页面。

完整的项目架构、数据口径、日常更新、历史补录、自动任务和故障排查说明见 [项目交接文档](docs/HANDOFF.md)。

> **走势图已下线（2026-09-08）**：页面不再展示分时走势，采集流程不再获取分钟数据；历史记录中已有的 `trend` 字段原样保留但不使用。`--refresh-trends` 已弃用（no-op）。

## 记录对象

- `513100`
- `159501`
- `159659`
- `QQQ`
- `NDX`

## ETF 记录字段

- 交易日期
- 代码
- 名称
- 当前价格
- 当天涨幅
- 当前净值（替代 T-1 估值，来自腾讯自选股 ETF 详情 `nav` 字段）
- 溢价率
- 数据源

溢价率计算方式：

```text
溢价率 = 当前价格 / 当前净值 - 1
```

## QQQ / NDX 记录字段

- 跟踪日期
- 标的
- 名称
- 当前点位/价格
- 当天涨幅
- 历史最高收盘点/价（由项目已有记录中的最高收盘值决定）
- 距最高收盘回撤
- 最高收盘日期
- 行情日期
- 数据源

回撤计算方式：

```text
回撤 = 当前点位或价格 / 历史最高收盘点或价 - 1
```

历史最高收盘由项目已有记录自行维护：每次写入新记录时，将当前收盘值与已有历史最高比较，取较大值。不使用盘中最高价。

## 数据源配置

所有行情数据一律通过**腾讯自选股连接器（westock MCP）**获取，不再从 HTTP 行情网站抓取。数据源与跟踪标的统一维护在：

```text
data_sources.json
```

- 活跃源（唯一取数源）：`westock_quote`（行情/收盘）、`westock_etf_detail`（ETF 净值/估值）、`westock_kline`（历史 K 线）。分时走势（`westock_minute`）自 2026-09-08 起不再采集。
- 东方财富、新浪财经、腾讯证券、Nasdaq 官方、Yahoo Finance 等 HTTP 源已停用（`retired`），仅保留供历史记录 `source_ids` 引用和页面数据源表展示，不再作为取数通道。

页面展示用的记录数据单独维护在：

```text
data/manifest.json
data/daily-records/YYYY/MM/YYYY-MM-DD.json
```

HTML 先加载 `manifest.json`，再按索引加载按年月归档的每日 JSON；本地查看时用 HTTP 服务打开，和 GitHub Pages 的运行方式一致。

目录示例：

```text
data/
  manifest.json
  daily-records/
    2026/
      06/
        2026-06-11.json
```

## 使用

当天收盘后记录：

```powershell
python record_nasdaq_etf.py
```

补录指定交易日：

```powershell
python record_nasdaq_etf.py --backfill-date 2026-06-01
```

ETF 价格、涨幅、历史 K 线优先使用腾讯自选股连接器（westock），溢价率通过 `estimate`/净值按 `price / estimate - 1` 计算。不再主动访问东方财富、新浪等 HTTP 行情站（仅作最后兜底）。

刷新并补齐已记录 ETF 交易日对应的 QQQ/NDX 回撤口径：

```powershell
python record_nasdaq_etf.py --refresh-benchmarks
```

只补某个美股行情日的 QQQ/NDX：

```powershell
python record_nasdaq_etf.py --backfill-benchmark-date 2026-06-12
```

补已记录数据中的分钟走势功能已随走势图下线（2026-09-08）停用：

```powershell
python record_nasdaq_etf.py --refresh-trends
```

> 该命令现为 no-op（仅保留参数兼容），不再抓取任何分时/分钟数据。历史记录中已有的 `trend` 原样保留，不做清理。

输出文件：

```text
index.html
assets/app.js
assets/app.css
data/manifest.json
data/daily-records/YYYY/MM/YYYY-MM-DD.json
```

前端使用 React + TypeScript，修改页面后构建：

```powershell
npm run typecheck
npm run build
```

本地查看：

```powershell
python -m http.server 5173
```

然后访问：

```text
http://127.0.0.1:5173/
```

## GitHub Pages

这个项目可以直接用 GitHub Pages 静态托管。

发布前确保这些文件已提交并推送：

```text
index.html
assets/app.js
assets/app.css
data/manifest.json
data/daily-records/
```

GitHub 仓库设置：

```text
Settings -> Pages -> Build and deployment
Source: Deploy from a branch
Branch: main
Folder: / (root)
```

启用后访问：

```text
https://auroka.github.io/nasdaq-etf/
```

## 说明

脚本会按交易日期和代码去重；同一天同一代码重复执行时会更新原记录，不会重复追加。
