---
name: nasdaq-data-completion
description: >
  纳指跟踪项目的专用数据记录与补全技能。只要用户在本项目内提到「记录纳指数据」
  「更新纳指数据」「补全/补齐纳指数据」「纳指每日更新」「跑一下纳指」「采集纳指」
  「更新 ETF 溢价」「补 QQQ/NDX」「把缺的纳指数据补上」，或定时任务/自动化要求
  记录当天行情数据，都必须优先使用本技能，不要手工取数或直接编辑 JSON。
  它会自动判断 A 股是否收盘、补齐所有缺失的中国交易日 ETF 记录与美股交易日
  QQQ/NDX 记录，写入后按市场日历做完整性审计。
---

# 纳指数据补全

## 唯一入口

在项目根目录执行（脚本已内置全部取数、校验、写入与审计逻辑）：

```bash
python fetch_nasdaq_data.py --json
```

- 进度信息走 stderr，最终结果是 stdout 上的 JSON。
- 不要手工调用数据源、不要直接编辑 `data/` 下的 JSON。
- 旧的历史脚本已删除；`nasdaq_store.py` 只负责读写数据文件，不含取数逻辑，不要直接调用它取数。

## 脚本自动处理的场景

| 场景 | 行为 |
| --- | --- |
| 中国交易日 15:00 前执行 | 不记录当天 ETF；只补 QQQ/NDX 最近一个已收盘美股交易日 |
| 中国交易日 15:00 后执行 | 记录当天 ETF + 最近一个已收盘美股交易日 |
| 任意多天缺口（周末、长假、客户端长时间未运行） | 一次性补齐全部缺失交易日，不是只补前两天 |
| 非交易日 / 周末执行 | 不产生 ETF 行；只按美股日历补 QQQ/NDX |
| 某天部分标的缺失 | 只补缺失的标的 |
| 已完整 | 不做任何写入，直接返回 `mode: noop` |

写入前提：所有目标日的数据先全部取到并通过交叉校验；任意一天失败则整体不写，避免出现半截数据。

## 读取结果

```json
{
  "ok": true,
  "mode": "write | noop | dry-run | check",
  "plan": {"etf_targets": [], "benchmark_targets": []},
  "written": {"etf_rows": 0, "benchmark_rows": 2},
  "summary": {
    "etf_expected_days": 93, "etf_missing_days": [],
    "us_expected_days": 97, "us_missing_days": []
  },
  "problems": []
}
```

- `ok`：写入后审计是否通过（退出码 0 / 1 与之对应）。
- `summary.etf_missing_days` / `us_missing_days`：仍缺的日期，正常应为空数组。
- `problems`：字段、溢价率复算、历史最高等异常。

## 失败处理

1. 退出码非 0 或 `ok: false`：先原样重跑一次（网络瞬时故障很常见，最多 2 次）。
2. 仍失败：如实报告失败的日期/标的与错误信息，**不要手工填数字、不要绕过校验、不要改脚本参数强行写入**。
3. 只有用户明确要求时才用 `--date YYYY-MM-DD` 强制重录某一天（会覆盖该日已有记录）。

## 其他命令

```bash
python fetch_nasdaq_data.py --check                 # 本地体检，不发网络请求
python fetch_nasdaq_data.py --dry-run               # 只取数校验并预览，不写文件
python fetch_nasdaq_data.py --date 2026-10-15       # 强制重录某个中国交易日
python fetch_nasdaq_data.py --since 2026-09-01      # 限定审计/补全起点
python fetch_nasdaq_data.py --now "2026-10-19 15:30"  # 模拟运行时间（测试用）
```

## 数据口径（复核时用）

- ETF：`estimate(D)` = D 的前一个中国交易日的官方净值（东财 DWJZ）；该日净值尚未公布时用 tinyright T-1 估值或按纳指涨跌推算，并在 `source_ids` 中标注来源。
- ETF：`premium = price / estimate - 1`。
- QQQ/NDX：按 `quote_date`（美股行情日）归档；`track_date` = `quote_date` 之后第一个中国交易日。
- `history_high` = 截至 `quote_date` 的最高收盘价，不使用盘中最高价。
- 涨跌幅、溢价率、回撤在 JSON 中都是小数比例（`0.0325` 表示 +3.25%）。
- 完整性判据：每个中国交易日 3 条 ETF（513100 / 159501 / 159659）；每个美股交易日 2 条基准（QQQ / NDX）。

## 报告给用户

用简洁列表说明：本次写入行数（ETF x 行 / 基准 y 行）、涉及的交易日、审计是否通过；若 `mode: noop` 则说明「已是最新且完整」。结果只在本会话内报告。

## 提交（按需）

默认**不自动提交**。只有用户明确要求提交，或本轮属于无人值守的自动化运行时，才按项目既有约定提交数据文件：

```bash
git add index.html data/manifest.json data/daily-records
git commit -m "Record Nasdaq tracking YYYY-MM-DD"   # 用本次最新记录的交易日
git push origin main
```

`index.html` 没有实际 diff 时不要提交；`assets/`、`src/`、`node_modules/` 与数据更新无关。
