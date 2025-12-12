from broker.paper_broker import PaperBroker

b = PaperBroker(starting_cash=5000)

# place order
order = b.place_order("TATASTEEL", 10, "buy", "market")
print(order)

# simulate tick
b.on_market_tick("TATASTEEL", 120.5)

print("Positions:", b.get_positions())
print("Cash:", b.get_cash())
print("Orders:", b.get_orders())
