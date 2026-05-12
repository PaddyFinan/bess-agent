def calculate_revenue(
    spread_analysis: dict,
    capacity_mwh: float = 50.0,
    power_capacity_mw: float = 25.0,
    efficiency: float = 0.85,
    cycles_per_day: float = 1.0,
    capture_rate: float = 0.75,
    ancillary_revenue_per_mw_year: float = 60_000,
    degradation_rate: float = 0.02,
    project_life_years: int = 15,
    override_avg_spread: float = None,
    override_std_spread: float = None
) -> dict:
    """
    Calculates projected annual revenue for a BESS project across
    three scenarios: base case, downside, and severe downside.

    Includes a full 15-year degradation schedule showing how revenue
    declines as battery capacity erodes at degradation_rate per year.

    The spread input can come from three sources in order of priority:
    1. override_avg_spread — explicit spread value passed directly
       (use this for seasonal averages, stress tests, or custom scenarios)
    2. spread_analysis dictionary — from get_spread_analysis() or
       get_seasonal_analysis()
    3. Nothing — returns an error

    This design means the tool never hardcodes a spread assumption.
    Claude can pass in any spread value from any source.

    Args:
        spread_analysis: Dictionary from get_spread_analysis() or
                        get_seasonal_analysis(). Used if no override.
        capacity_mwh: Battery energy capacity in MWh (default 50 MWh)
        power_capacity_mw: Battery power capacity in MW (default 25 MW)
        efficiency: Round-trip efficiency as decimal (default 0.85)
        cycles_per_day: Number of daily charge/discharge cycles (default 1.0)
        capture_rate: Fraction of theoretical spread captured (default 0.75)
        ancillary_revenue_per_mw_year: Annual ancillary payment per MW
        degradation_rate: Annual capacity degradation (default 0.02 = 2%)
        project_life_years: Number of years to model (default 15)
        override_avg_spread: Optional — use this spread instead of
                            spread_analysis avg_spread. Useful for:
                            - Seasonal weighted average
                            - Stress test scenarios
                            - Multi-year compression modelling
        override_std_spread: Optional — use this std dev instead of
                            spread_analysis std_spread. If override_avg_spread
                            is set but this is not, std defaults to 30% of
                            the override spread.

    Returns:
        Dictionary containing project specs, spreads, revenue by scenario,
        ancillary revenue, year-by-year degradation schedule, and the
        spread source used for transparency.
    """

    # ── DETERMINE SPREAD SOURCE ─────────────────────────────────────
    # Priority: override > spread_analysis > error

    if override_avg_spread is not None:
        avg_spread = override_avg_spread
        # If no override std provided, default to 30% of mean
        # This is a reasonable assumption for Italian power markets
        std_spread = override_std_spread if override_std_spread is not None \
            else round(override_avg_spread * 0.30, 2)
        spread_source = f"override: €{override_avg_spread}/MWh"
        days_analysed = "N/A — override spread used"
    elif spread_analysis:
        avg_spread = spread_analysis.get("avg_spread") or spread_analysis.get("annual_avg_spread")
        std_spread = spread_analysis.get("std_spread") or round(avg_spread * 0.30, 2)
        spread_source = "spread_analysis input"
        days_analysed = spread_analysis.get("days_analysed") or \
                       spread_analysis.get("total_days_analysed", "unknown")
    else:
        return {"error": "Must provide either spread_analysis or override_avg_spread"}

    # ── SCENARIO SPREADS WITH CAPTURE RATE ─────────────────────────

    base_spread = avg_spread * capture_rate
    downside_spread = (avg_spread - std_spread) * capture_rate
    severe_spread = max((avg_spread - (2 * std_spread)) * capture_rate, 0)

    # ── REVENUE FORMULA ─────────────────────────────────────────────

    def calc_arbitrage_annual(spread, capacity):
        daily = spread * capacity * efficiency * cycles_per_day
        return round(daily * 365, 0)

    def calc_arbitrage_daily(spread):
        return round(spread * capacity_mwh * efficiency * cycles_per_day, 2)

    # ── ANCILLARY SERVICES REVENUE ──────────────────────────────────
    # Fixed per MW — does not degrade with battery capacity

    ancillary_annual = round(power_capacity_mw * ancillary_revenue_per_mw_year, 0)

    # ── DEGRADATION SCHEDULE ────────────────────────────────────────
    # Revenue for each year of project life
    # Capacity declines by degradation_rate each year
    # Ancillary revenue stays fixed

    degradation_schedule = {
        "base_case": [],
        "downside": [],
        "severe_downside": [],
        "capacity_mwh_by_year": [],
        "degradation_factor_by_year": []
    }

    for year in range(1, project_life_years + 1):
        degradation_factor = (1 - degradation_rate) ** (year - 1)
        effective_capacity = capacity_mwh * degradation_factor

        base_arb = calc_arbitrage_annual(base_spread, effective_capacity)
        downside_arb = calc_arbitrage_annual(downside_spread, effective_capacity)
        severe_arb = calc_arbitrage_annual(severe_spread, effective_capacity)

        degradation_schedule["base_case"].append(round(base_arb + ancillary_annual, 0))
        degradation_schedule["downside"].append(round(downside_arb + ancillary_annual, 0))
        degradation_schedule["severe_downside"].append(round(severe_arb + ancillary_annual, 0))
        degradation_schedule["capacity_mwh_by_year"].append(round(effective_capacity, 2))
        degradation_schedule["degradation_factor_by_year"].append(round(degradation_factor, 4))

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
            "days_of_data": days_analysed,
            "spread_source": spread_source
        },
        "spreads": {
            "avg_spread_used": round(avg_spread, 2),
            "std_spread_used": round(std_spread, 2),
            "base_case_spread": round(base_spread, 2),
            "downside_spread": round(downside_spread, 2),
            "severe_spread": round(severe_spread, 2)
        },
        "arbitrage_revenue": {
            "base_case": degradation_schedule["base_case"][0] - ancillary_annual,
            "downside": degradation_schedule["downside"][0] - ancillary_annual,
            "severe_downside": degradation_schedule["severe_downside"][0] - ancillary_annual
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