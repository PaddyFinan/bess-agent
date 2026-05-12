import os
from dotenv import load_dotenv
from entsoe import EntsoePandasClient
import pandas as pd

load_dotenv()

def get_spread_analysis(days: int = 30) -> dict:
    """
    Fetches day-ahead electricity prices for Northern Italy (IT-NORTH)
    and returns a daily spread analysis over the specified number of days.

    This is the core data tool for the BESS revenue model. The spread
    between daily minimum and maximum prices represents the theoretical
    maximum arbitrage revenue available to a battery storage project.

    Args:
        days: Number of historical days to analyse (default 30)

    Returns:
        Dictionary containing:
        - daily_spreads: dict of {date: spread} for each complete day
        - avg_spread: average daily spread in €/MWh
        - min_spread: minimum daily spread in €/MWh
        - max_spread: maximum daily spread in €/MWh
        - std_spread: standard deviation of daily spreads
        - cv_spread: coefficient of variation as percentage
        - days_analysed: number of complete days in the dataset
    """

    # Connect to ENTSO-E
    api_key = os.getenv("ENTSO_E_API_KEY")
    client = EntsoePandasClient(api_key=api_key)

    # Define date range dynamically
    end = pd.Timestamp.now(tz="Europe/Rome").normalize()
    start = end - pd.Timedelta(days=days)

    # Pull day-ahead prices for Northern Italy
    prices = client.query_day_ahead_prices("10Y1001A1001A73I", start=start, end=end)

    # Group by date and calculate daily min and max
    daily = prices.groupby(prices.index.date).agg(
        min_price=('min'),
        max_price=('max')
    )

    # Calculate daily spread
    daily['spread'] = daily['max_price'] - daily['min_price']

    # Remove partial days and tomorrow's forecast
    today = pd.Timestamp.now(tz="Europe/Rome").date()
    daily = daily[daily.index.map(lambda d: prices.index.date.tolist().count(d)) >= 90]
    daily = daily[daily.index.map(lambda d: d <= today)]

    # Calculate summary statistics
    avg_spread = daily['spread'].mean()
    min_spread = daily['spread'].min()
    max_spread = daily['spread'].max()
    std_spread = daily['spread'].std()
    cv_spread = (std_spread / avg_spread) * 100

    # Build daily spreads dictionary
    daily_spreads = {
        str(date): round(row['spread'], 2)
        for date, row in daily.iterrows()
    }

    return {
        "daily_spreads": daily_spreads,
        "avg_spread": round(avg_spread, 2),
        "min_spread": round(min_spread, 2),
        "max_spread": round(max_spread, 2),
        "std_spread": round(std_spread, 2),
        "cv_spread": round(cv_spread, 1),
        "days_analysed": len(daily)
    }


def get_seasonal_analysis() -> dict:
    """
    Fetches 12 months of Italian day-ahead power prices and calculates
    spread statistics broken down by season.

    This is critical for project finance modelling — a 15-year revenue
    forecast cannot assume current seasonal conditions year-round.
    Italian power markets behave very differently across seasons:

    - Spring (Apr-Jun): Peak solar, deep midday crashes, widest spreads
    - Summer (Jul-Aug): High solar + high AC demand, moderate spreads
    - Autumn (Sep-Nov): Declining solar, narrowing spreads
    - Winter (Dec-Feb): Minimal solar, gas-driven evening peaks

    Returns:
        Dictionary containing:
        - seasonal_spreads: avg spread for each season
        - seasonal_std: standard deviation for each season
        - seasonal_days: number of days analysed per season
        - best_season: season with highest average spread
        - worst_season: season with lowest average spread
        - annual_avg_spread: weighted average across all seasons
        - seasonality_factor: ratio of best to worst season spread
        - seasonality_note: plain English interpretation
    """

    api_key = os.getenv("ENTSO_E_API_KEY")
    client = EntsoePandasClient(api_key=api_key)

    # Pull 12 months of data
    end = pd.Timestamp.now(tz="Europe/Rome").normalize()
    start = end - pd.Timedelta(days=365)

    print("  Fetching 12 months of price data for seasonal analysis...")
    prices = client.query_day_ahead_prices("10Y1001A1001A73I", start=start, end=end)

    # Group by date and calculate daily spreads
    daily = prices.groupby(prices.index.date).agg(
        min_price=('min'),
        max_price=('max')
    )
    daily['spread'] = daily['max_price'] - daily['min_price']

    # Remove partial days
    # ENTSO-E returns either 15-minute (96 intervals/day) or hourly (24 intervals/day)
    # Check each day individually against its expected full-day count
    today = pd.Timestamp.now(tz="Europe/Rome").date()
    date_counts = {}
    for d in prices.index.date:
        date_counts[d] = date_counts.get(d, 0) + 1
    daily = daily[daily.index.map(lambda d: (
        date_counts.get(d, 0) >= 90 or
        (date_counts.get(d, 0) >= 20 and date_counts.get(d, 0) <= 25)
    ))]
    daily = daily[daily.index.map(lambda d: d <= today)]

    # Convert index to datetime for month extraction
    daily.index = pd.to_datetime(daily.index)

    # ── ASSIGN SEASONS ──────────────────────────────────────────────

    def get_season(date):
        month = date.month
        if month in [3, 4, 5]:
            return "spring"
        elif month in [6, 7, 8]:
            return "summer"
        elif month in [9, 10, 11]:
            return "autumn"
        else:
            return "winter"

    daily['season'] = daily.index.map(get_season)

    # ── CALCULATE SEASONAL STATISTICS ──────────────────────────────

    seasons = ["spring", "summer", "autumn", "winter"]
    seasonal_spreads = {}
    seasonal_std = {}
    seasonal_days = {}
    seasonal_min = {}
    seasonal_max = {}

    for season in seasons:
        season_data = daily[daily['season'] == season]['spread']
        if len(season_data) > 0:
            seasonal_spreads[season] = round(float(season_data.mean()), 2)
            seasonal_std[season] = round(float(season_data.std()), 2)
            seasonal_days[season] = len(season_data)
            seasonal_min[season] = round(float(season_data.min()), 2)
            seasonal_max[season] = round(float(season_data.max()), 2)
        else:
            seasonal_spreads[season] = None
            seasonal_std[season] = None
            seasonal_days[season] = 0
            seasonal_min[season] = None
            seasonal_max[season] = None

    # ── ANNUAL WEIGHTED AVERAGE ─────────────────────────────────────

    total_days = sum(seasonal_days.values())
    annual_avg = sum(
        seasonal_spreads[s] * seasonal_days[s]
        for s in seasons
        if seasonal_spreads[s] is not None
    ) / total_days if total_days > 0 else 0

    # ── BEST AND WORST SEASONS ──────────────────────────────────────

    valid_seasons = {s: v for s, v in seasonal_spreads.items() if v is not None}
    best_season = max(valid_seasons, key=valid_seasons.get) if valid_seasons else None
    worst_season = min(valid_seasons, key=valid_seasons.get) if valid_seasons else None

    # ── SEASONALITY FACTOR ──────────────────────────────────────────

    seasonality_factor = None
    if best_season and worst_season and seasonal_spreads[worst_season] > 0:
        seasonality_factor = round(
            seasonal_spreads[best_season] / seasonal_spreads[worst_season], 2
        )

    # ── PLAIN ENGLISH INTERPRETATION ───────────────────────────────

    if seasonality_factor and seasonality_factor > 1.5:
        seasonality_note = (
            f"Strong seasonality detected (factor {seasonality_factor}x). "
            f"{best_season.capitalize()} spreads are {seasonality_factor}x wider than "
            f"{worst_season} spreads. A flat annual revenue assumption would significantly "
            f"overstate revenue in {worst_season} and understate it in {best_season}."
        )
    elif seasonality_factor and seasonality_factor > 1.2:
        seasonality_note = (
            f"Moderate seasonality detected (factor {seasonality_factor}x). "
            f"{best_season.capitalize()} outperforms {worst_season} by "
            f"{round((seasonality_factor - 1) * 100, 0):.0f}%. "
            f"Worth incorporating seasonal variation into the revenue model."
        )
    else:
        seasonality_note = (
            f"Low seasonality detected (factor {seasonality_factor}x). "
            f"Spreads are relatively consistent across seasons. "
            f"A flat annual average is a reasonable modelling assumption."
        )

    return {
        "seasonal_spreads": seasonal_spreads,
        "seasonal_std": seasonal_std,
        "seasonal_days": seasonal_days,
        "seasonal_min": seasonal_min,
        "seasonal_max": seasonal_max,
        "best_season": best_season,
        "worst_season": worst_season,
        "annual_avg_spread": round(annual_avg, 2),
        "seasonality_factor": seasonality_factor,
        "seasonality_note": seasonality_note,
        "total_days_analysed": total_days
    }