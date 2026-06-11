from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import re
import sys
import time
from http.client import RemoteDisconnected
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


APP_DIR = Path(__file__).resolve().parent
DEFAULT_OUTPUT = APP_DIR / "nasdaq_etf_daily_record.html"
DEFAULT_DATA_OUTPUT = APP_DIR / "nasdaq_etf_daily_data.js"
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

HTML_DATA_RE = re.compile(
    r'<script\s+id="{script_id}"\s+type="application/json">(.*?)</script>',
    re.S,
)

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
            if attempt < 2:
                time.sleep(1 + attempt)
    raise RuntimeError(f"request failed after retries: {url}: {last_error}")


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


def yahoo_date(timestamp: int) -> dt.date:
    return dt.datetime.fromtimestamp(timestamp, dt.timezone.utc).date()


def parse_nasdaq_date(value: str) -> dt.date:
    return dt.datetime.strptime(value, "%m/%d/%Y").date()


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
        try:
            nasdaq_points = parse_nasdaq_history(config, item, target_date)
        except RuntimeError:
            nasdaq_points = []
        target_points = [point for point in nasdaq_points if point["date"] == target_date]
        if target_points:
            points.append(target_points[-1])
            points = sorted(points, key=lambda point: point["date"])
            source_ids.add("nasdaq_api_historical")

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

        rows.append(
            {
                "trade_date": (q_time or now).date(),
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


def build_benchmark_rows(
    config: dict,
    track_date: dt.date,
    now: dt.datetime,
    target_date: dt.date | None = None,
) -> list[dict]:
    rows = []
    for item in config.get("benchmarks", []):
        quote_row = parse_benchmark_history(config, item, target_date)
        rows.append(
            {
                "track_date": track_date,
                "recorded_at": now.strftime("%Y-%m-%d %H:%M:%S"),
                **quote_row,
            }
        )
    return rows


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
    normalized.pop("source", None)
    return normalized


def normalize_benchmark_record(row: dict) -> dict:
    normalized = dict(row)
    normalized["source_ids"] = normalized.get("source_ids") or ["yahoo_chart"]
    return normalized


def data_path_for_html(path: Path) -> Path:
    if path == DEFAULT_OUTPUT:
        return DEFAULT_DATA_OUTPUT
    return path.with_name(f"{path.stem}_data.js")


def read_json_script(content: str, script_id: str) -> object | None:
    pattern = re.compile(HTML_DATA_RE.pattern.format(script_id=re.escape(script_id)), re.S)
    match = pattern.search(content)
    if not match:
        return None
    return json.loads(html.unescape(match.group(1)))


def read_data_file(path: Path) -> dict | None:
    if not path.exists():
        return None
    content = path.read_text(encoding="utf-8")
    match = re.search(
        r"window\.NASDAQ_TRACKING_DATA\s*=\s*(\{.*\})\s*;?\s*$",
        content,
        re.S,
    )
    if not match:
        return None
    return json.loads(match.group(1))


def read_records(data_path: Path, html_path: Path) -> tuple[list[dict], list[dict]]:
    data = read_data_file(data_path)
    if isinstance(data, dict):
        return (
            [normalize_etf_record(row) for row in data.get("etf_records", [])],
            [normalize_benchmark_record(row) for row in data.get("benchmark_records", [])],
        )

    if not html_path.exists():
        return [], []
    content = html_path.read_text(encoding="utf-8")
    app_data = read_json_script(content, "app-data")
    if isinstance(app_data, dict):
        etf_records = app_data.get("etf_records", [])
        benchmark_records = app_data.get("benchmark_records", [])
    else:
        etf_records = read_json_script(content, "records-data") or []
        benchmark_records = read_json_script(content, "benchmark-records-data") or []
    return (
        [normalize_etf_record(row) for row in etf_records],
        [normalize_benchmark_record(row) for row in benchmark_records],
    )


def pct_class(value: float) -> str:
    if value > 0:
        return "up"
    if value < 0:
        return "down"
    return "flat"


def fmt_number(value: float, digits: int) -> str:
    return f"{value:.{digits}f}"


def fmt_pct(value: float) -> str:
    return f"{value * 100:.2f}%"


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
            str(row.get("track_date", "")),
            -(symbols.index(row["symbol"]) if row.get("symbol") in symbols else 99),
        ),
        reverse=True,
    )


def render_data_js(etf_records: list[dict], benchmark_records: list[dict], config: dict) -> str:
    payload = {
        "generated_at": dt.datetime.now(TZ).strftime("%Y-%m-%d %H:%M:%S"),
        "etfs": config.get("etfs", []),
        "benchmarks": config.get("benchmarks", []),
        "sources": config.get("sources", []),
        "etf_records": sort_etf_records(etf_records, etf_codes(config)),
        "benchmark_records": sort_benchmark_records(benchmark_records, benchmark_symbols(config)),
    }
    data_json = json.dumps(payload, ensure_ascii=False, indent=2).replace("</", "<\\/")
    return f"window.NASDAQ_TRACKING_DATA = {data_json};\n"


def render_html(data_file_name: str) -> str:
    data_file = html.escape(data_file_name, quote=True)
    return """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>纳指跟踪记录</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f7f8fa;
      --panel: #ffffff;
      --text: #20242a;
      --muted: #667085;
      --line: #d8dde6;
      --header: #263241;
      --up: #067647;
      --down: #067647;
      --flat: #067647;
      --accent: #2f6fed;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font-family: "Microsoft YaHei", Arial, sans-serif;
      font-size: 14px;
      line-height: 1.5;
    }}
    main {{
      width: min(1320px, calc(100% - 32px));
      margin: 24px auto;
    }}
    .top {{
      display: flex;
      align-items: end;
      justify-content: space-between;
      gap: 16px;
      margin-bottom: 18px;
    }}
    h1 {{
      margin: 0 0 4px;
      font-size: 22px;
      font-weight: 700;
      letter-spacing: 0;
    }}
    .section-block {{
      margin-top: 14px;
    }}
    .meta {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      color: var(--muted);
      font-size: 13px;
    }}
    .pill {{
      border: 1px solid var(--line);
      background: var(--panel);
      padding: 4px 8px;
      border-radius: 6px;
      white-space: nowrap;
    }}
    .table-wrap {{
      overflow-x: auto;
      border: 1px solid var(--line);
      background: var(--panel);
    }}
    .drawdown-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 10px;
      margin: 0 0 12px;
    }}
    .drawdown-item {{
      border: 1px solid var(--line);
      background: var(--panel);
      padding: 12px;
    }}
    .drawdown-title {{
      display: flex;
      align-items: baseline;
      justify-content: space-between;
      gap: 10px;
      margin-bottom: 8px;
      font-weight: 700;
    }}
    .drawdown-code {{
      font-family: Consolas, "SFMono-Regular", monospace;
      font-variant-numeric: tabular-nums;
      color: var(--muted);
      font-size: 12px;
    }}
    .drawdown-row {{
      display: flex;
      justify-content: space-between;
      gap: 12px;
      color: var(--muted);
      font-size: 12px;
    }}
    .drawdown-row strong {{
      color: var(--text);
      font-family: Consolas, "SFMono-Regular", monospace;
      font-variant-numeric: tabular-nums;
      font-weight: 700;
    }}
    .drawdown-row-focus {{
      align-items: center;
      margin-top: 8px;
      padding: 8px 10px;
      border: 1px solid #abefc6;
      background: #ecfdf3;
      color: #075e3a;
      font-size: 13px;
      font-weight: 700;
    }}
    .drawdown-row-focus strong {{
      color: #067647;
      font-size: 18px;
      font-weight: 800;
    }}
    .tabs {{
      display: flex;
      align-items: center;
      gap: 6px;
      margin: 16px 0 0;
      border-bottom: 1px solid var(--line);
    }}
    .tab-button {{
      appearance: none;
      border: 1px solid transparent;
      border-bottom: 0;
      background: transparent;
      color: var(--muted);
      cursor: pointer;
      font: inherit;
      font-weight: 600;
      padding: 9px 14px;
      min-height: 38px;
    }}
    .tab-button:hover {{
      color: var(--text);
      background: #eef4ff;
    }}
    .tab-button[aria-selected="true"] {{
      background: var(--panel);
      border-color: var(--line);
      color: var(--accent);
      position: relative;
      top: 1px;
    }}
    .tab-panel[hidden] {{
      display: none;
    }}
    table {{
      width: 100%;
      min-width: 1120px;
      border-collapse: collapse;
    }}
    .compact table {{
      min-width: 900px;
    }}
    th, td {{
      padding: 10px 12px;
      border-bottom: 1px solid var(--line);
      text-align: center;
      white-space: nowrap;
      vertical-align: middle;
    }}
    th {{
      position: sticky;
      top: 0;
      z-index: 1;
      background: var(--header);
      color: #ffffff;
      font-weight: 600;
    }}
    tbody tr:nth-child(even) {{ background: #fbfcfe; }}
    tbody tr:hover {{ background: #eef4ff; }}
    td.num, td.mono {{
      font-family: Consolas, "SFMono-Regular", monospace;
      font-variant-numeric: tabular-nums;
    }}
    td.num {{ text-align: center; }}
    td.date-cell {{
      background: #f3f6fb;
      border-right: 1px solid var(--line);
      font-family: Consolas, "SFMono-Regular", monospace;
      font-variant-numeric: tabular-nums;
      font-weight: 700;
      text-align: center;
      vertical-align: middle;
    }}
    td.source-url {{
      max-width: 520px;
      white-space: normal;
      word-break: break-all;
      color: var(--muted);
      font-size: 12px;
    }}
    .up, .down, .flat {{ color: #067647; font-weight: 700; }}
    .empty td {{
      text-align: center;
      color: var(--muted);
      padding: 28px 12px;
    }}
    .note {{
      margin-top: 10px;
      color: var(--muted);
      font-size: 12px;
    }}
    .data-error {{
      border: 1px solid #fecdca;
      background: #fff1f0;
      color: #b42318;
      padding: 10px 12px;
      margin: 12px 0 0;
    }}
    @media (max-width: 720px) {{
      main {{ width: min(100% - 20px, 1320px); margin: 16px auto; }}
      .top {{ align-items: flex-start; flex-direction: column; }}
      h1 {{ font-size: 20px; }}
      .tabs {{ overflow-x: auto; }}
      .tab-button {{ flex: 0 0 auto; padding: 8px 12px; }}
      th, td {{ padding: 9px 10px; }}
    }}
  </style>
</head>
<body>
  <main>
    <section class="top" aria-label="概览">
      <div>
        <h1>纳指跟踪记录</h1>
        <div class="meta">
          <span class="pill">最新日期：<span id="latest-date">-</span></span>
        </div>
      </div>
      <div class="meta">
        <span class="pill">最近更新：<span id="updated-at">-</span></span>
      </div>
    </section>
    <p id="data-error" class="data-error" hidden></p>
    <nav class="tabs" role="tablist" aria-label="数据表格">
      <button class="tab-button" id="tab-etfs" type="button" role="tab" aria-selected="true" aria-controls="panel-etfs" data-tab-target="etfs">ETF每日记录</button>
      <button class="tab-button" id="tab-benchmarks" type="button" role="tab" aria-selected="false" aria-controls="panel-benchmarks" data-tab-target="benchmarks">QQQ/NDX每日记录</button>
      <button class="tab-button" id="tab-sources" type="button" role="tab" aria-selected="false" aria-controls="panel-sources" data-tab-target="sources">数据源</button>
    </nav>
    <section class="tab-panel" id="panel-etfs" role="tabpanel" aria-labelledby="tab-etfs">
      <section class="section-block" aria-label="A股纳指 ETF 溢价记录">
        <div class="drawdown-grid" id="etf-drawdown-summary"></div>
        <div class="table-wrap">
          <table id="etf-table">
            <thead><tr><th>交易日期</th><th>代码</th><th>名称</th><th>当前价格</th><th>当天涨幅</th><th>T-1估值</th><th>溢价率</th><th>T-1估值日</th><th>数据源</th></tr></thead>
            <tbody id="etf-records-body"><tr class="empty"><td colspan="9">暂无记录</td></tr></tbody>
          </table>
        </div>
      </section>
      <p class="note">ETF 溢价率 = 当前价格 / T-1 估值 - 1。相同交易日期和代码重复运行时更新原行。</p>
    </section>
    <section class="tab-panel" id="panel-benchmarks" role="tabpanel" aria-labelledby="tab-benchmarks" hidden>
      <section class="section-block" aria-label="QQQ / NDX 回撤记录">
        <div class="drawdown-grid" id="benchmark-drawdown-summary"></div>
        <div class="table-wrap">
          <table id="benchmark-table">
            <thead><tr><th>跟踪日期</th><th>标的</th><th>名称</th><th>当前点位/价格</th><th>当天涨幅</th><th>行情日期</th><th>数据源</th></tr></thead>
            <tbody id="benchmark-records-body"><tr class="empty"><td colspan="7">暂无记录</td></tr></tbody>
          </table>
        </div>
      </section>
      <p class="note">QQQ/NDX 摘要默认按 Nasdaq 官方历史行情统计；Yahoo Finance 日线行情仅作为备用源。回撤 = 当前点位或价格 / 历史最高收盘点或价 - 1。</p>
    </section>
    <section class="tab-panel" id="panel-sources" role="tabpanel" aria-labelledby="tab-sources" hidden>
      <section class="section-block" aria-label="数据源">
        <div class="table-wrap compact">
          <table id="source-table">
            <thead><tr><th>数据源</th><th>用途</th><th>接口</th></tr></thead>
            <tbody id="sources-body"><tr class="empty"><td colspan="3">暂无数据源</td></tr></tbody>
          </table>
        </div>
      </section>
    </section>
  </main>
  <script src="__DATA_FILE__"></script>
  <script>
    (() => {
      const data = window.NASDAQ_TRACKING_DATA;
      const errorNode = document.getElementById("data-error");
      const tabButtons = [...document.querySelectorAll("[data-tab-target]")];
      const tabPanels = new Map(
        [...document.querySelectorAll(".tab-panel")].map((panel) => [
          panel.id.replace("panel-", ""),
          panel,
        ])
      );
      const activateTab = (target, updateHash = true) => {
        const activeTarget = tabPanels.has(target) ? target : "etfs";
        tabButtons.forEach((button) => {
          const selected = button.dataset.tabTarget === activeTarget;
          button.setAttribute("aria-selected", String(selected));
          button.tabIndex = selected ? 0 : -1;
        });
        tabPanels.forEach((panel, panelTarget) => {
          panel.hidden = panelTarget !== activeTarget;
        });
        if (updateHash) {
          history.replaceState(null, "", `#${activeTarget}`);
        }
      };
      tabButtons.forEach((button) => {
        button.addEventListener("click", () => activateTab(button.dataset.tabTarget));
        button.addEventListener("keydown", (event) => {
          if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
          event.preventDefault();
          const currentIndex = tabButtons.indexOf(button);
          const nextIndex = event.key === "Home"
            ? 0
            : event.key === "End"
              ? tabButtons.length - 1
              : event.key === "ArrowRight"
                ? (currentIndex + 1) % tabButtons.length
                : (currentIndex - 1 + tabButtons.length) % tabButtons.length;
          tabButtons[nextIndex].focus();
          activateTab(tabButtons[nextIndex].dataset.tabTarget);
        });
      });
      activateTab(location.hash.slice(1) || "etfs", false);
      const setText = (id, value) => {
        const node = document.getElementById(id);
        if (node) {
          node.textContent = value ?? "-";
        }
      };
      const escapeHtml = (value) => String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#39;");
      const pctClass = (value) => value > 0 ? "up" : value < 0 ? "down" : "flat";
      const fmtNumber = (value, digits) => Number(value).toFixed(digits);
      const fmtPct = (value) => `${(Number(value) * 100).toFixed(2)}%`;
      const cell = (value, className = "") => `<td${className ? ` class="${className}"` : ""}>${escapeHtml(value)}</td>`;
      const summaryRow = (label, value, className = "", rowClass = "") => (
        `<div class="drawdown-row${rowClass ? ` ${rowClass}` : ""}"><span>${escapeHtml(label)}</span><strong${className ? ` class="${className}"` : ""}>${escapeHtml(value)}</strong></div>`
      );
      const summaryItem = (title, code, rows) => [
        '<div class="drawdown-item">',
        '<div class="drawdown-title">',
        `<span>${escapeHtml(title)}</span>`,
        `<span class="drawdown-code">${escapeHtml(code)}</span>`,
        '</div>',
        rows.join(""),
        '</div>',
      ].join("");
      const sourceMap = new Map((data?.sources || []).map((item) => [item.id, item]));
      const sourceNames = (ids) => (ids || [])
        .map((id) => sourceMap.get(id)?.name || id)
        .join("；");
      const orderMap = (items, key) => new Map((items || []).map((item, index) => [item[key], index]));
      const sortRows = (rows, dateKey, codeKey, order) => [...(rows || [])].sort((left, right) => {
        const dateCompare = String(right[dateKey] || "").localeCompare(String(left[dateKey] || ""));
        if (dateCompare !== 0) return dateCompare;
        return (order.get(left[codeKey]) ?? 99) - (order.get(right[codeKey]) ?? 99);
      });
      const groupedRows = (records, dateKey, colspan, renderCells) => {
        if (!records.length) {
          return `<tr class="empty"><td colspan="${colspan}">暂无记录</td></tr>`;
        }
        let html = "";
        let index = 0;
        while (index < records.length) {
          const date = records[index][dateKey];
          const group = records.filter((item) => item[dateKey] === date);
          group.forEach((row, groupIndex) => {
            html += "<tr>";
            if (groupIndex === 0) {
              html += `<td class="date-cell" rowspan="${group.length}">${escapeHtml(date)}</td>`;
            }
            html += renderCells(row);
            html += "</tr>";
          });
          index += group.length;
        }
        return html;
      };
      const latestRows = (records, dateKey, codeKey, order) => {
        const latestDate = [...new Set((records || []).map((row) => row[dateKey]).filter(Boolean))]
          .sort()
          .at(-1);
        if (!latestDate) return [];
        return sortRows(records.filter((row) => row[dateKey] === latestDate), dateKey, codeKey, order);
      };
      const renderEtfDrawdownSummary = (records) => {
        const latest = latestRows(records, "trade_date", "code", etfOrder);
        const html = latest.map((row) => {
          const sameCode = records.filter((item) => item.code === row.code);
          const highRow = sameCode.reduce((best, item) => (
            Number(item.price) > Number(best.price) ? item : best
          ), sameCode[0]);
          const drawdown = Number(row.price) / Number(highRow.price) - 1;
          return summaryItem(row.name, row.code, [
            summaryRow("历史最高记录价", `${fmtNumber(highRow.price, 3)} / ${highRow.trade_date}`),
            summaryRow("当天更新价", `${fmtNumber(row.price, 3)} / ${row.trade_date}`),
            summaryRow("回撤", fmtPct(drawdown), pctClass(drawdown), "drawdown-row-focus"),
          ]);
        }).join("");
        document.getElementById("etf-drawdown-summary").innerHTML = html || '<div class="drawdown-item">暂无回撤数据</div>';
      };
      const renderBenchmarkDrawdownSummary = (records) => {
        const latest = latestRows(records, "track_date", "symbol", benchmarkOrder);
        const html = latest.map((row) => summaryItem(row.name, row.symbol, [
          summaryRow("历史最高收盘", `${fmtNumber(row.history_high, 2)} / ${row.history_high_date}`),
          summaryRow("当天更新点", `${fmtNumber(row.value, 2)} / ${row.quote_date}`),
          summaryRow("回撤", fmtPct(row.drawdown), pctClass(Number(row.drawdown)), "drawdown-row-focus"),
        ])).join("");
        document.getElementById("benchmark-drawdown-summary").innerHTML = html || '<div class="drawdown-item">暂无回撤数据</div>';
      };

      if (!data) {
        errorNode.hidden = false;
        errorNode.textContent = "未加载到 nasdaq_etf_daily_data.js，请确认该文件和 HTML 在同一目录。";
        return;
      }

      const etfOrder = orderMap(data.etfs, "code");
      const benchmarkOrder = orderMap(data.benchmarks, "symbol");
      const etfRecords = sortRows(data.etf_records, "trade_date", "code", etfOrder);
      const benchmarkRecords = sortRows(data.benchmark_records, "track_date", "symbol", benchmarkOrder);
      const dates = [...new Set([
        ...etfRecords.map((row) => row.trade_date),
        ...benchmarkRecords.map((row) => row.track_date),
      ].filter(Boolean))];
      const updatedAt = [...etfRecords, ...benchmarkRecords]
        .map((row) => row.recorded_at || "")
        .sort()
        .at(-1) || "-";

      setText("latest-date", dates.sort().at(-1) || "-");
      setText("updated-at", updatedAt);
      renderEtfDrawdownSummary(etfRecords);
      renderBenchmarkDrawdownSummary(benchmarkRecords);

      document.getElementById("etf-records-body").innerHTML = groupedRows(
        etfRecords,
        "trade_date",
        9,
        (row) => [
          cell(row.code, "mono"),
          cell(row.name),
          cell(fmtNumber(row.price, 3), "num"),
          cell(fmtPct(row.daily_change), `num ${pctClass(Number(row.daily_change))}`),
          cell(fmtNumber(row.estimate, 4), "num"),
          cell(fmtPct(row.premium), `num ${pctClass(Number(row.premium))}`),
          cell(row.estimate_time),
          cell(sourceNames(row.source_ids)),
        ].join("")
      );

      document.getElementById("benchmark-records-body").innerHTML = groupedRows(
        benchmarkRecords,
        "track_date",
        7,
        (row) => [
          cell(row.symbol, "mono"),
          cell(row.name),
          cell(fmtNumber(row.value, 2), "num"),
          cell(fmtPct(row.daily_change), `num ${pctClass(Number(row.daily_change))}`),
          cell(row.quote_date),
          cell(sourceNames(row.source_ids)),
        ].join("")
      );

      document.getElementById("sources-body").innerHTML = (data.sources || []).length
        ? data.sources.map((source) => [
          "<tr>",
          cell(source.name),
          cell(source.purpose),
          cell(source.url_template || source.url || "-", "source-url"),
          "</tr>",
        ].join("")).join("")
        : '<tr class="empty"><td colspan="3">暂无数据源</td></tr>';
    })();
  </script>
</body>
</html>
""".replace("__DATA_FILE__", data_file).replace("{{", "{").replace("}}", "}")


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
    etf_records, benchmark_records = read_records(data_path, path)
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
        ("track_date", "symbol"),
    )

    data_path.write_text(render_data_js(etf_records, benchmark_records, config), encoding="utf-8")
    path.write_text(render_html(data_path.name), encoding="utf-8")
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
    benchmark_records: list[dict],
    now: dt.datetime,
) -> list[dict]:
    benchmarks = {item["symbol"]: item for item in config.get("benchmarks", [])}
    rows = []
    for record in benchmark_records:
        item = benchmarks.get(record.get("symbol"))
        if not item:
            continue
        track_date = dt.date.fromisoformat(record["track_date"])
        target_date = benchmark_target_date_for_track_date(track_date)
        quote_row = parse_benchmark_history(config, item, target_date)
        rows.append(
            {
                "track_date": track_date,
                "recorded_at": now.strftime("%Y-%m-%d %H:%M:%S"),
                **quote_row,
            }
        )
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--data-output", type=Path)
    parser.add_argument("--source-config", type=Path, default=DEFAULT_SOURCE_CONFIG)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--init-only", action="store_true")
    parser.add_argument("--backfill-date")
    parser.add_argument("--refresh-benchmarks", action="store_true")
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
            _, benchmark_records = read_records(data_path, path)
            benchmark_rows = build_benchmark_refresh_rows(config, benchmark_records, now)
        except (HTTPError, URLError, TimeoutError, RuntimeError, json.JSONDecodeError, ValueError) as exc:
            print(f"failed: {exc}", file=sys.stderr)
            return 1
        if args.dry_run:
            print(json.dumps({"benchmark_rows": benchmark_rows}, ensure_ascii=False, default=str, indent=2))
            return 0
        _, benchmark_changed = write_rows(path, data_path, config, [], benchmark_rows)
        print(f"refreshed {benchmark_changed} benchmark rows to {path} and {data_path}")
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
