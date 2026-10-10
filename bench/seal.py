"""Freeze an exam to disk.

Order matters: questions whose answer span is not reachable under every chunking
configuration are dropped *before* the frequency pairing, so a small-chunk arm
cannot be handed questions it could never answer and the pairing stays valid
inside every frequency band.  The manifest then records the frozen parameters,
the reachability accounting and the sha256 of every input, so a reported number
can be checked against the configuration that was fixed before the run.
"""

from __future__ import annotations

import hashlib
import json
import os
import random
import sys

import config
import corpus as C
import distance
import examgen as E
import reachcheck

CHUNK_SIZES = config.CHUNK_SIZES
MAX_CHUNK_LEN = config.MAX_CHUNK_LEN
SEED = config.SEED
BUCKET_ORDER = ("gold", "relation-fake-intra", "relation-fake-cross", "entity-fake")


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def row(q, corpus, n):
    ent = corpus.by_id[q.anchor_entity] if q.anchor_entity else None
    return {
        "id": n,
        "bucket": q.bucket,
        "tier": q.tier,
        "query": q.query,
        "anchor": q.anchor,
        "anchor_entity": q.anchor_entity,
        "anchor_band": ent.band() if ent else None,
        "answer_entity": q.answer_entity,
        "answer_span": [q.answer_start, q.answer_end],
        "sentence_span": list(q.sentence_span),
        "book": q.book,
    }


def frozen_config():
    """Every number that was fixed before any result was seen."""
    return {
        "seed": config.SEED,
        "chunk_sizes": list(config.CHUNK_SIZES),
        "max_chunk_len": config.MAX_CHUNK_LEN,
        "top_k": list(config.TOP_K),
        "drop_ratios": list(config.DROP_RATIOS),
        "hit_overlap": config.HIT_OVERLAP,
        "reach_coverage": config.REACH_COVERAGE,
        "overlap_bands": [list(b) for b in config.OVERLAP_BANDS],
        "target_gold_abstain": config.TARGET_GOLD_ABSTAIN,
        "calib_fraction": config.CALIB_FRACTION,
        "bm25_k1": config.BM25_K1,
        "bm25_b": config.BM25_B,
        "token_re": config.TOKEN_RE,
    }


def _entity_counts(corpus):
    counts = {}
    for e in corpus.entities:
        counts[e.type] = counts.get(e.type, 0) + 1
    return counts


def filter_reachable(corpus, buckets, sizes=None):
    """Drop questions whose answer span no chunk covers, under every size."""
    sizes = config.CHUNK_SIZES if sizes is None else sizes
    spans = {size: reachcheck.SpanIndex(corpus.chunk(size)) for size in sizes}
    kept = {name: [] for name in buckets}
    per_size = {str(size): 0 for size in sizes}
    total = 0
    for name, questions in buckets.items():
        for q in questions:
            total += 1
            flags = {size: reachcheck.covers(spans[size], q.answer_start, q.answer_end)
                     for size in sizes}
            for size, ok in flags.items():
                if ok:
                    per_size[str(size)] += 1
            if all(flags.values()):
                kept[name].append(q)
    kept_n = sum(len(v) for v in kept.values())
    report = {
        "chunk_sizes": list(sizes),
        "reach_coverage": config.REACH_COVERAGE,
        "n_total_candidates": total,
        "n_kept": kept_n,
        "n_excluded": total - kept_n,
        "n_reachable_per_size": per_size,
    }
    return kept, report


def main(argv):
    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "exam")
    per_arm = int(argv[argv.index("--per-arm") + 1]) if "--per-arm" in argv else 300
    out_dir = os.path.abspath(out_dir)
    os.makedirs(out_dir, exist_ok=True)

    corpus = C.Corpus()
    buckets = E.build(corpus, MAX_CHUNK_LEN)
    problems = E.validate(corpus, buckets, MAX_CHUNK_LEN)
    if problems:
        print("refusing to freeze: %d validation problems" % len(problems))
        for p in problems[:10]:
            print("   ", p)
        return 2

    kept, reach = filter_reachable(corpus, buckets)
    problems = E.validate(corpus, kept, MAX_CHUNK_LEN)
    if problems:
        print("refusing to freeze: %d problems after the reachability filter"
              % len(problems))
        for p in problems[:10]:
            print("   ", p)
        return 2

    paired = E.pair_by_band(corpus, kept, rng=random.Random(SEED))
    # The reported gold set is the one paired against the cross tier: cross-book
    # fakes are plentiful in every frequency band, so that pool keeps the gold
    # population's own frequency composition instead of being cut down to the
    # scarce same-book tier.
    arms = {
        "gold": paired["cross"]["gold"],
        "relation-fake-intra": paired["intra"]["fake"],
        "relation-fake-cross": paired["cross"]["fake"],
        "entity-fake": kept["entity-fake"],
    }
    rng = random.Random(SEED)
    rows, counts = [], {}
    for name in BUCKET_ORDER:
        pool = list(arms[name])
        rng.shuffle(pool)
        picked = pool[:per_arm]
        counts[name] = len(picked)
        for q in picked:
            rows.append(row(q, corpus, len(rows)))

    failures, distances = distance.check(corpus, rows)
    if failures:
        print("refusing to freeze: %d relation-level rows fail the distance rule"
              % len(failures))
        for f in failures[:10]:
            print("   ", f)
        return 2

    path = os.path.join(out_dir, "exam.jsonl")
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")

    manifest = {
        "config": frozen_config(),
        "per_arm": per_arm,
        "counts": counts,
        "gold_paired_with": "cross",
        "pairing_per_band": {tier: paired[tier]["per_band"] for tier in ("intra", "cross")},
        "pool_sizes_after_filter": {name: len(arms[name]) for name in BUCKET_ORDER},
        "reachability": reach,
        "distance_check": {"n_checked": len(distances),
                           "max_chunk_len": config.MAX_CHUNK_LEN, "failures": 0},
        "entity_counts": _entity_counts(corpus),
        "corpus_manifest_sha256": sha256_file(os.path.join(corpus.root, "corpus",
                                                           "manifest.json")),
        "entities_sha256": sha256_file(os.path.join(corpus.root, "corpus",
                                                    "entities.json")),
        "exam_sha256": sha256_file(path),
    }
    with open(os.path.join(out_dir, "manifest.json"), "w", encoding="utf-8",
              newline="\n") as fh:
        json.dump(manifest, fh, indent=1, sort_keys=True)
        fh.write("\n")

    print("frozen %d questions -> %s" % (len(rows), path))
    for name in BUCKET_ORDER:
        print("   %-22s %5d of a %6d pool" % (name, counts[name], len(arms[name])))
    print("   reachability: %d candidates, %d kept, %d excluded (per size %s)"
          % (reach["n_total_candidates"], reach["n_kept"], reach["n_excluded"],
             reach["n_reachable_per_size"]))
    print("   distance rule: %d rows checked, 0 failures" % len(distances))
    print("   exam sha256 = %s" % manifest["exam_sha256"])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
