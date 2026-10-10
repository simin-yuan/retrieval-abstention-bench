"""Two abstention probes, expressed as an answerer interface.

Criterion A -- score threshold.  Decline when the best score is below a
threshold.  The threshold is not chosen by taste: it is read off the
calibration half of the gold questions so that the intended gold abstain rate is
met exactly (`config.TARGET_GOLD_ABSTAIN`), and the remaining half carries every
reported number.

Criterion B -- the evidence must contain the anchor.  Decline when the chunk the
system would cite does not contain the entity the question is about.  This is
the probe a lexical retriever cannot satisfy by construction: the check is made
against the evidence, not against the query.

Both are implementations of the same tiny interface, so a real system can be
plugged in without touching the harness:

    answer(question, ranked, chunks) -> {"abstain": bool, "cited_chunk_id": str|None}

Free text is never inspected.  Without an LLM there is no way to tell a
fabrication from an answer, and that is the point of the design.
"""

from __future__ import annotations

import re

import metrics


def contains_word(haystack, needle):
    """Word-bounded, case-insensitive search for one surface form."""
    if not needle:
        return False
    return bool(re.search(r"(?<![A-Za-z])" + re.escape(needle) + r"(?![A-Za-z])",
                          haystack, re.I))


def threshold_for_gold(gold_scores, target):
    """Pre-registered rule: the threshold that leaves `target` of gold below it."""
    return metrics.quantile(sorted(gold_scores), target)


class Answerer:
    """Reference implementation of the answerer interface."""

    name = "abstract"

    def answer(self, question, ranked, chunks):
        raise NotImplementedError

    def __repr__(self):
        return "<Answerer %s>" % self.name


class ScoreThresholdAnswerer(Answerer):
    name = "score-threshold"

    def __init__(self, threshold):
        self.threshold = threshold

    def answer(self, question, ranked, chunks):
        if not ranked:
            return {"abstain": True, "cited_chunk_id": None}
        idx, score = ranked[0]
        if score < self.threshold:
            return {"abstain": True, "cited_chunk_id": None}
        return {"abstain": False, "cited_chunk_id": chunks.ids[idx]}


class AnchorEvidenceAnswerer(Answerer):
    name = "anchor-in-evidence"

    def answer(self, question, ranked, chunks):
        if not ranked:
            return {"abstain": True, "cited_chunk_id": None}
        idx = ranked[0][0]
        if not contains_word(chunks.texts[idx], question["anchor"]):
            return {"abstain": True, "cited_chunk_id": None}
        return {"abstain": False, "cited_chunk_id": chunks.ids[idx]}


class AlwaysAnswerAnswerer(Answerer):
    """Positive control: a system that never declines.  If the harness reports
    this as anything other than full fabrication acceptance, the probes are stuck."""

    name = "always-answer"

    def answer(self, question, ranked, chunks):
        if not ranked:
            return {"abstain": False, "cited_chunk_id": None}
        return {"abstain": False, "cited_chunk_id": chunks.ids[ranked[0][0]]}


class NeverAnswerAnswerer(Answerer):
    """Positive control: a system that always declines.  If the harness reports
    this as anything but full abstention, the probes cannot see caution."""

    name = "never-answer"

    def answer(self, question, ranked, chunks):
        return {"abstain": True, "cited_chunk_id": None}


def check_interface(result):
    """A plugin result must be structured; anything else is a harness error."""
    if not isinstance(result, dict):
        raise TypeError("answerer must return a dict, got %r" % type(result))
    if not isinstance(result.get("abstain"), bool):
        raise TypeError("answerer must return a boolean 'abstain'")
    cid = result.get("cited_chunk_id")
    if cid is not None and not isinstance(cid, str):
        raise TypeError("'cited_chunk_id' must be a string or None")
    return result
