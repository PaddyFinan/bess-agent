import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

def get_gas_prices(days: int = 30) -> dict:
    """
    Fetches TTF natural gas futures prices and calculates trend analysis.

    TTF (Title Transfer Facility) is the European gas benchmark and the
    primary driver of Italian evening peak power prices. Gas plants set
    the marginal price of electricity for much of the day in Italy, so
    TTF movements are a leading indicator of power price spread changes.

    A falling TTF signals that evening peak power prices may compress
    in coming weeks, reducing battery arbitrage spreads and putting
    pressure on DSCR. A rising TTF suggests widening spreads ahead.

    Args:
        days: Number of historical days to analyse (default 30)

    Returns:
        Dictionary containing:
        - current_price: latest TTF price in €/MWh
        - price_30d_ago: TTF price 30 days ago
        - change_pct: percentage change over the period
        - avg_7d: 7-day average price
        - avg_30d: 30-day average price
        - trend: "rising", "falling", or "stable"
        - signal: plain English interpretation for BESS spread impact
        - prices_series: dict of {date: price} for the full period
    """

    # ── FETCH TTF DATA ──────────────────────────────────────────────
    ticker = yf.Ticker("TTF=F")
    hist = ticker.history(period=f"{days + 5}d")

    if hist.empty:
        return {"error": "Could not fetch TTF gas price data"}

    # Use closing prices
    prices = hist["Close"].dropna()

    if len(prices) < 2:
        return {"error": "Insufficient TTF data returned"}

    # ── CALCULATE STATISTICS ────────────────────────────────────────

    current_price = round(float(prices.iloc[-1]), 2)
    price_30d_ago = round(float(prices.iloc[0]), 2)
    change_pct = round(((current_price - price_30d_ago) / price_30d_ago) * 100, 1)

    # 7-day and 30-day averages
    avg_7d = round(float(prices.tail(7).mean()), 2)
    avg_30d = round(float(prices.mean()), 2)

    # ── TREND SIGNAL ────────────────────────────────────────────────
    # Classify trend based on percentage change over the period

    if change_pct >= 5:
        trend = "rising"
    elif change_pct <= -5:
        trend = "falling"
    else:
        trend = "stable"

    # ── PLAIN ENGLISH SIGNAL ────────────────────────────────────────
    # Interpret what this means for Italian BESS spread economics

    if trend == "rising":
        signal = (
            f"TTF gas has risen {change_pct}% over the past {days} days "
            f"(€{price_30d_ago} → €{current_price}/MWh). Rising gas costs "
            f"push up evening peak power prices in Italy as gas plants bid "
            f"higher into the market. This is BULLISH for battery arbitrage "
            f"spreads — wider spreads mean higher revenue and stronger DSCR. "
            f"Monitor for sustained movement above €{round(current_price * 1.1, 1)}/MWh "
            f"which would signal a significant upside scenario."
        )
    elif trend == "falling":
        signal = (
            f"TTF gas has fallen {abs(change_pct)}% over the past {days} days "
            f"(€{price_30d_ago} → €{current_price}/MWh). Falling gas reduces "
            f"the cost of gas-fired generation, pushing down evening peak power "
            f"prices in Italy. This is BEARISH for battery arbitrage spreads — "
            f"compressing spreads reduce revenue and put pressure on DSCR. "
            f"If TTF falls below €{round(current_price * 0.85, 1)}/MWh, "
            f"model a downside spread scenario."
        )
    else:
        signal = (
            f"TTF gas has been broadly stable over the past {days} days "
            f"(€{price_30d_ago} → €{current_price}/MWh, {change_pct:+.1f}%). "
            f"Stable gas prices suggest Italian evening peak power prices are "
            f"unlikely to shift materially in the near term. Current spread "
            f"assumptions in the BESS revenue model are supported by the "
            f"gas price environment."
        )

    # ── BUILD PRICES SERIES ─────────────────────────────────────────

    prices_series = {
        str(date.date()): round(float(price), 2)
        for date, price in prices.items()
    }

    return {
        "current_price": current_price,
        "price_30d_ago": price_30d_ago,
        "change_pct": change_pct,
        "avg_7d": avg_7d,
        "avg_30d": avg_30d,
        "trend": trend,
        "signal": signal,
        "prices_series": prices_series
    }