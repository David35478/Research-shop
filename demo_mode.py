"""Demo mode CLI: simulates a full cycle without real transactions."""
import json
import sys

from src.demo_mode import run_demo_order


def main():
    topic = sys.argv[1] if len(sys.argv) > 1 else "Current adoption of NEAR Intents"
    amount = float(sys.argv[2]) if len(sys.argv) > 2 else 8.0
    print(json.dumps(run_demo_order(topic, amount), indent=2))


if __name__ == "__main__":
    main()
