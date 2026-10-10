"""IDF-weighted overlap between a question and the passage it was built from.

The overlap is a leak measure: it says how much of a question is still verbatim
source text, and therefore how much of the answer a retriever could reach by
literal matching alone.  It is weighted by IDF rather than counted in words, so
that keeping a rare name counts for more than keeping a comma.

Document frequency comes from the chapters, which is the finest split that
matches how the corpus is actually organised.
"""

from __future__ import annotations

import collections
import math

import chunking
import config


class ChapterIdf:
    def __init__(self, corpus):
        self.n = len(corpus.chapters)
        self.df = collections.Counter()
        for ch in corpus.chapters:
            base = corpus.book_span[ch["book"]][0]
            text = corpus.text[base + ch["start"]:base + ch["end"]]
            self.df.update(set(chunking.tokenize(text)))

    def __call__(self, token):
        return math.log((self.n + 1.0) / (self.df[token] + 1.0)) + 1.0


def overlap(query, source, idf):
    """Sum of IDF over the tokens the question shares with the source passage."""
    q = set(chunking.tokenize(query.replace("[MASK]", " ")))
    s = set(chunking.tokenize(source))
    if not q:
        return 0.0
    den = sum(idf(t) for t in q)
    if not den:
        return 0.0
    return sum(idf(t) for t in q & s) / den


def band(value, bands=None):
    """Band label for an overlap value, e.g. '0.6-0.8'."""
    bands = config.OVERLAP_BANDS if bands is None else bands
    for lo, hi in bands:
        if lo <= value < hi:
            return "%.1f-%.1f" % (lo, min(hi, 1.0))
    return "%.1f-%.1f" % bands[-1]


def annotate(corpus, rows, idf=None):
    """Add 'overlap' and 'overlap_band' to each row."""
    idf = idf or ChapterIdf(corpus)
    out = []
    for row in rows:
        s, e = row["sentence_span"]
        value = overlap(row["query"], corpus.text[s:e], idf)
        out.append(dict(row, overlap=value, overlap_band=band(value)))
    return out
