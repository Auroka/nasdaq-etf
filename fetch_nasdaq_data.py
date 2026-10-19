#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""自动补全纳指跟踪数据（3 只 A 股纳指 ETF + QQQ/NDX）。

设计目标
--------
1. 幂等：随时可运行，只补「按市场日历应该存在但还没记录」的数据，已有记录不重写。
2. 完整：写入前先把所有目标日的数据全部取到并交叉校验，任何一天失败则整体不写，
   避免出现「一半是新数据、一半是空档」的残缺状态。
3. 准确：每个关键数值至少两个独立来源交叉校验。
   - ETF 收盘价：新浪日 K（主）+ 腾讯日 K（校验）+ 东财日 K（仲裁）
   - ETF 净值：东财官方净值（主）+ tinyright IOPV（校验）+ 指数推算（兜底）
   - QQQ/NDX：Nasdaq 官方历史（主）+ 新浪美股日 K（校验）+ 全历史最高收盘

时间规则（北京时间）
--------------------
- A 股 15:00 收盘前运行：不记录当天的 ETF，只补 QQQ/NDX（取最近一个已收盘的美股交易日）。
- A 股 15:00 收盘后运行：记录当天 ETF + 最近一个已收盘的美股交易日。
- 非交易日运行：不产生 ETF 行；QQQ/NDX 按美股日历照常补。
- 美股某交易日 q 视为「已收盘可用」的条件：北京时间 >= (q+1) 06:00。

数据口径（与项目既有约定一致）
------------------------------
- ETF：estimate(D) = 最近一个中国交易日的基金净值（D 的前一中国交易日）。
- ETF：premium = price / estimate - 1。
- QQQ/NDX：按 quote_date（美股行情日）归档；track_date = quote_date 之后第一个中国交易日。
- history_high 取「截至 quote_date 的最高收盘」，不使用盘中最高价。

用法
----
    python fetch_nasdaq_data.py                # 自动补全（默认）
    python fetch_nasdaq_data.py --dry-run      # 只取数校验，不写文件
    python fetch_nasdaq_data.py --check        # 只做本地数据体检，不发网络请求
    python fetch_nasdaq_data.py --date 2026-10-15   # 强制重录某个中国交易日
    python fetch_nasdaq_data.py --json         # 机器可读结果（进度走 stderr）
"""
from __future__ import annotations

import argparse
import json
import re
import ssl
import sys
import time
import urllib.request
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, time as clock_time, timedelta, timezone
from http.client import RemoteDisconnected
from pathlib import Path
from typing import Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import quote

import record_nasdaq_etf as project

APP_DIR = Path(__file__).resolve().parent
DATA_MANIFEST = APP_DIR / "data" / "manifest.json"
INDEX_HTML = APP_DIR / "index.html"
SOURCE_CONFIG = APP_DIR / "data_sources.json"

TZ = timezone(timedelta(hours=8), "Asia/Shanghai")
A_SHARE_CLOSE = clock_time(15, 0)
# 美股 16:00 ET 收盘 ≈ 北京时间次日 04:00(夏令时)/05:00(冬令时)，统一留到 06:00 才算可用。
US_SETTLE_BUFFER = timedelta(hours=6)

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

HEADERS_SINA_CN = {"Referer": "https://finance.sina.com.cn/"}
HEADERS_TENCENT = {"Referer": "https://gu.qq.com/"}
HEADERS_EASTMONEY = {"Referer": "https://quote.eastmoney.com/"}
HEADERS_FUND = {"Referer": "https://fundf10.eastmoney.com/"}
HEADERS_NASDAQ = {
    "Accept": "application/json, text/plain, */*",
    "Origin": "https://www.nasdaq.com",
    "Referer": "https://www.nasdaq.com/",
}

# 交叉校验容差
PRICE_TOLERANCE = 0.0005          # ETF 收盘价，元
US_PRICE_TOLERANCE = 0.01         # QQQ 价格
US_INDEX_TOLERANCE = 0.5          # NDX 点位
PREMIUM_AUDIT_TOLERANCE = 1e-3    # 历史记录里存在源端四舍五入，体检只报提示


class DataError(RuntimeError):
    """取数或校验失败。"""


# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------
def http_text(
    url: str,
    *,
    headers: dict | None = None,
    retries: int = 4,
    timeout: int = 25,
    http_fallback: bool = False,
) -> str:
    """带重试与 HTTP 降级的 GET。

    东财 push2 域名在部分网络下 HTTPS 会被直接断连，HTTP 反而可用，故提供降级。
    """
    candidates = [url]
    if http_fallback and url.startswith("https://"):
        candidates.append("http://" + url[len("https://") :])

    last_error: Exception | None = None
    for attempt in range(retries):
        for candidate in candidates:
            request = urllib.request.Request(
                candidate,
                headers={"User-Agent": USER_AGENT, "Accept": "*/*", **(headers or {})},
            )
            try:
                with urllib.request.urlopen(request, timeout=timeout, context=ssl.create_default_context()) as response:
                    raw = response.read()
                    charset = response.headers.get_content_charset() or "utf-8"
                    return raw.decode(charset, "replace")
            except (HTTPError, URLError, TimeoutError, OSError, RemoteDisconnected) as exc:
                last_error = exc
        if attempt < retries - 1:
            time.sleep(0.6 * (attempt + 1))
    raise DataError(f"请求失败（{retries} 次重试）：{url} :: {last_error}")


def parse_jsonp_array(text: str) -> list:
    match = re.search(r"=\((\[.*\])\);?\s*$", text, re.S)
    if not match:
        raise DataError("响应不是预期的 JSONP 数组")
    return json.loads(match.group(1))


# ---------------------------------------------------------------------------
# 数据模型
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Bar:
    day: date
    close: float


@dataclass
class ProjectData:
    etf_records: list[dict]
    benchmark_records: list[dict]


def load_project_data() -> ProjectData:
    try:
        etf_records, benchmark_records = project.read_records(DATA_MANIFEST)
    except FileNotFoundError as exc:
        raise DataError(f"数据索引或每日文件缺失：{exc}") from exc
    except (json.JSONDecodeError, ValueError) as exc:
        raise DataError(f"数据文件解析失败：{exc}") from exc
    return ProjectData(etf_records, benchmark_records)


def load_config() -> dict:
    return json.loads(SOURCE_CONFIG.read_text(encoding="utf-8"))


def etf_codes(config: dict) -> list[str]:
    return [item["code"] for item in config.get("etfs", [])]


def etf_names(config: dict) -> dict[str, str]:
    return {item["code"]: item["name"] for item in config.get("etfs", [])}


def benchmarks(config: dict) -> list[dict]:
    return list(config.get("benchmarks", []))


# ---------------------------------------------------------------------------
# 行情源：A 股 ETF
# ---------------------------------------------------------------------------
def cn_symbol(code: str) -> str:
    return f"sh{code}" if code.startswith("5") else f"sz{code}"


def fetch_cn_bars_sina(code: str, count: int = 400) -> dict[date, Bar]:
    symbol = cn_symbol(code)
    url = (
        "https://quotes.sina.cn/cn/api/jsonp_v2.php/var%20_"
        f"{symbol}_240=/CN_MarketData.getKLineData?symbol={symbol}&scale=240&ma=no&datalen={count}"
    )
    rows = parse_jsonp_array(http_text(url, headers=HEADERS_SINA_CN))
    bars: dict[date, Bar] = {}
    for row in rows:
        try:
            bars[date.fromisoformat(str(row["day"])[:10])] = Bar(
                date.fromisoformat(str(row["day"])[:10]), float(row["close"])
            )
        except (KeyError, TypeError, ValueError):
            continue
    if not bars:
        raise DataError(f"{code} 新浪日 K 为空")
    return bars


def fetch_cn_bars_tencent(code: str, count: int = 400) -> dict[date, Bar]:
    symbol = cn_symbol(code)
    url = f"https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param={symbol},day,,,{count},"
    payload = json.loads(http_text(url, headers=HEADERS_TENCENT))
    node = (payload.get("data") or {}).get(symbol) or {}
    rows = node.get("day") or node.get("qfqday") or []
    bars: dict[date, Bar] = {}
    for row in rows:
        try:
            day = date.fromisoformat(str(row[0]))
            bars[day] = Bar(day, float(row[2]))
        except (IndexError, TypeError, ValueError):
            continue
    if not bars:
        raise DataError(f"{code} 腾讯日 K 为空")
    return bars


def fetch_cn_bars_eastmoney(code: str, start: date, end: date) -> dict[date, Bar]:
    market = "1" if code.startswith("5") else "0"
    url = (
        "https://push2his.eastmoney.com/api/qt/stock/kline/get"
        f"?secid={market}.{code}"
        "&fields1=f1,f2,f3,f4,f5,f6"
        "&fields2=f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61"
        f"&klt=101&fqt=1&beg={start.strftime('%Y%m%d')}&end={end.strftime('%Y%m%d')}"
    )
    payload = json.loads(http_text(url, headers=HEADERS_EASTMONEY, http_fallback=True))
    rows = ((payload.get("data") or {}).get("klines")) or []
    bars: dict[date, Bar] = {}
    for line in rows:
        fields = str(line).split(",")
        if len(fields) < 3:
            continue
        try:
            day = date.fromisoformat(fields[0])
            bars[day] = Bar(day, float(fields[2]))
        except ValueError:
            continue
    return bars


def fetch_tencent_quote(code: str) -> dict:
    """腾讯实时行情：收盘后 price 即当日收盘价；同时给出昨收，可用于校验涨幅。"""
    symbol = cn_symbol(code)
    text = http_text(f"https://qt.gtimg.cn/q={symbol}", headers=HEADERS_TENCENT)
    match = re.search(r'"(.*)"', text, re.S)
    if not match:
        raise DataError(f"{code} 腾讯行情为空")
    fields = match.group(1).split("~")
    if len(fields) < 33:
        raise DataError(f"{code} 腾讯行情字段不足")
    try:
        return {
            "price": float(fields[3]),
            "prev_close": float(fields[4]),
            "timestamp": fields[30],
            "change_pct": float(fields[32]),
        }
    except ValueError as exc:
        raise DataError(f"{code} 腾讯行情解析失败") from exc


# ---------------------------------------------------------------------------
# 行情源：ETF 净值
# ---------------------------------------------------------------------------
def fetch_nav_history(code: str, start: date, end: date) -> dict[date, float]:
    """东财基金历史净值（官方 DWJZ），按 20 条/页翻页。"""
    result: dict[date, float] = {}
    page = 1
    while page <= 40:
        url = (
            "https://api.fund.eastmoney.com/f10/lsjz?callback="
            f"&fundCode={code}&pageIndex={page}&pageSize=20"
            f"&startDate={start.isoformat()}&endDate={end.isoformat()}"
        )
        payload = json.loads(http_text(url, headers=HEADERS_FUND, http_fallback=True))
        rows = ((payload.get("Data") or {}).get("LSJZList")) or []
        if not rows:
            break
        for row in rows:
            try:
                result[date.fromisoformat(row["FSRQ"])] = float(row["DWJZ"])
            except (KeyError, TypeError, ValueError):
                continue
        oldest = date.fromisoformat(rows[-1]["FSRQ"])
        if len(rows) < 20 or oldest <= start:
            break
        page += 1
    return result


def fetch_tinyright() -> dict[str, dict]:
    """tinyright 的 IOPV（官方净值镜像）与 T-1 估值，仅用于校验/兜底。"""
    try:
        raw = http_text("https://n.tinyright.com/", timeout=20)
    except DataError:
        return {}
    text = raw.replace('\\"', '"')
    snapshot: dict[str, dict] = {}
    for key in ("iopvData", "t1Data"):
        match = re.search(r'"%s":(\[.*?\])\s*[,}]' % key, text, re.S)
        if not match:
            continue
        try:
            rows = json.loads(match.group(1))
        except json.JSONDecodeError:
            continue
        for row in rows:
            code = row.get("code")
            if not code:
                continue
            item = snapshot.setdefault(code, {})
            if key == "iopvData":
                item["iopv"] = row.get("iopv")
                item["iopv_date"] = row.get("date")
            else:
                item["t1"] = row.get("t1")
                item["t1_date"] = row.get("t1_date")
    return snapshot


# ---------------------------------------------------------------------------
# 行情源：QQQ / NDX
# ---------------------------------------------------------------------------
def fetch_us_history_nasdaq(symbol: str, assetclass: str, start: date, end: date) -> dict[date, float]:
    url = (
        f"https://api.nasdaq.com/api/quote/{quote(symbol, safe='')}/historical"
        f"?assetclass={assetclass}&fromdate={start.isoformat()}&todate={end.isoformat()}&limit=9999"
    )
    payload = json.loads(http_text(url, headers=HEADERS_NASDAQ, retries=5))
    status = payload.get("status") or {}
    if status.get("rCode") != 200:
        raise DataError(f"{symbol} Nasdaq 历史行情错误：{status}")
    rows = (((payload.get("data") or {}).get("tradesTable")) or {}).get("rows") or []
    series: dict[date, float] = {}
    for row in rows:
        try:
            day = datetime.strptime(str(row["date"]), "%m/%d/%Y").date()
            series[day] = float(str(row["close"]).replace(",", ""))
        except (KeyError, TypeError, ValueError):
            continue
    if not series:
        raise DataError(f"{symbol} Nasdaq 历史行情为空")
    return series


def fetch_us_history_sina(symbol: str) -> dict[date, float]:
    url = (
        "https://stock.finance.sina.com.cn/usstock/api/jsonp.php/var%20_x="
        f"/US_MinKService.getDailyK?symbol={quote(symbol, safe='')}&___qn=3"
    )
    rows = parse_jsonp_array(http_text(url, headers=HEADERS_SINA_CN, timeout=40))
    series: dict[date, float] = {}
    for row in rows:
        try:
            series[date.fromisoformat(str(row["d"])[:10])] = float(row["c"])
        except (KeyError, TypeError, ValueError):
            continue
    return series


# ---------------------------------------------------------------------------
# 日历与计划
# ---------------------------------------------------------------------------
def previous_trading_day(days: Iterable[date], target: date) -> date | None:
    candidates = [day for day in days if day < target]
    return max(candidates) if candidates else None


def next_trading_day(days: Iterable[date], target: date) -> date | None:
    candidates = [day for day in days if day > target]
    return min(candidates) if candidates else None


def next_weekday(target: date) -> date:
    candidate = target + timedelta(days=1)
    while candidate.weekday() >= 5:
        candidate += timedelta(days=1)
    return candidate


def latest_complete_us_day(us_days: list[date], now: datetime) -> date:
    """美股某日 q 收盘后，北京时间次日 06:00 起才算可用。"""
    cutoff = (now - US_SETTLE_BUFFER).date() - timedelta(days=1)
    candidates = [day for day in us_days if day <= cutoff]
    if not candidates:
        raise DataError("美股日历为空，无法确定最近可用交易日")
    return max(candidates)


def etf_target_end(cn_days: list[date], now: datetime) -> date | None:
    today = now.date()
    candidates = [
        day
        for day in cn_days
        if day < today or (day == today and now.time() >= A_SHARE_CLOSE)
    ]
    return max(candidates) if candidates else None


@dataclass
class Plan:
    cn_days: list[date]
    us_days: list[date]
    etf_targets: list[date]
    benchmark_targets: list[date]
    etf_end: date | None
    us_end: date
    etf_expected_range: tuple[date, date] | None
    us_expected_range: tuple[date, date]

    def as_dict(self) -> dict:
        return {
            "cn_calendar_range": [self.cn_days[0].isoformat(), self.cn_days[-1].isoformat()],
            "us_calendar_range": [self.us_days[0].isoformat(), self.us_days[-1].isoformat()],
            "etf_targets": [day.isoformat() for day in self.etf_targets],
            "benchmark_targets": [day.isoformat() for day in self.benchmark_targets],
            "etf_expected_end": self.etf_end.isoformat() if self.etf_end else None,
            "us_expected_end": self.us_end.isoformat(),
        }


def build_plan(
    config: dict,
    data: ProjectData,
    cn_days: list[date],
    us_days: list[date],
    now: datetime,
    since: date | None = None,
) -> Plan:
    codes = etf_codes(config)
    symbols = {item["symbol"] for item in benchmarks(config)}

    etf_by_day: dict[str, set[str]] = defaultdict(set)
    for row in data.etf_records:
        etf_by_day[str(row.get("trade_date"))].add(str(row.get("code")))

    bm_by_day: dict[str, set[str]] = defaultdict(set)
    for row in data.benchmark_records:
        bm_by_day[str(row.get("quote_date"))].add(str(row.get("symbol")))

    etf_end = etf_target_end(cn_days, now)
    us_end = latest_complete_us_day(us_days, now)

    recorded_etf_days = sorted(date.fromisoformat(day) for day in etf_by_day if day and day != "None")
    recorded_bm_days = sorted(date.fromisoformat(day) for day in bm_by_day if day and day != "None")

    etf_start = since or (recorded_etf_days[0] if recorded_etf_days else (etf_end or us_end) - timedelta(days=10))
    bm_start = since or (recorded_bm_days[0] if recorded_bm_days else us_end - timedelta(days=10))

    etf_targets = [
        day
        for day in cn_days
        if etf_end and etf_start <= day <= etf_end and etf_by_day.get(day.isoformat(), set()) != set(codes)
    ]
    benchmark_targets = [
        day
        for day in us_days
        if bm_start <= day <= us_end and bm_by_day.get(day.isoformat(), set()) != symbols
    ]

    return Plan(
        cn_days=cn_days,
        us_days=us_days,
        etf_targets=etf_targets,
        benchmark_targets=benchmark_targets,
        etf_end=etf_end,
        us_end=us_end,
        etf_expected_range=(etf_start, etf_end) if etf_end else None,
        us_expected_range=(bm_start, us_end),
    )


# ---------------------------------------------------------------------------
# 行构造
# ---------------------------------------------------------------------------
def pick_close(
    code: str,
    day: date,
    sina: dict[date, Bar],
    tencent: dict[date, Bar],
    *,
    allow_tencent_only: bool,
) -> tuple[float, list[str]]:
    """取收盘价并做双源校验；不一致时用东财仲裁。"""
    sina_bar = sina.get(day)
    tencent_bar = tencent.get(day)

    if sina_bar and sina_bar.close <= 0:
        sina_bar = None
    if tencent_bar and tencent_bar.close <= 0:
        tencent_bar = None

    if sina_bar and tencent_bar:
        if abs(sina_bar.close - tencent_bar.close) > PRICE_TOLERANCE:
            arbitrated = arbitrate_close(code, day, sina_bar.close, tencent_bar.close)
            return arbitrated, ["eastmoney_kline"]
        return sina_bar.close, ["sina_daily_kline", "tencent_kline"]

    if sina_bar:
        return sina_bar.close, ["sina_daily_kline"]
    if tencent_bar and allow_tencent_only:
        return tencent_bar.close, ["tencent_kline"]
    raise DataError(f"{code} 在 {day} 没有可用收盘价（新浪/腾讯均缺失）")


def arbitrate_close(code: str, day: date, sina_close: float, tencent_close: float) -> float:
    try:
        eastmoney = fetch_cn_bars_eastmoney(code, day, day)
    except (DataError, json.JSONDecodeError, ValueError) as exc:
        raise DataError(
            f"{code} {day} 新浪({sina_close})与腾讯({tencent_close})收盘不一致，且东财仲裁失败：{exc}"
        ) from exc
    em_close = eastmoney.get(day)
    if em_close is None:
        raise DataError(f"{code} {day} 新浪({sina_close})与腾讯({tencent_close})不一致，东财无当日数据")
    if abs(em_close.close - sina_close) <= PRICE_TOLERANCE:
        return sina_close
    if abs(em_close.close - tencent_close) <= PRICE_TOLERANCE:
        return tencent_close
    raise DataError(
        f"{code} {day} 三源收盘价不一致：新浪 {sina_close} / 腾讯 {tencent_close} / 东财 {em_close.close}"
    )


def index_ratio(us_series: dict[date, float], target: date, base: date) -> float:
    """纳指点位比值：取 <= 目标日 / <= 基准日 的最近收盘。"""
    target_days = [day for day in us_series if day <= target]
    base_days = [day for day in us_series if day <= base]
    if not target_days or not base_days:
        raise DataError(f"纳指历史不足以计算 {base} → {target} 的比值")
    return us_series[max(target_days)] / us_series[max(base_days)]


def resolve_estimate(
    code: str,
    trade_day: date,
    cn_days: list[date],
    nav_history: dict[date, float],
    tiny: dict[str, dict],
    us_series: dict[date, float],
) -> tuple[float, str, date]:
    """estimate(D) = 最近一个中国交易日的官方净值；未公布时按纳指涨跌推算。"""
    nav_day = previous_trading_day(cn_days, trade_day)
    if nav_day is None:
        raise DataError(f"{code} {trade_day} 找不到前一中国交易日")

    if nav_day in nav_history:
        return nav_history[nav_day], "eastmoney_fund_nav", nav_day

    tiny_item = tiny.get(code) or {}
    if str(tiny_item.get("iopv_date") or "") == nav_day.isoformat() and tiny_item.get("iopv"):
        return float(tiny_item["iopv"]), "tinyright_iopv", nav_day

    published_days = [day for day in nav_history if day <= nav_day]
    if not published_days:
        raise DataError(f"{code} 在 {nav_day} 及之前没有任何已公布净值")
    base_day = max(published_days)
    derived = nav_history[base_day] * index_ratio(us_series, nav_day, base_day)

    if str(tiny_item.get("t1_date") or "") == nav_day.isoformat() and tiny_item.get("t1"):
        tiny_value = float(tiny_item["t1"])
        if derived and abs(tiny_value / derived - 1) > 0.005:
            log(
                f"  [提示] {code} {nav_day} 净值推算({derived:.4f})与 tinyright T-1({tiny_value:.4f})"
                f"偏差超过 0.5%，采用 tinyright 值"
            )
        return tiny_value, "tinyright_t1", nav_day
    return derived, "derived_nav", nav_day


@dataclass
class MarketContext:
    """行情日历与价格序列；净值数据按需在计划确定后再拉取，避免无谓翻页。"""

    config: dict
    cn_sina: dict[str, dict[date, Bar]]
    cn_tencent: dict[str, dict[date, Bar]]
    us_nasdaq: dict[str, dict[date, float]]
    us_sina: dict[str, dict[date, float]]
    cn_days: list[date]
    us_days: list[date]


@dataclass
class FetchContext(MarketContext):
    nav_history: dict[str, dict[date, float]]
    tiny: dict[str, dict]


def build_etf_rows(targets: list[date], ctx: FetchContext, now: datetime) -> list[dict]:
    names = etf_names(ctx.config)
    rows: list[dict] = []
    for trade_day in targets:
        for code in etf_codes(ctx.config):
            sina = ctx.cn_sina[code]
            tencent = ctx.cn_tencent[code]
            close, price_sources = pick_close(
                code,
                trade_day,
                sina,
                tencent,
                allow_tencent_only=trade_day == now.date(),
            )
            previous_day = previous_trading_day(sina.keys(), trade_day) or previous_trading_day(
                tencent.keys(), trade_day
            )
            if previous_day is None:
                raise DataError(f"{code} {trade_day} 缺少前一交易日收盘，无法计算涨幅")
            previous_close = (sina.get(previous_day) or tencent.get(previous_day))
            if previous_close is None:
                raise DataError(f"{code} {trade_day} 前一交易日 {previous_day} 无收盘价")
            daily_change = close / previous_close.close - 1

            estimate, nav_source, nav_day = resolve_estimate(
                code,
                trade_day,
                ctx.cn_days,
                ctx.nav_history[code],
                ctx.tiny,
                ctx.us_nasdaq.get("NDX") or next(iter(ctx.us_nasdaq.values())),
            )
            premium = close / estimate - 1

            rows.append(
                {
                    "trade_date": trade_day,
                    "recorded_at": now.strftime("%Y-%m-%d %H:%M:%S"),
                    "code": code,
                    "name": names.get(code, code),
                    "price": close,
                    "daily_change": daily_change,
                    "estimate": estimate,
                    "premium": premium,
                    "source_ids": price_sources + [nav_source],
                    "trend": None,
                    "_nav_date": nav_day.isoformat(),
                }
            )
    return rows


def build_benchmark_rows(targets: list[date], ctx: FetchContext, now: datetime) -> list[dict]:
    rows: list[dict] = []
    qqq_changes: dict[date, float] = {}
    ndx_changes: dict[date, float] = {}

    for quote_day in targets:
        track_day = next_trading_day(ctx.cn_days, quote_day)
        if track_day is None:
            track_day = next_weekday(quote_day)
            log(f"  [提示] {quote_day} 之后没有已知中国交易日，track_date 暂用 {track_day}")

        for item in benchmarks(ctx.config):
            symbol = item["symbol"]
            primary = ctx.us_nasdaq[symbol]
            secondary = ctx.us_sina[symbol]
            if quote_day not in primary:
                raise DataError(f"{symbol} 缺少 {quote_day} 收盘价（Nasdaq）")

            close = primary[quote_day]
            if quote_day in secondary:
                tolerance = US_PRICE_TOLERANCE if symbol == "QQQ" else US_INDEX_TOLERANCE
                if abs(secondary[quote_day] - close) > tolerance:
                    raise DataError(
                        f"{symbol} {quote_day} 两源不一致：Nasdaq {close} / 新浪 {secondary[quote_day]}"
                    )
                sources = ["nasdaq_api_historical", "sina_us_daily"]
            else:
                sources = ["nasdaq_api_historical"]

            days = sorted(primary)
            index = days.index(quote_day)
            if index == 0:
                raise DataError(f"{symbol} {quote_day} 缺少前一日收盘，无法计算涨幅")
            daily_change = close / primary[days[index - 1]] - 1

            candidates = [(day, value) for day, value in primary.items() if day <= quote_day]
            candidates += [(day, value) for day, value in secondary.items() if day <= quote_day]
            high_day, high_value = max(candidates, key=lambda pair: pair[1])
            if high_value < close:
                high_day, high_value = quote_day, close

            rows.append(
                {
                    "track_date": track_day,
                    "recorded_at": now.strftime("%Y-%m-%d %H:%M:%S"),
                    "symbol": symbol,
                    "name": item.get("name", symbol),
                    "value": close,
                    "daily_change": daily_change,
                    "history_high": high_value,
                    "drawdown": close / high_value - 1,
                    "history_high_date": high_day,
                    "quote_date": quote_day,
                    "unit": item.get("unit", ""),
                    "source_ids": sources,
                    "trend": None,
                }
            )
            (qqq_changes if symbol == "QQQ" else ndx_changes)[quote_day] = daily_change

    for quote_day, change in qqq_changes.items():
        ndx_change = ndx_changes.get(quote_day)
        if ndx_change is not None and abs(change - ndx_change) > 0.015:
            log(f"  [提示] {quote_day} QQQ({change:+.2%}) 与 NDX({ndx_change:+.2%}) 涨幅差异偏大，请留意")
    return rows


# ---------------------------------------------------------------------------
# 校验
# ---------------------------------------------------------------------------
def validate_rows(etf_rows: list[dict], benchmark_rows: list[dict]) -> list[str]:
    problems: list[str] = []

    for row in etf_rows:
        code = row["code"]
        if row["price"] <= 0:
            problems.append(f"{row['trade_date']} {code} 价格异常：{row['price']}")
        if row["estimate"] <= 0:
            problems.append(f"{row['trade_date']} {code} 净值异常：{row['estimate']}")
        if abs(row["premium"] - (row["price"] / row["estimate"] - 1)) > 1e-12:
            problems.append(f"{row['trade_date']} {code} 溢价率复算不一致")
        if abs(row["daily_change"]) > 0.2:
            problems.append(f"{row['trade_date']} {code} 日涨幅异常：{row['daily_change']:.2%}")
        if not row["source_ids"]:
            problems.append(f"{row['trade_date']} {code} 缺少数据源标记")

    for row in benchmark_rows:
        symbol = row["symbol"]
        if row["value"] <= 0 or row["history_high"] <= 0:
            problems.append(f"{row['quote_date']} {symbol} 价格/历史最高异常")
        if row["history_high"] < row["value"] - 1e-9:
            problems.append(f"{row['quote_date']} {symbol} 历史最高小于当前收盘")
        if abs(row["drawdown"] - (row["value"] / row["history_high"] - 1)) > 1e-12:
            problems.append(f"{row['quote_date']} {symbol} 回撤复算不一致")
        if abs(row["daily_change"]) > 0.25:
            problems.append(f"{row['quote_date']} {symbol} 日涨幅异常：{row['daily_change']:.2%}")

    return problems


def audit_data(
    data: ProjectData,
    plan: Plan,
    config: dict,
) -> tuple[list[str], dict]:
    """按市场日历检查每个应有记录的日期是否齐全。"""
    codes = set(etf_codes(config))
    symbols = {item["symbol"] for item in benchmarks(config)}
    problems: list[str] = []
    summary: dict = {}

    etf_by_day: dict[str, dict[str, dict]] = defaultdict(dict)
    for row in data.etf_records:
        key = str(row.get("trade_date"))
        etf_by_day[key][str(row.get("code"))] = row

    if plan.etf_expected_range:
        start, end = plan.etf_expected_range
        expected_days = [day for day in plan.cn_days if start <= day <= end]
        missing_days = []
        for day in expected_days:
            rows = etf_by_day.get(day.isoformat(), {})
            if set(rows) != codes:
                missing_days.append(
                    {"date": day.isoformat(), "found": sorted(rows), "missing": sorted(codes - set(rows))}
                )
            for row in rows.values():
                price = row.get("price")
                estimate = row.get("estimate")
                premium = row.get("premium")
                if not price or not estimate or premium is None:
                    problems.append(f"ETF {day} {row.get('code')} 价格/净值/溢价率为空")
                    continue
                if abs(premium - (price / estimate - 1)) > PREMIUM_AUDIT_TOLERANCE:
                    problems.append(
                        f"ETF {day} {row.get('code')} 溢价率与 price/estimate-1 偏差过大"
                        f"（记录 {premium:.6f}）"
                    )
        summary["etf_expected_days"] = len(expected_days)
        summary["etf_missing_days"] = missing_days

    bm_by_day: dict[str, dict[str, dict]] = defaultdict(dict)
    for row in data.benchmark_records:
        bm_by_day[str(row.get("quote_date"))][str(row.get("symbol"))] = row

    start, end = plan.us_expected_range
    expected_us_days = [day for day in plan.us_days if start <= day <= end]
    missing_us = []
    for day in expected_us_days:
        rows = bm_by_day.get(day.isoformat(), {})
        if set(rows) != symbols:
            missing_us.append(
                {"date": day.isoformat(), "found": sorted(rows), "missing": sorted(symbols - set(rows))}
            )
        for row in rows.values():
            if row.get("history_high") and row.get("value") and row["history_high"] < row["value"] - 1e-9:
                problems.append(f"BM {day} {row.get('symbol')} 历史最高小于当前收盘")
    summary["us_expected_days"] = len(expected_us_days)
    summary["us_missing_days"] = missing_us

    # 重复键
    etf_keys = [(row.get("trade_date"), row.get("code")) for row in data.etf_records]
    duplicates = {key for key in etf_keys if etf_keys.count(key) > 1}
    if duplicates:
        problems.append(f"ETF 存在重复键：{sorted(duplicates)}")

    summary["etf_records"] = len(data.etf_records)
    summary["benchmark_records"] = len(data.benchmark_records)
    return problems, summary


def audit_local(data: ProjectData) -> tuple[list[str], dict]:
    """不发网络请求的本地体检：字段完整性 + 溢价率复算 + 重复键。"""
    problems: list[str] = []
    for row in data.etf_records:
        try:
            price = float(row["price"])
            estimate = float(row["estimate"])
            premium = float(row["premium"])
        except (KeyError, TypeError, ValueError):
            problems.append(f"ETF {row.get('trade_date')} {row.get('code')} 字段缺失")
            continue
        if price <= 0 or estimate <= 0:
            problems.append(f"ETF {row.get('trade_date')} {row.get('code')} 价格/净值非正数")
        if abs(premium - (price / estimate - 1)) > PREMIUM_AUDIT_TOLERANCE:
            problems.append(f"ETF {row.get('trade_date')} {row.get('code')} 溢价率偏差过大")

    for row in data.benchmark_records:
        try:
            value = float(row["value"])
            high = float(row["history_high"])
            drawdown = float(row["drawdown"])
        except (KeyError, TypeError, ValueError):
            problems.append(f"BM {row.get('quote_date')} {row.get('symbol')} 字段缺失")
            continue
        if high < value - 1e-9:
            problems.append(f"BM {row.get('quote_date')} {row.get('symbol')} 历史最高小于当前值")
        if abs(drawdown - (value / high - 1)) > 1e-6:
            problems.append(f"BM {row.get('quote_date')} {row.get('symbol')} 回撤偏差过大")

    etf_keys = [(row.get("trade_date"), row.get("code")) for row in data.etf_records]
    if len(etf_keys) != len(set(etf_keys)):
        problems.append("ETF 存在重复键")
    bm_keys = [(row.get("quote_date"), row.get("symbol")) for row in data.benchmark_records]
    if len(bm_keys) != len(set(bm_keys)):
        problems.append("BM 存在重复键")

    return problems, {
        "etf_records": len(data.etf_records),
        "benchmark_records": len(data.benchmark_records),
        "etf_days": len({row.get("trade_date") for row in data.etf_records}),
        "benchmark_days": len({row.get("quote_date") for row in data.benchmark_records}),
    }


# ---------------------------------------------------------------------------
# 写入
# ---------------------------------------------------------------------------
def write_rows(etf_rows: list[dict], benchmark_rows: list[dict], config: dict) -> tuple[int, int]:
    """复用项目既有写入器，保证 JSON / manifest / index.html 格式一致。

    写入器会整文件重写 index.html，从而抹掉用户侧手工加上的属性；
    这里先备份、写完再恢复，避免把无关改动带进 diff。
    """
    html_backup = INDEX_HTML.read_text(encoding="utf-8") if INDEX_HTML.exists() else None

    clean_etf_rows = [{key: value for key, value in row.items() if not key.startswith("_")} for row in etf_rows]
    etf_changed, benchmark_changed = project.write_rows(
        INDEX_HTML, DATA_MANIFEST, config, clean_etf_rows, benchmark_rows
    )

    if html_backup is not None and INDEX_HTML.read_text(encoding="utf-8") != html_backup:
        INDEX_HTML.write_text(html_backup, encoding="utf-8")
        log("  [写入] index.html 已恢复为运行前版本（保留用户侧改动）")
    return etf_changed, benchmark_changed


# ---------------------------------------------------------------------------
# 入口
# ---------------------------------------------------------------------------
QUIET = False
JSON_MODE = False


def log(message: str) -> None:
    if QUIET:
        return
    print(message, file=sys.stderr if JSON_MODE else sys.stdout, flush=True)


def emit(payload: dict) -> None:
    if JSON_MODE:
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))


def parse_now(value: str | None) -> datetime:
    if not value:
        return datetime.now(TZ)
    return datetime.strptime(value, "%Y-%m-%d %H:%M").replace(tzinfo=TZ)


def optional_source(label: str, factory, default):
    """次要数据源：失败只告警，不阻断主流程。"""
    try:
        return factory()
    except (DataError, json.JSONDecodeError, ValueError) as exc:
        log(f"  [警告] {label} 不可用（{exc}），本次跳过该源")
        return default


def build_market_context(config: dict, now: datetime) -> MarketContext:
    codes = etf_codes(config)
    log("[取数] A 股 ETF 日 K（新浪主源 / 腾讯校验）")
    cn_sina = {code: fetch_cn_bars_sina(code) for code in codes}
    cn_tencent = {
        code: optional_source(f"{code} 腾讯日 K", lambda c=code: fetch_cn_bars_tencent(c), {})
        for code in codes
    }

    log("[取数] A 股交易日历")
    calendar_days: set[date] = set()
    for bars in cn_sina.values():
        calendar_days.update(bars)
    for bars in cn_tencent.values():
        calendar_days.update(bars)
    cn_days = sorted(calendar_days)

    log("[取数] QQQ / NDX 历史（Nasdaq 官方主源 / 新浪美股校验）")
    us_nasdaq = {
        item["symbol"]: fetch_us_history_nasdaq(
            item.get("nasdaq_symbol") or item["symbol"],
            item.get("nasdaq_assetclass") or "index",
            date(1999, 1, 1),
            now.date(),
        )
        for item in benchmarks(config)
    }
    us_sina = {
        item["symbol"]: optional_source(
            f"{item['symbol']} 新浪美股日 K",
            lambda i=item: fetch_us_history_sina(i.get("sina_symbol") or i["symbol"]),
            {},
        )
        for item in benchmarks(config)
    }
    # 美股日历：取所有基准标的都有数据的交易日（QQQ 历史比 NDX 短，取交集更稳）
    day_sets = [set(series) for series in us_nasdaq.values() if series]
    us_days = sorted(set.intersection(*day_sets)) if day_sets else []
    if not us_days:
        raise DataError("无法建立美股交易日历（Nasdaq 历史行情为空）")

    return MarketContext(
        config=config,
        cn_sina=cn_sina,
        cn_tencent=cn_tencent,
        us_nasdaq=us_nasdaq,
        us_sina=us_sina,
        cn_days=cn_days,
        us_days=us_days,
    )


def with_nav_data(market: MarketContext, nav_start: date, now: datetime) -> FetchContext:
    codes = etf_codes(market.config)
    log(f"[取数] ETF 官方净值（东财，{nav_start} → {now.date()}）")
    nav_history = {code: fetch_nav_history(code, nav_start, now.date()) for code in codes}
    log("[取数] tinyright 快照（校验/兜底）")
    tiny = fetch_tinyright()
    return FetchContext(
        config=market.config,
        cn_sina=market.cn_sina,
        cn_tencent=market.cn_tencent,
        us_nasdaq=market.us_nasdaq,
        us_sina=market.us_sina,
        cn_days=market.cn_days,
        us_days=market.us_days,
        nav_history=nav_history,
        tiny=tiny,
    )


def main() -> int:
    global QUIET, JSON_MODE, INDEX_HTML, DATA_MANIFEST

    parser = argparse.ArgumentParser(description="自动补全纳指跟踪数据")
    parser.add_argument("--dry-run", action="store_true", help="只取数并校验，不写文件")
    parser.add_argument("--check", action="store_true", help="只做本地数据体检（不发网络请求）")
    parser.add_argument("--date", help="强制重录某个中国交易日（YYYY-MM-DD）")
    parser.add_argument("--since", help="审计/补全的起始日期（YYYY-MM-DD）")
    parser.add_argument("--now", help="以指定时间模拟运行（YYYY-MM-DD HH:MM，测试用）")
    parser.add_argument("--json", action="store_true", help="输出 JSON 结果（进度走 stderr）")
    parser.add_argument("--quiet", action="store_true", help="只输出最终摘要")
    parser.add_argument("--output", type=Path, default=INDEX_HTML, help="页面壳输出路径（测试用）")
    parser.add_argument("--data-output", type=Path, default=DATA_MANIFEST, help="数据索引路径（测试用）")
    args = parser.parse_args()

    INDEX_HTML = args.output.resolve()
    DATA_MANIFEST = args.data_output.resolve()

    JSON_MODE = args.json
    QUIET = args.quiet
    now = parse_now(args.now)

    config = load_config()
    data = load_project_data()

    if args.check:
        problems, summary = audit_local(data)
        log(f"[体检] ETF {summary['etf_records']} 行 / {summary['etf_days']} 天；"
            f"基准 {summary['benchmark_records']} 行 / {summary['benchmark_days']} 天")
        if problems:
            log(f"[体检] 发现 {len(problems)} 个问题：")
            for problem in problems:
                log(f"  - {problem}")
        else:
            log("[体检] 未发现字段/口径问题")
        emit({"ok": not problems, "mode": "check", "summary": summary, "problems": problems})
        return 0 if not problems else 1

    since = date.fromisoformat(args.since) if args.since else None

    market = build_market_context(config, now)
    log(
        f"[日历] A 股 {len(market.cn_days)} 个交易日（{market.cn_days[0]} → {market.cn_days[-1]}）；"
        f"美股 {len(market.us_days)} 个交易日（{market.us_days[0]} → {market.us_days[-1]}）"
    )

    plan: Plan | None = None
    # 指定日期：只处理该中国交易日 + 其对应的美股行情日
    if args.date:
        target = date.fromisoformat(args.date)
        if target not in market.cn_days:
            raise DataError(f"{target} 不是已知的中国交易日")
        us_target = previous_trading_day(market.us_days, target)
        if us_target is None:
            raise DataError(f"{target} 之前没有可用的美股交易日")
        etf_targets = [target]
        benchmark_targets = [us_target]
        log(f"[计划] 指定日期模式：ETF {target}；基准 quote_date {us_target}")
    else:
        plan = build_plan(config, data, market.cn_days, market.us_days, now, since)
        log(f"[计划] 当前 {now:%Y-%m-%d %H:%M}（A 股{'已' if now.time() >= A_SHARE_CLOSE else '未'}收盘）")
        log(f"[计划] ETF 目标日 {len(plan.etf_targets)} 个：{[day.isoformat() for day in plan.etf_targets] or '无'}")
        log(f"[计划] 基准目标日 {len(plan.benchmark_targets)} 个：{[day.isoformat() for day in plan.benchmark_targets] or '无'}")
        etf_targets = plan.etf_targets
        benchmark_targets = plan.benchmark_targets

    # 净值只拉到目标区间之前一点即可，避免整段历史翻页。
    if etf_targets:
        nav_start = min(etf_targets) - timedelta(days=45)
    elif since:
        nav_start = since - timedelta(days=45)
    else:
        nav_start = (market.cn_days[-1] if market.cn_days else now.date()) - timedelta(days=45)

    ctx = with_nav_data(market, nav_start, now) if etf_targets else None

    etf_rows = build_etf_rows(etf_targets, ctx, now) if etf_targets and ctx else []
    benchmark_rows = build_benchmark_rows(benchmark_targets, market, now) if benchmark_targets else []

    problems = validate_rows(etf_rows, benchmark_rows)
    if problems:
        log(f"[校验] 失败，发现 {len(problems)} 个问题（不会写入任何数据）：")
        for problem in problems:
            log(f"  - {problem}")
        emit({"ok": False, "mode": "write", "problems": problems})
        return 1

    if args.dry_run:
        log("[预览] --dry-run 不写文件。将要写入的行：")
        for row in etf_rows:
            log(
                f"  ETF {row['trade_date']} {row['code']} {row['name']} "
                f"price={row['price']} chg={row['daily_change']:+.2%} "
                f"est={row['estimate']:.4f}({row['_nav_date']}) prem={row['premium']:.2%} "
                f"src={','.join(row['source_ids'])}"
            )
        for row in benchmark_rows:
            log(
                f"  BM  {row['quote_date']} {row['symbol']} value={row['value']} "
                f"chg={row['daily_change']:+.2%} high={row['history_high']}@{row['history_high_date']} "
                f"dd={row['drawdown']:+.2%} track={row['track_date']} src={','.join(row['source_ids'])}"
            )
        emit(
            {
                "ok": True,
                "mode": "dry-run",
                "plan": plan.as_dict() if plan else None,
                "etf_rows": etf_rows,
                "benchmark_rows": benchmark_rows,
            }
        )
        return 0

    if not etf_rows and not benchmark_rows:
        plan_for_audit = build_plan(config, data, market.cn_days, market.us_days, now, since)
        audit_problems, audit_summary = audit_data(data, plan_for_audit, config)
        noop_ok = not audit_problems and not audit_summary.get("etf_missing_days") and not audit_summary.get(
            "us_missing_days"
        )
        log("[结果] 没有需要补的数据（已是最新且完整）" if noop_ok else "[结果] 没有新目标日，但审计发现问题")
        emit(
            {
                "ok": noop_ok,
                "mode": "noop",
                "plan": plan.as_dict() if plan else None,
                "summary": audit_summary,
                "problems": audit_problems,
            }
        )
        return 0 if noop_ok else 1

    etf_changed, benchmark_changed = write_rows(etf_rows, benchmark_rows, config)
    log(f"[写入] ETF {etf_changed} 行 / 基准 {benchmark_changed} 行")

    # 写后重新按磁盘内容审计，确保「执行完即完整」
    refreshed = load_project_data()
    plan_for_audit = build_plan(config, refreshed, market.cn_days, market.us_days, now, since)
    audit_problems, audit_summary = audit_data(refreshed, plan_for_audit, config)

    missing_etf = audit_summary.get("etf_missing_days") or []
    missing_us = audit_summary.get("us_missing_days") or []
    log(
        f"[审计] ETF {audit_summary.get('etf_expected_days', 0)} 个应有交易日，"
        f"缺失 {len(missing_etf)} 天；"
        f"基准 {audit_summary.get('us_expected_days', 0)} 个应有交易日，缺失 {len(missing_us)} 天"
    )
    for item in missing_etf:
        log(f"  [缺口] ETF {item['date']} 缺 {item['missing']}")
    for item in missing_us:
        log(f"  [缺口] BM  {item['date']} 缺 {item['missing']}")
    for problem in audit_problems:
        log(f"  [问题] {problem}")

    ok = not missing_etf and not missing_us and not audit_problems
    log("[结果] 数据完整 ✓" if ok else "[结果] 数据仍不完整 ✗")

    emit(
        {
            "ok": ok,
            "mode": "write",
            "plan": plan.as_dict() if plan else None,
            "written": {"etf_rows": etf_changed, "benchmark_rows": benchmark_changed},
            "etf_rows": etf_rows,
            "benchmark_rows": benchmark_rows,
            "summary": audit_summary,
            "problems": audit_problems + [f"缺口 {item}" for item in missing_etf + missing_us],
        }
    )
    return 0 if ok else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except DataError as exc:
        print(f"failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
