"""Word 1-2 gram TF-IDF with cosine similarity -- standard library only.

Baseline 2 of 2: the same tokens as BM25, but a bag-of-1-and-2-grams vector
model, which is the classic cheap baseline for lexical retrieval and fails in
different places than BM25 does.
"""

from __future__ import annotations

import math


def grams(tokens):
    out = list(tokens)
    out.extend(tokens[i] + "\u0001" + tokens[i + 1] for i in range(len(tokens) - 1))
    return out


class NgramTfidf:
    def __init__(self, chunks):
        self.token_ids = chunks.ids
        self.n = len(chunks.tokens)
        self.postings = {}            # gram -> [(doc, tf), ...]
        for i, toks in enumerate(chunks.tokens):
            counts = {}
            for g in grams(toks):
                counts[g] = counts.get(g, 0) + 1
            for g, c in counts.items():
                self.postings.setdefault(g, []).append((i, c))

        self.idf_cache = {}
        self.norms = [0.0] * self.n
        for g, posting in self.postings.items():
            idf = self.idf(g)
            for doc, tf in posting:
                w = (1.0 + math.log(tf)) * idf
                self.norms[doc] += w * w
        self.norms = [math.sqrt(v) or 1.0 for v in self.norms]

    def idf(self, gram):
        v = self.idf_cache.get(gram)
        if v is None:
            df = len(self.postings.get(gram, ()))
            v = math.log((1.0 + self.n) / (1.0 + df)) + 1.0
            self.idf_cache[gram] = v
        return v

    def search(self, query_tokens, k):
        """[(chunk_index, score), ...] best first."""
        counts = {}
        for g in grams(query_tokens):
            counts[g] = counts.get(g, 0) + 1
        qw, qnorm = {}, 0.0
        for g, c in counts.items():
            w = (1.0 + math.log(c)) * self.idf(g)
            qw[g] = w
            qnorm += w * w
        qnorm = math.sqrt(qnorm) or 1.0

        scores = {}
        for g, wq in qw.items():
            idf = self.idf(g)
            for doc, tf in self.postings.get(g, ()):
                scores[doc] = scores.get(doc, 0.0) + wq * idf * (1.0 + math.log(tf))
        ranked = [(doc, s / (qnorm * self.norms[doc])) for doc, s in scores.items()]
        return sorted(ranked, key=lambda kv: (-kv[1], kv[0]))[:k]
