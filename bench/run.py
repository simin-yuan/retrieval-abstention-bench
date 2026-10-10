"""Evaluate a frozen exam and summarise the result.

One cell = (retriever, chunk size, top-k, drop ratio).  Every cell is scored on
exactly the same questions, and criterion A's threshold is re-derived inside the
cell from the calibration half of the gold questions, by the rule fixed in
`config.py`.  Reported numbers come from the other half.
"""

from __future__ import annotations

import json
import os
import random

import abstain
import bm25
import chunking
import config
import corpus as C
import examgen
import leakcheck
import metrics
import ngram_tfidf

RETRIEVERS = {"bm25": bm25.BM25, "ngram-tfidf": ngram_tfidf.NgramTfidf}

BUCKET_KEYS = ("gold", "entity-fake", "relation-fake-intra", "relation-fake-cross")


def mean(values):
    values = list(values)
    return (sum(values) / len(values)) if values else float("nan")


def bucket_key(row):
    if row["bucket"] == "relation-fake":
        return "relation-fake-" + row["tier"]
    return row["bucket"]


def load_exam(path):
    with open(path, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def build_index(corpus, retriever, size):
    chunks = chunking.Chunks(corpus, size)
    return chunks, RETRIEVERS[retriever](chunks)


class OracleIndex:
    """A retriever handed the right chunk for every question.

    Used by the self-tests to show the ceiling: even a perfect top-1 cannot make
    a relation-level fake answerable, because the anchor is provably absent from
    the chunk that holds the answer (see `distance`).
    """

    def __init__(self, chunks, rows):
        self.ids = chunks.ids
        self.map = {}
        for row in rows:
            cover = chunks.covering(row["answer_span"][0], row["answer_span"][1])
            self.map[tuple(chunking.tokenize(row["query"]))] = (
                chunks.ids.index(cover[0]) if cover else None)

    def search(self, tokens, k):
        i = self.map.get(tuple(tokens))
        if i is None:
            return []
        tail = [j for j in range(len(self.ids)) if j != i][:max(0, k - 1)]
        return [(i, 1.0)] + [(j, 0.0) for j in tail]


def rank_with(index, chunks, rows, drop_ratio=0.0, kmax=None):
    """Ranking from an externally supplied retriever (used by the self-tests)."""
    kmax = kmax or max(config.TOP_K)
    ranked = []
    for row in rows:
        query = row["query"]
        if drop_ratio:
            query = examgen.drop_context(query, row["anchor"], drop_ratio,
                                         random.Random("%d-%d-%.1f" % (config.SEED, row["id"], drop_ratio)))
        ranked.append((row, query, index.search(chunking.tokenize(query), kmax)))
    return ranked


def rank_all(corpus, rows, retriever, size, drop_ratio=0.0, kmax=None):
    """Score every question once, at the deepest top-k the grid needs.

    Cells that differ only in k reuse the same ranking, which is what keeps the
    whole grid affordable.
    """
    chunks, index = build_index(corpus, retriever, size)
    return chunks, rank_with(index, chunks, rows, drop_ratio, kmax)


def records_for_k(corpus, chunks, ranked_rows, k, idf=None):
    """Per-question records for one cell, cut to top-k.

    A retriever is allowed to return nothing; that is recorded as a decline
    rather than crashing the harness.
    """
    out = []
    for row, query, ranking in ranked_rows:
        ranking = ranking[:k]
        span_s, span_e = row["answer_span"]
        span_len = max(1, span_e - span_s)
        need = config.HIT_OVERLAP * span_len
        src_s, src_e = row["sentence_span"]
        base = {
            "id": row["id"],
            "bucket": row["bucket"],
            "tier": row["tier"],
            "key": bucket_key(row),
            "band": row.get("anchor_band"),
            "overlap": row.get("overlap"),
            "overlap_band": row.get("overlap_band"),
            "query_overlap": leakcheck.overlap(query, corpus.text[src_s:src_e], idf) if idf else None,
        }
        if not ranking:
            out.append(dict(base, top1_score=0.0, top1_id=None, top1_cover=0.0,
                            hit=False, retrieved_chars=0,
                            anchor_in_top1=False, anchor_in_topk=False))
            continue
        top_i, top_score = ranking[0]
        out.append(dict(
            base,
            top1_score=top_score,
            top1_id=chunks.ids[top_i],
            top1_cover=chunks.overlap(chunks.ids[top_i], span_s, span_e) / span_len,
            hit=any(chunks.overlap(chunks.ids[i], span_s, span_e) >= need
                    for i, _ in ranking),
            retrieved_chars=sum(len(chunks.texts[i]) for i, _ in ranking),
            anchor_in_top1=abstain.contains_word(chunks.texts[top_i], row["anchor"]),
            anchor_in_topk=any(abstain.contains_word(chunks.texts[i], row["anchor"])
                               for i, _ in ranking),
        ))
    return out


def evaluate_cell(corpus, rows, retriever, size, k, drop_ratio=0.0, idf=None):
    """Per-question records for one cell."""
    chunks, ranked = rank_all(corpus, rows, retriever, size, drop_ratio, kmax=k)
    return records_for_k(corpus, chunks, ranked, k, idf)


def calibrate(records):
    """Pre-registered threshold rule; returns (threshold, calibration id set)."""
    gold = [r for r in records if r["key"] == "gold"]
    ids = [r["id"] for r in gold]
    random.Random(config.SEED).shuffle(ids)
    calib = set(ids[:int(len(ids) * config.CALIB_FRACTION)])
    scores = sorted(r["top1_score"] for r in gold if r["id"] in calib)
    return abstain.threshold_for_gold(scores, config.TARGET_GOLD_ABSTAIN), calib


def summarize(records):
    """Decide both criteria and aggregate.  Returns a dict of plain numbers."""
    threshold, calib = calibrate(records)
    for r in records:
        r["a_abstain"] = bool(r["top1_id"] is None or r["top1_score"] < threshold)
        r["b_abstain"] = not r["anchor_in_top1"]
        r["calibration"] = r["id"] in calib

    report = {"threshold": threshold, "buckets": {}}
    for key in BUCKET_KEYS:
        sub = [r for r in records if r["key"] == key]
        if not sub:
            continue
        report["buckets"][key] = {
            "n": len(sub),
            "abstain_A": mean(r["a_abstain"] for r in sub),
            "abstain_B": mean(r["b_abstain"] for r in sub),
            "fabrication_accepted_B": 1.0 - mean(r["b_abstain"] for r in sub),
            "hit": mean(r["hit"] for r in sub),
            "mean_retrieved_chars": mean(r["retrieved_chars"] for r in sub),
            "anchor_beyond_top1": mean(r["anchor_in_topk"] and not r["anchor_in_top1"]
                                       for r in sub),
        }

    gold_report = [r for r in records if r["key"] == "gold" and not r["calibration"]]
    cross = [r for r in records if r["key"] == "relation-fake-cross"]
    intra = [r for r in records if r["key"] == "relation-fake-intra"]
    report["auc_A_cross_vs_gold"] = metrics.auc(
        [r["top1_score"] for r in gold_report], [r["top1_score"] for r in cross])
    if intra:
        report["auc_A_intra_vs_gold"] = metrics.auc(
            [r["top1_score"] for r in gold_report], [r["top1_score"] for r in intra])

    # B on the headline pair: how much more often the system declines a question
    # whose answer is not in the corpus than one whose answer is.
    gold_b = [1.0 if r["b_abstain"] else 0.0 for r in gold_report]
    cross_b = [1.0 if r["b_abstain"] else 0.0 for r in cross]
    if gold_b and cross_b:
        diff = mean(cross_b) - mean(gold_b)
        lo, hi = metrics.bootstrap_diff_ci(cross_b, gold_b, seed=config.SEED)
        report["abstain_B_gap_cross_minus_gold"] = {"diff": diff, "ci95": [lo, hi]}
    report["gold_abstain_A"] = mean(r["a_abstain"] for r in gold_report)
    report["gold_hit"] = mean(r["hit"] for r in gold_report)
    return report


def compare(records_a, records_b):
    """Paired comparison of two cells over the same questions (criterion B)."""
    by_id = {r["id"]: r for r in records_b}
    b = c = 0
    for r in records_a:
        other = by_id.get(r["id"])
        if other is None:
            continue
        if r["b_abstain"] and not other["b_abstain"]:
            b += 1
        elif other["b_abstain"] and not r["b_abstain"]:
            c += 1
    rate = lambda recs: mean(1.0 if r["b_abstain"] else 0.0 for r in recs)
    return {"only_a_abstains": b, "only_b_abstains": c,
            "delta_abstain_B": rate(records_b) - rate(records_a),
            "p_value": metrics.mcnemar(b, c)}


def write_results(path, payload):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(payload, fh, indent=1, sort_keys=True)
        fh.write("\n")
    return path
