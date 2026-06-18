from __future__ import annotations

import argparse
import base64
import datetime as dt
import html
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from http.client import RemoteDisconnected
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


APP_DIR = Path(__file__).resolve().parent
DEFAULT_OUTPUT = APP_DIR / "index.html"
DATA_DIR = APP_DIR / "data"
DEFAULT_DATA_OUTPUT = DATA_DIR / "manifest.json"
DAILY_RECORDS_DIR_NAME = "daily-records"
LEGACY_JSON_OUTPUT = DATA_DIR / "nasdaq_etf_daily_data.json"
LEGACY_JS_OUTPUT = APP_DIR / "nasdaq_etf_daily_data.js"
DEFAULT_SOURCE_CONFIG = APP_DIR / "data_sources.json"
TZ = dt.timezone(dt.timedelta(hours=8), "Asia/Shanghai")

ETF_HEADERS = [
    "交易日期",
    "代码",
    "名称",
    "当前价格",
    "当天涨幅",
    "T-1估值",
    "溢价率",
    "T-1估值日",
    "数据源",
]
BENCHMARK_HEADERS = [
    "跟踪日期",
    "标的",
    "名称",
    "当前点位/价格",
    "当天涨幅",
    "历史最高收盘点/价",
    "距最高收盘回撤",
    "最高收盘日期",
    "行情日期",
    "数据源",
]
SOURCE_HEADERS = ["数据源", "用途", "接口"]

LEGACY_SOURCE_IDS = {
    "Eastmoney quote; n.tinyright T-1 valuation": ["eastmoney_quote", "tinyright_t1"],
    "n.tinyright quote and T-1 valuation": ["tinyright_table", "tinyright_t1"],
    "Eastmoney historical K-line; n.tinyright T-1 valuation": ["eastmoney_kline", "tinyright_t1"],
    "existing historical quote; user-provided T-1 valuation": [
        "manual_historical_quote",
        "user_provided_t1",
    ],
    "existing historical quote; n.tinyright T-1 valuation": [
        "manual_historical_quote",
        "tinyright_t1",
    ],
}


def load_source_config(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def source_lookup(config: dict) -> dict[str, dict]:
    return {item["id"]: item for item in config.get("sources", [])}


def etf_codes(config: dict) -> tuple[str, ...]:
    return tuple(item["code"] for item in config.get("etfs", []))


def benchmark_symbols(config: dict) -> tuple[str, ...]:
    return tuple(item["symbol"] for item in config.get("benchmarks", []))


def source_url(config: dict, source_id: str, **kwargs: str) -> str:
    source = source_lookup(config)[source_id]
    template = source.get("url_template") or source.get("url") or ""
    return template.format(**kwargs)


def fetch_text(url: str) -> str:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "text/html,application/json;q=0.9,*/*;q=0.8",
        "Referer": "https://quote.eastmoney.com/",
    }
    if "api.nasdaq.com" in url:
        headers.update(
            {
                "Accept": "application/json, text/plain, */*",
                "Origin": "https://www.nasdaq.com",
                "Referer": "https://www.nasdaq.com/",
            }
        )
    if "query1.finance.yahoo.com" in url:
        headers.update(
            {
                "Accept": "application/json, text/plain, */*",
                "Referer": "https://finance.yahoo.com/",
            }
        )
    if "quotes.sina.cn" in url:
        headers.update({"Referer": "https://finance.sina.com.cn/"})
    if "web.ifzq.gtimg.cn" in url:
        headers.update({"Referer": "https://gu.qq.com/"})
    req = Request(
        url,
        headers=headers,
    )
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            with urlopen(req, timeout=30) as res:
                charset = res.headers.get_content_charset() or "utf-8"
                return res.read().decode(charset, "replace")
        except (HTTPError, URLError, TimeoutError, OSError, RemoteDisconnected) as exc:
            last_error = exc
            if (
                "query1.finance.yahoo.com" in url
                and isinstance(exc, HTTPError)
                and exc.code == 403
            ):
                return fetch_text_with_powershell(url)
            if attempt < 2:
                time.sleep(1 + attempt)
    raise RuntimeError(f"request failed after retries: {url}: {last_error}")


def fetch_text_with_powershell(url: str) -> str:
    executable = shutil.which("powershell.exe") or shutil.which("pwsh")
    if not executable:
        raise RuntimeError("Yahoo request was blocked and PowerShell fallback is unavailable")

    # Yahoo sometimes blocks Python urllib on Windows while accepting the same URL via WinHTTP/.NET.
    command = (
        "$ProgressPreference='SilentlyContinue'; "
        "[Console]::OutputEncoding=[System.Text.Encoding]::UTF8; "
        "[Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12; "
        "Invoke-WebRequest -Uri $env:NASDAQ_ETF_FETCH_URL -UseBasicParsing "
        "-Headers @{ 'User-Agent' = 'Mozilla/5.0' } -OutFile $env:NASDAQ_ETF_FETCH_OUTPUT"
    )
    encoded_command = base64.b64encode(command.encode("utf-16le")).decode("ascii")
    env = dict(os.environ)
    env["NASDAQ_ETF_FETCH_URL"] = url
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        output_path = Path(tmp.name)
    env["NASDAQ_ETF_FETCH_OUTPUT"] = str(output_path)
    try:
        result = subprocess.run(
            [executable, "-NoProfile", "-EncodedCommand", encoded_command],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
            timeout=45,
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError(f"PowerShell Yahoo fallback failed: {result.stderr.strip()}")
        return output_path.read_text(encoding="utf-8-sig")
    finally:
        output_path.unlink(missing_ok=True)


def extract_json_array(text: str, key: str) -> list[dict]:
    marker = f'"{key}":['
    start = text.find(marker)
    if start == -1:
        raise ValueError(f"missing {key}")

    pos = start + len(f'"{key}":')
    depth = 0
    in_string = False
    escaped = False

    for i in range(pos, len(text)):
        ch = text[i]
        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
            if depth == 0:
                return json.loads(text[pos : i + 1])

    raise ValueError(f"unterminated {key}")


def clean_cell(fragment: str) -> str:
    text = re.sub(r"<[^>]+>", "", fragment)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def parse_number_text(value: str) -> float | None:
    value = value.replace(",", "").replace("%", "").replace("$", "").strip()
    if not value or value == "-":
        return None
    try:
        return float(value)
    except ValueError:
        return None


def parse_zh_datetime(value: str) -> str:
    match = re.fullmatch(r"(\d+)月(\d+)日\s+(\d+):(\d+)", value.strip())
    if not match:
        return value
    now = dt.datetime.now(TZ)
    month, day, hour, minute = map(int, match.groups())
    parsed = dt.datetime(now.year, month, day, hour, minute, tzinfo=TZ)
    if parsed.date() > now.date() + dt.timedelta(days=7):
        parsed = parsed.replace(year=now.year - 1)
    return parsed.strftime("%Y-%m-%d %H:%M:%S")


def parse_zh_date(value: str) -> str:
    match = re.fullmatch(r"(\d+)月(\d+)日", value.strip())
    if not match:
        return value
    now = dt.datetime.now(TZ)
    month, day = map(int, match.groups())
    parsed = dt.date(now.year, month, day)
    if parsed > now.date() + dt.timedelta(days=7):
        parsed = parsed.replace(year=now.year - 1)
    return parsed.isoformat()


def as_float(value) -> float | None:
    if value in (None, "", "-"):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def parse_datetime(value: str | None) -> dt.datetime | None:
    if not value:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return dt.datetime.strptime(value, fmt).replace(tzinfo=TZ)
        except ValueError:
            pass
    return None


def quote_time(row: dict) -> dt.datetime | None:
    try:
        ts = int(row.get("f124"))
    except (TypeError, ValueError):
        return None
    return dt.datetime.fromtimestamp(ts, TZ)


def secid_for_code(code: str) -> str:
    market = "1" if code.startswith("5") else "0"
    return f"{market}.{code}"


def parse_table_rows(raw: str, codes: tuple[str, ...]) -> dict[str, dict]:
    result = {}
    for row_match in re.finditer(r"<tr[^>]*>.*?</tr>", raw, re.S):
        cells = [clean_cell(cell) for cell in re.findall(r"<td[^>]*>(.*?)</td>", row_match.group(0), re.S)]
        if len(cells) < 15 or cells[1] not in codes:
            continue

        daily_change = parse_number_text(cells[4])
        premium = parse_number_text(cells[10])
        result[cells[1]] = {
            "market": {
                "code": cells[1],
                "name": cells[2],
                "price": parse_number_text(cells[3]),
                "daily_change_pct": daily_change,
                "datetime": parse_zh_datetime(cells[14]),
            },
            "realtime": {
                "realtime": parse_number_text(cells[9]),
                "premium": premium / 100 if premium is not None else None,
                "realtime_datetime": parse_zh_date(cells[11]),
            },
        }
    return result


def parse_tinyright(config: dict, codes: tuple[str, ...]) -> dict[str, dict]:
    raw = fetch_text(source_url(config, "tinyright_t1"))
    table_rows = parse_table_rows(raw, codes)
    if all(code in table_rows for code in codes):
        return table_rows

    candidates = []
    for value in (raw, html.unescape(raw)):
        candidates.append(value)
        candidates.append(value.replace('\\"', '"'))

    last_error: Exception | None = None
    for value in candidates:
        try:
            try:
                market_rows = extract_json_array(value, "stockData")
            except ValueError:
                market_rows = extract_json_array(value, "marketData")
            market = {item["code"]: item for item in market_rows}
            t1_rows = {item["code"]: item for item in extract_json_array(value, "t1Data")}
            return {
                code: {
                    "market": market.get(code, {}),
                    "realtime": {
                        "realtime": t1_rows.get(code, {}).get("t1"),
                        "realtime_datetime": t1_rows.get(code, {}).get("t1_date"),
                    },
                }
                for code in codes
            }
        except (ValueError, json.JSONDecodeError) as exc:
            last_error = exc

    raise RuntimeError(f"failed to parse n.tinyright data: {last_error}")


def parse_tinyright_t1(config: dict, codes: tuple[str, ...]) -> dict[str, dict]:
    raw = fetch_text(source_url(config, "tinyright_t1"))
    candidates = []
    for value in (raw, html.unescape(raw)):
        candidates.append(value)
        candidates.append(value.replace('\\"', '"'))

    last_error: Exception | None = None
    for value in candidates:
        try:
            rows = extract_json_array(value, "t1Data")
            return {row["code"]: row for row in rows if row.get("code") in codes}
        except (ValueError, json.JSONDecodeError) as exc:
            last_error = exc
    raise RuntimeError(f"failed to parse n.tinyright t1 data: {last_error}")


def parse_tinyright_iopv(config: dict, codes: tuple[str, ...]) -> dict[str, dict]:
    raw = fetch_text(source_url(config, "tinyright_iopv"))
    candidates = []
    for value in (raw, html.unescape(raw)):
        candidates.append(value)
        candidates.append(value.replace('\\"', '"'))

    last_error: Exception | None = None
    for value in candidates:
        try:
            rows = extract_json_array(value, "iopvData")
            return {row["code"]: row for row in rows if row.get("code") in codes}
        except (ValueError, json.JSONDecodeError) as exc:
            last_error = exc
    raise RuntimeError(f"failed to parse n.tinyright iopv data: {last_error}")


def parse_eastmoney(config: dict, codes: tuple[str, ...]) -> dict[str, dict]:
    secids = ",".join(secid_for_code(code) for code in codes)
    data = json.loads(fetch_text(source_url(config, "eastmoney_quote", secids=secids)))
    rows = data.get("data", {}).get("diff") or []
    return {row.get("f12"): row for row in rows if row.get("f12")}


def parse_eastmoney_kline(config: dict, code: str, trade_date: dt.date) -> dict:
    date_text = trade_date.strftime("%Y%m%d")
    url = source_url(config, "eastmoney_kline", secid=secid_for_code(code), date=date_text)
    data = json.loads(fetch_text(url))
    rows = data.get("data", {}).get("klines") or []
    if not rows:
        raise RuntimeError(f"{code} has no historical kline on {trade_date}")

    fields = rows[0].split(",")
    if len(fields) < 11:
        raise RuntimeError(f"{code} historical kline is incomplete")
    return {
        "code": code,
        "name": data.get("data", {}).get("name") or code,
        "date": dt.date.fromisoformat(fields[0]),
        "close": float(fields[2]),
        "daily_change": float(fields[8]) / 100,
    }


MAX_TREND_POINTS = 64


def downsample_trend_points(points: list[dict], max_points: int = MAX_TREND_POINTS) -> list[dict]:
    # 分钟数据太多会让数据文件膨胀；保留走势形状即可。
    if len(points) <= max_points:
        return points
    step = (len(points) - 1) / (max_points - 1)
    return [points[round(index * step)] for index in range(max_points)]


def trend_payload(trend_date: dt.date, source_ids: list[str], points: list[dict]) -> dict | None:
    valid_points = [
        {
            "time": str(point["time"]),
            "value": float(point["value"]),
        }
        for point in points
        if as_float(point.get("value")) is not None
    ]
    if not valid_points:
        return None
    return {
        "date": trend_date.isoformat(),
        "source_ids": source_ids,
        "points": downsample_trend_points(valid_points),
    }


def parse_eastmoney_trend(config: dict, code: str, target_date: dt.date, days: int = 1) -> dict | None:
    url = source_url(config, "eastmoney_trend", secid=secid_for_code(code), days=str(days))
    data = json.loads(fetch_text(url))
    rows = (data.get("data") or {}).get("trends") or []
    points = []
    for row in rows:
        fields = str(row).split(",")
        if len(fields) < 3:
            continue
        try:
            point_time = dt.datetime.strptime(fields[0], "%Y-%m-%d %H:%M")
        except ValueError:
            continue
        if point_time.date() != target_date:
            continue
        value = as_float(fields[2]) or as_float(fields[1])
        if value is None:
            continue
        points.append({"time": point_time.strftime("%H:%M"), "value": value})
    return trend_payload(target_date, ["eastmoney_trend"], points)


def cn_etf_symbol(code: str) -> str:
    prefix = "sh" if code.startswith("5") else "sz"
    return f"{prefix}{code}"


def parse_tencent_minute_trend(config: dict, code: str, target_date: dt.date) -> dict | None:
    # Tencent's minute endpoint has no explicit date, so use it only for same-day records.
    if target_date != dt.datetime.now(TZ).date():
        return None
    symbol = cn_etf_symbol(code)
    url = source_url(config, "tencent_minute", symbol=symbol)
    data = json.loads(fetch_text(url))
    rows = (((data.get("data") or {}).get(symbol) or {}).get("data") or {}).get("data") or []
    points = []
    for row in rows:
        fields = str(row).split()
        if len(fields) < 2:
            continue
        time_text = fields[0]
        value = as_float(fields[1])
        if len(time_text) != 4 or value is None:
            continue
        points.append({"time": f"{time_text[:2]}:{time_text[2:]}", "value": value})
    return trend_payload(target_date, ["tencent_minute"], points)


def parse_sina_minute_kline(config: dict, code: str, target_date: dt.date) -> dict | None:
    symbol = cn_etf_symbol(code)
    url = source_url(config, "sina_minute_kline", symbol=symbol, count="1023")
    text = fetch_text(url)
    match = re.search(r"=\((\[.*\])\);\s*$", text, re.S)
    if not match:
        return None
    rows = json.loads(match.group(1))
    points = []
    for row in rows:
        try:
            point_time = dt.datetime.strptime(str(row.get("day") or ""), "%Y-%m-%d %H:%M:%S")
        except ValueError:
            continue
        if point_time.date() != target_date:
            continue
        value = as_float(row.get("close")) or as_float(row.get("open"))
        if value is None:
            continue
        points.append({"time": point_time.strftime("%H:%M"), "value": value})
    return trend_payload(target_date, ["sina_minute_kline"], points)


def yahoo_date(timestamp: int) -> dt.date:
    return dt.datetime.fromtimestamp(timestamp, dt.timezone.utc).date()


def parse_nasdaq_date(value: str) -> dt.date:
    return dt.datetime.strptime(value, "%m/%d/%Y").date()


def parse_nasdaq_chart_date(value: str) -> dt.date:
    return dt.datetime.strptime(value, "%b %d, %Y").date()


def parse_us_market_time(value: str) -> dt.time | None:
    try:
        return dt.datetime.strptime(value, "%I:%M %p").time()
    except ValueError:
        return None


def is_us_regular_session(time_value: dt.time | None) -> bool:
    return time_value is not None and dt.time(9, 30) <= time_value <= dt.time(16, 0)


def fetch_nasdaq_chart_payload(config: dict, item: dict) -> dict:
    symbol = item.get("nasdaq_symbol") or item["symbol"]
    assetclass = item.get("nasdaq_assetclass") or "index"
    url = source_url(
        config,
        "nasdaq_api_chart",
        symbol=quote(symbol, safe=""),
        assetclass=assetclass,
    )
    data = json.loads(fetch_text(url))
    return data.get("data") or {}


def parse_nasdaq_history(
    config: dict,
    item: dict,
    target_date: dt.date,
    lookback_days: int = 14,
) -> list[dict]:
    symbol = item.get("nasdaq_symbol") or item["symbol"]
    assetclass = item.get("nasdaq_assetclass") or "index"
    fromdate = (target_date - dt.timedelta(days=lookback_days)).isoformat()
    url = source_url(
        config,
        "nasdaq_api_historical",
        symbol=quote(symbol, safe=""),
        assetclass=assetclass,
        fromdate=fromdate,
        todate=target_date.isoformat(),
    )
    data = json.loads(fetch_text(url))
    status = data.get("status", {})
    if status.get("rCode") != 200:
        raise RuntimeError(f"{symbol} Nasdaq historical API error: {status}")

    table = (data.get("data") or {}).get("tradesTable") or {}
    rows = table.get("rows") or []
    points = []
    for row in rows:
        date_text = row.get("date")
        close = parse_number_text(str(row.get("close", "")))
        if not date_text or close is None:
            continue
        date = parse_nasdaq_date(date_text)
        if date <= target_date:
            points.append(
                {
                    "date": date,
                    "close": close,
                    "source_id": "nasdaq_api_historical",
                }
            )

    if not points:
        raise RuntimeError(f"{symbol} has no Nasdaq historical rows before {target_date}")
    return sorted(points, key=lambda point: point["date"])


def parse_nasdaq_chart_quote(config: dict, item: dict, target_date: dt.date) -> dict | None:
    payload = fetch_nasdaq_chart_payload(config, item)
    chart_date_text = payload.get("timeAsOf")
    if not chart_date_text:
        return None
    try:
        chart_date = parse_nasdaq_chart_date(chart_date_text)
    except ValueError:
        return None
    if chart_date != target_date:
        return None
    close = parse_number_text(str(payload.get("lastSalePrice") or ""))
    if close is None:
        return None
    return {
        "date": chart_date,
        "close": close,
        "source_id": "nasdaq_api_chart",
    }


def parse_nasdaq_chart(config: dict, item: dict, target_date: dt.date) -> dict | None:
    payload = fetch_nasdaq_chart_payload(config, item)
    chart_date_text = payload.get("timeAsOf")
    if not chart_date_text:
        return None
    try:
        chart_date = parse_nasdaq_chart_date(chart_date_text)
    except ValueError:
        return None
    if chart_date != target_date:
        return None

    points = []
    for point in payload.get("chart") or []:
        value = as_float(point.get("y")) or as_float((point.get("z") or {}).get("value"))
        time_text = ((point.get("z") or {}).get("dateTime") or "").replace(" ET", "")
        if value is None or not is_us_regular_session(parse_us_market_time(time_text)):
            continue
        points.append({"time": time_text, "value": value})
    points.sort(key=lambda point: parse_us_market_time(point["time"]) or dt.time.min)

    close = parse_number_text(str(payload.get("lastSalePrice") or ""))
    if close is not None and points:
        # QQQ chart includes extended-hours prints; force the final regular-session
        # point to the official close used by the table row.
        if points[-1]["time"] == "4:00 PM":
            points[-1]["value"] = close
        else:
            points.append({"time": "4:00 PM", "value": close})
    return trend_payload(target_date, ["nasdaq_api_chart"], points)


def parse_yahoo_intraday_trend(config: dict, symbol: str, target_date: dt.date) -> dict | None:
    start = dt.datetime.combine(target_date - dt.timedelta(days=1), dt.time.min, tzinfo=dt.timezone.utc)
    end = dt.datetime.combine(target_date + dt.timedelta(days=2), dt.time.min, tzinfo=dt.timezone.utc)
    url = source_url(
        config,
        "yahoo_intraday_chart",
        symbol=quote(symbol, safe=""),
        period1=str(int(start.timestamp())),
        period2=str(int(end.timestamp())),
        interval="5m",
    )
    data = json.loads(fetch_text(url))
    chart = data.get("chart", {})
    if chart.get("error"):
        raise RuntimeError(f"{symbol} yahoo intraday error: {chart['error']}")

    result = (chart.get("result") or [None])[0]
    if not result:
        return None

    timestamps = result.get("timestamp") or []
    quote_rows = (result.get("indicators", {}).get("quote") or [{}])[0]
    closes = quote_rows.get("close") or []
    gmtoffset = int((result.get("meta") or {}).get("gmtoffset") or 0)
    points = []
    for index, ts in enumerate(timestamps):
        close = as_float(closes[index] if index < len(closes) else None)
        if close is None:
            continue
        local_time = dt.datetime.fromtimestamp(int(ts), dt.timezone.utc) + dt.timedelta(seconds=gmtoffset)
        if local_time.date() != target_date:
            continue
        points.append({"time": local_time.strftime("%H:%M"), "value": close})
    return trend_payload(target_date, ["yahoo_intraday_chart"], points)


def yahoo_etf_symbol(code: str) -> str:
    suffix = "SS" if code.startswith("5") else "SZ"
    return f"{code}.{suffix}"


def yahoo_intraday_enabled() -> bool:
    # Yahoo is only used after the primary trend source fails. Keep it on by default
    # so automated runs still get intraday trends when Eastmoney or Nasdaq drops a request.
    return os.environ.get("NASDAQ_ETF_ENABLE_YAHOO_INTRADAY") != "0"


def parse_etf_trend(config: dict, code: str, target_date: dt.date) -> dict | None:
    try:
        trend = parse_eastmoney_trend(config, code, target_date, days=5)
    except (RuntimeError, json.JSONDecodeError, ValueError):
        trend = None
    if trend:
        return trend
    try:
        trend = parse_tencent_minute_trend(config, code, target_date)
    except (RuntimeError, json.JSONDecodeError, ValueError):
        trend = None
    if trend:
        return trend
    try:
        trend = parse_sina_minute_kline(config, code, target_date)
    except (RuntimeError, json.JSONDecodeError, ValueError):
        trend = None
    if trend:
        return trend
    if not yahoo_intraday_enabled():
        return None
    try:
        return parse_yahoo_intraday_trend(config, yahoo_etf_symbol(code), target_date)
    except (RuntimeError, json.JSONDecodeError, ValueError):
        return None


def parse_benchmark_trend(config: dict, item: dict, target_date: dt.date) -> dict | None:
    try:
        trend = parse_nasdaq_chart(config, item, target_date)
    except (RuntimeError, json.JSONDecodeError, ValueError):
        trend = None
    if trend:
        return trend
    if not yahoo_intraday_enabled():
        return None
    try:
        return parse_yahoo_intraday_trend(config, item.get("yahoo_symbol") or item["symbol"], target_date)
    except (RuntimeError, json.JSONDecodeError, ValueError):
        return None


def parse_benchmark_history(config: dict, item: dict, target_date: dt.date | None = None) -> dict:
    symbol = item["yahoo_symbol"]
    source_ids: set[str] = set()
    points = []
    if target_date:
        try:
            points = parse_nasdaq_history(config, item, target_date, lookback_days=11000)
            source_ids = {"nasdaq_api_historical"}
        except (RuntimeError, json.JSONDecodeError):
            points = []

    if not points:
        url = source_url(config, "yahoo_chart", symbol=quote(symbol, safe=""))
        source_ids = {"yahoo_chart"}
        try:
            data = json.loads(fetch_text(url))
            chart = data.get("chart", {})
            if chart.get("error"):
                raise RuntimeError(f"{symbol} yahoo chart error: {chart['error']}")

            result = (chart.get("result") or [None])[0]
            if not result:
                raise RuntimeError(f"{symbol} yahoo chart has no result")

            timestamps = result.get("timestamp") or []
            quote_rows = (result.get("indicators", {}).get("quote") or [{}])[0]
            closes = quote_rows.get("close") or []
            for index, ts in enumerate(timestamps):
                close = as_float(closes[index] if index < len(closes) else None)
                if close is None:
                    continue
                points.append({"date": yahoo_date(ts), "close": close, "source_id": "yahoo_chart"})

            if not points:
                raise RuntimeError(f"{symbol} yahoo chart has no price points")
        except (RuntimeError, json.JSONDecodeError):
            if not target_date:
                raise
            points = parse_nasdaq_history(config, item, target_date, lookback_days=11000)
            source_ids = {"nasdaq_api_historical"}

    if target_date and not any(point["date"] == target_date for point in points):
        target_points = []
        try:
            nasdaq_points = parse_nasdaq_history(config, item, target_date)
            target_points = [point for point in nasdaq_points if point["date"] == target_date]
        except RuntimeError:
            pass
        if not target_points:
            try:
                chart_point = parse_nasdaq_chart_quote(config, item, target_date)
            except (RuntimeError, json.JSONDecodeError, ValueError):
                chart_point = None
            if chart_point:
                target_points = [chart_point]
        if target_points:
            points.append(target_points[-1])
            points = sorted(points, key=lambda point: point["date"])
            source_ids.add(target_points[-1].get("source_id", "nasdaq_api_historical"))

    selected_index = len(points) - 1
    if target_date:
        matching_indexes = [idx for idx, point in enumerate(points) if point["date"] <= target_date]
        if not matching_indexes:
            raise RuntimeError(f"{symbol} has no benchmark history before {target_date}")
        selected_index = matching_indexes[-1]

    selected = points[selected_index]
    prev = points[selected_index - 1] if selected_index > 0 else None
    current = selected["close"]
    daily_change = current / prev["close"] - 1 if prev else 0.0

    history_slice = points[: selected_index + 1]
    high_point = max(history_slice, key=lambda point: point["close"])

    drawdown = current / high_point["close"] - 1
    return {
        "symbol": item["symbol"],
        "name": item["name"],
        "value": current,
        "daily_change": daily_change,
        "history_high": high_point["close"],
        "drawdown": drawdown,
        "history_high_date": high_point["date"],
        "quote_date": selected["date"],
        "unit": item.get("unit", ""),
        "source_ids": sorted(source_ids | {selected.get("source_id", "yahoo_chart")}),
    }


def benchmark_target_date_for_track_date(track_date: dt.date) -> dt.date:
    return track_date - dt.timedelta(days=1)


def next_weekday(date_value: dt.date) -> dt.date:
    next_date = date_value + dt.timedelta(days=1)
    while next_date.weekday() >= 5:
        next_date += dt.timedelta(days=1)
    return next_date


def build_etf_rows(config: dict, now: dt.datetime) -> list[dict]:
    codes = etf_codes(config)
    tinyright = parse_tinyright(config, codes)
    try:
        eastmoney = parse_eastmoney(config, codes)
    except (RuntimeError, json.JSONDecodeError):
        eastmoney = {}
    rows = []

    for code in codes:
        quote_row = eastmoney.get(code, {})
        market = tinyright[code]["market"]
        realtime = tinyright[code]["realtime"]

        price = as_float(quote_row.get("f2")) or as_float(market.get("price"))
        daily_change = as_float(quote_row.get("f3"))
        if daily_change is None:
            daily_change = as_float(market.get("daily_change_pct"))
        if daily_change is None:
            prev = as_float(market.get("yesterdayClosePrice"))
            daily_change = ((price / prev - 1) * 100) if price and prev else None

        estimate = as_float(realtime.get("realtime"))
        if price is None or daily_change is None or estimate is None:
            raise RuntimeError(f"{code} data is incomplete")

        estimate_time = realtime.get("realtime_datetime") or ""
        e_time = parse_datetime(estimate_time)
        q_time = quote_time(quote_row) or parse_datetime(market.get("datetime")) or e_time
        premium = as_float(realtime.get("premium"))
        if premium is None:
            premium = price / estimate - 1
        source_ids = ["eastmoney_quote", "tinyright_t1"] if quote_row else ["tinyright_table", "tinyright_t1"]
        trade_date = (q_time or now).date()
        trend = parse_etf_trend(config, code, trade_date)

        rows.append(
            {
                "trade_date": trade_date,
                "recorded_at": now.strftime("%Y-%m-%d %H:%M:%S"),
                "code": code,
                "name": quote_row.get("f14") or market.get("name") or code,
                "price": price,
                "daily_change": daily_change / 100,
                "estimate": estimate,
                "premium": premium,
                "quote_time": q_time.strftime("%Y-%m-%d %H:%M:%S") if q_time else "",
                "estimate_time": estimate_time,
                "source_ids": source_ids,
                "quote_date": q_time.date() if q_time else None,
                "estimate_date": e_time.date() if e_time else None,
                "trend": trend,
            }
        )

    return rows


def build_backfill_etf_rows(
    config: dict,
    trade_date: dt.date,
    now: dt.datetime,
    valuation_target_date: dt.date | None = None,
) -> list[dict]:
    codes = etf_codes(config)
    t1_data = parse_tinyright_t1(config, codes)
    iopv_data = parse_tinyright_iopv(config, codes)
    rows = []

    for code in codes:
        quote_row = parse_eastmoney_kline(config, code, trade_date)
        source_ids = ["eastmoney_kline", "tinyright_t1"]
        valuation = t1_data.get(code)
        if valuation:
            valuation_date = dt.date.fromisoformat(valuation["t1_date"])
            estimate = float(valuation["t1"])
        else:
            valuation_date = None
            estimate = None

        if valuation_target_date and valuation_date != valuation_target_date:
            iopv = iopv_data.get(code)
            iopv_date = dt.date.fromisoformat(iopv["date"]) if iopv else None
            if iopv and iopv_date == valuation_target_date:
                valuation_date = iopv_date
                estimate = float(iopv["iopv"])
                source_ids = ["eastmoney_kline", "tinyright_iopv"]
            else:
                raise RuntimeError(
                    f"{code} valuation date mismatch: expected {valuation_target_date}, "
                    f"got T-1 {valuation_date} and IOPV {iopv_date}"
                )

        if valuation_date is None or estimate is None:
            raise RuntimeError(f"{code} has no valuation")

        price = quote_row["close"]
        rows.append(
            {
                "trade_date": trade_date,
                "recorded_at": now.strftime("%Y-%m-%d %H:%M:%S"),
                "code": code,
                "name": quote_row["name"],
                "price": price,
                "daily_change": quote_row["daily_change"],
                "estimate": estimate,
                "premium": price / estimate - 1,
                "quote_time": f"{trade_date.isoformat()} 15:00:00",
                "estimate_time": valuation_date.isoformat(),
                "source_ids": source_ids,
                "quote_date": trade_date,
                "estimate_date": valuation_date,
            }
        )

    return rows


def trend_matches_date(trend: dict | None, date_value: dt.date) -> bool:
    if not trend or not (trend.get("points") or []):
        return False
    return trend.get("date") == date_value.isoformat()


def build_benchmark_row(
    config: dict,
    item: dict,
    track_date: dt.date,
    now: dt.datetime,
    target_date: dt.date | None = None,
    existing_trend: dict | None = None,
    include_trend: bool = True,
) -> dict:
    quote_row = parse_benchmark_history(config, item, target_date)
    trend = existing_trend if trend_matches_date(existing_trend, quote_row["quote_date"]) else None
    if include_trend and not trend:
        trend = parse_benchmark_trend(config, item, quote_row["quote_date"])
    return {
        "track_date": track_date,
        "recorded_at": now.strftime("%Y-%m-%d %H:%M:%S"),
        **quote_row,
        "trend": trend,
    }


def build_benchmark_rows(
    config: dict,
    track_date: dt.date,
    now: dt.datetime,
    target_date: dt.date | None = None,
) -> list[dict]:
    return [
        build_benchmark_row(config, item, track_date, now, target_date)
        for item in config.get("benchmarks", [])
    ]


def public_etf_row(item: dict) -> dict:
    return {
        "trade_date": item["trade_date"].isoformat()
        if hasattr(item["trade_date"], "isoformat")
        else str(item["trade_date"]),
        "recorded_at": item["recorded_at"],
        "code": item["code"],
        "name": item["name"],
        "price": item["price"],
        "daily_change": item["daily_change"],
        "estimate": item["estimate"],
        "premium": item["premium"],
        "quote_time": item.get("quote_time", ""),
        "estimate_time": item["estimate_time"],
        "source_ids": item.get("source_ids") or infer_legacy_source_ids(item.get("source", "")),
        "trend": item.get("trend"),
    }


def public_benchmark_row(item: dict) -> dict:
    return {
        "track_date": item["track_date"].isoformat()
        if hasattr(item["track_date"], "isoformat")
        else str(item["track_date"]),
        "recorded_at": item["recorded_at"],
        "symbol": item["symbol"],
        "name": item["name"],
        "value": item["value"],
        "daily_change": item["daily_change"],
        "history_high": item["history_high"],
        "drawdown": item["drawdown"],
        "history_high_date": item["history_high_date"].isoformat()
        if hasattr(item["history_high_date"], "isoformat")
        else str(item["history_high_date"]),
        "quote_date": item["quote_date"].isoformat()
        if hasattr(item["quote_date"], "isoformat")
        else str(item["quote_date"]),
        "unit": item.get("unit", ""),
        "source_ids": item.get("source_ids", ["yahoo_chart"]),
        "trend": item.get("trend"),
    }


def infer_legacy_source_ids(source_text: str) -> list[str]:
    if source_text in LEGACY_SOURCE_IDS:
        return LEGACY_SOURCE_IDS[source_text]
    if not source_text:
        return []
    return ["manual_historical_quote"]


def normalize_etf_record(row: dict) -> dict:
    normalized = dict(row)
    normalized["source_ids"] = normalized.get("source_ids") or infer_legacy_source_ids(normalized.get("source", ""))
    normalized["trend"] = normalized.get("trend")
    normalized.pop("source", None)
    return normalized


def normalize_benchmark_record(row: dict) -> dict:
    normalized = dict(row)
    normalized["source_ids"] = normalized.get("source_ids") or ["yahoo_chart"]
    normalized["trend"] = normalized.get("trend")
    return normalized


def data_path_for_html(path: Path) -> Path:
    if path == DEFAULT_OUTPUT:
        return DEFAULT_DATA_OUTPUT
    return path.with_name(f"{path.stem}_manifest.json")


def load_json_or_legacy_js(path: Path) -> dict:
    content = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        return json.loads(content)

    match = re.search(
        r"window\.NASDAQ_TRACKING_DATA\s*=\s*(\{.*\})\s*;?\s*$",
        content,
        re.S,
    )
    if not match:
        raise ValueError(f"unsupported data file: {path}")
    return json.loads(match.group(1))


def read_manifest_payload(path: Path, manifest: dict) -> dict:
    etf_records: list[dict] = []
    benchmark_records: list[dict] = []
    for item in manifest.get("daily_files", []):
        daily_path = path.parent / item["file"]
        if not daily_path.exists():
            raise FileNotFoundError(f"missing daily data file: {daily_path}")
        daily_data = json.loads(daily_path.read_text(encoding="utf-8"))
        etf_records.extend(daily_data.get("etf_records", []))
        benchmark_records.extend(daily_data.get("benchmark_records", []))

    payload = dict(manifest)
    payload["etf_records"] = etf_records
    payload["benchmark_records"] = benchmark_records
    return payload


def read_data_file(path: Path) -> dict | None:
    candidates = [path]
    if path == DEFAULT_DATA_OUTPUT and not path.exists():
        candidates.extend([LEGACY_JSON_OUTPUT, LEGACY_JS_OUTPUT])

    for candidate in candidates:
        if not candidate.exists():
            continue

        data = load_json_or_legacy_js(candidate)
        if "daily_files" in data:
            return read_manifest_payload(candidate, data)
        return data

    return None


def read_records(data_path: Path) -> tuple[list[dict], list[dict]]:
    data = read_data_file(data_path)
    if isinstance(data, dict):
        return (
            [normalize_etf_record(row) for row in data.get("etf_records", [])],
            [normalize_benchmark_record(row) for row in data.get("benchmark_records", [])],
        )
    return [], []


def sort_etf_records(records: list[dict], codes: tuple[str, ...]) -> list[dict]:
    return sorted(
        records,
        key=lambda row: (
            str(row.get("trade_date", "")),
            -(codes.index(row["code"]) if row.get("code") in codes else 99),
        ),
        reverse=True,
    )


def sort_benchmark_records(records: list[dict], symbols: tuple[str, ...]) -> list[dict]:
    return sorted(
        records,
        key=lambda row: (
            str(row.get("quote_date", "")),
            -(symbols.index(row["symbol"]) if row.get("symbol") in symbols else 99),
        ),
        reverse=True,
    )


def daily_record_relative_path(date_text: str) -> Path:
    year, month, _ = date_text.split("-")
    return Path(DAILY_RECORDS_DIR_NAME) / year / month / f"{date_text}.json"


def split_daily_records(etf_records: list[dict], benchmark_records: list[dict], config: dict) -> dict[str, dict]:
    days: dict[str, dict] = {}
    for row in sort_etf_records(etf_records, etf_codes(config)):
        days.setdefault(row["trade_date"], {"etf_records": [], "benchmark_records": []})["etf_records"].append(row)
    for row in sort_benchmark_records(benchmark_records, benchmark_symbols(config)):
        days.setdefault(row["quote_date"], {"etf_records": [], "benchmark_records": []})["benchmark_records"].append(row)
    return dict(sorted(days.items(), reverse=True))


def render_daily_json(date_text: str, records: dict) -> str:
    return json.dumps(
        {
            "date": date_text,
            "etf_records": records["etf_records"],
            "benchmark_records": records["benchmark_records"],
        },
        ensure_ascii=False,
        indent=2,
    )


def render_manifest_json(daily_records: dict[str, dict], config: dict) -> str:
    payload = {
        "generated_at": dt.datetime.now(TZ).strftime("%Y-%m-%d %H:%M:%S"),
        "etfs": config.get("etfs", []),
        "benchmarks": config.get("benchmarks", []),
        "sources": config.get("sources", []),
        "daily_files": [
            {
                "date": date_text,
                "file": daily_record_relative_path(date_text).as_posix(),
                "etf_count": len(records["etf_records"]),
                "benchmark_count": len(records["benchmark_records"]),
            }
            for date_text, records in daily_records.items()
        ],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def relative_web_path(page_path: Path, asset_path: Path) -> str:
    try:
        return Path(os.path.relpath(asset_path, page_path.parent)).as_posix()
    except ValueError:
        return asset_path.name


def render_html(data_url: str) -> str:
    escaped_data_url = html.escape(data_url, quote=True)
    # Python 只负责数据和页面壳，具体界面交给 React。
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>纳指跟踪记录</title>
  <link rel="stylesheet" href="assets/app.css">
</head>
<body>
  <div id="root" data-url="{escaped_data_url}"></div>
  <script type="module" src="assets/app.js"></script>
</body>
</html>
"""


def write_data_files(
    data_path: Path,
    config: dict,
    etf_records: list[dict],
    benchmark_records: list[dict],
) -> None:
    daily_records = split_daily_records(etf_records, benchmark_records, config)
    for date_text, records in daily_records.items():
        daily_path = data_path.parent / daily_record_relative_path(date_text)
        daily_path.parent.mkdir(parents=True, exist_ok=True)
        daily_path.write_text(render_daily_json(date_text, records), encoding="utf-8")
    data_path.write_text(render_manifest_json(daily_records, config), encoding="utf-8")


def write_page_and_data(
    path: Path,
    data_path: Path,
    config: dict,
    etf_records: list[dict],
    benchmark_records: list[dict],
) -> None:
    write_data_files(data_path, config, etf_records, benchmark_records)
    path.write_text(render_html(relative_web_path(path, data_path)), encoding="utf-8")


def upsert_records(records: list[dict], rows: list[dict], key_fields: tuple[str, ...]) -> int:
    existing = {
        tuple(str(row.get(field)) for field in key_fields): idx
        for idx, row in enumerate(records)
    }
    changed = 0
    for row in rows:
        key = tuple(str(row.get(field)) for field in key_fields)
        if key in existing:
            records[existing[key]] = row
        else:
            existing[key] = len(records)
            records.append(row)
        changed += 1
    return changed


def write_rows(
    path: Path,
    data_path: Path,
    config: dict,
    etf_rows: list[dict] | None = None,
    benchmark_rows: list[dict] | None = None,
) -> tuple[int, int]:
    etf_records, benchmark_records = read_records(data_path)
    etf_records = [normalize_etf_record(row) for row in etf_records]
    benchmark_records = [normalize_benchmark_record(row) for row in benchmark_records]

    etf_changed = upsert_records(
        etf_records,
        [public_etf_row(row) for row in etf_rows or []],
        ("trade_date", "code"),
    )
    benchmark_changed = upsert_records(
        benchmark_records,
        [public_benchmark_row(row) for row in benchmark_rows or []],
        ("quote_date", "symbol"),
    )

    write_page_and_data(path, data_path, config, etf_records, benchmark_records)
    return etf_changed, benchmark_changed


def validate_timing(rows: list[dict], now: dt.datetime, force: bool) -> str | None:
    if force:
        return None
    if now.weekday() >= 5:
        return "today is not a weekday"
    if now.time() < dt.time(15, 0):
        return "market has not closed yet"

    today = now.date()
    for item in rows:
        if item["quote_date"] != today:
            return f"{item['code']} quote date is {item['quote_date']}, not {today}"
    return None


def build_current_rows(config: dict, now: dt.datetime) -> tuple[list[dict], list[dict]]:
    etf_rows = build_etf_rows(config, now)
    benchmark_rows = build_benchmark_rows(
        config,
        now.date(),
        now,
        target_date=benchmark_target_date_for_track_date(now.date()),
    )
    return etf_rows, benchmark_rows


def build_backfill_rows(
    config: dict,
    trade_date: dt.date,
    now: dt.datetime,
) -> tuple[list[dict], list[dict]]:
    benchmark_rows = build_benchmark_rows(
        config,
        trade_date,
        now,
        target_date=benchmark_target_date_for_track_date(trade_date),
    )
    quote_date = benchmark_rows[0]["quote_date"] if benchmark_rows else None
    valuation_target_date = (
        quote_date if isinstance(quote_date, dt.date) else dt.date.fromisoformat(quote_date)
    ) if quote_date else None
    etf_rows = build_backfill_etf_rows(config, trade_date, now, valuation_target_date)
    return etf_rows, benchmark_rows


def build_benchmark_refresh_rows(
    config: dict,
    etf_records: list[dict],
    benchmark_records: list[dict],
    now: dt.datetime,
) -> list[dict]:
    benchmarks = {item["symbol"]: item for item in config.get("benchmarks", [])}
    rows = []
    daily_dates = {
        str(row.get("trade_date"))
        for row in etf_records
        if row.get("trade_date")
    } | {
        str(row.get("quote_date"))
        for row in benchmark_records
        if row.get("quote_date")
    }
    existing_track_keys = set()
    existing_quote_keys = set()

    for record in benchmark_records:
        item = benchmarks.get(record.get("symbol"))
        if not item:
            continue
        track_date = dt.date.fromisoformat(record["track_date"])
        target_date = benchmark_target_date_for_track_date(track_date)
        row = build_benchmark_row(
            config,
            item,
            track_date,
            now,
            target_date,
            existing_trend=record.get("trend"),
            include_trend=False,
        )
        quote_date = row["quote_date"].isoformat()
        rows.append(row)
        existing_track_keys.add((track_date.isoformat(), item["symbol"]))
        existing_quote_keys.add((quote_date, item["symbol"]))

    for track_date_text in sorted({str(row.get("trade_date")) for row in etf_records if row.get("trade_date")}):
        track_date = dt.date.fromisoformat(track_date_text)
        target_date = benchmark_target_date_for_track_date(track_date)
        for item in config.get("benchmarks", []):
            symbol = item["symbol"]
            if (track_date_text, symbol) in existing_track_keys:
                continue
            row = build_benchmark_row(
                config,
                item,
                track_date,
                now,
                target_date,
                include_trend=False,
            )
            quote_date = row["quote_date"].isoformat()
            quote_key = (quote_date, symbol)
            # 只补当前数据集中已有日期的缺口，避免周末/节假日推导出新的孤立历史文件。
            if quote_date not in daily_dates or quote_key in existing_quote_keys:
                continue
            rows.append(row)
            existing_track_keys.add((track_date_text, symbol))
            existing_quote_keys.add(quote_key)

    return rows


def build_benchmark_quote_date_rows(
    config: dict,
    quote_date: dt.date,
    now: dt.datetime,
    track_date: dt.date | None = None,
) -> list[dict]:
    track_date = track_date or next_weekday(quote_date)
    return [
        build_benchmark_row(
            config,
            item,
            track_date,
            now,
            target_date=quote_date,
            include_trend=False,
        )
        for item in config.get("benchmarks", [])
    ]


def refresh_missing_trends(
    config: dict,
    etf_records: list[dict],
    benchmark_records: list[dict],
) -> tuple[int, int]:
    etf_changed = 0
    for row in etf_records:
        points = (row.get("trend") or {}).get("points") or []
        if row.get("trend") and len(points) <= MAX_TREND_POINTS:
            continue
        trend = parse_etf_trend(
            config,
            row["code"],
            dt.date.fromisoformat(row["trade_date"]),
        )
        if trend:
            row["trend"] = trend
            etf_changed += 1

    benchmark_config = {item["symbol"]: item for item in config.get("benchmarks", [])}
    benchmark_changed = 0
    for row in benchmark_records:
        points = (row.get("trend") or {}).get("points") or []
        if row.get("trend") and len(points) <= MAX_TREND_POINTS:
            continue
        item = benchmark_config.get(row.get("symbol"))
        if not item:
            continue
        trend = parse_benchmark_trend(config, item, dt.date.fromisoformat(row["quote_date"]))
        if trend:
            row["trend"] = trend
            benchmark_changed += 1

    return etf_changed, benchmark_changed


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--data-output", type=Path)
    parser.add_argument("--source-config", type=Path, default=DEFAULT_SOURCE_CONFIG)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--init-only", action="store_true")
    parser.add_argument("--backfill-date")
    parser.add_argument("--backfill-benchmark-date")
    parser.add_argument("--track-date")
    parser.add_argument("--refresh-benchmarks", action="store_true")
    parser.add_argument("--refresh-trends", action="store_true")
    args = parser.parse_args()

    path = args.output.resolve()
    data_path = args.data_output.resolve() if args.data_output else data_path_for_html(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data_path.parent.mkdir(parents=True, exist_ok=True)
    config = load_source_config(args.source_config.resolve())
    now = dt.datetime.now(TZ)

    if args.init_only:
        write_rows(path, data_path, config, [], [])
        print(f"initialized {path} and {data_path}")
        return 0

    if args.refresh_benchmarks:
        try:
            etf_records, benchmark_records = read_records(data_path)
            benchmark_rows = build_benchmark_refresh_rows(config, etf_records, benchmark_records, now)
        except (HTTPError, URLError, TimeoutError, RuntimeError, json.JSONDecodeError, ValueError) as exc:
            print(f"failed: {exc}", file=sys.stderr)
            return 1
        if args.dry_run:
            print(json.dumps({"benchmark_rows": benchmark_rows}, ensure_ascii=False, default=str, indent=2))
            return 0
        _, benchmark_changed = write_rows(path, data_path, config, [], benchmark_rows)
        print(f"refreshed {benchmark_changed} benchmark rows to {path} and {data_path}")
        return 0

    if args.refresh_trends:
        etf_records, benchmark_records = read_records(data_path)
        etf_changed, benchmark_changed = refresh_missing_trends(config, etf_records, benchmark_records)
        write_page_and_data(path, data_path, config, etf_records, benchmark_records)
        print(
            f"refreshed {etf_changed} ETF trend rows and {benchmark_changed} benchmark trend rows "
            f"to {path} and {data_path}"
        )
        return 0

    if args.backfill_benchmark_date:
        try:
            benchmark_rows = build_benchmark_quote_date_rows(
                config,
                dt.date.fromisoformat(args.backfill_benchmark_date),
                now,
                dt.date.fromisoformat(args.track_date) if args.track_date else None,
            )
        except (HTTPError, URLError, TimeoutError, RuntimeError, json.JSONDecodeError, ValueError) as exc:
            print(f"failed: {exc}", file=sys.stderr)
            return 1
        if args.dry_run:
            print(json.dumps({"benchmark_rows": benchmark_rows}, ensure_ascii=False, default=str, indent=2))
            return 0
        _, benchmark_changed = write_rows(path, data_path, config, [], benchmark_rows)
        print(
            f"backfilled {benchmark_changed} benchmark rows "
            f"to {path} and {data_path}"
        )
        return 0

    if args.backfill_date:
        try:
            etf_rows, benchmark_rows = build_backfill_rows(config, dt.date.fromisoformat(args.backfill_date), now)
        except (HTTPError, URLError, TimeoutError, RuntimeError, json.JSONDecodeError, ValueError) as exc:
            print(f"failed: {exc}", file=sys.stderr)
            return 1
        if args.dry_run:
            print(json.dumps({"etf_rows": etf_rows, "benchmark_rows": benchmark_rows}, ensure_ascii=False, default=str, indent=2))
            return 0
        etf_changed, benchmark_changed = write_rows(path, data_path, config, etf_rows, benchmark_rows)
        print(
            f"backfilled {etf_changed} ETF rows and {benchmark_changed} benchmark rows "
            f"to {path} and {data_path}"
        )
        return 0

    try:
        etf_rows, benchmark_rows = build_current_rows(config, now)
    except (HTTPError, URLError, TimeoutError, RuntimeError, json.JSONDecodeError, ValueError) as exc:
        print(f"failed: {exc}", file=sys.stderr)
        return 1

    reason = validate_timing(etf_rows, now, args.force)
    if reason:
        write_rows(path, data_path, config, [], [])
        print(f"skipped: {reason}; html ready at {path}; data ready at {data_path}")
        return 0

    if args.dry_run:
        print(json.dumps({"etf_rows": etf_rows, "benchmark_rows": benchmark_rows}, ensure_ascii=False, default=str, indent=2))
        return 0

    etf_changed, benchmark_changed = write_rows(path, data_path, config, etf_rows, benchmark_rows)
    print(
        f"recorded {etf_changed} ETF rows and {benchmark_changed} benchmark rows "
        f"to {path} and {data_path}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
