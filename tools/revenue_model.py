def calculate_revenue(
    spread_analysis: dict,
    capacity_mwh: float = 50.0,
    power_capacity_mw: float = 25.0,
    efficiency: float = 0.85,
    cycles_per_day: float = 1.0,
    capture_rate: float = 0.75,
    ancillary_revenue_per_mw_year: float = 60_000
) -> dict:
    """
    Calculates projected annual revenue for a BESS project across
    three scenarios: base case, downside, and severe downside.

    Revenue is stacked from two sources:
    1. Energy arbitrage — exploiting daily power price spreads
    2. Ancillary services — frequency regulation payments from Terna

    This reflects how real Italian BESS projects generate revenue,
    as modelled in project finance due diligence.

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

    Returns:
        Dictionary containing:
        - project_specs: all input assumptions used
        - arbitrage_revenue: energy arbitrage revenue for each scenario
        - ancillary_revenue: fixed ancillary services revenue
        - total_revenue: combined stacked revenue for each scenario
        - daily_revenue: daily arbitrage revenue for each scenario
        - spreads: effective spread used in each scenario
    """

    # ── EXTRACT SPREAD STATISTICS ───────────────────────────────────

    avg_spread = spread_analysis["avg_spread"]
    std_spread = spread_analysis["std_spread"]
    days_analysed = spread_analysis["days_analysed"]

    # ── SCENARIO SPREADS WITH CAPTURE RATE ─────────────────────────

    base_spread = avg_spread * capture_rate
    downside_spread = (avg_spread - std_spread) * capture_rate
    severe_spread = max((avg_spread - (2 * std_spread)) * capture_rate, 0)

    # ── ARBITRAGE REVENUE ───────────────────────────────────────────
    # Daily Revenue = Effective Spread × Capacity × Efficiency × Cycles
    # Annual Revenue = Daily Revenue × 365

    def calc_arbitrage_annual(spread):
        daily = spread * capacity_mwh * efficiency * cycles_per_day
        return round(daily * 365, 0)

    def calc_arbitrage_daily(spread):
        return round(spread * capacity_mwh * efficiency * cycles_per_day, 2)

    base_arbitrage = calc_arbitrage_annual(base_spread)
    downside_arbitrage = calc_arbitrage_annual(downside_spread)
    severe_arbitrage = calc_arbitrage_annual(severe_spread)

    # ── ANCILLARY SERVICES REVENUE ──────────────────────────────────
    # Fixed annual payment from Terna for frequency regulation
    # Based on MW capacity — same across all scenarios
    # Ancillary revenue is treated as fixed — it doesn't vary with
    # power price spreads the way arbitrage does

    ancillary_annual = round(power_capacity_mw * ancillary_revenue_per_mw_year, 0)

    # ── TOTAL STACKED REVENUE ───────────────────────────────────────

    base_total = base_arbitrage + ancillary_annual
    downside_total = downside_arbitrage + ancillary_annual
    severe_total = severe_arbitrage + ancillary_annual

    return {
        "project_specs": {
            "capacity_mwh": capacity_mwh,
            "power_capacity_mw": power_capacity_mw,
            "efficiency_pct": efficiency * 100,
            "cycles_per_day": cycles_per_day,
            "capture_rate_pct": capture_rate * 100,
            "ancillary_rate_per_mw": ancillary_revenue_per_mw_year,
            "days_of_data": days_analysed
        },
        "spreads": {
            "base_case_spread": round(base_spread, 2),
            "downside_spread": round(downside_spread, 2),
            "severe_spread": round(severe_spread, 2)
        },
        "arbitrage_revenue": {
            "base_case": base_arbitrage,
            "downside": downside_arbitrage,
            "severe_downside": severe_arbitrage
        },
        "ancillary_revenue": {
            "annual": ancillary_annual,
            "note": f"Fixed: €{ancillary_revenue_per_mw_year:,.0f}/MW/year × {power_capacity_mw}MW"
        },
        "annual_revenue": {
            "base_case": base_total,
            "downside": downside_total,
            "severe_downside": severe_total
        },
        "daily_revenue": {
            "base_case": calc_arbitrage_daily(base_spread),
            "downside": calc_arbitrage_daily(downside_spread),
            "severe_downside": calc_arbitrage_daily(severe_spread)
        }
    }