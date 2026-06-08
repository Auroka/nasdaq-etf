window.NASDAQ_TRACKING_DATA = {
  "generated_at": "2026-06-08 16:28:42",
  "etfs": [
    {
      "code": "513100",
      "name": "纳指ETF国泰"
    },
    {
      "code": "159501",
      "name": "纳指ETF嘉实"
    },
    {
      "code": "159659",
      "name": "纳斯达克100ETF招商"
    }
  ],
  "benchmarks": [
    {
      "symbol": "QQQ",
      "name": "Invesco QQQ Trust",
      "yahoo_symbol": "QQQ",
      "unit": "USD"
    },
    {
      "symbol": "NDX",
      "name": "Nasdaq 100 Index",
      "yahoo_symbol": "^NDX",
      "unit": "points"
    }
  ],
  "sources": [
    {
      "id": "eastmoney_quote",
      "name": "东方财富实时行情",
      "purpose": "A股纳指 ETF 当前价格、当天涨幅和行情日期",
      "url_template": "https://push2.eastmoney.com/api/qt/ulist.np/get?fltt=2&fields=f12,f14,f2,f3,f13,f124&secids={secids}"
    },
    {
      "id": "eastmoney_kline",
      "name": "东方财富历史 K 线",
      "purpose": "A股纳指 ETF 补录日期的收盘价和当天涨幅",
      "url_template": "https://push2his.eastmoney.com/api/qt/stock/kline/get?secid={secid}&fields1=f1,f2,f3,f4,f5,f6&fields2=f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61&klt=101&fqt=1&beg={date}&end={date}"
    },
    {
      "id": "tinyright_t1",
      "name": "估值日记 T-1 估值",
      "purpose": "A股纳指 ETF T-1 估值和估值日",
      "url": "https://n.tinyright.com/"
    },
    {
      "id": "tinyright_table",
      "name": "估值日记表格行情",
      "purpose": "东方财富不可用时的 A股纳指 ETF 价格和涨幅兜底",
      "url": "https://n.tinyright.com/"
    },
    {
      "id": "yahoo_chart",
      "name": "Yahoo Finance 日线行情",
      "purpose": "QQQ 和 NDX 当前点位、当天涨幅、历史最高收盘点/价和回撤",
      "url_template": "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=30y&interval=1d&includePrePost=false&events=history"
    },
    {
      "id": "manual_historical_quote",
      "name": "人工保留的历史行情",
      "purpose": "已补录记录中的历史收盘价",
      "url": ""
    },
    {
      "id": "user_provided_t1",
      "name": "用户提供的 T-1 估值",
      "purpose": "已人工校正记录中的 T-1 估值",
      "url": ""
    }
  ],
  "etf_records": [
    {
      "trade_date": "2026-06-08",
      "recorded_at": "2026-06-08 15:21:17",
      "code": "513100",
      "name": "纳指ETF国泰",
      "price": 2.114,
      "daily_change": -0.041299999999999996,
      "estimate": 1.9706,
      "premium": 0.0728,
      "quote_time": "2026-06-08 15:21:16",
      "estimate_time": "2026-06-05",
      "source_ids": [
        "eastmoney_quote",
        "tinyright_t1"
      ]
    },
    {
      "trade_date": "2026-06-08",
      "recorded_at": "2026-06-08 15:21:17",
      "code": "159501",
      "name": "纳指ETF嘉实",
      "price": 2.016,
      "daily_change": -0.034,
      "estimate": 1.8498,
      "premium": 0.0898,
      "quote_time": "2026-06-08 15:20:33",
      "estimate_time": "2026-06-05",
      "source_ids": [
        "eastmoney_quote",
        "tinyright_t1"
      ]
    },
    {
      "trade_date": "2026-06-08",
      "recorded_at": "2026-06-08 15:21:17",
      "code": "159659",
      "name": "纳斯达克100ETF招商",
      "price": 2.233,
      "daily_change": -0.0383,
      "estimate": 2.1213,
      "premium": 0.0527,
      "quote_time": "2026-06-08 15:20:30",
      "estimate_time": "2026-06-05",
      "source_ids": [
        "eastmoney_quote",
        "tinyright_t1"
      ]
    },
    {
      "trade_date": "2026-06-05",
      "recorded_at": "2026-06-05 18:46:03",
      "code": "513100",
      "name": "国泰纳指100",
      "price": 2.205,
      "daily_change": -0.015600000000000001,
      "estimate": 2.0703,
      "premium": 0.06509999999999999,
      "quote_time": "2026-06-05 15:00:00",
      "estimate_time": "2026-06-04",
      "source_ids": [
        "tinyright_table",
        "tinyright_t1"
      ]
    },
    {
      "trade_date": "2026-06-05",
      "recorded_at": "2026-06-05 18:46:03",
      "code": "159501",
      "name": "嘉实纳指100",
      "price": 2.087,
      "daily_change": -0.0095,
      "estimate": 1.9434,
      "premium": 0.0739,
      "quote_time": "2026-06-05 15:00:00",
      "estimate_time": "2026-06-04",
      "source_ids": [
        "tinyright_table",
        "tinyright_t1"
      ]
    },
    {
      "trade_date": "2026-06-05",
      "recorded_at": "2026-06-05 18:46:03",
      "code": "159659",
      "name": "招商纳指100",
      "price": 2.322,
      "daily_change": -0.013600000000000001,
      "estimate": 2.2286,
      "premium": 0.04190000000000001,
      "quote_time": "2026-06-05 15:00:00",
      "estimate_time": "2026-06-04",
      "source_ids": [
        "tinyright_table",
        "tinyright_t1"
      ]
    },
    {
      "trade_date": "2026-06-04",
      "recorded_at": "2026-06-04 16:28:04",
      "code": "513100",
      "name": "纳指ETF国泰",
      "price": 2.24,
      "daily_change": -0.025699999999999997,
      "estimate": 2.0808,
      "premium": 0.0765,
      "quote_time": "2026-06-04 16:12:02",
      "estimate_time": "2026-06-03",
      "source_ids": [
        "eastmoney_quote",
        "tinyright_t1"
      ]
    },
    {
      "trade_date": "2026-06-04",
      "recorded_at": "2026-06-04 16:28:04",
      "code": "159501",
      "name": "纳指ETF嘉实",
      "price": 2.107,
      "daily_change": -0.021400000000000002,
      "estimate": 1.9533,
      "premium": 0.0787,
      "quote_time": "2026-06-04 15:34:09",
      "estimate_time": "2026-06-03",
      "source_ids": [
        "eastmoney_quote",
        "tinyright_t1"
      ]
    },
    {
      "trade_date": "2026-06-04",
      "recorded_at": "2026-06-04 16:28:04",
      "code": "159659",
      "name": "纳斯达克100ETF招商",
      "price": 2.354,
      "daily_change": -0.0216,
      "estimate": 2.24,
      "premium": 0.0509,
      "quote_time": "2026-06-04 15:34:30",
      "estimate_time": "2026-06-03",
      "source_ids": [
        "eastmoney_quote",
        "tinyright_t1"
      ]
    },
    {
      "trade_date": "2026-06-03",
      "recorded_at": "2026-06-03 16:05:49",
      "code": "513100",
      "name": "纳指ETF国泰",
      "price": 2.299,
      "daily_change": -0.018799999999999997,
      "estimate": 2.087,
      "premium": 0.1016,
      "quote_time": "2026-06-03 16:05:41",
      "estimate_time": "2026-06-02",
      "source_ids": [
        "eastmoney_quote",
        "tinyright_t1"
      ]
    },
    {
      "trade_date": "2026-06-03",
      "recorded_at": "2026-06-03 16:05:49",
      "code": "159501",
      "name": "纳指ETF嘉实",
      "price": 2.153,
      "daily_change": -0.0146,
      "estimate": 1.9591,
      "premium": 0.0989,
      "quote_time": "2026-06-03 15:34:00",
      "estimate_time": "2026-06-02",
      "source_ids": [
        "eastmoney_quote",
        "tinyright_t1"
      ]
    },
    {
      "trade_date": "2026-06-03",
      "recorded_at": "2026-06-03 16:05:49",
      "code": "159659",
      "name": "纳斯达克100ETF招商",
      "price": 2.406,
      "daily_change": -0.0143,
      "estimate": 2.2466,
      "premium": 0.0709,
      "quote_time": "2026-06-03 15:34:30",
      "estimate_time": "2026-06-02",
      "source_ids": [
        "eastmoney_quote",
        "tinyright_t1"
      ]
    },
    {
      "trade_date": "2026-06-02",
      "recorded_at": "2026-06-02 16:53:08",
      "code": "513100",
      "name": "国泰纳指100",
      "price": 2.343,
      "daily_change": -0.009300000000000001,
      "estimate": 2.0766,
      "premium": 0.1283,
      "quote_time": "2026-06-02 14:59:00",
      "estimate_time": "2026-06-01",
      "source_ids": [
        "tinyright_table",
        "tinyright_t1"
      ]
    },
    {
      "trade_date": "2026-06-02",
      "recorded_at": "2026-06-02 16:53:08",
      "code": "159501",
      "name": "嘉实纳指100",
      "price": 2.185,
      "daily_change": -0.0068000000000000005,
      "estimate": 1.9494,
      "premium": 0.1209,
      "quote_time": "2026-06-02 14:59:00",
      "estimate_time": "2026-06-01",
      "source_ids": [
        "tinyright_table",
        "tinyright_t1"
      ]
    },
    {
      "trade_date": "2026-06-02",
      "recorded_at": "2026-06-02 16:53:08",
      "code": "159659",
      "name": "招商纳指100",
      "price": 2.441,
      "daily_change": -0.013300000000000001,
      "estimate": 2.2353,
      "premium": 0.092,
      "quote_time": "2026-06-02 14:59:00",
      "estimate_time": "2026-06-01",
      "source_ids": [
        "tinyright_table",
        "tinyright_t1"
      ]
    },
    {
      "trade_date": "2026-06-01",
      "recorded_at": "2026-06-02 17:11:05",
      "code": "513100",
      "name": "纳指ETF国泰",
      "price": 2.365,
      "daily_change": 0.0405,
      "estimate": 2.0767,
      "premium": 0.13882602205422057,
      "quote_time": "2026-06-01 15:00:00",
      "estimate_time": "2026-06-01",
      "source_ids": [
        "manual_historical_quote",
        "user_provided_t1"
      ]
    },
    {
      "trade_date": "2026-06-01",
      "recorded_at": "2026-06-02 17:11:05",
      "code": "159501",
      "name": "纳指ETF嘉实",
      "price": 2.2,
      "daily_change": 0.0368,
      "estimate": 1.9494,
      "premium": 0.12855237508977124,
      "quote_time": "2026-06-01 15:00:00",
      "estimate_time": "2026-06-01",
      "source_ids": [
        "manual_historical_quote",
        "user_provided_t1"
      ]
    },
    {
      "trade_date": "2026-06-01",
      "recorded_at": "2026-06-02 16:55:21",
      "code": "159659",
      "name": "纳斯达克100ETF招商",
      "price": 2.474,
      "daily_change": 0.038599999999999995,
      "estimate": 2.2353427658335216,
      "premium": 0.1067653864160234,
      "quote_time": "2026-06-01 15:00:00",
      "estimate_time": "2026-06-01",
      "source_ids": [
        "manual_historical_quote",
        "tinyright_t1"
      ]
    }
  ],
  "benchmark_records": [
    {
      "track_date": "2026-06-08",
      "recorded_at": "2026-06-08 15:32:28",
      "symbol": "QQQ",
      "name": "Invesco QQQ Trust",
      "value": 705.0599975585938,
      "daily_change": -0.04800095663859216,
      "history_high": 746.1599731445312,
      "drawdown": -0.055081989204983084,
      "history_high_date": "2026-06-02",
      "quote_date": "2026-06-05",
      "unit": "USD",
      "source_ids": [
        "yahoo_chart"
      ]
    },
    {
      "track_date": "2026-06-08",
      "recorded_at": "2026-06-08 15:32:28",
      "symbol": "NDX",
      "name": "Nasdaq 100 Index",
      "value": 28957.599609375,
      "daily_change": -0.04769205383151265,
      "history_high": 30660.599609375,
      "drawdown": -0.055543597375678155,
      "history_high_date": "2026-06-02",
      "quote_date": "2026-06-05",
      "unit": "points",
      "source_ids": [
        "yahoo_chart"
      ]
    },
    {
      "track_date": "2026-06-05",
      "recorded_at": "2026-06-08 15:32:28",
      "symbol": "QQQ",
      "name": "Invesco QQQ Trust",
      "value": 740.6099853515625,
      "daily_change": -0.00483739336316813,
      "history_high": 746.1599731445312,
      "drawdown": -0.007438066892786477,
      "history_high_date": "2026-06-02",
      "quote_date": "2026-06-04",
      "unit": "USD",
      "source_ids": [
        "yahoo_chart"
      ]
    },
    {
      "track_date": "2026-06-05",
      "recorded_at": "2026-06-08 15:32:28",
      "symbol": "NDX",
      "name": "Nasdaq 100 Index",
      "value": 30407.810546875,
      "daily_change": -0.005345863833036035,
      "history_high": 30660.599609375,
      "drawdown": -0.008244752735452221,
      "history_high_date": "2026-06-02",
      "quote_date": "2026-06-04",
      "unit": "points",
      "source_ids": [
        "yahoo_chart"
      ]
    }
  ]
};
