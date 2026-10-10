"""The harness's own checks -- invariants, the two negative assertions, controls.

Three kinds of check, all of them able to fail:

* Invariants -- the exam is what it claims: hashes match, relation-level fakes
  respect the distance rule, reachability is decided without a retriever, and
  every cell is scored on the same questions.
* Negative assertions -- the design's two red flags: if the entity-level fakes are
  not declined by construction, or a relation-level fake fails the distance rule,
  the exam is broken and the run means nothing.
* Positive controls -- an oracle retriever and two degenerate answerers, so that
  every metric is shown moving to both ends instead of being assumed healthy.

`python bench/selftest.py` prints one line per check and exits non-zero if any of
them fails.
"""

from __future__ import annotations

import json
import hashlib
import os
import sys

import abstain
import chunking
import config
import corpus as C
import distance
import reachcheck
import run

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXAM = os.path.join(ROOT, "exam", "exam.jsonl")
MANIFEST = os.path.join(ROOT, "exam", "manifest.json")
SAMPLE = 200


class NullIndex:
    """A retriever that returns nothing at all."""

    def search(self, tokens, k):
        return []


def sha256_file(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def load_manifest(path=None):
    with open(path or MANIFEST, encoding="utf-8") as fh:
        return json.load(fh)


def sample_of(rows, n=SAMPLE):
    step = max(1, len(rows) // n)
    return rows[::step]


def build_context():
    corpus = C.Corpus()
    rows = run.load_exam(EXAM)
    ctx = {"corpus": corpus, "rows": rows, "manifest": load_manifest()}
    sample = sample_of(rows)
    ctx["sample"] = sample
    ctx["cell_800"] = run.evaluate_cell(corpus, sample, "bm25", 800, 5)
    ctx["cell_3200"] = run.evaluate_cell(corpus, sample, "bm25", 3200, 5)

    chunks = chunking.Chunks(corpus, config.MAX_CHUNK_LEN)
    oracle = run.rank_with(run.OracleIndex(chunks, rows), chunks, rows)
    ctx["oracle"] = run.records_for_k(corpus, chunks, oracle, 5)
    run.summarize(ctx["oracle"])          # attach both criteria's decisions
    null = run.rank_with(NullIndex(), chunks, rows)
    ctx["null"] = run.records_for_k(corpus, chunks, null, 5)
    run.summarize(ctx["null"])
    return ctx


# --- invariants -------------------------------------------------------------

def check_manifest_sha(ctx):
    stored = ctx["manifest"].get("exam_sha256")
    actual = sha256_file(ctx["_exam_path"])
    return actual == stored, "exam.jsonl sha256 %s" % (
        "matches the manifest" if actual == stored else "MISMATCH: %s vs %s" % (actual, stored))


def check_exam_shape(ctx):
    rows = ctx["rows"]
    ids = set(r["id"] for r in rows)
    bad = [r["id"] for r in rows
           if "MASK" not in r["query"] or not r["anchor"]
           or not r.get("answer_span") or not r.get("sentence_span")]
    per_arm = ctx["manifest"].get("counts")
    counts = {}
    for r in rows:
        key = run.bucket_key(r)
        counts[key] = counts.get(key, 0) + 1
    ok = len(ids) == len(rows) and not bad
    if per_arm:
        ok = ok and all(counts.get(k, 0) == v for k, v in per_arm.items())
    return ok, "%d rows, %d unique ids, %d malformed, buckets %s" % (
        len(rows), len(ids), len(bad), counts)


def check_corpus_source_clean(ctx):
    corpus = ctx["corpus"]
    # Assembled at runtime: the string itself must not appear anywhere in this
    # repository, including in the check that looks for it.
    needle = "Project" + " " + "Gutenberg"
    hits = corpus.text.count(needle)
    return hits == 0, "%d occurrences of an excluded distributor string" % hits


def check_entity_table(ctx):
    corpus = ctx["corpus"]
    bad_type = [e.id for e in corpus.entities if e.type not in ("person", "place")]
    numeric = [e.id for e in corpus.entities if e.forms and all(f.isdigit() for f in e.forms)]
    absent = [e.id for e in corpus.entities if not e.positions]
    ok = not bad_type and not numeric and not absent
    by_type = {}
    for e in corpus.entities:
        by_type[e.type] = by_type.get(e.type, 0) + 1
    return ok, "%d entities %s, %d bad types, %d numeric, %d with no occurrence" % (
        len(corpus.entities), by_type, len(bad_type), len(numeric), len(absent))


def check_distance_rule(ctx):
    failures, distances = distance.check(ctx["corpus"], ctx["rows"])
    return not failures, "%d relation-level rows checked, %d failures%s" % (
        len(distances), len(failures),
        "" if not failures else " (first: %s)" % (failures[0],))


def check_reachability_is_retriever_free(ctx):
    corpus = ctx["corpus"]
    spans = corpus.chunk(3200)
    start = spans[5][0] + 100
    span = (start, start + 2400)
    per, ok = reachcheck.reachable_everywhere(corpus, span)
    return (ok is False and per[800] is False and per[3200] is True), (
        "synthetic 2400-char span: per-size %s" % {str(k): v for k, v in per.items()})


def check_same_questions_per_cell(ctx):
    a = sorted(r["id"] for r in ctx["cell_800"])
    b = sorted(r["id"] for r in ctx["cell_3200"])
    return a == b, "%d vs %d questions, identical=%s" % (len(a), len(b), a == b)


def check_frozen_config(ctx):
    """Every parameter recorded at seal time must still be the live constant.

    This is what makes "thresholds fixed before the run" checkable: change one
    after the fact -- to make a number look better -- and `verify` goes red until
    the exam is re-sealed and re-scored.
    """
    import seal

    stored = ctx["manifest"].get("config") or {}
    live = seal.frozen_config()
    diffs = []
    for key, value in live.items():
        if key not in stored:
            diffs.append("%s missing from the manifest" % key)
        elif stored[key] != value:
            diffs.append("%s %r -> %r" % (key, stored[key], value))
    return not diffs, "%d frozen parameters%s" % (
        len(live), "" if not diffs else "; drifted: " + ", ".join(diffs))


def check_threshold_rule(ctx):
    threshold, calib = run.calibrate(ctx["cell_800"])
    gold = [r for r in ctx["cell_800"] if r["key"] == "gold" and r["id"] in calib]
    rate = run.mean(r["top1_score"] < threshold for r in gold)
    tol = 1.0 / max(1, len(gold)) + 1e-9
    return abs(rate - config.TARGET_GOLD_ABSTAIN) <= tol, (
        "gold abstain A on the calibration half %.3f (target %.2f, %d questions)"
        % (rate, config.TARGET_GOLD_ABSTAIN, len(gold)))


# --- negative assertions ----------------------------------------------------

def check_entity_fake_negative(ctx):
    """An invented anchor must not appear anywhere in the corpus."""
    corpus = ctx["corpus"]
    fakes = [r for r in ctx["rows"] if r["bucket"] == "entity-fake"]
    leaking = [r["id"] for r in fakes if corpus.contains(r["anchor"])]
    return not leaking, "%d entity-level fakes, %d of their anchors occur in the corpus" % (
        len(fakes), len(leaking))


def check_fakes_are_declined_by_construction(ctx):
    recs = [r for r in ctx["oracle"] if r["key"] == "entity-fake"]
    rate = run.mean(r["b_abstain"] for r in recs)
    return rate == 1.0, "criterion B abstain on entity-level fakes under the oracle: %.3f" % rate


# --- positive controls ------------------------------------------------------

def check_oracle_ceiling(ctx):
    gold = [r for r in ctx["oracle"] if r["key"] == "gold"]
    cross = [r for r in ctx["oracle"] if r["key"] == "relation-fake-cross"]
    hit = run.mean(r["hit"] for r in gold)
    abstain = run.mean(r["b_abstain"] for r in cross)
    return (hit == 1.0 and abstain == 1.0), (
        "oracle retriever: gold hit@5 %.3f, cross abstain B %.3f" % (hit, abstain))


def check_null_floor(ctx):
    hit = run.mean(r["hit"] for r in ctx["null"])
    summary = run.summarize(ctx["null"])
    abstain_a = summary["buckets"]["gold"]["abstain_A"]
    abstain_b = summary["buckets"]["gold"]["abstain_B"]
    return (hit == 0.0 and abstain_a == 1.0 and abstain_b == 1.0), (
        "empty retriever: hit %.3f, gold abstain A %.3f, gold abstain B %.3f"
        % (hit, abstain_a, abstain_b))


def check_answerer_extremes(ctx):
    question = {"anchor": "Rosings"}
    chunks = type("C", (), {"ids": ["0"], "texts": ["Rosings is a house."]})()
    always = abstain.check_interface(
        abstain.AlwaysAnswerAnswerer().answer(question, [(0, 1.0)], chunks))
    never = abstain.check_interface(
        abstain.NeverAnswerAnswerer().answer(question, [(0, 1.0)], chunks))
    rejected = False
    try:
        abstain.check_interface("I think the answer is Rosings")
    except TypeError:
        rejected = True
    ok = always["abstain"] is False and never["abstain"] is True and rejected
    return ok, "always-answer abstains=%s, never-answer abstains=%s, free text rejected=%s" % (
        always["abstain"], never["abstain"], rejected)


CHECKS = [
    ("manifest sha256", check_manifest_sha),
    ("exam shape", check_exam_shape),
    ("corpus source clean", check_corpus_source_clean),
    ("entity table", check_entity_table),
    ("distance rule", check_distance_rule),
    ("reachability is retriever-free", check_reachability_is_retriever_free),
    ("same questions per cell", check_same_questions_per_cell),
    ("threshold rule on the calibration half", check_threshold_rule),
    ("frozen parameters unchanged", check_frozen_config),
    ("negative: entity-level fakes never occur", check_entity_fake_negative),
    ("negative: fakes declined by construction", check_fakes_are_declined_by_construction),
    ("positive: oracle ceiling", check_oracle_ceiling),
    ("positive: empty retriever floor", check_null_floor),
    ("positive: answerer extremes", check_answerer_extremes),
]


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    exam_path = argv[0] if argv else EXAM
    ctx = build_context()
    ctx["_exam_path"] = exam_path
    failed = 0
    for name, fn in CHECKS:
        try:
            ok, detail = fn(ctx)
        except Exception as exc:  # a check that cannot run is a failed check
            ok, detail = False, "%s: %s" % (type(exc).__name__, exc)
        print("%-4s %-38s %s" % ("PASS" if ok else "FAIL", name, detail))
        failed += 0 if ok else 1
    print("\n%d checks, %d failed" % (len(CHECKS), failed))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
