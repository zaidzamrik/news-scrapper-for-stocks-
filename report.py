from __future__ import annotations

import json
from typing import Any, Dict, List

from utils import safe_float, today_utc


DISCLAIMER = "Disclaimer: This is a research tool, not financial advice."


def build_report(
    ticker: str,
    articles: List[Dict[str, Any]],
    news_summary: Dict[str, Any],
    technicals: Dict[str, Any],
    scoring: Dict[str, Any],
) -> Dict[str, Any]:
    """Build a report dictionary for console and JSON output."""
    explanations = generate_explanations(news_summary, technicals, scoring)

    slim_articles = [
        {
            "title": article.get("title"),
            "url": article.get("url"),
            "source": article.get("source"),
            "published_at": article.get("published_at").isoformat()
            if article.get("published_at")
            else None,
            "sentiment_score": article.get("sentiment_score"),
            "sentiment_label": article.get("sentiment_label"),
            "relevance_score": article.get("relevance_score"),
        }
        for article in articles
    ]

    return {
        "ticker": ticker,
        "generated_at": today_utc().isoformat(),
        "signal": scoring.get("signal"),
        "opinion": scoring.get("signal"),
        "score": scoring.get("total_score"),
        "risk_profile": scoring.get("risk_profile"),
        "thresholds": scoring.get("thresholds"),
        "news": {
            "summary": news_summary,
            "articles": slim_articles,
        },
        "technicals": technicals,
        "scoring": scoring,
        "explanations": explanations,
        "disclaimer": DISCLAIMER,
    }


def generate_explanations(
    news_summary: Dict[str, Any],
    technicals: Dict[str, Any],
    scoring: Dict[str, Any],
) -> Dict[str, List[str]]:
    """Generate plain-English explanations for buy/risk/hold/exit logic."""
    buy_reasons: List[str] = []
    risk_reasons: List[str] = []
    hold_conditions: List[str] = []
    exit_triggers: List[str] = []

    regime = technicals.get("trend_regime", "neutral")
    rsi = safe_float(technicals.get("rsi_14", 50.0))
    atr_pct = safe_float(technicals.get("atr_pct", 0.0))
    volume_ratio = safe_float(technicals.get("volume_ratio", 1.0))

    sentiment_7d = safe_float(news_summary.get("7d", {}).get("weighted_sentiment", 0.0))
    sentiment_1d = safe_float(news_summary.get("1d", {}).get("weighted_sentiment", 0.0))

    if regime == "bullish":
        buy_reasons.append("Trend regime is bullish with price above key moving averages.")
    elif regime == "bearish":
        risk_reasons.append("Trend regime is bearish; price is below key moving averages.")

    if sentiment_7d > 0.2:
        buy_reasons.append("Recent 7-day news sentiment is positive.")
    elif sentiment_7d < -0.2:
        risk_reasons.append("Recent 7-day news sentiment is negative.")

    if safe_float(technicals.get("return_20d", 0.0)) > 0.05:
        buy_reasons.append("Short-term momentum over the last 20 days is strong.")
    if safe_float(technicals.get("return_60d", 0.0)) < -0.05:
        risk_reasons.append("Medium-term momentum over the last 60 days is weak.")

    if volume_ratio > 1.2:
        buy_reasons.append("Above-average volume suggests confirmation of the recent move.")
    elif volume_ratio < 0.8:
        risk_reasons.append("Below-average volume raises doubts about the move's strength.")

    if rsi > 70:
        risk_reasons.append("RSI is overbought, increasing pullback risk.")
    elif rsi < 30:
        buy_reasons.append("RSI is oversold, which can precede rebounds.")

    if atr_pct > 0.05:
        risk_reasons.append("Volatility is elevated (ATR > 5% of price).")

    if technicals.get("bearish_divergence"):
        risk_reasons.append("Potential bearish RSI divergence detected.")
    if technicals.get("support_break"):
        risk_reasons.append("Price broke recent support on heavy volume.")

    hold_conditions.append("Hold while price stays above the 50-day moving average.")
    hold_conditions.append("Hold while 7-day news sentiment remains non-negative.")
    hold_conditions.append("Hold while trend regime is not bearish.")

    exit_triggers.append("Reduce/exit if price closes below the 50-day moving average for 3 consecutive days.")
    exit_triggers.append("Reduce/exit if price breaks 20-day support with above-average volume.")
    exit_triggers.append("Reduce/exit if RSI becomes overextended (above 70) and bearish divergence appears.")
    exit_triggers.append("Reduce/exit if 1-day news sentiment turns sharply negative (below -0.4).")

    current_triggers: List[str] = []
    if technicals.get("support_break"):
        current_triggers.append("Support break with volume appears to be active.")
    if technicals.get("bearish_divergence"):
        current_triggers.append("Bearish divergence signal appears active.")
    if sentiment_1d < -0.4:
        current_triggers.append("Latest 1-day sentiment is sharply negative.")

    if current_triggers:
        exit_triggers = current_triggers + exit_triggers

    return {
        "buy_case": buy_reasons,
        "risk_case": risk_reasons,
        "hold_conditions": hold_conditions,
        "exit_triggers": exit_triggers,
    }


def build_simple_summary(report: Dict[str, Any]) -> str:
    """Build a beginner-friendly, short summary string."""
    simple = build_simple_payload(report)
    lines = [
        f"Ticker: {simple['ticker']}",
        f"Date: {simple['date']}",
        f"Signal: {simple['signal']}",
        "Why:",
    ]
    lines.extend([f"- {reason}" for reason in simple["why"]])
    lines.extend(
        [
            "Plan:",
            f"Buy: {simple['plan']['buy']}",
            f"Hold: {simple['plan']['hold']}",
            f"Exit: {simple['plan']['exit']}",
            "Risks:",
        ]
    )
    lines.extend([f"- {risk}" for risk in simple["risks"]])
    lines.append(simple["disclaimer"])
    return "\n".join(lines)


def build_simple_payload(report: Dict[str, Any]) -> Dict[str, Any]:
    """Build a structured beginner-friendly summary payload."""
    ticker = report.get("ticker", "N/A")
    generated_at = report.get("generated_at", "")
    date = generated_at.split("T")[0] if generated_at else ""

    signal_key = report.get("signal") or report.get("opinion") or "DONT_BUY"
    signal_display = "DON'T BUY" if signal_key == "DONT_BUY" else str(signal_key)

    news_summary = report.get("news", {}).get("summary", {})
    technicals = report.get("technicals", {})
    has_news = any(
        safe_float(news_summary.get(window, {}).get("count", 0.0)) > 0 for window in ("1d", "7d", "30d")
    )

    sentiment_7d = safe_float(news_summary.get("7d", {}).get("weighted_sentiment", 0.0))
    sentiment_1d = safe_float(news_summary.get("1d", {}).get("weighted_sentiment", 0.0))
    regime = technicals.get("trend_regime", "neutral")
    ret_20d = safe_float(technicals.get("return_20d", 0.0))
    rsi = safe_float(technicals.get("rsi_14", 50.0))
    atr_pct = safe_float(technicals.get("atr_pct", 0.0))
    support_break = bool(technicals.get("support_break"))
    bearish_divergence = bool(technicals.get("bearish_divergence"))
    volume_ratio = safe_float(technicals.get("volume_ratio", 1.0))

    reasons = _signal_reasons(
        signal_key=signal_key,
        has_news=has_news,
        sentiment_7d=sentiment_7d,
        regime=regime,
        ret_20d=ret_20d,
        rsi=rsi,
        support_break=support_break,
        bearish_divergence=bearish_divergence,
    )
    risks = _signal_risks(
        signal_key=signal_key,
        sentiment_1d=sentiment_1d,
        atr_pct=atr_pct,
        support_break=support_break,
        volume_ratio=volume_ratio,
        has_news=has_news,
    )
    plan = _signal_plan(signal_key)

    return {
        "ticker": ticker,
        "date": date,
        "signal": signal_display,
        "why": reasons,
        "plan": plan,
        "risks": risks,
        "disclaimer": DISCLAIMER,
    }


def _signal_reasons(
    signal_key: str,
    has_news: bool,
    sentiment_7d: float,
    regime: str,
    ret_20d: float,
    rsi: float,
    support_break: bool,
    bearish_divergence: bool,
) -> List[str]:
    if signal_key == "BUY":
        reasons: List[str] = []
        if has_news and sentiment_7d > 0.2:
            reasons.append("Positive recent news")
        if regime == "bullish":
            reasons.append("Trend looks strong")
        if ret_20d > 0:
            reasons.append("Good time to consider entry")
        if not reasons:
            reasons = ["Conditions look supportive", "Trend appears constructive", "Entry setup looks favorable"]
        return reasons[:3]

    if signal_key == "HOLD":
        reasons = ["Stock remains stable", "No major warning signs", "Continue monitoring"]
        if regime == "bearish":
            reasons[0] = "Stock is under pressure"
        elif regime == "bullish":
            reasons[0] = "Trend still looks supportive"
        return reasons[:3]

    if signal_key == "EXIT":
        reasons = ["Signals have weakened", "Risk appears elevated", "Conditions suggest caution"]
        if support_break:
            reasons[0] = "Price support has broken down"
        elif bearish_divergence:
            reasons[0] = "Momentum has started to fade"
        elif sentiment_7d < -0.2:
            reasons[0] = "Recent news has turned negative"
        return reasons[:3]

    reasons = ["Signals are currently mixed", "The timing does not look favorable for entry"]
    if regime == "neutral":
        reasons.append("Better to wait for clearer confirmation")
    elif regime == "bearish":
        reasons.append("Trend still looks uncertain")
    elif rsi > 70:
        reasons.append("The move may already be stretched")
    else:
        reasons.append("Better to wait for clearer confirmation")
    return reasons[:3]


def _signal_risks(
    signal_key: str,
    sentiment_1d: float,
    atr_pct: float,
    support_break: bool,
    volume_ratio: float,
    has_news: bool,
) -> List[str]:
    risks: List[str] = []
    if signal_key == "EXIT":
        risks.append("Further downside could follow")
    if sentiment_1d < -0.4:
        risks.append("Sudden negative news")
    if support_break and len(risks) < 2:
        risks.append("Short-term direction looks weak")
    if atr_pct > 0.05 and len(risks) < 2:
        risks.append("Market volatility")
    if volume_ratio < 0.8 and len(risks) < 2:
        risks.append("Conviction behind the move looks weak")
    if not has_news and len(risks) < 2:
        risks.append("News visibility is limited right now")
    if not risks:
        risks.append("Unclear short-term direction")
    return risks[:2]


def _signal_plan(signal_key: str) -> Dict[str, str]:
    if signal_key == "BUY":
        return {
            "buy": "Consider entering while conditions stay supportive",
            "hold": "If already owned, keep monitoring the trend",
            "exit": "Exit if conditions weaken further",
        }
    if signal_key == "HOLD":
        return {
            "buy": "Wait for stronger confirmation before adding",
            "hold": "If already owned, continue monitoring",
            "exit": "Exit if conditions weaken further",
        }
    if signal_key == "EXIT":
        return {
            "buy": "Do not add until conditions improve",
            "hold": "Holding here looks risky",
            "exit": "Consider reducing or exiting now",
        }
    return {
        "buy": "Wait for stronger confirmation",
        "hold": "If already owned, continue monitoring",
        "exit": "Exit if conditions weaken further",
    }


def print_report(report: Dict[str, Any]) -> None:
    """Print the beginner-friendly summary report."""
    print(build_simple_summary(report))
    
def export_json(report: Dict[str, Any], path: str) -> None:
    """Export report to JSON file."""
    with open(path, "w", encoding="utf-8") as file:
        json.dump(report, file, indent=2)
