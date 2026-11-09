from src.agent import process_order
import json

result = process_order(
    topic="Current adoption of NEAR Intents",
    payment_amount_usd=8.0
)

print(json.dumps(result, indent=2))
