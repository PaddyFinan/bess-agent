import os
import json
from anthropic import Anthropic
from dotenv import load_dotenv
from tools.price_data import get_spread_analysis
from tools.revenue_model import calculate_revenue
from tools.dscr import calculate_dscr

load_dotenv()

# ── INITIALISE CLIENT ───────────────────────────────────────────────

client = Anthropic()

# ── SYSTEM PROMPT ───────────────────────────────────────────────────
# This tells Claude who it is and how to behave

SYSTEM_PROMPT = """You are a project finance analyst specialising in battery energy 
storage systems (BESS) in the Italian electricity market. You work for an 
infrastructure advisory team — similar to a Big 4 TAS practice or a project 
finance desk at a bank like BNP Paribas or Natixis.

You have access to three tools:

1. get_spread_analysis — fetches live Italian day-ahead power prices from ENTSO-E 
   and calculates daily arbitrage spread statistics over a rolling window

2. calculate_revenue — models annual BESS revenue by stacking energy arbitrage 
   and ancillary services income across base case, downside, and severe downside 
   scenarios

3. calculate_dscr — calculates Debt Service Coverage Ratio across all three 
   scenarios, flags bankability, and sizes the maximum supportable debt at a 
   1.30x DSCR threshold

When asked about a project, always run the full analysis chain: spreads → revenue 
→ DSCR. Interpret the results like a professional analyst — don't just recite 
numbers, explain what they mean for the project's bankability and risk profile.

When flagging risks, be specific: reference the actual numbers, explain why they 
matter, and suggest what a lender or developer would do in response.

Current market context you should weave into your analysis:
- Italian BESS market is growing rapidly — over 1GW installed as of March 2025
- MACSE scheme offers 15-year contracts, improving project bankability significantly
- Solar cannibalisation is driving midday price crashes in Italy, widening spreads
- TTF gas prices influence evening peak power prices — a key risk to monitor
- Spread compression is the central long-term risk for merchant BESS projects
- Standard project finance DSCR thresholds: 1.30x minimum, 1.20x absolute floor"""

# ── TOOL DEFINITIONS ────────────────────────────────────────────────
# These tell Claude what tools exist and when to use them

TOOLS = [
    {
        "name": "get_spread_analysis",
        "description": """Fetches live day-ahead electricity prices for Northern Italy 
        (IT-NORTH bidding zone) from the ENTSO-E Transparency Platform and calculates 
        daily arbitrage spread statistics. Returns average, minimum, maximum, and 
        standard deviation of daily spreads over the specified window. Use this first 
        whenever analysing current market conditions or starting a project assessment.""",
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
        "name": "calculate_revenue",
        "description": """Calculates projected annual revenue for a BESS project by 
        stacking energy arbitrage revenue (from power price spreads) and ancillary 
        services revenue (frequency regulation payments from Terna). Returns revenue 
        across base case, downside, and severe downside scenarios. Use this after 
        get_spread_analysis to model project economics.""",
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
                }
            },
            "required": []
        }
    },
    {
        "name": "calculate_dscr",
        "description": """Calculates Debt Service Coverage Ratio (DSCR) for a BESS 
        project across base case, downside, and severe downside scenarios. Flags each 
        scenario as GREEN (>=1.30x), AMBER (1.20-1.30x), or RED (<1.20x). Also sizes 
        the maximum supportable loan at a 1.30x DSCR threshold. Use this after 
        calculate_revenue to assess project bankability.""",
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
    }
]

# ── TOOL EXECUTION ──────────────────────────────────────────────────
# This function runs whichever tool Claude decides to call

def execute_tool(tool_name: str, tool_input: dict, spread_data=None, revenue_data=None):
    """
    Executes the named tool with the given inputs.
    Passes previously computed data between tools so they chain correctly.
    """
    if tool_name == "get_spread_analysis":
        days = tool_input.get("days", 30)
        result = get_spread_analysis(days=days)
        return result

    elif tool_name == "calculate_revenue":
        if spread_data is None:
            return {"error": "Must run get_spread_analysis first"}
        result = calculate_revenue(
            spread_analysis=spread_data,
            capacity_mwh=tool_input.get("capacity_mwh", 50.0),
            power_capacity_mw=tool_input.get("power_capacity_mw", 25.0),
            efficiency=tool_input.get("efficiency", 0.85),
            cycles_per_day=tool_input.get("cycles_per_day", 1.0),
            capture_rate=tool_input.get("capture_rate", 0.75),
            ancillary_revenue_per_mw_year=tool_input.get("ancillary_revenue_per_mw_year", 60000)
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

    else:
        return {"error": f"Unknown tool: {tool_name}"}


# ── CONVERSATION LOOP ───────────────────────────────────────────────

def run_agent():
    """
    Runs the BESS project finance agent as a conversation.
    Claude can call tools multiple times and chain them together.
    """
    print("\n" + "=" * 60)
    print("BESS Project Finance Agent — IT-NORTH")
    print("=" * 60)
    print("Ask me anything about Italian battery storage project finance.")
    print("Type 'exit' to quit.\n")

    conversation_history = []

    # Store tool results so they can be passed between tools
    spread_data = None
    revenue_data = None

    while True:
        # Get user input
        user_input = input("You: ").strip()

        if user_input.lower() in ["exit", "quit", "q"]:
            print("Goodbye.")
            break

        if not user_input:
            continue

        # Add user message to history
        conversation_history.append({
            "role": "user",
            "content": user_input
        })

        # ── AGENTIC LOOP ────────────────────────────────────────────
        # Keep going until Claude stops calling tools

        while True:
            response = client.messages.create(
                model="claude-sonnet-4-5",
                max_tokens=4096,
                system=SYSTEM_PROMPT,
                tools=TOOLS,
                messages=conversation_history
            )

            # Check if Claude wants to call a tool
            if response.stop_reason == "tool_use":

                # Add Claude's response to history
                conversation_history.append({
                    "role": "assistant",
                    "content": response.content
                })

                # Process each tool call
                tool_results = []

                for block in response.content:
                    if block.type == "tool_use":
                        tool_name = block.name
                        tool_input = block.input

                        print(f"\n[Agent calling: {tool_name}...]")

                        # Execute the tool
                        result = execute_tool(
                            tool_name,
                            tool_input,
                            spread_data=spread_data,
                            revenue_data=revenue_data
                        )

                        # Store results for chaining
                        if tool_name == "get_spread_analysis":
                            spread_data = result
                        elif tool_name == "calculate_revenue":
                            revenue_data = result

                        # Add result to tool results list
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": json.dumps(result)
                        })

                # Add tool results to history
                conversation_history.append({
                    "role": "user",
                    "content": tool_results
                })

            # Claude has finished — print the response
            else:
                assistant_message = ""
                for block in response.content:
                    if hasattr(block, "text"):
                        assistant_message += block.text

                print(f"\nAgent: {assistant_message}\n")

                # Add to history for next turn
                conversation_history.append({
                    "role": "assistant",
                    "content": assistant_message
                })

                break


# ── ENTRY POINT ─────────────────────────────────────────────────────

if __name__ == "__main__":
    run_agent()