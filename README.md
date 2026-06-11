# Nasdaq Tracking Daily Record

纳斯达克 100 指数跟踪工具。记录三只 A 股纳指 ETF 的交易日收盘后数据，同时跟踪 QQQ 和 NDX 距离历史最高收盘点/价的回撤，并生成一个可直接打开查看的 HTML 页面。

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

历史最高点按 Yahoo Finance 日线 close 统计，不使用盘中最高价。

## 数据源配置

接口数据源、ETF 代码和 QQQ/NDX 标的统一维护在：

```text
data_sources.json
```

页面展示用的记录数据单独维护在：

```text
nasdaq_etf_daily_data.js
```

HTML 只负责加载这个数据文件并填充表格，直接双击打开即可查看。

## 使用

当天收盘后记录：

```powershell
python record_nasdaq_etf.py
```

补录指定交易日：

```powershell
python record_nasdaq_etf.py --backfill-date 2026-06-01
```

只刷新已记录的 QQQ/NDX 回撤口径：

```powershell
python record_nasdaq_etf.py --refresh-benchmarks
```

输出文件：

```text
index.html
nasdaq_etf_daily_data.js
```

## 说明

脚本会按交易日期和代码去重；同一天同一代码重复执行时会更新原记录，不会重复追加。
