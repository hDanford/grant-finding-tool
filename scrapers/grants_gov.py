# scrapers/grants_gov.py
# Uses the official Grants.gov REST APIs:
# - search2 (public, no auth) to find opportunities
# - fetchOpportunity (public, no auth) for detail/description
# Respect site ToS: lightweight requests, short pauses.

import re
import time
import requests
from dateutil import parser as dp
from .base import clean, relevant, make_item

SOURCE_SLUG = "grants.gov"
SEARCH_URL = "https://api.grants.gov/v1/api/search2"
FETCH_URL  = "https://api.grants.gov/v1/api/fetchOpportunity"
HEADERS = {
    "User-Agent": "first-responder-grant-finder/1.0 (+github)",
    "Content-Type": "application/json",
}

# Focused keywords for your use case
KEYWORDS = [
    "first responder", "first responders", "wellness", "mental health",
    "behavioral health", "psychological evaluation", "pre-employment",
    "critical incident", "stress debriefing", "fitness for duty",
    "peer support", "cisd"
]

def _post_json(url, body):
    r = requests.post(url, json=body, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.json()

def _search_keyword(word: str, max_rows: int = 400):
    """Page through search2 for a single keyword."""
    start, rows = 0, 100
    hits = []
    while start < max_rows:
        body = {
            "keyword": word,
            "oppStatuses": "forecasted|posted",
            "startRecordNum": start,
            "rows": rows,
        }
        payload = _post_json(SEARCH_URL, body).get("data") or {}
        page = payload.get("oppHits") or []
        if not page:
            break
        hits.extend(page)
        start += rows
        if s
