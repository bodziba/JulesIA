import json
import os
import uuid
from datetime import datetime
from typing import List, Dict, Any
from config import TICKETS_FILE

def _load_tickets() -> List[Dict[str, Any]]:
    if not os.path.exists(TICKETS_FILE):
        return []
    try:
        with open(TICKETS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError:
        return []
    except Exception as e:
        print(f"Error loading tickets: {e}")
        return []

def _save_tickets(tickets: List[Dict[str, Any]]) -> None:
    try:
        with open(TICKETS_FILE, 'w', encoding='utf-8') as f:
            json.dump(tickets, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving tickets: {e}")

def add_ticket(system: str, client: str, type_str: str, description: str, analysis: str, criticality: str) -> Dict[str, Any]:
    tickets = _load_tickets()
    ticket = {
        "id": str(uuid.uuid4()),
        "system": system,
        "client": client,
        "type": type_str,
        "description": description,
        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "analysis": analysis,
        "criticality": criticality
    }
    tickets.insert(0, ticket)
    _save_tickets(tickets)
    return ticket

def get_all_tickets() -> List[Dict[str, Any]]:
    return _load_tickets()

def delete_ticket(ticket_id: str) -> bool:
    tickets = _load_tickets()
    initial_length = len(tickets)
    tickets = [t for t in tickets if t.get("id") != ticket_id]
    if len(tickets) < initial_length:
        _save_tickets(tickets)
        return True
    return False

def clear_all_tickets() -> None:
    _save_tickets([])
