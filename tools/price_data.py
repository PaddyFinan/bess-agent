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