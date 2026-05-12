import os
import json
import glob
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()

app = Flask(__name__, static_folder='static')
CORS(app)

client = Anthropic()

# ── IMPORT OUR TOOLS ────────────────────────────────────────────────

from tools.price_data import get_spread_analysis, get_seasonal_analysis
from tools.revenue_model import calculate_revenue
from tools.dscr import calculate_dscr
from tools.gas_prices import get_gas_prices
from tools.news_monitor import get_policy_news
from memory import load_snapshot, save_snapshot, format_memory_context

# ── AGENT SETUP ─────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are a project finance analyst specialising in battery energy 
storage systems (BESS) in the Italian electricity market. You work for an 
infrastructure advisory team — similar to a Big 4 TAS practice or a project 
finance desk at a bank like BNP Paribas or Natixis.

You have access to six tools:
1. get_spread_analysis — live Italian power price spreads (30-day rolling)
2. get_seasonal_analysis — 12-month seasonal spread breakdown
3. calculate_revenue — 15-year revenue model with degradation and spread compression
4. calculate_dscr — year-by-year DSCR schedule with minimum DSCR identification
5. get_gas_prices — TTF gas prices as leading indicator
6. get_policy_news — web search for Italian BESS policy news

Key assumptions for this project:
- 50 MWh / 25 MW battery, 2-hour duration, LFP chemistry
- 85% round-trip efficiency, 1.0 cycle/day, 75% capture rate
- €60,000/MW/year ancillary services (Terna MSD market)
- 2% annual battery degradation, 1% annual spread compression
- €14M loan, 6% interest, 15-year tenor → €1,440,000 annual debt service
- Base case uses seasonal weighted average spread (~€76/MWh)
- DSCR thresholds: 1.30x minimum, 1.20x absolute floor

Always use override_avg_spread with the seasonal average for annual revenue 
forecasting. Never use the 30-day spring snapshot as a proxy for annual revenue.

Be concise in dashboard responses — users can see the charts already."""

TOOLS = [
    {
        "name": "get_spread_analysis",
        "description": "Fetches live Italian day-ahead power prices and calculates 30-day spread statistics.",
        "input_schema": {
            "type": "object",
            "properties": {
                "days": {"type": "integer", "description": "Days to analyse (default 30)"}
            },
            "required": []
        }
    },
    {
        "name": "get_seasonal_analysis",
        "description": "Fetches 12 months of Italian power prices and calculates seasonal spread breakdown.",
        "input_schema": {"type": "object", "properties": {}, "required": []}
    },
    {
        "name": "calculate_revenue",
        "description": "Models 15-year BESS revenue with degradation and spread compression.",
        "input_schema": {
            "type": "object",
            "properties": {
                "override_avg_spread": {"type": "number", "description": "Custom spread in €/MWh"},
                "spread_compression_rate": {"type": "number", "description": "Annual compression (default 0.01)"},
                "capacity_mwh": {"type": "number"},
                "capture_rate": {"type": "number"},
                "ancillary_revenue_per_mw_year": {"type": "number"}
            },
            "required": []
        }
    },
    {
        "name": "calculate_dscr",
        "description": "Calculates year-by-year DSCR across project life. Identifies minimum DSCR year.",
        "input_schema": {
            "type": "object",
            "properties": {
                "loan_amount": {"type": "number"},
                "interest_rate": {"type": "number"},
                "loan_tenor_years": {"type": "integer"}
            },
            "required": []
        }
    },
    {
        "name": "get_gas_prices",
        "description": "Fetches TTF natural gas futures prices and trend analysis.",
        "input_schema": {
            "type": "object",
            "properties": {
                "days": {"type": "integer"}
            },
            "required": []
        }
    },
    {
        "name": "get_policy_news",
        "description": "Searches web for recent Italian BESS policy news and market developments.",
        "input_schema": {"type": "object", "properties": {}, "required": []}
    }
]

def execute_tool(tool_name, tool_input, spread_data=None, revenue_data=None, gas_data=None):
    if tool_name == "get_spread_analysis":
        return get_spread_analysis(days=tool_input.get("days", 30))
    elif tool_name == "get_seasonal_analysis":
        return get_seasonal_analysis()
    elif tool_name == "calculate_revenue":
        return calculate_revenue(
            spread_analysis=spread_data or {},
            capacity_mwh=tool_input.get("capacity_mwh", 50.0),
            capture_rate=tool_input.get("capture_rate", 0.75),
            ancillary_revenue_per_mw_year=tool_input.get("ancillary_revenue_per_mw_year", 60000),
            spread_compression_rate=tool_input.get("spread_compression_rate", 0.01),
            override_avg_spread=tool_input.get("override_avg_spread", None)
        )
    elif tool_name == "calculate_dscr":
        if revenue_data is None:
            return {"error": "Must run calculate_revenue first"}
        return calculate_dscr(
            revenue_model=revenue_data,
            loan_amount=tool_input.get("loan_amount", 14_000_000),
            interest_rate=tool_input.get("interest_rate", 0.06),
            loan_tenor_years=tool_input.get("loan_tenor_years", 15)
        )
    elif tool_name == "get_gas_prices":
        return get_gas_prices(days=tool_input.get("days", 30))
    elif tool_name == "get_policy_news":
        return get_policy_news()
    return {"error": f"Unknown tool: {tool_name}"}


# ── API ENDPOINTS ────────────────────────────────────────────────────

@app.route('/api/status')
def api_status():
    """Current market vitals — spread, gas, DSCR"""
    try:
        spread_data = get_spread_analysis(days=30)
        gas_data = get_gas_prices(days=30)
        revenue_data = calculate_revenue(
            spread_analysis={},
            override_avg_spread=76.15,
            spread_compression_rate=0.01
        )
        dscr_data = calculate_dscr(revenue_data)
        return jsonify({
            "avg_spread": spread_data["avg_spread"],
            "ttf_price": gas_data["current_price"],
            "ttf_trend": gas_data["trend"],
            "ttf_change_pct": gas_data["change_pct"],
            "base_dscr": dscr_data["dscr_scenarios"]["base_case"],
            "base_flag": dscr_data["flags"]["base_case"],
            "min_dscr": dscr_data["minimum_dscr"]["base_case"]["dscr"],
            "min_dscr_year": dscr_data["minimum_dscr"]["base_case"]["year"],
            "deal_assessment": dscr_data["deal_assessment"]
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/spreads')
def api_spreads():
    """30-day daily spread chart data"""
    try:
        data = get_spread_analysis(days=30)
        return jsonify({
            "dates": list(data["daily_spreads"].keys()),
            "spreads": list(data["daily_spreads"].values()),
            "avg_spread": data["avg_spread"],
            "std_spread": data["std_spread"]
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/dscr_trajectory')
def api_dscr_trajectory():
    """15-year DSCR trajectory for all three scenarios"""
    try:
        revenue_data = calculate_revenue(
            spread_analysis={},
            override_avg_spread=76.15,
            spread_compression_rate=0.01
        )
        dscr_data = calculate_dscr(revenue_data)
        return jsonify({
            "years": list(range(1, 16)),
            "base_case": dscr_data["dscr_schedule"]["base_case"],
            "downside": dscr_data["dscr_schedule"]["downside"],
            "severe_downside": dscr_data["dscr_schedule"]["severe_downside"],
            "min_threshold": 1.30,
            "floor_threshold": 1.20
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/seasonal')
def api_seasonal():
    """Seasonal spread breakdown"""
    try:
        data = get_seasonal_analysis()
        return jsonify({
            "seasons": ["spring", "summer", "autumn", "winter"],
            "spreads": [
                data["seasonal_spreads"]["spring"],
                data["seasonal_spreads"]["summer"],
                data["seasonal_spreads"]["autumn"],
                data["seasonal_spreads"]["winter"]
            ],
            "days": [
                data["seasonal_days"]["spring"],
                data["seasonal_days"]["summer"],
                data["seasonal_days"]["autumn"],
                data["seasonal_days"]["winter"]
            ],
            "annual_avg": data["annual_avg_spread"],
            "seasonality_factor": data["seasonality_factor"],
            "seasonality_note": data["seasonality_note"]
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/news')
def api_news():
    """Latest policy news"""
    try:
        data = get_policy_news()
        return jsonify({
            "sentiment": data["overall_sentiment"],
            "policy_signals": data["policy_signals_detected"],
            "market_signals": data["market_signals_detected"],
            "summary": data["summary"],
            "full_analysis": data["raw_analysis"][:2000]
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/report')
def api_report():
    """Latest daily report"""
    try:
        reports = sorted(glob.glob('reports/report_*.md'), reverse=True)
        if not reports:
            return jsonify({"content": "No reports generated yet. Run daily_report.py first."})
        with open(reports[0], 'r') as f:
            content = f.read()
        return jsonify({
            "content": content,
            "filename": os.path.basename(reports[0])
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/chat', methods=['POST'])
def api_chat():
    """Chat with the agent"""
    try:
        data = request.json
        messages = data.get('messages', [])
        previous_snapshot = load_snapshot()
        memory_context = format_memory_context(previous_snapshot)

        spread_data = None
        revenue_data = None
        gas_data = None

        while True:
            response = client.messages.create(
                model="claude-sonnet-4-5",
                max_tokens=4096,
                system=SYSTEM_PROMPT + f"\n\n{memory_context}",
                tools=TOOLS,
                messages=messages
            )

            if response.stop_reason == "tool_use":
                messages.append({"role": "assistant", "content": response.content})
                tool_results = []

                for block in response.content:
                    if block.type == "tool_use":
                        result = execute_tool(
                            block.name, block.input,
                            spread_data=spread_data,
                            revenue_data=revenue_data,
                            gas_data=gas_data
                        )
                        if block.name == "get_spread_analysis":
                            spread_data = result
                        elif block.name == "calculate_revenue":
                            revenue_data = result
                        elif block.name == "get_gas_prices":
                            gas_data = result
                        elif block.name == "calculate_dscr" and spread_data and revenue_data and gas_data:
                            save_snapshot(spread_data, revenue_data, result, gas_data)

                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": json.dumps(result)
                        })

                messages.append({"role": "user", "content": tool_results})

            else:
                assistant_message = ""
                for block in response.content:
                    if hasattr(block, "text"):
                        assistant_message += block.text

                messages.append({"role": "assistant", "content": assistant_message})
                return jsonify({
                    "response": assistant_message,
                    "messages": messages
                })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── SERVE DASHBOARD ──────────────────────────────────────────────────

@app.route('/')
def index():
    return send_from_directory('static', 'index.html')


if __name__ == '__main__':
    os.makedirs('static', exist_ok=True)
    print("\n" + "="*50)
    print("BESS Project Finance Dashboard")
    print("="*50)
    print("Starting server at http://localhost:5000")
    print("="*50 + "\n")
    app.run(debug=True, port=5000)