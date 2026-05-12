from tools.price_data import get_spread_analysis
from tools.revenue_model import calculate_revenue
from tools.dscr import calculate_dscr

# Step 1: Get spread data
print("Fetching spread analysis...")
spread_data = get_spread_analysis(days=30)

# Step 2: Calculate revenue with degradation
print("Calculating revenue model with degradation...")
revenue = calculate_revenue(spread_data)

# Step 3: Calculate DSCR with year-by-year schedule
print("Calculating DSCR schedule...")
dscr = calculate_dscr(revenue)

# ── PROJECT SPECS ───────────────────────────────────────────────────
print("\nProject Specifications")
print("=" * 55)
print(f"Capacity:             {revenue['project_specs']['capacity_mwh']} MWh / {revenue['project_specs']['power_capacity_mw']} MW")
print(f"Degradation rate:     {revenue['project_specs']['degradation_rate_pct']}% per year")
print(f"Year 1 capacity:      {revenue['year1_capacity_mwh']} MWh")
print(f"Year 15 capacity:     {revenue['final_year_capacity_mwh']} MWh")

# ── DEGRADATION SCHEDULE ────────────────────────────────────────────
print("\nYear-by-Year Revenue and DSCR (Base Case)")
print("=" * 55)
print(f"{'Year':<6} {'Capacity':>10} {'Revenue':>12} {'DSCR':>8} {'Flag':>8}")
print("-" * 55)

schedule = revenue['degradation_schedule']
dscr_sched = dscr['dscr_schedule']['base_case']

for i in range(15):
    year = i + 1
    capacity = schedule['capacity_mwh_by_year'][i]
    rev = schedule['base_case'][i]
    d = dscr_sched[i]
    flag = "GREEN" if d >= 1.30 else "AMBER" if d >= 1.20 else "RED"
    print(f"{year:<6} {capacity:>9.1f}  €{rev:>10,.0f}  {d:>6.2f}x  [{flag}]")

# ── MINIMUM DSCR ────────────────────────────────────────────────────
print("\nMinimum DSCR Across Project Life")
print("=" * 55)
for scenario, info in dscr['minimum_dscr'].items():
    if info:
        print(f"{scenario:<20} {info['dscr']}x in year {info['year']} [{info['flag']}]")

# ── DEBT SIZING ─────────────────────────────────────────────────────
print("\nMaximum Supportable Loan (sized against worst year)")
print("=" * 55)
for scenario, value in dscr['debt_sizing']['max_supportable_loan'].items():
    print(f"  {scenario:<20} €{value:>12,.0f}")
print(f"\n  Actual loan:         €{dscr['debt_structure']['loan_amount']:>12,.0f}")

# ── SUMMARY ─────────────────────────────────────────────────────────
print("\nScenario Analysis")
print("=" * 55)
for line in dscr['summary']:
    print(f"• {line}")

print(f"\nOverall Deal Assessment")
print("=" * 55)
print(dscr['deal_assessment'])