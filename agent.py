import os
import json
from anthropic import Anthropic
from dotenv import load_dotenv
from tools.price_data import get_spread_analysis, get_seasonal_analysis
from tools.revenue_model import calculate_revenue
from tools.dscr import calculate_dscr
from tools.gas_prices import get_gas_prices
from tools.news_monitor import get_policy_news
from memory import save_snapshot, load_snapshot, format_memory_context

load_dotenv()

# ── INITIALISE CLIENT ───────────────────────────────────────────────

client = Anthropic()

# ── SYSTEM PROMPT ───────────────────────────────────────────────────

SYSTEM_PROMPT = """You are a project finance analyst specialising in battery energy 
storage systems (BESS) in the Italian electricity market. You work for an 
infrastructure advisory team — similar to a Big 4 TAS practice or a project 
finance desk at a bank like BNP Paribas or Natixis.

You have access to six tools:

1. get_spread_analysis — fetches live Italian day-ahead power prices from ENTSO-E 
   and calculates daily arbitrage spread statistics over a rolling 30-day window

2. get_seasonal_analysis — fetches 12 months of Italian power prices and calculates 
   spread statistics broken down by season. Returns the annual weighted average 
   spread which is more accurate for long-term revenue modelling

3. calculate_revenue — models annual BESS revenue with a full 15-year degradation 
   schedule. Accepts an override_avg_spread parameter so you can pass in any 
   spread value directly — use this with the seasonal average, stress scenarios, 
   or multi-year compression modelling. Never hardcode spreads.

4. calculate_dscr — calculates DSCR for every year of the project life. Identifies 
   the minimum DSCR year which is what lenders actually underwrite against

5. get_gas_prices — fetches TTF natural gas futures prices as a leading indicator 
   of spread compression risk

6. get_policy_news — searches the web for recent Italian BESS policy news

IMPORTANT RULES ON SPREAD INPUTS:
- For current market monitoring: use get_spread_analysis then calculate_revenue normally
- For annual revenue forecasting: use get_seasonal_analysis, then pass 
  annual_avg_spread as override_avg_spread into calculate_revenue
- For stress tests: pass a custom spread directly via override_avg_spread
- Never use the 30-day rolling average as a proxy for annual revenue

When asked for a full analysis, always run all six tools and present both the 
current market picture (30-day) and the annual reality (seasonal average).

Interpret results like a professional analyst. Reference actual numbers, explain 
what they mean for bankability, and suggest what a lender or developer would do.

If a previous snapshot exists in context, compare and flag meaningful changes.

Current market context:
- Italian BESS market growing rapidly — over 1GW installed as of March 2025
- MACSE scheme offers 15-year contracts, improving bankability significantly
- Solar cannibalisation driving midday price crashes — widening spreads
- TTF gas prices influence evening peaks — key risk to monitor
- Strong seasonality — spring spreads ~2x winter spreads
- Spread compression is the central long-term risk for merchant BESS
- Standard DSCR thresholds: 1.30x minimum, 1.20x absolute floor"""

# ── TOOL DEFINITIONS ────────────────────────────────────────────────

TOOLS = [
    {
        "name": "get_spread_analysis",
        "description": """Fetches live day-ahead electricity prices for Northern Italy 
        (IT-NORTH bidding zone) from the ENTSO-E Transparency Platform and calculates 
        daily arbitrage spread statistics over a rolling 30-day window. Use this for 
        current market monitoring. For annual revenue forecasting use 
        get_seasonal_analysis instead.""",
        "input_schema": {
            "type": "object",
            "properties": {
                "days": {
                    "type": "integer",
                    "description": "Number of historical days to analyse (default 30)"
                }
            },
            "required": []
        }
    },
    {
        "name": "get_seasonal_analysis",
        "description": """Fetches 12 months of Italian day-ahead power prices and 
        calculates spread statistics broken down by season. Returns the annual 
        weighted average spread — use this as the input to calculate_revenue via 
        override_avg_spread for defensible annual revenue forecasting. Always use 
        this instead of the 30-day window when building a project finance model.""",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "calculate_revenue",
        "description": """Calculates projected annual revenue for a BESS project with 
        a full 15-year degradation schedule. 

        SPREAD INPUT PRIORITY:
        1. If override_avg_spread is provided — use that spread directly
        2. Otherwise use spread_analysis input from get_spread_analysis

        Always use override_avg_spread when you want to model with the seasonal 
        average, a stressed spread, or any custom scenario. This ensures the model 
        never hardcodes assumptions.""",
        "input_schema": {
            "type": "object",
            "properties": {
                "capacity_mwh": {
                    "type": "number",
                    "description": "Battery energy capacity in MWh (default 50)"
                },
                "power_capacity_mw": {
                    "type": "number",
                    "description": "Battery power capacity in MW (default 25)"
                },
                "efficiency": {
                    "type": "number",
                    "description": "Round-trip efficiency as decimal (default 0.85)"
                },
                "cycles_per_day": {
                    "type": "number",
                    "description": "Number of daily charge/discharge cycles (default 1.0)"
                },
                "capture_rate": {
                    "type": "number",
                    "description": "Fraction of theoretical spread captured (default 0.75)"
                },
                "ancillary_revenue_per_mw_year": {
                    "type": "number",
                    "description": "Annual ancillary service payment per MW in euros (default 60000)"
                },
                "override_avg_spread": {
                    "type": "number",
                    "description": "Optional — override the spread with a custom value in €/MWh. Use this when modelling with seasonal average, stress scenarios, or multi-year spread compression. Pass seasonal annual_avg_spread here for annual forecasting."
                },
                "override_std_spread": {
                    "type": "number",
                    "description": "Optional — override the standard deviation for scenario construction. Defaults to 30% of override_avg_spread if not provided."
                }
            },
            "required": []
        }
    },
    {
        "name": "calculate_dscr",
        "description": """Calculates Debt Service Coverage Ratio for every year of 
        the project life using the degradation schedule from calculate_revenue. 
        Identifies the minimum DSCR year — the number lenders actually underwrite 
        against. Flags GREEN (>=1.30x), AMBER (1.20-1.30x), or RED (<1.20x). 
        Sizes maximum supportable loan against the worst revenue year.""",
        "input_schema": {
            "type": "object",
            "properties": {
                "loan_amount": {
                    "type": "number",
                    "description": "Total loan amount in euros (default 17500000)"
                },
                "interest_rate": {
                    "type": "number",
                    "description": "Annual interest rate as decimal (default 0.06)"
                },
                "loan_tenor_years": {
                    "type": "integer",
                    "description": "Loan repayment period in years (default 15)"
                }
            },
            "required": []
        }
    },
    {
        "name": "get_gas_prices",
        "description": """Fetches TTF natural gas futures prices and calculates 
        trend analysis. TTF is the primary driver of Italian evening peak power 
        prices and a leading indicator of spread compression risk.""",
        "input_schema": {
            "type": "object",
            "properties": {
                "days": {
                    "type": "integer",
                    "description": "Number of historical days to analyse (default 30)"
                }
            },
            "required": []
        }
    },
    {
        "name": "get_policy_news",
        "description": """Searches the web for recent news relevant to Italian BESS 
        project finance — MACSE auctions, Terna announcements, EU policy changes, 
        and market developments.""",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    }
]

# ── TOOL EXECUTION ──────────────────────────────────────────────────

def execute_tool(tool_name: str, tool_input: dict, spread_data=None, revenue_data=None, gas_data=None):
    if tool_name == "get_spread_analysis":
        days = tool_input.get("days", 30)
        result = get_spread_analysis(days=days)
        return result

    elif tool_name == "get_seasonal_analysis":
        result = get_seasonal_analysis()
        return result

    elif tool_name == "calculate_revenue":
        result = calculate_revenue(
            spread_analysis=spread_data or {},
            capacity_mwh=tool_input.get("capacity_mwh", 50.0),
            power_capacity_mw=tool_input.get("power_capacity_mw", 25.0),
            efficiency=tool_input.get("efficiency", 0.85),
            cycles_per_day=tool_input.get("cycles_per_day", 1.0),
            capture_rate=tool_input.get("capture_rate", 0.75),
            ancillary_revenue_per_mw_year=tool_input.get("ancillary_revenue_per_mw_year", 60000),
            override_avg_spread=tool_input.get("override_avg_spread", None),
            override_std_spread=tool_input.get("override_std_spread", None)
        )
        return result

    elif tool_name == "calculate_dscr":
        if revenue_data is None:
            return {"error": "Must run calculate_revenue first"}
        result = calculate_dscr(
            revenue_model=revenue_data,
            loan_amount=tool_input.get("loan_amount", 17_500_000),
            interest_rate=tool_input.get("interest_rate", 0.06),
            loan_tenor_years=tool_input.get("loan_tenor_years", 15)
        )
        return result

    elif tool_name == "get_gas_prices":
        days = tool_input.get("days", 30)
        result = get_gas_prices(days=days)
        return result

    elif tool_name == "get_policy_news":
        result = get_policy_news()
        return result

    else:
        return {"error": f"Unknown tool: {tool_name}"}


# ── CONVERSATION LOOP ───────────────────────────────────────────────

def run_agent():
    print("\n" + "=" * 60)
    print("BESS Project Finance Agent — IT-NORTH")
    print("=" * 60)
    print("Ask me anything about Italian battery storage project finance.")
    print("Type 'exit' to quit.\n")

    conversation_history = []
    spread_data = None
    revenue_data = None
    gas_data = None
    dscr_data = None

    previous_snapshot = load_snapshot()
    memory_context = format_memory_context(previous_snapshot)

    while True:
        user_input = input("You: ").strip()

        if user_input.lower() in ["exit", "quit", "q"]:
            print("Goodbye.")
            break

        if not user_input:
            continue

        conversation_history.append({
            "role": "user",
            "content": user_input
        })

        while True:
            response = client.messages.create(
                model="claude-sonnet-4-5",
                max_tokens=4096,
                system=SYSTEM_PROMPT + f"\n\n{memory_context}",
                tools=TOOLS,
                messages=conversation_history
            )

            if response.stop_reason == "tool_use":
                conversation_history.append({
                    "role": "assistant",
                    "content": response.content
                })

                tool_results = []

                for block in response.content:
                    if block.type == "tool_use":
                        tool_name = block.name
                        tool_input = block.input

                        print(f"\n[Agent calling: {tool_name}...]")

                        result = execute_tool(
                            tool_name,
                            tool_input,
                            spread_data=spread_data,
                            revenue_data=revenue_data,
                            gas_data=gas_data
                        )

                        if tool_name == "get_spread_analysis":
                            spread_data = result
                        elif tool_name == "calculate_revenue":
                            revenue_data = result
                        elif tool_name == "get_gas_prices":
                            gas_data = result
                        elif tool_name == "calculate_dscr":
                            dscr_data = result
                            if spread_data and revenue_data and gas_data:
                                save_snapshot(spread_data, revenue_data, result, gas_data)
                                print("[Memory saved]")

                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": json.dumps(result)
                        })

                conversation_history.append({
                    "role": "user",
                    "content": tool_results
                })

            else:
                assistant_message = ""
                for block in response.content:
                    if hasattr(block, "text"):
                        assistant_message += block.text

                print(f"\nAgent: {assistant_message}\n")

                conversation_history.append({
                    "role": "assistant",
                    "content": assistant_message
                })

                break


# ── ENTRY POINT ─────────────────────────────────────────────────────

if __name__ == "__main__":
    run_agent()