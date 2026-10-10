"""Reachability of a gold span, decided without any retriever.

A gold span is reachable under a chunking configuration when a single chunk
covers at least `config.REACH_COVERAGE` of it.  The exam keeps a question only
if its gold span is reachable under EVERY configured chunk size: otherwise a
large-chunk arm would be credited for questions a small-chunk arm could never
answer, and the claim that every arm sees the same questions would be false.

Nothing here looks at scores, so a bug in a retriever cannot move the exam.
"""

from __future__ import annotations

import bisect

import config


class SpanIndex:
    """Chunk spans with a bisect lookup, so testing a span costs the chunks it
    actually touches instead of a walk over the whole book."""

    def __init__(self, spans):
        self.spans = list(spans)
        self.starts = [s for s, _ in self.spans]

    def max_coverage(self, start, end):
        i = max(0, bisect.bisect_right(self.starts, start) - 1)
        best = 0
        while i < len(self.spans) and self.spans[i][0] < end:
            s, e = self.spans[i]
            cover = min(e, end) - max(s, start)
            if cover > best:
                best = cover
            i += 1
        return best

    def covers(self, start, end, want=None):
        want = config.REACH_COVERAGE if want is None else want
        return self.max_coverage(start, end) >= (end - start) * want


def covers(spans, start, end, want=None):
    """Sequence of chunks covering at least `want` of [start, end)?

    Accepts a SpanIndex or a plain sequence of spans.
    """
    if isinstance(spans, SpanIndex):
        return spans.covers(start, end, want)
    want = config.REACH_COVERAGE if want is None else want
    needed = (end - start) * want
    for s, e in spans:
        if min(e, end) - max(s, start) >= needed:
            return True
    return False


def reachable_everywhere(corpus, span, sizes=None):
    """{size: bool} for one span, plus a yes/no over all sizes."""
    sizes = config.CHUNK_SIZES if sizes is None else sizes
    per = {}
    for size in sizes:
        per[size] = SpanIndex(corpus.chunk(size)).covers(span[0], span[1])
    return per, all(per.values())


def filter_rows(corpus, rows, sizes=None):
    """Keep the rows whose gold span is reachable under every chunk size.

    Returns (kept, dropped, report).  The report carries the accounting the
    design asks for: totals, reachable count, exclusions, and the per-size
    reachable count that would have been used had the exam not been filtered.
    """
    sizes = config.CHUNK_SIZES if sizes is None else sizes
    spans = {size: corpus.chunk(size) for size in sizes}
    kept, dropped = [], []
    per_size = {str(size): 0 for size in sizes}
    for row in rows:
        span = tuple(row["answer_span"])
        flags = {size: covers(spans[size], span[0], span[1]) for size in sizes}
        for size, ok in flags.items():
            if ok:
                per_size[str(size)] += 1
        row = dict(row, reachable=flags)
        if all(flags.values()):
            kept.append(row)
        else:
            dropped.append(row)
    report = {
        "chunk_sizes": list(sizes),
        "reach_coverage": config.REACH_COVERAGE,
        "n_total": len(rows),
        "n_reachable_all_sizes": len(kept),
        "n_excluded": len(dropped),
        "n_reachable_per_size": per_size,
    }
    return kept, dropped, report
