"""
The three tools Tiffy can use. Each is a plain Python function.
The agent reads the function name, the docstring and the arguments to decide when to call it.
"""

import csv
import os
import tempfile
from datetime import datetime
from pathlib import Path

from support_agent import rag

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

# Tickets are saved in a CSV file. On Vercel the project folder is read-only,
# so we use the temp folder there (it resets when the server restarts; fine for a demo).
if os.environ.get("VERCEL"):
    TICKETS_FILE = Path(tempfile.gettempdir()) / "tickets.csv"
else:
    TICKETS_FILE = Path(__file__).resolve().parent.parent / "tickets.csv"

TICKET_FIELDS = ["ticket_id", "time", "customer_message", "reason", "priority", "status"]


def search_help_docs(question: str) -> dict:
    """Search TiffinGo's help docs and return the 3 best matching sections.

    Use this for any question about delivery, orders, payments, refunds, tiffin plans or food.

    Args:
        question: The customer's question, in plain words.

    Returns:
        A dict with 'results': a list of {source, text}.
    """
    return {"results": rag.search(question, top_k=3)}


def create_ticket(message: str, reason: str, priority: str) -> dict:
    """Save a support ticket so a person can follow up. Returns the ticket ID.

    Args:
        message: What the customer said, in their own words (short).
        reason: Why a person is needed, e.g. 'felt unwell after meal', 'refund above 1000',
            'rider complaint', 'angry customer', 'not in help docs', 'asked for a person'.
        priority: 'high' if someone feels unwell after a meal, otherwise 'normal'.

    Returns:
        A dict with the ticket_id.
    """
    priority = "high" if str(priority).lower() == "high" else "normal"
    rows = []
    if TICKETS_FILE.exists():
        with open(TICKETS_FILE, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
    # The ID is made by the code (never by the model) and always goes up, so it never repeats.
    last = max((int(r["ticket_id"].split("-")[1]) for r in rows), default=1000)
    ticket_id = f"TKT-{last + 1}"
    new_file = not TICKETS_FILE.exists()
    with open(TICKETS_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=TICKET_FIELDS)
        if new_file:
            writer.writeheader()
        writer.writerow({
            "ticket_id": ticket_id,
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "customer_message": message,
            "reason": reason,
            "priority": priority,
            "status": "open",
        })
    return {"ticket_id": ticket_id, "status": "open"}


def get_order_status(order_id: str, phone_last4: str) -> dict:
    """Look up one order. Needs BOTH the order ID and the last 4 digits of the phone number.

    Args:
        order_id: The order ID, like TG1001.
        phone_last4: The last 4 digits of the phone number on the order.

    Returns:
        The order details if both match the same order, otherwise {'found': False}.
    """
    with open(DATA_DIR / "orders.csv", newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if (row["order_id"].upper() == str(order_id).strip().upper()
                    and row["phone_last4"] == str(phone_last4).strip()):
                # Only share order details. Never the name or phone digits.
                return {
                    "found": True,
                    "order_id": row["order_id"],
                    "items": row["items"],
                    "status": row["status"],
                    "order_time": row["order_time"],
                    "amount_inr": row["amount_inr"],
                }
    return {"found": False}
