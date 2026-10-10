"""The distance check, applied to a frozen exam.

A relation-level fake is only valid when the replacement anchor sits further from
the answer than the largest chunk: otherwise some chunking configuration would
place both in one chunk and the question would become answerable in that arm.
The check reads only corpus geometry, so no retriever can influence it, and it
runs once at seal time.
"""

from __future__ import annotations

import config


def check(corpus, rows):
    """(failures, distances) for the relation-level rows of an exam."""
    failures, distances = [], {}
    for row in rows:
        if row["bucket"] != "relation-fake":
            continue
        anchor = corpus.by_id[row["anchor_entity"]]
        answer = corpus.by_id[row["answer_entity"]]
        dist = corpus.min_distance(anchor, answer)
        distances[row["id"]] = dist
        if dist is None or dist <= config.MAX_CHUNK_LEN:
            failures.append((row["id"], "distance %r <= max_chunk_len %d"
                             % (dist, config.MAX_CHUNK_LEN)))
        same_book = anchor.book == answer.book
        if (row["tier"] == "intra") != same_book:
            failures.append((row["id"], "tier %r does not match books %s/%s"
                             % (row["tier"], anchor.book, answer.book)))
    return failures, distances
