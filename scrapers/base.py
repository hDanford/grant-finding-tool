# scrapers/base.py
import re

# Shared keyword set; add more as needed
KEYWORDS = [
    "grant","funding","first responder","wellness","mental health","behavioral health",
    "psychological","fitness for duty","critical incident","stress","peer support","cisd"
]

def clean(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())

def relevant(text: str) -> bool:
    t = (text or "").lower()
    return any(k in t for k in KEYWORDS)

def make_item(
    *,
    title: str,
    url: str,
    source: str,
    description: str = "",
    posted_date: str | None = None,
    deadline_date: str | None = None,
    tags: list[str] | None = None
) -> dict:
    return {
        "title": title,
        "url": url,
        "source": source,
        "description": description[:500] if description else "",
        "posted_date": posted_date,
        "deadline_date": deadline_date,
        "tags": tags or ["first-responders","wellness"],
    }
