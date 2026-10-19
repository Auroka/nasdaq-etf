# Nasdaq Tracking Daily Record

纳斯达克 100 指数跟踪工具。记录三只 A 股纳指 ETF 的交易日收盘后数据，同时跟踪 QQQ 和 NDX 距离历史最高收盘点/价的回撤，并生成一个可通过本地 HTTP 服务或 GitHub Pages 查看的 HTML 页面。

完整的项目架构、数据口径、日常更新、历史补录、自动任务和故障排查说明见 [项目交接文档](docs/HANDOFF.md)。

> **走势图已下线（2026-09-08）**：页面不再展示分时走势，采集流程不再获取分钟数据；历史记录中已有的 `trend` 字段原样保留但不使用。相关分时命令已随旧脚本删除。

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
- 当前净值（最近一个中国交易日的官方净值，来自东财基金净值 DWJZ）
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

所有行情数据由 `fetch_nasdaq_data.py` 获取，每个关键数值都做双源交叉校验。数据源与跟踪标的统一维护在：

```text
data_sources.json
```

| 数据 | 主源 | 校验 / 兜底 |
| --- | --- | --- |
| ETF 收盘价、日涨幅 | 新浪日 K | 腾讯日 K；不一致时用东财 K 线仲裁 |
| ETF 净值（estimate） | 东财官方净值（DWJZ） | tinyright IOPV → tinyright T-1 → 纳指涨跌推算 |
| QQQ / NDX 收盘、涨幅、历史最高 | Nasdaq 官方历史行情 | 新浪美股日 K（NDX 使用 `.NDX`） |

走势图已于 2026-09-08 下线，分时数据源全部停用。

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

自动补齐所有未记录的交易日（推荐，脚本会判断是否收盘）：

```powershell
python fetch_nasdaq_data.py
```

```text
- 中国交易日 15:00 前执行：不记录当天 ETF，只补 QQQ/NDX 最近一个已收盘美股交易日
- 中国交易日 15:00 后执行：记录当天 ETF + 最近一个已收盘美股交易日
- 任意多天缺口（周末、长假、长时间未运行）：一次性补齐
- 写入前取齐所有目标日并交叉校验，任一失败则整体不写
- 写入后按中国/美国交易日历审计，缺一天即报失败
```

其他命令：

```powershell
python fetch_nasdaq_data.py --dry-run             # 预览，不写文件
python fetch_nasdaq_data.py --check               # 本地体检，不发网络请求
python fetch_nasdaq_data.py --date 2026-10-15     # 强制重录某个中国交易日
python fetch_nasdaq_data.py --since 2026-09-01    # 限定审计/补全起点
python fetch_nasdaq_data.py --json                # 机器可读结果
```

溢价率计算方式：

```text
溢价率 = 收盘价 / 当前净值 - 1
```

取数统一由 `fetch_nasdaq_data.py` 完成；`nasdaq_store.py` 只负责读写数据文件。旧的历史采集脚本已删除。

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
