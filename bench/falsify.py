"""Falsification: break the harness on purpose and require it to notice.

Every check in `selftest` is only worth something if it can fail.  Each case
below mutates an input -- a byte of the frozen exam, a leaked anchor, a pair of
entities that are too close, a shorter arm, a target moved after the fact, a
worse oracle -- and passes only when the guarding check reports FAIL.  A case
where the check still reports PASS means the check is decorative.

`python bench/falsify.py` prints one line per case and exits non-zero if any
breakage went unnoticed.
"""

from __future__ import annotations

import copy
import os
import sys
import tempfile

import config
import distance
import selftest as S


def _fails(check, ctx):
    """Run a check on a mutated context; True when it catches the breakage."""
    try:
        ok, detail = check(ctx)
    except Exception as exc:
        return True, "%s: %s" % (type(exc).__name__, exc)
    return (not ok), detail


def case_manifest_byte(ctx):
    """One flipped byte in the frozen exam must break the hash check."""
    path = os.path.join(tempfile.mkdtemp(prefix="falsify-"), "exam.jsonl")
    with open(S.EXAM, "rb") as fh:
        data = fh.read()
    with open(path, "wb") as fh:
        fh.write(data[:1000] + b" " + data[1001:])
    mutated = dict(ctx, _exam_path=path)
    return _fails(S.check_manifest_sha, mutated)


def case_entity_fake_leaks(ctx):
    """An entity-level fake whose anchor really occurs must be caught."""
    rows = copy.deepcopy(ctx["rows"])
    leaked = None
    for row in rows:
        if row["bucket"] == "entity-fake":
            row["anchor"] = "Rosings"
            leaked = row["id"]
            break
    mutated = dict(ctx, rows=rows)
    caught, detail = _fails(S.check_entity_fake_negative, mutated)
    return caught, "%s (%s)" % (detail, leaked)


def case_close_pair(ctx):
    """A relation-level row whose two entities sit inside one chunk must be caught."""
    corpus = ctx["corpus"]
    pair = None
    for a in corpus.entities:
        for b in corpus.entities:
            if a.id >= b.id or a.book != b.book:
                continue
            d = corpus.min_distance(a, b)
            if d is not None and 0 < d <= config.MAX_CHUNK_LEN:
                pair = (a, b)
                break
        if pair:
            break
    rows = copy.deepcopy(ctx["rows"])
    for row in rows:
        if row["bucket"] == "relation-fake" and row["tier"] == "cross":
            row["anchor_entity"], row["answer_entity"] = pair[0].id, pair[1].id
            row["tier"] = "intra"
            break
    mutated = dict(ctx, rows=rows)
    caught, detail = _fails(S.check_distance_rule, mutated)
    return caught, "pair %s/%s: %s" % (pair[0].id, pair[1].id, detail)


def case_shorter_arm(ctx):
    """An arm that quietly lost questions must be caught."""
    mutated = dict(ctx, cell_3200=ctx["cell_3200"][5:])
    return _fails(S.check_same_questions_per_cell, mutated)


def case_config_moved(ctx):
    """A parameter changed after sealing must be caught by the frozen-parameter check."""
    original = config.HIT_OVERLAP
    try:
        config.HIT_OVERLAP = 0.0
        caught, detail = _fails(S.check_frozen_config, ctx)
    finally:
        config.HIT_OVERLAP = original
    return caught, detail


def case_worse_oracle(ctx):
    """An oracle that misses the answer chunk must stop passing the ceiling."""
    records = copy.deepcopy(ctx["oracle"])
    for row in records:
        if row["key"] == "gold":
            row["hit"] = False
            break
    mutated = dict(ctx, oracle=records)
    return _fails(S.check_oracle_ceiling, mutated)


def case_fake_answered(ctx):
    """If a fake were answered, the construction check must report it."""
    records = copy.deepcopy(ctx["oracle"])
    for row in records:
        if row["key"] == "entity-fake":
            row["b_abstain"] = False
            break
    mutated = dict(ctx, oracle=records)
    return _fails(S.check_fakes_are_declined_by_construction, mutated)


CASES = [
    ("manifest byte flip", case_manifest_byte),
    ("entity-level anchor leaks", case_entity_fake_leaks),
    ("entities too close", case_close_pair),
    ("shorter arm", case_shorter_arm),
    ("parameter moved after sealing", case_config_moved),
    ("oracle misses the answer", case_worse_oracle),
    ("fake answered", case_fake_answered),
]


def main(argv=None):
    ctx = S.build_context()
    ctx["_exam_path"] = S.EXAM
    failed = 0
    for name, fn in CASES:
        caught, detail = fn(ctx)
        print("%-4s %-28s %s" % ("CAUGHT" if caught else "MISSED", name, detail))
        failed += 0 if caught else 1
    print("\n%d cases, %d breakages unnoticed" % (len(CASES), failed))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
