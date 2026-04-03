"""Command-line entry point for the stock research assistant."""
from __future__ import annotations

import argparse
import sys

from news_fetcher import fetch_news
from report import build_report, export_json, print_report
from scoring import compute_scores
from sentiment import aggregate_sentiment, enrich_articles_with_sentiment
from stock_lookup import resolve_security_input
from technicals import compute_indicators, fetch_market_data
from utils import setup_logger


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Stock Research Assistant")
    parser.add_argument("ticker", help="Stock ticker or company name, e.g. AAPL or Apple Inc.")
    parser.add_argument(
        "--lookback-days",
        type=int,
        default=365,
        help="Lookback window in days for market data and news search",
    )
    parser.add_argument("--max-articles", type=int, default=50, help="Max number of news articles")
    parser.add_argument(
        "--risk-profile",
        choices=["conservative", "moderate", "aggressive"],
        default="moderate",
        help="Risk profile for scoring",
    )
    parser.add_argument("--company-name", default="", help="Optional company name to refine news search")
    parser.add_argument("--export-json", default="", help="Optional path to export report as JSON")
    parser.add_argument("--log-level", default="ERROR", help="Logging level")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    logger = setup_logger("stock_research", args.log_level)

    resolution = resolve_security_input(args.ticker, logger=logger)
    ticker = resolution["ticker"]
    company_name = args.company_name.strip() or resolution["company_name"]
    logger.info("Starting research for %s", ticker)

    articles = fetch_news(
        ticker,
        lookback_days=args.lookback_days,
        max_articles=args.max_articles,
        company_name=company_name,
        logger=logger,
    )
    articles = enrich_articles_with_sentiment(articles)
    news_summary = aggregate_sentiment(articles)

    market_data = fetch_market_data(ticker, lookback_days=args.lookback_days, logger=logger)
    if market_data is None:
        logger.warning("Skipping technical analysis due to missing market data.")
        technicals = {}
    else:
        technicals = compute_indicators(market_data)

    scores = compute_scores(news_summary, technicals, risk_profile=args.risk_profile)

    report = build_report(ticker, articles, news_summary, technicals, scores)
    print_report(report)

    if args.export_json:
        export_json(report, args.export_json)
        logger.info("Exported JSON report to %s", args.export_json)

    # TODO: Add backtesting module hook to validate scoring model against historical outcomes.
    # TODO: Integrate paper-trading workflow for simulated execution and tracking.

    return 0


if __name__ == "__main__":
    sys.exit(main())
