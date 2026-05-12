from tools.price_data import get_seasonal_analysis
from tools.revenue_model import calculate_revenue
from tools.dscr import calculate_dscr

# Get seasonal average
print("Fetching seasonal analysis...")
seasonal = get_seasonal_analysis()
print(f"Annual weighted average spread: €{seasonal['annual_avg_spread']}/MWh")

# Run revenue model with seasonal average + 2% compression
print("\nRunning revenue model with degradation + spread compression...")
revenue = calculate_revenue(
    spread_analysis={},
    override_avg_spread=seasonal['annual_avg_spread'],
    spread_compression_rate=0.02
)

# Run DSCR
dscr = calculate_dscr(revenue)

# Print the combined schedule
print(f"\nProject Specs:")
print(f"  Degradation rate:    {revenue['project_specs']['degradation_rate_pct']}% per year")
print(f"  Compression rate:    {revenue['project_specs']['spread_compression_rate_pct']}% per year")
print(f"  Year 1 base spread:  €{revenue['year1_base_spread']}/MWh")
print(f"  Year 15 base spread: €{revenue['final_year_base_spread']}/MWh")
print(f"  Year 1 capacity:     {revenue['year1_capacity_mwh']} MWh")
print(f"  Year 15 capacity:    {revenue['final_year_capacity_mwh']} MWh")

print(f"\nYear-by-Year Schedule (Base Case)")
print("=" * 65)
print(f"{'Year':<6} {'Capacity':>10} {'Spread':>10} {'Revenue':>12} {'DSCR':>8} {'Flag':>8}")
print("-" * 65)

schedule = revenue['degradation_schedule']
dscr_sched = dscr['dscr_schedule']['base_case']

for i in range(15):
    year = i + 1
    capacity = schedule['capacity_mwh_by_year'][i]
    spread = schedule['effective_base_spread_by_year'][i]
    rev = schedule['base_case'][i]
    d = dscr_sched[i]
    flag = "GREEN" if d >= 1.30 else "AMBER" if d >= 1.20 else "RED"
    print(f"{year:<6} {capacity:>9.1f}  {spread:>8.2f}  €{rev:>10,.0f}  {d:>6.2f}x  [{flag}]")

print("\nMinimum DSCR Across Project Life")
print("=" * 65)
for scenario, info in dscr['minimum_dscr'].items():
    if info:
        print(f"  {scenario:<22} {info['dscr']}x in year {info['year']} [{info['flag']}]")

print(f"\nDeal Assessment: {dscr['deal_assessment']}")