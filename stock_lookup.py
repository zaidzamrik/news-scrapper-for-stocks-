"""Lookup helpers for resolving stock names into tickers via the SEC company list."""
from __future__ import annotations

import re
import time
from typing import Any, Dict, Optional

import requests

from utils import normalize_text, setup_logger


SEC_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
SEC_HEADERS = {
    "User-Agent": "stock-research-assistant/1.0 research@example.com",
    "Accept-Encoding": "gzip, deflate",
}
COMMON_SUFFIXES = (
    " inc",
    " corp",
    " corporation",
    " ltd",
    " limited",
    " plc",
    " llc",
    " holdings",
    " holding",
    " group",
    " sa",
    " nv",
)
_CACHE_TTL_SECONDS = 60 * 60 * 12
_company_cache: Dict[str, Any] = {"loaded_at": 0.0, "records": []}


def resolve_security_input(query: str, logger=None) -> Dict[str, str]:
    """Resolve a ticker or company name into a canonical ticker and display name."""
    logger = logger or setup_logger(__name__)
    cleaned_query = (query or "").strip()
    if not cleaned_query:
        return {"input": "", "ticker": "", "company_name": "", "matched": ""}

    records = _load_company_records(logger)
    if not records:
        return {
            "input": cleaned_query,
            "ticker": cleaned_query.upper(),
            "company_name": cleaned_query,
            "matched": "fallback",
        }

    exact_ticker = _match_exact_ticker(cleaned_query, records)
    if exact_ticker:
        return exact_ticker

    exact_name = _match_company_name(cleaned_query, records)
    if exact_name:
        return exact_name

    partial_name = _match_company_name(cleaned_query, records, partial=True)
    if partial_name:
        return partial_name

    return {
        "input": cleaned_query,
        "ticker": cleaned_query.upper(),
        "company_name": cleaned_query,
        "matched": "fallback",
    }


def search_securities(query: str, limit: int = 8, logger=None) -> list[Dict[str, str]]:
    """Return ticker/company suggestions for autocomplete without affecting the analysis flow."""
    logger = logger or setup_logger(__name__)
    cleaned_query = (query or "").strip()
    if not cleaned_query:
        return []

    records = _load_company_records(logger)
    if not records:
        return []

    normalized_query = _normalize_company_name(cleaned_query)
    ticker_query = cleaned_query.upper()
    suggestions: list[Dict[str, str]] = []

    for record in records:
        company_name = record["company_name"]
        ticker = record["ticker"]
        normalized_name = record["normalized_name"]

        if ticker.startswith(ticker_query) or normalized_name.startswith(normalized_query):
            suggestions.append({"ticker": ticker, "company_name": company_name})
        elif normalized_query and normalized_query in normalized_name:
            suggestions.append({"ticker": ticker, "company_name": company_name})

        if len(suggestions) >= limit:
            break

    return suggestions


def _load_company_records(logger) -> list[Dict[str, str]]:
    now = time.time()
    if _company_cache["records"] and now - _company_cache["loaded_at"] < _CACHE_TTL_SECONDS:
        return _company_cache["records"]

    try:
        response = requests.get(SEC_TICKERS_URL, headers=SEC_HEADERS, timeout=20)
        response.raise_for_status()
        data = response.json()
    except Exception as exc:  # pragma: no cover - network dependent
        logger.warning("SEC ticker lookup failed: %s", exc)
        return _company_cache["records"]

    records: list[Dict[str, str]] = []
    for item in data.values():
        ticker = str(item.get("ticker", "")).strip().upper()
        company_name = str(item.get("title", "")).strip()
        if not ticker or not company_name:
            continue
        records.append(
            {
                "ticker": ticker,
                "company_name": company_name,
                "normalized_name": _normalize_company_name(company_name),
            }
        )

    _company_cache["records"] = records
    _company_cache["loaded_at"] = now
    return records


def _match_exact_ticker(query: str, records: list[Dict[str, str]]) -> Optional[Dict[str, str]]:
    ticker_query = query.strip().upper()
    for record in records:
        if record["ticker"] == ticker_query:
            return {
                "input": query,
                "ticker": record["ticker"],
                "company_name": record["company_name"],
                "matched": "ticker",
            }
    return None


def _match_company_name(
    query: str,
    records: list[Dict[str, str]],
    partial: bool = False,
) -> Optional[Dict[str, str]]:
    normalized_query = _normalize_company_name(query)
    if not normalized_query:
        return None

    for record in records:
        normalized_name = record["normalized_name"]
        is_match = normalized_name == normalized_query if not partial else normalized_query in normalized_name
        if is_match:
            return {
                "input": query,
                "ticker": record["ticker"],
                "company_name": record["company_name"],
                "matched": "partial_name" if partial else "company_name",
            }
    return None


def _normalize_company_name(value: str) -> str:
    normalized = normalize_text(value)
    normalized = re.sub(r"[^a-z0-9 ]+", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    for suffix in COMMON_SUFFIXES:
        if normalized.endswith(suffix):
            normalized = normalized[: -len(suffix)].strip()
    return normalized
