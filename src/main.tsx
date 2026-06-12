import React, { useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";
import type { BenchmarkRecord, EtfRecord, NasdaqTrackingData, Trend } from "./types";

type TabKey = "etfs" | "benchmarks" | "sources";

const data = window.NASDAQ_TRACKING_DATA;

const fmtNumber = (value: number, digits: number) => Number(value).toFixed(digits);
const fmtPct = (value: number) => `${(Number(value) * 100).toFixed(2)}%`;

const orderMap = <T extends object>(items: T[], key: keyof T) =>
  new Map(items.map((item, index) => [String(item[key]), index]));

const sortRows = <T extends object>(
  rows: T[],
  dateKey: keyof T,
  symbolKey: keyof T,
  order: Map<string, number>
) =>
  [...rows].sort((a, b) => {
    const byDate = String(b[dateKey]).localeCompare(String(a[dateKey]));
    if (byDate) return byDate;
    return (order.get(String(a[symbolKey])) ?? 99) - (order.get(String(b[symbolKey])) ?? 99);
  });

const latestRows = <T extends object>(
  records: T[],
  dateKey: keyof T,
  symbolKey: keyof T,
  order: Map<string, number>
) => {
  const latestDate = records[0]?.[dateKey];
  if (!latestDate) return [];
  return records
    .filter((row) => row[dateKey] === latestDate)
    .sort((a, b) => (order.get(String(a[symbolKey])) ?? 99) - (order.get(String(b[symbolKey])) ?? 99));
};

const groupByDate = <T extends object>(rows: T[], dateKey: keyof T) => {
  const groups: Array<{ date: string; rows: T[] }> = [];
  for (const row of rows) {
    const date = String(row[dateKey]);
    const last = groups[groups.length - 1];
    if (last?.date === date) {
      last.rows.push(row);
    } else {
      groups.push({ date, rows: [row] });
    }
  }
  return groups;
};

function TrendSparkline({ trend }: { trend?: Trend | null }) {
  const points = trend?.points?.filter((point) => Number.isFinite(point.value)) ?? [];
  if (points.length < 2) {
    return <span className="trend-empty">暂无走势</span>;
  }

  const width = 132;
  const height = 42;
  const padding = 4;
  const values = points.map((point) => point.value);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min || 1;
  // 把当天价格压缩到一个小 SVG 里，表格里看走势不占空间。
  const d = points
    .map((point, index) => {
      const x = padding + (index / (points.length - 1)) * (width - padding * 2);
      const y = height - padding - ((point.value - min) / span) * (height - padding * 2);
      return `${index === 0 ? "M" : "L"}${x.toFixed(2)} ${y.toFixed(2)}`;
    })
    .join(" ");
  const first = points[0].value;
  const last = points[points.length - 1].value;
  const trendClass = last >= first ? "trend-up" : "trend-down";
  const title = `${trend?.date ?? ""} ${points[0].time} - ${points[points.length - 1].time}`;

  return (
    <div className="trend-cell" title={title}>
      <svg viewBox={`0 0 ${width} ${height}`} aria-label={title} role="img">
        <path className="trend-fill" d={`${d} L${width - padding} ${height - padding} L${padding} ${height - padding} Z`} />
        <path className={trendClass} d={d} />
      </svg>
      <span className="trend-date">{trend?.date}</span>
    </div>
  );
}

function DrawdownItem({ title, code, rows }: { title: string; code: string; rows: Array<[string, string, boolean?]> }) {
  return (
    <div className="drawdown-item">
      <div className="drawdown-title">
        <span>{title}</span>
        <span className="drawdown-code">{code}</span>
      </div>
      {rows.map(([label, value, focus]) => (
        <div className={`drawdown-row${focus ? " drawdown-row-focus" : ""}`} key={label}>
          <span>{label}</span>
          <strong className={focus ? "percent" : ""}>{value}</strong>
        </div>
      ))}
    </div>
  );
}

function EtfDrawdownSummary({ records, order }: { records: EtfRecord[]; order: Map<string, number> }) {
  const latest = latestRows(records, "trade_date", "code", order);
  const items = latest.map((row) => {
    const related = records.filter((item) => item.code === row.code);
    const highRow = related.reduce((best, item) => (Number(item.price) > Number(best.price) ? item : best), related[0]);
    const drawdown = Number(row.price) / Number(highRow.price) - 1;
    return (
      <DrawdownItem
        key={row.code}
        title={row.name}
        code={row.code}
        rows={[
          ["历史最高记录价", `${fmtNumber(highRow.price, 3)} / ${highRow.trade_date}`],
          ["当天更新价", `${fmtNumber(row.price, 3)} / ${row.trade_date}`],
          ["回撤", fmtPct(drawdown), true]
        ]}
      />
    );
  });
  return <div className="drawdown-grid">{items.length ? items : <div className="drawdown-item">暂无回撤数据</div>}</div>;
}

function BenchmarkDrawdownSummary({ records, order }: { records: BenchmarkRecord[]; order: Map<string, number> }) {
  const latest = latestRows(records, "track_date", "symbol", order);
  const items = latest.map((row) => (
    <DrawdownItem
      key={row.symbol}
      title={row.name}
      code={row.symbol}
      rows={[
        ["历史最高收盘", `${fmtNumber(row.history_high, 2)} / ${row.history_high_date}`],
        ["当天更新点", `${fmtNumber(row.value, 2)} / ${row.quote_date}`],
        ["回撤", fmtPct(row.drawdown), true]
      ]}
    />
  ));
  return <div className="drawdown-grid">{items.length ? items : <div className="drawdown-item">暂无回撤数据</div>}</div>;
}

function EtfTable({ records }: { records: EtfRecord[] }) {
  const groups = groupByDate(records, "trade_date");
  return (
    <table>
      <thead>
        <tr>
          <th>交易日期</th>
          <th>代码</th>
          <th>名称</th>
          <th>当前价格</th>
          <th>当天涨幅</th>
          <th>T-1估值</th>
          <th>溢价率</th>
          <th>T-1估值日</th>
          <th>走势</th>
        </tr>
      </thead>
      <tbody>
        {groups.length ? (
          groups.flatMap(({ date, rows }) =>
            rows.map((row, index) => (
              <tr key={`${row.trade_date}-${row.code}`}>
                {index === 0 && (
                  <td className="date-cell" rowSpan={rows.length}>
                    {date}
                  </td>
                )}
                <td className="mono">{row.code}</td>
                <td>{row.name}</td>
                <td className="num">{fmtNumber(row.price, 3)}</td>
                <td className="num percent">{fmtPct(row.daily_change)}</td>
                <td className="num">{fmtNumber(row.estimate, 4)}</td>
                <td className="num percent">{fmtPct(row.premium)}</td>
                <td>{row.estimate_time}</td>
                <td><TrendSparkline trend={row.trend} /></td>
              </tr>
            ))
          )
        ) : (
          <tr className="empty"><td colSpan={9}>暂无记录</td></tr>
        )}
      </tbody>
    </table>
  );
}

function BenchmarkTable({ records }: { records: BenchmarkRecord[] }) {
  const groups = groupByDate(records, "track_date");
  return (
    <table>
      <thead>
        <tr>
          <th>跟踪日期</th>
          <th>标的</th>
          <th>名称</th>
          <th>当前点位/价格</th>
          <th>当天涨幅</th>
          <th>行情日期</th>
          <th>走势</th>
        </tr>
      </thead>
      <tbody>
        {groups.length ? (
          groups.flatMap(({ date, rows }) =>
            rows.map((row, index) => (
              <tr key={`${row.track_date}-${row.symbol}`}>
                {index === 0 && (
                  <td className="date-cell" rowSpan={rows.length}>
                    {date}
                  </td>
                )}
                <td className="mono">{row.symbol}</td>
                <td>{row.name}</td>
                <td className="num">{fmtNumber(row.value, 2)}</td>
                <td className="num percent">{fmtPct(row.daily_change)}</td>
                <td>{row.quote_date}</td>
                <td><TrendSparkline trend={row.trend} /></td>
              </tr>
            ))
          )
        ) : (
          <tr className="empty"><td colSpan={7}>暂无记录</td></tr>
        )}
      </tbody>
    </table>
  );
}

function SourceTable({ appData }: { appData: NasdaqTrackingData }) {
  return (
    <table>
      <thead>
        <tr>
          <th>数据源</th>
          <th>用途</th>
          <th>接口</th>
        </tr>
      </thead>
      <tbody>
        {appData.sources.length ? (
          appData.sources.map((source) => (
            <tr key={source.id}>
              <td>{source.name}</td>
              <td>{source.purpose}</td>
              <td className="source-url">{source.url_template || source.url || "-"}</td>
            </tr>
          ))
        ) : (
          <tr className="empty"><td colSpan={3}>暂无数据源</td></tr>
        )}
      </tbody>
    </table>
  );
}

function App({ appData }: { appData: NasdaqTrackingData }) {
  const [activeTab, setActiveTab] = useState<TabKey>("etfs");
  const etfOrder = useMemo(() => orderMap(appData.etfs, "code"), [appData.etfs]);
  const benchmarkOrder = useMemo(() => orderMap(appData.benchmarks, "symbol"), [appData.benchmarks]);
  const etfRecords = useMemo(() => sortRows(appData.etf_records, "trade_date", "code", etfOrder), [appData.etf_records, etfOrder]);
  const benchmarkRecords = useMemo(
    () => sortRows(appData.benchmark_records, "track_date", "symbol", benchmarkOrder),
    [appData.benchmark_records, benchmarkOrder]
  );
  const latestDate = [...etfRecords.map((row) => row.trade_date), ...benchmarkRecords.map((row) => row.track_date)].sort().pop() ?? "-";
  const latestUpdate = [...etfRecords, ...benchmarkRecords]
    .map((row) => row.recorded_at)
    .filter(Boolean)
    .sort()
    .pop() ?? appData.generated_at;

  return (
    <main>
      <header className="top">
        <div>
          <h1>纳指跟踪记录</h1>
          <div className="meta">
            <span className="pill">最新日期：{latestDate}</span>
            <span className="pill">最近更新：{latestUpdate}</span>
          </div>
        </div>
      </header>

      <nav className="tabs" aria-label="数据表切换">
        <button className={`tab-button${activeTab === "etfs" ? " active" : ""}`} type="button" onClick={() => setActiveTab("etfs")}>ETF每日记录</button>
        <button className={`tab-button${activeTab === "benchmarks" ? " active" : ""}`} type="button" onClick={() => setActiveTab("benchmarks")}>QQQ/NDX每日记录</button>
        <button className={`tab-button${activeTab === "sources" ? " active" : ""}`} type="button" onClick={() => setActiveTab("sources")}>数据源</button>
      </nav>

      {activeTab === "etfs" && (
        <section className="section-block">
          <EtfDrawdownSummary records={etfRecords} order={etfOrder} />
          <div className="table-wrap">
            <EtfTable records={etfRecords} />
          </div>
        </section>
      )}

      {activeTab === "benchmarks" && (
        <section className="section-block">
          <BenchmarkDrawdownSummary records={benchmarkRecords} order={benchmarkOrder} />
          <div className="table-wrap">
            <BenchmarkTable records={benchmarkRecords} />
          </div>
          <p className="note">QQQ/NDX 摘要默认按 Nasdaq 官方历史行情统计；Yahoo Finance 日线行情仅作为备用源。回撤 = 当前点位或价格 / 历史最高收盘点或价 - 1。</p>
        </section>
      )}

      {activeTab === "sources" && (
        <section className="section-block">
          <div className="table-wrap compact">
            <SourceTable appData={appData} />
          </div>
        </section>
      )}
    </main>
  );
}

const root = document.getElementById("root");

if (root) {
  createRoot(root).render(
    data ? (
      <App appData={data} />
    ) : (
      <main>
        <div className="error">未加载到 nasdaq_etf_daily_data.js，请确认该文件和 HTML 在同一目录。</div>
      </main>
    )
  );
}
