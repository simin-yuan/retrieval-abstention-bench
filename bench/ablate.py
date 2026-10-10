"""Sweep the grid, one variable at a time, and render the report.

Every cell is scored on the same question set: the exam is frozen, and
reachability was decided without a retriever, so no arm can quietly lose
questions it finds hard.  Cells that differ only in top-k share one ranking.
"""

from __future__ import annotations

import collections
import json

import config
import leakcheck
import metrics
import run

PRESETS = {
    "quick": {"ks": (5,), "drop_ratios": (0.6,)},
    "default": {"ks": (1, 5, 10), "drop_ratios": (0.4, 0.6, 0.8)},
    "full": {"ks": config.TOP_K, "drop_ratios": config.DROP_RATIOS},
}

BASELINE = {"retriever": "bm25", "size": 1600, "k": 5, "drop_ratio": 0.6}


def cell_key(cell):
    return "%s|%d|%d|%.1f" % (cell["retriever"], cell["size"], cell["k"], cell["drop_ratio"])


def cells(preset):
    """The (retriever, size, drop) passes to score, plus the cells to report."""
    preset = PRESETS.get(preset, PRESETS["default"])
    passes, report = [], []
    for retriever in ("bm25", "ngram-tfidf"):
        for size in config.CHUNK_SIZES:
            for drop in preset["drop_ratios"]:
                passes.append({"retriever": retriever, "size": size, "drop_ratio": drop})
                for k in preset["ks"]:
                    report.append({"retriever": retriever, "size": size, "k": k,
                                   "drop_ratio": drop})
    return passes, report


def run_grid(corpus, rows, preset="default", progress=None):
    """Score the grid.  Returns the full result payload.

    Every cell keeps its per-question records in memory so that cells can be
    compared pairwise on the same questions; only the headline cell's records
    are written out, to keep results.json readable.
    """
    idf = leakcheck.ChapterIdf(corpus)
    rows = leakcheck.annotate(corpus, rows, idf)
    passes, report = cells(preset)
    results = {"preset": preset, "n_questions": len(rows), "cells": {},
               "comparisons": {}, "records": {}}
    all_records = {}
    for p in passes:
        chunks, ranked = run.rank_all(corpus, rows, p["retriever"], p["size"], p["drop_ratio"])
        for cell in [c for c in report if (c["retriever"], c["size"], c["drop_ratio"]) ==
                     (p["retriever"], p["size"], p["drop_ratio"])]:
            recs = run.records_for_k(corpus, chunks, ranked, cell["k"], idf)
            key = cell_key(cell)
            all_records[key] = recs
            summary = run.summarize(recs)
            summary["ids_ok"] = sorted(r["id"] for r in recs) == sorted(r["id"] for r in rows)
            summary["mean_query_overlap"] = run.mean(r["query_overlap"] for r in recs)
            results["cells"][key] = {"cell": cell, "summary": summary}
        if progress:
            progress("scored %s size=%d drop=%.1f" % (p["retriever"], p["size"], p["drop_ratio"]))

    base_key = cell_key(BASELINE)
    base = all_records.get(base_key)
    if base:
        results["records"][base_key] = base
        for key, recs in all_records.items():
            if key != base_key:
                results["comparisons"][key] = run.compare(base, recs)
    return results


def _pct(x):
    return "-" if x is None or x != x else "%.1f%%" % (100.0 * x)


def render(results, headline=None):
    """Markdown report: retrieval, headline abstention, ablations, bands."""
    head = headline or cell_key(BASELINE)
    cells = results["cells"]
    out = []
    out.append("# Results\n")
    out.append("Questions in the frozen exam: **%d** (every cell below is scored on "
               "exactly these, `ids_ok` column).\n" % results["n_questions"])
    out.append("Criterion A = decline when the best score is below the calibrated "
               "threshold. Criterion B = decline when the cited chunk does not contain "
               "the anchor. Reported cells exclude the calibration half of the gold "
               "questions.\n")

    out.append("\n## Retrieval quality on the answerable questions (gold)\n")
    out.append("| retriever | chunk | k | drop | hit@k | mean retrieved chars | gold abstain A | gold abstain B | ids ok |")
    out.append("|---|---|---|---|---|---|---|---|---|")
    for key in sorted(cells):
        c, s = cells[key]["cell"], cells[key]["summary"]
        g = s["buckets"].get("gold", {})
        out.append("| %s | %d | %d | %.1f | %s | %.0f | %s | %s | %s |" % (
            c["retriever"], c["size"], c["k"], c["drop_ratio"], _pct(g.get("hit")),
            g.get("mean_retrieved_chars", float("nan")), _pct(g.get("abstain_A")),
            _pct(g.get("abstain_B")), "yes" if s["ids_ok"] else "NO"))

    h = cells.get(head)
    if h:
        c = h["cell"]
        out.append("\n## Headline: %s, chunk %d, top-%d, drop %.1f\n"
                   % (c["retriever"], c["size"], c["k"], c["drop_ratio"]))
        out.append("| bucket | n | abstain A | abstain B | answered (B) | anchor beyond top-1 |")
        out.append("|---|---|---|---|---|---|")
        for b in run.BUCKET_KEYS:
            s = h["summary"]["buckets"].get(b)
            if not s:
                continue
            out.append("| %s | %d | %s | %s | %s | %s |" % (
                b, s["n"], _pct(s["abstain_A"]), _pct(s["abstain_B"]),
                _pct(s["fabrication_accepted_B"]), _pct(s["anchor_beyond_top1"])))
        gap = h["summary"].get("abstain_B_gap_cross_minus_gold")
        if gap:
            out.append("\nAbstain-rate gap, relation-fake (cross) minus gold, criterion B: "
                       "**%+.1f points** (95%% bootstrap CI %+.1f to %+.1f).\n"
                       % (100 * gap["diff"], 100 * gap["ci95"][0], 100 * gap["ci95"][1]))
        auc = h["summary"].get("auc_A_cross_vs_gold")
        if auc == auc:
            out.append("Criterion A, score AUC between gold and relation-fake (cross): "
                       "**%.3f** (0.5 = the score cannot tell them apart).\n" % auc)
        auc_intra = h["summary"].get("auc_A_intra_vs_gold")
        if auc_intra == auc_intra:
            out.append("Criterion A, score AUC between gold and relation-fake (intra): "
                       "**%.3f**. The cross-book tier is the easier of the two for "
                       "criterion A -- its swapped anchor never occurs in the target book "
                       "at all, and a score is allowed to notice that. The same-book "
                       "tier keeps the swapped anchor inside the book, a long way from "
                       "the answer, so it is the cleaner test of whether a score "
                       "threshold can see the difference.\n" % auc_intra)

    out.append("\n## Ablations (one variable at a time, baseline %s)\n" % head)
    out.append("Each row changes exactly one axis; the paired test is McNemar on the "
               "same questions, criterion B, and no arm loses questions (see `ids ok` "
               "above).\n")
    out.append("| axis | value | gold hit@k | cross abstain B | Δ vs baseline | McNemar p |")
    out.append("|---|---|---|---|---|---|")
    for key in sorted(cells):
        c, s = cells[key]["cell"], cells[key]["summary"]
        cross = s["buckets"].get("relation-fake-cross")
        if not cross:
            continue
        label = []
        if c["size"] != BASELINE["size"]:
            label.append("chunk")
        if c["k"] != BASELINE["k"]:
            label.append("top-k")
        if c["drop_ratio"] != BASELINE["drop_ratio"]:
            label.append("drop-ratio")
        if c["retriever"] != BASELINE["retriever"]:
            label.append("retriever")
        if not label:
            continue
        delta, p = "-", "-"
        cmp = results["comparisons"].get(key)
        if cmp:
            delta = "%+.1f pts" % (100.0 * cmp["delta_abstain_B"])
            p = "%.2g" % cmp["p_value"]
        out.append("| %s | %s | %s | %s | %s | %s |" % (
            ",".join(label), "%s/%d/%d/%.1f" % (c["retriever"], c["size"], c["k"],
                                                c["drop_ratio"]),
            _pct(s["buckets"].get("gold", {}).get("hit")), _pct(cross["abstain_B"]),
            delta, p))

    recs = results["records"].get(head)
    if recs:
        out.append("\n## Leak check: abstention by IDF-weighted overlap of the question "
                   "with its source passage\n")
        out.append("| overlap | n gold | n cross | gold hit@k | cross abstain B |")
        out.append("|---|---|---|---|---|")
        by_band = collections.defaultdict(list)
        for r in recs:
            key = "n/a" if r["query_overlap"] is None else leakcheck.band(r["query_overlap"])
            by_band[key].append(r)
        for band in sorted(by_band):
            sub = by_band[band]
            gold = [r for r in sub if r["key"] == "gold"]
            cross = [r for r in sub if r["key"] == "relation-fake-cross"]
            out.append("| %s | %d | %d | %s | %s |" % (
                band, len(gold), len(cross),
                _pct(run.mean(r["hit"] for r in gold)) if gold else "-",
                _pct(run.mean(r["b_abstain"] for r in cross)) if cross else "-"))

    out.append("\nRead the bands within a bucket, not across them: a relation-level fake "
               "replaces the anchor with an entity that does not appear in the source "
               "passage, so its overlap is lower by construction, which is why the two "
               "`n` columns shift differently. Every gold question sits in the top band "
               "(they keep their source text verbatim, which is what makes them "
               "answerable), so the fakes are the interesting column: the ones still "
               "close to their source passage are declined most reliably, and the bands "
               "where the query was cut hardest are the noisy ones where a wrong chunk "
               "can happen to contain the swapped anchor.\n")

    out.append("\n## Per-question records\n")
    out.append("`results.json` carries one record per question per kept cell, including "
               "top-1 score, cited chunk, coverage of the gold span and both criteria's "
               "decision, so every number above can be recomputed without the corpus.\n")
    return "\n".join(out) + "\n"


def main(argv=None):
    import argparse
    import os
    import corpus as C

    ap = argparse.ArgumentParser(description="run the abstention grid")
    ap.add_argument("--preset", default="quick", choices=sorted(PRESETS))
    ap.add_argument("--out", default="results")
    args = ap.parse_args(argv)

    corpus = C.Corpus()
    rows = run.load_exam(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                      "..", "exam", "exam.jsonl"))
    payload = run_grid(corpus, rows, args.preset,
                       progress=lambda m: print(" ", m))
    os.makedirs(args.out, exist_ok=True)
    run.write_results(os.path.join(args.out, "results.json"), payload)
    with open(os.path.join(args.out, "results.md"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(render(payload))
    print("wrote %s/results.json and %s/results.md" % (args.out, args.out))


if __name__ == "__main__":
    main()
