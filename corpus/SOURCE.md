# Corpus: sources and public-domain basis

Four novels by Jane Austen, **all four published during her lifetime**:

| File | Work | First published | Chapters | Size (characters) |
|---|---|---|---|---|
| `books/sense-and-sensibility.txt` | Sense and Sensibility | 1811 | 50 | 668,536 |
| `books/pride-and-prejudice.txt` | Pride and Prejudice | 1813 | 61 | 684,054 |
| `books/mansfield-park.txt` | Mansfield Park | 1814 | 48 | 881,530 |
| `books/emma.txt` | Emma | 1815 | 55 | 880,580 |

Total: 214 chapters, 3,114,700 characters.

Austen's other two completed novels are deliberately **excluded**: they were published
after her death, and this corpus only uses works published while the author was alive.

## Why public domain

All four works were published before 1929, and the author died in **1817** — more than
100 years ago. That satisfies the United States public-domain rule and also clears
life-plus-100-year terms used in other jurisdictions.

## Transcription source

Text is taken from the **Standard Ebooks** editions, fetched as single-page HTML on
2026-10-11. Standard Ebooks dedicates the entirety of each ebook file — markup and cover
included — to the public domain under **CC0 1.0 Universal**; no attribution is required,
and it is given here anyway. The transcription source URL for each book is recorded in
`manifest.json`.

## What the build keeps

Only the **chapter bodies**. Title page, imprint, endnotes, colophon and version notes are
dropped. This is not only tidiness: the imprint of the source edition names the
transcription project the edition was built from, and that name must not appear anywhere in
this repository. `build_corpus.py` therefore **assembles that name from fragments** for its
own absence check instead of spelling it out, and asserts the built corpus does not contain
it. The assertion runs on every build and fails loudly (`forbidden-term survived`) rather
than silently shipping it.

## Reproducing the corpus

```
python corpus/build_corpus.py --out corpus        # needs network access
```

The script downloads the four editions, strips everything but the chapters, writes
`books/*.txt` and `manifest.json`, and runs the forbidden-term gate. Per-book SHA-256
values are recorded in `manifest.json`; every run rebuilds them from the fetched bytes, so
a changed upstream edition shows up as a changed hash.
