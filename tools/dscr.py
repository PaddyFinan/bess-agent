def calculate_dscr(
    revenue_model: dict,
    loan_amount: float = 17_500_000,
    interest_rate: float = 0.06,
    loan_tenor_years: int = 15
) -> dict:
    """
    Calculates Debt Service Coverage Ratio (DSCR) for a BESS project
    across base case, downside, and severe downside scenarios.

    Now includes a full year-by-year DSCR schedule using the degradation
    curve from the revenue model. Identifies the minimum DSCR year for
    each scenario — this is the number lenders actually underwrite against.

    DSCR = Annual Revenue / Annual Debt Service

    Industry thresholds:
    - DSCR >= 1.30x: Green — comfortable, bankable
    - DSCR 1.20x-1.30x: Amber — acceptable but tight
    - DSCR < 1.20x: Red — breach, project cannot be financed

    Args:
        revenue_model: Dictionary returned by calculate_revenue()
        loan_amount: Total debt in euros (default €17.5m)
        interest_rate: Annual interest rate as decimal (default 0.06)
        loan_tenor_years: Loan repayment period in years (default 15)

    Returns:
        Dictionary containing:
        - debt_structure: loan details and annual debt service
        - dscr_scenarios: year 1 DSCR for each scenario
        - flags: green/amber/red status for each scenario
        - summary: plain English interpretation
        - deal_assessment: overall bankability verdict
        - debt_sizing: maximum supportable loan at 1.30x DSCR
        - dscr_schedule: year-by-year DSCR for each scenario
        - minimum_dscr: worst year DSCR for each scenario
    """

    # ── ANNUAL DEBT SERVICE ─────────────────────────────────────────
    # Annuity formula: fixed annual payment covering interest + principal

    r = interest_rate
    n = loan_tenor_years
    annual_debt_service = loan_amount * (r * (1 + r)**n) / ((1 + r)**n - 1)
    annual_debt_service = round(annual_debt_service, 0)

    # ── EXTRACT YEAR 1 REVENUES ─────────────────────────────────────

    base_revenue_y1 = revenue_model["annual_revenue"]["base_case"]
    downside_revenue_y1 = revenue_model["annual_revenue"]["downside"]
    severe_revenue_y1 = revenue_model["annual_revenue"]["severe_downside"]

    # ── YEAR 1 DSCR ─────────────────────────────────────────────────

    base_dscr_y1 = round(base_revenue_y1 / annual_debt_service, 2)
    downside_dscr_y1 = round(downside_revenue_y1 / annual_debt_service, 2)
    severe_dscr_y1 = round(severe_revenue_y1 / annual_debt_service, 2)

    # ── FLAG EACH SCENARIO ──────────────────────────────────────────

    def get_flag(dscr):
        if dscr >= 1.30:
            return "GREEN"
        elif dscr >= 1.20:
            return "AMBER"
        else:
            return "RED"

    # ── YEAR BY YEAR DSCR SCHEDULE ──────────────────────────────────
    # Uses degradation schedule from revenue model
    # Debt service is fixed every year — revenue declines with degradation

    degradation_schedule = revenue_model.get("degradation_schedule", {})

    dscr_schedule = {
        "base_case": [],
        "downside": [],
        "severe_downside": []
    }

    if degradation_schedule:
        for year_revenue in degradation_schedule["base_case"]:
            dscr_schedule["base_case"].append(
                round(year_revenue / annual_debt_service, 2)
            )
        for year_revenue in degradation_schedule["downside"]:
            dscr_schedule["downside"].append(
                round(year_revenue / annual_debt_service, 2)
            )
        for year_revenue in degradation_schedule["severe_downside"]:
            dscr_schedule["severe_downside"].append(
                round(year_revenue / annual_debt_service, 2)
            )

    # ── MINIMUM DSCR ────────────────────────────────────────────────
    # The worst year — what lenders actually underwrite against

    def get_min_dscr(schedule):
        if not schedule:
            return None
        min_val = min(schedule)
        min_year = schedule.index(min_val) + 1
        return {"dscr": min_val, "year": min_year, "flag": get_flag(min_val)}

    minimum_dscr = {
        "base_case": get_min_dscr(dscr_schedule["base_case"]),
        "downside": get_min_dscr(dscr_schedule["downside"]),
        "severe_downside": get_min_dscr(dscr_schedule["severe_downside"])
    }

    # ── PLAIN ENGLISH SUMMARY ───────────────────────────────────────

    def interpret_dscr(scenario, dscr, flag, min_dscr_info):
        min_str = ""
        if min_dscr_info:
            min_str = (f" Minimum DSCR of {min_dscr_info['dscr']}x "
                      f"occurs in year {min_dscr_info['year']} "
                      f"[{min_dscr_info['flag']}].")

        if flag == "GREEN":
            return (f"{scenario}: Year 1 DSCR of {dscr}x — comfortable. "
                   f"Project generates €{dscr:.2f} for every €1.00 of debt service.{min_str}")
        elif flag == "AMBER":
            return (f"{scenario}: Year 1 DSCR of {dscr}x — tight but acceptable. "
                   f"Project is at the margin of bankability.{min_str}")
        else:
            return (f"{scenario}: Year 1 DSCR of {dscr}x — breach. "
                   f"Project cannot service its debt.{min_str}")

    summary = [
        interpret_dscr("Base case", base_dscr_y1, get_flag(base_dscr_y1),
                      minimum_dscr["base_case"]),
        interpret_dscr("Downside", downside_dscr_y1, get_flag(downside_dscr_y1),
                      minimum_dscr["downside"]),
        interpret_dscr("Severe downside", severe_dscr_y1, get_flag(severe_dscr_y1),
                      minimum_dscr["severe_downside"])
    ]

    # ── OVERALL DEAL ASSESSMENT ─────────────────────────────────────
    # Based on minimum DSCR across project life, not just year 1

    base_min = minimum_dscr["base_case"]["dscr"] if minimum_dscr["base_case"] else base_dscr_y1
    downside_min = minimum_dscr["downside"]["dscr"] if minimum_dscr["downside"] else downside_dscr_y1

    if base_min >= 1.30 and downside_min >= 1.20:
        deal_assessment = "BANKABLE — project supports debt financing across full project life"
    elif base_min >= 1.20 and downside_min >= 1.10:
        deal_assessment = "CONDITIONALLY BANKABLE — lender protections required in later years"
    else:
        deal_assessment = "NOT BANKABLE — revenue insufficient to support debt across project life"

    # ── MAXIMUM SUPPORTABLE DEBT ────────────────────────────────────

    min_acceptable_dscr = 1.30

    def max_loan_from_revenue(annual_rev):
        max_debt_service = annual_rev / min_acceptable_dscr
        return round(max_debt_service * ((1 + r)**n - 1) / (r * (1 + r)**n), 0)

    # Size debt against minimum year revenue, not year 1
    base_min_rev = min(degradation_schedule.get("base_case", [base_revenue_y1]))
    downside_min_rev = min(degradation_schedule.get("downside", [downside_revenue_y1]))
    severe_min_rev = min(degradation_schedule.get("severe_downside", [severe_revenue_y1]))

    max_loan_base = max_loan_from_revenue(base_min_rev)
    max_loan_downside = max_loan_from_revenue(downside_min_rev)
    max_loan_severe = max_loan_from_revenue(severe_min_rev)

    return {
        "debt_structure": {
            "loan_amount": loan_amount,
            "interest_rate_pct": interest_rate * 100,
            "tenor_years": loan_tenor_years,
            "annual_debt_service": annual_debt_service
        },
        "dscr_scenarios": {
            "base_case": base_dscr_y1,
            "downside": downside_dscr_y1,
            "severe_downside": severe_dscr_y1
        },
        "flags": {
            "base_case": get_flag(base_dscr_y1),
            "downside": get_flag(downside_dscr_y1),
            "severe_downside": get_flag(severe_dscr_y1)
        },
        "summary": summary,
        "deal_assessment": deal_assessment,
        "dscr_schedule": dscr_schedule,
        "minimum_dscr": minimum_dscr,
        "debt_sizing": {
            "min_dscr_threshold": min_acceptable_dscr,
            "max_supportable_loan": {
                "base_case": max_loan_base,
                "downside": max_loan_downside,
                "severe_downside": max_loan_severe
            },
            "note": "Sized against minimum revenue year across project life"
        }
    }