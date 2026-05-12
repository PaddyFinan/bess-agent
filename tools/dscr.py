def calculate_dscr(
    revenue_model: dict,
    loan_amount: float = 17_500_000,
    interest_rate: float = 0.06,
    loan_tenor_years: int = 15
) -> dict:
    """
    Calculates Debt Service Coverage Ratio (DSCR) for a BESS project
    across base case, downside, and severe downside scenarios.

    Takes the output of calculate_revenue() as its primary input.
    DSCR = Annual Revenue / Annual Debt Service

    Also calculates maximum supportable loan at 1.30x DSCR threshold —
    working backwards from revenue to determine optimal debt sizing.

    Industry thresholds:
    - DSCR >= 1.30x: Green — comfortable, bankable
    - DSCR 1.20x-1.30x: Amber — acceptable but tight
    - DSCR < 1.20x: Red — breach, project cannot be financed

    Args:
        revenue_model: Dictionary returned by calculate_revenue()
        loan_amount: Total debt in euros (default €17.5m = 70% of €25m project)
        interest_rate: Annual interest rate as decimal (default 0.06 = 6%)
        loan_tenor_years: Loan repayment period in years (default 15)

    Returns:
        Dictionary containing:
        - debt_structure: loan details and annual debt service
        - dscr_scenarios: DSCR for each revenue scenario
        - flags: green/amber/red status for each scenario
        - summary: plain English interpretation
        - deal_assessment: overall bankability verdict
        - debt_sizing: maximum supportable loan at 1.30x DSCR
    """

    # ── ANNUAL DEBT SERVICE ─────────────────────────────────────────
    # Annuity formula: fixed annual payment covering interest + principal
    # Payment = Loan × [r(1+r)^n] / [(1+r)^n - 1]

    r = interest_rate
    n = loan_tenor_years
    annual_debt_service = loan_amount * (r * (1 + r)**n) / ((1 + r)**n - 1)
    annual_debt_service = round(annual_debt_service, 0)

    # ── EXTRACT ANNUAL REVENUES FROM TOOL 2 OUTPUT ─────────────────

    base_revenue = revenue_model["annual_revenue"]["base_case"]
    downside_revenue = revenue_model["annual_revenue"]["downside"]
    severe_revenue = revenue_model["annual_revenue"]["severe_downside"]

    # ── CALCULATE DSCR FOR EACH SCENARIO ───────────────────────────

    base_dscr = round(base_revenue / annual_debt_service, 2)
    downside_dscr = round(downside_revenue / annual_debt_service, 2)
    severe_dscr = round(severe_revenue / annual_debt_service, 2)

    # ── FLAG EACH SCENARIO ──────────────────────────────────────────

    def get_flag(dscr):
        if dscr >= 1.30:
            return "GREEN"
        elif dscr >= 1.20:
            return "AMBER"
        else:
            return "RED"

    base_flag = get_flag(base_dscr)
    downside_flag = get_flag(downside_dscr)
    severe_flag = get_flag(severe_dscr)

    # ── PLAIN ENGLISH SUMMARY ───────────────────────────────────────

    def interpret_dscr(scenario, dscr, flag):
        if flag == "GREEN":
            return (f"{scenario}: DSCR of {dscr}x — comfortable. Project generates "
                   f"€{dscr:.2f} for every €1.00 of debt service. Bankable.")
        elif flag == "AMBER":
            return (f"{scenario}: DSCR of {dscr}x — tight but acceptable. Project is "
                   f"at the margin of bankability. Lender may require reserves.")
        else:
            return (f"{scenario}: DSCR of {dscr}x — breach. Project cannot service "
                   f"its debt under these conditions. Deal restructuring required.")

    summary = [
        interpret_dscr("Base case", base_dscr, base_flag),
        interpret_dscr("Downside", downside_dscr, downside_flag),
        interpret_dscr("Severe downside", severe_dscr, severe_flag)
    ]

    # ── OVERALL DEAL ASSESSMENT ─────────────────────────────────────

    if base_flag == "GREEN" and downside_flag in ["GREEN", "AMBER"]:
        deal_assessment = "BANKABLE — project supports debt financing under base and downside scenarios"
    elif base_flag in ["GREEN", "AMBER"] and severe_flag != "RED":
        deal_assessment = "CONDITIONALLY BANKABLE — lender protections likely required"
    else:
        deal_assessment = "NOT BANKABLE — revenue insufficient to support proposed debt structure"

    # ── MAXIMUM SUPPORTABLE DEBT ────────────────────────────────────
    # Works backwards from revenue to find the largest loan the project
    # can support at the minimum acceptable DSCR of 1.30x
    # Rearranged annuity formula: Loan = Payment × [(1+r)^n-1] / [r(1+r)^n]

    min_acceptable_dscr = 1.30

    def max_loan_from_revenue(annual_rev):
        max_debt_service = annual_rev / min_acceptable_dscr
        return round(max_debt_service * ((1 + r)**n - 1) / (r * (1 + r)**n), 0)

    max_loan_base = max_loan_from_revenue(base_revenue)
    max_loan_downside = max_loan_from_revenue(downside_revenue)
    max_loan_severe = max_loan_from_revenue(severe_revenue)

    return {
        "debt_structure": {
            "loan_amount": loan_amount,
            "interest_rate_pct": interest_rate * 100,
            "tenor_years": loan_tenor_years,
            "annual_debt_service": annual_debt_service
        },
        "dscr_scenarios": {
            "base_case": base_dscr,
            "downside": downside_dscr,
            "severe_downside": severe_dscr
        },
        "flags": {
            "base_case": base_flag,
            "downside": downside_flag,
            "severe_downside": severe_flag
        },
        "summary": summary,
        "deal_assessment": deal_assessment,
        "debt_sizing": {
            "min_dscr_threshold": min_acceptable_dscr,
            "max_supportable_loan": {
                "base_case": max_loan_base,
                "downside": max_loan_downside,
                "severe_downside": max_loan_severe
            },
            "note": "Maximum loan supportable at 1.30x DSCR minimum threshold"
        }
    }