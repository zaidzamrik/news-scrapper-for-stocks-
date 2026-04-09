from __future__ import annotations

import datetime as dt
import os
from typing import Any, Dict, List, Optional

import requests

from utils import (
    dedupe_items,
    normalize_text,
    parse_datetime,
    parse_gdelt_datetime,
    safe_float,
    setup_logger,
    today_utc,
    url_domain,
)

HIGH_RELEVANCE_DOMAINS = {
    "reuters.com",
    "bloomberg.com",
    "wsj.com",
    "ft.com",
    "cnbc.com",
    "marketwatch.com",
    "investors.com",
    "seekingalpha.com",
    "morningstar.com",
    "fool.com",
    "finance.yahoo.com",
    "sec.gov",
}

MID_RELEVANCE_HINTS = ("finance", "markets", "investor", "news")


def fetch_news(
    ticker: str,
    lookback_days: int = 30,
    max_articles: int = 50,
    company_name: Optional[str] = None,
    logger=None,
) -> List[Dict[str, Any]]:
    """Fetch recent news from available providers."""
    logger = logger or setup_logger(__name__)
    ticker = ticker.upper().strip()
    company_name = (company_name or "").strip()

    articles: List[Dict[str, Any]] = []

    newsapi_key = os.getenv("NEWSAPI_KEY")
    if newsapi_key:
        try:
            articles.extend(
                _fetch_newsapi(ticker, lookback_days, max_articles, newsapi_key, company_name, logger)
            )
        except Exception as exc:  # pragma: no cover - network issues
            logger.warning("NewsAPI fetch failed: %s", exc)

    try:
        articles.extend(_fetch_gdelt(ticker, lookback_days, max_articles, company_name, logger))
    except Exception as exc:  # pragma: no cover - network issues
        logger.warning("GDELT fetch failed: %s", exc)

    if not articles:
        logger.warning("No news articles found. Check API keys or network access.")
        return []

    articles = _normalize_articles(articles, lookback_days)
    articles = dedupe_items(articles, ["url", "title"])

    for article in articles:
        article["relevance_score"] = score_relevance(article, ticker, company_name)

    articles = sorted(
        articles,
        key=lambda x: x.get("published_at") or dt.datetime.min.replace(tzinfo=dt.timezone.utc),
        reverse=True,
    )
    return articles[:max_articles]


def _normalize_articles(articles: List[Dict[str, Any]], lookback_days: int) -> List[Dict[str, Any]]:
    cutoff = today_utc() - dt.timedelta(days=lookback_days)
    normalized = []
    for article in articles:
        published_at = article.get("published_at")
        if published_at is None:
            published_at = parse_datetime(article.get("published_at_raw"))
        if published_at is None:
            continue
        if published_at < cutoff:
            continue
        article = dict(article)
        article["published_at"] = published_at
        normalized.append(article)
    return normalized


def score_relevance(article: Dict[str, Any], ticker: str, company_name: str = "") -> float:
    """Score article relevance based on domain and ticker/company mention."""
    domain = url_domain(article.get("url"))
    base_score = 0.4
    if domain in HIGH_RELEVANCE_DOMAINS:
        base_score = 0.8
    elif any(hint in domain for hint in MID_RELEVANCE_HINTS):
        base_score = 0.6

    title = normalize_text(article.get("title"))
    description = normalize_text(article.get("description"))
    content = f"{title} {description}"

    mention_score = 0.0
    if ticker and ticker.lower() in content:
        mention_score += 0.15
    if company_name and company_name.lower() in content:
        mention_score += 0.15

    return min(1.0, base_score + mention_score)


def _fetch_newsapi(
    ticker: str,
    lookback_days: int,
    max_articles: int,
    api_key: str,
    company_name: str,
    logger,
) -> List[Dict[str, Any]]:
    """Fetch news from NewsAPI.org."""
    logger.info("Fetching news from NewsAPI")
    base_url = "https://newsapi.org/v2/everything"
    query_terms = [ticker]
    if company_name:
        query_terms.append(f'"{company_name}"')
    query = " OR ".join(query_terms)

    from_date = (today_utc() - dt.timedelta(days=lookback_days)).strftime("%Y-%m-%d")

    params = {
        "q": query,
        "language": "en",
        "sortBy": "publishedAt",
        "pageSize": min(max_articles, 100),
        "from": from_date,
        "apiKey": api_key,
    }

    response = requests.get(base_url, params=params, timeout=15)
    response.raise_for_status()
    data = response.json()

    articles: List[Dict[str, Any]] = []
    for item in data.get("articles", []):
        published_at = parse_datetime(item.get("publishedAt"))
        articles.append(
            {
                "title": item.get("title"),
                "description": item.get("description"),
                "url": item.get("url"),
                "source": (item.get("source") or {}).get("name"),
                "published_at": published_at,
                "provider": "NewsAPI",
            }
        )
    return articles


def _fetch_gdelt(
    ticker: str,
    lookback_days: int,
    max_articles: int,
    company_name: str,
    logger,
) -> List[Dict[str, Any]]:
    """Fetch news from GDELT DOC API (no API key required)."""
    logger.info("Fetching news from GDELT")
    base_url = "https://api.gdeltproject.org/api/v2/doc/doc"
    query_terms = [f'"{ticker}"']
    if company_name:
        query_terms.append(f'"{company_name}"')
    query_terms.append("stock")
    query = " OR ".join(query_terms)

    end_dt = today_utc()
    start_dt = end_dt - dt.timedelta(days=lookback_days)
    params = {
        "query": query,
        "mode": "ArtList",
        "maxrecords": min(max_articles, 250),
        "format": "json",
        "startdatetime": start_dt.strftime("%Y%m%d%H%M%S"),
        "enddatetime": end_dt.strftime("%Y%m%d%H%M%S"),
    }

    response = requests.get(base_url, params=params, timeout=15)
    response.raise_for_status()
    data = response.json()

    articles: List[Dict[str, Any]] = []
    for item in data.get("articles", []):
        published_at = parse_gdelt_datetime(item.get("seendate"))
        articles.append(
            {
                "title": item.get("title"),
                "description": item.get("description"),
                "url": item.get("url"),
                "source": item.get("domain"),
                "published_at": published_at,
                "provider": "GDELT",
            }
        )
    return articles
