# fetch.py
import json, os, time, importlib, pkgutil, hashlib, os as _os
from collections import Counter

OUT = os.path.join("data", "grants.json")
os.makedirs(os.path.dirname(OUT), exist_ok=True)

SCRAPER_PACKAGE = "scrapers"
# Pin scrapers via env, e.g. SCRAPERS="grants_gov" (recommended while testing)
PINNED = {s.strip() for s in (_os.getenv("SCRAPERS") or "grants_gov").split(",") if s.strip()}

def canonical(item):
    h = hashlib.sha256((item.get("title","") + item.get("url","")).encode("utf-8")).hexdigest()[:16]
    item["id"] = h
    return item

def iter_scraper_modules():
    pkg = importlib.import_module(SCRAPER_PACKAGE)
    for m in pkgutil.iter_modules(pkg.__path__, prefix=pkg.__name__ + "."):
        name = m.name
        leaf = name.rsplit(".", 1)[-1]
        if leaf.startswith("_"):  # skip disabled/private modules
            continue
        if name.endswith(".base") or name.endswith(".__init__"):
            continue
        if PINNED and leaf not in PINNED:
            continue
        yield importlib.import_module(name)

def run_all_scrapers():
    all_items = []
    loaded = []
    loaded_mods = []
    for mod in iter_scraper_modules():
        fetcher = getattr(mod, "fetch", None)
        if not callable(fetcher):
            continue
        loaded.append(mod.__name__)
        loaded_mods.append(mod)
        try:
            items = fetcher() or []
            all_items.extend(items)
        except Exception as e:
            print(f"[WARN] {mod.__name__} failed: {e}")
            continue
    print(f"[INFO] Loaded scrapers: {loaded or 'NONE'}")
    return all_items, loaded_mods

def main():
    items, mods = run_all_scrapers()

    # Dedupe by URL
    seen, unique = set(), []
    for it in items:
        url = it.get("url")
        if not url or url in seen:
            continue
        seen.add(url)
        unique.append(canonical(it))

    # Sort newest first
    def key(x):
        d = x.get("posted_date") or "0000-00-00"
        return (d, (x.get("title") or "").lower())
    unique.sort(key=key, reverse=True)

    # Source counts & meta keywords (per scraper)
    counts = Counter([it.get("source") or "unknown" for it in unique])
    kw_meta = {}
    for m in mods:
        slug = getattr(m, "SOURCE_SLUG", m.__name__.split(".")[-1])
        kws = getattr(m, "KEYWORDS", None)
        if kws:
            kw_meta[slug] = list(dict.fromkeys(kws))  # unique preserve order

    out = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "count": len(unique),
        "source_counts": counts,
        "meta": { "keywords": kw_meta },
        "items": unique,
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"[INFO] Wrote {OUT} with {len(unique)} items | by source: {dict(counts)} | meta.keywords: {kw_meta}")

if __name__ == "__main__":
    main()
