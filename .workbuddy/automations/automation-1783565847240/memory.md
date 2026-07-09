# 纳指ETF每日数据更新 — 执行历史

## 2026-07-09 15:28
- **状态**: 成功
- **采集结果**: 3 ETF rows + 2 benchmark rows
- **ETF 数据**:
  - 513100 (纳指ETF国泰): price=2.166, +1.17%, premium=9.04%
  - 159501 (纳指ETF嘉实): price=2.049, +0.79%, premium=9.84%
  - 159659 (纳斯达克100ETF招商): price=2.293, +1.10%, premium=6.93%
- **溢价率验证**: 三只全部通过 price/estimate-1 复算
- **Git**: commit c68fd48, push origin main 成功
- **修复**: data_sources.json 缺失 tinyright_t1/tinyright_iopv/tinyright_table/eastmoney_fund_nav/user_provided_t1 源，已从 git 历史恢复（未在此次提交中）
- **注意**: CLAUDE.md、src/、assets/、docs/ 等有未提交改动，需手动处理
