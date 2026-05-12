def calculate_revenue(
    spread_analysis: dict,
    capacity_mwh: float = 50.0,
    power_capacity_mw: float = 25.0,
    efficiency: float = 0.85,
    cycles_per_day: float = 1.0,
    capture_rate: float = 0.75,
    ancillary_revenue_per_mw_year: float = 60_000,
    degradation_rate: float = 0.02,
    project_life_years: int = 15
) -> dict:
    """
    Calculates projected annual revenue for a BESS project across
    three scenarios: base case, downside, and severe downside.

    Now includes a year-by-year degradation curve — battery capacity
    declines at degradation_rate per year, reducing revenue over the
    project life. This is critical for project finance modelling as
    lenders underwrite against the minimum DSCR year, not just year 1.

    Revenue is stacked from two sources:
    1. Energy arbitrage — exploiting daily power price spreads
    2. Ancillary services — frequency regulation payments from Terna

    Args:
        spread_analysis: Dictionary returned by get_spread_analysis()
        capacity_mwh: Battery energy capacity in MWh (default 50 MWh)
        power_capacity_mw: Battery power capacity in MW (default 25 MW)
        efficiency: Round-trip efficiency as decimal (default 0.85)
        cycles_per_day: Number of daily charge/discharge cycles (default 1.0)
        capture_rate: Fraction of theoretical spread captured (default 0.75)
        ancillary_revenue_per_mw_year: Annual ancillary service payment
                                       per MW of capacity in euros
                                       (default €60,000/MW/year)
        degradation_rate: Annual capacity degradation as decimal (default 0.02 = 2%)
        project_life_years: Number of years to model (default 15)

    Returns:
        Dictionary containing:
        - project_specs: all input assumptions used
        - spreads: effective spread used in each scenario
        - arbitrage_revenue: year 1 arbitrage revenue for each scenario
        - ancillary_revenue: fixed ancillary services revenue
        - annual_revenue: year 1 total stacked revenue for each scenario
        - daily_revenue: daily arbitrage revenue for each scenario
        - degradation_schedule: year-by-year revenue for each scenario
        - year1_capacity_mwh: starting capacity
        - final_year_capacity_mwh: capacity in final year after degradation
    """

    # ── EXTRACT SPREAD STATISTICS ───────────────────────────────────

    avg_spread = spread_analysis["avg_spread"]
    std_spread = spread_analysis["std_spread"]
    days_analysed = spread_analysis["days_analysed"]

    # ── SCENARIO SPREADS WITH CAPTURE RATE ─────────────────────────

    base_spread = avg_spread * capture_rate
    downside_spread = (avg_spread - std_spread) * capture_rate
    severe_spread = max((avg_spread - (2 * std_spread)) * capture_rate, 0)

    # ── YEAR 1 ARBITRAGE REVENUE ────────────────────────────────────
    # Uses full capacity — degradation not yet applied

    def calc_arbitrage_annual(spread, capacity):
        daily = spread * capacity * efficiency * cycles_per_day
        return round(daily * 365, 0)

    def calc_arbitrage_daily(spread):
        return round(spread * capacity_mwh * efficiency * cycles_per_day, 2)

    base_arbitrage_y1 = calc_arbitrage_annual(base_spread, capacity_mwh)
    downside_arbitrage_y1 = calc_arbitrage_annual(downside_spread, capacity_mwh)
    severe_arbitrage_y1 = calc_arbitrage_annual(severe_spread, capacity_mwh)

    # ── ANCILLARY SERVICES REVENUE ──────────────────────────────────
    # Fixed annual payment — does not degrade with battery capacity
    # Ancillary services are paid per MW of power capacity, not MWh

    ancillary_annual = round(power_capacity_mw * ancillary_revenue_per_mw_year, 0)

    # ── DEGRADATION SCHEDULE ────────────────────────────────────────
    # Calculate revenue for each year of the project life
    # Capacity declines by degradation_rate each year
    # Ancillary revenue stays fixed (paid per MW, not MWh)

    degradation_schedule = {
        "base_case": [],
        "downside": [],
        "severe_downside": [],
        "capacity_mwh_by_year": [],
        "degradation_factor_by_year": []
    }

    for year in range(1, project_life_years + 1):
        # Degradation factor — capacity as fraction of original
        degradation_factor = (1 - degradation_rate) ** (year - 1)
        effective_capacity = capacity_mwh * degradation_factor

        # Arbitrage revenue scales with capacity
        base_arb = calc_arbitrage_annual(base_spread, effective_capacity)
        downside_arb = calc_arbitrage_annual(downside_spread, effective_capacity)
        severe_arb = calc_arbitrage_annual(severe_spread, effective_capacity)

        # Total revenue = arbitrage (degrading) + ancillary (fixed)
        base_total = base_arb + ancillary_annual
        downside_total = downside_arb + ancillary_annual
        severe_total = severe_arb + ancillary_annual

        degradation_schedule["base_case"].append(round(base_total, 0))
        degradation_schedule["downside"].append(round(downside_total, 0))
        degradation_schedule["severe_downside"].append(round(severe_total, 0))
        degradation_schedule["capacity_mwh_by_year"].append(round(effective_capacity, 2))
        degradation_schedule["degradation_factor_by_year"].append(round(degradation_factor, 4))

    # Final year capacity
    final_capacity = capacity_mwh * (1 - degradation_rate) ** (project_life_years - 1)

    return {
        "project_specs": {
            "capacity_mwh": capacity_mwh,
            "power_capacity_mw": power_capacity_mw,
            "efficiency_pct": efficiency * 100,
            "cycles_per_day": cycles_per_day,
            "capture_rate_pct": capture_rate * 100,
            "ancillary_rate_per_mw": ancillary_revenue_per_mw_year,
            "degradation_rate_pct": degradation_rate * 100,
            "project_life_years": project_life_years,
            "days_of_data": days_analysed
        },
        "spreads": {
            "base_case_spread": round(base_spread, 2),
            "downside_spread": round(downside_spread, 2),
            "severe_spread": round(severe_spread, 2)
        },
        "arbitrage_revenue": {
            "base_case": base_arbitrage_y1,
            "downside": downside_arbitrage_y1,
            "severe_downside": severe_arbitrage_y1
        },
        "ancillary_revenue": {
            "annual": ancillary_annual,
            "note": f"Fixed: €{ancillary_revenue_per_mw_year:,.0f}/MW/year × {power_capacity_mw}MW"
        },
        "annual_revenue": {
            "base_case": degradation_schedule["base_case"][0],
            "downside": degradation_schedule["downside"][0],
            "severe_downside": degradation_schedule["severe_downside"][0]
        },
        "daily_revenue": {
            "base_case": calc_arbitrage_daily(base_spread),
            "downside": calc_arbitrage_daily(downside_spread),
            "severe_downside": calc_arbitrage_daily(severe_spread)
        },
        "degradation_schedule": degradation_schedule,
        "year1_capacity_mwh": capacity_mwh,
        "final_year_capacity_mwh": round(final_capacity, 2)
    }