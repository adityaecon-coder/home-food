"""
Sensitive words. If a customer's message contains one of these, the chat skips the AI and
hands the customer straight to a human support executive (a ticket is raised by the code).

Normal questions such as "How long do refunds take?" are NOT in this list: Tanny answers
those from the help docs.
"""

import re

# Health or safety problems: raised as HIGH priority.
HEALTH_WORDS = ["food poisoning", "hospital", "ambulance", "vomit", "allergic reaction"]

# Legal, money or "I want a person" topics: raised as normal priority.
OTHER_WORDS = ["lawyer", "legal action", "consumer court", "police", "fraud", "scam",
               "chargeback", "compensation", "manager", "executive"]

PATTERN = re.compile(r"\b(" + "|".join(HEALTH_WORDS + OTHER_WORDS) + r")", re.IGNORECASE)


def find_sensitive_word(message: str):
    """Return (word, priority) for the first sensitive word found, or None."""
    m = PATTERN.search(message)
    if not m:
        return None
    word = m.group(1).lower()
    return word, ("high" if word in HEALTH_WORDS else "normal")
