import re
import requests
from bs4 import BeautifulSoup
from dateutil import parser as dp
from urllib.parse import urljoin, urlparse

SOURCE_SLUG = "multi_source"

# 1) Put all your listing pages here (server-rendered pages are best)
START_URLS = [
    # "https://example.gov/grants",
    # "https://another.gov/programs/funding",
]

# 2) Relevance filter — tweak to your needs
KEYWORDS = [
    "grant","funding","first responder","wellness","mental health","behavioral health",
    "psychological","fitness for duty","critical incident","stress","peer support","cisd"
]

# 3) Global default selectors (work for many list pages)
DEFAULT_SELECTORS = {
    "card": "article, .result, .card, .views-row, li.search-result",
    "title": "h1, h2, h3, .title, .card-title, a",
    "link": "a[href]",
    "desc": "p, .summary, .teaser, .card-text",
    "date": "time[datetime], .date, .published, .pubdate"
}

# 4) Optional PER-SITE overrides (match by netloc OR full URL)
#    Add entries like:
#    "example.gov": {"card":"div.card", "title":".title", "link":"a", "desc":".summary", "date":"time"}
PER_SITE_SELECTORS = {
    # "example.com": {"card":".news-card", "title":"h3", "link":"a", "desc":".excerpt", "date":"time"},
    # "https://example.com/grants": {"card":"li.result", "title":"a", "link":"a", "desc":"p", "date":".date"},
}

HEADERS = {"User-Agent": "grant-finder/1.0 (+https://github.com/your/repo)"}


def _clean(s):
    return re.sub(r"\s+", " ", (s or "").strip())


def _relevant(text):
    t = (text or "").lower()
    return all(tok in t for tok in []) or any(k in t for k in KEYWORDS)


def _selectors_for(url):
    netloc = urlparse(url).netloc.lower()
    # full URL match first, then domain, else default
    if url in PER_SITE_SELECTORS:
        base = dict(DEFAULT_SELECTORS); base.update(PER_SITE_SELECTORS[url]); return base
    if netloc in PER_SITE_SELECTORS:
        base = dict(DEFAULT_SELECTORS); base.update(PER_SITE_SELECTORS[netloc]); return base
    return DEFAULT_SELECTORS


def _parse_date(root, selectors):
    # Try structured date first
    node = root.select_one(selectors.get("date", "")) if selectors.get("date") else None
    if node:
        # time[datetime] → attribute; others → text
        dt = node.get("datetime") if node.has_attr("datetime") else node.get_text(" ")
        try:
            return dp.parse(str(dt), fuzzy=True).date().isoformat()
        except Exception:
            pass
    # Fallback: any string looking like a date
    txt = root.get_text(" ")
    m = re.search(r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec|\d{1,2}/\d{1,2}/\d{2,4}|\d{4})", txt, re.I)
    if m:
        try:
            return dp.parse(m.group(0), fuzzy=True).date().isoformat()
        except Exception:
            return None
    return None


def _extract_items_from_listing(list_url):
    sel = _selectors_for(list_url)
    items = []

    try:
        r = requests.get(list_url, timeout=20, headers=HEADERS)
        r.raise_for_status()
    except Exception:
        return items

    soup = BeautifulSoup(r.text, "html.parser")
    for card in soup.select(sel["card"]):
        title_el = card.select_one(sel["title"])
        link_el  = card.select_one(sel["link"])
        desc_el  = card.select_one(sel["desc"])

        if not link_el or not title_el:
            continue

        # Build absolute URL
        href = link_el.get("href")
        if not href:
            continue
        url = urljoin(list_url, href)

        title = _clean(title_el.get_text())
        desc  = _clean(desc_el.get_text()) if desc_el else ""

        # Filter
        if not _relevant(title + " " + desc):
            continue

        posted = _parse_date(card, sel)

        items.append({
            "title": title,
            "url": url,
            "source": SOURCE_SLUG,
            "description": desc[:500],
            "posted_date": posted,
            "deadline_date": None,
            "tags": ["first-responders","wellness"]
        })
    return items


def fetch():
    all_items, seen = [], set()
    for url in START_URLS:
        for item in _extract_items_from_listing(url):
            if item["url"] in seen:
                continue
            seen.add(item["url"])
            all_items.append(item)
    return all_items
