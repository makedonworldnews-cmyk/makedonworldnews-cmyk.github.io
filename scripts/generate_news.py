import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import feedparser

ROOT = Path(__file__).resolve().parents[1]
FEEDS_FILE = ROOT / "feeds.json"
OUT_FILE = ROOT / "data" / "news.json"

MAX_ITEMS_PER_GROUP = 12  # лимит по регион
TIMEOUT_SECONDS = 20


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def best_link(entry: Dict[str, Any]) -> str:
    # feedparser entries can have 'link' plus alternates
    link = entry.get("link") or ""
    if link:
        return link
    links = entry.get("links") or []
    if links and isinstance(links, list):
        for l in links:
            if isinstance(l, dict) and l.get("href"):
                return str(l["href"])
    return ""


def best_published(entry: Dict[str, Any]) -> str:
    # prefer published_parsed; fallback to updated_parsed
    tp = entry.get("published_parsed") or entry.get("updated_parsed")
    if tp:
        try:
            return datetime.fromtimestamp(time.mktime(tp), tz=timezone.utc).isoformat(timespec="seconds")
        except Exception:
            pass
    # fallback raw strings if present (may be non-ISO)
    return entry.get("published") or entry.get("updated") or ""


def main() -> None:
    if not FEEDS_FILE.exists():
        raise SystemExit("Missing feeds.json in repo root.")

    cfg = json.loads(FEEDS_FILE.read_text(encoding="utf-8"))
    feeds = cfg.get("feeds") or []
    if not isinstance(feeds, list) or not feeds:
        raise SystemExit("feeds.json must contain a non-empty 'feeds' array.")

    # Build groups by region
    groups_map: Dict[str, List[Dict[str, Any]]] = {}

    for f in feeds:
        region = (f.get("region") or "Регион").strip()
        source = (f.get("source") or "Извор").strip()
        url = (f.get("url") or "").strip()
        if not url:
            continue

        parsed = feedparser.parse(url, agent="MakedonWorldNewsBot/1.0", request_headers={"Cache-Control": "no-cache"})
        if getattr(parsed, "bozo", False):
            # skip broken feeds but keep going
            continue

        entries = getattr(parsed, "entries", []) or []
        for e in entries[: MAX_ITEMS_PER_GROUP * 2]:
            title = (e.get("title") or "").strip()
            link = best_link(e).strip()
            if not title or not link:
                continue
            item = {
                "source": source,
                "title": title,
                "link": link,
                "published_at": best_published(e)
            }
            groups_map.setdefault(region, []).append(item)

    # Clean + limit
    groups = []
    for region, items in groups_map.items():
        # sort by published_at if iso-ish, else leave stable
        def key(it: Dict[str, Any]) -> str:
            return it.get("published_at") or ""
        items_sorted = sorted(items, key=key, reverse=True)

        # de-dup by link
        seen = set()
        uniq = []
        for it in items_sorted:
            lk = it.get("link")
            if not lk or lk in seen:
                continue
            seen.add(lk)
            uniq.append(it)
            if len(uniq) >= MAX_ITEMS_PER_GROUP:
                break

        groups.append({"region": region, "items": uniq})

    # stable order by region name
    groups = sorted(groups, key=lambda g: g.get("region", ""))

    out = {
        "generated_at": iso_now(),
        "groups": groups
    }

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUT_FILE.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
