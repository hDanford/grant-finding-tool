import json, os, time, hashlib
from scrapers import dhs_frg, ofca, ohio_rrr

OUT = os.path.join("data", "grants.json")
os.makedirs("data", exist_ok=True)

def canonical(item):
    h = hashlib.sha256((item.get("title","") + item.get("url","")).encode("utf-8")).hexdigest()[:16]
    item["id"] = h
    return item

def main():
    all_items = []
    for fetcher in (dhs_frg.fetch, ofca.fetch, ohio_rrr.fetch):
        try:
            all_items.extend(fetcher())
        except Exception:
            continue

    # dedupe by URL
    seen = set()
    unique = []
    for it in all_items:
        url = it.get("url")
        if not url or url in seen:
            continue
        seen.add(url)
        unique.append(canonical(it))

    # sort newest first
    def key(x):
        d = x.get("posted_date") or "0000-00-00"
        return d, x.get("title","").lower()
    unique.sort(key=key, reverse=True)

    out = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "count": len(unique),
        "items": unique
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"Wrote {OUT} with {len(unique)} items")

if __name__ == "__main__":
    main()
