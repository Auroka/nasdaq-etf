export type Source = {
  id: string;
  name: string;
  purpose: string;
  url?: string;
  url_template?: string;
};

export type Etf = {
  code: string;
  name: string;
};

export type Benchmark = {
  symbol: string;
  name: string;
  yahoo_symbol: string;
  nasdaq_symbol?: string;
  nasdaq_assetclass?: string;
  unit: string;
};

export type TrendPoint = {
  time: string;
  value: number;
};

export type Trend = {
  date: string;
  source_ids: string[];
  points: TrendPoint[];
};

export type EtfRecord = {
  trade_date: string;
  recorded_at: string;
  code: string;
  name: string;
  price: number;
  daily_change: number;
  estimate: number;
  premium: number;
  quote_time?: string;
  estimate_time: string;
  source_ids: string[];
  trend?: Trend | null;
};

export type BenchmarkRecord = {
  track_date: string;
  recorded_at: string;
  symbol: string;
  name: string;
  value: number;
  daily_change: number;
  history_high: number;
  drawdown: number;
  history_high_date: string;
  quote_date: string;
  unit: string;
  source_ids: string[];
  trend?: Trend | null;
};

export type NasdaqTrackingData = {
  generated_at: string;
  etfs: Etf[];
  benchmarks: Benchmark[];
  sources: Source[];
  etf_records: EtfRecord[];
  benchmark_records: BenchmarkRecord[];
};

declare global {
  interface Window {
    NASDAQ_TRACKING_DATA?: NasdaqTrackingData;
  }
}
