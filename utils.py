"""Utility helpers for the stock scrapper."""
from __future__ import annotations

import datetime as dt
import logging
from typing import Any, Dict, Iterable, Optional
from urllib.parse import urlparse

from dateutil import parser as date_parser
from dateutil import tz


UTC = tz.tzutc()


def setup_logger(name: str, level: str = "INFO") -> logging.Logger:
    """Configure and return a module-level logger."""
    logger = logging.getLogger(name)
    if logger.handlers:
        # Respect existing handlers if configured by main.
        return logger
    logger.setLevel(level.upper())
    handler = logging.StreamHandler()
    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger


def parse_datetime(value: Any) -> Optional[dt.datetime]:
    """Parse a datetime string or object into a timezone-aware UTC datetime."""
    if value is None:
        return None
    if isinstance(value, dt.datetime):
        dt_obj = value
    else:
        try:
            dt_obj = date_parser.parse(str(value))
        except (ValueError, TypeError):
            return None
    if dt_obj.tzinfo is None:
        dt_obj = dt_obj.replace(tzinfo=UTC)
    return dt_obj.astimezone(UTC)


def parse_gdelt_datetime(value: str) -> Optional[dt.datetime]:
    """Parse GDELT datetime strings like '20240201235900' into UTC."""
    if not value:
        return None
    try:
        dt_obj = dt.datetime.strptime(value, "%Y%m%d%H%M%S")
    except ValueError:
        return None
    return dt_obj.replace(tzinfo=UTC)


def normalize_text(text: Optional[str]) -> str:
    """Normalize text for comparisons."""
    return (text or "").strip().lower()


def dedupe_items(items: Iterable[Dict[str, Any]], key_fields: Iterable[str]) -> list[Dict[str, Any]]:
    """Remove duplicates based on a tuple of key fields."""
    seen = set()
    unique_items: list[Dict[str, Any]] = []
    for item in items:
        key = tuple(normalize_text(item.get(field)) for field in key_fields)
        if key in seen:
            continue
        seen.add(key)
        unique_items.append(item)
    return unique_items


def url_domain(url: Optional[str]) -> str:
    """Extract domain from a URL."""
    if not url:
        return ""
    try:
        parsed = urlparse(url)
        return parsed.netloc.lower()
    except Exception:
        return ""


def safe_float(value: Any, default: float = 0.0) -> float:
    """Cast a value to float safely."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def clamp(value: float, min_value: float, max_value: float) -> float:
    """Clamp a numeric value to a range."""
    return max(min_value, min(max_value, value))


def pct_change(current: float, previous: float) -> float:
    """Compute percentage change with guard for zero."""
    if previous == 0:
        return 0.0
    return (current - previous) / previous


def moving_average(series, window: int):
    """Simple moving average wrapper for pandas Series."""
    return series.rolling(window=window).mean()


def ema(series, span: int):
    """Exponential moving average wrapper for pandas Series."""
    return series.ewm(span=span, adjust=False).mean()


def today_utc() -> dt.datetime:
    """Return current UTC timestamp."""
    return dt.datetime.now(tz=UTC)


def summarize_missing(data: Dict[str, Any]) -> list[str]:
    """Return a list of missing keys for user-facing reporting."""
    return [key for key, value in data.items() if value in (None, "", [], {})]
