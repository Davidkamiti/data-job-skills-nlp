"""Collect job posts from Hacker News "Ask HN: Who is hiring?" monthly threads.

Uses the public Algolia HN Search API (no API key). Author names are never
saved and email addresses are redacted, so the output holds only post text.

Usage (from the repo root):
    python src/collect_hn_hiring.py --months 12
"""
import argparse
import re
import time
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

import pandas as pd
import requests

BASE = "https://hn.algolia.com/api/v1"
TITLE_RE = re.compile(r"Ask HN: Who is hiring\?\s*\((\w+)\s+(\d{4})\)", re.IGNORECASE)
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
PHONE_RE = re.compile(r"\+?\d{1,3}[\s.-]?\(?\d{2,4}\)?[\s.-]\d{3,4}[\s.-]\d{3,4}")
HEADERS = {"User-Agent": "data-job-skills-nlp (portfolio project)"}
PAUSE_SECONDS = 1.0  # be polite to the API


def get_json(session, url, params=None, retries=4):
    """GET with simple retry/backoff. Returns parsed JSON."""
    for attempt in range(retries):
        try:
            resp = session.get(url, params=params, timeout=60)
            if resp.status_code == 200:
                return resp.json()
            if resp.status_code not in (429, 500, 502, 503, 504):
                resp.raise_for_status()
        except requests.RequestException as exc:
            print(f"  request problem ({exc}); retrying...")
        time.sleep(2 ** attempt * 2)
    raise RuntimeError(f"Failed to fetch {url} after {retries} attempts")


def month_label(title, created_at_i):
    """'2026-10' from the thread title, falling back to the creation date."""
    m = TITLE_RE.search(title or "")
    if m:
        try:
            return datetime.strptime(f"{m.group(1)} {m.group(2)}", "%B %Y").strftime("%Y-%m")
        except ValueError:
            pass
    return datetime.fromtimestamp(created_at_i, tz=timezone.utc).strftime("%Y-%m")


def find_threads(session, months):
    """Return the newest `months` hiring threads as dicts (id, title, month)."""
    threads = {}
    for page in range(0, 5):
        data = get_json(session, f"{BASE}/search_by_date", params={
            "query": "Ask HN: Who is hiring?",
            "tags": "story,author_whoishiring",
            "hitsPerPage": 100,
            "page": page,
        })
        hits = data.get("hits", [])
        for h in hits:
            if TITLE_RE.search(h.get("title") or ""):       # skips "Who wants to be hired?" etc.
                threads[h["objectID"]] = {
                    "id": h["objectID"],
                    "title": h["title"],
                    "created_at_i": h["created_at_i"],
                    "month": month_label(h["title"], h["created_at_i"]),
                }
        if len(hits) < 100 or len(threads) >= months:
            break
        time.sleep(PAUSE_SECONDS)
    ordered = sorted(threads.values(), key=lambda t: t["created_at_i"], reverse=True)
    return ordered[:months]


class _TextExtractor(HTMLParser):
    """Turn the HTML in an HN comment into plain text with line breaks."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag in ("p", "br", "li", "div"):
            self.parts.append("\n")

    def handle_data(self, data):
        self.parts.append(data)


def clean_text(html):
    parser = _TextExtractor()
    parser.feed(html or "")
    text = "".join(parser.parts)
    text = EMAIL_RE.sub("[email]", text)
    text = PHONE_RE.sub("[phone]", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n", text)
    return text.strip()


def extract_posts(thread, item_json):
    """Top-level comments of a thread are the job posts. Replies are discussion, so skipped."""
    rows = []
    for child in item_json.get("children", []):
        text = clean_text(child.get("text"))
        if len(text) < 40:                                   # deleted or empty
            continue
        rows.append({
            "thread_month": thread["month"],
            "thread_id": thread["id"],
            "post_id": child["id"],
            "posted_at": child.get("created_at"),
            "headline": text.split("\n", 1)[0][:200],
            "text": text,
            "n_chars": len(text),
        })
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--months", type=int, default=12, help="how many monthly threads to fetch")
    ap.add_argument("--out", default="data/raw/hn_hiring_posts.csv")
    ap.add_argument("--sample-out", default="data/sample/hn_hiring_sample.csv")
    ap.add_argument("--sample-size", type=int, default=50)
    args = ap.parse_args()

    session = requests.Session()
    session.headers.update(HEADERS)

    threads = find_threads(session, args.months)
    if not threads:
        raise SystemExit("No hiring threads found. Check your internet connection.")
    print(f"Found {len(threads)} threads: {threads[-1]['month']} to {threads[0]['month']}")

    rows = []
    for t in threads:
        print(f"Fetching {t['title']} ...")
        item = get_json(session, f"{BASE}/items/{t['id']}")
        posts = extract_posts(t, item)
        print(f"  {len(posts)} posts")
        rows.extend(posts)
        time.sleep(PAUSE_SECONDS)

    df = pd.DataFrame(rows).drop_duplicates(subset="post_id").sort_values(
        ["thread_month", "post_id"]).reset_index(drop=True)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False)

    sample = df.sample(min(args.sample_size, len(df)), random_state=42)
    sample_out = Path(args.sample_out)
    sample_out.parent.mkdir(parents=True, exist_ok=True)
    sample.to_csv(sample_out, index=False)

    print(f"\nSaved {len(df)} posts to {out}")
    print(f"Saved a {len(sample)}-post sample to {sample_out}")
    print("\nPosts per month:")
    print(df.groupby("thread_month").size().to_string())
    print(f"\nMedian post length: {int(df['n_chars'].median())} characters")


if __name__ == "__main__":
    main()
