"""Rank statistics, quantiles and resampling -- standard library only."""

from __future__ import annotations

import math
import random


def quantile(sorted_values, q):
    if not sorted_values:
        return float("nan")
    if len(sorted_values) == 1:
        return sorted_values[0]
    pos = q * (len(sorted_values) - 1)
    lo = int(math.floor(pos))
    hi = min(lo + 1, len(sorted_values) - 1)
    frac = pos - lo
    return sorted_values[lo] * (1.0 - frac) + sorted_values[hi] * frac


def auc(pos_scores, neg_scores):
    """P(a random positive scores above a random negative), ties counted 1/2.

    Rank based, so it needs no distributional assumption and no numpy.
    """
    n_pos, n_neg = len(pos_scores), len(neg_scores)
    if not n_pos or not n_neg:
        return float("nan")
    values = sorted([(s, 1) for s in pos_scores] + [(s, 0) for s in neg_scores],
                    key=lambda t: t[0])
    n = len(values)
    ranks = [0.0] * n
    i = 0
    while i < n:
        j = i
        while j + 1 < n and values[j + 1][0] == values[i][0]:
            j += 1
        mid = (i + j) / 2.0 + 1.0
        for k in range(i, j + 1):
            ranks[k] = mid
        i = j + 1
    r_pos = sum(ranks[k] for k in range(n) if values[k][1] == 1)
    return (r_pos - n_pos * (n_pos + 1) / 2.0) / (n_pos * n_neg)


def bootstrap_ci(values, statistic, iters=2000, seed=0, alpha=0.05):
    """Percentile bootstrap CI for a statistic of one sample."""
    if not values:
        return (float("nan"), float("nan"))
    rng = random.Random(seed)
    n = len(values)
    stats = []
    for _ in range(iters):
        sample = [values[rng.randrange(n)] for _ in range(n)]
        stats.append(statistic(sample))
    stats.sort()
    return (quantile(stats, alpha / 2.0), quantile(stats, 1.0 - alpha / 2.0))


def bootstrap_diff_ci(a, b, iters=2000, seed=0, alpha=0.05):
    """Percentile CI for mean(a) - mean(b), resampling each sample separately.

    Concatenating the two samples and slicing the resample does not recover the
    groups -- the resample is shuffled -- so the two are resampled apart.
    """
    if not a or not b:
        return (float("nan"), float("nan"))
    rng = random.Random(seed)
    na, nb = len(a), len(b)
    diffs = []
    for _ in range(iters):
        sa = [a[rng.randrange(na)] for _ in range(na)]
        sb = [b[rng.randrange(nb)] for _ in range(nb)]
        diffs.append(sum(sa) / na - sum(sb) / nb)
    diffs.sort()
    return (quantile(diffs, alpha / 2.0), quantile(diffs, 1.0 - alpha / 2.0))


def _binom_tail(k, n):
    return sum(math.comb(n, i) for i in range(0, k + 1)) / (2.0 ** n) if n else 1.0


def sign_test(pos, neg):
    """Two-sided exact sign test on `pos` wins against `neg` wins."""
    n = pos + neg
    if n == 0:
        return 1.0
    tail = _binom_tail(min(pos, neg), n)
    return min(1.0, 2.0 * tail)


def mcnemar(b, c):
    """Two-sided exact McNemar test on `b` and `c` discordant pairs."""
    return sign_test(b, c)
