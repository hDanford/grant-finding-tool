# fetch.py
import json, os, time, importlib, pkgutil, hashlib

OUT = os.path.join("data", "grants.json")
SCRAPER_PACKAGE = "scrapers"

os.makedirs("data", exist_ok=True)

def canonical(item):
    h = hashlib.sha256((item.get("title","") + item.get("url","")).encode("utf-8")).hexdigest()[:16]
    item["id"] = h
    return item

def iter_scraper_modules():
    pkg = importlib.import_module(SCRAPER_PACKAGE)
    for m in pkgutil.iter_modules(pkg.__path__, prefix=pkg.__name__ + "."):
        name = m.name
        # skip private/dunder modules
        if name.rsplit(".", 1)[-1].startswith("_"):
            continue
        # base and __init__ are helpers, not scrapers
        if name.endswith(".base") or name.endswith(".__init__"):
            continue
        yield importlib.import_module(name)

def run_all_scrapers():
    all_items = []
    for mod in iter_scraper_modules():
        fetcher = getattr(mod, "fetch", None)
        if not callable(fetcher):
            continue
        try:
            items = fetcher() or []
            all_items.extend(items)
        except Exception:
            # keep going even if one scraper fails
            continue
    return all_items

def main():
    items = run_all_scrapers()

    # Dedupe by URL
    seen, unique = set(), []
    for it in items:
        url = it.get("url")
        if not url or url in seen:
            continue
        seen.add(url)
        unique.append(canonical(it))

    # Sort newest first by posted_date then title
    def key(x):
        d = x.get("posted_date") or "0000-00-00"
        return (d, (x.get("title") or "").lower())
    unique.sort(key=key, reverse=True)

    out = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "count": len(unique),
        "items": unique,
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"Wrote {OUT} with {len(unique)} items")

if __name__ == "__main__":
    main()
