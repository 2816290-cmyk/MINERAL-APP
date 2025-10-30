import json
import os
from typing import Dict, Any

from config import USERS_FILE, LOGS_FILE

def ensure_data_files():
    """Create data directory + empty files if missing."""
    os.makedirs(os.path.dirname(USERS_FILE), exist_ok=True)
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, "w") as f:
            json.dump({"users": []}, f, indent=2)
    if not os.path.exists(LOGS_FILE):
        with open(LOGS_FILE, "w") as f:
            json.dump({"logs": []}, f, indent=2)

def load_users() -> Dict[str, Any]:
    ensure_data_files()
    with open(USERS_FILE, "r") as f:
        return json.load(f)

def save_users(data: Dict[str, Any]) -> None:
    with open(USERS_FILE, "w") as f:
        json.dump(data, f, indent=2)

def append_log(entry: Dict[str, Any]) -> None:
    """Append a log entry to logs.json"""
    ensure_data_files()
    with open(LOGS_FILE, "r") as f:
        logs = json.load(f)
    logs.setdefault("logs", []).append(entry)
    with open(LOGS_FILE, "w") as f:
        json.dump(logs, f, indent=2)
