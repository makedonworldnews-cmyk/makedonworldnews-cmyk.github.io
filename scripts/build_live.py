# scripts/build_live.py
import json, time, sys
from pathlib import Path

import feedparser
import requests

OUT_DIR = Path("data")
OUT_DIR.mkdir(parents=True, exist_ok=True)

# IMPORTANT: Start small. Later you can add more feeds safely.
# Replace / extend this list with your 818 feed URLs gradually.
FEEDS = [
    {"region": "Македонија", "name": "МИА", "url": "https://mia.mk/rss"},
    {"region": "Македонија", "name": "Makfax", "url": "https://makfax.com.mk/feed/"},
    {"region": "Македонија", "name": "NetPress", "url": "https://netpress.com.mk/feed/"},
    {"region": "Свет", "name": "BBC", "url": "https://feeds.bbci.co.uk/news/world/rss.xml"},
    {"region": "Свет", "name": "Al Jazeera", "url": "https://www.aljazeera.com/xml/rss/all.xml"},
]

TIMEOUT = 12
MAX_ITEMS_PER_FEED = 5

def fetch_feed(feed):
    url = feed["url"]
    headers = {"User-Agent": "MakedonWorldNewsBot/1.0 (+https://makedonworldnews-cmyk.github.io/)"}
    r = requests.get(url, headers=headers, timeout=TIMEOUT)
    r.raise_for_status()
    parsed = feedparser.parse(r.content)

    items = []
    for e in parsed.entries[:MAX_ITEMS_PER_FEED]:
        title = (getattr(e, "title", "") or "").strip()
        link = (getattr(e, "link", "") or "").strip()
        if title and link:
            items.append({
                "title": title,
                "link": link,
                "published": (getattr(e, "published", "") or "").strip(),
            })
    return items

def main():
    live = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "items": []
    }
    errors = []

    for f in FEEDS:
        try:
            items = fetch_feed(f)
            for it in items:
                live["items"].append({
                    "region": f["region"],
                    "source": f["name"],
                    **it
                })
        except Exception as e:
            errors.append({"source": f["name"], "url": f["url"], "error": str(e)})

    # Optional: sort newest-first when published exists
    # Keep simple and stable:
    live["items"] = live["items"][:200]  # cap for performance

    (OUT_DIR / "live.json").write_text(json.dumps(live, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT_DIR / "errors.json").write_text(json.dumps({"generated_at": live["generated_at"], "errors": errors},
                                                    ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"OK: {len(live['items'])} items, {len(errors)} errors")

if __name__ == "__main__":
    main()
