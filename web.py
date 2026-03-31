<<<<<<< HEAD
from __future__ import annotations

import os
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException, Query

from news_fetcher import fetch_news
from report import build_report, build_simple_summary
=======
"""FastAPI web service wrapper around the existing CLI analysis pipeline.

This does not change the underlying analysis logic; it only exposes it over HTTP.
"""

from __future__ import annotations

import os
from typing import Any, Dict

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from news_fetcher import fetch_news
from report import build_report, build_simple_payload, build_simple_summary
>>>>>>> e9bd4da (editied commit)
from scoring import compute_scores
from sentiment import aggregate_sentiment, enrich_articles_with_sentiment
from technicals import compute_indicators, fetch_market_data
from utils import setup_logger


<<<<<<< HEAD
app = FastAPI(title="Stock Research Assistant", version="1.0")
logger = setup_logger("stock_research_web", os.getenv("LOG_LEVEL", "ERROR"))


@app.get("/")
def root() -> Dict[str, str]:
    return {
        "message": "Stock Research Assistant is running. Try /health, /docs, or /analyze?ticker=AAPL"
    }
=======
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = FastAPI(title="Stock Research Assistant", version="1.0")
logger = setup_logger("stock_research_web", os.getenv("LOG_LEVEL", "ERROR"))

app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")


@app.get("/")
def root() -> FileResponse:
    return FileResponse(os.path.join(BASE_DIR, "templates", "index.html"))
>>>>>>> e9bd4da (editied commit)


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
<<<<<<< HEAD
    """Run analysis and return JSON.

    - If `simple=true`, returns `summary_text` and `signal`.
    - Always returns `report` (full JSON) for programmatic use.
    """
=======
    """Run analysis and return JSON."""
>>>>>>> e9bd4da (editied commit)
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

        opinion = (report.get("opinion") or "").lower()
        if "buy" in opinion:
            signal = "BUY"
        elif "hold" in opinion:
            signal = "HOLD"
        else:
            signal = "AVOID"

<<<<<<< HEAD
        payload: Dict[str, Any] = {"ticker": ticker_norm, "signal": signal, "report": report}
=======
        payload: Dict[str, Any] = {
            "ticker": ticker_norm,
            "signal": signal,
            "simple": build_simple_payload(report),
            "report": report,
        }
>>>>>>> e9bd4da (editied commit)
        if simple:
            payload["summary_text"] = build_simple_summary(report)
        return payload
    except Exception as exc:
<<<<<<< HEAD
        # Keep error surface small for beginners; details are in logs.
=======
>>>>>>> e9bd4da (editied commit)
        logger.exception("Analyze failed")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {exc}") from exc
