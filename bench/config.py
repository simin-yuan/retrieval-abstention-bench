"""Frozen parameters.

Everything that could be tuned after seeing a result lives here, in one file,
and the exam manifest records these constants.  A reported number can therefore
be checked against the parameters that were fixed before the run -- thresholds
are not allowed to move afterwards.
"""

# Corpus / exam
SEED = 20261011
CHUNK_SIZES = (800, 1600, 3200)          # ablation grid; chunks are chapter-aligned
MAX_CHUNK_LEN = max(CHUNK_SIZES)
TOP_K = (1, 3, 5, 10)

# Retrieval scoring
BM25_K1 = 1.2
BM25_B = 0.75
TOKEN_RE = r"[a-z0-9]+"

# Question generation
DROP_RATIOS = (0.4, 0.6, 0.8)

# A retrieved chunk counts as a hit when it covers this share of the gold span.
HIT_OVERLAP = 0.5

# A gold span counts as reachable under a chunking configuration when some
# chunk covers this share of it.  The exam keeps only spans reachable under
# EVERY configured chunk size, so the same questions are used by every arm.
REACH_COVERAGE = 0.8

# Bands for the IDF-weighted query/source overlap, low to high.  Fixed before
# any overlap is measured.
OVERLAP_BANDS = ((0.0, 0.2), (0.2, 0.4), (0.4, 0.6), (0.6, 0.8), (0.8, 1.01))

# Criterion A turns a score into a decision with a threshold.  The threshold is
# read off the calibration half of the gold questions so that the intended gold
# abstain rate is exactly this; the rule is fixed here, before any run.  The
# remaining half carries all reported numbers.
TARGET_GOLD_ABSTAIN = 0.05
CALIB_FRACTION = 0.5
