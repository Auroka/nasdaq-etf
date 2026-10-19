# nasdaq-etf 项目规则

## 用途
- 记录 `513100`、`159501`、`159659` 三只纳指 ETF 的交易日收盘后价格、当天涨幅和溢价率。
- 记录 QQQ 和 NDX 的当前点位/价格、当天涨幅、历史最高收盘点/价和距离最高收盘的回撤。
- 输出文件是 `index.html`、`assets/app.js`、`assets/app.css`、`data/manifest.json` 和 `data/daily-records/YYYY/MM/YYYY-MM-DD.json`；通过本地 HTTP 服务或 GitHub Pages 查看 ETF 溢价表、QQQ/NDX 回撤表和数据源表。

## 走势图已下线（2026-09-08 用户决定）
- 页面不再渲染「走势」列（分时迷你图），采集与回填流程**不再抓取任何分时/分钟数据（trend）**。
- 历史每日 JSON 中已存在的 `trend` 字段原样保留（数据无损、不主动清理），但不再校验、不再使用。
- 新写入的记录 `trend` 均为 `null`；旧脚本中的 `--refresh-trends` 等命令已随脚本一并删除。
- 早盘停牌导致的分时缺口等知识不再作为数据操作依据。

## 文件约定
- `data_sources.json`：项目唯一的数据源和跟踪标的配置入口；新增或调整接口、代码、标的时先改这里。
- `fetch_nasdaq_data.py`：**当前唯一取数入口**。自动判断收盘状态、补齐所有缺失交易日、多源交叉校验、写后审计。
- `nasdaq_store.py`：数据存储层（读每日记录、写 JSON / manifest / 页面壳），不含任何取数逻辑。
- `.workbuddy/skills/nasdaq-data-completion/SKILL.md`：项目级 skill，「记录/补全纳指数据」任务优先使用。
- `data/manifest.json`：页面数据索引；只放生成时间、跟踪标的、数据源和每日文件引用。
- `data/daily-records/YYYY/MM/YYYY-MM-DD.json`：按交易日期和年月目录拆分的每日记录；ETF 使用 `trade_date` 归档，QQQ/NDX 使用 `quote_date` 归档；相同日期和代码/标的重复运行时更新原行。
- `src/`：React + TypeScript 前端源码；表格、tab、回撤摘要都在这里维护。
- `assets/`：前端构建产物，`index.html` 直接加载这里的 `app.js` 和 `app.css`。
- `index.html`：React 页面壳；从 `data/manifest.json` 加载索引，再按索引读取每日记录并挂载前端应用。
- `docs/HANDOFF.md`：完整项目交接文档；架构、数据口径、更新流程、自动任务和故障处理以这里的当前内容为准。
- 不提交缓存、虚拟环境、密钥或本地临时文件。

## 维护规范
- 代码保持简洁、直观，优先沿用现有函数和数据结构；复杂逻辑要写少量说明原因的注释。
- 目录结构必须清晰：配置放根目录，采集脚本放根目录，页面源码放 `src/`，构建产物放 `assets/`，数据索引和每日记录放 `data/`。
- 说明文档保持简洁清晰，只写当前真实可用的命令、路径和数据口径；代码、目录、数据源、自动任务或操作流程调整后同步更新 `README.md`、本文件和 `docs/HANDOFF.md`。
- 文件命名要能直接表达用途；多余的缓存、日志、旧数据文件和临时文件要删除，不能因为"也许有用"长期保留。
- 数据文件只保留一种正式入口：`data/manifest.json` 加 `data/daily-records/YYYY/MM/YYYY-MM-DD.json`；旧的单文件数据结构只允许作为脚本兼容读取来源，不再提交。

## 数据获取规则（2026-10-19 更新）

**日常取数一律使用 `fetch_nasdaq_data.py`，并通过项目 skill `nasdaq-data-completion` 触发。**

- 背景：早期依赖的第三方行情连接器自 2026-09 起长期不可用，继续依赖会导致每天都需要人工兜底。2026-10-19 起改为 HTTP 多源交叉校验，仍满足「准确 + 完整」两条硬要求。不要再引入任何 MCP 行情连接器作为取数路径。
- 唯一取数入口：`python fetch_nasdaq_data.py`（自动判断是否收盘、补齐所有缺失交易日、写入后按市场日历审计）。
- 数据源（完整配置见 `data_sources.json`）：

| 数据 | 主源 | 校验/兜底 |
| --- | --- | --- |
| ETF 收盘价、日涨幅 | 新浪日 K `quotes.sina.cn` | 腾讯日 K `web.ifzq.gtimg.cn`；两者不一致时用东财 K 线仲裁 |
| ETF 净值（estimate） | 东财官方净值 `api.fund.eastmoney.com/f10/lsjz`（DWJZ） | tinyright IOPV → tinyright T-1 → 纳指涨跌推算 |
| QQQ/NDX 收盘、涨幅、历史最高 | Nasdaq 官方 `api.nasdaq.com/api/quote/.../historical` | 新浪美股日 K（NDX 必须用 `.NDX`） |

规则要点：
- 任一关键数值必须两源一致；不一致且无法仲裁时**整体终止，不写入任何数据**。
- 写入前必须取齐所有目标日；写入后按中国/美国交易日历审计，缺一天即视为失败。
- 溢价率 = `price / estimate - 1`，必须复算校验与 premium 字段一致。
- 旧的 `record_nasdaq_etf.py` 已删除，不存在任何历史取数入口，请勿再引用。

### Skill
`.workbuddy/skills/nasdaq-data-completion/SKILL.md`：本项目所有「记录 / 更新 / 补全纳指数据」的任务优先使用该 skill，不要手工取数或直接改 JSON。

### 历史补录与回填

```text
python fetch_nasdaq_data.py                # 自动补齐（推荐）
python fetch_nasdaq_data.py --dry-run      # 预览
python fetch_nasdaq_data.py --check        # 本地体检（无网络）
python fetch_nasdaq_data.py --date YYYY-MM-DD  # 强制重录某天
```

### QQQ/NDX 日线与回撤
历史最高收盘由「Nasdaq 全历史收盘序列 ∪ 新浪美股全历史收盘序列」取截至 `quote_date` 的最大值，不使用盘中最高价。

## 执行约定
- 默认使用 UTF-8。
- **取数主路径**：`python fetch_nasdaq_data.py`（自动补齐 + 写后审计），或通过 skill `nasdaq-data-completion` 触发；不要先逐站手工探测数据源。
- 脚本会自行判断「A 股是否收盘」：15:00 前不记当天 ETF，只补 QQQ/NDX；非交易日不产生 ETF 行。
- 补录某天使用 `python fetch_nasdaq_data.py --date YYYY-MM-DD`（会覆盖该日记录）。
- 修改脚本后至少运行 `python -m py_compile fetch_nasdaq_data.py`，并用 `--dry-run` 验证真实取数。
- 修改前端后运行 `npm run typecheck` 和 `npm run build`。
- 本地查看使用 `python -m http.server 5173`，访问 `http://127.0.0.1:5173/`。
