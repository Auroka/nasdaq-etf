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
from urllib.request import Request, urlopen


CODES = ("513100", "159501", "159659")
APP_DIR = Path(__file__).resolve().parent
DEFAULT_OUTPUT = APP_DIR / "nasdaq_etf_daily_record.html"
TZ = dt.timezone(dt.timedelta(hours=8), "Asia/Shanghai")
TINYRIGHT_URL = "https://n.tinyright.com/"
EASTMONEY_URL = (
    "https://push2.eastmoney.com/api/qt/ulist.np/get"
    "?fltt=2&fields=f12,f14,f2,f3,f13,f124&secids=1.513100,0.159501,0.159659"
)
EASTMONEY_KLINE_URL = (
    "https://push2his.eastmoney.com/api/qt/stock/kline/get"
    "?secid={secid}&fields1=f1,f2,f3,f4,f5,f6"
    "&fields2=f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61"
    "&klt=101&fqt=1&beg={date}&end={date}"
)
HEADERS = [
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
DATA_RE = re.compile(
    r'<script\s+id="records-data"\s+type="application/json">(.*?)</script>',
    re.S,
)


def fetch_text(url: str) -> str:
    req = Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html,application/json;q=0.9,*/*;q=0.8",
        },
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
    value = value.replace(",", "").replace("%", "").strip()
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


def parse_table_rows(raw: str) -> dict[str, dict]:
    result = {}
    for row_match in re.finditer(r"<tr[^>]*>.*?</tr>", raw, re.S):
        cells = [clean_cell(cell) for cell in re.findall(r"<td[^>]*>(.*?)</td>", row_match.group(0), re.S)]
        if len(cells) < 15 or cells[1] not in CODES:
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


def parse_tinyright() -> dict[str, dict]:
    raw = fetch_text(TINYRIGHT_URL)
    table_rows = parse_table_rows(raw)
    if all(code in table_rows for code in CODES):
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
                for code in CODES
            }
        except (ValueError, json.JSONDecodeError) as exc:
            last_error = exc

    raise RuntimeError(f"failed to parse n.tinyright data: {last_error}")


def parse_tinyright_t1() -> dict[str, dict]:
    raw = fetch_text(TINYRIGHT_URL)
    candidates = []
    for value in (raw, html.unescape(raw)):
        candidates.append(value)
        candidates.append(value.replace('\\"', '"'))

    last_error: Exception | None = None
    for value in candidates:
        try:
            rows = extract_json_array(value, "t1Data")
            return {row["code"]: row for row in rows if row.get("code") in CODES}
        except (ValueError, json.JSONDecodeError) as exc:
            last_error = exc
    raise RuntimeError(f"failed to parse n.tinyright t1 data: {last_error}")


def parse_eastmoney() -> dict[str, dict]:
    data = json.loads(fetch_text(EASTMONEY_URL))
    rows = data.get("data", {}).get("diff") or []
    return {row.get("f12"): row for row in rows if row.get("f12")}


def secid_for_code(code: str) -> str:
    market = "1" if code.startswith("5") else "0"
    return f"{market}.{code}"


def parse_eastmoney_kline(code: str, trade_date: dt.date) -> dict:
    date_text = trade_date.strftime("%Y%m%d")
    url = EASTMONEY_KLINE_URL.format(secid=secid_for_code(code), date=date_text)
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


def build_rows(now: dt.datetime) -> list[dict]:
    tinyright = parse_tinyright()
    try:
        eastmoney = parse_eastmoney()
    except (RuntimeError, json.JSONDecodeError):
        eastmoney = {}
    rows = []

    for code in CODES:
        quote = eastmoney.get(code, {})
        market = tinyright[code]["market"]
        realtime = tinyright[code]["realtime"]

        price = as_float(quote.get("f2")) or as_float(market.get("price"))
        daily_change = as_float(quote.get("f3"))
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
        q_time = quote_time(quote) or parse_datetime(market.get("datetime")) or e_time
        premium = as_float(realtime.get("premium"))
        if premium is None:
            premium = price / estimate - 1
        source = "Eastmoney quote; n.tinyright T-1 valuation" if quote else "n.tinyright quote and T-1 valuation"

        rows.append(
            {
                "trade_date": (q_time or now).date(),
                "recorded_at": now.strftime("%Y-%m-%d %H:%M:%S"),
                "code": code,
                "name": quote.get("f14") or market.get("name") or code,
                "price": price,
                "daily_change": daily_change / 100,
                "estimate": estimate,
                "premium": premium,
                "quote_time": q_time.strftime("%Y-%m-%d %H:%M:%S") if q_time else "",
                "estimate_time": estimate_time,
                "source": source,
                "quote_date": q_time.date() if q_time else None,
                "estimate_date": e_time.date() if e_time else None,
            }
        )

    return rows


def build_backfill_rows(trade_date: dt.date, now: dt.datetime) -> list[dict]:
    t1_data = parse_tinyright_t1()
    rows = []

    for code in CODES:
        quote = parse_eastmoney_kline(code, trade_date)
        valuation = t1_data.get(code)
        if not valuation:
            raise RuntimeError(f"{code} has no T-1 valuation")

        valuation_date = dt.date.fromisoformat(valuation["t1_date"])

        estimate = float(valuation["t1"])
        price = quote["close"]
        rows.append(
            {
                "trade_date": trade_date,
                "recorded_at": now.strftime("%Y-%m-%d %H:%M:%S"),
                "code": code,
                "name": quote["name"],
                "price": price,
                "daily_change": quote["daily_change"],
                "estimate": estimate,
                "premium": price / estimate - 1,
                "quote_time": f"{trade_date.isoformat()} 15:00:00",
                "estimate_time": valuation_date.isoformat(),
                "source": "Eastmoney historical K-line; n.tinyright T-1 valuation",
                "quote_date": trade_date,
                "estimate_date": valuation_date,
            }
        )

    return rows


def public_row(item: dict) -> dict:
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
        "quote_time": item["quote_time"],
        "estimate_time": item["estimate_time"],
        "source": item["source"],
    }


def read_records(path: Path) -> list[dict]:
    if not path.exists():
        return []
    content = path.read_text(encoding="utf-8")
    match = DATA_RE.search(content)
    if not match:
        return []
    return json.loads(html.unescape(match.group(1)))


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


def render_cell(value: object, class_name: str = "") -> str:
    class_attr = f' class="{class_name}"' if class_name else ""
    return f"<td{class_attr}>{html.escape(str(value))}</td>"


def render_html(records: list[dict]) -> str:
    records = sorted(
        records,
        key=lambda row: (
            str(row.get("trade_date", "")),
            -(CODES.index(row["code"]) if row.get("code") in CODES else 99),
        ),
        reverse=True,
    )
    latest_date = records[0]["trade_date"] if records else "-"
    updated_at = records[0]["recorded_at"] if records else "-"
    data_json = json.dumps(records, ensure_ascii=False, indent=2).replace("</", "<\\/")

    if records:
        row_parts = []
        current_date = None
        date_group_size = 0
        date_group_index = 0

        for row in records:
            if row["trade_date"] != current_date:
                current_date = row["trade_date"]
                date_group_size = sum(1 for item in records if item["trade_date"] == current_date)
                date_group_index = 0
            else:
                date_group_index += 1

            cells = ["<tr>"]
            if date_group_index == 0:
                cells.append(
                    f'<td class="date-cell" rowspan="{date_group_size}">'
                    f'{html.escape(str(row["trade_date"]))}</td>'
                )
            cells.extend(
                [
                    render_cell(row["code"], "mono"),
                    render_cell(row["name"]),
                    render_cell(fmt_number(float(row["price"]), 3), "num"),
                    render_cell(fmt_pct(float(row["daily_change"])), f'num {pct_class(float(row["daily_change"]))}'),
                    render_cell(fmt_number(float(row["estimate"]), 4), "num"),
                    render_cell(fmt_pct(float(row["premium"])), f'num {pct_class(float(row["premium"]))}'),
                    render_cell(row["estimate_time"]),
                    render_cell(row["source"]),
                    "</tr>",
                ]
            )
            row_parts.append("".join(cells))

        rows_html = "\n".join(row_parts)
    else:
        rows_html = f'<tr class="empty"><td colspan="{len(HEADERS)}">暂无记录</td></tr>'

    headers_html = "".join(f"<th>{html.escape(header)}</th>" for header in HEADERS)
    total_days = len({row["trade_date"] for row in records})

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>纳指 ETF 日记录</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f7f8fa;
      --panel: #ffffff;
      --text: #20242a;
      --muted: #667085;
      --line: #d8dde6;
      --header: #263241;
      --up: #b42318;
      --down: #067647;
      --flat: #475467;
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
      width: min(1280px, calc(100% - 32px));
      margin: 24px auto;
    }}
    .top {{
      display: flex;
      align-items: end;
      justify-content: space-between;
      gap: 16px;
      margin-bottom: 14px;
    }}
    h1 {{
      margin: 0 0 4px;
      font-size: 22px;
      font-weight: 700;
      letter-spacing: 0;
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
    table {{
      width: 100%;
      min-width: 1120px;
      border-collapse: collapse;
    }}
    th, td {{
      padding: 10px 12px;
      border-bottom: 1px solid var(--line);
      text-align: left;
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
    td.num {{ text-align: right; }}
    td.date-cell {{
      background: #f3f6fb;
      border-right: 1px solid var(--line);
      font-family: Consolas, "SFMono-Regular", monospace;
      font-variant-numeric: tabular-nums;
      font-weight: 700;
      text-align: center;
      vertical-align: middle;
    }}
    .up {{ color: var(--up); font-weight: 600; }}
    .down {{ color: var(--down); font-weight: 600; }}
    .flat {{ color: var(--flat); }}
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
    @media (max-width: 720px) {{
      main {{ width: min(100% - 20px, 1280px); margin: 16px auto; }}
      .top {{ align-items: flex-start; flex-direction: column; }}
      h1 {{ font-size: 20px; }}
      th, td {{ padding: 9px 10px; }}
    }}
  </style>
</head>
<body>
  <main>
    <section class="top" aria-label="概览">
      <div>
        <h1>纳指 ETF 日记录</h1>
        <div class="meta">
          <span class="pill">最新交易日：{html.escape(str(latest_date))}</span>
          <span class="pill">记录数：{len(records)}</span>
          <span class="pill">交易日数：{total_days}</span>
        </div>
      </div>
      <div class="meta">
        <span class="pill">最近更新：{html.escape(str(updated_at))}</span>
      </div>
    </section>
    <section class="table-wrap" aria-label="记录表">
      <table>
        <thead><tr>{headers_html}</tr></thead>
        <tbody>
{rows_html}
        </tbody>
      </table>
    </section>
    <p class="note">溢价率 = 当前价格 / T-1 估值 - 1。相同交易日期和代码重复运行时更新原行。</p>
  </main>
  <script id="records-data" type="application/json">{data_json}</script>
</body>
</html>
"""


def write_rows(path: Path, rows: list[dict]) -> int:
    records = read_records(path)
    existing = {
        (str(row.get("trade_date")), str(row.get("code"))): idx
        for idx, row in enumerate(records)
    }

    changed = 0
    for item in rows:
        row = public_row(item)
        key = (row["trade_date"], row["code"])
        if key in existing:
            records[existing[key]] = row
        else:
            existing[key] = len(records)
            records.append(row)
        changed += 1

    path.write_text(render_html(records), encoding="utf-8")
    return changed


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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--init-only", action="store_true")
    parser.add_argument("--backfill-date")
    args = parser.parse_args()

    path = args.output.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    now = dt.datetime.now(TZ)

    if args.init_only:
        write_rows(path, [])
        print(f"initialized {path}")
        return 0

    if args.backfill_date:
        try:
            rows = build_backfill_rows(dt.date.fromisoformat(args.backfill_date), now)
        except (HTTPError, URLError, TimeoutError, RuntimeError, json.JSONDecodeError, ValueError) as exc:
            print(f"failed: {exc}", file=sys.stderr)
            return 1
        if args.dry_run:
            print(json.dumps(rows, ensure_ascii=False, default=str, indent=2))
            return 0
        changed = write_rows(path, rows)
        print(f"backfilled {changed} rows to {path}")
        return 0

    try:
        rows = build_rows(now)
    except (HTTPError, URLError, TimeoutError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"failed: {exc}", file=sys.stderr)
        return 1

    reason = validate_timing(rows, now, args.force)
    if reason:
        write_rows(path, [])
        print(f"skipped: {reason}; html ready at {path}")
        return 0

    if args.dry_run:
        print(json.dumps(rows, ensure_ascii=False, default=str, indent=2))
        return 0

    changed = write_rows(path, rows)
    print(f"recorded {changed} rows to {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
