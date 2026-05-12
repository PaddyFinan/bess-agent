# BESS Project Finance Agent

An autonomous AI agent that monitors Italian battery storage project finance in real time. Pulls live market data, models revenue across a 15-year degradation curve, stress tests debt coverage, monitors policy news, and generates daily reports — without any manual input.

Built in Python using the Anthropic Claude API with autonomous tool use and GitHub Actions scheduling.

---

## What this is

I'm a 22 year old economics student heading to Bocconi to study Accounting and Financial Management, with a focus on breaking into renewable energy finance. I built this project to teach myself AI agent development while actually learning the domain I want to work in.

The idea came from a simple question: what does a junior analyst actually do when they're stress testing a battery storage deal? They pull market data, model revenue, calculate DSCRs across the project life, and flag risks. So I built an agent that does exactly that — autonomously, from a plain English question.

---

## What it does

There are two ways to use it:

**Conversational mode** — run `agent.py` and ask questions in plain English:

- *"Analyse our Italian BESS project including the degradation curve"*
- *"What happens if we increase the loan to €22 million?"*
- *"Stress test a 100 MWh project with a 65% capture rate"*
- *"What does the bank say about our debt sizing?"*
- *"What's the latest policy news affecting the project?"*

Claude decides which tools to call, chains them together, and produces written analysis. Every assumption is adjustable on the fly.

**Autonomous mode** — GitHub Actions runs `daily_report.py` every morning at 7am Italian time. It fetches fresh market data, runs the full analysis, compares results to the previous day, flags any meaningful changes, and commits the report directly to the repository. No laptop required.

---

## The finance logic

A battery storage project earns money by charging when electricity is cheap and discharging when it's expensive. The spread between those two prices is the arbitrage revenue. In Italy, solar panels flood the grid at midday pushing prices toward zero, then gas plants drive prices back up in the evening peak. That intraday spread is what the battery captures.

The project also earns ancillary services revenue — Terna (Italy's grid operator) pays batteries just to be available for frequency regulation, regardless of whether they actually discharge.

**Battery degradation** is a critical factor in project finance. Lithium-ion batteries lose roughly 2% of their capacity each year. A battery that starts at 50 MWh in year 1 will only deliver 37.7 MWh by year 15. This means revenue declines each year while the debt service payment stays fixed — so the DSCR deteriorates over time. Lenders underwrite against the **minimum DSCR year** (usually year 14 or 15), not just year 1.

Combined revenue streams are stress tested against the project's debt service obligations. The key metric is the **Debt Service Coverage Ratio (DSCR)** — how many euros of revenue the project generates for every euro of debt it needs to repay. Banks require a minimum of 1.20-1.30x. Below that is a covenant breach.

---

## Architecture

agent.py                  ← Conversational interface with Claude
daily_report.py           ← Autonomous scheduled run
memory.py                 ← Snapshot system for trend comparison
tools/
price_data.py         ← Tool 1: Live ENTSO-E power prices
revenue_model.py      ← Tool 2: Stacked revenue with degradation curve
dscr.py               ← Tool 3: 15-year DSCR schedule and debt sizing
gas_prices.py         ← Tool 4: TTF gas prices as leading indicator
news_monitor.py       ← Tool 5: Policy news via Claude web search
reports/                  ← Auto-generated daily reports
.github/workflows/
daily_report.yml      ← GitHub Actions scheduler

Claude receives tool definitions, autonomously decides which tools to call based on your question, chains them in sequence, and produces written analysis. The tools are all parameterised — Claude can adjust any assumption on the fly from a plain English request.

---

## The five tools

**Tool 1 — Italian power prices**
Fetches live day-ahead electricity prices for the IT-NORTH bidding zone from the ENTSO-E Transparency Platform. Calculates daily arbitrage spread statistics across a rolling 30-day window — average, minimum, maximum, standard deviation, and coefficient of variation. Automatically excludes partial days and tomorrow's forecast data.

**Tool 2 — Revenue model with degradation**
Models annual BESS revenue by stacking two sources: energy arbitrage and ancillary services. Returns both year 1 revenue and a full 15-year degradation schedule — showing how revenue declines as battery capacity erodes at 2% per year. The degradation schedule feeds directly into the DSCR calculator.

**Tool 3 — DSCR calculator with 15-year schedule**
Calculates Debt Service Coverage Ratio for every year of the project life using the degradation schedule from Tool 2. Identifies the minimum DSCR year — the number lenders actually underwrite against. Flags each scenario GREEN (≥1.30x), AMBER (1.20-1.29x), or RED (<1.20x). Sizes the maximum supportable loan against the worst revenue year, not year 1.

**Tool 4 — TTF gas prices**
Fetches TTF natural gas futures prices via Yahoo Finance. TTF is the European gas benchmark and the primary driver of Italian evening peak power prices — a falling TTF is a leading indicator of spread compression before it shows up in the power price data. Returns current price, 30-day trend, and a plain English signal on what the movement means for BESS spread economics.

**Tool 5 — Policy news monitor**
Uses Claude's built-in web search to find recent news relevant to Italian BESS project finance — MACSE auction results, Terna announcements, EU energy storage policy, and market developments. Returns a structured analysis of what each development means for project economics, flagging whether each item is bullish, bearish, or neutral for the project.

---

## Memory and monitoring

Every time a full analysis runs, the agent saves a snapshot of key metrics to `memory.json`. The next run loads that snapshot and compares current numbers to previous numbers. Claude flags any meaningful changes — DSCR deterioration, spread compression, gas price movements that signal risk ahead.

---

## Autonomous scheduling

GitHub Actions runs the full analysis every morning at 7am Italian time on GitHub's servers. The workflow fetches live data across all five tools, generates a daily monitoring report, and commits it to the `reports/` folder automatically.

---

## Financial assumptions

| Assumption | Value | Source |
|---|---|---|
| Battery capacity | 50 MWh / 25 MW | Standard utility scale, 2-hour duration |
| Round-trip efficiency | 85% | Industry standard LFP chemistry |
| Capture rate | 75% | Conservative merchant estimate |
| Cycles per day | 1.0 | Standard arbitrage operation |
| Degradation rate | 2% per year | Standard LFP degradation assumption |
| Project life | 15 years | Matched to loan tenor |
| Year 1 capacity | 50 MWh | — |
| Year 15 capacity | 37.7 MWh | After 14 years of 2% degradation |
| Ancillary services rate | €60,000/MW/year | 2024-2025 Italian capacity market auctions |
| Total project cost | €25 million | Current 2026 installed cost benchmarks |
| Loan amount | €17.5 million | 70% gearing on €25m project |
| Interest rate | 6.0% | Conservative — current EURIBOR ~2.88% + ~2.5-3% margin |
| Loan tenor | 15 years | Standard infrastructure project finance |
| DSCR minimum | 1.30x | Standard project finance threshold |
| DSCR floor | 1.20x | Absolute covenant breach level |

---

## Data sources

- **Power prices**: ENTSO-E Transparency Platform — IT-NORTH bidding zone, rolling 30-day window
- **Gas prices**: TTF futures via Yahoo Finance
- **Policy news**: Claude web search — real-time monitoring of Italian and EU energy policy
- **Ancillary service rates**: Validated against 2024-2025 Italian capacity market auction results
- **Capital costs**: Current 2026 BESS installed cost benchmarks
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

**4. Set up your API keys**

Create a `.env` file in the root folder:

ENTSO_E_API_KEY=your_entsoe_token
ANTHROPIC_API_KEY=your_anthropic_key

Get your ENTSO-E token by registering at transparency.entsoe.eu and emailing transparency@entsoe.eu to request API access.

**5. Run the conversational agent**
```bash
python agent.py
```

**6. Run a standalone daily report**
```bash
python daily_report.py
```

---

## Sample output

Ask the agent *"Analyse the project including the degradation curve and tell me what a bank would say about the debt sizing"* and it will:

1. Fetch live Italian power prices and calculate 30-day spread statistics
2. Pull TTF gas futures and assess compression risk
3. Model revenue with a full 15-year degradation schedule
4. Calculate DSCR for every year and identify the minimum DSCR year
5. Search for recent policy news and assess its impact
6. Produce a structured analysis recommending debt sizing, covenant terms, and conditions precedent — in the style of a project finance term sheet

---

## Honest limitations

This is a learning project and proof of concept. A production-grade model would use 2-3 years of historical data, model seasonal variation, incorporate transaction costs, and integrate professional price forecasts. The architecture is designed to scale — the tool structure means adding new data sources requires minimal changes.

---

## What's next

- Seasonality analysis — comparing current spreads to the same period in prior years
- Multi-year scenario comparison — modelling spread compression over the project life
- Web dashboard — a visual interface showing live DSCR, spread charts, and daily reports

---

Built by Padraic Finan — economics student at CU Boulder, incoming MSc Accounting and Financial Management at Bocconi University (2026-2028). Interested in renewable energy finance, infrastructure investment, and applied AI.