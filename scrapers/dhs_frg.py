import requests, re
from bs4 import BeautifulSoup
from dateutil import parser as dp

BASE = "https://www.dhs.gov"
LIST_URL = "https://www.dhs.gov/science-and-technology/frg-grants"

KEYWORDS = [
    "first responder","wellness","mental health","behavioral health",
    "psychological","fitness for duty","critical incident","stress","peer"
]

def _clean(s): 
    return re.sub(r"\s+", " ", (s or "").strip())

def _match(text):
    t = (text or "").lower()
    return any(k in t for k in KEYWORDS)

def fetch():
    out = []
    r = requests.get(LIST_URL, timeout=20)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    for a in soup.select("main a[href]"):
        href = a.get("href")
        if not href: 
            continue
        if href.startswith("/"):
            href = BASE + href
        if not href.startswith(BASE):
            continue

        try:
            ar = requests.get(href, timeout=20)
            if ar.status_code != 200:
                continue
            asoup = BeautifulSoup(ar.text, "html.parser")
            h = asoup.select_one("h1, .node__title, .page-title")
            title = _clean(h.get_text() if h else a.get_text())
            body = _clean(" ".join(x.get_text(' ') for x in asoup.select("main p, article p")[:6]))
            if not _match(title + " " + body):
                continue
            posted = None
            t = asoup.select_one("time[datetime], .submitted time")
            if t and t.has_attr("datetime"):
                try:
                    posted = dp.parse(t["datetime"]).date().isoformat()
                except Exception:
                    posted = None
            out.append({
                "title": title,
                "url": href,
                "source": "dhs_frg",
                "description": body[:500],
                "posted_date": posted,
                "deadline_date": None,
                "tags": ["first-responders","federal","dhs"]
            })
        except Exception:
            continue
    return out
