import json
import os
from anthropic import Anthropic
from dotenv import load_dotenv
from tools.price_data import get_spread_analysis
from tools.revenue_model import calculate_revenue
from tools.dscr import calculate_dscr
from tools.gas_prices import get_gas_prices
from memory import save_snapshot, load_snapshot, format_memory_context
from datetime import datetime

load_dotenv()

client = Anthropic()

SYSTEM_PROMPT = """You are a project finance analyst specialising in battery energy 
storage systems (BESS) in the Italian electricity market. You produce a concise 
daily monitoring report for a 50 MWh / 25 MW merchant BESS project in Northern Italy.

Your report should be structured, professional, and focused on changes since the 
last analysis. Flag any deterioration in DSCR, movements in TTF gas prices that 
signal spread compression risk, or unusual spread behaviour.

Keep the report concise — this is a daily monitoring memo, not a full due diligence 
report. Lead with the most important finding. Use clear headings. End with a 
one-line verdict on whether the deal remains bankable."""

def run_daily_report():
    """
    Runs the full analysis chain autonomously and produces a written report.
    Designed to be called by GitHub Actions every morning.
    """

    print(f"\n{'='*60}")
    print(f"BESS Daily Report — {datetime.now().strftime('%Y-%m-%d %H:%M')} UTC")
    print(f"{'='*60}\n")

    # ── STEP 1: LOAD PREVIOUS SNAPSHOT ─────────────────────────────
    previous_snapshot = load_snapshot()
    memory_context = format_memory_context(previous_snapshot)

    # ── STEP 2: RUN ALL FOUR TOOLS ──────────────────────────────────
    print("Fetching market data...")
    spread_data = get_spread_analysis(days=30)
    print(f"  ✓ Spreads: avg €{spread_data['avg_spread']}/MWh")

    gas_data = get_gas_prices(days=30)
    print(f"  ✓ TTF gas: €{gas_data['current_price']}/MWh ({gas_data['change_pct']:+.1f}% 30d)")

    revenue_data = calculate_revenue(spread_data)
    print(f"  ✓ Revenue: €{revenue_data['annual_revenue']['base_case']:,.0f} base case")

    dscr_data = calculate_dscr(revenue_data)
    print(f"  ✓ DSCR: {dscr_data['dscr_scenarios']['base_case']}x base / "
          f"{dscr_data['dscr_scenarios']['downside']}x downside")

    # ── STEP 3: SAVE SNAPSHOT ───────────────────────────────────────
    save_snapshot(spread_data, revenue_data, dscr_data, gas_data)
    print("  ✓ Memory snapshot saved\n")

    # ── STEP 4: GENERATE REPORT WITH CLAUDE ────────────────────────
    print("Generating report...\n")

    # Build the data summary to send to Claude
    data_summary = f"""
Current market data (just fetched):

POWER SPREADS (IT-NORTH, 30-day rolling):
- Average daily spread: €{spread_data['avg_spread']}/MWh
- Min / Max: €{spread_data['min_spread']} / €{spread_data['max_spread']}/MWh
- Standard deviation: €{spread_data['std_spread']}/MWh
- Coefficient of variation: {spread_data['cv_spread']}%
- Days analysed: {spread_data['days_analysed']}

TTF GAS PRICES:
- Current: €{gas_data['current_price']}/MWh
- 30-day change: {gas_data['change_pct']:+.1f}%
- 7-day average: €{gas_data['avg_7d']}/MWh
- Trend: {gas_data['trend'].upper()}
- Signal: {gas_data['signal']}

REVENUE MODEL (50 MWh / 25 MW, 75% capture, €60k/MW ancillary):
- Base case annual revenue: €{revenue_data['annual_revenue']['base_case']:,.0f}
- Downside annual revenue: €{revenue_data['annual_revenue']['downside']:,.0f}
- Severe downside annual revenue: €{revenue_data['annual_revenue']['severe_downside']:,.0f}
- Ancillary services (fixed): €{revenue_data['ancillary_revenue']['annual']:,.0f}/year

DSCR (€17.5M loan, 6%, 15 years → €{dscr_data['debt_structure']['annual_debt_service']:,.0f}/year):
- Base case: {dscr_data['dscr_scenarios']['base_case']}x [{dscr_data['flags']['base_case']}]
- Downside: {dscr_data['dscr_scenarios']['downside']}x [{dscr_data['flags']['downside']}]
- Severe downside: {dscr_data['dscr_scenarios']['severe_downside']}x [{dscr_data['flags']['severe_downside']}]
- Deal assessment: {dscr_data['deal_assessment']}

Max supportable debt at 1.30x DSCR:
- Base case: €{dscr_data['debt_sizing']['max_supportable_loan']['base_case']:,.0f}
- Downside: €{dscr_data['debt_sizing']['max_supportable_loan']['downside']:,.0f}
"""

    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=2048,
        system=SYSTEM_PROMPT + f"\n\n{memory_context}",
        messages=[
            {
                "role": "user",
                "content": f"Produce today's daily monitoring report based on this data:\n{data_summary}"
            }
        ]
    )

    report = response.content[0].text

    # ── STEP 5: PRINT AND SAVE REPORT ───────────────────────────────
    print(report)

    # Save report to file with date stamp
    report_filename = f"reports/report_{datetime.now().strftime('%Y-%m-%d')}.md"
    os.makedirs("reports", exist_ok=True)

    with open(report_filename, "w") as f:
        f.write(f"# BESS Daily Report — {datetime.now().strftime('%Y-%m-%d')}\n\n")
        f.write(report)

    print(f"\n{'='*60}")
    print(f"Report saved to {report_filename}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    run_daily_report()