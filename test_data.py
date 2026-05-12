from tools.gas_prices import get_gas_prices

result = get_gas_prices()

print("TTF Gas Price Analysis")
print("=" * 50)
print(f"Current price:     €{result['current_price']}/MWh")
print(f"Price 30 days ago: €{result['price_30d_ago']}/MWh")
print(f"Change:            {result['change_pct']:+.1f}%")
print(f"7-day average:     €{result['avg_7d']}/MWh")
print(f"30-day average:    €{result['avg_30d']}/MWh")
print(f"Trend:             {result['trend'].upper()}")
print(f"\nSignal:\n{result['signal']}")