"""Question generation.

The three buckets share one underlying sentence, so they differ in exactly one
slot -- the anchor.  Every question is: one visible entity (the anchor), the
context, and one masked position (the answer).

  gold              anchor is real and sits in the same sentence as the answer
  entity-fake       anchor is replaced by an invented name that appears nowhere
  relation-fake     anchor is replaced by a real entity that is far from the
                    answer; tier "intra" = same book, "cross" = another book

Relation-fakes are only accepted when the replacement entity sits further from
the answer than the largest candidate chunk, so no chunking of the corpus can
put the two in the same evidence chunk.
"""

from __future__ import annotations

import random
import re

import corpus as C

# Invented names used for entity-level fakes.  Every candidate is checked
# against the corpus before use; an invented name that occurs is a bug, not a
# judgement call.
INVENTED = {
    "person": ["Mr. Ellsworth", "Miss Danvers", "Lady Ashby", "Mrs. Whitfield",
               "Sir Roland Crewe", "Miss Pemberton", "Mr. Halstead"],
    "place": ["Ashby Park", "Thornfield", "Winstead", "Ravensworth",
              "Bellhaven", "Marsden", "Coldbrook"],
}


class Question:
    __slots__ = ("bucket", "tier", "query", "answer_start", "answer_end",
                 "answer_entity", "anchor", "anchor_entity", "book",
                 "sentence_span")

    def __init__(self, bucket, tier, query, answer_span, answer_entity,
                 anchor, anchor_entity, book, sentence_span):
        self.bucket = bucket
        self.tier = tier                  # None / "intra" / "cross"
        self.query = query
        self.answer_start, self.answer_end = answer_span
        self.answer_entity = answer_entity.id
        self.anchor = anchor              # the anchor STRING as it appears
        self.anchor_entity = anchor_entity.id if anchor_entity else None
        self.book = book
        self.sentence_span = sentence_span

    def __repr__(self):
        return "<%s%s %s/%s>" % (self.bucket, "/" + self.tier if self.tier else "",
                                 self.anchor, self.answer_entity)


def invented_for(corpus, kind, rng):
    """An invented name of the right type that is absent from the corpus."""
    pool = [n for n in INVENTED[kind] if not corpus.contains(n)]
    if not pool:
        raise SystemExit("no unused invented name left for type %r" % kind)
    return rng.choice(pool)


def make_query(corpus, start, end, answer_pos, answer_len, anchor_pos,
               anchor_len, anchor_replacement):
    """Sentence text with the answer masked and, optionally, the anchor swapped."""
    s = corpus.text[start:end]
    edits = [(answer_pos - start, answer_pos - start + answer_len, C.MASK)]
    if anchor_replacement is not None and anchor_pos is not None:
        edits.append((anchor_pos - start, anchor_pos - start + anchor_len,
                      anchor_replacement))
    for a, b, rep in sorted(edits, key=lambda e: -e[0]):
        s = s[:a] + rep + s[b:]
    return s


def gold_candidates(corpus):
    """(sentence_span, anchor, anchor_pos, answer, answer_pos) with both in one sentence."""
    out = []
    for start, end, ents in corpus.sentences_with_entities():
        for anchor in ents:
            for answer in ents:
                if anchor is answer or anchor.book != answer.book:
                    continue
                a_pos = corpus.occurrences_inside(anchor, start, end)
                ans_pos = corpus.occurrences_inside(answer, start, end)
                if not a_pos or not ans_pos:
                    continue
                out.append(((start, end), anchor, a_pos[0], answer, ans_pos[0]))
    return out


def build(corpus, max_chunk_len, rng=None, limit=None, intra_cap=10, cross_cap=3):
    """Build the three buckets from the corpus.  Returns a dict of lists.

    The caps bound how many relation-fakes one gold sentence may contribute per
    tier.  Cross-book candidates are plentiful -- most entities live in another
    book -- so that tier is capped tighter than the scarce same-book tier.
    """
    rng = rng or random.Random(0)
    cands = gold_candidates(corpus)
    rng.shuffle(cands)
    if limit:
        cands = cands[:limit]

    buckets = {"gold": [], "entity-fake": [], "relation-fake-intra": [],
               "relation-fake-cross": []}
    by_type = {}
    for ent in corpus.entities:
        by_type.setdefault(ent.type, []).append(ent)
    for (start, end), anchor, a_pos, answer, ans_pos in cands:
        ans_form = corpus.form_at(answer, ans_pos)
        a_form = corpus.form_at(anchor, a_pos)
        if not ans_form or not a_form:
            continue
        answer_span = (ans_pos, ans_pos + len(ans_form))

        buckets["gold"].append(Question(
            "gold", None,
            make_query(corpus, start, end, ans_pos, len(ans_form), a_pos, len(a_form), None),
            answer_span, answer, a_form, anchor, anchor.book, (start, end)))

        rep = invented_for(corpus, anchor.type, rng)
        buckets["entity-fake"].append(Question(
            "entity-fake", None,
            make_query(corpus, start, end, ans_pos, len(ans_form), a_pos, len(a_form), rep),
            answer_span, answer, rep, None, anchor.book, (start, end)))

        seen = set()
        intra_n = cross_n = 0
        for cand in by_type[anchor.type]:
            if cand is anchor or cand is answer or not cand.positions:
                continue
            if cand.occurrences_in(start, end):
                continue
            dist = corpus.min_distance(cand, answer)
            if dist is None or dist <= max_chunk_len:
                continue
            tier = "intra" if cand.book == answer.book else "cross"
            if tier == "intra":
                if intra_n >= intra_cap:
                    continue
                intra_n += 1
            else:
                if cross_n >= cross_cap:
                    continue
                cross_n += 1
            key = (tier, cand.id)
            if key in seen:
                continue
            seen.add(key)
            buckets["relation-fake-" + tier].append(Question(
                "relation-fake", tier,
                make_query(corpus, start, end, ans_pos, len(ans_form), a_pos,
                           len(a_form), cand.forms[0]),
                answer_span, answer, cand.forms[0], cand, anchor.book, (start, end)))
    return buckets


_WORD = re.compile(r"[A-Za-z0-9']+")


def drop_context(query, anchor, drop_ratio, rng):
    """Remove a share of the context words -- never the anchor, never the mask.

    Words are dropped uniformly at random, rare ones included: protecting the
    rare words would quietly make the questions easier than they look.  What
    survives is measured afterwards as the IDF-weighted overlap in `leakcheck`.
    """
    anchor_words = set(_WORD.findall(anchor or ""))
    mask_start = query.find(C.MASK)
    mask_end = mask_start + len(C.MASK)
    droppable = [m.span() for m in _WORD.finditer(query)
                 if not (mask_start <= m.start() < mask_end)
                 and m.group(0) not in anchor_words]
    n_drop = int(round(drop_ratio * len(droppable)))
    if n_drop <= 0:
        return query
    for a, b in sorted(rng.sample(droppable, n_drop), reverse=True):
        query = query[:a] + query[b:]
    return query


def pair_by_band(corpus, buckets, rng=None):
    """Match the anchor-frequency composition of gold and of each fake tier.

    A rare anchor scores differently from a common one whatever the retriever
    does, so a bucket that leans on rare anchors would show a difference that
    has nothing to do with admitting ignorance.  Gold is paired separately
    against each tier -- the tiers are reported separately, and the same-book
    tier is far smaller than the cross-book one.
    """
    rng = rng or random.Random(0)

    def by_band(name):
        per = {}
        for q in buckets[name]:
            ent = corpus.by_id.get(q.anchor_entity)
            if ent is not None:
                per.setdefault(ent.band(), []).append(q)
        return per

    gold_by_band = by_band("gold")
    out = {}
    for tier in ("intra", "cross"):
        fake_by_band = by_band("relation-fake-" + tier)
        gold, fake, per_band = [], [], {}
        for band in sorted(set(gold_by_band) | set(fake_by_band)):
            gl = list(gold_by_band.get(band, ()))
            fl = list(fake_by_band.get(band, ()))
            rng.shuffle(gl)
            rng.shuffle(fl)
            n = min(len(gl), len(fl))
            gold.extend(gl[:n])
            fake.extend(fl[:n])
            per_band[band] = n
        out[tier] = {"gold": gold, "fake": fake, "per_band": per_band}
    return out


def validate(corpus, buckets, max_chunk_len):
    """The two negative assertions.  Any violation is a generator bug."""
    problems = []
    for q in buckets["gold"] + buckets["entity-fake"] + \
            buckets["relation-fake-intra"] + buckets["relation-fake-cross"]:
        s, e = q.sentence_span
        if not (s <= q.answer_start < q.answer_end <= e):
            problems.append(("answer span outside sentence", repr(q)))
        if C.MASK not in q.query:
            problems.append(("no mask in query", repr(q)))
        if corpus.form_at(corpus.by_id[q.answer_entity], q.answer_start) is None:
            problems.append(("answer span does not sit on a real form", repr(q)))
    # entity-level fakes: an invented anchor that occurs in the corpus would
    # make the question answerable, so every one must be absent.
    for q in buckets["entity-fake"]:
        if corpus.contains(q.anchor):
            problems.append(("entity-fake anchor occurs in corpus", repr(q)))
    # relation-level fakes: every one must clear the distance check.
    for name in ("relation-fake-intra", "relation-fake-cross"):
        for q in buckets[name]:
            d = corpus.min_distance(corpus.by_id[q.anchor_entity],
                                    corpus.by_id[q.answer_entity])
            if d <= max_chunk_len:
                problems.append(("relation-fake too close (%d <= %d)" % (d, max_chunk_len),
                                 repr(q)))
            tier = "intra" if corpus.by_id[q.anchor_entity].book == \
                corpus.by_id[q.answer_entity].book else "cross"
            if tier != q.tier:
                problems.append(("relation-fake tier mismatch", repr(q)))
    return problems


def main():
    max_chunk_len = 3200          # keep in step with seal.CHUNK_SIZES
    c = C.Corpus()
    print("corpus: %d books, %d chapters, %d chars, %d entities"
          % (len(c.order), len(c.chapters), len(c.text), len(c.entities)))
    buckets = build(c, max_chunk_len)
    print("\nraw buckets")
    for k in ("gold", "entity-fake", "relation-fake-intra", "relation-fake-cross"):
        print("   %-22s %6d" % (k, len(buckets[k])))
    paired = pair_by_band(c, buckets)
    print("\nfrequency-matched pairs (gold vs each tier, equal counts per band)")
    for tier in ("intra", "cross"):
        print("   %-6s gold %5d  fake %5d  per band %s"
              % (tier, len(paired[tier]["gold"]), len(paired[tier]["fake"]),
                 paired[tier]["per_band"]))
    problems = validate(c, buckets, max_chunk_len)
    print("\nnegative assertions: %s" % ("PASS" if not problems else "FAIL"))
    for p in problems[:10]:
        print("   ", p)
    print("\nexample gold query:")
    print("   ", buckets["gold"][0].query[:200].replace("\n", " "))
    print("example relation-fake (cross) query:")
    print("   ", buckets["relation-fake-cross"][0].query[:200].replace("\n", " "))


if __name__ == "__main__":
    main()
