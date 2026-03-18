"""Sentiment analysis utilities for news articles."""
from __future__ import annotations

import datetime as dt
from typing import Any, Dict, Iterable

from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

from utils import clamp, normalize_text, safe_float, today_utc


analyzer = SentimentIntensityAnalyzer()


def analyze_sentiment(text: str) -> float:
    """Return compound sentiment score in range [-1, 1]."""
    if not text:
        return 0.0
    return analyzer.polarity_scores(text).get("compound", 0.0)


def sentiment_label(score: float) -> str:
    """Map compound score to a label."""
    if score >= 0.2:
        return "positive"
    if score <= -0.2:
        return "negative"
    return "neutral"


def enrich_articles_with_sentiment(articles: Iterable[Dict[str, Any]]) -> list[Dict[str, Any]]:
    """Add sentiment scores and labels to each article."""
    enriched = []
    for article in articles:
        title = article.get("title", "")
        description = article.get("description", "")
        text = " ".join([title, description]).strip()
        score = analyze_sentiment(text)
        article = dict(article)
        article["sentiment_score"] = score
        article["sentiment_label"] = sentiment_label(score)
        enriched.append(article)
    return enriched


def aggregate_sentiment(
    articles: Iterable[Dict[str, Any]],
    windows: Iterable[int] = (1, 7, 30),
    now: dt.datetime | None = None,
) -> Dict[str, Dict[str, float]]:
    """Aggregate sentiment over rolling day windows."""
    now = now or today_utc()
    results: Dict[str, Dict[str, float]] = {}
    for days in windows:
        cutoff = now - dt.timedelta(days=days)
        window_articles = [
            article
            for article in articles
            if article.get("published_at")
            and article["published_at"] >= cutoff
        ]
        if not window_articles:
            results[f"{days}d"] = {
                "count": 0,
                "avg_sentiment": 0.0,
                "weighted_sentiment": 0.0,
                "positive_pct": 0.0,
                "negative_pct": 0.0,
            }
            continue

        scores = [safe_float(article.get("sentiment_score", 0.0)) for article in window_articles]
        weights = [safe_float(article.get("relevance_score", 1.0), 1.0) for article in window_articles]
        weighted_sum = sum(score * weight for score, weight in zip(scores, weights))
        total_weight = sum(weights) or 1.0
        avg_sentiment = sum(scores) / len(scores)
        weighted_sentiment = weighted_sum / total_weight

        pos_count = sum(1 for score in scores if score >= 0.2)
        neg_count = sum(1 for score in scores if score <= -0.2)
        total = len(scores)

        results[f"{days}d"] = {
            "count": total,
            "avg_sentiment": clamp(avg_sentiment, -1.0, 1.0),
            "weighted_sentiment": clamp(weighted_sentiment, -1.0, 1.0),
            "positive_pct": pos_count / total,
            "negative_pct": neg_count / total,
        }
    return results


def summarize_headlines(articles: Iterable[Dict[str, Any]], limit: int = 5) -> list[str]:
    """Return a few normalized headlines for report context."""
    headlines = []
    for article in articles:
        title = normalize_text(article.get("title"))
        if title:
            headlines.append(title)
        if len(headlines) >= limit:
            break
    return headlines
