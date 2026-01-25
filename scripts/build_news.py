import csv, json, time
from pathlib import Path

import feedparser
import requests

FEEDS_CSV = Path("data/feeds.csv")
OUT_DIR = Path("data")
OUT_DIR.mkdir(parents=True, exist_ok=True)

TIMEOUT = 12
MAX_ITEMS_PER_FEED = 5
MAX_TOTAL_ITEMS = 400

def read_feeds():
    feeds = []
    with FEEDS_CSV.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            region = (row.get("region") or "").strip()
            name = (row.get("name") or "").strip()
            url = (row.get("url") or "").strip()
            if region and name and url.startswith("http"):
                feeds.append({"region": region, "name": name, "url": url})
    return feeds

def fetch_feed(feed):
    headers = {"User-Agent": "MakedonWorldNewsBot/1.0 (+https://makedonworldnews-cmyk.github.io/)"}
    r = requests.get(feed["url"], headers=headers, timeout=TIMEOUT)
    r.raise_for_status()
    parsed = feedparser.parse(r.content)

    items = []
    for e in parsed.entries[:MAX_ITEMS_PER_FEED]:
        title = (getattr(e, "title", "") or "").strip()
        link = (getattr(e, "link", "") or "").strip()
        published = (getattr(e, "published", "") or "").strip()
        if title and link:
            items.append({"title": title, "link": link, "published": published})
    return items

def main():
    feeds = read_feeds()
    out = {
        "updatedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "groups": []
    }
    errors = []

    by_region = {}
    for f in feeds:
        by_region.setdefault(f["region"], []).append(f)

    total = 0
    for region, sources in by_region.items():
        group_items = []
        for src in sources:
            try:
                items = fetch_feed(src)
                for it in items:
                    group_items.append({
                        "source": src["name"],
                        "title": it["title"],
                        "link": it["link"],
                        "published": it["published"]
                    })
                    total += 1
                    if total >= MAX_TOTAL_ITEMS:
                        break
            except Exception as e:
                errors.append({"source": src["name"], "url": src["url"], "error": str(e)})
                group_items.append({
                    "source": src["name"],
                    "title": "⚠️ Не може да се вчита (извор/timeout)",
                    "link": src["url"],
                    "published": ""
                })
            if total >= MAX_TOTAL_ITEMS:
                break

        out["groups"].append({"region": region, "items": group_items})
        if total >= MAX_TOTAL_ITEMS:
            break

    (OUT_DIR / "news.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT_DIR / "errors.json").write_text(json.dumps({"updatedAt": out["updatedAt"], "errors": errors}, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"OK: regions={len(out['groups'])} total_items={total} errors={len(errors)}")

if __name__ == "__main__":
    main()
