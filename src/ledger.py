import json
from pathlib import Path
from datetime import datetime, timezone

LEDGER_FILE = Path("public_ledger.json")
_TMP_LEDGER_FILE = Path("/tmp/public_ledger.json")


def log_sale(entry: dict):
    entry["timestamp"] = datetime.now(timezone.utc).isoformat()

    for target in (LEDGER_FILE, _TMP_LEDGER_FILE):
        try:
            if target.exists():
                data = json.loads(target.read_text())
            else:
                data = []
            data.append(entry)
            target.write_text(json.dumps(data, indent=2))
            return
        except (OSError, json.JSONDecodeError):
            continue  # unwritable or corrupt: try the next location
    # Ledger is best-effort: an order must never fail on a logging write


def get_ledger():
    if LEDGER_FILE.exists():
        return json.loads(LEDGER_FILE.read_text())
    if _TMP_LEDGER_FILE.exists():
        return json.loads(_TMP_LEDGER_FILE.read_text())
    return []
