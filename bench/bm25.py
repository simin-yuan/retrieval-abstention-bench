"""Okapi BM25 over chunks -- standard library only.

Baseline 1 of 2: a lexical retriever with no tuning beyond k1 and b, both fixed
in `config.py`.  Query term frequency is ignored (terms are de-duplicated), the
usual convention for short queries.
"""

from __future__ import annotations

import math

import config


class BM25:
    def __init__(self, chunks):
        self.token_ids = chunks.ids
        self.n = len(chunks.tokens)
        self.doc_len = [len(t) for t in chunks.tokens]
        self.avgdl = (sum(self.doc_len) / self.n) if self.n else 1.0
        self.tf = []
        self.postings = {}
        for i, toks in enumerate(chunks.tokens):
            counts = {}
            for t in toks:
                counts[t] = counts.get(t, 0) + 1
            self.tf.append(counts)
            for t in counts:
                self.postings.setdefault(t, []).append(i)
        self._idf_cache = {}

    def idf(self, term):
        v = self._idf_cache.get(term)
        if v is None:
            df = len(self.postings.get(term, ()))
            v = math.log(1.0 + (self.n - df + 0.5) / (df + 0.5))
            self._idf_cache[term] = v
        return v

    def search(self, query_tokens, k):
        """[(chunk_index, score), ...] best first."""
        scores = {}
        for term in set(query_tokens):
            idf = self.idf(term)
            for i in self.postings.get(term, ()):
                tf = self.tf[i][term]
                denom = tf + config.BM25_K1 * (
                    1.0 - config.BM25_B + config.BM25_B * self.doc_len[i] / self.avgdl)
                scores[i] = scores.get(i, 0.0) + idf * tf * (config.BM25_K1 + 1.0) / denom
        return sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))[:k]
