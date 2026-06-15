# Nasdaq Tracking Daily Record

纳斯达克 100 指数跟踪工具。记录三只 A 股纳指 ETF 的交易日收盘后数据，同时跟踪 QQQ 和 NDX 距离历史最高收盘点/价的回撤，并生成一个可通过本地 HTTP 服务或 GitHub Pages 查看的 HTML 页面。

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
- T-1 估值
- 溢价率
- T-1 估值日
- 数据源

溢价率计算方式：

```text
溢价率 = 当前价格 / T-1 估值 - 1
```

## QQQ / NDX 记录字段

- 跟踪日期
- 标的
- 名称
- 当前点位/价格
- 当天涨幅
- 历史最高收盘点/价
- 距最高收盘回撤
- 最高收盘日期
- 行情日期
- 数据源

回撤计算方式：

```text
回撤 = 当前点位或价格 / 历史最高收盘点或价 - 1
```

历史最高点默认按 Nasdaq 官方历史行情的收盘价统计，不使用盘中最高价；Yahoo Finance 仅作为备用源。

## 数据源配置

接口数据源、ETF 代码和 QQQ/NDX 标的统一维护在：

```text
data_sources.json
```

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

刷新并补齐已记录 ETF 交易日对应的 QQQ/NDX 回撤口径：

```powershell
python record_nasdaq_etf.py --refresh-benchmarks
```

只补某个美股行情日的 QQQ/NDX：

```powershell
python record_nasdaq_etf.py --backfill-benchmark-date 2026-06-12
```

补已记录数据中的分钟走势；东方财富或 Nasdaq 分钟走势不可用时，会用 Yahoo Finance 历史分钟行情兜底：

```powershell
python record_nasdaq_etf.py --refresh-trends
```

如果 Python 客户端被 Yahoo Finance 拦截导致历史分钟走势无法补齐，在当前 PowerShell 会话中执行兜底脚本：

```powershell
& .\scripts\refresh_yahoo_intraday_trends.ps1
```

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
