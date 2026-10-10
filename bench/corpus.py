"""Load the frozen corpus.

Nothing in here is stored twice: `entities.json` holds names only, and every
occurrence position is recomputed from the book text at load time.  Matching is
scoped to the entity's own book, which is what makes a bare first name
unambiguous (see corpus/AMBIGUOUS.md).
"""

from __future__ import annotations

import bisect
import json
import os
import re

MASK = "[MASK]"


def repo_root():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def form_pattern(form):
    """Word-bounded, case-sensitive match for one surface form."""
    return re.compile(r"(?<![A-Za-z])" + re.escape(form) + r"(?![A-Za-z])")


class Entity:
    __slots__ = ("id", "type", "book", "forms", "positions")

    def __init__(self, rec, positions):
        self.id = rec["id"]
        self.type = rec["type"]
        self.book = rec["book"]
        self.forms = list(rec["forms"])
        self.positions = positions          # sorted, absolute in corpus text

    @property
    def n(self):
        return len(self.positions)

    def band(self):
        """Frequency band, used to pair gold and fake questions."""
        n = self.n
        for lo, name in ((500, "A"), (200, "B"), (100, "C"), (50, "D")):
            if n >= lo:
                return name
        return "E"

    def occurrences_in(self, start, end):
        i = bisect.bisect_left(self.positions, start)
        out = []
        while i < len(self.positions) and self.positions[i] < end:
            out.append(self.positions[i])
            i += 1
        return out

    def __repr__(self):
        return "<%s %s n=%d>" % (self.type, self.id, self.n)


class Corpus:
    def __init__(self, root=None):
        self.root = root or repo_root()
        cdir = os.path.join(self.root, "corpus")
        with open(os.path.join(cdir, "manifest.json"), encoding="utf-8") as fh:
            self.manifest = json.load(fh)
        self.order = list(self.manifest["order"])

        # A book file is its text plus one trailing newline; the manifest
        # records the length without it, so a truncation is caught here.
        self.texts, self.book_span, off = {}, {}, 0
        for slug in self.order:
            with open(os.path.join(cdir, "books", slug + ".txt"), encoding="utf-8") as fh:
                raw = fh.read()
            text = raw[:-1] if raw.endswith("\n") else raw
            want = self.manifest["books"][slug]["chars"]
            if len(text) != want:
                raise SystemExit("corpus drift in %s: %d != %d" % (slug, len(text), want))
            self.texts[slug] = text
            self.book_span[slug] = (off, off + len(text))
            off += len(text) + 2
        self.text = "\n\n".join(self.texts[s] for s in self.order)

        with open(os.path.join(cdir, "entities.json"), encoding="utf-8") as fh:
            recs = json.load(fh)["entities"]
        self.entities, self.by_id = [], {}
        for rec in recs:
            base = self.book_span[rec["book"]][0]
            positions = []
            for form in rec["forms"]:
                for m in form_pattern(form).finditer(self.texts[rec["book"]]):
                    positions.append(base + m.start())
            ent = Entity(rec, sorted(positions))
            self.entities.append(ent)
            self.by_id[ent.id] = ent
        self.chapters = list(self.manifest["chapters"])
        self._dists = None
        self._contains_cache = {}

    # ---- geometry ---------------------------------------------------------
    def book_of(self, pos):
        for slug in self.order:
            a, b = self.book_span[slug]
            if a <= pos < b:
                return slug
        return None

    def min_distance(self, a, b):
        """Smallest gap between any occurrence of a and any occurrence of b."""
        if a is b:
            return 0
        return self._distances()[(a.id, b.id)]

    def _min_distance(self, a, b):
        pa, pb, i, j, best = a.positions, b.positions, 0, 0, None
        while i < len(pa) and j < len(pb):
            d = abs(pa[i] - pb[j])
            if best is None or d < best:
                best = d
            if pa[i] < pb[j]:
                i += 1
            else:
                j += 1
        return best

    def _distances(self):
        """Pairwise minimum distances, computed once and cached."""
        if self._dists is None:
            d = {}
            for i, a in enumerate(self.entities):
                for b in self.entities[i + 1:]:
                    v = self._min_distance(a, b)
                    d[(a.id, b.id)] = v
                    d[(b.id, a.id)] = v
            self._dists = d
        return self._dists

    def sentences(self, lo=20, hi=400):
        """Sentence-ish spans.

        Split on terminal punctuation -- but not after an abbreviation such as
        'Mr.', so that a name like 'Mrs. Bennet' is never cut in half.
        """
        split = re.compile(r"(?<=[.!?])(?<!\bMr\.)(?<!\bMrs\.)(?<!\bMiss\.)"
                           r"(?<!\bDr\.)(?<!\bSt\.)(?<!\bSir\.)(?<!\bEsq\.)"
                           r"[\"'”’)\]]*\s+")
        spans, prev = [], 0
        for m in split.finditer(self.text):
            spans.append((prev, m.start()))
            prev = m.end()
        spans.append((prev, len(self.text)))
        return [(s, e) for s, e in spans if lo <= e - s <= hi]

    def entities_within(self, start, end):
        """Entities having at least one occurrence inside [start, end)."""
        out = []
        for ent in self.entities:
            if ent.occurrences_in(start, end):
                out.append(ent)
        return out

    def sentences_with_entities(self):
        out = []
        for start, end in self.sentences():
            hits = self.entities_within(start, end)
            if len(hits) >= 2:
                out.append((start, end, hits))
        return out

    def occurrences_inside(self, ent, start, end):
        """Occurrences of `ent` whose whole surface form lies inside [start, end)."""
        out = []
        for p in ent.occurrences_in(start, end):
            form = self.form_at(ent, p)
            if form and p + len(form) <= end:
                out.append(p)
        return out

    def contains(self, needle):
        """Case-insensitive word-level search, used to vet invented anchors.

        Cached: a scan of the whole corpus is not cheap, and the same handful of
        candidate names is checked on every build.
        """
        key = needle.lower()
        if key not in self._contains_cache:
            self._contains_cache[key] = bool(
                re.search(r"(?<![A-Za-z])" + re.escape(needle) + r"(?![A-Za-z])",
                          self.text, re.I))
        return self._contains_cache[key]

    def form_at(self, ent, pos):
        """The surface form of `ent` matching at exactly `pos`, or None."""
        for form in ent.forms:
            if form_pattern(form).match(self.text, pos):
                return form
        return None

    def chunk(self, size, start=0):
        """Chapter-aligned chunks of at most `size` characters (end-of-corpus tail dropped)."""
        out = []
        for ch in self.chapters:
            bs = self.book_span[ch["book"]][0]
            s, e = bs + ch["start"], bs + ch["end"]
            i = s
            while i < e:
                out.append((i, min(i + size, e)))
                i += size
        return [c for c in out if c[0] >= start]
