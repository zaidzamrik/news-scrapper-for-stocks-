"""Market data fetching and technical indicator calculations."""
from __future__ import annotations

import datetime as dt
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd
import yfinance as yf

from utils import ema, moving_average, pct_change, safe_float, setup_logger, today_utc


def fetch_market_data(ticker: str, lookback_days: int = 365, logger=None) -> Optional[pd.DataFrame]:
    """Fetch OHLCV market data using yfinance."""
    logger = logger or setup_logger(__name__)
    ticker = ticker.upper().strip()

    lookback_days = max(lookback_days, 260)  # ensure enough history for 200d SMA
    end_dt = today_utc()
    start_dt = end_dt - dt.timedelta(days=lookback_days)

    logger.info("Fetching market data from Yahoo Finance")
    try:
        data = yf.Ticker(ticker).history(start=start_dt, end=end_dt, auto_adjust=False)
    except Exception as exc:  # pragma: no cover - network issues
        logger.error("Market data fetch failed: %s", exc)
        return None

    if data is None or data.empty:
        logger.warning("No market data returned for %s", ticker)
        return None

    data = data.rename(columns=str.title)
    data = data[["Open", "High", "Low", "Close", "Volume"]].dropna()
    return data


def compute_indicators(df: pd.DataFrame) -> Dict[str, Any]:
    """Compute technical indicators and return a summary dictionary."""
    data = df.copy()

    data["SMA20"] = moving_average(data["Close"], 20)
    data["SMA50"] = moving_average(data["Close"], 50)
    data["SMA200"] = moving_average(data["Close"], 200)

    data["EMA12"] = ema(data["Close"], 12)
    data["EMA26"] = ema(data["Close"], 26)
    data["MACD"] = data["EMA12"] - data["EMA26"]
    data["MACDSignal"] = ema(data["MACD"], 9)
    data["MACDHist"] = data["MACD"] - data["MACDSignal"]

    data["RSI14"] = _rsi(data["Close"], 14)
    data["ATR14"] = _atr(data, 14)

    data["VolumeAvg20"] = moving_average(data["Volume"], 20)
    data["VolumeRatio"] = data["Volume"] / data["VolumeAvg20"]

    data["Support20"] = data["Low"].rolling(window=20).min()
    data["Resistance20"] = data["High"].rolling(window=20).max()

    data["Return20d"] = data["Close"].pct_change(periods=20)
    data["Return60d"] = data["Close"].pct_change(periods=60)

    latest = data.iloc[-1]

    trend_regime = _trend_regime(data)
    trend_strength = _trend_strength(latest)

    bearish_divergence = _bearish_divergence(data)
    support_break = _support_break(latest)

    summary = {
        "last_close": safe_float(latest.get("Close")),
        "sma_20": safe_float(latest.get("SMA20")),
        "sma_50": safe_float(latest.get("SMA50")),
        "sma_200": safe_float(latest.get("SMA200")),
        "ema_12": safe_float(latest.get("EMA12")),
        "ema_26": safe_float(latest.get("EMA26")),
        "rsi_14": safe_float(latest.get("RSI14")),
        "macd": safe_float(latest.get("MACD")),
        "macd_signal": safe_float(latest.get("MACDSignal")),
        "macd_hist": safe_float(latest.get("MACDHist")),
        "atr_14": safe_float(latest.get("ATR14")),
        "atr_pct": safe_float(latest.get("ATR14")) / safe_float(latest.get("Close"), 1.0),
        "volume": safe_float(latest.get("Volume")),
        "volume_avg_20": safe_float(latest.get("VolumeAvg20")),
        "volume_ratio": safe_float(latest.get("VolumeRatio")),
        "support_20": safe_float(latest.get("Support20")),
        "resistance_20": safe_float(latest.get("Resistance20")),
        "return_20d": safe_float(latest.get("Return20d")),
        "return_60d": safe_float(latest.get("Return60d")),
        "trend_regime": trend_regime,
        "trend_strength": trend_strength,
        "bearish_divergence": bearish_divergence,
        "support_break": support_break,
        "data_points": int(len(data)),
        "latest_date": data.index[-1].to_pydatetime().isoformat(),
    }

    return summary


def _rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)

    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50.0)


def _atr(data: pd.DataFrame, period: int = 14) -> pd.Series:
    high = data["High"]
    low = data["Low"]
    close = data["Close"]
    prev_close = close.shift(1)

    tr = pd.concat(
        [
            high - low,
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)

    atr = tr.rolling(window=period).mean()
    return atr


def _trend_regime(data: pd.DataFrame) -> str:
    latest = data.iloc[-1]
    sma50 = latest.get("SMA50")
    sma200 = latest.get("SMA200")
    close = latest.get("Close")

    if np.isnan(sma50) or np.isnan(sma200):
        return "neutral"

    slope = data["SMA50"].diff().tail(5).mean()

    if close > sma50 > sma200 and slope > 0:
        return "bullish"
    if close < sma50 < sma200 and slope < 0:
        return "bearish"
    return "neutral"


def _trend_strength(latest: pd.Series) -> float:
    close = safe_float(latest.get("Close"))
    sma50 = safe_float(latest.get("SMA50"))
    sma200 = safe_float(latest.get("SMA200"))
    if close == 0:
        return 0.0
    return (sma50 - sma200) / close


def _bearish_divergence(data: pd.DataFrame) -> bool:
    if len(data) < 15:
        return False
    recent = data.tail(15)
    price_change = pct_change(recent["Close"].iloc[-1], recent["Close"].iloc[0])
    rsi_change = recent["RSI14"].iloc[-1] - recent["RSI14"].max()
    return price_change > 0.02 and recent["RSI14"].iloc[-1] > 70 and rsi_change < -5


def _support_break(latest: pd.Series) -> bool:
    close = safe_float(latest.get("Close"))
    support = safe_float(latest.get("Support20"))
    volume_ratio = safe_float(latest.get("VolumeRatio"), 1.0)
    return close < support and volume_ratio > 1.5
