# scrapers/grants_gov.py
# Grants.gov public REST APIs (no auth for search2/fetchOpportunity).
# Docs:
# - search2: https://api.grants.gov/v1/api/search2
# - fetchOpportunity: https://api.grants.gov/v1/api/fetchOpportunity

import re
import time
import requests
from dateutil import parser as dp
from .base import clean, make_item  # we'll extend item with extra fields

SOURCE_SLUG = "grants.gov"
SEARCH_URL = "https://api.grants.gov/v1/api/search2"
FETCH_URL  = "https://api.grants.gov/v1/api/fetchOpportunity"
HEADERS = {
    "User-Agent": "first-responder-grant-finder/1.0 (+github)",
    "Content-Type": "application/json",
}

# Default keywords used by the scraper (shown in UI as starting keywords)
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
    "cisd",
]

def _post_json(url, body):
    r = requests.post(url, json=body, headers=HEADERS, timeout=45)
    r.raise_for_status()
    return r.json()

def _search_keyword(word: str, max_rows: int = 400):
    """Page through search2 for one keyword."""
    start, rows = 0, 100
    hits = []
    while start < max_rows:
        body = {
            "keyword": word,
            "oppStatuses": "forecasted|posted",  # looking forward + open
            "startRecordNum": start,
            "rows": rows,
        }
        payload = _post_json(SEARCH_URL, body).get("data") or {}
        page = payload.get("oppHits") or []
        if not page:
            break
        hits.extend(page)
        start += rows
        if start >= int(payload.get("hitCount") or 0):
            break
        time.sleep(0.15)
    return hits

def _detail_desc_and_meta(opp_id: int):
    """Fetch description + detail facets from fetchOpportunity."""
    try:
        data = _post_json(FETCH_URL, {"opportunityId": int(opp_id)}).get("data") or {}
    except Exception:
        return "", {}, {}, {}, [], []

    syn = data.get("synopsis") or {}
    forecast = data.get("forecast") or {}

    # Description
    desc = (
        syn.get("synopsisDesc")
        or syn.get("opportunityDescription")
        or forecast.get("forecastDescription")
        or ""
    )
    desc = re.sub(r"<[^>]+>", " ", str(desc))
    desc = clean(desc)

    # Facets
    agency_name = syn.get("agencyName") or (data.get("agencyDetails") or {}).get("agencyName")
    opp_status = (syn.get("docType") or data.get("docType") or "").lower()  # synopsis/forecast
    funding_instr = [fi.get("description") for fi in (syn.get("fundingInstruments") or []) if fi.get("description")]
    funding_cats  = [fa.get("description") for fa in (syn.get("fundingActivityCategories") or []) if fa.get("description")]
    eligs         = [e.get("description") for e in (syn.get("applicantTypes") or []) if e.get("description")]
    alns          = [a.get("alnNumber") for a in (data.get("alns") or []) if a.get("alnNumber")]

    return desc, agency_name, opp_status, funding_instr, funding_cats, eligs, alns

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
            agency_code = h.get("agencyCode")
            agency_name_hit = h.get("agencyName")
            opp_status_hit = (h.get("oppStatus") or "").lower()
            doc_type = h.get("docType") or ""

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

            # Detail
            desc, agency_name, opp_status, finstr, fcat, eligs, alns = _detail_desc_and_meta(opp_id)

            item = make_item(
                title=title or f"Grants.gov Opportunity {opp_id}",
                url=url,
                source=SOURCE_SLUG,
                description=desc,
                posted_date=posted,
                deadline_date=deadline,
                tags=["federal", "grants.gov"],
            )

            # enrich with filterable fields
            item.update({
                "opportunity_number": h.get("number"),
                "agency_code": agency_code,
                "agency_name": agency_name or agency_name_hit,
                "opp_status": (opp_status or opp_status_hit),
                "doc_type": doc_type,
                "funding_instruments": finstr or [],
                "funding_categories": fcat or [],
                "eligibilities": eligs or [],
                "alns": alns or (h.get("alnist") or []),
            })

            out.append(item)
    return out
