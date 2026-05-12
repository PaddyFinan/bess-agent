from tools.price_data import get_spread_analysis
from tools.revenue_model import calculate_revenue
from tools.dscr import calculate_dscr

# Step 1: Get spread data
print("Fetching spread analysis...")
spread_data = get_spread_analysis(days=30)

# Step 2: Calculate revenue
print("Calculating revenue model...")
revenue = calculate_revenue(spread_data)

# Step 3: Calculate DSCR
print("Calculating DSCR...")
dscr = calculate_dscr(revenue)

# ── REVENUE BREAKDOWN ───────────────────────────────────────────────
print("\nRevenue Breakdown")
print("=" * 50)
print(f"Ancillary services (fixed):  €{revenue['ancillary_revenue']['annual']:>10,.0f}/year")
print(f"  {revenue['ancillary_revenue']['note']}")
print(f"\nArbitrage revenue:")
for scenario, value in revenue['arbitrage_revenue'].items():
    print(f"  {scenario:<20} €{value:>10,.0f}/year")
print(f"\nTotal stacked revenue:")
for scenario, value in revenue['annual_revenue'].items():
    print(f"  {scenario:<20} €{value:>10,.0f}/year")

# ── DEBT STRUCTURE ──────────────────────────────────────────────────
print("\nDebt Structure")
print("=" * 50)
print(f"Loan amount:          €{dscr['debt_structure']['loan_amount']:>15,.0f}")
print(f"Interest rate:        {dscr['debt_structure']['interest_rate_pct']:>14.1f}%")
print(f"Tenor:                {dscr['debt_structure']['tenor_years']:>13} years")
print(f"Annual debt service:  €{dscr['debt_structure']['annual_debt_service']:>15,.0f}")

# ── DSCR SCENARIOS ──────────────────────────────────────────────────
print("\nDSCR Scenarios")
print("=" * 50)
for scenario, value in dscr['dscr_scenarios'].items():
    flag = dscr['flags'][scenario]
    print(f"  {scenario:<20} {value:>6.2f}x   [{flag}]")

# ── SUMMARY ─────────────────────────────────────────────────────────
print("\nScenario Analysis")
print("=" * 50)
for line in dscr['summary']:
    print(f"• {line}")

# ── DEAL ASSESSMENT ─────────────────────────────────────────────────
print("\nOverall Deal Assessment")
print("=" * 50)
print(dscr['deal_assessment'])

# ── DEBT SIZING ─────────────────────────────────────────────────────
print("\nMaximum Supportable Loan at 1.30x DSCR (€)")
print("=" * 50)
for scenario, value in dscr['debt_sizing']['max_supportable_loan'].items():
    print(f"  {scenario:<20} €{value:>12,.0f}")
print(f"\n  Actual loan:         €{dscr['debt_structure']['loan_amount']:>12,.0f}")
print(f"  Note: {dscr['debt_sizing']['note']}")