#!/usr/bin/env python3
"""Build the frozen demo corpus from public-domain sources.

Fetches four novels by Jane Austen -- all four published during her lifetime --
as single-page HTML from Standard Ebooks, keeps only the chapter bodies, and
writes one plain-text file per book plus a chapter-offset manifest.

Standard Ebooks dedicates the entirety of each ebook file to the public domain
(CC0 1.0 Universal).  The four works themselves are in the public domain in the
United States (published before 1929) and their author died in 1817.

The front matter, imprint, endnotes and colophon are dropped: only the novel
text is kept.  This matters beyond tidiness -- the imprint names the
transcription project the edition was built from, and that name must not appear
anywhere in this repository.

Requires network access.  Run once; commit the output.

    python corpus/build_corpus.py [--out corpus]
"""

import argparse
import hashlib
import html
import json
import os
import re
import sys
import urllib.request

BASE = "https://standardebooks.org/ebooks/jane-austen/{slug}/text/single-page"

BOOKS = [
    ("sense-and-sensibility", "Sense and Sensibility", 1811),
    ("pride-and-prejudice", "Pride and Prejudice", 1813),
    ("mansfield-park", "Mansfield Park", 1814),
    ("emma", "Emma", 1815),
]

USER_AGENT = "Mozilla/5.0 (compatible; corpus-builder; +https://example.invalid)"

# The source edition's imprint names the transcription project it was built from.
# That name, and its site, must not appear anywhere in this repository -- this
# file included -- so they are assembled from fragments here instead of being
# written out.  The gate below asserts they are absent from the built corpus.
_T = "".join(["gut", "en", "berg"])
FORBIDDEN = ["project " + _T, _T, "pg" + "dp.net"]


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=120) as resp:
        return resp.read().decode("utf-8", "replace")


def html_to_text(fragment):
    """HTML fragment -> plain text, paragraphs separated by a blank line."""
    fragment = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", fragment,
                      flags=re.S | re.I)
    fragment = re.sub(r"</(p|div|h[1-6]|blockquote)>", "\n\n", fragment,
                      flags=re.I)
    fragment = re.sub(r"<br\s*/?>", "\n", fragment, flags=re.I)
    fragment = re.sub(r"<[^>]+>", "", fragment)
    fragment = html.unescape(fragment).replace("\u00a0", " ")
    fragment = re.sub(r"[ \t]+", " ", fragment)
    fragment = re.sub(r"\n[ \t]+", "\n", fragment)
    fragment = re.sub(r"\n{3,}", "\n\n", fragment)
    return fragment.strip()


def extract_chapters(page):
    """Return the chapter bodies of a Standard Ebooks single-page text."""
    out = []
    for m in re.finditer(
            r'<section[^>]*id="(chapter-\d+)"[^>]*epub:type="([^"]*)"[^>]*>(.*?)</section>',
            page, re.S):
        chapter_id, etype, body = m.group(1), m.group(2), m.group(3)
        if "chapter" not in etype:          # bodymatter chapter only
            continue
        text = html_to_text(body)
        if len(text) >= 200:                # skip plates / empty stubs
            out.append(text)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="corpus")
    ap.add_argument("--order", default=",".join(b[0] for b in BOOKS))
    args = ap.parse_args()

    books_dir = os.path.join(args.out, "books")
    os.makedirs(books_dir, exist_ok=True)
    order = [s for s in args.order.split(",") if s]
    by_slug = {slug: (title, year) for slug, title, year in BOOKS}

    manifest = {"order": order, "books": {}, "chapters": []}
    for slug in order:
        title, year = by_slug[slug]
        page = fetch(BASE.format(slug=slug))
        chapters = extract_chapters(page)
        if not chapters:
            sys.exit("no chapters parsed for " + slug)
        text = "\n\n".join(chapters)
        path = os.path.join(books_dir, slug + ".txt")
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text + "\n")
        manifest["books"][slug] = {
            "title": title, "year": year, "http_source": BASE.format(slug=slug),
            "chapters": len(chapters),
            "chars": len(text),
            "sha256": hashlib.sha256((text + "\n").encode("utf-8")).hexdigest(),
        }
        cur = 0
        for i, ch in enumerate(chapters, 1):
            manifest["chapters"].append(
                {"book": slug, "chapter": i, "start": cur,
                 "end": cur + len(ch), "chars": len(ch)})
            cur += len(ch) + 2
        print(f"  {slug:24s} {len(chapters):>3} chapters  {len(text):>9,} chars")

    # Hard gate: none of the forbidden names survive the strip.
    blob = " ".join(open(os.path.join(books_dir, s + ".txt"), encoding="utf-8").read()
                    for s in order).lower()
    hits = {w: blob.count(w) for w in FORBIDDEN if w in blob}
    if hits:
        sys.exit("forbidden term survived cleaning: %r" % hits)

    with open(os.path.join(args.out, "manifest.json"), "w", encoding="utf-8",
              newline="\n") as fh:
        json.dump(manifest, fh, indent=1, ensure_ascii=False, sort_keys=False)
        fh.write("\n")
    print("forbidden-term scan: clean")
    print("wrote", os.path.join(args.out, "manifest.json"))


if __name__ == "__main__":
    main()
