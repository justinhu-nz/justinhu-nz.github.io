#!/usr/bin/env python3
"""
Fetches the latest articles from the Authory RSS feed and patches index.html.
Run from the repo root: python3 scripts/update_articles.py
"""

import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
import re
import sys

RSS_URL = "https://authory.com/justinhu/rss"
INDEX_PATH = "index.html"
LIMIT = 5

# Markers that bound the article list inside the JSON-encoded template string
ARTICLE_LIST_START = '>Latest stories<\\u002Fp>\\n\\n<div style=\\"display: flex; flex-direction: column; font-size: 17px\\">\\n'
ARTICLE_LIST_END   = '\\n<\\u002Fdiv>\\n<p style=\\"font-size: 14px; margin: 16px 0 0\\">'


def fetch_rss(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "justinhu-site/1.0"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return resp.read()


def parse_articles(xml_bytes: bytes, limit: int) -> list[dict]:
    root = ET.fromstring(xml_bytes)
    channel = root.find("channel")
    articles = []
    for item in channel.findall("item")[:limit]:
        title = item.findtext("title", "").strip()
        link  = item.findtext("link",  "").strip()
        pub   = item.findtext("pubDate", "").strip()
        try:
            dt    = datetime.strptime(pub.replace(" GMT", " +0000"), "%a, %d %b %Y %H:%M:%S %z")
            label = f"{dt.day} {dt.strftime('%b')}"
        except ValueError:
            label = ""
        if title and link:
            articles.append({"title": title, "link": link, "date": label})
    return articles


def encode(s: str) -> str:
    """Escape a string for insertion into the JSON-encoded template."""
    return s.replace("\\", "\\\\").replace('"', '\\"')


def build_article_html(articles: list[dict]) -> str:
    REGULAR_STYLE = (
        'display: flex; justify-content: space-between; align-items: baseline; '
        'gap: 19px; padding: 12px 0; border-top: 1px solid rgba(0,0,0,.06); '
        'color: #444; text-decoration: none'
    )
    LAST_STYLE = (
        'display: flex; justify-content: space-between; align-items: baseline; '
        'gap: 19px; padding: 12px 0; border-top: 1px solid rgba(0,0,0,.06); '
        'border-bottom: 1px solid rgba(0,0,0,.06); color: #444; text-decoration: none'
    )

    rows = []
    for i, a in enumerate(articles):
        style = LAST_STYLE if i == len(articles) - 1 else REGULAR_STYLE
        title = encode(a["title"])
        link  = encode(a["link"])
        date  = encode(a["date"])
        rows.append(
            f'<a href=\\"{link}\\" class=\\"article\\" style=\\"{style}\\">'
            f'\\n<span style=\\"line-height: 1.45\\">{title}<\\u002Fspan>'
            f'\\n<span style=\\"font-size: 14px; color: #888; white-space: nowrap; flex-shrink: 0\\">{date}<\\u002Fspan>'
            f'\\n<\\u002Fa>'
        )
    return "\\n".join(rows)


def patch_index(articles: list[dict]) -> bool:
    with open(INDEX_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    start_idx = content.find(ARTICLE_LIST_START)
    end_idx   = content.find(ARTICLE_LIST_END)

    if start_idx == -1 or end_idx == -1:
        print("ERROR: Could not locate article list markers in index.html", file=sys.stderr)
        sys.exit(1)

    start_idx += len(ARTICLE_LIST_START)
    new_articles = build_article_html(articles)
    new_content  = content[:start_idx] + new_articles + content[end_idx:]

    if new_content == content:
        print("No changes — articles already up to date.")
        return False

    with open(INDEX_PATH, "w", encoding="utf-8") as f:
        f.write(new_content)
    print(f"Updated {len(articles)} articles in {INDEX_PATH}.")
    return True


if __name__ == "__main__":
    print(f"Fetching {RSS_URL} ...")
    xml_bytes = fetch_rss(RSS_URL)
    articles  = parse_articles(xml_bytes, LIMIT)
    if not articles:
        print("No articles found in feed — aborting without changes.", file=sys.stderr)
        sys.exit(1)
    for a in articles:
        print(f"  {a['date']:6}  {a['title']}")
    patch_index(articles)
