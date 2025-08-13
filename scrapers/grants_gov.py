# scrapers/grants_gov.py
# Official Grants.gov REST APIs (no auth required):
# - search2  → find opportunities
# - fetchOpportunity → get detailed description
# Docs: https://www.grants.gov/api (see "Applicant API" → search2/fetchOpportunity)
# Auth: not required for search2/fetchOpportunity.

import re
import time
import requests
from dateutil import parser as dp
from .base import clean, make_item  # note: we skip base.relevant to avoid over-filtering

SOURCE_SLUG = "grants.gov"
SEARCH_URL = "https://api.grants.gov/v1/api/search2"
FETCH_URL  = "https://api.grants.gov/v1/api/fetchOpportunity"
HEADERS = {
    "User-Agent": "first-responder-grant-finder/1.0 (+github)",
    "Content-Type": "application/json",
}

# Query terms tuned to your use case
KEYWORDS = [
    "first responder",
    "first responders",
    "wellness",
    "mental health",
    "behavioral health",
    "psychological evaluation",
    "pre-employment",
    "critical incident",
    "stress debriefing",
    "fitness for duty",
    "peer support",
    "cisd"
]

def _post_json(url, body):
    r = requests.post(url, json=body, headers=HEADERS, timeout=45)
    r.raise_for_status()
    return r.json()

def _search_keyword(word: str, max_rows: int = 300):
    """Page through search2 for a single keyword."""
    start, rows = 0, 100
    hits = []
    while start < max_rows:
        body = {
            "keyword": word,
            "oppStatuses": "forecasted|posted",
            "startRecordNum": start,
            "rows": rows,
            # You can add more filters here (agencies, categories, eligibilities) if desired.
        }
        payload = _post_json(SEARCH_URL, body).get("data") or {}
        page = payload.get("oppHits") or []
        if not page:
            break
        hits.extend(page)
        start += rows
        if start >= int(payload.get("hitCount") or 0):
            break
        time.sleep(0.2)  # be polite
    return hits

def _detail_desc(opp_id: int) -> str:
    """Fetch detailed description text from fetchOpportunity."""
    try:
        data = _post_json(FETCH_URL, {"opportunityId": int(opp_id)}).get("data") or {}
    except Exception:
        return ""

    syn = data.get("synopsis") or {}
    forecast = data.get("forecast") or {}
    desc = (
        syn.get("synopsisDesc")
        or syn.get("opportunityDescription")
        or forecast.get("forecastDescription")
        or ""
    )
    # strip HTML tags
    desc = re.sub(r"<[^>]+>", " ", str(desc))
    return clean(desc)

def fetch():
    out, seen = [], set()

    for kw in KEYWORDS:
        for h in _search_keyword(kw):
            opp_id = h.get("id")
            if not opp_id or opp_id in seen:
                continue
            seen.add(opp_id)

            title = clean(h.get("title") or h.get("opportunityTitle") or "")
            url = f"https://www.grants.gov/search-results-detail/{opp_id}"

            # Dates
            open_date = h.get("openDate") or h.get("postedDate") or ""
            close_date = h.get("closeDate") or ""
            try:
                posted = dp.parse(open_date).date().isoformat() if open_date else None
            except Exception:
                posted = None
            try:
                deadline = dp.parse(close_date).date().isoformat() if close_date else None
            except Exception:
                deadline = None

            desc = _detail_desc(opp_id)

            # Basic tags
            tags = ["federal", "grants.gov"]
            blob = f"{title} {desc}".lower()
            if "first responder" in blob:
                tags.append("first-responders")
            if "wellness" in blob:
                tags.append("wellness")

            out.append(
                make_item(
                    title=title or f"Grants.gov Opportunity {opp_id}",
                    url=url,
                    source=SOURCE_SLUG,
                    description=desc,
                    posted_date=posted,
                    deadline_date=deadline,
                    tags=tags,
                )
            )
    return out
