#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""纳指跟踪项目的数据存储层：读取每日记录、写入 JSON / manifest / 页面壳。

从已废弃的 record_nasdaq_etf.py 中抽离，只保留「读记录 + 写文件」这类纯 I/O 逻辑，
不包含任何取数代码。日常取数与补全入口仍为 fetch_nasdaq_data.py。

数据布局
--------
    data/manifest.json                       索引（生成时间、标的、数据源、每日文件）
    data/daily-records/YYYY/MM/YYYY-MM-DD.json  单日记录（ETF 按 trade_date、
                                                QQQ/NDX 按 quote_date 归档）
    index.html                               页面壳（由 React 渲染 assets/app.js）
"""
from __future__ import annotations

import datetime as dt
import html
import json
import os
import re
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
DEFAULT_OUTPUT = APP_DIR / "index.html"
DATA_DIR = APP_DIR / "data"
DEFAULT_DATA_OUTPUT = DATA_DIR / "manifest.json"
DAILY_RECORDS_DIR_NAME = "daily-records"
LEGACY_JSON_OUTPUT = DATA_DIR / "nasdaq_etf_daily_data.json"
LEGACY_JS_OUTPUT = APP_DIR / "nasdaq_etf_daily_data.js"
TZ = dt.timezone(dt.timedelta(hours=8), "Asia/Shanghai")

LEGACY_SOURCE_IDS = {
    "Eastmoney quote": ["eastmoney_quote"],
    "Eastmoney historical K-line": ["eastmoney_kline"],
    "existing historical quote": ["manual_historical_quote"],
}


# ---------------------------------------------------------------------------
# 排序用的标的顺序
# ---------------------------------------------------------------------------
def etf_codes(config: dict) -> tuple[str, ...]:
    return tuple(item["code"] for item in config.get("etfs", []))


def benchmark_symbols(config: dict) -> tuple[str, ...]:
    return tuple(item["symbol"] for item in config.get("benchmarks", []))


# ---------------------------------------------------------------------------
# 行规范化
# ---------------------------------------------------------------------------
def infer_legacy_source_ids(source_text: str) -> list[str]:
    if source_text in LEGACY_SOURCE_IDS:
        return LEGACY_SOURCE_IDS[source_text]
    if not source_text:
        return []
    return ["manual_historical_quote"]


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
        "source_ids": item.get("source_ids", []),
        "trend": item.get("trend"),
    }


def normalize_etf_record(row: dict) -> dict:
    normalized = dict(row)
    normalized["source_ids"] = normalized.get("source_ids") or infer_legacy_source_ids(normalized.get("source", ""))
    normalized["trend"] = normalized.get("trend")
    normalized.pop("source", None)
    return normalized


def normalize_benchmark_record(row: dict) -> dict:
    normalized = dict(row)
    normalized["source_ids"] = normalized.get("source_ids") or []
    normalized["trend"] = normalized.get("trend")
    return normalized


# ---------------------------------------------------------------------------
# 读取
# ---------------------------------------------------------------------------
def load_json_or_legacy_js(path: Path) -> dict:
    content = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        return json.loads(content)

    match = re.search(r"window\.NASDAQ_TRACKING_DATA\s*=\s*(\{.*\})\s*;?\s*$", content, re.S)
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


# ---------------------------------------------------------------------------
# 分组与渲染
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# 写入
# ---------------------------------------------------------------------------
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
    existing = {tuple(str(row.get(field)) for field in key_fields): idx for idx, row in enumerate(records)}
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
    """按 (trade_date, code) / (quote_date, symbol) 覆盖写入，并重建 manifest 与页面壳。"""
    etf_records, benchmark_records = read_records(data_path)

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
