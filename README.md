# Nasdaq ETF Daily Record

记录三只纳指 ETF 的交易日收盘后数据，并生成一个可直接打开查看的 HTML 表格。

## 记录对象

- `513100`
- `159501`
- `159659`

## 记录字段

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

## 使用

当天收盘后记录：

```powershell
python record_nasdaq_etf.py
```

补录指定交易日：

```powershell
python record_nasdaq_etf.py --backfill-date 2026-06-01
```

输出文件：

```text
nasdaq_etf_daily_record.html
```

## 说明

脚本会按交易日期和代码去重；同一天同一代码重复执行时会更新原记录，不会重复追加。
