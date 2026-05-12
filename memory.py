import json
import os
from datetime import datetime

MEMORY_FILE = "memory.json"

def save_snapshot(spread_data: dict, revenue_data: dict, dscr_data: dict, gas_data: dict):
    """
    Saves a snapshot of the current analysis to memory.json.
    Called automatically after every full analysis run.
    """
    snapshot = {
        "timestamp": datetime.now().isoformat(),
        "date": datetime.now().strftime("%Y-%m-%d"),
        "time": datetime.now().strftime("%H:%M"),
        "spread": {
            "avg_spread": spread_data.get("avg_spread"),
            "min_spread": spread_data.get("min_spread"),
            "max_spread": spread_data.get("max_spread"),
            "std_spread": spread_data.get("std_spread"),
            "cv_spread": spread_data.get("cv_spread"),
            "days_analysed": spread_data.get("days_analysed")
        },
        "gas": {
            "current_price": gas_data.get("current_price"),
            "change_pct": gas_data.get("change_pct"),
            "trend": gas_data.get("trend")
        },
        "revenue": {
            "base_case": revenue_data.get("annual_revenue", {}).get("base_case"),
            "downside": revenue_data.get("annual_revenue", {}).get("downside"),
            "severe_downside": revenue_data.get("annual_revenue", {}).get("severe_downside")
        },
        "dscr": {
            "base_case": dscr_data.get("dscr_scenarios", {}).get("base_case"),
            "downside": dscr_data.get("dscr_scenarios", {}).get("downside"),
            "severe_downside": dscr_data.get("dscr_scenarios", {}).get("severe_downside"),
            "base_flag": dscr_data.get("flags", {}).get("base_case"),
            "downside_flag": dscr_data.get("flags", {}).get("downside"),
            "severe_flag": dscr_data.get("flags", {}).get("severe_downside"),
            "deal_assessment": dscr_data.get("deal_assessment"),
            "annual_debt_service": dscr_data.get("debt_structure", {}).get("annual_debt_service")
        }
    }

    with open(MEMORY_FILE, "w") as f:
        json.dump(snapshot, f, indent=2)

    return snapshot


def load_snapshot() -> dict | None:
    """
    Loads the previous analysis snapshot from memory.json.
    Returns None if no previous snapshot exists.
    """
    if not os.path.exists(MEMORY_FILE):
        return None

    with open(MEMORY_FILE, "r") as f:
        return json.load(f)


def format_memory_context(previous: dict) -> str:
    """
    Formats the previous snapshot into a readable context string
    that gets passed to Claude at the start of each analysis.
    """
    if previous is None:
        return "No previous analysis found — this is the first run."

    return f"""
PREVIOUS ANALYSIS SNAPSHOT ({previous['date']} at {previous['time']}):

Power spreads:
- Average daily spread: €{previous['spread']['avg_spread']}/MWh
- Standard deviation: €{previous['spread']['std_spread']}/MWh
- Coefficient of variation: {previous['spread']['cv_spread']}%

TTF gas:
- Price: €{previous['gas']['current_price']}/MWh
- 30-day change: {previous['gas']['change_pct']}%
- Trend: {previous['gas']['trend']}

Revenue (annual):
- Base case: €{previous['revenue']['base_case']:,.0f}
- Downside: €{previous['revenue']['downside']:,.0f}
- Severe downside: €{previous['revenue']['severe_downside']:,.0f}

DSCR:
- Base case: {previous['dscr']['base_case']}x [{previous['dscr']['base_flag']}]
- Downside: {previous['dscr']['downside']}x [{previous['dscr']['downside_flag']}]
- Severe downside: {previous['dscr']['severe_downside']}x [{previous['dscr']['severe_flag']}]
- Deal assessment: {previous['dscr']['deal_assessment']}

When presenting the current analysis, compare these previous numbers to the 
current results and flag any meaningful changes — especially DSCR deterioration 
or gas price movements that signal spread compression risk ahead.
""".strip()