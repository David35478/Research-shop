import json
from pathlib import Path
from datetime import datetime, timezone

LEDGER_FILE = Path("public_ledger.json")


def log_sale(entry: dict):
    entry["timestamp"] = datetime.now(timezone.utc).isoformat()

        if LEDGER_FILE.exists():
                data = json.loads(LEDGER_FILE.read_text())
                    else:
                            data = []

                                data.append(entry)
                                    LEDGER_FILE.write_text(json.dumps(data, indent=2))


                                    def get_ledger():
                                        if not LEDGER_FILE.exists():
                                                return []
                                                    return json.loads(LEDGER_FILE.read_text())