"""Chapter-aligned chunking and the shared tokenizer.

Chunk boundaries never cross a chapter, so a chunk is always a real passage of
a real book rather than an arbitrary character window.
"""

from __future__ import annotations

import re

import config

_TOKEN = re.compile(config.TOKEN_RE)


def tokenize(text):
    return _TOKEN.findall(text.lower())


class Chunks:
    """One chunking configuration: fixed size, chapter-aligned."""

    def __init__(self, corpus, size):
        self.size = size
        self.spans = corpus.chunk(size)
        self.texts = [corpus.text[s:e] for s, e in self.spans]
        self.tokens = [tokenize(t) for t in self.texts]
        self.ids = ["%d:%d" % (size, i) for i in range(len(self.spans))]

    def __len__(self):
        return len(self.spans)

    def span_of(self, cid):
        return self.spans[self.ids.index(cid)]

    def covering(self, start, end, coverage=None):
        """Chunk ids covering at least `coverage` of [start, end)."""
        want = config.REACH_COVERAGE if coverage is None else coverage
        needed = (end - start) * want
        out = []
        for i, (s, e) in enumerate(self.spans):
            overlap = min(e, end) - max(s, start)
            if overlap >= needed:
                out.append(self.ids[i])
        return out

    def overlap(self, cid, start, end):
        s, e = self.span_of(cid)
        return max(0, min(e, end) - max(s, start))
