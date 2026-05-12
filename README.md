# BESS Project Finance Agent

An autonomous AI agent that monitors Italian battery storage project finance in real time. Pulls live market data, models revenue across a 15-year degradation and spread compression curve, stress tests debt coverage, monitors policy news, and generates daily reports — without any manual input.

Built in Python using the Anthropic Claude API with autonomous tool use, GitHub Actions scheduling, and a live web dashboard.

---

## What this is

I'm a 22 year old economics student heading to Bocconi to study Accounting and Financial Management, with a focus on breaking into renewable energy finance. I built this project to teach myself AI agent development while actually learning the domain I want to work in.

The idea came from a simple question: what does a junior analyst actually do when they're stress testing a battery storage deal? They pull market data, model revenue across the project life, calculate DSCRs, monitor policy risk, and flag when something changes. So I built an agent that does exactly that — autonomously, from a plain English question.

---

## Live Dashboard

Run `python app.py` and open `http://localhost:5000` to see the live dashboard.

It shows:
- **Live market vitals** — current Italian power spread, TTF gas price, base case DSCR, minimum DSCR across project life
- **30-day spread chart** — daily arbitrage spread history with average line
- **15-year DSCR trajectory** — all three scenarios with degradation and compression, covenant threshold lines
- **Seasonal spread analysis** — spring/summer/autumn/winter breakdown with annual weighted average
- **Policy & market news** — real-time web search results with sentiment analysis
- **Latest daily report** — the most recent autonomous morning report
- **Chat with the agent** — conversational interface to all six tools

Every panel has a plain English explanation accessible via the ⓘ icon.

---

## Two ways to use it

**Conversational mode** — run `agent.py` and ask questions in plain English:

- *"Analyse the project using the seasonal average spread"*
- *"What happens if we increase the loan to €18 million?"*
- *"What would a bank say about the debt sizing?"*
- *"Model a 100 MWh project with 65% capture rate"*
- *"What if spread compression is 3% per year?"*
- *"What is the latest policy news affecting this project?"*

Claude decides which tools to call, chains them together, and produces written analysis. Every assumption is adjustable on the fly.

**Autonomous mode** — GitHub Actions runs `daily_report.py` every morning at 7am Italian time. It fetches fresh market data, runs the full analysis, compares results to the previous day, flags any meaningful changes, and commits the report directly to the repository. No laptop required.

---

## The finance logic

A battery storage project earns money by charging when electricity is cheap and discharging when it's expensive. The spread between those two prices is the arbitrage revenue. In Italy, solar panels flood the grid at midday pushing prices toward zero, then gas plants drive prices back up in the evening peak. That intraday spread is what the battery captures.

The project also earns ancillary services revenue — Terna (Italy's grid operator) pays batteries just to be available for frequency regulation, regardless of whether they actually discharge.

**Three compounding effects** erode revenue over the 15-year project life:

1. **Seasonality** — Italian spreads vary dramatically by season. Spring spreads (~€114/MWh) are more than double winter spreads (~€56/MWh). Using a spring snapshot as a proxy for annual revenue overstates it by ~38%. The model uses the annual weighted average (~€76/MWh) as the base case.

2. **Battery degradation** — LFP batteries lose ~2% of capacity per year. A battery that starts at 50 MWh in year 1 only delivers 37.7 MWh by year 15. Revenue declines proportionally.

3. **Spread compression** — As more batteries enter the Italian market, they compete for the same arbitrage opportunity. Spreads compress ~1% per year structurally. Combined with degradation, the project's revenue in year 15 is meaningfully lower than year 1.

Both degradation and compression compound simultaneously. This is why **lenders underwrite against the minimum DSCR year** (usually year 15), not the year 1 number. A deal that looks comfortable at year 1 can breach covenants by year 15 if these effects aren't modelled properly.

Combined revenue streams are stress tested against the project's debt service obligations. The key metric is the **Debt Service Coverage Ratio (DSCR)** — how many euros of revenue the project generates for every euro of debt it needs to repay.

---

## Architecture
agent.py                  ← Conversational interface with Claude
app.py                    ← Flask web dashboard server
daily_report.py           ← Autonomous scheduled run
memory.py                 ← Snapshot system for trend comparison
tools/
price_data.py         ← Tool 1: Live ENTSO-E power prices (30-day)
Tool 2: Seasonal analysis (12-month breakdown)
revenue_model.py      ← Tool 3: 15-year revenue with degradation + compression
dscr.py               ← Tool 4: Year-by-year DSCR schedule, minimum DSCR
gas_prices.py         ← Tool 5: TTF gas prices as leading indicator
news_monitor.py       ← Tool 6: Policy news via Claude web search
static/
index.html            ← Full dashboard UI
reports/                  ← Auto-generated daily reports
.github/workflows/
daily_report.yml      ← GitHub Actions scheduler (7am Italian time)

Claude receives tool definitions, autonomously decides which tools to call based on your question, chains them in sequence, and produces written analysis. The tools are all parameterised — Claude can adjust any assumption on the fly.

---

## The six tools

**Tool 1 — Italian power prices (30-day)**
Fetches live day-ahead electricity prices for the IT-NORTH bidding zone from ENTSO-E. Calculates daily arbitrage spread statistics — average, min, max, standard deviation, coefficient of variation. Excludes partial days and tomorrow's forecast data automatically.

**Tool 2 — Seasonal analysis (12-month)**
Fetches 12 months of IT-NORTH prices and breaks them down by season. Returns the annual weighted average spread — the correct input for long-term revenue modelling. Handles both 15-minute and hourly ENTSO-E data formats. Seasonality factor of ~2x between spring and winter.

**Tool 3 — Revenue model with degradation and compression**
Models annual BESS revenue by stacking energy arbitrage and ancillary services. Returns a full 15-year schedule showing how revenue declines as both battery capacity (degradation) and market spreads (compression) erode simultaneously. Accepts `override_avg_spread` so any spread assumption — seasonal average, stress test, or custom scenario — can be passed directly. Nothing is hardcoded.

**Tool 4 — DSCR calculator with 15-year schedule**
Calculates Debt Service Coverage Ratio for every year of the project life using the degradation and compression schedule. Identifies the minimum DSCR year — the number lenders actually underwrite against. Flags GREEN (≥1.30x), AMBER (1.20-1.29x), or RED (<1.20x). Sizes maximum supportable loan against the worst revenue year.

**Tool 5 — TTF gas prices**
Fetches TTF natural gas futures via Yahoo Finance. Returns current price, 30-day trend, and a plain English signal. TTF is the primary driver of Italian evening peak prices — a falling TTF is a leading indicator of spread compression before it shows up in ENTSO-E data.

**Tool 6 — Policy news monitor**
Uses Claude's built-in web search to find recent news relevant to Italian BESS project finance — MACSE auction results, Terna announcements, EU energy storage policy, TTF outlook. Returns structured analysis flagging each item as bullish, bearish, or neutral for project economics.

---

## Memory and monitoring

Every time a full analysis runs, the agent saves a snapshot to `memory.json`. The next run loads that snapshot and compares current numbers to previous numbers. Claude flags meaningful changes — DSCR deterioration, spread compression signals, gas price movements that indicate risk ahead.

---

## Autonomous scheduling

GitHub Actions runs the full analysis every morning at 7am Italian time on GitHub's servers. The workflow fetches live data from all six tools, generates a professional monitoring report, and commits it to the `reports/` folder automatically. Reports accumulate daily — building a record of how market conditions and project bankability evolve over time.

---

## Financial assumptions

| Assumption | Value | Source |
|---|---|---|
| Battery capacity | 50 MWh / 25 MW | Standard utility scale, 2-hour duration |
| Chemistry | LFP (Lithium Iron Phosphate) | Industry standard for utility BESS |
| Round-trip efficiency | 85% | Standard LFP assumption |
| Capture rate | 75% | Conservative merchant estimate |
| Cycles per day | 1.0 | Standard arbitrage operation |
| Battery degradation | 2% per year | Standard LFP degradation curve |
| Spread compression | 1% per year | Conservative Italian market assumption |
| Year 1 capacity | 50.0 MWh | — |
| Year 15 capacity | 37.7 MWh | After 14 years of 2% degradation |
| Ancillary services | €60,000/MW/year | 2024-2025 Italian capacity market auctions |
| Annual ancillary revenue | €1,500,000 (fixed) | 25 MW × €60k/MW/year |
| Total project cost | €25 million | 2026 installed cost benchmarks |
| Loan amount | €14 million | 56% gearing — appropriate for merchant BESS |
| Interest rate | 6.0% | EURIBOR ~2.88% + ~3% margin |
| Loan tenor | 15 years | Standard infrastructure project finance |
| Annual debt service | ~€1,440,000 | Annuity formula |
| DSCR minimum | 1.30x | Standard project finance threshold |
| DSCR floor | 1.20x | Absolute covenant breach level |

**Base case result:** BANKABLE — minimum DSCR 1.44x in year 15 (GREEN throughout project life)

---

## Data sources

- **Power prices**: ENTSO-E Transparency Platform — IT-NORTH bidding zone
- **Gas prices**: TTF futures via Yahoo Finance
- **Policy news**: Claude web search — real-time
- **Ancillary service rates**: Validated against 2024-2025 Italian capacity market auction results
- **Capital costs**: 2026 BESS installed cost benchmarks (€250-320/kWh equipment)
- **EURIBOR**: Live 12-month rate (~2.88% as of May 2026)

---

## How to run it

**1. Clone the repo**
```bash
git clone https://github.com/PaddyFinan/bess-agent.git
cd bess-agent
```

**2. Create a virtual environment**
```bash
python -m venv venv
source venv/bin/activate
```

**3. Install dependencies**
```bash
pip install -r requirements.txt
```

**4. Set up API keys**

Create a `.env` file:

ENTSO_E_API_KEY=your_entsoe_token
ANTHROPIC_API_KEY=your_anthropic_key

Get your ENTSO-E token by registering at transparency.entsoe.eu and emailing transparency@entsoe.eu to request API access.

**5. Run the dashboard**
```bash
python app.py
```
Open `http://localhost:5000`

**6. Run the conversational agent**
```bash
python agent.py
```

**7. Run a standalone daily report**
```bash
python daily_report.py
```

---

## Honest limitations

This is a learning project and proof of concept. A production-grade model would use 2-3 years of historical data, model zonal pricing differences, incorporate transaction costs, account for battery replacement cycles, and integrate professional price forecasts from Aurora Energy Research or Wood Mackenzie. The architecture is designed to scale — adding new data sources or refining assumptions requires minimal changes.

---

Built by Padraic Finan — economics student at CU Boulder, incoming MSc Accounting and Financial Management at Bocconi University (2026-2028). Interested in renewable energy finance, infrastructure investment, and applied AI.