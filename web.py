"""FastAPI web service wrapper around the existing CLI analysis pipeline.

This does not change the underlying analysis logic; it only exposes it over HTTP.
"""

from __future__ import annotations

import datetime as dt
import os
from typing import Any, Dict

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from news_fetcher import fetch_news
from report import build_report, build_simple_payload, build_simple_summary
from scoring import compute_scores
from sentiment import aggregate_sentiment, enrich_articles_with_sentiment
from technicals import compute_indicators, fetch_market_data
from utils import setup_logger


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = FastAPI(title="Stock Research Assistant", version="1.0")
logger = setup_logger("stock_research_web", os.getenv("LOG_LEVEL", "ERROR"))

app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")

try:  # Optional: used only to convert non-JSON-native scalars.
    import numpy as np  # type: ignore
except Exception:  # pragma: no cover
    np = None  # type: ignore

try:  # Optional: used only to convert Timestamp-like values.
    import pandas as pd  # type: ignore
except Exception:  # pragma: no cover
    pd = None  # type: ignore


def _json_sanitize(value: Any) -> Any:
    """Convert common non-JSON-native types (numpy/pandas/datetime) into JSON-safe primitives."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value

    if isinstance(value, dt.datetime):
        return value.isoformat()

    if isinstance(value, dict):
        return {str(key): _json_sanitize(val) for key, val in value.items()}

    if isinstance(value, (list, tuple, set)):
        return [_json_sanitize(item) for item in value]

    if np is not None:
        try:
            if isinstance(value, np.generic):
                return _json_sanitize(value.item())
        except Exception:
            pass

    if pd is not None:
        try:
            if isinstance(value, pd.Timestamp):
                return value.isoformat()
        except Exception:
            pass

    # Last resort: stringify unknown objects instead of failing the whole request.
    return str(value)


@app.get("/")
def root() -> FileResponse:
    return FileResponse(os.path.join(BASE_DIR, "templates", "index.html"))


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.get("/analyze")
def analyze(
    ticker: str = Query(..., min_length=1, max_length=10, description="Stock ticker, e.g. AAPL"),
    lookback_days: int = Query(365, ge=7, le=3650, description="Lookback window in days"),
    max_articles: int = Query(25, ge=0, le=100, description="Max number of news articles"),
    risk_profile: str = Query(
        "moderate",
        pattern="^(conservative|moderate|aggressive)$",
        description="Risk profile for scoring",
    ),
    company_name: str = Query("", max_length=80, description="Optional company name to refine news search"),
    simple: bool = Query(True, description="Return beginner-friendly summary text"),
) -> Dict[str, Any]:
    """Run analysis and return JSON."""
    try:
        ticker_norm = ticker.upper().strip()

        articles = fetch_news(
            ticker_norm,
            lookback_days=lookback_days,
            max_articles=max_articles,
            company_name=company_name,
            logger=logger,
        )
        articles = enrich_articles_with_sentiment(articles)
        news_summary = aggregate_sentiment(articles)

        market_data = fetch_market_data(ticker_norm, lookback_days=lookback_days, logger=logger)
        technicals = compute_indicators(market_data) if market_data is not None else {}

        scores = compute_scores(news_summary, technicals, risk_profile=risk_profile)
        report = build_report(ticker_norm, articles, news_summary, technicals, scores)
        payload: Dict[str, Any] = build_simple_payload(report)
        return _json_sanitize(payload)
    except Exception as exc:
        logger.exception("Analyze failed")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {exc}") from exc
