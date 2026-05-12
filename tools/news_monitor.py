import os
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

def get_policy_news() -> dict:
    """
    Uses Claude's built-in web search to find recent news relevant to
    Italian BESS project finance — policy changes, MACSE auctions,
    Terna announcements, EU energy storage regulation.

    This tool gives the agent forward-looking context that doesn't
    show up in price data — regulatory changes, auction results,
    and market structure shifts that affect project assumptions.

    Returns:
        Dictionary containing:
        - raw_analysis: full text response from Claude
        - overall_sentiment: bullish/bearish/neutral for BESS economics
        - policy_signals_detected: list of policy keywords found
        - market_signals_detected: list of market keywords found
        - summary: plain English summary of what matters for the project
        - search_completed: confirmation the search ran
    """

    client = Anthropic()

    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=2048,
        tools=[{
            "type": "web_search_20250305",
            "name": "web_search",
            "max_uses": 5
        }],
        messages=[{
            "role": "user",
            "content": """Search for recent news (last 2-4 weeks) relevant to Italian battery 
storage project finance. Focus on:

1. MACSE auction results or announcements (Italy's 15-year storage contracts)
2. Terna grid announcements affecting battery storage or ancillary services
3. EU energy storage policy — Green Deal, REPowerEU, storage mandates
4. Italian electricity market regulation changes
5. TTF gas price outlook or European energy market developments
6. New large BESS projects announced or commissioned in Italy
7. Any news affecting Italian power price spreads

For each relevant item found, provide:
- Headline and source
- Date
- Why it matters for a merchant BESS project in Northern Italy
- Whether it is BULLISH (improves project economics), BEARISH (worsens them), or NEUTRAL

End with an overall sentiment assessment for Italian BESS project finance 
and a one paragraph summary of the most important findings."""
        }]
    )

    # Extract the text response
    full_text = ""
    for block in response.content:
        if hasattr(block, "text"):
            full_text += block.text

    # Determine overall sentiment from the text
    text_lower = full_text.lower()
    bullish_count = text_lower.count("bullish")
    bearish_count = text_lower.count("bearish")

    if bullish_count > bearish_count:
        overall_sentiment = "bullish"
    elif bearish_count > bullish_count:
        overall_sentiment = "bearish"
    else:
        overall_sentiment = "neutral"

    # Extract summary — last paragraph of the response
    paragraphs = [p.strip() for p in full_text.split('\n\n') if p.strip()]
    if paragraphs:
        summary = paragraphs[-1]
    else:
        summary = full_text

    # Flag items that mention key policy terms
    policy_keywords = ["macse", "terna", "eu", "regulation", "policy", "auction", "cfd", "contract"]
    market_keywords = ["ttf", "spread", "price", "solar", "arbitrage", "revenue", "capacity"]

    policy_signals = []
    market_signals = []

    for keyword in policy_keywords:
        if keyword in text_lower:
            policy_signals.append(keyword.upper())

    for keyword in market_keywords:
        if keyword in text_lower:
            market_signals.append(keyword.upper())

    return {
        "raw_analysis": full_text,
        "overall_sentiment": overall_sentiment,
        "policy_signals_detected": list(set(policy_signals)),
        "market_signals_detected": list(set(market_signals)),
        "summary": summary,
        "search_completed": True
    }