window.NASDAQ_TRACKING_DATA = {
  "generated_at": "2026-06-12 09:48:27",
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
      "nasdaq_symbol": "QQQ",
      "nasdaq_assetclass": "etf",
      "unit": "USD"
    },
    {
      "symbol": "NDX",
      "name": "Nasdaq 100 Index",
      "yahoo_symbol": "^NDX",
      "nasdaq_symbol": "NDX",
      "nasdaq_assetclass": "index",
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
      "id": "eastmoney_trend",
      "name": "东方财富分钟走势",
      "purpose": "A股纳指 ETF 当天分钟走势折线图",
      "url_template": "https://push2his.eastmoney.com/api/qt/stock/trends2/get?secid={secid}&fields1=f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f11&fields2=f51,f52,f53,f54,f55,f56,f57,f58&iscr=0&iscca=0&ndays=1"
    },
    {
      "id": "tinyright_t1",
      "name": "估值日记 T-1 估值",
      "purpose": "A股纳指 ETF T-1 估值和估值日",
      "url": "https://n.tinyright.com/"
    },
    {
      "id": "tinyright_iopv",
      "name": "估值日记 IOPV 估值",
      "purpose": "补录缺失日期时，用估值日匹配的 IOPV 估值对齐历史日期",
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
      "purpose": "Nasdaq 官方 API 不可用时，作为 QQQ 和 NDX 日线行情备用源",
      "url_template": "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=30y&interval=1d&includePrePost=false&events=history"
    },
    {
      "id": "nasdaq_api_historical",
      "name": "Nasdaq 官方历史行情",
      "purpose": "默认获取 QQQ 和 NDX 的目标日收盘价、当天涨幅、历史最高收盘点/价和回撤",
      "url_template": "https://api.nasdaq.com/api/quote/{symbol}/historical?assetclass={assetclass}&fromdate={fromdate}&todate={todate}&limit=30"
    },
    {
      "id": "nasdaq_api_chart",
      "name": "Nasdaq 官方分钟走势",
      "purpose": "QQQ 和 NDX 当天分钟走势折线图；历史接口目标日缺失时补最新价",
      "url_template": "https://api.nasdaq.com/api/quote/{symbol}/chart?assetclass={assetclass}"
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
      "trade_date": "2026-06-11",
      "recorded_at": "2026-06-11 15:16:10",
      "code": "513100",
      "name": "纳指ETF国泰",
      "price": 2.13,
      "daily_change": -0.0060999999999999995,
      "estimate": 1.9393,
      "premium": 0.0983,
      "quote_time": "2026-06-11 15:16:12",
      "estimate_time": "2026-06-10",
      "source_ids": [
        "eastmoney_quote",
        "tinyright_t1"
      ],
      "trend": null
    },
    {
      "trade_date": "2026-06-11",
      "recorded_at": "2026-06-11 15:16:10",
      "code": "159501",
      "name": "纳指ETF嘉实",
      "price": 2.01,
      "daily_change": -0.0045000000000000005,
      "estimate": 1.8205,
      "premium": 0.1041,
      "quote_time": "2026-06-11 15:16:03",
      "estimate_time": "2026-06-10",
      "source_ids": [
        "eastmoney_quote",
        "tinyright_t1"
      ],
      "trend": null
    },
    {
      "trade_date": "2026-06-11",
      "recorded_at": "2026-06-11 15:16:10",
      "code": "159659",
      "name": "纳斯达克100ETF招商",
      "price": 2.236,
      "daily_change": -0.009300000000000001,
      "estimate": 2.0878,
      "premium": 0.071,
      "quote_time": "2026-06-11 15:15:36",
      "estimate_time": "2026-06-10",
      "source_ids": [
        "eastmoney_quote",
        "tinyright_t1"
      ],
      "trend": null
    },
    {
      "trade_date": "2026-06-10",
      "recorded_at": "2026-06-11 14:04:28",
      "code": "513100",
      "name": "纳指ETF国泰",
      "price": 2.143,
      "daily_change": -0.0259,
      "estimate": 1.979,
      "premium": 0.08287013643254149,
      "quote_time": "2026-06-10 15:00:00",
      "estimate_time": "2026-06-09",
      "source_ids": [
        "eastmoney_kline",
        "tinyright_iopv"
      ],
      "trend": null
    },
    {
      "trade_date": "2026-06-10",
      "recorded_at": "2026-06-11 14:04:28",
      "code": "159501",
      "name": "纳指ETF嘉实",
      "price": 2.019,
      "daily_change": -0.0289,
      "estimate": 1.8578,
      "premium": 0.08676929701797831,
      "quote_time": "2026-06-10 15:00:00",
      "estimate_time": "2026-06-09",
      "source_ids": [
        "eastmoney_kline",
        "tinyright_iopv"
      ],
      "trend": null
    },
    {
      "trade_date": "2026-06-10",
      "recorded_at": "2026-06-11 14:04:28",
      "code": "159659",
      "name": "纳斯达克100ETF招商",
      "price": 2.257,
      "daily_change": -0.0255,
      "estimate": 2.1305,
      "premium": 0.0593757333959164,
      "quote_time": "2026-06-10 15:00:00",
      "estimate_time": "2026-06-09",
      "source_ids": [
        "eastmoney_kline",
        "tinyright_iopv"
      ],
      "trend": null
    },
    {
      "trade_date": "2026-06-09",
      "recorded_at": "2026-06-09 15:18:27",
      "code": "513100",
      "name": "纳指ETF国泰",
      "price": 2.2,
      "daily_change": 0.0407,
      "estimate": 2.0033,
      "premium": 0.09820000000000001,
      "quote_time": "2026-06-09 15:18:29",
      "estimate_time": "2026-06-08",
      "source_ids": [
        "eastmoney_quote",
        "tinyright_t1"
      ],
      "trend": null
    },
    {
      "trade_date": "2026-06-09",
      "recorded_at": "2026-06-09 15:18:27",
      "code": "159501",
      "name": "纳指ETF嘉实",
      "price": 2.079,
      "daily_change": 0.0313,
      "estimate": 1.8805,
      "premium": 0.1056,
      "quote_time": "2026-06-09 15:17:42",
      "estimate_time": "2026-06-08",
      "source_ids": [
        "eastmoney_quote",
        "tinyright_t1"
      ],
      "trend": null
    },
    {
      "trade_date": "2026-06-09",
      "recorded_at": "2026-06-09 15:18:27",
      "code": "159659",
      "name": "纳斯达克100ETF招商",
      "price": 2.316,
      "daily_change": 0.037200000000000004,
      "estimate": 2.1564,
      "premium": 0.07400000000000001,
      "quote_time": "2026-06-09 15:17:57",
      "estimate_time": "2026-06-08",
      "source_ids": [
        "eastmoney_quote",
        "tinyright_t1"
      ],
      "trend": null
    },
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
      ],
      "trend": null
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
      ],
      "trend": null
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
      ],
      "trend": null
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
      ],
      "trend": null
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
      ],
      "trend": null
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
      ],
      "trend": null
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
      ],
      "trend": null
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
      ],
      "trend": null
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
      ],
      "trend": null
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
      ],
      "trend": null
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
      ],
      "trend": null
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
      ],
      "trend": null
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
      ],
      "trend": null
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
      ],
      "trend": null
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
      ],
      "trend": null
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
      ],
      "trend": null
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
      ],
      "trend": null
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
      ],
      "trend": null
    }
  ],
  "benchmark_records": [
    {
      "track_date": "2026-06-11",
      "recorded_at": "2026-06-11 15:37:52",
      "symbol": "QQQ",
      "name": "Invesco QQQ Trust",
      "value": 693.69,
      "daily_change": -0.019976548041196307,
      "history_high": 746.16,
      "drawdown": -0.0703200385976197,
      "history_high_date": "2026-06-02",
      "quote_date": "2026-06-10",
      "unit": "USD",
      "source_ids": [
        "nasdaq_api_historical"
      ],
      "trend": null
    },
    {
      "track_date": "2026-06-11",
      "recorded_at": "2026-06-11 15:37:52",
      "symbol": "NDX",
      "name": "Nasdaq 100 Index",
      "value": 28508.03,
      "daily_change": -0.019820522958964415,
      "history_high": 30660.6,
      "drawdown": -0.07020638865514695,
      "history_high_date": "2026-06-02",
      "quote_date": "2026-06-10",
      "unit": "points",
      "source_ids": [
        "nasdaq_api_historical"
      ],
      "trend": null
    },
    {
      "track_date": "2026-06-10",
      "recorded_at": "2026-06-11 15:37:52",
      "symbol": "QQQ",
      "name": "Invesco QQQ Trust",
      "value": 707.83,
      "daily_change": -0.01150725487731652,
      "history_high": 746.16,
      "drawdown": -0.05136967942532422,
      "history_high_date": "2026-06-02",
      "quote_date": "2026-06-09",
      "unit": "USD",
      "source_ids": [
        "nasdaq_api_historical"
      ],
      "trend": null
    },
    {
      "track_date": "2026-06-10",
      "recorded_at": "2026-06-11 15:37:52",
      "symbol": "NDX",
      "name": "Nasdaq 100 Index",
      "value": 29084.5,
      "daily_change": -0.011210888868188329,
      "history_high": 30660.6,
      "drawdown": -0.051404734414851605,
      "history_high_date": "2026-06-02",
      "quote_date": "2026-06-09",
      "unit": "points",
      "source_ids": [
        "nasdaq_api_historical"
      ],
      "trend": null
    },
    {
      "track_date": "2026-06-09",
      "recorded_at": "2026-06-11 15:37:52",
      "symbol": "QQQ",
      "name": "Invesco QQQ Trust",
      "value": 716.07,
      "daily_change": 0.015615692281508053,
      "history_high": 746.16,
      "drawdown": -0.04032647153425528,
      "history_high_date": "2026-06-02",
      "quote_date": "2026-06-08",
      "unit": "USD",
      "source_ids": [
        "nasdaq_api_historical"
      ],
      "trend": null
    },
    {
      "track_date": "2026-06-09",
      "recorded_at": "2026-06-11 15:37:52",
      "symbol": "NDX",
      "name": "Nasdaq 100 Index",
      "value": 29414.26,
      "daily_change": 0.015769953311047802,
      "history_high": 30660.6,
      "drawdown": -0.040649563283171264,
      "history_high_date": "2026-06-02",
      "quote_date": "2026-06-08",
      "unit": "points",
      "source_ids": [
        "nasdaq_api_historical"
      ],
      "trend": null
    },
    {
      "track_date": "2026-06-08",
      "recorded_at": "2026-06-11 15:37:52",
      "symbol": "QQQ",
      "name": "Invesco QQQ Trust",
      "value": 705.06,
      "daily_change": -0.048000972171588385,
      "history_high": 746.16,
      "drawdown": -0.0550820199421036,
      "history_high_date": "2026-06-02",
      "quote_date": "2026-06-05",
      "unit": "USD",
      "source_ids": [
        "nasdaq_api_historical"
      ],
      "trend": null
    },
    {
      "track_date": "2026-06-08",
      "recorded_at": "2026-06-11 15:37:52",
      "symbol": "NDX",
      "name": "Nasdaq 100 Index",
      "value": 28957.6,
      "daily_change": -0.04769202385834437,
      "history_high": 30660.6,
      "drawdown": -0.05554359666803654,
      "history_high_date": "2026-06-02",
      "quote_date": "2026-06-05",
      "unit": "points",
      "source_ids": [
        "nasdaq_api_historical"
      ],
      "trend": null
    },
    {
      "track_date": "2026-06-05",
      "recorded_at": "2026-06-11 15:37:52",
      "symbol": "QQQ",
      "name": "Invesco QQQ Trust",
      "value": 740.61,
      "daily_change": -0.004837344297980439,
      "history_high": 746.16,
      "drawdown": -0.007438082984882577,
      "history_high_date": "2026-06-02",
      "quote_date": "2026-06-04",
      "unit": "USD",
      "source_ids": [
        "nasdaq_api_historical"
      ],
      "trend": null
    },
    {
      "track_date": "2026-06-05",
      "recorded_at": "2026-06-11 15:37:52",
      "symbol": "NDX",
      "name": "Nasdaq 100 Index",
      "value": 30407.81,
      "daily_change": -0.005345874096045811,
      "history_high": 30660.6,
      "drawdown": -0.008244783207112638,
      "history_high_date": "2026-06-02",
      "quote_date": "2026-06-04",
      "unit": "points",
      "source_ids": [
        "nasdaq_api_historical"
      ],
      "trend": null
    }
  ]
};
