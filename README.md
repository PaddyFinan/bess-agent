# BESS Project Finance Agent

An AI agent that stress-tests battery storage project finance deals using live Italian power market data. Built in Python with Claude as the reasoning brain.

---

## What this is

## What this is

I'm a 22 year old economics student heading to Bocconi to study Accounting and Financial Management, with a focus on breaking into renewable energy finance. I built this project to teach myself AI agent development while actually learning the domain I want to work in.

The idea came from a simple question: what does a junior analyst actually do when they're stress testing a battery storage deal? They pull market data, model revenue, calculate DSCRs, and flag risks. So I built an agent that does exactly that — autonomously, from a plain English question.

---

## What it does

You ask it something like *"analyse our Italian BESS project"* or *"what happens if we increase the loan to €22 million?"* and it:

1. Fetches live day-ahead electricity prices for Northern Italy from the ENTSO-E Transparency Platform
2. Calculates daily arbitrage spread statistics across a rolling 30-day window
3. Models stacked annual revenue — energy arbitrage plus ancillary services from Terna's MSD market
4. Runs a full DSCR stress test across base case, downside, and severe downside scenarios
5. Flags bankability against standard project finance thresholds
6. Sizes the maximum supportable debt at a 1.30x DSCR minimum
7. Writes up the analysis in plain English like a junior analyst would

The whole thing runs autonomously. Claude decides which tools to call, chains them together, and interprets the results. You just ask questions.

---

## Why Italy and why BESS

Italy is one of the most interesting battery storage markets in Europe right now. It has extreme midday solar price crashes — sometimes hitting zero — followed by sharp evening peaks when gas plants take over. That spread between cheap midday power and expensive evening power is what a battery exploits to make money.

The problem is that spread is volatile, it varies day to day, and as more batteries get built the spread compresses over time. That's the central risk in any BESS project finance deal and it's exactly what this agent monitors.

The Italian market also has the MACSE scheme — 15-year government contracts for battery storage — plus ancillary service markets run by Terna. Stack those revenue streams together and you have a financeable project. Remove them and you don't. The agent models all of this.

---

## The finance concepts behind it

A battery storage project gets financed like any infrastructure project — a bank lends money against projected future revenue. The key metric is the **Debt Service Coverage Ratio (DSCR)**: how many euros of revenue does the project generate for every euro of debt it needs to repay.

Banks want to see:
- **1.30x minimum** in the base case
- **1.20x absolute floor** — below this is a technical breach

The agent calculates DSCR across three scenarios:
- **Base case** — average market spreads
- **Downside** — one standard deviation below average
- **Severe downside** — two standard deviations below average

It also works backwards from revenue to tell you the maximum loan the project can support at a 1.30x threshold — which is what a bank actually does when sizing a deal.

---

## Technical architecture