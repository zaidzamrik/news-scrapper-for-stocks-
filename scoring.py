"""Scoring engine combining news sentiment and technical signals."""
from __future__ import annotations

from typing import Any, Dict, Tuple

from utils import clamp, safe_float


WEIGHT_PROFILES = {
    "conservative": {
        "news": 0.20,
        "trend": 0.25,
        "momentum": 0.15,
        "volatility": 0.25,
        "volume": 0.15,
    },
    "moderate": {
        "news": 0.25,
        "trend": 0.25,
        "momentum": 0.20,
        "volatility": 0.15,
        "volume": 0.15,
    },
    "aggressive": {
        "news": 0.20,
        "trend": 0.30,
        "momentum": 0.30,
        "volatility": 0.10,
        "volume": 0.10,
    },
}

THRESHOLDS = {
    "conservative": {"buy": 66, "hold": 51},
    "moderate": {"buy": 60, "hold": 45},
    "aggressive": {"buy": 56, "hold": 41},
}


def compute_scores(
    news_summary: Dict[str, Any],
    technicals: Dict[str, Any],
    risk_profile: str = "moderate",
) -> Dict[str, Any]:
    """Compute component and total scores."""
    risk_profile = risk_profile.lower()
    weights = WEIGHT_PROFILES.get(risk_profile, WEIGHT_PROFILES["moderate"])

    component_scores = {
        "news": _score_news(news_summary),
        "trend": _score_trend(technicals),
        "momentum": _score_momentum(technicals),
        "volatility": _score_volatility(technicals),
        "volume": _score_volume(technicals),
    }

    available_weights = _available_weights(weights, news_summary)
    total_norm = sum(component_scores[key] * available_weights[key] for key in component_scores)
    total_score = round((total_norm + 1) * 50, 2)

    thresholds = THRESHOLDS.get(risk_profile, THRESHOLDS["moderate"])
    if total_score >= thresholds["buy"]:
        opinion = "Buy Candidate"
    elif total_score >= thresholds["hold"]:
        opinion = "Hold/Monitor"
    else:
        opinion = "Avoid"

    return {
        "risk_profile": risk_profile,
        "weights": weights,
        "effective_weights": available_weights,
        "component_scores": component_scores,
        "component_scores_100": {key: round((val + 1) * 50, 2) for key, val in component_scores.items()},
        "total_score": total_score,
        "opinion": opinion,
        "thresholds": thresholds,
    }


def _score_news(news_summary: Dict[str, Any]) -> float:
    seven_day = news_summary.get("7d", {}) if news_summary else {}
    sentiment = safe_float(seven_day.get("weighted_sentiment", 0.0))
    return clamp(sentiment, -1.0, 1.0)


def _score_trend(technicals: Dict[str, Any]) -> float:
    regime = (technicals or {}).get("trend_regime", "neutral")
    base = {
        "bullish": 0.7,
        "neutral": 0.0,
        "bearish": -0.7,
    }.get(regime, 0.0)
    strength = safe_float((technicals or {}).get("trend_strength", 0.0))
    close = safe_float((technicals or {}).get("last_close", 0.0))
    sma_20 = safe_float((technicals or {}).get("sma_20", 0.0))
    sma_50 = safe_float((technicals or {}).get("sma_50", 0.0))
    sma_200 = safe_float((technicals or {}).get("sma_200", 0.0))

    if close > sma_20 > 0 and close > sma_200 and sma_50 > sma_200:
        base += 0.35
    elif close < sma_20 and close < sma_200 and sma_50 < sma_200:
        base -= 0.35

    return clamp(base + strength * 1.5, -1.0, 1.0)


def _score_momentum(technicals: Dict[str, Any]) -> float:
    ret_20 = safe_float((technicals or {}).get("return_20d", 0.0))
    ret_60 = safe_float((technicals or {}).get("return_60d", 0.0))
    macd_hist = safe_float((technicals or {}).get("macd_hist", 0.0))
    rsi = safe_float((technicals or {}).get("rsi_14", 50.0))

    ret_score = clamp(ret_20 / 0.10, -1.0, 1.0) * 0.5 + clamp(ret_60 / 0.20, -1.0, 1.0) * 0.5
    macd_score = clamp(macd_hist / 0.5, -1.0, 1.0)

    rsi_bias = 0.0
    if rsi > 70:
        rsi_bias = -0.2
    elif rsi < 30:
        rsi_bias = 0.2

    combined = 0.6 * ret_score + 0.3 * macd_score + 0.1 * rsi_bias
    return clamp(combined, -1.0, 1.0)


def _score_volatility(technicals: Dict[str, Any]) -> float:
    atr_pct = safe_float((technicals or {}).get("atr_pct", 0.0))
    # Lower ATR% is generally better for risk-adjusted stability.
    return clamp((0.06 - atr_pct) / 0.04, -1.0, 1.0)


def _score_volume(technicals: Dict[str, Any]) -> float:
    volume_ratio = safe_float((technicals or {}).get("volume_ratio", 1.0))
    return clamp((volume_ratio - 0.85) / 0.6, -0.5, 1.0)


def _available_weights(weights: Dict[str, float], news_summary: Dict[str, Any]) -> Dict[str, float]:
    """Renormalize weights when news is unavailable so missing articles do not mute the signal."""
    has_news = bool(
        news_summary
        and any(
            safe_float(news_summary.get(window, {}).get("count", 0.0)) > 0
            for window in ("1d", "7d", "30d")
        )
    )
    effective = dict(weights)
    if has_news:
        return effective

    effective["news"] = 0.0
    total = sum(effective.values()) or 1.0
    return {key: value / total for key, value in effective.items()}
